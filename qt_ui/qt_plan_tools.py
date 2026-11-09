"""Blank-sheet design tools and rectangle gesture coordination."""

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QShortcut, QKeySequence
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
                              QCheckBox, QToolButton, QSizePolicy, QScrollArea, QWidget)

from survey.plan_mode import is_drawn_plan
from qt_ui.qt_rectangle_design import RectangleDesignController
from survey.plan_objects import FREE_ANNOTATIONS, object_is_round
from app_core.plan_preferences import tool_colors, save_tool_colors
from qt_ui.qt_plan_colors import choose_plan_color
from qt_ui.qt_plan_icons import plan_tool_icon


class PlanToolsOverlay(QFrame):
    def __init__(self, owner):
        super().__init__(owner.floorplan_view.viewport())
        self.setProperty("fixedViewportOverlay", True)
        self.owner = owner
        self.open = False
        self.active_tool = None
        self.stroke_color = QColor(tool_colors("structure").get("color", "#263238"))
        self.setObjectName("designTools")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*(owner.spx(12) for _ in range(4)))
        layout.setSpacing(owner.spx(7))
        header_row = QHBoxLayout()
        self.header = QLabel()
        self.header.setObjectName("designTitle")
        header_row.addWidget(self.header)
        header_row.addStretch()
        self.close_button = QToolButton()
        self.close_button.setObjectName("designClose")
        self.close_button.setFixedSize(owner.spx(26), owner.spx(26))
        self.close_button.clicked.connect(lambda: self.set_open(False))
        header_row.addWidget(self.close_button)
        layout.addLayout(header_row)
        self.scroll = QScrollArea()
        self.scroll.setObjectName("designToolsScroll")
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setMinimumSize(0, 0)
        self.content = QWidget()
        self.content.setObjectName("designToolsContent")
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll)
        layout = QVBoxLayout(self.content)
        self.content_layout = layout
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(owner.spx(6))
        self.structure_heading = QLabel()
        layout.addWidget(self.structure_heading)
        row = QHBoxLayout()
        self.tool_row = row
        row.setSpacing(owner.spx(4))
        self.rectangle_button = self.create_tool_button("blank_tool_rectangle")
        self.line_button = self.create_tool_button("blank_tool_line")
        self.circle_button = self.create_tool_button("blank_tool_circle")
        self.arc_button = self.create_tool_button("blank_tool_arc")
        self.text_button = self.create_tool_button("blank_tool_text")
        self.eraser_button = self.create_tool_button("blank_tool_eraser")
        self.select_button = self.create_tool_button("blank_tool_select")
        self.wall_button = self.create_tool_button("wall_title")
        from qt_ui.qt_wall_sides import edit_wall_sides
        self.wall_button.clicked.connect(lambda: edit_wall_sides(owner))
        self.undo_button = self.create_tool_button("blank_tool_undo")
        self.redo_button = self.create_tool_button("blank_tool_redo")
        for button in (self.rectangle_button, self.line_button, self.circle_button, self.arc_button, self.eraser_button, self.select_button):
            button.setEnabled(False)
            row.addWidget(button)
        layout.addLayout(row)
        row.insertWidget(row.count(), self.wall_button)
        self.annotation_heading = QLabel()
        layout.addWidget(self.annotation_heading)
        annotation_row = QHBoxLayout()
        self.annotation_row = annotation_row
        annotation_row.setSpacing(owner.spx(4))
        self.annotation_buttons = {}
        for tool in ("marker", "window", "door", *FREE_ANNOTATIONS, "annotation_eraser", "annotation_select"):
            button = self.create_tool_button("annotation_" + {"annotation_select": "select", "annotation_eraser": "eraser"}.get(tool, tool))
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
        self.snap_button = self.create_tool_button("blank_tool_snap")
        self.snap_button.setCheckable(True)
        self.snap_button.setChecked(False)
        self.snap_button.setEnabled(False)
        self.color_button = self.create_tool_button("blank_tool_color")
        self.color_button.clicked.connect(self.choose_color)
        self.edit_text_button = self.create_tool_button("plan_text_edit")
        self.edit_text_button.clicked.connect(self.edit_selected_text)
        actions.addWidget(self.snap_button)
        actions.addWidget(self.color_button)
        actions.addWidget(self.edit_text_button)
        row.addStretch()
        actions.addStretch()
        layout.addLayout(actions)
        self.include_annotations = QCheckBox(owner.tr('selection_include_annotations'))
        self.include_annotations.setChecked(True)
        self.include_annotations.toggled.connect(self.selection_scope_changed)
        layout.addWidget(self.include_annotations)
        self.active_label = QLabel()
        self.active_label.setObjectName("designActiveTool")
        layout.addWidget(self.active_label)
        self.note = QLabel()
        self.note.setObjectName("designHint")
        self.note.setTextFormat(Qt.TextFormat.PlainText)
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

    def create_tool_button(self, tooltip_key):
        button = QToolButton()
        button.setObjectName("designToolButton")
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        button.setToolTip(self.owner.tr(tooltip_key))
        return button

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
        self.close_button.setToolTip(tr("close"))
        self.close_button.setAccessibleName(tr("close"))
        self.close_button.setIcon(self.icon("close", 16))
        self.close_button.setIconSize(QSize(self.owner.spx(16), self.owner.spx(16)))
        self.toggle_button.setIcon(self.icon("edit", 18))
        self.toggle_button.setIconSize(QSize(self.owner.spx(18), self.owner.spx(18)))
        self.scroll.setAccessibleName(tr("blank_tools"))
        self.structure_heading.setText(tr("annotation_structure"))
        self.annotation_heading.setText(tr("annotation_group"))
        self.actions_heading.setText(tr("annotation_controls"))
        for heading in (self.structure_heading, self.annotation_heading, self.actions_heading):
            heading.setObjectName("designSection")
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
            self.active_tool = None
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
        if self.active_tool is not None:
            self.select_tool(None)
        else:
            self.set_open(False)

    def selection_scope_changed(self):
        self.controller.cancel()
        self.update_tool_state()
        self.position_controls()

    def select_rectangle(self):
        self.select_tool("rectangle")

    def select_tool(self, tool):
        if tool is not None and not self.controller.editable():
            return
        self.controller.cancel()
        if tool in ("marker", "door", "window", *FREE_ANNOTATIONS) and not self.controller.annotation.configure(tool):
            self.update_tool_state()
            return
        self.active_tool = tool
        self.update_tool_state()
        self.position_controls()

    def update_tool_state(self):
        shared = self.include_annotations.isChecked()
        self.include_annotations.setText(self.owner.tr('selection_include_annotations'))
        self.include_annotations.setVisible(self.open and self.active_tool == 'select')
        self.eraser_button.setToolTip(self.owner.tr("structure_eraser"))
        self.eraser_button.setAccessibleName(self.owner.tr("structure_eraser"))
        self.select_button.setToolTip(self.owner.tr('selection_shared' if shared else 'annotation_select_structure'))
        self.select_button.setAccessibleName(self.owner.tr('selection_shared' if shared else 'annotation_select_structure'))
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
        self.snap_button.setAccessibleName(self.owner.tr("blank_tool_snap"))
        self.color_button.setEnabled(self.open and self.active_tool in ("rectangle", "line", "circle", "arc"))
        selection = self.controller.selection
        self.wall_button.setEnabled(self.open and self.controller.editable() and self.active_tool == "select"
                                    and not selection.moving and not self.controller.rotation.active
                                    and bool(selection.selected or selection.selected_curves))
        self.wall_button.setToolTip(self.owner.tr("wall_title"))
        self.wall_button.setAccessibleName(self.owner.tr("wall_title"))
        curve_edit = len(selection.selected_curves) == 1 and not (selection.selected or selection.selected_labels or selection.selected_annotations)
        annotation_edit = len(selection.selected_annotations) == 1 and not (selection.selected or selection.selected_labels or selection.selected_curves)
        self.edit_text_button.setEnabled(self.open and self.active_tool == "select"
                                         and (len(selection.selected_labels) == 1 or curve_edit or annotation_edit)
                                         and not selection.moving)
        if self.active_tool in ("marker", "door", "window", *FREE_ANNOTATIONS, "annotation_select"):
            a = self.controller.annotation
            self.edit_text_button.setEnabled(self.open and not a.moving and (self.active_tool != "annotation_select" or len(a.selected) + len(a.selected_labels) == 1))
        edit_text = self.owner.tr('annotation_properties' if annotation_edit else "curve_edit" if curve_edit else "plan_text_edit")
        if self.active_tool in ("marker", "door", "window", *FREE_ANNOTATIONS, "annotation_select"):
            edit_text = self.owner.tr("annotation_properties")
        self.edit_text_button.setToolTip(edit_text)
        self.edit_text_button.setAccessibleName(edit_text)
        key = {"rectangle": "blank_tools_note", "line": "line_tools_note",
               "circle": "circle_tools_note", "arc": "arc_tools_note",
               "eraser": "eraser_tools_note", "select": "selection_tools_note", "text": "text_tools_note",
               "marker": "annotation_marker_note", "door": "annotation_place_note", "window": "annotation_place_note",
               "desk": "object_place_note", "symbol": "object_place_note",
               "annotation_select": "annotation_selection_note", "annotation_eraser": "annotation_eraser_note",None:'design_choose_tool'}[self.active_tool]
        if self.active_tool == 'select' and shared:
            key = 'selection_shared_note'
        template = self.controller.annotation.templates.get(self.active_tool)
        if self.active_tool in FREE_ANNOTATIONS and template and object_is_round(template):
            key = "object_round_note"
        caption = self.owner.tr("design_caption_" + self.active_tool) if self.active_tool else self.owner.tr("design_no_tool")
        self.active_label.setText(self.owner.tr("design_active_tool", tool=caption))
        self.note.setText(self.owner.tr(key) + (" " + self.owner.tr("axis_lock_hint")
                                              if self.active_tool in ("line", "arc") else ""))
        self.update_tool_icons()
        if self.open:
            self.owner.floorplan_view.viewport().setCursor(Qt.CursorShape.CrossCursor if self.active_tool is not None else Qt.CursorShape.ArrowCursor)
        if self.owner.session is not None and not self.controller.editable():
            for button in (self.rectangle_button, self.line_button, self.circle_button, self.arc_button,
                           self.text_button, self.eraser_button, self.select_button, self.snap_button,
                           self.color_button, self.edit_text_button, *self.annotation_buttons.values()):
                button.setEnabled(False)
            self.note.setText(self.owner.tr("layer_readonly"))
        if hasattr(self.owner, "layers_panel"):
            self.owner.layers_panel.update_selection()

    def icon(self, tool, size=22, swatch=None):
        return plan_tool_icon(tool, self.owner.theme, self.owner.spx(size),
                              self.devicePixelRatioF(), swatch)

    def update_tool_icons(self):
        for tool, button in (("line", self.line_button), ("select", self.select_button),
                             ("wall", self.wall_button),
                             ("rectangle", self.rectangle_button), ("eraser", self.eraser_button),
                             ("circle", self.circle_button), ("arc", self.arc_button),
                             ("text", self.text_button), ("edit", self.edit_text_button),
                             *self.annotation_buttons.items()):
            button.setIcon(self.icon(tool))
            button.setIconSize(QSize(self.owner.spx(22), self.owner.spx(22)))
            button.setText(self.owner.tr("design_caption_" + tool))

    def edit_selected_text(self):
        if self.active_tool == "annotation_select":
            self.controller.annotation.edit()
            return
        s = self.controller.selection
        if self.active_tool == 'select' and len(s.selected_annotations) == 1 and not(s.selected or s.selected_labels or s.selected_curves):
            s.edit_annotations(s.selected_annotations)
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
        self.color_button.setIcon(self.icon("color", swatch=self.stroke_color.name()))
        self.color_button.setIconSize(QSize(self.owner.spx(22), self.owner.spx(22)))
        self.color_button.setText(self.owner.tr("design_caption_color"))
        self.color_button.setAccessibleName(self.owner.tr("blank_tool_color"))
        self.color_button.setToolTip(self.owner.tr("blank_tool_color") + " · " + self.stroke_color.name())

    def update_snap_icon(self):
        self.snap_button.setIcon(self.icon("snap"))
        self.snap_button.setIconSize(QSize(self.owner.spx(22), self.owner.spx(22)))
        self.snap_button.setText(self.owner.tr("design_caption_snap"))

    def update_history_icons(self):
        for tool, button in (("undo", self.undo_button), ("redo", self.redo_button)):
            button.setIcon(self.icon(tool))
            button.setIconSize(QSize(self.owner.spx(22), self.owner.spx(22)))
            button.setText(self.owner.tr("blank_tool_" + tool))

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
                self.active_tool = None
                self.snap_button.setEnabled(False)
                self.controller.cancel()
                self.owner.floorplan_view.design_mode_active = False
                self.owner.floorplan_view.viewport().setCursor(Qt.CursorShape.ArrowCursor)
                self.toggle_button.setChecked(False)
                self.escape_shortcut.setEnabled(False)
                self.hide()
                self.update_tool_state()
            top = viewport.mapFromGlobal(points.mapToGlobal(QPoint(0, 0))).y()
            bottom = min(bottom, top - margin)
        self.toggle_button.setGeometry(margin, max(margin, bottom - size.height()), size.width(), size.height())
        # A stylesheet/font change invalidates native button hints before Qt
        # necessarily invalidates every nested row. Re-measure those rows now.
        for row in (self.tool_row, self.annotation_row, self.action_row):
            row.invalidate()
        self.content_layout.invalidate()
        margins = self.layout().contentsMargins()
        # Reserve a scrollbar gutter so captions never get clipped when the
        # available map height requires scrolling (large UI scales, short screens).
        gutter = self.owner.spx(16)
        row_width = max(self.tool_row.sizeHint().width(), self.annotation_row.sizeHint().width(), self.action_row.sizeHint().width())
        width = max(self.owner.spx(350), row_width + margins.left() + margins.right() + gutter)
        note_width = width - margins.left() - margins.right() - gutter
        self.content.setMinimumWidth(note_width)
        self.note.setFixedWidth(note_width)
        # heightForWidth includes minimumHeight: remove the previous fixed height
        # before measuring, otherwise each positioning pass grows the palette.
        self.note.setMinimumHeight(0)
        self.note.setMaximumHeight(16777215)
        text_height = max(self.note.heightForWidth(note_width), self.note.fontMetrics().boundingRect(
            QRect(0, 0, note_width, 10000), Qt.TextFlag.TextWordWrap, self.note.text()).height())
        self.note.setFixedHeight(text_height + self.owner.spx(4))
        self.content_layout.invalidate()
        content_height = self.content_layout.sizeHint().height()
        self.content.setMinimumHeight(content_height)
        header_height = max(self.header.sizeHint().height(), self.close_button.height())
        desired_height = (content_height + header_height + self.layout().spacing()
                          + margins.top() + margins.bottom() + 2 * self.frameWidth())
        available_height = max(header_height + margins.top() + margins.bottom(), self.toggle_button.y() - 2 * margin)
        self.setFixedSize(width, min(desired_height, available_height))
        self.layout().activate()
        self.content_layout.activate()
        self.move(margin, max(margin, self.toggle_button.y() - margin - self.height()))
        self.toggle_button.raise_()
        if self.open:
            self.raise_()

    def eventFilter(self, source, event):
        if source is self.parentWidget() and event.type() == QEvent.Type.Resize:
            QTimer.singleShot(0, self.position_controls)
        return super().eventFilter(source, event)
