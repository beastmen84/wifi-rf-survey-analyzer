"""Measured text placement/editing; glyph geometry remains portable across exports."""
from copy import deepcopy

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainterPath
from PySide6.QtWidgets import QDialog

from qt_ui.qt_text_editor import PlanTextDialog
from survey.plan_geometry import segment_bounds
from survey.plan_labels import label_geometry, transform_labels
from survey.plan_label_rendering import build_label, label_item


class TextDesignController:
    def __init__(self, drawing):
        self.drawing, self.owner, self.view = drawing, drawing.owner, drawing.view
        self.labels, self.items, self.preview_items = [], [], []
        self.pending = self.preview = None
        self.last_pointer = None
        self.offset = QPointF()
        self.clicked = self.consume_release = self.dialog_open = False
        self.last_style = None

    def reset_scene(self):
        self.items, self.preview_items = [], []
        self.preview = None
        self.cancel()

    def clear_preview(self):
        for item in self.preview_items:
            self.view.scene.removeItem(item)
        self.preview_items, self.preview = [], None

    def cancel(self):
        active = self.pending is not None or self.clicked
        self.clear_preview()
        self.pending, self.last_pointer = None, None
        self.offset = QPointF()
        self.clicked = self.consume_release = False
        for item in self.items:
            item.setOpacity(1)
        return active

    def redraw(self, labels):
        for item in self.items:
            self.view.scene.removeItem(item)
        self.labels = deepcopy(labels)
        self.items = [label_item(label) for label in labels]
        for item in self.items:
            self.view.scene.addItem(item)

    def show_labels(self, labels):
        self.clear_preview()
        self.preview_items = [label_item(label) for label in labels]
        for item in self.preview_items:
            item.setOpacity(.85)
            item.setZValue(9)
            self.view.scene.addItem(item)
        self.preview = self.preview_items[0] if self.preview_items else None

    def hide_preview(self):
        for item in self.preview_items:
            item.hide()

    def clamp(self, label):
        left, top, right, bottom = segment_bounds(label_geometry(label))
        bounds = self.view.scene.sceneRect()
        if right - left > bounds.width() + 1e-7 or bottom - top > bounds.height() + 1e-7:
            raise ValueError("Text does not fit on the sheet")
        dx = max(bounds.left() - left, min(0, bounds.right() - right))
        dy = max(bounds.top() - top, min(0, bounds.bottom() - bottom))
        return transform_labels([label], dx=dx, dy=dy)[0]

    def read_editor(self, previous=None):
        session, pixmap = self.owner.session, self.view.pixmap_item
        self.dialog_open = True
        try:
            dialog = PlanTextDialog(self.owner, previous or self.last_style)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return None
            if session is not self.owner.session or pixmap is not self.view.pixmap_item:
                return None
            label = build_label(dialog.values(), previous.get("id") if previous else None)
            self.last_style = label
            return label
        except (ValueError, KeyError, TypeError):
            self.owner.status.showMessage(self.owner.tr("plan_text_invalid"))
            return None
        finally:
            self.dialog_open = False

    def begin_placement(self, label, position):
        self.pending = deepcopy(label)
        self.offset = QPointF()
        self.last_pointer = QPointF(position)
        return self.update_pending(position)

    def update_pending(self, position, bypass=False):
        if self.pending is None:
            return False
        position = QPointF(position)
        self.last_pointer = QPointF(position)
        point = self.view.mapToScene(position.toPoint()) + self.offset
        label = dict(self.pending, x=point.x(), y=point.y())
        try:
            label = self.clamp(label)
        except ValueError:
            self.owner.status.showMessage(self.owner.tr("plan_text_outside"))
            self.hide_preview()
            return False
        geometry = label_geometry(label)
        snapped = self.drawing.snap_shape(geometry, bypass)
        if snapped:
            label = transform_labels([label], dx=snapped[0]["x1"] - geometry[0]["x1"],
                                      dy=snapped[0]["y1"] - geometry[0]["y1"])[0]
        self.pending = label
        self.show_labels([label])
        left, top, right, bottom = segment_bounds(label_geometry(label))
        self.drawing.show_snap_guides(QRectF(left, top, right - left, bottom - top))
        self.drawing.show_measurement(self.owner.tr("plan_text_place_hint"), position)
        return True

    def refresh_snap(self):
        if self.pending is not None and self.last_pointer is not None:
            self.update_pending(self.last_pointer)

    def rotate(self):
        if self.pending is None:
            return False
        rotated = transform_labels([self.pending], 90, (self.pending["x"], self.pending["y"]))[0]
        if not self.drawing.selection.fits(label_geometry(rotated)):
            self.owner.status.showMessage(self.owner.tr("plan_text_outside"))
            return True
        self.pending = rotated
        self.show_labels([rotated])
        return True

    def press(self, event):
        if not self.view.scene.sceneRect().contains(self.view.mapToScene(event.position().toPoint())):
            return True
        if self.pending is not None:
            if self.update_pending(event.position(), bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)):
                if self.drawing.apply_edit(self.drawing.segments() or [], self.drawing.labels() + [self.pending]):
                    self.cancel()
            self.consume_release = True
        else:
            self.clicked = True
        return True

    def move(self, event):
        if self.pending is not None:
            if self.view.scene.sceneRect().contains(self.view.mapToScene(event.position().toPoint())):
                self.update_pending(event.position(), bool(event.modifiers() & Qt.KeyboardModifier.AltModifier))
            else:
                self.hide_preview()
        return False

    def release(self, event):
        if self.consume_release:
            self.consume_release = False
            return True
        if self.clicked:
            self.clicked = False
            label = self.read_editor()
            if label is not None:
                self.begin_placement(label, event.position())
        return True

    def edit(self, index):
        if not 0 <= index < len(self.labels):
            return False
        original = deepcopy(self.labels[index])
        label = self.read_editor(original)
        if label is None:
            return True
        try:
            label = self.clamp(dict(label, x=original["x"], y=original["y"], angle=original["angle"]))
        except ValueError:
            self.owner.status.showMessage(self.owner.tr("plan_text_outside"))
            return True
        labels = self.drawing.labels()
        if index >= len(labels) or labels[index]["id"] != original["id"]:
            return True
        labels[index] = label
        self.drawing.apply_edit(self.drawing.segments() or [], labels)
        self.drawing.selection.set_selected((), (index,))
        return True

    def hit(self, point):
        for index in reversed(range(len(self.labels))):
            if self.bounds_path(self.labels[index]).contains(point):
                return index
        return None

    @staticmethod
    def bounds_path(label):
        path = QPainterPath()
        lines = label_geometry(label)
        path.moveTo(lines[0]["x1"], lines[0]["y1"])
        for line in lines:
            path.lineTo(line["x2"], line["y2"])
        path.closeSubpath()
        return path

    def intersecting(self, rect):
        return tuple(index for index, label in enumerate(self.labels)
                     if self.bounds_path(label).intersects(rect))
