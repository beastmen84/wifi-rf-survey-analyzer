"""Blank-sheet design tools and rectangle gesture coordination."""

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPixmap, QShortcut, QKeySequence, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from survey.plan_mode import is_drawn_plan
from qt_ui.qt_theme import QT_THEMES
from qt_ui.qt_rectangle_design import RectangleDesignController
from survey.plan_objects import FREE_ANNOTATIONS, object_is_round
from app_core.plan_preferences import tool_colors, save_tool_colors
from qt_ui.qt_plan_colors import choose_plan_color


class PlanToolsOverlay(QFrame):
    def __init__(self, owner):
        super().__init__(owner.floorplan_view.viewport())
        self.setProperty("fixedViewportOverlay", True)
        self.setFont(owner.font())
        self.owner = owner
        self.open = False
        self.active_tool = "rectangle"
        self.stroke_color = QColor(tool_colors("structure").get("color", "#263238"))
        self.setObjectName("boundariesToolbar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*(owner.spx(8) for _ in range(4)))
        layout.setSpacing(owner.spx(7))
        self.header = QLabel()
        layout.addWidget(self.header)
        self.structure_heading = QLabel()
        layout.addWidget(self.structure_heading)
        row = QHBoxLayout()
        self.tool_row = row
        row.setSpacing(owner.spx(4))
        self.rectangle_button = owner.create_boundaries_tool_button("square.png", "blank_tool_rectangle")
        self.line_button = owner.create_boundaries_text_button("", "blank_tool_line")
        self.circle_button = owner.create_boundaries_text_button("", "blank_tool_circle")
        self.arc_button = owner.create_boundaries_text_button("", "blank_tool_arc")
        self.text_button = owner.create_boundaries_text_button("", "blank_tool_text")
        self.eraser_button = owner.create_boundaries_tool_button("eraser.png", "blank_tool_eraser")
        self.select_button = owner.create_boundaries_text_button("", "blank_tool_select")
        self.undo_button = owner.create_boundaries_text_button("", "blank_tool_undo")
        self.redo_button = owner.create_boundaries_text_button("", "blank_tool_redo")
        for button in (self.rectangle_button, self.line_button, self.circle_button, self.arc_button, self.eraser_button, self.select_button):
            button.setEnabled(False)
            row.addWidget(button)
        layout.addLayout(row)
        self.annotation_heading = QLabel()
        layout.addWidget(self.annotation_heading)
        annotation_row = QHBoxLayout()
        self.annotation_row = annotation_row
        annotation_row.setSpacing(owner.spx(4))
        self.annotation_buttons = {}
        for tool in ("marker", "window", "door", *FREE_ANNOTATIONS, "annotation_eraser", "annotation_select"):
            button = owner.create_boundaries_text_button("", "annotation_" + {"annotation_select": "select", "annotation_eraser": "eraser"}.get(tool, tool))
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, tool=tool: self.select_tool(tool))
            self.annotation_buttons[tool] = button
            annotation_row.addWidget(button)
        annotation_row.insertWidget(3, self.text_button)
        annotation_row.addStretch()
        layout.addLayout(annotation_row)
        self.actions_heading = QLabel()
        layout.addWidget(self.actions_heading)
        actions = QHBoxLayout()
        self.action_row = actions
        actions.setSpacing(owner.spx(4))
        actions.addWidget(self.undo_button)
        actions.addWidget(self.redo_button)
        self.snap_button = owner.create_boundaries_text_button("", "blank_tool_snap")
        self.snap_button.setCheckable(True)
        self.snap_button.setChecked(False)
        self.snap_button.setEnabled(False)
        self.color_button = owner.create_boundaries_text_button("", "blank_tool_color")
        self.color_button.clicked.connect(self.choose_color)
        self.edit_text_button = owner.create_boundaries_text_button("", "plan_text_edit")
        self.edit_text_button.clicked.connect(self.edit_selected_text)
        actions.addWidget(self.snap_button)
        actions.addWidget(self.color_button)
        actions.addWidget(self.edit_text_button)
        row.addStretch()
        actions.addStretch()
        layout.addLayout(actions)
        self.note = QLabel()
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        self.toggle_button = QPushButton(self.parentWidget())
        self.toggle_button.setProperty("fixedViewportOverlay", True)
        self.toggle_button.setObjectName("appBarToggleButton")
        self.toggle_button.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation, True)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setMinimumHeight(owner.spx(34))
        self.toggle_button.clicked.connect(self.set_open)
        self.controller = RectangleDesignController(self)
        self.snap_button.toggled.connect(self.toggle_grid_snap)
        self.drawing_error = False
        self.rectangle_button.setCheckable(True)
        self.eraser_button.setCheckable(True)
        self.line_button.setCheckable(True)
        self.circle_button.setCheckable(True)
        self.arc_button.setCheckable(True)
        self.text_button.setCheckable(True)
        self.select_button.setCheckable(True)
        self.rectangle_button.clicked.connect(self.select_rectangle)
        self.eraser_button.clicked.connect(lambda: self.select_tool("eraser"))
        self.line_button.clicked.connect(lambda: self.select_tool("line"))
        self.circle_button.clicked.connect(lambda: self.select_tool("circle"))
        self.arc_button.clicked.connect(lambda: self.select_tool("arc"))
        self.text_button.clicked.connect(lambda: self.select_tool("text"))
        self.select_button.clicked.connect(lambda: self.select_tool("select"))
        self.undo_button.clicked.connect(self.controller.undo)
        self.redo_button.clicked.connect(self.controller.redo)
        self.escape_shortcut = QShortcut(QKeySequence("Esc"), owner)
        self.escape_shortcut.activated.connect(self.on_escape)
        self.parentWidget().installEventFilter(self)
        self.sync()

    def available(self):
        session = self.owner.session
        return bool(session and not self.drawing_error and self.owner.get_px_per_meter()
                    and self.owner.floorplan_view.has_floorplan() and
                    is_drawn_plan(session.metadata))

    def sync(self):
        self.drawing_error = False
        try:
            self.controller.sync()
        except (ValueError, TypeError, KeyError):
            self.drawing_error = True
            self.owner.status.showMessage(self.owner.tr("rectangle_invalid_drawing"))
        tr = self.owner.tr
        self.toggle_button.setText(tr("blank_tools"))
        self.toggle_button.setToolTip(tr("blank_tools_hint"))
        self.header.setText(tr("blank_tools"))
        self.structure_heading.setText(tr("annotation_structure"))
        self.annotation_heading.setText(tr("annotation_group"))
        self.actions_heading.setText(tr("annotation_controls"))
        for heading in (self.structure_heading, self.annotation_heading, self.actions_heading):
            heading.setStyleSheet("font-weight:600;color:" + QT_THEMES[self.owner.theme]["muted"] + ";")
        self.select_button.setToolTip(tr("annotation_select_structure"))
        for button, key in ((self.rectangle_button, "rectangle"), (self.line_button, "line"),
                            (self.circle_button, "circle"), (self.arc_button, "arc"),
                            (self.text_button, "text"),
                            (self.eraser_button, "eraser"), (self.select_button, "select"),
                            (self.undo_button, "undo"), (self.redo_button, "redo"),
                            (self.snap_button, "snap"), (self.color_button, "color")):
            text = tr("blank_tool_" + key)
            button.setToolTip(text)
            button.setAccessibleName(text)
        self.snap_button.setToolTip(tr("grid_all_vertices_help"))
        self.update_color_icon()
        self.update_snap_icon()
        self.update_history_icons()
        available = self.available()
        if not available or self.owner.scan_in_progress or self.owner.tabs.currentIndex() != 0:
            self.set_open(False)
        self.toggle_button.setVisible(available)
        self.toggle_button.setEnabled(available and not self.owner.scan_in_progress)
        self.update_tool_state()
        self.position_controls()

    def set_open(self, opened):
        self.open = bool(opened and self.available() and not self.owner.scan_in_progress)
        if self.open:
            self.owner.floorplan_view.hide_point_tooltip()
            if self.owner.points_panel_expanded:
                self.owner.toggle_points_panel()
            self.owner.set_boundaries_mode_enabled(False, show_status=False)
            self.owner.floorplan_view.cancel_scale_calibration_pick()
            self.owner.floorplan_view.cancel_ap_position_pick()
        else:
            self.controller.cancel()
        self.toggle_button.setChecked(self.open)
        self.owner.floorplan_view.design_mode_active = self.open
        self.owner.floorplan_view.viewport().setCursor(Qt.CursorShape.CrossCursor if self.open else Qt.CursorShape.ArrowCursor)
        self.escape_shortcut.setEnabled(self.open)
        self.setVisible(self.open)
        self.update_tool_state()
        self.undo_button.setEnabled(self.open and bool(self.controller.undo_stack))
        self.redo_button.setEnabled(self.open and bool(self.controller.redo_stack))
        self.position_controls()

    def on_escape(self):
        if self.controller.rotation.active:
            self.controller.rotation.cancel()
            return
        if not self.controller.cancel():
            self.set_open(False)

    def select_rectangle(self):
        self.select_tool("rectangle")

    def select_tool(self, tool):
        if not self.controller.editable():
            return
        self.controller.cancel()
        if tool in ("marker", "door", "window", *FREE_ANNOTATIONS) and not self.controller.annotation.configure(tool):
            self.update_tool_state()
            return
        self.active_tool = tool
        self.update_tool_state()
        self.position_controls()

    def update_tool_state(self):
        self.eraser_button.setToolTip(self.owner.tr("structure_eraser"))
        self.eraser_button.setAccessibleName(self.owner.tr("structure_eraser"))
        self.select_button.setToolTip(self.owner.tr("annotation_select_structure"))
        self.select_button.setAccessibleName(self.owner.tr("annotation_select_structure"))
        for tool, button in self.annotation_buttons.items():
            button.setEnabled(self.open)
            button.setChecked(self.open and self.active_tool == tool)
            text = self.owner.tr("annotation_" + {"annotation_select": "select", "annotation_eraser": "eraser"}.get(tool, tool))
            button.setToolTip(text)
            button.setAccessibleName(text)
        for tool, button in (("rectangle", self.rectangle_button), ("line", self.line_button),
                             ("circle", self.circle_button), ("arc", self.arc_button),
                             ("text", self.text_button),
                             ("eraser", self.eraser_button), ("select", self.select_button)):
            button.setEnabled(self.open)
            button.setChecked(self.open and self.active_tool == tool)
        self.snap_button.setEnabled(self.open and self.active_tool not in ("eraser", "annotation_eraser"))
        self.snap_button.setToolTip(self.owner.tr("drawing_snap_help"))
        self.color_button.setEnabled(self.open and self.active_tool in ("rectangle", "line", "circle", "arc"))
        selection = self.controller.selection
        curve_edit = len(selection.selected_curves) == 1 and not (selection.selected or selection.selected_labels)
        self.edit_text_button.setEnabled(self.open and self.active_tool == "select"
                                         and (len(selection.selected_labels) == 1 or curve_edit)
                                         and not selection.moving)
        if self.active_tool in ("marker", "door", "window", *FREE_ANNOTATIONS, "annotation_select"):
            a = self.controller.annotation
            self.edit_text_button.setEnabled(self.open and not a.moving and (self.active_tool != "annotation_select" or len(a.selected) + len(a.selected_labels) == 1))
        edit_text = self.owner.tr("curve_edit" if curve_edit else "plan_text_edit")
        if self.active_tool in ("marker", "door", "window", *FREE_ANNOTATIONS, "annotation_select"):
            edit_text = self.owner.tr("annotation_properties")
        self.edit_text_button.setToolTip(edit_text)
        self.edit_text_button.setAccessibleName(edit_text)
        key = {"rectangle": "blank_tools_note", "line": "line_tools_note",
               "circle": "circle_tools_note", "arc": "arc_tools_note",
               "eraser": "eraser_tools_note", "select": "selection_tools_note", "text": "text_tools_note",
               "marker": "annotation_marker_note", "door": "annotation_place_note", "window": "annotation_place_note",
               "desk": "object_place_note", "symbol": "object_place_note",
               "annotation_select": "annotation_selection_note", "annotation_eraser": "annotation_eraser_note"}[self.active_tool]
        template = self.controller.annotation.templates.get(self.active_tool)
        if self.active_tool in FREE_ANNOTATIONS and template and object_is_round(template):
            key = "object_round_note"
        self.note.setText(self.owner.tr(key) + (" " + self.owner.tr("axis_lock_hint")
                                              if self.active_tool in ("line", "arc") else ""))
        self.update_tool_icons()
        if self.owner.session is not None and not self.controller.editable():
            for button in (self.rectangle_button, self.line_button, self.circle_button, self.arc_button,
                           self.text_button, self.eraser_button, self.select_button, self.snap_button,
                           self.color_button, self.edit_text_button, *self.annotation_buttons.values()):
                button.setEnabled(False)
            self.note.setText(self.owner.tr("layer_readonly"))
        if hasattr(self.owner, "layers_panel"):
            self.owner.layers_panel.update_selection()

    def update_tool_icons(self):
        size = self.owner.spx(20)
        for tool, button in (("line", self.line_button), ("select", self.select_button),
                             ("rectangle", self.rectangle_button), ("eraser", self.eraser_button),
                             ("circle", self.circle_button), ("arc", self.arc_button),
                             ("text", self.text_button), ("edit", self.edit_text_button), *self.annotation_buttons.items()):
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.scale(size / 24, size / 24)
            color = QColor("#ffffff" if button.isChecked() else QT_THEMES[self.owner.theme]["text"])
            pen = QPen(color, 1.8)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            if tool == "rectangle":
                painter.drawRect(3, 4, 18, 16)
            elif tool in ("eraser", "annotation_eraser"):
                path = QPainterPath()
                path.moveTo(3, 14)
                path.lineTo(13, 4)
                path.lineTo(21, 12)
                path.lineTo(12, 21)
                path.lineTo(9, 21)
                path.closeSubpath()
                painter.drawPath(path)
                painter.drawLine(8, 9, 16, 17)
                painter.drawLine(14, 21, 22, 21)
            elif tool == "marker":
                pen.setStyle(Qt.PenStyle.DashLine)
                painter.setPen(pen)
                path = QPainterPath()
                path.moveTo(3, 17)
                path.cubicTo(6, 2, 14, 22, 21, 5)
                painter.drawPath(path)
            elif tool == "window":
                painter.drawRect(3, 8, 18, 8)
                painter.drawLine(3, 12, 21, 12)
            elif tool == "door":
                painter.drawLine(4, 20, 4, 4)
                painter.drawArc(4, 4, 32, 32, 90 * 16, 90 * 16)
                painter.drawLine(3, 20, 21, 20)
            elif tool == "desk":
                path = QPainterPath()
                path.moveTo(3, 4)
                for x, y in ((21, 4), (21, 10), (10, 10), (10, 21), (3, 21)):
                    path.lineTo(x, y)
                path.closeSubpath()
                painter.drawPath(path)
            elif tool == "symbol":
                painter.drawEllipse(2, 2, 20, 20)
                painter.drawLine(8, 8, 16, 16)
                painter.drawLine(8, 16, 16, 8)
            elif tool == "circle":
                painter.drawEllipse(4, 4, 16, 16)
                painter.setBrush(color)
                painter.drawEllipse(11, 11, 2, 2)
                painter.drawLine(12, 12, 18, 7)
            elif tool == "arc":
                path = QPainterPath()
                path.moveTo(3, 18)
                path.cubicTo(3, 0, 21, 0, 21, 18)
                painter.drawPath(path)
                painter.setBrush(color)
                painter.drawEllipse(1, 16, 4, 4)
                painter.drawEllipse(19, 16, 4, 4)
            elif tool == "text":
                font = painter.font()
                font.setPixelSize(21)
                font.setBold(True)
                painter.setFont(font)
                painter.drawText(QRect(0, 0, 24, 24), Qt.AlignmentFlag.AlignCenter, "T")
            elif tool == "edit":
                painter.drawLine(6, 17, 17, 6)
                painter.drawLine(9, 20, 20, 9)
                painter.drawLine(17, 6, 20, 9)
                painter.drawLine(6, 17, 5, 21)
                painter.drawLine(5, 21, 9, 20)
            elif tool == "line":
                painter.drawLine(4, 12, 20, 12)
                painter.setBrush(color)
                painter.drawEllipse(2, 10, 4, 4)
                painter.drawEllipse(18, 10, 4, 4)
            else:
                pen.setStyle(Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.drawRect(3, 3, 14, 14)
                painter.setPen(QPen(color, 1.3))
                painter.setBrush(color)
                arrow = QPainterPath()
                arrow.moveTo(12, 10)
                arrow.lineTo(22, 16)
                arrow.lineTo(18, 17)
                arrow.lineTo(16, 22)
                arrow.closeSubpath()
                painter.drawPath(arrow)
            painter.end()
            button.setIcon(QIcon(pixmap))
            button.setIconSize(QSize(size, size))

    def edit_selected_text(self):
        if self.active_tool == "annotation_select":
            self.controller.annotation.edit()
            return
        if self.active_tool in ("marker", "door", "window", *FREE_ANNOTATIONS):
            self.controller.annotation.configure(self.active_tool)
            return
        indices = self.controller.selection.selected_labels
        if len(indices) == 1:
            self.controller.text.edit(indices[0])
        elif len(self.controller.selection.selected_curves) == 1:
            self.controller.curve.edit(self.controller.selection.selected_curves[0])

    def toggle_grid_snap(self, checked):
        if self.active_tool == "marker":
            self.controller.annotation.marker_grid = checked
        self.update_snap_icon()
        if checked:
            self.owner.set_floorplan_grid_enabled(True, show_status=False)
        self.controller.refresh_snap()

    def choose_color(self):
        color = choose_plan_color(self.stroke_color, self.owner, self.owner.tr("blank_tool_color"))
        if color.isValid():
            self.stroke_color = color
            save_tool_colors("structure", dict(color=color.name()))
            self.update_color_icon()

    def update_color_icon(self):
        pixmap = QPixmap(self.owner.spx(18), self.owner.spx(18))
        pixmap.fill(self.stroke_color)
        self.color_button.setIcon(QIcon(pixmap))
        self.color_button.setIconSize(QSize(self.owner.spx(18), self.owner.spx(18)))

    def update_snap_icon(self):
        size = self.owner.spx(18)
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        color = "#FFFFFF" if self.snap_button.isChecked() else QT_THEMES[self.owner.theme]["text"]
        painter.setPen(QPen(QColor(color), max(1, self.owner.spx(1))))
        for position in (1, size // 3, size * 2 // 3, size - 2):
            painter.drawLine(position, 1, position, size - 2)
            painter.drawLine(1, position, size - 2, position)
        painter.end()
        self.snap_button.setIcon(QIcon(pixmap))
        self.snap_button.setIconSize(QSize(size, size))

    def update_history_icons(self):
        size = self.owner.spx(20)
        palette = QT_THEMES[self.owner.theme]
        for button, mirrored in ((self.undo_button, False), (self.redo_button, True)):
            icon = QIcon()
            for mode, color in ((QIcon.Mode.Normal, palette["text"]), (QIcon.Mode.Disabled, palette["muted"])):
                pixmap = QPixmap(size, size)
                pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.scale(size / 24, size / 24)
                if mirrored:
                    painter.translate(24, 0)
                    painter.scale(-1, 1)
                pen = QPen(QColor(color), 2)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                path = QPainterPath()
                path.moveTo(19, 19)
                path.cubicTo(22, 9, 12, 5, 5, 11)
                path.moveTo(5, 5)
                path.lineTo(5, 11)
                path.lineTo(11, 11)
                painter.drawPath(path)
                painter.end()
                icon.addPixmap(pixmap, mode)
            button.setIcon(icon)
            button.setIconSize(QSize(size, size))

    def position_controls(self):
        viewport = self.parentWidget()
        margin = self.owner.spx(12)
        size = self.toggle_button.sizeHint()
        bottom = viewport.height() - margin
        # The expanded point table overlays the map: keep controls above it.
        points = getattr(self.owner, "points_overlay", None)
        if points is not None and self.owner.points_panel_expanded and not points.isHidden():
            if self.open:
                self.open = False
                self.snap_button.setEnabled(False)
                self.controller.cancel()
                self.owner.floorplan_view.design_mode_active = False
                self.owner.floorplan_view.viewport().setCursor(Qt.CursorShape.ArrowCursor)
                self.toggle_button.setChecked(False)
                self.escape_shortcut.setEnabled(False)
                self.hide()
            top = viewport.mapFromGlobal(points.mapToGlobal(QPoint(0, 0))).y()
            bottom = min(bottom, top - margin)
        self.toggle_button.setGeometry(margin, max(margin, bottom - size.height()), size.width(), size.height())
        margins = self.layout().contentsMargins()
        width = max(self.owner.spx(350), max(self.tool_row.sizeHint().width(), self.annotation_row.sizeHint().width(), self.action_row.sizeHint().width())
                    + margins.left() + margins.right())
        if "\n" in self.note.text():
            width = max(width, max(self.note.fontMetrics().horizontalAdvance(row) for row in self.note.text().splitlines())
                        + margins.left() + margins.right() + self.owner.spx(8))
        note_width = width - margins.left() - margins.right()
        self.note.setFixedWidth(note_width)
        # heightForWidth includes minimumHeight: remove the previous fixed height
        # before measuring, otherwise each positioning pass grows the palette.
        self.note.setMinimumHeight(0)
        self.note.setMaximumHeight(16777215)
        text_height = max(self.note.heightForWidth(note_width), self.note.fontMetrics().boundingRect(
            QRect(0, 0, note_width, 10000), Qt.TextFlag.TextWordWrap, self.note.text()).height())
        self.note.setFixedHeight(text_height + self.owner.spx(4))
        self.layout().invalidate()
        self.setFixedSize(width, self.layout().sizeHint().height())
        self.move(margin, max(margin, self.toggle_button.y() - margin - self.height()))
        self.toggle_button.raise_()
        if self.open:
            self.raise_()

    def eventFilter(self, source, event):
        if source is self.parentWidget() and event.type() == QEvent.Type.Resize:
            QTimer.singleShot(0, self.position_controls)
        return super().eventFilter(source, event)
