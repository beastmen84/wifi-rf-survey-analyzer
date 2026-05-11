"""Qt live map scene, tooltips, marker rendering, and render worker."""

from io import BytesIO

import pandas as pd
from PIL import Image
from PySide6.QtCore import QObject, QPointF, QRectF, QSize, Qt, Signal, Slot
from PySide6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsEllipseItem,
    QGraphicsItemGroup,
    QGraphicsPathItem,
    QGraphicsPixmapItem,
    QGraphicsPolygonItem,
    QGraphicsScene,
    QGraphicsView,
    QWidget,
)

from app_logging import log_event, log_exception
from ap_groups import AP_ROLE_TEST, build_dominant_ap_group_labels, format_ap_label, normalize_ap_role
from ap_positioning import (
    AP_POSITION_MISSING,
    AP_POSITION_NO_SCALE,
    AP_POSITION_OK,
    AP_POSITION_STRONG_FAR,
    AP_POSITION_UNEXPECTED_DOMINANT,
    AP_POSITION_WEAK_CLOSE,
    analyze_dominant_ap_position,
)
from constants import SURVEY_FIELDNAMES
from heatmap_tools import get_channel_map_points, get_dominant_ap_points
from live_renderer import render_live_continuous_map
from map_rendering import get_channel_color, get_channel_sort_key, get_limited_bssid_color_map
from qt_floorplan import AP_MARKER_BASE_SIZE, load_ap_position_icon
from qt_tooltips import build_html_tooltip


LIVE_POINT_MARKER_BASE_SIZE = 14


class LiveMapRenderWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, rows, map_file, config, translations, aliases=None, ap_groups=None, px_per_meter=None):
        super().__init__()
        self.rows = list(rows or [])
        self.map_file = map_file
        self.config = config
        self.translations = translations
        self.aliases = aliases or {}
        self.ap_groups = list(ap_groups or [])
        self.px_per_meter = px_per_meter

    @Slot()
    def run(self):
        try:
            log_event(
                f"qt live render worker start map_type={self.config.map_type} band={self.config.band}",
                logger_name="live_map",
            )
            bg_image = load_floorplan_image(self.map_file)
            df = pd.DataFrame(self.rows, columns=SURVEY_FIELDNAMES)
            payload = render_live_map_payload(
                df=df,
                config=self.config,
                bg_image=bg_image,
                translations=self.translations,
                aliases=self.aliases,
                ap_groups=self.ap_groups,
                px_per_meter=self.px_per_meter,
            )
        except Exception as exc:
            log_exception("qt live render worker failed", exc, logger_name="live_map")
            self.failed.emit(str(exc))
            return

        point_count = len(payload.get("point_infos", [])) if payload else 0
        log_event(
            f"qt live render worker done payload={bool(payload)} points={point_count}",
            logger_name="live_map",
        )
        self.finished.emit(payload)


