"""Blank-sheet design tools and rectangle gesture coordination."""

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPixmap, QShortcut, QKeySequence, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QColorDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from app_core.constants import DEFAULT_FLOORPLAN_METADATA_KEY, GENERATED_FLOORPLAN_METADATA_KEY
from qt_ui.qt_theme import QT_THEMES
from qt_ui.qt_rectangle_design import RectangleDesignController


class PlanToolsOverlay(QFrame):
    def __init__(self, owner):
        super().__init__(owner.floorplan_view.viewport())
        self.setFont(owner.font())
        self.owner = owner
        self.open = False
        self.active_tool = "rectangle"
        self.stroke_color = QColor("#263238")
        self.setObjectName("boundariesToolbar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*(owner.spx(8) for _ in range(4)))
        layout.setSpacing(owner.spx(7))
        self.header = QLabel()
        layout.addWidget(self.header)
        row = QHBoxLayout()
        self.tool_row = row
        row.setSpacing(owner.spx(4))
        self.rectangle_button = owner.create_boundaries_tool_button("square.png", "blank_tool_rectangle")
        self.line_button = owner.create_boundaries_text_button("", "blank_tool_line")
        self.eraser_button = owner.create_boundaries_tool_button("eraser.png", "blank_tool_eraser")
        self.select_button = owner.create_boundaries_text_button("", "blank_tool_select")
        self.undo_button = owner.create_boundaries_text_button("", "blank_tool_undo")
        self.redo_button = owner.create_boundaries_text_button("", "blank_tool_redo")
        for button in (self.rectangle_button, self.line_button, self.eraser_button, self.select_button):
            button.setEnabled(False)
            row.addWidget(button)
        layout.addLayout(row)
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
        actions.addWidget(self.snap_button)
        actions.addWidget(self.color_button)
        row.addStretch()
        actions.addStretch()
        layout.addLayout(actions)
        self.note = QLabel()
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        self.toggle_button = QPushButton(self.parentWidget())
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
        self.select_button.setCheckable(True)
        self.rectangle_button.clicked.connect(self.select_rectangle)
        self.eraser_button.clicked.connect(lambda: self.select_tool("eraser"))
        self.line_button.clicked.connect(lambda: self.select_tool("line"))
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
                    any(session.metadata.get(key) == "1" for key in
                        (DEFAULT_FLOORPLAN_METADATA_KEY, GENERATED_FLOORPLAN_METADATA_KEY)))

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
        for button, key in ((self.rectangle_button, "rectangle"), (self.line_button, "line"),
                            (self.eraser_button, "eraser"), (self.select_button, "select"),
                            (self.undo_button, "undo"), (self.redo_button, "redo"),
                            (self.snap_button, "snap"), (self.color_button, "color")):
            text = tr("blank_tool_" + key)
            button.setToolTip(text)
            button.setAccessibleName(text)
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
        if not self.controller.cancel():
            self.set_open(False)

    def select_rectangle(self):
        self.select_tool("rectangle")

    def select_tool(self, tool):
        self.controller.cancel()
        self.active_tool = tool
        self.update_tool_state()
        self.position_controls()

    def update_tool_state(self):
        for tool, button in (("rectangle", self.rectangle_button), ("line", self.line_button),
                             ("eraser", self.eraser_button), ("select", self.select_button)):
            button.setEnabled(self.open)
            button.setChecked(self.open and self.active_tool == tool)
        self.snap_button.setEnabled(self.open and self.active_tool != "eraser")
        self.color_button.setEnabled(self.open and self.active_tool in ("rectangle", "line"))
        key = {"rectangle": "blank_tools_note", "line": "line_tools_note",
               "eraser": "eraser_tools_note", "select": "selection_tools_note"}[self.active_tool]
        self.note.setText(self.owner.tr(key))
        self.update_tool_icons()

    def update_tool_icons(self):
        size = self.owner.spx(20)
        for tool, button in (("line", self.line_button), ("select", self.select_button)):
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.scale(size / 24, size / 24)
            color = QColor("#ffffff" if button.isChecked() else QT_THEMES[self.owner.theme]["text"])
            pen = QPen(color, 1.8)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            if tool == "line":
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

    def toggle_grid_snap(self, checked):
        self.update_snap_icon()
        if checked:
            self.owner.set_floorplan_grid_enabled(True, show_status=False)
        self.controller.refresh_snap()

    def choose_color(self):
        color = QColorDialog.getColor(self.stroke_color, self.owner, self.owner.tr("blank_tool_color"))
        if color.isValid():
            self.stroke_color = color
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
        width = max(self.owner.spx(270), max(self.tool_row.sizeHint().width(), self.action_row.sizeHint().width())
                    + margins.left() + margins.right())
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
