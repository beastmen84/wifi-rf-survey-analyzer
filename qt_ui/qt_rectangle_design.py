"""Right-button rectangle gestures and provisional, dimensioned placement."""
import math

from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPen, QPixmap
from PySide6.QtWidgets import (QApplication, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QGraphicsLineItem, QGraphicsRectItem, QLabel, QVBoxLayout)

from app_core.units import distance_unit_label, display_units_to_meters, meters_to_display_units
from survey.plan_drawing import PLAN_DRAWING_KEY, drawing_segments, encode_drawing, rectangle_segments
from qt_ui.scaling import widget_px


class RectangleSizeDialog(QDialog):
    def __init__(self, owner, bounds, density, previous=None):
        super().__init__(owner)
        self.owner, self.density = owner, density
        self.setWindowTitle(owner.tr("rectangle_size_title"))
        self.setMinimumWidth(widget_px(owner, 430))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*(widget_px(owner, 20) for _ in range(4)))
        layout.setSpacing(widget_px(owner, 12))
        hint = QLabel(owner.tr("rectangle_size_hint"))
        hint.setWordWrap(True)
        hint.setMinimumHeight(hint.fontMetrics().lineSpacing() * 3)
        layout.addWidget(hint)
        form = QFormLayout()
        self.width_spin, self.height_spin = QDoubleSpinBox(), QDoubleSpinBox()
        for index, (spin, extent, key) in enumerate(((self.width_spin, bounds.width(), "blank_plan_width"),
                                                   (self.height_spin, bounds.height(), "blank_plan_height"))):
            spin.setObjectName("blankPlanDimension")
            spin.setDecimals(2)
            spin.setRange(.01, math.floor(meters_to_display_units(extent / density, owner.measurement_system) * 100) / 100)
            spin.setSuffix(" " + distance_unit_label(owner.measurement_system))
            spin.setMinimumHeight(widget_px(owner, 36))
            spin.setKeyboardTracking(False)
            spin.setValue(meters_to_display_units(previous[index] / density, owner.measurement_system)
                          if previous else min((5, 3)[index], spin.maximum()))
            form.addRow(owner.tr(key), spin)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(owner.tr("cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def dimensions(self):
        return tuple(display_units_to_meters(spin.value(), self.owner.measurement_system) * self.density
                     for spin in (self.width_spin, self.height_spin))


class RectangleDesignController(QObject):
    def __init__(self, tools):
        super().__init__(tools)
        self.tools, self.owner = tools, tools.owner
        self.view = self.owner.floorplan_view
        self.view.rectangle_design = self
        self.session = self.pixmap = None
        self.document = None
        self.items = []
        self.undo_stack, self.redo_stack = [], []
        self.preview = None
        self.origin = self.press_position = self.pending_size = self.last_size = None
        self.dragged = self.consume_release = False
        self.measurement = QLabel(self.view.viewport())
        self.measurement.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.measurement.setStyleSheet("background:#182433;color:white;border:1px solid #8194aa;border-radius:4px;padding:6px 9px;")
        self.measurement.hide()
        self.owner.installEventFilter(self)

    def eventFilter(self, source, event):
        if source is self.owner and event.type() == QEvent.Type.WindowDeactivate:
            self.cancel()
        return super().eventFilter(source, event)

    def sync(self):
        session = self.owner.session
        changed_scene = session is not self.session or self.view.pixmap_item is not self.pixmap
        if changed_scene:
            if self.view.pixmap_item is not self.pixmap:
                # scene.clear() has already destroyed these C++ graphics items.
                self.preview = None
                self.items = []
            self.cancel()
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.last_size = None
            self.session, self.pixmap = session, self.view.pixmap_item
            self.document = None
        document = session.metadata.get(PLAN_DRAWING_KEY) if session else None
        if changed_scene or document != self.document:
            self.redraw()
            self.document = document
        self.tools.undo_button.setEnabled(self.tools.open and bool(self.undo_stack))
        self.tools.redo_button.setEnabled(self.tools.open and bool(self.redo_stack))

    def segments(self):
        return drawing_segments(self.owner.session.metadata) if self.owner.session else None

    def redraw(self):
        for item in self.items:
            self.view.scene.removeItem(item)
        self.items = []
        lines = self.segments()
        bounds = self.view.scene.sceneRect()
        if any(line[key] > extent + 1e-7 for line in lines or []
               for keys, extent in ((('x1', 'x2'), bounds.width()), (('y1', 'y2'), bounds.height())) for key in keys):
            raise ValueError("Saved drawing is outside the sheet")
        if lines is not None and self.view.pixmap_item is not None:
            white = QPixmap(self.view.pixmap_item.pixmap().size())
            white.fill(Qt.GlobalColor.white)
            self.view.pixmap_item.setPixmap(white)
        for line in lines or []:
            item = QGraphicsLineItem(line["x1"], line["y1"], line["x2"], line["y2"])
            item.setPen(QPen(QColor(line["color"]), 2))
            item.setZValue(5)
            item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.view.scene.addItem(item)
            self.items.append(item)

    def cancel(self):
        existed = self.origin is not None or self.pending_size is not None
        if self.preview is not None:
            self.view.scene.removeItem(self.preview)
            self.preview = None
        self.origin = self.press_position = self.pending_size = None
        self.dragged = self.consume_release = False
        self.measurement.hide()
        return existed

    def hide_preview(self):
        if self.preview is not None:
            self.preview.hide()
        self.measurement.hide()

    def pointer_rect(self, point):
        bounds = self.view.scene.sceneRect()
        if self.pending_size:
            width, height = self.pending_size
            return QRectF(min(max(point.x(), 0), bounds.right() - width),
                          min(max(point.y(), 0), bounds.bottom() - height), width, height)
        point = QPointF(min(max(point.x(), 0), bounds.right()), min(max(point.y(), 0), bounds.bottom()))
        return QRectF(self.origin, point).normalized()

    def show_preview(self, rect, position):
        if self.preview is None:
            self.preview = QGraphicsRectItem()
            self.preview.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.preview.setZValue(8)
            self.view.scene.addItem(self.preview)
        self.preview.setRect(rect)
        pen = QPen(self.tools.stroke_color, 2, Qt.PenStyle.DashLine)
        self.preview.setPen(pen)
        self.preview.show()
        density = self.owner.get_px_per_meter()
        values = [meters_to_display_units(value / density, self.owner.measurement_system)
                  for value in (rect.width(), rect.height())]
        numbers = [self.measurement.locale().toString(value, "f", 2) for value in values]
        self.measurement.setText(f"{numbers[0]} × {numbers[1]} {distance_unit_label(self.owner.measurement_system)}")
        self.measurement.adjustSize()
        viewport = self.view.viewport()
        self.measurement.move(max(4, min(int(position.x()) + 16, viewport.width() - self.measurement.width() - 4)),
                              max(4, min(int(position.y()) + 18, viewport.height() - self.measurement.height() - 4)))
        self.measurement.show()
        self.measurement.raise_()

    def press(self, event):
        if event.button() != Qt.MouseButton.RightButton:
            return False
        point = self.view.mapToScene(event.position().toPoint())
        if self.pending_size:
            if self.view.scene.sceneRect().contains(point):
                rect = self.pointer_rect(point)
                self.commit(rect)
                self.cancel()
            self.consume_release = True
        elif self.view.scene.sceneRect().contains(point):
            self.origin, self.press_position = point, event.position()
            self.dragged = False
        return True

    def move(self, event):
        point = self.view.mapToScene(event.position().toPoint())
        if self.pending_size:
            if self.view.scene.sceneRect().contains(point):
                self.show_preview(self.pointer_rect(point), event.position())
            else:
                self.hide_preview()
        if self.origin is not None and event.buttons() & Qt.MouseButton.RightButton:
            self.dragged |= (event.position() - self.press_position).manhattanLength() >= QApplication.startDragDistance()
            if self.dragged:
                self.show_preview(self.pointer_rect(point), event.position())
            return True
        return False

    def release(self, event):
        if event.button() != Qt.MouseButton.RightButton:
            return False
        if self.consume_release:
            self.consume_release = False
            return True
        if self.origin is None:
            return True
        point = self.view.mapToScene(event.position().toPoint())
        dragged = self.dragged or (event.position() - self.press_position).manhattanLength() >= QApplication.startDragDistance()
        if dragged:
            rect = self.pointer_rect(point)
            if rect.width() > 0 and rect.height() > 0:
                self.commit(rect)
            self.cancel()
        else:
            anchor = self.origin
            self.cancel()
            dialog = RectangleSizeDialog(self.owner, self.view.scene.sceneRect(), self.owner.get_px_per_meter(), self.last_size)
            try:
                if dialog.exec() == QDialog.DialogCode.Accepted and self.tools.open:
                    self.begin_placement(*dialog.dimensions(), anchor=anchor)
            finally:
                dialog.deleteLater()
        return True

    def begin_placement(self, width, height, anchor=None):
        bounds = self.view.scene.sceneRect()
        if not all(math.isfinite(value) and value > 0 for value in (width, height)) or width > bounds.width() or height > bounds.height():
            raise ValueError("Rectangle does not fit the blank sheet")
        self.cancel()
        self.pending_size = self.last_size = (width, height)
        point = anchor if anchor is not None else bounds.center()
        self.show_preview(self.pointer_rect(point), self.view.mapFromScene(point))

    def commit(self, rect):
        if rect.width() <= 0 or rect.height() <= 0 or not self.view.scene.sceneRect().contains(rect):
            raise ValueError("Rectangle is outside the sheet")
        previous = list(self.segments() or [])
        lines = rectangle_segments(rect.x(), rect.y(), rect.width(), rect.height(), self.tools.stroke_color.name())
        self.undo_stack.append(previous)
        if len(self.undo_stack) > 50:
            del self.undo_stack[0]
        self.redo_stack.clear()
        self.store(previous + lines)

    def store(self, segments):
        self.owner.session.metadata[PLAN_DRAWING_KEY] = encode_drawing(segments)
        self.owner.session.dirty = True
        self.owner.invalidate_live_preview()
        self.owner.refresh_session_labels()

    def undo(self):
        if self.undo_stack:
            self.cancel()
            self.redo_stack.append(list(self.segments() or []))
            self.store(self.undo_stack.pop())

    def redo(self):
        if self.redo_stack:
            self.cancel()
            self.undo_stack.append(list(self.segments() or []))
            self.store(self.redo_stack.pop())