class LiveMapView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = None
        self.marker_items = []
        self.ap_marker_items = []
        self.zoom_level = 1.0
        self._pan_last_pos = None
        self._pan_cursor_active = False
        self.ap_position_icon = load_ap_position_icon()
        self.gradient_legend = LiveGradientLegendWidget(self.viewport())
        self.gradient_legend.setFixedSize(122, 220)
        self.gradient_legend.hide()

        self.setObjectName("liveMapView")
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setBackgroundBrush(QBrush(Qt.GlobalColor.darkGray))
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def clear(self):
        self.scene.clear()
        self.pixmap_item = None
        self.marker_items = []
        self.ap_marker_items = []
        self.zoom_level = 1.0
        self.end_pan()
        self.clear_gradient_legend()

    def set_payload(self, payload):
        self.clear()
        if not payload:
            return

        pixmap = pil_to_qpixmap(payload["image"])
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)
        self.scene.setSceneRect(pixmap.rect())
        self.add_markers(payload.get("point_infos", []))
        self.add_ap_markers(payload.get("ap_infos", []))
        self.resetTransform()
        self.zoom_level = 1.0
        self.fit_to_view()

    def add_markers(self, point_infos):
        for info in point_infos:
            try:
                x = float(info.get("x"))
                y = float(info.get("y"))
            except (TypeError, ValueError):
                continue

            item = self.create_marker_item(info)
            item.setPos(x, y)
            item.setZValue(20)
            tooltip = info.get("tooltip")
            if tooltip:
                item.setToolTip(str(tooltip))
            self.scene.addItem(item)
            self.marker_items.append(item)

    def add_ap_markers(self, ap_infos):
        for info in ap_infos:
            try:
                x = float(info.get("x"))
                y = float(info.get("y"))
            except (TypeError, ValueError):
                continue

            item = self.create_ap_marker_item(info)
            item.setPos(x, y)
            item.setZValue(30)
            tooltip = info.get("tooltip")
            if tooltip:
                item.setToolTip(str(tooltip))
            self.scene.addItem(item)
            self.ap_marker_items.append(item)

    def create_ap_marker_item(self, info):
        if info.get("highlight"):
            return self.create_highlighted_ap_marker_item(info)

        if self.ap_position_icon and not self.ap_position_icon.isNull():
            pixmap = self.ap_position_icon
            item = QGraphicsPixmapItem(pixmap)
            item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            item.setOffset(-pixmap.width() / 2, -pixmap.height() / 2)
            max_source_size = max(pixmap.width(), pixmap.height())
            if max_source_size > 0:
                item.setScale(AP_MARKER_BASE_SIZE / max_source_size)
            return item

        radius = AP_MARKER_BASE_SIZE / 2
        item = QGraphicsEllipseItem(-radius, -radius, radius * 2, radius * 2)
        item.setBrush(QBrush(QColor(str(info.get("color") or "#0d6efd"))))
        item.setPen(QPen(Qt.GlobalColor.white, 1.6))
        return item

    def create_highlighted_ap_marker_item(self, info):
        group = QGraphicsItemGroup()
        ring_radius = AP_MARKER_BASE_SIZE / 2 + 6
        ring = QGraphicsEllipseItem(-ring_radius, -ring_radius, ring_radius * 2, ring_radius * 2)
        ring.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        ring.setPen(QPen(QColor("#f1c40f"), 3.0))
        group.addToGroup(ring)

        if self.ap_position_icon and not self.ap_position_icon.isNull():
            pixmap = self.ap_position_icon
            icon = QGraphicsPixmapItem(pixmap)
            icon.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            icon.setOffset(-pixmap.width() / 2, -pixmap.height() / 2)
            max_source_size = max(pixmap.width(), pixmap.height())
            if max_source_size > 0:
                icon.setScale(AP_MARKER_BASE_SIZE / max_source_size)
            group.addToGroup(icon)
        else:
            radius = AP_MARKER_BASE_SIZE / 2
            marker = QGraphicsEllipseItem(-radius, -radius, radius * 2, radius * 2)
            marker.setBrush(QBrush(QColor(str(info.get("color") or "#0d6efd"))))
            marker.setPen(QPen(Qt.GlobalColor.white, 1.6))
            group.addToGroup(marker)

        return group

    def create_marker_item(self, info):
        shape = str(info.get("shape") or "circle")
        color = QColor(str(info.get("color") or "#111111"))
        outline = QColor(str(info.get("outline") or "#ffffff"))
        outline_width = float(info.get("outline_width") or 1.2)
        radius = LIVE_POINT_MARKER_BASE_SIZE / 2

        if shape == "triangle":
            polygon = QPolygonF([
                QPointF(0, -radius),
                QPointF(radius, radius),
                QPointF(-radius, radius),
            ])
            item = QGraphicsPolygonItem(polygon)
        elif shape == "cross":
            path = QPainterPath()
            path.moveTo(-radius, -radius)
            path.lineTo(radius, radius)
            path.moveTo(radius, -radius)
            path.lineTo(-radius, radius)
            item = QGraphicsPathItem(path)
        else:
            item = QGraphicsEllipseItem(-radius, -radius, radius * 2, radius * 2)

        if shape == "cross":
            item.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            item.setPen(QPen(outline, max(1.6, outline_width)))
        else:
            item.setBrush(QBrush(color))
            item.setPen(QPen(outline, outline_width))
        return item

    def zoom_in(self):
        self.set_zoom(self.zoom_level * 1.25)

    def zoom_out(self):
        self.set_zoom(self.zoom_level / 1.25)

    def set_zoom(self, zoom_level):
        if self.pixmap_item is None:
            return

        zoom_level = min(8.0, max(0.1, zoom_level))
        factor = zoom_level / self.zoom_level
        self.zoom_level = zoom_level
        self.scale(factor, factor)
        self.refresh_viewport_overlays()

    def fit_to_view(self):
        if self.pixmap_item is None:
            return

        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        transform = self.transform()
        self.zoom_level = max(transform.m11(), transform.m22())
        self.refresh_viewport_overlays()

    def set_gradient_legend(self, scale_payload):
        self.gradient_legend.set_scale_payload(scale_payload)
        self.position_gradient_legend()
        self.gradient_legend.show()
        self.gradient_legend.raise_()

    def clear_gradient_legend(self):
        self.gradient_legend.clear()
        self.gradient_legend.hide()

    def position_gradient_legend(self):
        viewport_size = self.viewport().size()
        width = max(112, min(128, viewport_size.width() // 5))
        height = max(156, min(230, viewport_size.height() - 28))
        self.gradient_legend.setFixedSize(width, height)
        self.gradient_legend.move(
            max(12, viewport_size.width() - width - 14),
            max(12, viewport_size.height() - height - 14),
        )
        self.gradient_legend.raise_()
        self.gradient_legend.update()

    def refresh_viewport_overlays(self):
        if not self.gradient_legend.isHidden():
            self.position_gradient_legend()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refresh_viewport_overlays()

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self.refresh_viewport_overlays()

    def can_pan(self):
        return (
            self.pixmap_item is not None
            and (
                self.horizontalScrollBar().maximum() > self.horizontalScrollBar().minimum()
                or self.verticalScrollBar().maximum() > self.verticalScrollBar().minimum()
            )
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.can_pan():
            self.begin_pan(event.position().toPoint())
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._pan_last_pos is not None:
            current_pos = event.position().toPoint()
            delta = current_pos - self._pan_last_pos
            self._pan_last_pos = current_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._pan_last_pos is not None:
            self.end_pan()
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        self.end_pan()
        super().leaveEvent(event)

    def begin_pan(self, position):
        self._pan_last_pos = position
        self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
        if not self._pan_cursor_active:
            QApplication.setOverrideCursor(Qt.CursorShape.ClosedHandCursor)
            self._pan_cursor_active = True

    def end_pan(self):
        self._pan_last_pos = None
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        if self._pan_cursor_active:
            QApplication.restoreOverrideCursor()
            self._pan_cursor_active = False

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
            return

        super().wheelEvent(event)


def load_floorplan_image(file_path):
    if str(file_path).lower().endswith(".pdf"):
        import fitz

        document = fitz.open(file_path)
        try:
            page = document[0]
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        finally:
            document.close()
        return image

    return Image.open(file_path).convert("RGB")


def pil_to_qpixmap(image):
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    pixmap = QPixmap()
    pixmap.loadFromData(buffer.getvalue(), "PNG")
    return pixmap


def create_marker_icon(color, shape="circle", outline_only=False):
    pixmap = QPixmap(18, 18)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    marker_color = QColor(str(color or "#7f8c8d"))
    pen = QPen(marker_color if outline_only else QColor("#1f2933"), 1.4)
    painter.setPen(pen)
    painter.setBrush(QBrush(Qt.BrushStyle.NoBrush if outline_only else marker_color))

    if shape == "triangle":
        polygon = QPolygonF([
            QPointF(9, 3),
            QPointF(15, 15),
            QPointF(3, 15),
        ])
        painter.drawPolygon(polygon)
    else:
        painter.drawEllipse(3, 3, 12, 12)
    painter.end()
    return QIcon(pixmap)


class LiveGradientLegendWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scale_payload = {}
        self.setMinimumHeight(180)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def sizeHint(self):
        return QSize(122, 220)

    def set_scale_payload(self, scale_payload):
        self.scale_payload = dict(scale_payload or {})
        self.update()

    def clear(self):
        self.scale_payload = {}
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.scale_payload:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        background = QColor(self.palette().color(QPalette.ColorRole.Window))
        background.setAlpha(235)
        border = QColor(self.palette().color(QPalette.ColorRole.Mid))
        text = QColor(self.palette().color(QPalette.ColorRole.WindowText))
        panel_rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        painter.setPen(QPen(border, 1))
        painter.setBrush(QBrush(background))
        painter.drawRoundedRect(panel_rect, 6, 6)

        margin = 10
        bar_width = 22
        label_gap = 8
        rect = QRectF(margin, margin, bar_width, max(40, self.height() - margin * 2))
        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        for position, color in gradient_stops(str(self.scale_payload.get("cmap", ""))):
            gradient.setColorAt(position, QColor(color))

        painter.fillRect(rect, QBrush(gradient))
        painter.setPen(QPen(border, 1))
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        painter.drawRoundedRect(rect, 3, 3)

        suffix = str(self.scale_payload.get("suffix", ""))
        max_label = f"{format_value(self.scale_payload.get('max'))}{suffix}"
        min_label = f"{format_value(self.scale_payload.get('min'))}{suffix}"
        midpoint = midpoint_label(self.scale_payload, suffix)
        text_left = rect.right() + label_gap
        text_width = max(20, self.width() - int(text_left) - margin)

        painter.setPen(text)
        metrics = painter.fontMetrics()
        painter.drawText(
            QRectF(text_left, rect.top() - 2, text_width, metrics.height() + 4),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            max_label,
        )
        painter.drawText(
            QRectF(text_left, rect.center().y() - metrics.height() / 2, text_width, metrics.height() + 4),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            midpoint,
        )
        painter.drawText(
            QRectF(text_left, rect.bottom() - metrics.height() - 2, text_width, metrics.height() + 4),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            min_label,
        )
        painter.end()


def gradient_stops(cmap):
    if cmap == "RdYlGn_r":
        return (
            (0.0, "#d94343"),
            (0.5, "#f2d33b"),
            (1.0, "#25a865"),
        )

    return (
        (0.0, "#25a865"),
        (0.5, "#f2d33b"),
        (1.0, "#d94343"),
    )


def midpoint_label(scale_payload, suffix):
    try:
        minimum = float(scale_payload.get("min"))
        maximum = float(scale_payload.get("max"))
    except (TypeError, ValueError):
        return ""

    return f"{format_value((minimum + maximum) / 2)}{suffix}"


def render_live_map_payload(df, config, bg_image, translations, aliases=None, ap_groups=None, px_per_meter=None):
    if config.is_channel:
        payload = build_channel_payload(df, config, bg_image, translations, aliases or {})
        return attach_ap_position_markers(
            payload,
            ap_groups or [],
            aliases or {},
            translations,
            selected_group=config.ap_group_filter,
        )

    if config.is_dominant:
        payload = build_dominant_payload(
            df,
            config,
            bg_image,
            translations,
            aliases or {},
            ap_groups or [],
            px_per_meter,
        )
        return attach_ap_position_markers(payload, ap_groups or [], aliases or {}, translations)

    payload = render_live_continuous_map(
        df,
        config,
        bg_image,
        translations,
        lambda map_type, row, raw_rows: build_live_tooltip(
            map_type,
            row,
            raw_rows,
            translations,
            aliases or {},
        ),
        get_color_scale_limits,
    )
    return attach_ap_position_markers(
        payload,
        ap_groups or [],
        aliases or {},
        translations,
        selected_group=config.ap_group_filter,
    )


def attach_ap_position_markers(payload, ap_groups, aliases, translations, selected_group=""):
    if not payload:
        return payload

    payload["ap_infos"] = build_ap_position_marker_infos(
        ap_groups,
        aliases,
        translations,
        selected_group=selected_group,
    )
    return payload


def build_ap_position_marker_infos(ap_groups, aliases, translations, selected_group=""):
    ap_infos = []
    selected_group = str(selected_group or "")
    for group in ap_groups or []:
        if normalize_ap_role(group.get("role")) == AP_ROLE_TEST:
            continue

        position = group.get("position") or {}
        try:
            x = int(position.get("x"))
            y = int(position.get("y"))
        except (TypeError, ValueError):
            continue

        group_id = str(group.get("group_id", ""))
        label = str(group.get("alias", "")).strip() or format_group_label(group_id, aliases)
        ap_infos.append({
            "x": x,
            "y": y,
            "label": label,
            "highlight": bool(selected_group and group_id == selected_group),
            "tooltip": build_ap_position_tooltip(group, label, x, y, translations),
        })
    return ap_infos


def build_ap_position_tooltip(group, label, x, y, translations):
    bssids = ", ".join(str(bssid) for bssid in group.get("bssids", []) if str(bssid)) or "-"
    return build_html_tooltip(
        translations.get("ap_position_marker_title", "AP position"),
        [
            (translations.get("ap_group", "AP group"), group.get("group_id", "-")),
            (translations.get("ap_label", "Label"), label),
            ("x/y", f"{x}, {y}"),
            ("BSSID", bssids),
        ],
        "#0d6efd",
    )


def build_channel_payload(df, config, bg_image, translations, aliases):
    channel_df = get_channel_map_points(
        df,
        config.ssid,
        config.band,
        ap_group_map=config.ap_group_map,
        ap_group_roles=config.ap_group_roles,
    )
    if config.ap_group_filter and not channel_df.empty:
        channel_df = channel_df[channel_df["ap_group"] == config.ap_group_filter]
    if channel_df.empty:
        return None

    point_infos = []
    legend_items_by_label = {}
    for _index, row in channel_df.iterrows():
        channel = row.get("channel", "")
        color = get_channel_color(channel, config.band)
        label = format_channel_legend_label(row, aliases)
        sort_key = get_channel_sort_key(channel, config.band) + (str(label).casefold(),)
        point_infos.append({
            "x": float(row["x"]),
            "y": float(row["y"]),
            "color": color,
            "outline": "black",
            "outline_width": 1,
            "legend_label": label,
            "legend_sort_key": sort_key,
            "tooltip": build_channel_tooltip(row, config, translations, aliases),
        })
        legend_items_by_label.setdefault(label, {
            "label": label,
            "color": color,
            "sort_key": sort_key,
        })

    legend_items = sorted(legend_items_by_label.values(), key=lambda item: item["sort_key"])
    return {
        "image": bg_image.copy(),
        "point_infos": point_infos,
        "scale_payload": {
            "kind": "swatches",
            "title": translations.get("channel_title", "AP channels"),
            "items": legend_items,
        },
    }


def build_dominant_payload(df, config, bg_image, translations, aliases, ap_groups, px_per_meter):
    dominant_df = get_dominant_ap_points(
        df,
        config.ssid,
        config.band,
        ap_group_map=config.ap_group_map,
        ap_group_roles=config.ap_group_roles,
    )
    if dominant_df.empty:
        return None

    color_map, _visible_ap_groups, _hidden_ap_count = get_limited_bssid_color_map(dominant_df)
    group_labels = build_dominant_ap_group_labels(dominant_df, aliases)
    legend_items_by_label = {}
    point_infos = []
    has_roaming_overlap = False
    has_position_warning = False

    for _index, row in dominant_df.iterrows():
        position_analysis = analyze_dominant_ap_position(row, ap_groups, px_per_meter=px_per_meter)
        position_warning_color = get_ap_position_warning_color(position_analysis)
        has_position_warning = has_position_warning or bool(position_warning_color)
        has_roaming_overlap = has_roaming_overlap or bool(row.get("roaming_overlap"))
        label = group_labels.get(
            row.get("dominant_ap_group", ""),
            format_ap_label(row.get("dominant_bssid", ""), aliases, row.get("dominant_ap_group", "")),
        )
        color = color_map.get(row.get("dominant_ap_group", ""), "#7f8c8d")
        point_infos.append({
            "x": float(row["x"]),
            "y": float(row["y"]),
            "color": color,
            "outline": "#f1c40f" if row.get("roaming_overlap") else "black",
            "outline_width": 1,
            "shape": "triangle" if position_warning_color else "circle",
            "legend_label": label,
            "tooltip": build_dominant_tooltip(row, config, translations, aliases, position_analysis),
        })
        legend_items_by_label.setdefault(label, {
            "label": label,
            "color": color,
        })

    legend_items = sorted(legend_items_by_label.values(), key=lambda item: item["label"].casefold())
    if has_roaming_overlap:
        legend_items.append({
            "label": translations.get("roaming_overlap", "Delta <= 5 dB"),
            "color": "#f1c40f",
            "outline_only": True,
        })
    if has_position_warning:
        legend_items.append({
            "label": translations.get("ap_position_warning_legend", "Triangle = suspicious AP position"),
            "color": "#d62728",
            "shape": "triangle",
        })

    return {
        "image": bg_image.copy(),
        "point_infos": point_infos,
        "scale_payload": {
            "kind": "swatches",
            "title": translations.get("dominant_title", "Dominant AP"),
            "items": legend_items,
        },
    }


def get_color_scale_limits(grid_z, config):
    if getattr(config, "color_scale", "fixed") == "auto":
        finite_values = grid_z[pd.notna(grid_z)]
        if len(finite_values):
            return float(finite_values.min()), float(finite_values.max())

    return -90, -40


def build_live_tooltip(map_type, row, raw_rows, translations, aliases=None):
    aliases = aliases or {}
    if map_type == "interference":
        return build_html_tooltip(
            translations.get("interference_title", "AP interference"),
            [
                ("x/y", f"{format_value(row.get('x'))}, {format_value(row.get('y'))}"),
                (translations.get("risk", "Risk"), f"{format_value(row.get('risk'))}%"),
                (
                    translations.get("serving_ap", "Serving AP"),
                    format_ap_label(row.get("serving_bssid", ""), aliases, row.get("serving_ap_group", "")),
                ),
                (
                    translations.get("serving_channel", "Serving channel"),
                    format_channel_with_width(row.get("serving_channel"), row.get("serving_channel_width_mhz")),
                ),
                (
                    translations.get("interferer", "Interferer"),
                    format_ap_label(
                        row.get("strongest_interferer_bssid", ""),
                        aliases,
                        row.get("strongest_interferer_ap_group", ""),
                    ),
                ),
                (
                    translations.get("interferer_channel", "Interferer channel"),
                    format_channel_with_width(
                        row.get("strongest_interferer_channel"),
                        row.get("strongest_interferer_channel_width_mhz"),
                    ),
                ),
            ],
            "#d73027",
        )

    return build_html_tooltip(
        translations.get("signal_title", "Signal coverage"),
        [
            ("SSID", row.get("ssid", "-")),
            ("x/y", f"{format_value(row.get('x'))}, {format_value(row.get('y'))}"),
            ("dBm", format_value(row.get("signal_dbm"))),
            (translations.get("source_rows", "Source rows"), raw_rows if raw_rows is not None else "-"),
        ],
        "#111111",
    )


def build_channel_tooltip(row, config, translations, aliases):
    return build_html_tooltip(
        translations.get("channel_title", "AP channels"),
        [
            ("SSID", config.ssid),
            ("x/y", f"{format_value(row.get('x'))}, {format_value(row.get('y'))}"),
            (
                translations.get("reference_ap", "AP"),
                format_ap_label(row.get("bssid", ""), aliases, row.get("ap_group", "")),
            ),
            (translations.get("ap_group_role", "Role"), format_ap_role(row.get("ap_role"), translations)),
            (
                translations.get("reference_channel", "Channel"),
                format_channel_with_width(row.get("channel"), row.get("channel_width_mhz")),
            ),
            (translations.get("best", "Best"), f"{format_value(row.get('signal_dbm'))} dBm"),
            (translations.get("confidence", "confidence"), format_row_confidence(row)),
        ],
        get_channel_color(row.get("channel", ""), config.band),
    )


def build_dominant_tooltip(row, config, translations, aliases, position_analysis):
    position_rows = build_position_tooltip_rows(position_analysis, translations, aliases)
    return build_html_tooltip(
        translations.get("dominant_title", "Dominant AP"),
        [
            ("SSID", config.ssid),
            ("x/y", f"{format_value(row.get('x'))}, {format_value(row.get('y'))}"),
            (
                translations.get("reference_ap", "AP"),
                format_ap_label(row.get("dominant_bssid", ""), aliases, row.get("dominant_ap_group", "")),
            ),
            (
                translations.get("ap_group_role", "Role"),
                format_ap_role(row.get("dominant_ap_role"), translations),
            ),
            (
                translations.get("reference_channel", "Channel"),
                format_channel_with_width(row.get("dominant_channel"), row.get("dominant_channel_width_mhz")),
            ),
            (translations.get("best", "Best"), f"{format_value(row.get('dominant_signal_dbm'))} dBm"),
            (translations.get("confidence", "confidence"), format_named_confidence(row, "dominant")),
            (
                translations.get("second_ap", "Second AP"),
                format_ap_label(row.get("second_bssid", ""), aliases, row.get("second_ap_group", ""))
                if row.get("second_bssid", "")
                else "-",
            ),
            (
                translations.get("second_ap_role", "Second AP role"),
                format_ap_role(row.get("second_ap_role"), translations) if row.get("second_ap_role") else "-",
            ),
            (translations.get("second_confidence", "Second confidence"), format_named_confidence(row, "second")),
            ("Delta", f"{format_value(row.get('delta_db'))} dB"),
        ] + position_rows,
        "#f1c40f" if row.get("roaming_overlap") else "#34495e",
    )


def build_position_tooltip_rows(analysis, translations, aliases=None):
    if not analysis or analysis.get("status") == AP_POSITION_MISSING:
        return []

    rows = [
        (
            translations.get("ap_position_distance", "AP distance"),
            format_ap_position_distance(analysis, "dominant", translations),
        )
    ]
    nearest_group = analysis.get("nearest_ap_group", "")
    dominant_group = analysis.get("dominant_ap_group", "")
    if nearest_group and nearest_group != dominant_group:
        rows.append((
            translations.get("ap_position_nearest", "Nearest physical AP"),
            f"{format_group_label(nearest_group, aliases or {})} "
            f"({format_ap_position_distance(analysis, 'nearest', translations)})",
        ))
    rows.append((
        translations.get("ap_position_analysis", "Position analysis"),
        format_ap_position_status(analysis, translations),
    ))
    return rows


def format_channel_legend_label(row, aliases):
    return (
        f"CH {format_value(row.get('channel'))} - "
        f"{format_ap_label(row.get('bssid', ''), aliases, row.get('ap_group', ''))}"
    )


def format_group_label(group_id, aliases):
    return aliases.get(str(group_id), "") or str(group_id or "-")


def format_channel_with_width(channel, width):
    channel_label = format_value(channel)
    width_label = format_value(width)
    if width_label == "-":
        return f"CH {channel_label}"
    return f"CH {channel_label} / {width_label} MHz"


def format_ap_role(role, translations):
    return translations.get(f"ap_group_role_{normalize_ap_role(role)}", str(role or "-"))


def format_row_confidence(row):
    samples_seen = format_value(row.get("samples_seen", ""))
    samples_total = format_value(row.get("samples_total", ""))
    confidence = format_value(row.get("scan_confidence", ""))
    if samples_seen == "-" or samples_total == "-":
        return "-"
    suffix = f" ({confidence})" if confidence != "-" else ""
    return f"{samples_seen}/{samples_total}{suffix}"


def format_named_confidence(row, prefix):
    samples_seen = format_value(row.get(f"{prefix}_samples_seen", ""))
    samples_total = format_value(row.get(f"{prefix}_samples_total", ""))
    confidence = format_value(row.get(f"{prefix}_scan_confidence", ""))
    if samples_seen == "-" or samples_total == "-":
        return "-"
    suffix = f" ({confidence})" if confidence != "-" else ""
    return f"{samples_seen}/{samples_total}{suffix}"


def get_ap_position_warning_color(analysis):
    warnings = analysis.get("warnings", []) if analysis else []
    if not warnings:
        return ""

    if AP_POSITION_STRONG_FAR in warnings or AP_POSITION_WEAK_CLOSE in warnings:
        return "#d62728"
    return "#ff7f0e"


def format_ap_position_distance(analysis, key, translations):
    distance_m = analysis.get(f"{key}_distance_m")
    if distance_m is not None:
        return translations.get("ap_position_distance_m", "{distance} m").format(distance=round(distance_m, 1))

    distance_px = analysis.get(f"{key}_distance_px")
    if distance_px is not None:
        return translations.get("ap_position_distance_px", "{distance} px").format(
            distance=int(round(distance_px))
        )
    return "-"


def format_ap_position_status(analysis, translations):
    warnings = analysis.get("warnings", [])
    if warnings:
        return "; ".join(
            translations.get(ap_position_warning_translation_key(warning), warning)
            for warning in warnings
        )

    status = analysis.get("status")
    if status == AP_POSITION_NO_SCALE:
        return translations.get("ap_position_no_scale", "Scale not calibrated")
    if status == AP_POSITION_OK:
        return translations.get("ap_position_ok", "Consistent")
    return "-"


def ap_position_warning_translation_key(warning):
    return {
        AP_POSITION_STRONG_FAR: "ap_position_strong_far",
        AP_POSITION_WEAK_CLOSE: "ap_position_weak_close",
        AP_POSITION_UNEXPECTED_DOMINANT: "ap_position_unexpected_dominant",
    }.get(warning, "ap_position_unknown_warning")


def format_value(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value if value not in (None, "") else "-")

    if pd.isna(number):
        return "-"
    if number.is_integer():
        return str(int(number))
    return f"{number:.1f}"
