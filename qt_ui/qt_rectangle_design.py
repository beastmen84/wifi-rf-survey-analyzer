"""Right-button rectangle gestures and provisional, dimensioned placement."""
import math

from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPen, QPixmap
from PySide6.QtWidgets import (QApplication, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsRectItem, QLabel, QVBoxLayout)

from app_core.units import distance_unit_label, display_units_to_meters, meters_to_display_units
from survey.plan_drawing import PLAN_DRAWING_KEY, drawing_segments, encode_drawing, rectangle_segments
from survey.plan_snapping import PlanSnapper, SnapResult
from qt_ui.scaling import widget_px
from qt_ui.qt_plan_eraser import PlanEraserController


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
        self.snapper = PlanSnapper()
        self.snap_items = []
        self.snap_guides = ()
        self.snap_bypass = False
        self.last_pointer = None
        self.undo_stack, self.redo_stack = [], []
        self.preview = None
        self.origin = self.press_position = self.pending_size = self.last_size = None
        self.dragged = self.consume_release = False
        self.measurement = QLabel(self.view.viewport())
        self.measurement.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.measurement.setStyleSheet("background:#182433;color:white;border:1px solid #8194aa;border-radius:4px;padding:6px 9px;")
        self.measurement.hide()
        self.eraser = PlanEraserController(self)
        self.owner.installEventFilter(self)
        self.view.installEventFilter(self)
        self.view.viewport().installEventFilter(self)

    def eventFilter(self, source, event):
        if source is self.owner and event.type() == QEvent.Type.WindowDeactivate:
            self.cancel()
        if (self.tools.open and event.type() in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease)
                and event.key() == Qt.Key.Key_Alt):
            self.snap_bypass = event.type() == QEvent.Type.KeyPress
            self.refresh_snap()
            return True  # Alt belongs to Design Mode, not menu mnemonic focus.
        return super().eventFilter(source, event)

    def sync(self):
        session = self.owner.session
        changed_scene = session is not self.session or self.view.pixmap_item is not self.pixmap
        if changed_scene:
            if self.view.pixmap_item is not self.pixmap:
                # scene.clear() has already destroyed these C++ graphics items.
                self.preview = None
                self.items = []
                self.snap_items = []
                self.eraser.reset_scene()
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
        self.eraser.cancel()
        for item in self.items:
            self.view.scene.removeItem(item)
        self.items = []
        lines = self.segments()
        bounds = self.view.scene.sceneRect()
        if any(line[key] > extent + 1e-7 for line in lines or []
               for keys, extent in ((('x1', 'x2'), bounds.width()), (('y1', 'y2'), bounds.height())) for key in keys):
            raise ValueError("Saved drawing is outside the sheet")
        self.eraser.set_segments(lines or [])
        self.snapper = PlanSnapper(lines or [])
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
        existed = self.eraser.cancel() or self.origin is not None or self.pending_size is not None
        if self.preview is not None:
            self.view.scene.removeItem(self.preview)
            self.preview = None
        self.origin = self.press_position = self.pending_size = None
        self.dragged = self.consume_release = False
        self.last_pointer = None
        self.snap_bypass = False
        self.clear_snap_guides()
        self.measurement.hide()
        return existed

    def hide_preview(self):
        self.eraser.hide_preview()
        self.last_pointer = None
        if self.preview is not None:
            self.preview.hide()
        self.measurement.hide()
        for item in self.snap_items:
            item.hide()

    def snap_position(self, point, width=0, height=0, bypass=False):
        bounds = self.view.scene.sceneRect()
        if bypass or self.snap_bypass:
            return SnapResult(min(max(point.x(), bounds.left()), bounds.right() - width),
                              min(max(point.y(), bounds.top()), bounds.bottom() - height))
        zoom = max(1e-9, math.hypot(self.view.transform().m11(), self.view.transform().m12()))
        grid = self.view.grid_spacing_pixels() if self.tools.snap_button.isChecked() else None
        return self.snapper.snap(point.x(), point.y(), width, height,
                                 (bounds.left(), bounds.top(), bounds.right(), bounds.bottom()),
                                 widget_px(self.owner, 10) / zoom, grid)

    def pointer_rect(self, point, bypass=False):
        if self.pending_size:
            width, height = self.pending_size
            result = self.snap_position(point, width, height, bypass)
            self.snap_guides = result.guides
            return QRectF(result.x, result.y, width, height)
        result = self.snap_position(point, bypass=bypass)
        self.snap_guides = result.guides
        point = QPointF(result.x, result.y)
        return QRectF(self.origin, point).normalized()

    def refresh_snap(self):
        if self.tools.active_tool != "rectangle":
            return
        if self.last_pointer is not None and (self.pending_size or self.dragged):
            point = self.view.mapToScene(self.last_pointer.toPoint())
            if self.view.scene.sceneRect().contains(point) or self.dragged:
                self.show_preview(self.pointer_rect(point), self.last_pointer)

    def clear_snap_guides(self):
        for item in self.snap_items:
            self.view.scene.removeItem(item)
        self.snap_items = []
        self.snap_guides = ()

    def show_snap_guides(self, rect):
        guides = self.snap_guides
        self.clear_snap_guides()
        self.snap_guides = guides
        zoom = max(1e-9, math.hypot(self.view.transform().m11(), self.view.transform().m12()))
        radius = widget_px(self.owner, 5) / zoom
        for guide in guides:
            x, y = guide.point
            pen = QPen(QColor("#d97706"), 1.5)
            pen.setCosmetic(True)
            marker = QGraphicsEllipseItem(x - radius, y - radius, 2 * radius, 2 * radius)
            marker.setPen(pen)
            additions = [marker]
            if guide.axis in ("x", "y") and guide.span:
                pen = QPen(QColor("#d97706"), 1, Qt.PenStyle.DotLine)
                pen.setCosmetic(True)
                if guide.axis == "x":
                    line = QGraphicsLineItem(x, min(rect.top(), guide.span[0]), x, max(rect.bottom(), guide.span[1]))
                else:
                    line = QGraphicsLineItem(min(rect.left(), guide.span[0]), y, max(rect.right(), guide.span[1]), y)
                line.setPen(pen)
                additions.append(line)
            for item in additions:
                item.setZValue(9)
                item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                self.view.scene.addItem(item)
                self.snap_items.append(item)

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
        self.show_snap_guides(rect)
        density = self.owner.get_px_per_meter()
        values = [meters_to_display_units(value / density, self.owner.measurement_system)
                  for value in (rect.width(), rect.height())]
        numbers = [self.measurement.locale().toString(value, "f", 2) for value in values]
        text = f"{numbers[0]} × {numbers[1]} {distance_unit_label(self.owner.measurement_system)}"
        kinds = [kind for kind in ("corner", "edge", "grid") if any(guide.kind == kind for guide in self.snap_guides)]
        if kinds:
            text += "\n" + " · ".join(self.owner.tr("design_snap_" + kind) for kind in kinds)
        self.show_measurement(text, position)

    def show_measurement(self, text, position):
        self.measurement.setText(text)
        self.measurement.adjustSize()
        viewport = self.view.viewport()
        self.measurement.move(max(4, min(int(position.x()) + 16, viewport.width() - self.measurement.width() - 4)),
                              max(4, min(int(position.y()) + 18, viewport.height() - self.measurement.height() - 4)))
        self.measurement.show()
        self.measurement.raise_()

    def press(self, event):
        if event.button() != Qt.MouseButton.RightButton:
            return False
        if self.tools.active_tool == "eraser":
            return self.eraser.press(event)
        point = self.view.mapToScene(event.position().toPoint())
        self.last_pointer = event.position()
        bypass = bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)
        if self.pending_size:
            if self.view.scene.sceneRect().contains(point):
                rect = self.pointer_rect(point, bypass)
                self.commit(rect)
                self.cancel()
            self.consume_release = True
        elif self.view.scene.sceneRect().contains(point):
            result = self.snap_position(point, bypass=bypass)
            self.origin, self.press_position = QPointF(result.x, result.y), event.position()
            self.snap_guides = result.guides
            self.show_snap_guides(QRectF(self.origin, self.origin))
            self.dragged = False
        return True

    def move(self, event):
        if self.tools.active_tool == "eraser":
            return self.eraser.move(event)
        self.last_pointer = event.position()
        bypass = bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)
        point = self.view.mapToScene(event.position().toPoint())
        if self.pending_size:
            if self.view.scene.sceneRect().contains(point):
                self.show_preview(self.pointer_rect(point, bypass), event.position())
            else:
                self.hide_preview()
        if self.origin is not None and event.buttons() & Qt.MouseButton.RightButton:
            self.dragged |= (event.position() - self.press_position).manhattanLength() >= QApplication.startDragDistance()
            if self.dragged:
                self.show_preview(self.pointer_rect(point, bypass), event.position())
            return True
        return False

    def release(self, event):
        if event.button() != Qt.MouseButton.RightButton:
            return False
        if self.tools.active_tool == "eraser":
            return self.eraser.release(event)
        if self.consume_release:
            self.consume_release = False
            return True
        if self.origin is None:
            return True
        point = self.view.mapToScene(event.position().toPoint())
        dragged = self.dragged or (event.position() - self.press_position).manhattanLength() >= QApplication.startDragDistance()
        if dragged:
            rect = self.pointer_rect(point, bool(event.modifiers() & Qt.KeyboardModifier.AltModifier))
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
        self.last_pointer = QPointF(self.view.mapFromScene(point))
        self.show_preview(self.pointer_rect(point), self.view.mapFromScene(point))

    def commit(self, rect):
        if rect.width() <= 0 or rect.height() <= 0 or not self.view.scene.sceneRect().contains(rect):
            raise ValueError("Rectangle is outside the sheet")
        previous = list(self.segments() or [])
        lines = rectangle_segments(rect.x(), rect.y(), rect.width(), rect.height(), self.tools.stroke_color.name())
        self.apply_edit(previous + lines)

    def apply_edit(self, segments):
        previous = list(self.segments() or [])
        if segments == previous:
            return False
        encode_drawing(segments)  # Validate before changing history or metadata.
        self.undo_stack.append(previous)
        if len(self.undo_stack) > 50:
            del self.undo_stack[0]
        self.redo_stack.clear()
        self.store(segments)
        return True

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
