"""Annotation-only gestures, properties and selection; never edits walls."""
from copy import deepcopy
import math
from uuid import uuid4

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPainterPathStroker, QPainter, QPen, QPixmap, QIcon
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog,
    QButtonGroup, QHBoxLayout, QWidget, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QLabel, QPushButton, QVBoxLayout)

from app_core.units import distance_unit_label, display_units_to_meters, meters_to_display_units
from survey.plan_annotations import (annotation_points, overlaps, place_aperture, supported, align_aperture,
                                     transform_annotations, validate_annotations)
from survey.plan_annotation_rendering import annotation_item, annotation_path, annotation_fits, annotation_parts
from qt_ui.qt_theme import QT_THEMES
from survey.plan_labels import transform_labels, labels_geometry
from survey.plan_label_rendering import label_item
from survey.plan_geometry import segment_bounds
from survey.planar_geometry import point_projection
from app_core.plan_preferences import tool_colors, save_tool_colors
from qt_ui.qt_plan_colors import choose_plan_color
from qt_ui.scaling import widget_px
from qt_ui.qt_plan_objects import ObjectAnnotationDialog
from survey.plan_objects import (FREE_ANNOTATIONS, HOSTED_ANNOTATIONS, object_default,
                                 object_geometry, object_is_round)

ANNOTATION_TOOLS = ("marker", *HOSTED_ANNOTATIONS, *FREE_ANNOTATIONS, "annotation_select", "annotation_eraser")
DOOR_CHOICES = (("single", 0, 1), ("single", 1, 1), ("single", 0, -1), ("single", 1, -1),
                ("double", 0, 1), ("double", 0, -1), ("sliding", 0, 1), ("frame", 0, 1))


