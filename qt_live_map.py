from io import BytesIO

import pandas as pd
from PIL import Image
from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
)

from constants import SURVEY_FIELDNAMES
from live_renderer import render_live_continuous_map


class LiveMapRenderWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, rows, map_file, config, translations):
        super().__init__()
        self.rows = list(rows or [])
        self.map_file = map_file
        self.config = config
        self.translations = translations

    @Slot()
    def run(self):
        try:
            bg_image = load_floorplan_image(self.map_file)
            df = pd.DataFrame(self.rows, columns=SURVEY_FIELDNAMES)
            payload = render_live_continuous_map(
                df,
                self.config,
                bg_image,
                self.translations,
                lambda map_type, row, raw_rows: build_live_tooltip(
                    map_type,
                    row,
                    raw_rows,
                    self.translations,
                ),
                get_color_scale_limits,
            )
        except Exception as exc:
            self.failed.emit(str(exc))
            return

        self.finished.emit(payload)


class LiveMapView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = None
        self.marker_items = []
        self.zoom_level = 1.0

        self.setObjectName("liveMapView")
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setBackgroundBrush(QBrush(Qt.GlobalColor.darkGray))

    def clear(self):
        self.scene.clear()
        self.pixmap_item = None
        self.marker_items = []
        self.zoom_level = 1.0

    def set_payload(self, payload):
        self.clear()
        if not payload:
            return

        pixmap = pil_to_qpixmap(payload["image"])
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)
        self.scene.setSceneRect(pixmap.rect())
        self.add_markers(payload.get("point_infos", []))
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

            item = QGraphicsEllipseItem(-4, -4, 8, 8)
            item.setPos(x, y)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
            item.setBrush(QBrush(QColor(str(info.get("color") or "#111111"))))
            item.setPen(QPen(QColor(str(info.get("outline") or "#ffffff")), 1.2))
            item.setZValue(20)
            tooltip = info.get("tooltip")
            if tooltip:
                item.setToolTip(str(tooltip))
            self.scene.addItem(item)
            self.marker_items.append(item)

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

    def fit_to_view(self):
        if self.pixmap_item is None:
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


def get_color_scale_limits(grid_z, config):
    if getattr(config, "color_scale", "fixed") == "auto":
        finite_values = grid_z[pd.notna(grid_z)]
        if len(finite_values):
            return float(finite_values.min()), float(finite_values.max())

    return -90, -40


def build_live_tooltip(map_type, row, raw_rows, translations):
    if map_type == "interference":
        return "\n".join([
            translations.get("interference_title", "AP interference"),
            f"x/y: {format_value(row.get('x'))}, {format_value(row.get('y'))}",
            f"{translations.get('risk', 'Risk')}: {format_value(row.get('risk'))}%",
            f"{translations.get('serving_ap', 'Serving AP')}: {row.get('serving_ap_group', '-')}",
            f"{translations.get('serving_channel', 'Serving channel')}: {format_value(row.get('serving_channel'))}",
            f"{translations.get('interferer', 'Interferer')}: {row.get('strongest_interferer_ap_group', '-')}",
            f"{translations.get('interferer_channel', 'Interferer channel')}: {format_value(row.get('strongest_interferer_channel'))}",
        ])

    return "\n".join([
        translations.get("signal_title", "Signal coverage"),
        f"x/y: {format_value(row.get('x'))}, {format_value(row.get('y'))}",
        f"dBm: {format_value(row.get('signal_dbm'))}",
        f"{translations.get('source_rows', 'Source rows')}: {raw_rows if raw_rows is not None else '-'}",
    ])


def format_value(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value if value not in (None, "") else "-")

    if number.is_integer():
        return str(int(number))
    return f"{number:.1f}"
