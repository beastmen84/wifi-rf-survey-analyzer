"""Qt graphics view used for floor plans, survey points, and AP markers."""

from pathlib import Path
import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
)

from app_core.units import (
    MEASUREMENT_SYSTEM_IMPERIAL,
    distance_unit_label,
    display_units_to_meters,
    meters_to_display_units,
    normalize_measurement_system,
)
from qt_ui.qt_tooltips import build_html_tooltip


AP_MARKER_BASE_SIZE = 20
METRIC_GRID_INTERVALS_M = (0.5, 1.0, 2.0, 5.0, 10.0, 20.0)
IMPERIAL_GRID_INTERVALS_FT = (1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 50.0)
MIN_GRID_SPACING_PX = 40.0
GRID_MAJOR_EVERY = 5


class FloorplanView(QGraphicsView):
    surveyPointRequested = Signal(int, int)
    apPositionPicked = Signal(str, int, int)
    apPositionCancelled = Signal()
    scaleCalibrationFirstPointPicked = Signal()
    scaleCalibrationCompleted = Signal(float)
    scaleCalibrationCancelled = Signal()
    pointSelected = Signal(dict)
    pointSelectionCleared = Signal()
    boundariesMaskChanged = Signal(bool)

    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = None
        self.marker_items = []
        self.ap_marker_items = []
        self.grid_items = []
        self.scale_calibration_items = []
        self.scale_calibration_points = []
        self.selected_point_key = None
        self.zoom_level = 1.0
        self.pending_ap_position_group_id = ""
        self.pending_ap_position_label = ""
        self.scale_calibration_active = False
        self.ap_position_icon = load_ap_position_icon()
        self.ap_tooltip_formatter = None
        self.grid_visible = False
        self.grid_px_per_meter = None
        self.grid_measurement_system = "metric"
        self.grid_color = "#3A6EA5"
        self.grid_label = ""
        self.grid_ui_scale = 1.0
        self.boundaries_edit_active = False
        self.boundaries_tool = "draw"
        self.boundaries_shape = "circle"
        self.boundaries_brush_size_px = 36.0
        self.boundaries_mask_image = None
        self.boundaries_mask_item = None
        self.boundaries_mask_has_content = False
        self.boundaries_drawing_active = False
        self.boundaries_last_point = None

        self.setObjectName("floorplanView")
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setBackgroundBrush(QBrush(Qt.GlobalColor.darkGray))

    def load_floorplan(self, file_path):
        pixmap = load_floorplan_pixmap(file_path)
        if pixmap.isNull():
            raise ValueError(f"Cannot load floor plan: {file_path}")

        self.reset_boundaries_mask(emit_signal=False)
        self.scene.clear()
        self.marker_items = []
        self.ap_marker_items = []
        self.grid_items = []
        self.scale_calibration_items = []
        self.scale_calibration_points = []
        self.selected_point_key = None
        self.scale_calibration_active = False
        self.boundaries_edit_active = False
        self.pending_ap_position_group_id = ""
        self.pending_ap_position_label = ""
        self.viewport().unsetCursor()
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)
        self.scene.setSceneRect(pixmap.rect())
        self.refresh_grid()
        self.resetTransform()
        self.zoom_level = 1.0
        self.fit_to_view()

    def clear_floorplan(self):
        self.reset_boundaries_mask(emit_signal=False)
        self.scene.clear()
        self.pixmap_item = None
        self.marker_items = []
        self.ap_marker_items = []
        self.grid_items = []
        self.grid_visible = False
        self.scale_calibration_items = []
        self.scale_calibration_points = []
        self.boundaries_edit_active = False
        self.boundaries_drawing_active = False
        self.boundaries_last_point = None
        self.selected_point_key = None
        self.zoom_level = 1.0
        self.cancel_ap_position_pick(emit_signal=False)
        self.cancel_scale_calibration_pick(emit_signal=False)

    def has_floorplan(self):
        return self.pixmap_item is not None

    def set_boundaries_edit_mode(self, active):
        active = bool(active and self.has_floorplan())
        if active:
            self.cancel_ap_position_pick(emit_signal=False)
            self.cancel_scale_calibration_pick(emit_signal=False)

        self.boundaries_edit_active = active
        self.boundaries_drawing_active = False
        self.boundaries_last_point = None
        if self.boundaries_mask_item is not None:
            self.boundaries_mask_item.setVisible(active)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.viewport().unsetCursor()

    def set_boundaries_tool_state(self, tool="draw", shape="circle"):
        self.boundaries_tool = "eraser" if tool == "eraser" else "draw"
        self.boundaries_shape = "square" if shape == "square" else "circle"

    def has_boundaries_mask(self):
        return self.boundaries_mask_has_content

    def reset_boundaries_mask(self, emit_signal=True):
        if (
            self.boundaries_mask_item is not None
            and self.boundaries_mask_item.scene() is self.scene
        ):
            self.scene.removeItem(self.boundaries_mask_item)
        self.boundaries_mask_image = None
        self.boundaries_mask_item = None
        self.boundaries_mask_has_content = False
        self.boundaries_drawing_active = False
        self.boundaries_last_point = None
        if emit_signal:
            self.boundariesMaskChanged.emit(False)

    def clear_boundaries_mask(self):
        if self.boundaries_mask_image is None and self.boundaries_mask_item is None:
            if self.boundaries_mask_has_content:
                self.boundaries_mask_has_content = False
                self.boundariesMaskChanged.emit(False)
            return

        if self.boundaries_mask_image is not None:
            self.boundaries_mask_image.fill(Qt.GlobalColor.transparent)
        if self.boundaries_mask_item is not None and self.boundaries_mask_image is not None:
            self.boundaries_mask_item.setPixmap(QPixmap.fromImage(self.boundaries_mask_image))
        changed = self.boundaries_mask_has_content
        self.boundaries_mask_has_content = False
        self.boundaries_drawing_active = False
        self.boundaries_last_point = None
        self.viewport().update()
        if changed:
            self.boundariesMaskChanged.emit(False)

    def ensure_boundaries_mask(self):
        if not self.has_floorplan():
            return False

        if self.boundaries_mask_image is None:
            source_pixmap = self.pixmap_item.pixmap()
            self.boundaries_mask_image = QImage(
                source_pixmap.size(),
                QImage.Format.Format_ARGB32_Premultiplied,
            )
            self.boundaries_mask_image.fill(Qt.GlobalColor.transparent)

        if self.boundaries_mask_item is None:
            self.boundaries_mask_item = QGraphicsPixmapItem(
                QPixmap.fromImage(self.boundaries_mask_image)
            )
            self.boundaries_mask_item.setZValue(6)
            self.boundaries_mask_item.setVisible(self.boundaries_edit_active)
            self.scene.addItem(self.boundaries_mask_item)

        return True

    def apply_boundaries_brush(self, x, y):
        if not self.ensure_boundaries_mask():
            return

        point = self.clamp_boundaries_point(QPointF(float(x), float(y)))
        painter = QPainter(self.boundaries_mask_image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        if self.boundaries_tool == "eraser":
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.setBrush(Qt.GlobalColor.transparent)
        else:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setBrush(QColor(37, 99, 235, 90))

        half = self.boundaries_brush_size_px / 2.0
        rect = QRectF(
            point.x() - half,
            point.y() - half,
            self.boundaries_brush_size_px,
            self.boundaries_brush_size_px,
        )
        if self.boundaries_shape == "square":
            painter.drawRect(rect)
        else:
            painter.drawEllipse(rect)
        painter.end()

        self.boundaries_mask_item.setPixmap(QPixmap.fromImage(self.boundaries_mask_image))
        if self.boundaries_tool != "eraser" and not self.boundaries_mask_has_content:
            self.boundaries_mask_has_content = True
            self.boundariesMaskChanged.emit(True)
        self.viewport().update()

    def apply_boundaries_stroke(self, start_point, end_point):
        start_point = self.clamp_boundaries_point(start_point)
        end_point = self.clamp_boundaries_point(end_point)
        dx = end_point.x() - start_point.x()
        dy = end_point.y() - start_point.y()
        distance = math.hypot(dx, dy)
        step = max(4.0, self.boundaries_brush_size_px / 3.0)
        steps = max(1, int(math.ceil(distance / step)))
        for index in range(1, steps + 1):
            ratio = index / steps
            self.apply_boundaries_brush(
                start_point.x() + dx * ratio,
                start_point.y() + dy * ratio,
            )

    def clamp_boundaries_point(self, point):
        rect = self.scene.sceneRect()
        if rect.isNull():
            return point
        return QPointF(
            min(max(point.x(), rect.left()), rect.right()),
            min(max(point.y(), rect.top()), rect.bottom()),
        )

    def set_grid(
        self,
        visible,
        px_per_meter=None,
        measurement_system="metric",
        color="#3A6EA5",
        label="",
        ui_scale=1.0,
    ):
        self.grid_visible = bool(visible and px_per_meter)
        self.grid_px_per_meter = float(px_per_meter) if px_per_meter else None
        self.grid_measurement_system = normalize_measurement_system(measurement_system)
        self.grid_color = color
        self.grid_label = str(label or "") if self.grid_visible else ""
        self.grid_ui_scale = max(0.5, float(ui_scale or 1.0))
        self.refresh_grid()
        self.viewport().update()

    def refresh_grid(self):
        self.clear_grid_items()
        if not self.has_floorplan() or not self.grid_visible or not self.grid_px_per_meter:
            return

        interval_m = choose_grid_interval_meters(
            self.grid_px_per_meter,
            self.grid_measurement_system,
        )
        spacing_px = interval_m * self.grid_px_per_meter
        if spacing_px <= 0:
            return

        rect = self.scene.sceneRect()
        width = rect.width()
        height = rect.height()
        if width <= 0 or height <= 0:
            return

        minor_color = QColor(self.grid_color)
        minor_color.setAlpha(65)
        major_color = QColor(self.grid_color)
        major_color.setAlpha(115)
        minor_pen = QPen(minor_color, 1.0)
        major_pen = QPen(major_color, 1.5)

        x = 0.0
        index = 0
        while x <= width:
            item = QGraphicsLineItem(x, 0, x, height)
            item.setPen(major_pen if index % GRID_MAJOR_EVERY == 0 else minor_pen)
            item.setZValue(4)
            self.scene.addItem(item)
            self.grid_items.append(item)
            index += 1
            x = index * spacing_px

        y = 0.0
        index = 0
        while y <= height:
            item = QGraphicsLineItem(0, y, width, y)
            item.setPen(major_pen if index % GRID_MAJOR_EVERY == 0 else minor_pen)
            item.setZValue(4)
            self.scene.addItem(item)
            self.grid_items.append(item)
            index += 1
            y = index * spacing_px

    def clear_grid_items(self):
        for item in self.grid_items:
            self.scene.removeItem(item)
        self.grid_items = []

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        if not self.grid_visible or not self.grid_label:
            return

        painter.save()
        painter.resetTransform()
        painter.setClipping(False)
        font = painter.font()
        font.setBold(True)
        font.setPointSizeF(font.pointSizeF() * self.grid_ui_scale)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        margin = scaled_grid_value(12, self.grid_ui_scale)
        padding_x = scaled_grid_value(10, self.grid_ui_scale)
        padding_y = scaled_grid_value(5, self.grid_ui_scale)
        extra_width = scaled_grid_value(8, self.grid_ui_scale)
        radius = scaled_grid_value(4, self.grid_ui_scale)
        text_width = metrics.horizontalAdvance(self.grid_label)
        text_height = metrics.height()
        label_rect = QRectF(
            margin,
            margin,
            text_width + padding_x * 2 + extra_width,
            text_height + padding_y * 2,
        )
        background = QColor("#FFFFFF")
        background.setAlpha(230)
        border = QColor(self.grid_color)
        border.setAlpha(180)
        painter.setBrush(QBrush(background))
        painter.setPen(QPen(border, 1.0))
        painter.drawRoundedRect(label_rect, radius, radius)
        painter.setPen(QColor(self.grid_color))
        painter.drawText(
            label_rect.adjusted(padding_x, padding_y, -padding_x, -padding_y),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.grid_label,
        )
        painter.restore()

    def set_points(self, points):
        for item in self.marker_items:
            self.scene.removeItem(item)
        self.marker_items = []

        if not self.has_floorplan():
            return

        for point in points:
            try:
                x = float(point.get("x", 0))
                y = float(point.get("y", 0))
                signal = float(point.get("best_signal_dbm", point.get("signal_dbm", -90)))
            except (TypeError, ValueError):
                continue

            radius = 7
            item = QGraphicsEllipseItem(x - radius, y - radius, radius * 2, radius * 2)
            self.style_point_marker(item, point_color(signal), self.point_key(point) == self.selected_point_key)
            item.setToolTip(format_point_tooltip(point))
            item.setData(0, dict(point))
            self.scene.addItem(item)
            self.marker_items.append(item)

    def style_point_marker(self, item, color, selected=False):
        item.setBrush(QBrush(color))
        if selected:
            item.setPen(QPen(QColor("#1f2937"), 3.2))
            item.setZValue(20)
        else:
            item.setPen(QPen(Qt.GlobalColor.white, 2.0))
            item.setZValue(10)

    def point_key(self, point):
        point_id = str(point.get("point_id", "")).strip()
        if point_id:
            return ("id", point_id)

        return (
            "position",
            str(point.get("timestamp", "")),
            str(point.get("x", "")),
            str(point.get("y", "")),
        )

    def select_point(self, point):
        self.selected_point_key = self.point_key(point) if point else None
        self.refresh_point_marker_selection()

    def clear_selected_point(self):
        self.selected_point_key = None
        self.refresh_point_marker_selection()

    def refresh_point_marker_selection(self):
        for item in self.marker_items:
            point = item.data(0)
            if not isinstance(point, dict):
                continue
            try:
                signal = float(point.get("best_signal_dbm", point.get("signal_dbm", -90)))
            except (TypeError, ValueError):
                signal = -90
            self.style_point_marker(
                item,
                point_color(signal),
                self.point_key(point) == self.selected_point_key,
            )

    def set_ap_groups(self, groups):
        for item in self.ap_marker_items:
            self.scene.removeItem(item)
        self.ap_marker_items = []

        if not self.has_floorplan():
            return

        for group in groups or []:
            position = group.get("position") or {}
            try:
                x = int(position.get("x"))
                y = int(position.get("y"))
            except (TypeError, ValueError):
                continue

            label = str(group.get("alias", "")).strip() or str(group.get("group_id", ""))
            item = self.create_ap_marker(x, y, group, label)
            self.scene.addItem(item)
            self.ap_marker_items.append(item)

    def create_ap_marker(self, x, y, group, label):
        if self.ap_position_icon and not self.ap_position_icon.isNull():
            pixmap = self.ap_position_icon
            item = QGraphicsPixmapItem(pixmap)
            item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            item.setOffset(-pixmap.width() / 2, -pixmap.height() / 2)
            max_source_size = max(pixmap.width(), pixmap.height())
            if max_source_size > 0:
                item.setScale(AP_MARKER_BASE_SIZE / max_source_size)
            item.setPos(x, y)
        else:
            radius = AP_MARKER_BASE_SIZE / 2
            item = QGraphicsEllipseItem(-radius, -radius, radius * 2, radius * 2)
            item.setBrush(QBrush(QColor("#0d6efd")))
            item.setPen(QPen(Qt.GlobalColor.white, 1.6))
            item.setPos(x, y)

        item.setZValue(30)
        tooltip = (
            self.ap_tooltip_formatter(group, label, x, y)
            if callable(self.ap_tooltip_formatter)
            else format_ap_tooltip(group, label, x, y)
        )
        item.setToolTip(tooltip)
        return item

    def start_ap_position_pick(self, group_id, label):
        if not self.has_floorplan():
            return False

        self.cancel_scale_calibration_pick(emit_signal=False)
        self.pending_ap_position_group_id = str(group_id)
        self.pending_ap_position_label = str(label or group_id)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        return True

    def cancel_ap_position_pick(self, emit_signal=True):
        if not self.pending_ap_position_group_id:
            return False

        self.pending_ap_position_group_id = ""
        self.pending_ap_position_label = ""
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.viewport().unsetCursor()
        if emit_signal:
            self.apPositionCancelled.emit()
        return True

    def start_scale_calibration_pick(self):
        if not self.has_floorplan():
            return False

        self.cancel_ap_position_pick(emit_signal=False)
        self.clear_scale_calibration_overlay()
        self.scale_calibration_active = True
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        return True

    def cancel_scale_calibration_pick(self, emit_signal=True):
        if not self.scale_calibration_active and not self.scale_calibration_points:
            return False

        self.scale_calibration_active = False
        self.clear_scale_calibration_overlay()
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.viewport().unsetCursor()
        if emit_signal:
            self.scaleCalibrationCancelled.emit()
        return True

    def clear_scale_calibration_overlay(self):
        for item in self.scale_calibration_items:
            self.scene.removeItem(item)
        self.scale_calibration_items = []
        self.scale_calibration_points = []

    def pick_scale_calibration_point(self, x, y):
        self.scale_calibration_points.append((float(x), float(y)))
        marker = QGraphicsEllipseItem(float(x) - 5, float(y) - 5, 10, 10)
        marker.setBrush(QBrush(QColor("#0d6efd")))
        marker.setPen(QPen(Qt.GlobalColor.white, 1.6))
        marker.setZValue(40)
        self.scene.addItem(marker)
        self.scale_calibration_items.append(marker)

        if len(self.scale_calibration_points) == 1:
            self.scaleCalibrationFirstPointPicked.emit()
            return

        first_x, first_y = self.scale_calibration_points[0]
        line = QGraphicsLineItem(first_x, first_y, float(x), float(y))
        line.setPen(QPen(QColor("#0d6efd"), 3))
        line.setZValue(39)
        self.scene.addItem(line)
        self.scale_calibration_items.append(line)

        distance_px = math.hypot(float(x) - first_x, float(y) - first_y)
        self.scale_calibration_active = False
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.viewport().unsetCursor()
        self.scaleCalibrationCompleted.emit(distance_px)

    def zoom_in(self):
        self.set_zoom(self.zoom_level * 1.25)

    def zoom_out(self):
        self.set_zoom(self.zoom_level / 1.25)

    def set_zoom(self, zoom_level):
        if not self.has_floorplan():
            return

        zoom_level = min(6.0, max(0.1, zoom_level))
        factor = zoom_level / self.zoom_level
        self.zoom_level = zoom_level
        self.scale(factor, factor)

    def fit_to_view(self):
        if not self.has_floorplan():
            return

        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        transform = self.transform()
        self.zoom_level = max(transform.m11(), transform.m22())

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
            return
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            delta = event.angleDelta().y() or event.angleDelta().x()
            if delta:
                scroll_bar = self.horizontalScrollBar()
                scroll_bar.setValue(scroll_bar.value() - delta)
                event.accept()
                return

        super().wheelEvent(event)

    def mousePressEvent(self, event):
        if self.boundaries_edit_active and event.button() == Qt.MouseButton.RightButton:
            point = self.mapToScene(event.position().toPoint())
            point = self.clamp_boundaries_point(point)
            self.boundaries_drawing_active = True
            self.boundaries_last_point = point
            self.apply_boundaries_brush(point.x(), point.y())
            event.accept()
            return

        if self.scale_calibration_active:
            if event.button() == Qt.MouseButton.LeftButton:
                point = self.mapToScene(event.position().toPoint())
                self.pick_scale_calibration_point(point.x(), point.y())
            event.accept()
            return

        if self.pending_ap_position_group_id:
            if event.button() == Qt.MouseButton.LeftButton:
                point = self.mapToScene(event.position().toPoint())
                group_id = self.pending_ap_position_group_id
                self.pending_ap_position_group_id = ""
                self.pending_ap_position_label = ""
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
                self.viewport().unsetCursor()
                self.apPositionPicked.emit(group_id, int(round(point.x())), int(round(point.y())))
            event.accept()
            return

        if self.has_floorplan() and event.button() == Qt.MouseButton.RightButton:
            point = self.mapToScene(event.position().toPoint())
            self.surveyPointRequested.emit(int(round(point.x())), int(round(point.y())))
            event.accept()
            return

        if self.has_floorplan() and event.button() == Qt.MouseButton.LeftButton:
            scene_point = self.mapToScene(event.position().toPoint())
            for item in self.scene.items(scene_point):
                point_data = item.data(0)
                if isinstance(point_data, dict):
                    self.select_point(point_data)
                    self.pointSelected.emit(point_data)
                    event.accept()
                    return
            self.pointSelectionCleared.emit()
            self.clear_selected_point()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            self.boundaries_edit_active
            and self.boundaries_drawing_active
            and event.buttons() & Qt.MouseButton.RightButton
            and self.boundaries_last_point is not None
        ):
            point = self.clamp_boundaries_point(
                self.mapToScene(event.position().toPoint())
            )
            self.apply_boundaries_stroke(self.boundaries_last_point, point)
            self.boundaries_last_point = point
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.boundaries_edit_active and event.button() == Qt.MouseButton.RightButton:
            self.boundaries_drawing_active = False
            self.boundaries_last_point = None
            event.accept()
            return

        super().mouseReleaseEvent(event)
        if not self.pending_ap_position_group_id and not self.scale_calibration_active:
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self.cancel_scale_calibration_pick():
            event.accept()
            return

        if event.key() == Qt.Key.Key_Escape and self.cancel_ap_position_pick():
            event.accept()
            return

        super().keyPressEvent(event)

    def focus_on(self, x, y):
        if not self.has_floorplan():
            return

        self.centerOn(float(x), float(y))