class AnnotationDialog(QDialog):
    def __init__(self, controller, item):
        super().__init__(controller.owner)
        self.controller, self.value = controller, deepcopy(item)
        owner = controller.owner
        self.setWindowTitle(owner.tr("annotation_" + item["kind"]))
        self.setMinimumWidth(widget_px(owner, 380))
        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)
        self.color = QPushButton()
        def update_color():
            self.color.setText(self.value["color"])
            self.color.setStyleSheet("border:2px solid " + self.value["color"] + ";padding:6px;")
        def choose():
            value = choose_plan_color(self.value["color"], self)
            if value.isValid():
                self.value["color"] = value.name()
                update_color()
        self.color.clicked.connect(choose)
        update_color()
        form.addRow(owner.tr("blank_tool_color"), self.color)
        self.stroke = QDoubleSpinBox()
        self.stroke.setRange(.5, 20)
        self.stroke.setSingleStep(.5)
        self.stroke.setValue(item["stroke"])
        self.stroke.setSuffix(" px")
        form.addRow(owner.tr("annotation_stroke"), self.stroke)
        if item["kind"] == "marker":
            self.grid = QCheckBox(owner.tr("annotation_grid"))
            self.grid.setChecked(controller.drawing.tools.snap_button.isChecked())
            form.addRow(self.grid)
        else:
            self.width_spin = QDoubleSpinBox()
            self.width_spin.setDecimals(2)
            self.width_spin.setRange(.01, meters_to_display_units(100, owner.measurement_system))
            self.width_spin.setSingleStep(.01)
            self.width_spin.setSuffix(" " + distance_unit_label(owner.measurement_system))
            self.width_spin.setValue(meters_to_display_units(math.dist(*annotation_points(item)) / owner.get_px_per_meter(), owner.measurement_system))
            form.addRow(owner.tr("blank_plan_width"), self.width_spin)
            if item["kind"] == "door":
                self.door_group = QButtonGroup(self)
                self.door_buttons = {}
                choices = QWidget()
                row = QHBoxLayout(choices)
                row.setContentsMargins(0, 0, 0, 0)
                row.setSpacing(widget_px(owner, 4))
                for index, choice in enumerate(DOOR_CHOICES):
                    key = "door_option_" + str(index)
                    button = owner.create_boundaries_text_button("", key)
                    button.setCheckable(True)
                    button.setFixedSize(widget_px(owner, 46), widget_px(owner, 46))
                    button.setToolTip(owner.tr(key))
                    button.setAccessibleName(owner.tr(key))
                    self.door_group.addButton(button, index)
                    self.door_buttons[choice] = button
                    row.addWidget(button)
                row.addStretch()
                self.door_group.idClicked.connect(lambda _index: self.update_door_icons())
                variant = item.get("variant", "single")
                self.choose_door(variant, item.get("hinge", 0) if variant == "single" else 0,
                                 item.get("side", 1) if variant in ("single", "double") else 1)
                layout.addWidget(QLabel(owner.tr("annotation_type")))
                layout.addWidget(choices)
        hint = QLabel(owner.tr("annotation_properties_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(owner.tr("cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def choose_door(self, variant, hinge=0, side=1):
        self.door_buttons[(variant, hinge, side)].setChecked(True)
        self.update_door_icons()

    def update_door_icons(self):
        size = widget_px(self.controller.owner, 34)
        palette = QT_THEMES[self.controller.owner.theme]
        for choice, button in self.door_buttons.items():
            variant, hinge, side = choice
            item = dict(kind="door", x1=0, y1=0, x2=20, y2=0, variant=variant, hinge=hinge, side=side)
            bounds = annotation_path(item).boundingRect().adjusted(-3, -3, 3, 3)
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            scale = min(size / bounds.width(), size / bounds.height())
            painter.translate(size / 2, size / 2)
            painter.scale(scale, scale)
            painter.translate(-bounds.center().x(), -bounds.center().y())
            for path, dashed in annotation_parts(item):
                pen = QPen(QColor("#ffffff" if button.isChecked() else palette["text"]), 1.5 / scale)
                if dashed:
                    pen.setStyle(Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.drawPath(path)
            painter.end()
            button.setIcon(QIcon(pixmap))
            button.setIconSize(pixmap.size())

    def properties(self):
        result = deepcopy(self.value)
        result["stroke"] = self.stroke.value()
        if result["kind"] == "marker":
            self.controller.marker_grid = self.grid.isChecked()
            self.controller.drawing.tools.snap_button.setChecked(self.grid.isChecked())
        else:
            width = display_units_to_meters(self.width_spin.value(), self.controller.owner.measurement_system) * self.controller.owner.get_px_per_meter()
            a, b = annotation_points(result)
            length = math.dist(a, b)
            cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
            result.update(x1=cx - width * ux / 2, y1=cy - width * uy / 2,
                          x2=cx + width * ux / 2, y2=cy + width * uy / 2)
            if result["kind"] == "door":
                variant, hinge, side = DOOR_CHOICES[self.door_group.checkedId()]
                result.update(variant=variant, hinge=hinge, side=side)
        return result


class AnnotationController:
    def __init__(self, drawing):
        self.drawing, self.owner, self.view = drawing, drawing.owner, drawing.view
        self.items, self.preview = [], []
        self.model = []
        self.selected, self.selected_labels = (), ()
        self.origin = self.last_pointer = None
        self.moving = self.dialog_open = self.consume_release = False
        self.pending, self.path, self.draft, self.draft_labels = None, [], [], []
        self.marker_grid = False
        self.templates = {}

    def reset_scene(self):
        self.items, self.preview = [], []
        self.model = []
        self.cancel()

    def cancel(self):
        existed = bool(self.selected or self.selected_labels or self.origin is not None or self.moving or self.path or self.pending)
        self.clear_preview()
        self.selected, self.selected_labels = (), ()
        self.origin = self.last_pointer = None
        self.moving = self.consume_release = False
        self.pending, self.path, self.draft, self.draft_labels = None, [], [], []
        return existed

    def clear_preview(self):
        for item in self.preview:
            self.view.scene.removeItem(item)
        self.preview = []

    def hide_preview(self):
        for item in self.preview:
            item.hide()

    def redraw(self, items):
        self.cancel()
        for item in self.items:
            self.view.scene.removeItem(item)
        self.items = []
        self.model = items
        for annotation in items:
            item = annotation_item(annotation)
            self.view.scene.addItem(item)
            self.items.append(item)

    def configure(self, kind):
        density = self.owner.get_px_per_meter()
        template = self.templates.get(kind) or (object_default(kind, density) if kind in FREE_ANNOTATIONS else dict(id="template", kind=kind, color="#d97706" if kind == "marker" else "#334155",
            stroke=3 if kind == "marker" else 2, points=[[0, 0], [1, 1]], x1=0, y1=0, x2=density * (.9 if kind == "door" else 1.2), y2=0,
            variant="single", hinge=0, side=1))
        template = dict(template, **tool_colors(kind))
        result = self.dialog(template)
        if result is not None:
            self.templates[kind] = result
            save_tool_colors(kind, result)
            if kind == "marker":
                self.drawing.tools.snap_button.setChecked(self.marker_grid)
            if self.marker_grid:
                self.owner.set_floorplan_grid_enabled(True, show_status=False)
        return result is not None

    def dialog(self, item):
        self.dialog_open = True
        session, pixmap = self.owner.session, self.view.pixmap_item
        dialog = (ObjectAnnotationDialog if item["kind"] in FREE_ANNOTATIONS else AnnotationDialog)(self, item)
        try:
            if (dialog.exec() == QDialog.DialogCode.Accepted and self.drawing.tools.open
                    and session is self.owner.session and pixmap is self.view.pixmap_item):
                return dialog.properties()
        finally:
            dialog.deleteLater()
            self.dialog_open = False
        return None

    def valid(self, items, labels=(), exclude=(), lines=None, existing=None):
        try:
            validate_annotations(items)
        except (ValueError, TypeError, KeyError, OverflowError):
            return False
        others = [a for a in (self.model if existing is None else existing) if a["id"] not in exclude]
        bounds = self.view.scene.sceneRect()
        for item in items:
            if not annotation_fits(item, bounds):
                return False
            if not supported(item, self.drawing.selection.lines if lines is None else lines) or overlaps(item, others):
                return False
            others.append(item)
        return self.drawing.selection.fits(labels_geometry(labels)) if labels else True

    def show(self, items=(), labels=(), valid=True, rectangle=None):
        self.clear_preview()
        for annotation in items:
            self.preview.append(annotation_item(annotation, "#0284c7" if valid else "#ef4444"))
        for label in labels:
            self.preview.append(label_item(label if valid else dict(label, color="#ef4444"), selected=True))
        if rectangle is not None:
            from PySide6.QtWidgets import QGraphicsRectItem
            from PySide6.QtGui import QPen
            item = QGraphicsRectItem(rectangle)
            item.setPen(QPen(QColor("#0284c7"), 1, Qt.PenStyle.DashLine))
            self.preview.append(item)
        for item in self.preview:
            item.setZValue(9)
            item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.view.scene.addItem(item)

    def point(self, position, grid=False, drawing_snap=False):
        p = self.view.mapToScene(position.toPoint())
        bounds = self.view.scene.sceneRect()
        x, y = min(max(p.x(), bounds.left()), bounds.right()), min(max(p.y(), bounds.top()), bounds.bottom())
        if drawing_snap and not self.drawing.snap_bypass:
            snapper = self.drawing.reference_snapper if self.drawing.tools.active_tool == "marker" else self.drawing.snapper
            result = snapper.snap(x, y, 0, 0,
                (bounds.left(), bounds.top(), bounds.right(), bounds.bottom()), self.tolerance(),
                self.view.grid_spacing_pixels() if grid else None)
            x, y = result.x, result.y
            self.drawing.snap_guides = result.guides
        else:
            self.drawing.snap_guides = ()
        return [x, y]

    def tolerance(self):
        return widget_px(self.owner, 10) / max(1e-9, abs(self.view.transform().m11()))

    def pick(self, point):
        # Text on filled furniture stays reachable. Keep the existing priority
        # for hosted openings/markers under whitespace in a label's frame.
        hit = self.drawing.text.hit(QPointF(*point))
        stroker = QPainterPathStroker()
        items = self.model
        for index in reversed(range(len(items))):
            stroker.setWidth(self.tolerance() * 2 + items[index]["stroke"])
            path = self.items[index].path()
            margin = self.tolerance() + items[index]["stroke"] / 2
            if not path.boundingRect().adjusted(-margin, -margin, margin, margin).contains(QPointF(*point)):
                continue
            if ((items[index]["kind"] in FREE_ANNOTATIONS and path.contains(QPointF(*point)))
                    or stroker.createStroke(path).contains(QPointF(*point))):
                if hit is not None and items[index]["kind"] in FREE_ANNOTATIONS:
                    return (), (hit,)
                return (index,), ()
        return ((), (hit,)) if hit is not None else ((), ())

    def selected_items(self):
        items = self.model
        return [items[i] for i in self.selected]

    def selected_texts(self):
        labels = self.drawing.text.labels
        return [labels[i] for i in self.selected_labels]

    def select(self, indices=(), labels=()):
        self.selected, self.selected_labels = tuple(indices), tuple(labels)
        self.show(self.selected_items(), self.selected_texts())
        self.drawing.tools.update_tool_state()
        if self.selected or self.selected_labels:
            items = self.selected_items()
            if len(items) == 1 and not self.selected_labels and items[0]["kind"] in FREE_ANNOTATIONS:
                text = self.object_measurement(items[0]) + "\n" + self.owner.tr(
                    "object_round_selection_note" if object_is_round(items[0]) else "object_selection_note")
            else:
                text = self.owner.tr("object_selection_note" if any(a["kind"] in FREE_ANNOTATIONS for a in items) else "annotation_selection_note")
            self.drawing.show_measurement(text, self.last_pointer or QPointF())

    def press(self, event):
        self.last_pointer = event.position()
        tool = self.drawing.tools.active_tool
        if self.moving:
            self.update_move(event.position())
            if self.valid(self.draft, self.draft_labels, exclude=[a["id"] for a in self.selected_items()]):
                self.commit_selection(self.draft, self.draft_labels)
                self.moving = False
            self.consume_release = True
        elif tool in FREE_ANNOTATIONS:
            self.update_object(event.position())
            if self.pending and self.valid([self.pending]):
                item = dict(self.pending, id=uuid4().hex)
                self.drawing.apply_edit(self.drawing.segments() or [], annotations=self.drawing.annotations() + [item])
            else:
                self.owner.status.showMessage(self.owner.tr("object_invalid"))
            self.consume_release = True
        elif tool in HOSTED_ANNOTATIONS:
            self.update_aperture(event.position())
            if self.pending and self.valid([self.pending]):
                self.drawing.apply_edit(self.drawing.segments() or [], annotations=self.drawing.annotations() + [self.pending])
            else:
                self.owner.status.showMessage(self.owner.tr("annotation_invalid"))
            self.consume_release = True
        else:
            self.origin = self.point(event.position(), tool == "marker" and self.marker_grid, tool == "marker")
            self.path = [self.origin] if tool == "marker" else []
            if tool == "marker":
                self.drawing.show_snap_guides(QRectF(QPointF(*self.origin), QPointF(*self.origin)))
        return True

    def object_measurement(self, item):
        sizes = [item["width"]] if item["kind"] == "symbol" or item["variant"] in ("square", "round", "l_equal") else [item["width"], item["height"]]
        unit = distance_unit_label(self.owner.measurement_system)
        values = [meters_to_display_units(size / self.owner.get_px_per_meter(), self.owner.measurement_system) for size in sizes]
        return self.owner.tr("object_" + item["kind"] + "_" + item["variant"]) + "\n" + " × ".join(
            self.drawing.measurement.locale().toString(value, "f", 2) for value in values) + " " + unit

    def update_object(self, position):
        template = self.templates.get(self.drawing.tools.active_tool)
        if template is None:
            return
        point = self.view.mapToScene(position.toPoint())
        if not self.view.scene.sceneRect().contains(point):
            self.pending = None
            self.clear_preview()
            self.drawing.clear_snap_guides()
            self.drawing.measurement.hide()
            return
        item = dict(template, id="preview", cx=point.x(), cy=point.y())
        geometry = object_geometry(item)
        snapped = self.drawing.snap_shape(geometry, centers=[(item["cx"], item["cy"])])
        self.pending = transform_annotations([item], dx=snapped[0]["x1"] - geometry[0]["x1"],
                                            dy=snapped[0]["y1"] - geometry[0]["y1"])[0]
        self.show([self.pending], valid=self.valid([self.pending]))
        self.drawing.show_snap_guides(annotation_path(self.pending).boundingRect())
        note = "object_round_note" if object_is_round(item) else "object_place_note"
        self.drawing.show_measurement(self.object_measurement(item) + "\n" + self.owner.tr(note), position)

    def update_aperture(self, position):
        tool = self.drawing.tools.active_tool
        template = deepcopy(self.templates.get(tool))
        if not template:
            return
        template["id"] = uuid4().hex
        self.pending = self.hosted(self.point(position), math.dist(*annotation_points(template)), template)
        valid = self.pending is not None and self.valid([self.pending])
        self.show([self.pending] if self.pending else [], valid=valid)
        if self.pending:
            self.drawing.show_snap_guides(annotation_path(self.pending).boundingRect())
        self.drawing.show_measurement(self.owner.tr("annotation_place_note" if valid else "annotation_invalid"), position)

    def hosted(self, point, width, template):
        lines = self.drawing.selection.lines
        item = place_aperture(point, width, lines, self.tolerance(), template)
        if item is None and not self.drawing.snap_bypass:
            # A jamb can anchor to a wall endpoint even though the cursor's
            # usual center grip would initially extend beyond that wall.
            choices = []
            for line in lines:
                a, b = (line["x1"], line["y1"]), (line["x2"], line["y2"])
                if math.dist(point, point_projection(point, a, b)) > self.tolerance():
                    continue
                length = math.dist(a, b)
                for sign in (-1, 1):
                    center = [point[i] + sign * width / 2 * (b[i] - a[i]) / length for i in (0, 1)]
                    placed = place_aperture(center, width, lines, self.tolerance(), template)
                    if placed and min(math.dist(point, p) for p in annotation_points(placed)) <= self.tolerance():
                        choices.append(placed)
            item = choices[0] if choices else None
        self.drawing.snap_guides = ()
        if item and not self.drawing.snap_bypass:
            bounds = self.view.scene.sceneRect()
            item, self.drawing.snap_guides = align_aperture(item, lines, self.drawing.snapper,
                (bounds.left(), bounds.top(), bounds.right(), bounds.bottom()), self.tolerance(),
                self.view.grid_spacing_pixels() if self.drawing.tools.snap_button.isChecked() else None)
        return item

    def refresh_snap(self):
        if self.last_pointer is None:
            return
        tool = self.drawing.tools.active_tool
        if self.moving:
            self.update_move(self.last_pointer)
        elif tool in FREE_ANNOTATIONS:
            self.update_object(self.last_pointer)
        elif tool in HOSTED_ANNOTATIONS:
            self.update_aperture(self.last_pointer)
        elif tool == "marker":
            point = self.point(self.last_pointer, self.marker_grid, True)
            if self.origin is not None and len(self.path) > 1:
                self.show([dict(self.templates["marker"], id="preview", points=self.path[:-1] + [point])])
            self.drawing.show_snap_guides(QRectF(QPointF(*point), QPointF(*point)))

    def move(self, event):
        self.last_pointer = event.position()
        tool = self.drawing.tools.active_tool
        if self.moving:
            self.update_move(event.position())
            return False
        if tool in FREE_ANNOTATIONS:
            self.update_object(event.position())
            return False
        if tool in HOSTED_ANNOTATIONS:
            self.update_aperture(event.position())
            return False
        if self.origin is None or not event.buttons() & Qt.MouseButton.RightButton:
            if tool == "annotation_eraser":
                self.selected, self.selected_labels = self.pick(self.point(event.position()))
                self.show(self.selected_items(), self.selected_texts(), valid=False)
            elif tool == "marker":
                point = self.point(event.position(), self.marker_grid, True)
                self.drawing.show_snap_guides(QRectF(QPointF(*point), QPointF(*point)))
                if self.drawing.snap_guides:
                    self.drawing.show_measurement(self.owner.tr("annotation_marker_note"), event.position())
                else:
                    self.drawing.measurement.hide()
            return False
        point = self.point(event.position(), tool == "marker" and self.marker_grid, tool == "marker")
        if tool == "marker":
            if math.dist(point, self.path[-1]) >= max(.1, self.tolerance() / 10):
                if len(self.path) >= 9998:
                    return True
                if self.marker_grid and not self.drawing.snap_bypass and point[0] != self.path[-1][0] and point[1] != self.path[-1][1]:
                    self.path.append([point[0], self.path[-1][1]])
                self.path.append(point)
            if len(self.path) >= 2:
                self.show([dict(self.templates["marker"], id="preview", points=self.path)])
                self.drawing.show_snap_guides(QRectF(QPointF(*point), QPointF(*point)))
        else:
            rect = QRectF(QPointF(*self.origin), QPointF(*point)).normalized()
            area = QPainterPath()
            area.addRect(rect)
            stroker = QPainterPathStroker()
            stroker.setWidth(2)
            self.selected = tuple(i for i, a in enumerate(self.model)
                                  if (a["kind"] in FREE_ANNOTATIONS and annotation_path(a).intersects(area))
                                  or stroker.createStroke(annotation_path(a)).intersects(area))
            self.selected_labels = self.drawing.text.intersecting(rect)
            self.show(self.selected_items(), self.selected_texts(), valid=tool != "annotation_eraser", rectangle=rect)
        return True

    def release(self, event):
        if self.consume_release:
            self.consume_release = False
            return True
        if self.origin is None:
            return True
        if self.drawing.tools.active_tool == "marker":
            self.move(event)  # The release endpoint is also sampled below.
            point = self.point(event.position(), self.marker_grid, True)
            if point != self.path[-1]:
                if self.marker_grid and not self.drawing.snap_bypass and point[0] != self.path[-1][0] and point[1] != self.path[-1][1]:
                    self.path.append([point[0], self.path[-1][1]])
                self.path.append(point)
            if len(self.path) >= 2:
                item = dict(self.templates["marker"], id=uuid4().hex, points=self.path)
                if self.valid([item]):
                    self.drawing.apply_edit(self.drawing.segments() or [], annotations=self.drawing.annotations() + [item])
            self.cancel()
        else:
            if math.dist(self.origin, self.point(event.position())) <= self.tolerance() / 2:
                self.selected, self.selected_labels = self.pick(self.origin)
            self.origin = None
            if self.drawing.tools.active_tool == "annotation_eraser":
                self.delete()
            else:
                self.select(self.selected, self.selected_labels)
        return True

    def delete(self):
        if not (self.selected or self.selected_labels):
            return False
        items = [a for i, a in enumerate(self.drawing.annotations()) if i not in self.selected]
        labels = [a for i, a in enumerate(self.drawing.labels()) if i not in self.selected_labels]
        self.cancel()
        return self.drawing.apply_edit(self.drawing.segments() or [], labels=labels, annotations=items)

    def begin_move(self):
        if not (self.selected or self.selected_labels):
            return False
        self.move_source, self.label_source = deepcopy(self.selected_items()), deepcopy(self.selected_texts())
        self.anchor = self.point(self.last_pointer) if self.last_pointer is not None else annotation_points(self.move_source[0])[0] if self.move_source else [self.label_source[0]["x"], self.label_source[0]["y"]]
        self.draft, self.draft_labels = self.move_source, self.label_source
        self.moving = True
        return True

    def update_move(self, position):
        point = self.point(position)
        dx, dy = point[0] - self.anchor[0], point[1] - self.anchor[1]
        draft = transform_annotations(self.move_source, dx=dx, dy=dy)
        for index, item in enumerate(draft):
            if item["kind"] in HOSTED_ANNOTATIONS:
                a, b = annotation_points(item)
                center = [(a[i] + b[i]) / 2 for i in (0, 1)]
                hosted = self.hosted(center, math.dist(a, b), item)
                if hosted:
                    draft[index] = hosted
        self.draft, self.draft_labels = draft, transform_labels(self.label_source, dx=dx, dy=dy)
        if not any(a["kind"] in HOSTED_ANNOTATIONS for a in draft):
            geometry = labels_geometry(self.draft_labels)
            for item in draft:
                if item["kind"] in FREE_ANNOTATIONS:
                    geometry.extend(object_geometry(item))
                else:
                    geometry.extend(dict(x1=a[0], y1=a[1], x2=b[0], y2=b[1], color=item["color"])
                                    for a, b in zip(item["points"], item["points"][1:]))
            if geometry:
                centers = None
                if any(a["kind"] in FREE_ANNOTATIONS for a in draft):
                    centers = [(a["cx"], a["cy"]) for a in draft if a["kind"] in FREE_ANNOTATIONS]
                    centers.extend((a["x"], a["y"]) for a in self.draft_labels)
                    if len(draft) + len(self.draft_labels) > 1:
                        left, top, right, bottom = segment_bounds(geometry)
                        centers.append(((left + right) / 2, (top + bottom) / 2))
                snapped = self.drawing.snap_shape(geometry, centers=centers)
                dx, dy = snapped[0]["x1"] - geometry[0]["x1"], snapped[0]["y1"] - geometry[0]["y1"]
                self.draft = transform_annotations(draft, dx=dx, dy=dy)
                self.draft_labels = transform_labels(self.draft_labels, dx=dx, dy=dy)
        self.show(self.draft, self.draft_labels, valid=self.valid(self.draft, self.draft_labels, exclude=[a["id"] for a in self.move_source]))
        if self.draft:
            self.drawing.show_snap_guides(annotation_path(self.draft[0]).boundingRect())

    def commit_selection(self, items, labels):
        ids, label_ids = [a["id"] for a in items], [a["id"] for a in labels]
        replacements, text_replacements = {a["id"]: a for a in items}, {a["id"]: a for a in labels}
        annotations = [replacements.get(a["id"], a) for a in self.drawing.annotations()]
        texts = [text_replacements.get(a["id"], a) for a in self.drawing.labels()]
        changed = self.drawing.apply_edit(self.drawing.segments() or [], labels=texts, annotations=annotations)
        self.cancel()
        self.select([i for i, a in enumerate(self.drawing.annotations()) if a["id"] in ids],
                    [i for i, a in enumerate(self.drawing.labels()) if a["id"] in label_ids])
        return changed

    def rotate(self):
        tool = self.drawing.tools.active_tool
        if tool in FREE_ANNOTATIONS and tool in self.templates:
            item = self.templates[tool]
            if not object_is_round(item):
                item["angle"] = (item["angle"] + 90) % 360
                if self.last_pointer is not None:
                    self.update_object(self.last_pointer)
                    if self.pending is not None:
                        self.drawing.dimensions.update_object(self.pending)
            return True
        items = deepcopy(self.draft if self.moving else self.selected_items())
        labels = deepcopy(self.draft_labels if self.moving else self.selected_texts())
        if not (items or labels):
            return False
        points = [p for a in items for p in annotation_points(a)] + [[a["x"], a["y"]] for a in labels]
        pivot = tuple((min(p[i] for p in points) + max(p[i] for p in points)) / 2 for i in (0, 1))
        markers = transform_annotations([a for a in items if a["kind"] not in HOSTED_ANNOTATIONS], 90, pivot)
        marker_map = {a["id"]: a for a in markers}
        for item in items:
            if item["kind"] not in HOSTED_ANNOTATIONS:
                item.update(marker_map[item["id"]])
            elif item["kind"] == "door" and item.get("variant", "single") in ("single", "double"):
                item["side"] *= -1
        labels = transform_labels(labels, 90, pivot)
        if self.valid(items, labels, exclude=[a["id"] for a in self.selected_items()]):
            if self.moving:
                self.move_source, self.label_source = items, labels
                self.anchor = self.point(self.last_pointer) if self.last_pointer is not None else list(pivot)
                self.draft, self.draft_labels = items, labels
                self.show(items, labels)
                if len(items) == 1 and not labels and items[0]["kind"] in FREE_ANNOTATIONS:
                    self.drawing.dimensions.update_object(items[0])
            else:
                self.commit_selection(items, labels)
                if len(items) == 1 and not labels and items[0]["kind"] in FREE_ANNOTATIONS:
                    self.drawing.dimensions.update_object(items[0])
        return True

    def edit(self):
        if len(self.selected_labels) == 1 and not self.selected:
            return self.drawing.text.edit(self.selected_labels[0])
        if len(self.selected) != 1 or self.selected_labels:
            return False
        item = self.dialog(self.selected_items()[0])
        if item is not None:
            if self.valid([item], exclude=[item["id"]]):
                changed = self.commit_selection([item], [])
                if changed:
                    save_tool_colors(item["kind"], item)
                return changed
            self.owner.status.showMessage(self.owner.tr("object_invalid" if item["kind"] in FREE_ANNOTATIONS else "annotation_invalid"))
        return False
