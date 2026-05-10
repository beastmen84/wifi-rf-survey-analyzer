from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView


class FloorplanView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = None
        self.marker_items = []
        self.zoom_level = 1.0

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
        self.zoom_level = 1.0

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

            item = QGraphicsEllipseItem(x - 5, y - 5, 10, 10)
            item.setBrush(QBrush(point_color(signal)))
            item.setPen(QPen(Qt.GlobalColor.white, 1.5))
            item.setZValue(10)
            item.setToolTip(format_point_tooltip(point))
            self.scene.addItem(item)
            self.marker_items.append(item)

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


def point_color(signal_dbm):
    if signal_dbm >= -60:
        return Qt.GlobalColor.green
    if signal_dbm >= -70:
        return Qt.GlobalColor.yellow
    if signal_dbm >= -80:
        return Qt.GlobalColor.darkYellow
    return Qt.GlobalColor.red


def format_point_tooltip(point):
    ssids = ", ".join(point.get("ssids", [])) or "-"
    return (
        f"x={point.get('x', '-')}, y={point.get('y', '-')}\n"
        f"dBm: {point.get('best_signal_dbm', '-')}\n"
        f"SSID: {ssids}\n"
        f"{point.get('timestamp', '')}"
    )
