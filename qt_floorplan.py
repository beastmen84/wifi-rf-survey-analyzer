"""Qt graphics view used for floor plans, survey points, and AP markers."""

from pathlib import Path
import math

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
)


class FloorplanView(QGraphicsView):
    surveyPointRequested = Signal(int, int)
    apPositionPicked = Signal(str, int, int)
    apPositionCancelled = Signal()
    scaleCalibrationFirstPointPicked = Signal()
    scaleCalibrationCompleted = Signal(float)
    scaleCalibrationCancelled = Signal()
    pointSelected = Signal(dict)
    pointSelectionCleared = Signal()

    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = None
        self.marker_items = []
        self.ap_marker_items = []
        self.scale_calibration_items = []
        self.scale_calibration_points = []
        self.selected_point_key = None
        self.zoom_level = 1.0
        self.pending_ap_position_group_id = ""
        self.pending_ap_position_label = ""
        self.scale_calibration_active = False
        self.ap_position_icon = load_ap_position_icon()
        self.ap_tooltip_formatter = None

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

        self.scene.clear()
        self.marker_items = []
        self.ap_marker_items = []
        self.scale_calibration_items = []
        self.scale_calibration_points = []
        self.selected_point_key = None
        self.scale_calibration_active = False
        self.pending_ap_position_group_id = ""
        self.pending_ap_position_label = ""
        self.viewport().unsetCursor()
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)
        self.scene.setSceneRect(pixmap.rect())
        self.resetTransform()
        self.zoom_level = 1.0
        self.fit_to_view()

    def clear_floorplan(self):
        self.scene.clear()
        self.pixmap_item = None
        self.marker_items = []
        self.ap_marker_items = []
        self.scale_calibration_items = []
        self.scale_calibration_points = []
        self.selected_point_key = None
        self.zoom_level = 1.0
        self.cancel_ap_position_pick(emit_signal=False)
        self.cancel_scale_calibration_pick(emit_signal=False)

    def has_floorplan(self):
        return self.pixmap_item is not None

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
            pixmap = self.ap_position_icon.scaled(
                26,
                26,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            item = QGraphicsPixmapItem(pixmap)
            item.setOffset(-pixmap.width() / 2, -pixmap.height() / 2)
            item.setPos(x, y)
        else:
            item = QGraphicsEllipseItem(-7, -7, 14, 14)
            item.setBrush(QBrush(QColor("#0d6efd")))
            item.setPen(QPen(Qt.GlobalColor.white, 1.6))
            item.setPos(x, y)

        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
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
        self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        return True

    def cancel_ap_position_pick(self, emit_signal=True):
        if not self.pending_ap_position_group_id:
            return False

        self.pending_ap_position_group_id = ""
        self.pending_ap_position_label = ""
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

        super().wheelEvent(event)

    def mousePressEvent(self, event):
        if self.scale_calibration_active:
            if event.button() == Qt.MouseButton.LeftButton:
                point = self.mapToScene(event.position().toPoint())
                self.pick_scale_calibration_point(point.x(), point.y())
            event.accept()
            return

        if self.pending_ap_position_group_id:
            if event.button() == Qt.MouseButton.RightButton:
                point = self.mapToScene(event.position().toPoint())
                group_id = self.pending_ap_position_group_id
                self.pending_ap_position_group_id = ""
                self.pending_ap_position_label = ""
                self.viewport().unsetCursor()
                self.apPositionPicked.emit(group_id, int(round(point.x())), int(round(point.y())))
            else:
                self.viewport().setCursor(Qt.CursorShape.CrossCursor)
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

    def mouseReleaseEvent(self, event):
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
    icon_path = Path(__file__).with_name("images") / "wifi.png"
    if not icon_path.exists():
        return QPixmap()

    return QPixmap(str(icon_path))


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
    ssid_text = "\n".join(f"  - {ssid}" for ssid in ssids) if ssids else "  -"
    signal_scope = str(point.get("signal_scope", "all"))
    scope_label = "relevant networks" if signal_scope == "relevant" else "all networks"
    row_count = point.get("row_count", "-")
    relevant_count = point.get("relevant_row_count", 0)
    relevant_line = f"Relevant rows: {relevant_count}/{row_count}" if relevant_count else f"Rows: {row_count}"

    return (
        "Survey point\n"
        "-------------\n"
        f"Position: x={point.get('x', '-')}, y={point.get('y', '-')}\n"
        f"Best signal: {point.get('best_signal_dbm', '-')} dBm ({scope_label})\n"
        f"{relevant_line}\n"
        f"Time: {point.get('timestamp', '-')}\n"
        "\n"
        "Detected SSID:\n"
        f"{ssid_text}"
    )


def format_ap_tooltip(group, label, x, y):
    bssids = ", ".join(group.get("bssids", [])) or "-"
    return (
        f"{label}\n"
        f"Gruppo: {group.get('group_id', '-')}\n"
        f"x/y: {x}, {y}\n"
        f"BSSID: {bssids}"
    )
