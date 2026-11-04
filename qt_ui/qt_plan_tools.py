"""Blank-plan toolbar shell. Geometry editing is deliberately not enabled yet."""

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPixmap, QShortcut, QKeySequence, QPainter, QPen
from PySide6.QtWidgets import QColorDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QStyle, QVBoxLayout

from app_core.constants import DEFAULT_FLOORPLAN_METADATA_KEY, GENERATED_FLOORPLAN_METADATA_KEY
from qt_ui.qt_theme import QT_THEMES


class PlanToolsOverlay(QFrame):
    def __init__(self, owner):
        super().__init__(owner.floorplan_view.viewport())
        self.setFont(owner.font())
        self.owner = owner
        self.open = False
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
        self.eraser_button = owner.create_boundaries_tool_button("eraser.png", "blank_tool_eraser")
        self.undo_button = owner.create_boundaries_text_button("", "blank_tool_undo")
        self.redo_button = owner.create_boundaries_text_button("", "blank_tool_redo")
        self.undo_button.setIcon(owner.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        self.redo_button.setIcon(owner.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        # No enabled control should pretend to draw or erase before geometry exists.
        for button in (self.rectangle_button, self.eraser_button, self.undo_button, self.redo_button):
            button.setEnabled(False)
            row.addWidget(button)
        self.snap_button = owner.create_boundaries_text_button("", "blank_tool_snap")
        self.snap_button.setCheckable(True)
        self.snap_button.setChecked(True)
        self.snap_button.toggled.connect(self.update_snap_icon)
        self.color_button = owner.create_boundaries_text_button("", "blank_tool_color")
        self.color_button.clicked.connect(self.choose_color)
        row.addWidget(self.snap_button)
        row.addWidget(self.color_button)
        layout.addLayout(row)
        self.note = QLabel()
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        self.toggle_button = QPushButton(self.parentWidget())
        self.toggle_button.setObjectName("appBarToggleButton")
        self.toggle_button.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation, True)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setMinimumHeight(owner.spx(34))
        self.toggle_button.clicked.connect(self.set_open)
        self.escape_shortcut = QShortcut(QKeySequence("Esc"), owner)
        self.escape_shortcut.activated.connect(lambda: self.set_open(False))
        self.parentWidget().installEventFilter(self)
        self.sync()

    def available(self):
        session = self.owner.session
        return bool(session and self.owner.floorplan_view.has_floorplan() and
                    any(session.metadata.get(key) == "1" for key in
                        (DEFAULT_FLOORPLAN_METADATA_KEY, GENERATED_FLOORPLAN_METADATA_KEY)))

    def sync(self):
        tr = self.owner.tr
        self.toggle_button.setText(tr("blank_tools"))
        self.toggle_button.setToolTip(tr("blank_tools_hint"))
        self.header.setText(tr("blank_tools"))
        self.note.setText(tr("blank_tools_note"))
        for button, key in ((self.rectangle_button, "rectangle"), (self.eraser_button, "eraser"),
                            (self.undo_button, "undo"), (self.redo_button, "redo"),
                            (self.snap_button, "snap"), (self.color_button, "color")):
            text = tr("blank_tool_" + key)
            button.setToolTip(text)
            button.setAccessibleName(text)
        self.update_color_icon()
        self.update_snap_icon()
        available = self.available()
        if not available or self.owner.scan_in_progress or self.owner.tabs.currentIndex() != 0:
            self.set_open(False)
        self.toggle_button.setVisible(available)
        self.toggle_button.setEnabled(available and not self.owner.scan_in_progress)
        self.position_controls()

    def set_open(self, opened):
        self.open = bool(opened and self.available() and not self.owner.scan_in_progress)
        if self.open:
            if self.owner.points_panel_expanded:
                self.owner.toggle_points_panel()
            self.owner.set_boundaries_mode_enabled(False, show_status=False)
        self.toggle_button.setChecked(self.open)
        self.owner.floorplan_view.design_mode_active = self.open
        self.escape_shortcut.setEnabled(self.open)
        self.setVisible(self.open)
        self.position_controls()

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
                self.owner.floorplan_view.design_mode_active = False
                self.toggle_button.setChecked(False)
                self.escape_shortcut.setEnabled(False)
                self.hide()
            top = viewport.mapFromGlobal(points.mapToGlobal(QPoint(0, 0))).y()
            bottom = min(bottom, top - margin)
        self.toggle_button.setGeometry(margin, max(margin, bottom - size.height()), size.width(), size.height())
        margins = self.layout().contentsMargins()
        width = max(self.owner.spx(240), self.tool_row.sizeHint().width() + margins.left() + margins.right())
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
