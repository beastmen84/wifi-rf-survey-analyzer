"""Transient split-segment dimensions; no model, topology or export changes."""
import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsPathItem, QLabel

from app_core.units import distance_unit_label, meters_to_display_units
from qt_ui.scaling import widget_px
from survey.plan_annotations import annotation_points
from survey.plan_objects import HOSTED_ANNOTATIONS
from survey.plan_erasing import nearest_segment
from survey.planar_geometry import point_projection


class SegmentDimensions:
    def __init__(self, drawing):
        self.drawing, self.view, self.owner = drawing, drawing.view, drawing.owner
        self.items, self.values = [], None
        self.badge = QLabel(self.view.viewport())
        self.badge.setProperty("fixedViewportOverlay", True)
        self.badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.badge.setStyleSheet("background:#182433;color:white;border:1px solid #8194aa;border-radius:4px;padding:6px 9px;")
        self.badge.hide()

    def reset_scene(self):
        self.items = []  # scene.clear() already deleted these native objects.
        self.hide()

    def hide(self):
        self.values = None
        self.badge.hide()
        for item in self.items:
            item.hide()

    def position(self):
        margin = widget_px(self.owner, 12)
        self.badge.adjustSize()
        top = margin
        if self.drawing.measurement.isVisible():
            top = self.drawing.measurement.geometry().bottom() + widget_px(self.owner, 8)
        self.badge.move(max(margin, self.view.viewport().width() - margin - self.badge.width()),
                        max(margin, min(top, self.view.viewport().height() - self.badge.height() - margin)))

    def number(self, pixels):
        value = meters_to_display_units(pixels / self.owner.get_px_per_meter(), self.owner.measurement_system)
        return self.badge.locale().toString(value, "f", 2) + " " + distance_unit_label(self.owner.measurement_system)

    def update(self, event):
        d = self.drawing
        if (not d.tools.open or d.rotation.active or event.buttons() & Qt.MouseButton.LeftButton
                or not self.view.viewport().rect().contains(event.position().toPoint())):
            self.hide()
            return
        point = self.view.mapToScene(event.position().toPoint())
        aperture = None
        if d.tools.active_tool in ("door", "window"):
            aperture = d.annotation.pending
        elif d.tools.active_tool == "annotation_select" and d.annotation.moving and len(d.annotation.draft) == 1:
            aperture = d.annotation.draft[0] if d.annotation.draft[0]["kind"] in HOSTED_ANNOTATIONS else None
        # Cursor quotes refer to the actual pointer projection. Jamb snapping
        # may put an opening's center elsewhere; its clearances are separate.
        lines = d.selection.lines  # Current displayed model; do not renormalize on every mouse event.
        zoom = max(1e-9, math.hypot(self.view.transform().m11(), self.view.transform().m12()))
        index = nearest_segment(lines, point.x(), point.y(), widget_px(self.owner, 8) / zoom + 1)
        if index is None:
            self.hide()
            return
        line = lines[index]
        a, b = (line["x1"], line["y1"]), (line["x2"], line["y2"])
        p = point_projection((point.x(), point.y()), a, b)
        length, before = math.dist(a, b), math.dist(a, p)
        self.values = dict(index=index, before=before, after=length - before, projection=p,
                           before_m=before / self.owner.get_px_per_meter(), after_m=(length - before) / self.owner.get_px_per_meter())
        rows = [self.owner.tr("segment_dimensions_title"),
                "<span style='color:#67caff'>A</span> · " + self.owner.tr("segment_before") + ": " + self.number(before),
                "<span style='color:#d8b4fe'>B</span> · " + self.owner.tr("segment_after") + ": " + self.number(length - before)]
        if aperture:
            ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
            if all(math.dist(q, point_projection(q, a, b)) <= 1e-5 for q in annotation_points(aperture)):
                low, high = sorted((q[0] - a[0]) * ux + (q[1] - a[1]) * uy for q in annotation_points(aperture))
                self.values.update(clearance_before=low, clearance_after=length - high)
                rows.extend((self.owner.tr("segment_opening_before") + ": " + self.number(low),
                             self.owner.tr("segment_opening_after") + ": " + self.number(length - high)))
        self.badge.setText("<br>".join(rows))
        self.position()
        self.badge.show()
        self.badge.raise_()
        for item in self.items:
            self.view.scene.removeItem(item)
        self.items = []
        normal = (-(b[1] - a[1]) / length, (b[0] - a[0]) / length)
        offset, tick = widget_px(self.owner, 12) / zoom, widget_px(self.owner, 4) / zoom
        for start, end, color in ((a, p, "#0284c7"), (p, b, "#a855f7")):
            path = QPainterPath()
            path.moveTo(start[0] + normal[0] * offset, start[1] + normal[1] * offset)
            path.lineTo(end[0] + normal[0] * offset, end[1] + normal[1] * offset)
            for x, y in (start, end):
                path.moveTo(x + normal[0] * (offset - tick), y + normal[1] * (offset - tick))
                path.lineTo(x + normal[0] * (offset + tick), y + normal[1] * (offset + tick))
            item = QGraphicsPathItem(path)
            pen = QPen(QColor(color), 1.5)
            pen.setCosmetic(True)
            item.setPen(pen)
            item.setZValue(10)
            item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.view.scene.addItem(item)
            self.items.append(item)
