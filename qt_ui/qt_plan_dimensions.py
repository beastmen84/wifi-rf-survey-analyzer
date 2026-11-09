"""Transient split-segment dimensions; no model, topology or export changes."""
import math
from html import escape

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen, QTransform
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsTextItem, QLabel, QWidget

from app_core.units import distance_unit_label, meters_to_display_units
from qt_ui.scaling import widget_px
from survey.plan_annotations import annotation_points, aperture_host_span
from survey.plan_objects import HOSTED_ANNOTATIONS, FREE_ANNOTATIONS, object_vertices
from survey.plan_erasing import nearest_segment
from survey.planar_geometry import point_projection


class SegmentDimensions:
    def __init__(self, drawing):
        self.drawing, self.view, self.owner = drawing, drawing.view, drawing.owner
        self.items, self.values = [], None
        self.text_items = []
        self.last_object = None
        self.badge = QLabel(self.view.viewport())
        self.badge.setProperty("fixedViewportOverlay", True)
        self.badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.badge.setStyleSheet("background:#182433;color:white;border:1px solid #8194aa;border-radius:4px;padding:6px 9px;")
        self.badge.hide()
        self.view.zoomChanged.connect(self.refresh)

    def reset_scene(self):
        self.items = []  # scene.clear() already deleted these native objects.
        self.text_items = []
        self.hide()

    def hide(self):
        self.values = None
        self.last_object = None
        self.badge.hide()
        for item in self.items + self.text_items:
            item.hide()

    def refresh(self, *_args):
        if self.last_object is not None and self.badge.isVisible():
            self.update_object(self.last_object)

    def path_item(self, index, path, color, dashed=False):
        while len(self.items) <= index:
            item = QGraphicsPathItem()
            item.setZValue(10)
            item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.view.scene.addItem(item)
            self.items.append(item)
        item = self.items[index]
        pen = QPen(QColor(color), 1.5, Qt.PenStyle.DashLine if dashed else Qt.PenStyle.SolidLine)
        pen.setCosmetic(True)
        item.setPen(pen)
        item.setPath(path)
        item.show()

    def update_object(self, item):
        quotes = self.drawing.clearance_index.query(item)
        if not quotes:
            self.hide()
            return
        self.last_object = item
        self.values = dict(kind="object", quotes=quotes)
        rows = [self.owner.tr("object_clearances")]
        zoom = max(1e-9, math.hypot(self.view.transform().m11(), self.view.transform().m12()))
        tick = widget_px(self.owner, 4) / zoom
        transform = self.view.viewportTransform()
        inverse, _valid = transform.inverted()
        points = [transform.map(QPointF(*point)) for point in object_vertices(item)]
        object_box = QRectF(QPointF(min(p.x() for p in points), min(p.y() for p in points)),
                            QPointF(max(p.x() for p in points), max(p.y() for p in points)))
        occupied = [child.geometry() for child in self.view.viewport().children()
                    if isinstance(child, QWidget) and child.isVisible() and child.property("fixedViewportOverlay")]
        for text in self.text_items:
            text.hide()
        for index, quote in enumerate(quotes):
            color = "#ef4444" if quote.overlap else ("#0284c7", "#a855f7")[index]
            caption = self.owner.tr("object_intersects" if quote.overlap else "object_gap_" + quote.direction)
            value = self.number(quote.distance)
            accent = "#fca5a5" if quote.overlap else ("#67caff", "#d8b4fe")[index]
            rows.append("<span style='color:" + accent + "'>" + escape(caption) + "</span> · " + escape(value))
            a, b = quote.start, quote.end
            path = QPainterPath()
            path.moveTo(*a)
            path.lineTo(*b)
            if quote.distance > 1e-7:
                nx, ny = -(b[1] - a[1]) / quote.distance, (b[0] - a[0]) / quote.distance
                for x, y in (a, b):
                    path.moveTo(x - tick * nx, y - tick * ny)
                    path.lineTo(x + tick * nx, y + tick * ny)
            else:
                path.moveTo(a[0] - tick, a[1] - tick)
                path.lineTo(a[0] + tick, a[1] + tick)
                path.moveTo(a[0] - tick, a[1] + tick)
                path.lineTo(a[0] + tick, a[1] - tick)
            while len(self.text_items) <= index:
                text = QGraphicsTextItem()
                text.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
                text.setFont(self.owner.font())
                text.setZValue(11)
                text.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                self.view.scene.addItem(text)
                self.text_items.append(text)
            text = self.text_items[index]
            ink = "#b91c1c" if quote.overlap else ("#0369a1", "#7e22ce")[index]
            if text.data(0) != (value, ink):
                text.setHtml("<span style='background:white;color:" + ink + ";font-weight:600'>" + escape(value) + "</span>")
                text.setData(0, (value, ink))
            bounds = text.boundingRect()
            projection = ((abs(b[0] - a[0]) * bounds.width() + abs(b[1] - a[1]) * bounds.height()) / quote.distance
                          if quote.distance > 1e-7 else math.inf)
            middle = QPointF((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            screen_middle = transform.map(middle)
            rect = QRectF(screen_middle.x() - bounds.width() / 2, screen_middle.y() - bounds.height() / 2,
                          bounds.width(), bounds.height())
            if (quote.distance * zoom <= projection + widget_px(self.owner, 6)
                    or not self.view.viewport().rect().contains(rect.toAlignedRect())
                    or any(rect.intersects(QRectF(other)) for other in occupied)):
                rect = self.callout_rect(bounds, screen_middle, object_box, occupied)
                # End the leader at the nearest label edge, in scene coordinates.
                end = QPointF(min(max(screen_middle.x(), rect.left()), rect.right()),
                              min(max(screen_middle.y(), rect.top()), rect.bottom()))
                path.moveTo(middle)
                path.lineTo(inverse.map(end))
            text.setPos(inverse.map(rect.center()))
            text.setTransform(QTransform.fromTranslate(-bounds.width() / 2, -bounds.height() / 2))
            text.show()
            occupied.append(rect)
            self.path_item(index, path, color, True)
        for unused in self.items[len(quotes):]:
            unused.hide()
        self.badge.setText("<br>".join(rows))
        self.position()
        self.badge.show()
        self.badge.raise_()

    def callout_rect(self, bounds, middle, object_box, occupied):
        """Place short-gap numbers outside the object at a readable device size."""
        gap = widget_px(self.owner, 8)
        w, h = bounds.width(), bounds.height()
        viewport = QRectF(self.view.viewport().rect()).adjusted(gap, gap, -gap, -gap)
        candidates = [QRectF(middle.x() - w / 2, object_box.top() - h - gap, w, h),
                      QRectF(middle.x() - w / 2, object_box.bottom() + gap, w, h),
                      QRectF(object_box.left() - w - gap, middle.y() - h / 2, w, h),
                      QRectF(object_box.right() + gap, middle.y() - h / 2, w, h)]
        # A drawing palette can occupy all four immediate positions. Include
        # obstacle edges so labels can escape it and one another without hiding
        # a number under the panel or choosing the same fallback twice.
        xs, ys = [middle.x() - w / 2], [middle.y() - h / 2]
        for obstacle in [object_box, *occupied]:
            obstacle = QRectF(obstacle)
            xs.extend((obstacle.left() - w - gap, obstacle.right() + gap))
            ys.extend((obstacle.top() - h - gap, obstacle.bottom() + gap))
        candidates.extend(QRectF(x, y, w, h) for x in xs for y in ys)
        for rect in candidates:
            rect.moveLeft(max(viewport.left(), min(rect.left(), viewport.right() - w)))
            rect.moveTop(max(viewport.top(), min(rect.top(), viewport.bottom() - h)))
        def score(rect):
            overlaps = [rect.intersected(QRectF(other)) for other in [object_box, *occupied]]
            area = sum(max(0, hit.width()) * max(0, hit.height()) for hit in overlaps)
            return area, math.hypot(rect.center().x() - middle.x(), rect.center().y() - middle.y())
        return min(candidates, key=score)

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
        free = None
        if d.tools.active_tool in FREE_ANNOTATIONS:
            free = d.annotation.pending
        elif d.tools.active_tool == "annotation_select":
            objects = d.annotation.draft if d.annotation.moving else d.annotation.selected_items()
            if len(objects) == 1 and not d.annotation.selected_labels and objects[0]["kind"] in FREE_ANNOTATIONS:
                free = objects[0]
        if free is not None:
            self.update_object(free)
            return
        self.last_object = None
        for text in self.text_items:
            text.hide()
        aperture = None
        if d.tools.active_tool in ("door", "window"):
            aperture = d.annotation.pending
        elif d.tools.active_tool == "annotation_select" and d.annotation.moving and len(d.annotation.draft) == 1:
            aperture = d.annotation.draft[0] if d.annotation.draft[0]["kind"] in HOSTED_ANNOTATIONS else None
        lines = d.selection.lines  # Current displayed model; do not renormalize on every mouse event.
        zoom = max(1e-9, math.hypot(self.view.transform().m11(), self.view.transform().m12()))
        if d.tools.active_tool in HOSTED_ANNOTATIONS and aperture is None:
            self.hide()
            return
        profile = None
        if aperture is not None:
            span = aperture_host_span(aperture, lines)
            if span is None:
                self.hide()
                return
            index, a, b = span
            first, last = map(tuple, annotation_points(aperture))
            before, after = math.dist(a, first), math.dist(last, b)
            p = tuple((first[i]+last[i])/2 for i in (0, 1))
            labels = ('segment_opening_before', 'segment_opening_after')
            runs = ((a, first, '#0284c7'), (last, b, '#a855f7'))
            from survey.wall_geometry import aperture_profile
            profile = aperture_profile(aperture, lines)
        else:
            index = nearest_segment(lines, point.x(), point.y(), widget_px(self.owner, 8) / zoom + 1)
            if index is None:
                self.hide()
                return
            line = lines[index]
            a, b = (line['x1'], line['y1']), (line['x2'], line['y2'])
            p = point_projection((point.x(), point.y()), a, b)
            before, after = math.dist(a, p), math.dist(p, b)
            labels = ('segment_before', 'segment_after')
            runs = ((a, p, '#0284c7'), (p, b, '#a855f7'))
        length = math.dist(a, b)
        self.values = dict(index=index, before=before, after=after, projection=p,
                           before_m=before / self.owner.get_px_per_meter(), after_m=after / self.owner.get_px_per_meter())
        if aperture is not None:
            self.values.update(kind='aperture', clearance_before=before, clearance_after=after)
        rows = [self.owner.tr("segment_dimensions_title"),
                "<span style='color:#67caff'>A</span> · " + self.owner.tr(labels[0]) + ": " + self.number(before),
                "<span style='color:#d8b4fe'>B</span> · " + self.owner.tr(labels[1]) + ": " + self.number(after)]
        self.badge.setText("<br>".join(rows))
        self.position()
        self.badge.show()
        self.badge.raise_()
        normal = (-(b[1] - a[1]) / length, (b[0] - a[0]) / length)
        offset, tick = widget_px(self.owner, 12) / zoom, widget_px(self.owner, 4) / zoom
        if profile is not None:
            offset += profile[1]
        for index, (start, end, color) in enumerate(runs):
            path = QPainterPath()
            path.moveTo(start[0] + normal[0] * offset, start[1] + normal[1] * offset)
            path.lineTo(end[0] + normal[0] * offset, end[1] + normal[1] * offset)
            for x, y in (start, end):
                path.moveTo(x + normal[0] * (offset - tick), y + normal[1] * (offset - tick))
                path.lineTo(x + normal[0] * (offset + tick), y + normal[1] * (offset + tick))
            self.path_item(index, path, color)