def load_floorplan_pixmap(file_path):
    if file_path.lower().endswith(".pdf"):
        import fitz

        document = fitz.open(file_path)
        try:
            page = document[0]
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = QImage(
                pixmap.samples,
                pixmap.width,
                pixmap.height,
                pixmap.stride,
                QImage.Format.Format_RGB888,
            ).copy()
        finally:
            document.close()
        return QPixmap.fromImage(image)

    return QPixmap(file_path)


def load_ap_position_icon():
    icon_path = Path(__file__).resolve().parent.parent / "images" / "wifi.png"
    if not icon_path.exists():
        return QPixmap()

    return QPixmap(str(icon_path))


def choose_grid_interval_meters(px_per_meter, measurement_system, min_spacing_px=MIN_GRID_SPACING_PX):
    px_per_meter = float(px_per_meter)
    if px_per_meter <= 0:
        return 1.0

    if normalize_measurement_system(measurement_system) == MEASUREMENT_SYSTEM_IMPERIAL:
        for interval_ft in IMPERIAL_GRID_INTERVALS_FT:
            interval_m = display_units_to_meters(interval_ft, MEASUREMENT_SYSTEM_IMPERIAL)
            if interval_m * px_per_meter >= min_spacing_px:
                return interval_m
        return display_units_to_meters(IMPERIAL_GRID_INTERVALS_FT[-1], MEASUREMENT_SYSTEM_IMPERIAL)

    for interval_m in METRIC_GRID_INTERVALS_M:
        if interval_m * px_per_meter >= min_spacing_px:
            return interval_m
    return METRIC_GRID_INTERVALS_M[-1]


