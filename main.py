import sys

try:
    from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal, Slot
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )
except ModuleNotFoundError as exc:
    print("PySide6 is required for main.py. Run: pip install -r requirements.txt")
    raise SystemExit(1) from exc

from app_logging import configure_logging, log_event, log_exception, log_unhandled_exception
from i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, normalize_language, translate


START_LANGUAGE_LABELS = {
    "IT": "Italiano",
    "EN": "English",
}


class AppImportWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    @Slot()
    def run(self):
        try:
            log_event("qt app module import start", logger_name="startup")
            from qt_app import WifiHeatmapQtApp
        except Exception as exc:
            log_exception("qt app module import failed", exc, logger_name="startup")
            self.failed.emit(str(exc))
            return

        log_event("qt app module import done", logger_name="startup")
        self.finished.emit(WifiHeatmapQtApp)


class StartWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.language = DEFAULT_LANGUAGE
        self.app_class = None
        self.workspace_window = None
        self.load_thread = None
        self.load_worker = None
        self.load_error = None
        self.close_after_load = False

        self.setObjectName("startWindow")
        self.setMinimumSize(1100, 720)
        self.resize(1320, 820)

        self.build_ui()
        self.apply_styles()
        self.retranslate()
        self.set_ready(False)
        QTimer.singleShot(0, self.start_async_imports)

    def tr(self, key, **kwargs):
        return translate(self.language, key, **kwargs)

    def build_ui(self):
        page = QWidget()
        page.setObjectName("startPage")
        self.setCentralWidget(page)

        outer = QVBoxLayout(page)
        outer.setContentsMargins(56, 36, 56, 24)
        outer.setSpacing(24)

        top_row = QHBoxLayout()
        top_row.addStretch(1)
        self.language_combo = QComboBox()
        self.language_combo.setObjectName("languageCombo")
        for language_code in SUPPORTED_LANGUAGES:
            self.language_combo.addItem(
                START_LANGUAGE_LABELS.get(language_code, language_code),
                language_code,
            )
        self.language_combo.setCurrentIndex(max(0, self.language_combo.findData(self.language.upper())))
        self.language_combo.currentIndexChanged.connect(self.change_language)
        top_row.addWidget(self.language_combo)
        outer.addLayout(top_row)

        body = QHBoxLayout()
        body.setSpacing(28)
        body.addStretch(1)

        hero = QFrame()
        hero.setObjectName("startHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(40, 38, 40, 34)
        hero_layout.setSpacing(18)

        self.badge = QLabel()
        self.badge.setObjectName("startBadge")
        self.title = QLabel()
        self.title.setObjectName("startTitle")
        self.title.setWordWrap(True)
        self.subtitle = QLabel()
        self.subtitle.setObjectName("startSubtitle")
        self.subtitle.setWordWrap(True)
        hero_layout.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignLeft)
        hero_layout.addWidget(self.title)
        hero_layout.addWidget(self.subtitle)
        hero_layout.addSpacing(14)

        self.workflow_title = QLabel()
        self.workflow_title.setObjectName("startSectionTitle")
        hero_layout.addWidget(self.workflow_title)
        self.workflow_labels = []
        for _index in range(3):
            row = QLabel()
            row.setObjectName("startStep")
            row.setWordWrap(True)
            self.workflow_labels.append(row)
            hero_layout.addWidget(row)
        hero_layout.addStretch(1)

        self.loading_title = QLabel()
        self.loading_title.setObjectName("startSectionTitle")
        self.loading_status = QLabel()
        self.loading_status.setObjectName("startMuted")
        self.loading_progress = QProgressBar()
        self.loading_progress.setTextVisible(False)
        self.loading_progress.setFixedHeight(8)
        hero_layout.addWidget(self.loading_title)
        hero_layout.addWidget(self.loading_status)
        hero_layout.addWidget(self.loading_progress)

        actions = QFrame()
        actions.setObjectName("startActions")
        actions_layout = QVBoxLayout(actions)
        actions_layout.setContentsMargins(32, 34, 32, 32)
        actions_layout.setSpacing(14)

        self.actions_title = QLabel()
        self.actions_title.setObjectName("startSectionTitle")
        self.actions_hint = QLabel()
        self.actions_hint.setObjectName("startMuted")
        self.actions_hint.setWordWrap(True)
        actions_layout.addWidget(self.actions_title)
        actions_layout.addWidget(self.actions_hint)
        actions_layout.addSpacing(14)

        self.new_button = QPushButton()
        self.open_button = QPushButton()
        self.exit_button = QPushButton()
        self.new_button.setObjectName("primaryStartButton")
        self.open_button.setObjectName("secondaryStartButton")
        self.exit_button.setObjectName("secondaryStartButton")
        self.new_button.clicked.connect(self.launch_new_survey)
        self.open_button.clicked.connect(self.launch_open_survey)
        self.exit_button.clicked.connect(self.close)
        for button in (self.new_button, self.open_button, self.exit_button):
            button.setMinimumHeight(50)
            actions_layout.addWidget(button)

        actions_layout.addStretch(1)
        self.ready_note = QLabel()
        self.ready_note.setObjectName("startMuted")
        self.ready_note.setWordWrap(True)
        actions_layout.addWidget(self.ready_note)

        body.addWidget(hero, 3)
        body.addWidget(actions, 2)
        body.addStretch(1)
        outer.addStretch(1)
        outer.addLayout(body)
        outer.addStretch(1)

        self.copyright_label = QLabel()
        self.copyright_label.setObjectName("startFooter")
        self.copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self.copyright_label)

    def apply_styles(self):
        self.setStyleSheet(
            """
            QMainWindow#startWindow, QWidget#startPage {
                background: #eef2f6;
                color: #172033;
                font-family: "Segoe UI";
                font-size: 14px;
            }
            QFrame#startHero, QFrame#startActions {
                background: #ffffff;
                border: 1px solid #d4dce7;
                border-radius: 10px;
            }
            QFrame#startHero {
                min-width: 620px;
            }
            QFrame#startActions {
                min-width: 360px;
                max-width: 430px;
            }
            QLabel#startBadge {
                background: #dff3e7;
                color: #0f6b3b;
                border: 1px solid #b8dfc9;
                border-radius: 6px;
                padding: 7px 12px;
                font-weight: 600;
            }
            QLabel#startTitle {
                color: #111827;
                font-size: 42px;
                font-weight: 800;
            }
            QLabel#startSubtitle {
                color: #516070;
                font-size: 18px;
            }
            QLabel#startSectionTitle {
                color: #162033;
                font-size: 17px;
                font-weight: 700;
            }
            QLabel#startStep {
                color: #263447;
                font-size: 15px;
                padding: 2px 0;
            }
            QLabel#startMuted, QLabel#startFooter {
                color: #64748b;
            }
            QPushButton#primaryStartButton {
                background: #1f6feb;
                color: #ffffff;
                border: 1px solid #1f6feb;
                border-radius: 7px;
                font-size: 15px;
                font-weight: 700;
                padding: 10px 14px;
            }
            QPushButton#primaryStartButton:hover {
                background: #185fc8;
            }
            QPushButton#primaryStartButton:disabled {
                background: #9db9df;
                border-color: #9db9df;
                color: #eef4ff;
            }
            QPushButton#secondaryStartButton {
                background: #ffffff;
                color: #172033;
                border: 1px solid #c9d3df;
                border-radius: 7px;
                font-size: 15px;
                font-weight: 600;
                padding: 10px 14px;
            }
            QPushButton#secondaryStartButton:hover {
                background: #f3f6fa;
            }
            QPushButton#secondaryStartButton:disabled {
                color: #9aa7b5;
                background: #f5f7fa;
            }
            QComboBox {
                background: #ffffff;
                color: #172033;
                border: 1px solid #c9d3df;
                border-radius: 6px;
                padding: 6px 10px;
                min-width: 72px;
            }
            QComboBox#languageCombo {
                background: #1f6feb;
                color: #ffffff;
                border: 1px solid #1f6feb;
                border-radius: 7px;
                padding: 8px 12px;
                min-width: 128px;
                font-weight: 700;
            }
            QComboBox#languageCombo:hover {
                background: #185fc8;
                border-color: #185fc8;
            }
            QComboBox#languageCombo::drop-down {
                border: 0;
                width: 28px;
            }
            QComboBox#languageCombo QAbstractItemView {
                background: #ffffff;
                color: #172033;
                selection-background-color: #dbeafe;
                selection-color: #111827;
                border: 1px solid #c9d3df;
            }
            QProgressBar {
                background: #e3e9f2;
                border: 0;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: #1f6feb;
                border-radius: 4px;
            }
            """
        )

    def retranslate(self):
        self.setWindowTitle(self.tr("app_title"))
        self.badge.setText(self.tr("qt_interface_badge"))
        self.title.setText(self.tr("app_title"))
        self.subtitle.setText(self.tr("start_subtitle"))
        self.workflow_title.setText(self.tr("start_workflow_title"))
        for label, key in zip(self.workflow_labels, ("start_workflow_1", "start_workflow_2", "start_workflow_3")):
            label.setText(self.tr(key))
        self.loading_title.setText(self.tr("start_loading_title"))
        self.actions_title.setText(self.tr("start_actions_title"))
        self.actions_hint.setText(self.tr("start_actions_hint"))
        self.new_button.setText(self.tr("new_survey"))
        self.open_button.setText(self.tr("open_existing_survey"))
        self.exit_button.setText(self.tr("exit"))
        self.ready_note.setText(self.tr("start_ready_hint"))
        self.copyright_label.setText(self.tr("copyright"))
        self.update_loading_text()

    def change_language(self, _index=None):
        self.language = normalize_language(self.language_combo.currentData())
        self.retranslate()

    def start_async_imports(self):
        self.load_thread = QThread(self)
        self.load_worker = AppImportWorker()
        self.load_worker.moveToThread(self.load_thread)
        self.load_thread.started.connect(self.load_worker.run)
        self.load_worker.finished.connect(self.finish_app_import)
        self.load_worker.finished.connect(self.load_thread.quit)
        self.load_worker.finished.connect(self.load_worker.deleteLater)
        self.load_worker.failed.connect(self.fail_app_import)
        self.load_worker.failed.connect(self.load_thread.quit)
        self.load_worker.failed.connect(self.load_worker.deleteLater)
        self.load_thread.finished.connect(self.cleanup_load_thread)
        self.load_thread.finished.connect(self.load_thread.deleteLater)
        self.load_thread.start()

    def finish_app_import(self, app_class):
        self.app_class = app_class
        self.load_error = None
        self.set_ready(True)
        if self.close_after_load:
            QApplication.instance().quit()

    def fail_app_import(self, message):
        self.load_error = message
        self.set_ready(False)
        self.update_loading_text()
        QMessageBox.critical(self, self.tr("loading_app_error"), message)
        if self.close_after_load:
            QApplication.instance().quit()

    def cleanup_load_thread(self):
        self.load_thread = None
        self.load_worker = None

    def set_ready(self, is_ready):
        self.new_button.setEnabled(is_ready)
        self.open_button.setEnabled(is_ready)
        if is_ready:
            self.loading_progress.setRange(0, 1)
            self.loading_progress.setValue(1)
        else:
            self.loading_progress.setRange(0, 0 if self.load_error is None else 1)
            self.loading_progress.setValue(0)
        self.update_loading_text()

    def update_loading_text(self):
        if not hasattr(self, "loading_status"):
            return
        if self.load_error:
            self.loading_status.setText(self.tr("loading_app_error"))
        elif self.app_class is not None:
            self.loading_status.setText(self.tr("loading_app_ready"))
        else:
            self.loading_status.setText(self.tr("loading_app"))

    def launch_new_survey(self):
        self.launch_workspace("new")

    def launch_open_survey(self):
        self.launch_workspace("open")

    def launch_workspace(self, action):
        if self.app_class is None:
            return

        csv_file = None
        if action == "open":
            csv_file, _selected_filter = QFileDialog.getOpenFileName(
                self,
                self.tr("open_existing_survey"),
                "",
                self.tr("qt_survey_file_filter"),
            )
            if not csv_file:
                return

        self.new_button.setEnabled(False)
        self.open_button.setEnabled(False)
        try:
            window = self.app_class()
            window.change_language(self.language.upper())
            if action == "new":
                if not window.new_survey():
                    window.deleteLater()
                    self.set_ready(True)
                    return
            else:
                if not window.open_survey(csv_file):
                    window.deleteLater()
                    self.set_ready(True)
                    return

            self.workspace_window = window
            window.destroyed.connect(QApplication.instance().quit)
            self.hide()
            window.showMaximized()
        except Exception as exc:
            log_exception("qt workspace launch failed", exc, logger_name="startup")
            self.set_ready(True)
            QMessageBox.critical(self, self.tr("loading_app_error"), str(exc))

    def closeEvent(self, event):
        if self.load_thread is not None and self.load_thread.isRunning():
            self.close_after_load = True
            self.loading_status.setText(self.tr("loading_app"))
            event.ignore()
            return
        event.accept()


def install_exception_logging():
    def handle_exception(exc_type, exc_value, exc_traceback):
        log_unhandled_exception(exc_type, exc_value, exc_traceback)
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = handle_exception


def main():
    configure_logging()
    install_exception_logging()
    log_event("qt launcher start", logger_name="startup")
    app = QApplication(sys.argv)
    app.setApplicationName("Wi-Fi Heatmap Survey")
    window = StartWindow()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
