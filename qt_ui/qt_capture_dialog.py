"""Guided capture UI; measurements stay provisional until explicitly saved."""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QScrollArea, QStackedWidget, QToolButton, QVBoxLayout, QWidget,
)

from qt_ui.qt_theme import QT_THEMES
from qt_ui.scaling import widget_px
from survey.measurement_presentation import measurement_cards
from wifi.adapters import adapter_name

PREPARATION_SECONDS = 2


class GuidedCaptureDialog(QDialog):
    start_requested = Signal()
    save_requested = Signal()
    retry_requested = Signal()
    discard_requested = Signal()

    def __init__(self, app, x, y, adapter=None, *, read_only=False):
        super().__init__(app)
        self.app, self.read_only = app, read_only
        self.phase = "review" if read_only else "prepare"
        self.remaining = PREPARATION_SECONDS
        self.setObjectName("guidedCapture")
        self.setWindowTitle(self.text("details" if read_only else "title"))
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(widget_px(app, 680), widget_px(app, 420))
        self.setMinimumWidth(widget_px(app, 520))
        screen = self.screen()
        if screen:
            self.resize(min(self.width(), int(screen.availableGeometry().width() * .9)),
                        min(self.height(), int(screen.availableGeometry().height() * .88)))
        outer = QVBoxLayout(self)
        outer.setContentsMargins(*(widget_px(app, 22) for _ in range(4)))
        outer.setSpacing(widget_px(app, 14))
        self.steps = QLabel()
        self.steps.setObjectName("captureSteps")
        outer.addWidget(self.steps)
        self.heading = QLabel(self.text("position", x=x, y=y))
        self.heading.setObjectName("captureHeading")
        outer.addWidget(self.heading)
        receiver = QLabel(adapter_name(adapter or {}))
        receiver.setTextFormat(Qt.TextFormat.PlainText)
        receiver.setObjectName("captureMuted")
        receiver.setWordWrap(True)
        outer.addWidget(receiver)
        self.stack = QStackedWidget()
        outer.addWidget(self.stack, 1)

        collecting = QWidget()
        collecting_layout = QVBoxLayout(collecting)
        collecting_layout.setContentsMargins(0, 0, 0, 0)
        collecting_layout.addStretch(1)
        self.stage_title = QLabel(self.text("hold"))
        self.stage_title.setObjectName("captureStageTitle")
        self.stage_title.setWordWrap(True)
        collecting_layout.addWidget(self.stage_title)
        self.counter = QLabel()
        self.counter.setObjectName("captureCounter")
        collecting_layout.addWidget(self.counter)
        self.hold_hint = QLabel(self.text("hold_hint"))
        self.hold_hint.setWordWrap(True)
        collecting_layout.addWidget(self.hold_hint)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setMinimumHeight(widget_px(app, 10))
        collecting_layout.addWidget(self.progress)
        self.progress_detail = QLabel()
        self.progress_detail.setWordWrap(True)
        self.progress_detail.setObjectName("captureMuted")
        collecting_layout.addWidget(self.progress_detail)
        collecting_layout.addStretch(1)
        self.stack.addWidget(collecting)

        review_scroll = QScrollArea()
        review_scroll.setWidgetResizable(True)
        review_scroll.setFrameShape(QFrame.Shape.NoFrame)
        review = QWidget()
        review_layout = QVBoxLayout(review)
        review_layout.setContentsMargins(0, 0, widget_px(app, 6), 0)
        review_layout.setSpacing(widget_px(app, 12))
        self.review_title = QLabel()
        self.review_title.setObjectName("captureStageTitle")
        self.review_title.setWordWrap(True)
        review_layout.addWidget(self.review_title)
        self.cards = []
        for _ in range(3):
            card = QFrame()
            card.setObjectName("measurementCard")
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(*(widget_px(app, 13) for _ in range(4)))
            card_layout.setSpacing(widget_px(app, 18))
            main = QVBoxLayout()
            main.setSpacing(widget_px(app, 5))
            title = QLabel()
            title.setObjectName("captureMuted")
            title.setWordWrap(True)
            value = QLabel()
            value.setObjectName("measurementValue")
            value.setWordWrap(True)
            detail = QLabel()
            detail.setObjectName("measurementDetail")
            detail.setWordWrap(True)
            detail.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            for label in (title, value, detail):
                label.setTextFormat(Qt.TextFormat.PlainText)
            main.addStretch(1)
            main.addWidget(title)
            main.addWidget(value)
            main.addStretch(1)
            card_layout.addLayout(main, 2)
            separator = QFrame()
            separator.setObjectName("measurementDivider")
            separator.setFixedWidth(widget_px(app, 1))
            card_layout.addWidget(separator)
            card_layout.addWidget(detail, 3)
            self.cards.append((card, title, value, detail))
            review_layout.addWidget(card)
        self.review_hint = QLabel(self.text("review_hint"))
        self.review_hint.setWordWrap(True)
        self.review_hint.setObjectName("captureMuted")
        review_layout.addWidget(self.review_hint)
        self.details_toggle = QToolButton()
        self.details_toggle.setText(self.text("details"))
        self.details_toggle.setCheckable(True)
        self.details_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.details_toggle.setArrowType(Qt.ArrowType.RightArrow)
        review_layout.addWidget(self.details_toggle)
        self.notes_label = QLabel()
        self.notes_label.setTextFormat(Qt.TextFormat.PlainText)
        self.notes_label.setWordWrap(True)
        self.notes_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.notes_label.hide()
        self.details_toggle.toggled.connect(self.toggle_details)
        review_layout.addWidget(self.notes_label)
        review_layout.addStretch(1)
        review_scroll.setWidget(review)
        self.stack.addWidget(review_scroll)

        buttons = QHBoxLayout()
        self.discard_button = QPushButton(self.text("close" if read_only else "cancel"))
        self.discard_button.clicked.connect(self.reject)
        buttons.addWidget(self.discard_button)
        buttons.addStretch(1)
        self.retry_button = QPushButton(self.text("retry"))
        self.retry_button.clicked.connect(self.retry_requested)
        buttons.addWidget(self.retry_button)
        self.primary_button = QPushButton()
        self.primary_button.setObjectName("capturePrimary")
        self.primary_button.setDefault(True)
        self.primary_button.clicked.connect(self.primary_action)
        buttons.addWidget(self.primary_button)
        for button in (self.discard_button, self.retry_button, self.primary_button):
            button.setAutoDefault(True)
        outer.addLayout(buttons)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.prepare_tick)
        self.apply_style()
        self.set_phase(self.phase)

    def text(self, key, **kw):
        return self.app.tr("measurement_" + key, **kw)

    def apply_style(self):
        p = QT_THEMES[self.app.theme]
        s = lambda value: widget_px(self.app, value)
        self.setStyleSheet(f"""
            QDialog#guidedCapture {{ background: {p['bg']}; }}
            QLabel {{ background: transparent; color: {p['text']}; }}
            QLabel#captureHeading {{ font-size: {s(21)}px; font-weight: 700; }}
            QLabel#captureStageTitle {{ font-size: {s(18)}px; font-weight: 700; }}
            QLabel#captureCounter {{ font-size: {s(29)}px; color: {p['metric_info']}; font-weight: 700; padding: {s(10)}px 0; }}
            QLabel#captureSteps, QLabel#captureMuted {{ color: {p['muted']}; }}
            QFrame#measurementCard {{ background: {p['panel']}; border: 1px solid {p['border']}; border-radius: {s(9)}px; }}
            QLabel#measurementValue {{ font-size: {s(17)}px; font-weight: 700; }}
            QLabel#measurementDetail {{ font-size: {s(12)}px; color: {p['muted']}; }}
            QFrame#measurementDivider {{ background: {p['border']}; border: 0; }}
            QLabel#measurementValue[tone="good"] {{ color: {p['metric_good']}; }}
            QLabel#measurementValue[tone="warning"] {{ color: {p['metric_warning']}; }}
            QLabel#measurementValue[tone="danger"] {{ color: {p['metric_danger']}; }}
            QPushButton {{ min-width: 0; padding: {s(9)}px {s(13)}px; }}
            QPushButton#capturePrimary {{ background: {p['metric_info']}; color: white; font-weight: 700; }}
            QPushButton#capturePrimary:disabled {{ background: {p['panel_alt']}; color: {p['muted']}; }}
            QPushButton:focus {{ border: 2px solid {p['metric_info']}; }}
            QProgressBar {{ background: {p['panel_alt']}; border: 0; border-radius: {s(5)}px; }}
            QProgressBar::chunk {{ background: {p['metric_info']}; border-radius: {s(5)}px; }}
            QToolButton {{ color: {p['text']}; border: 0; padding: {s(6)}px 0; }}
        """)

    def set_phase(self, phase):
        self.phase = phase
        active = 3 if phase in {"review", "error"} else 2 if phase in {"scanning", "cancelling"} else 1
        self.steps.setText("  ›  ".join(("● " if index == active else "") + self.text(key)
                                      for index, key in enumerate(("prepare", "collect", "review"), 1)))
        self.stack.setCurrentIndex(1 if phase == "review" else 0)
        self.retry_button.setVisible(phase in {"review", "error"} and not self.read_only)
        self.primary_button.setVisible(phase in {"prepare", "review"} and not self.read_only)
        self.primary_button.setText(self.text("start" if phase == "prepare" else "save"))
        self.discard_button.setEnabled(phase != "cancelling")
        if phase == "prepare":
            self.primary_button.setEnabled(True)
            self.remaining = PREPARATION_SECONDS
            self.stage_title.setText(self.text("hold"))
            self.counter.setText(self.text("countdown", seconds=self.remaining))
            self.hold_hint.show()
            self.progress.hide()
            self.progress_detail.clear()
        QTimer.singleShot(0, self.fit_phase_size)

    def fit_phase_size(self):
        """Size for the current phase rather than the tallest stacked page."""
        screen = self.screen()
        available = screen.availableGeometry() if screen else None
        target = widget_px(self.app, 560 if self.phase == "review" else 420)
        if available:
            target = min(target, int(available.height() * .88))
        center = self.frameGeometry().center()
        self.resize(self.width(), target)
        if self.isVisible() and available:
            frame = self.frameGeometry()
            frame.moveCenter(center)
            self.move(max(available.left(), min(frame.left(), available.right() - frame.width() + 1)),
                      max(available.top(), min(frame.top(), available.bottom() - frame.height() + 1)))

    def begin_preparation(self):
        self.set_phase("prepare")
        self.timer.start()

    def prepare_tick(self):
        self.remaining -= 1
        if self.remaining <= 0:
            self.primary_action()
        else:
            self.counter.setText(self.text("countdown", seconds=self.remaining))

    def primary_action(self):
        if self.phase == "prepare":
            self.timer.stop()
            self.set_phase("scanning")
            self.stage_title.setText(self.text("collect"))
            self.counter.clear()
            self.progress.setRange(0, 0)
            self.progress.show()
            self.start_requested.emit()
        elif self.phase == "review":
            self.save_requested.emit()

    def update_progress(self, info):
        if self.phase != "scanning":
            return
        self.counter.setText(self.text("attempt", attempt=info["attempt"], total=info["total"]))
        self.progress.setRange(0, info["total"])
        self.progress.setValue(info.get("completed", 0))
        self.progress_detail.setText(self.text("progress", completed=info.get("successful_reads", 0), total=info["total"], samples=info.get("fresh_samples", 0)))

    def show_review(self, assessment, scope=()):
        self.timer.stop()
        self.set_phase("review")
        self.primary_button.setEnabled(assessment.can_save)
        self.review_title.setText(self.text("ready" if assessment.collection == "verified" and assessment.stability != "variable" else "check"))
        for widgets, data in zip(self.cards, measurement_cards(assessment, self.app.tr)):
            card, title, value, detail = widgets
            title.setText(data["title"])
            value.setText(data["value"])
            value.setProperty("tone", data["tone"])
            value.style().unpolish(value)
            value.style().polish(value)
            detail.setText(data["detail"])
        notes = [self.text("scope", ssids=", ".join(sorted(scope)))] if scope else []
        notes.extend(self.text("note_" + note) for note in assessment.notes)
        self.notes_label.setText("\n\n".join(notes))
        self.details_toggle.setVisible(bool(notes))

    def toggle_details(self, expanded):
        self.notes_label.setVisible(expanded)
        self.details_toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)

    def show_error(self, message):
        self.timer.stop()
        self.set_phase("error")
        self.stage_title.setText(self.text("failure"))
        self.counter.clear()
        self.hold_hint.hide()
        self.progress.hide()
        self.progress_detail.setText(message)

    def show_cancelling(self):
        self.timer.stop()
        self.set_phase("cancelling")
        self.stage_title.setText(self.text("cancelling"))

    def reject(self):
        self.timer.stop()
        if self.read_only:
            super().reject()
        elif self.phase != "cancelling":
            self.discard_requested.emit()

    def closeEvent(self, event):
        if self.read_only:
            super().closeEvent(event)
        else:
            self.reject()
            event.ignore()

    def finish(self, saved=False):
        self.timer.stop()
        super().done(QDialog.DialogCode.Accepted if saved else QDialog.DialogCode.Rejected)