def format_grid_interval(px_per_meter, measurement_system):
    measurement_system = normalize_measurement_system(measurement_system)
    interval_m = choose_grid_interval_meters(px_per_meter, measurement_system)
    value = meters_to_display_units(interval_m, measurement_system)
    if abs(value - round(value)) < 0.01:
        value_text = str(int(round(value)))
    else:
        value_text = f"{value:.1f}".rstrip("0").rstrip(".")
    return f"{value_text} {distance_unit_label(measurement_system)}"


def scaled_grid_value(value, ui_scale):
    return max(1, int(round(float(value) * float(ui_scale or 1.0))))


def point_color(signal_dbm):
    if signal_dbm >= -60:
        return QColor("#4E8F5A")
    if signal_dbm >= -70:
        return QColor("#D6B84A")
    if signal_dbm >= -80:
        return QColor("#D49A32")
    return QColor("#C65A5A")


def format_point_tooltip(point):
    ssids = [str(ssid) for ssid in point.get("ssids", []) if str(ssid)]
    ssid_text = ssids or "-"
    signal_scope = str(point.get("signal_scope", "all"))
    scope_label = "relevant networks" if signal_scope == "relevant" else "all networks"
    row_count = point.get("row_count", "-")
    relevant_count = point.get("relevant_row_count", 0)
    rows_label = "Relevant rows" if relevant_count else "Rows"
    rows_value = f"{relevant_count}/{row_count}" if relevant_count else row_count
    signal_value = point.get("best_signal_dbm", "-")
    try:
        accent = point_color(float(signal_value)).name()
    except (TypeError, ValueError):
        accent = "#111111"

    return build_html_tooltip(
        "Survey point",
        [
            ("x/y", f"{point.get('x', '-')}, {point.get('y', '-')}"),
            ("Best signal", f"{signal_value} dBm ({scope_label})"),
            (rows_label, rows_value),
            ("Time", point.get("timestamp", "-")),
            ("Detected SSID", ssid_text),
        ],
        accent,
    )


def format_ap_tooltip(group, label, x, y):
    bssids = ", ".join(group.get("bssids", [])) or "-"
    return build_html_tooltip(
        "AP position",
        [
            ("AP group", group.get("group_id", "-")),
            ("Label", label),
            ("x/y", f"{x}, {y}"),
            ("BSSID", bssids),
        ],
        "#0d6efd",
    )
