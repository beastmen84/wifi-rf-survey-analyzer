import sys
from pathlib import Path

try:
    from PySide6.QtCore import QObject, QPoint, Qt, QThread, QTimer, Signal, Slot
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QDialog,
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
from app_settings import get_saved_theme, get_saved_ui_scale, save_theme, save_ui_scale
from i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, normalize_language, translate
from qt_theme import QT_THEME_OPTIONS, QT_THEMES
from ui_scaling import UI_SCALE_OPTIONS, normalize_ui_scale_mode, resolve_ui_scale, scale_font_px, scale_px


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
        self.theme = get_saved_theme(default="light", valid_themes=QT_THEMES)
        self.ui_scale_mode = normalize_ui_scale_mode(get_saved_ui_scale())
        self.ui_scale = resolve_ui_scale(self.ui_scale_mode)
        self.app_class = None
        self.workspace_window = None
        self.load_thread = None
        self.load_worker = None
        self.load_error = None
        self.close_after_load = False

        self.setObjectName("startWindow")
        self.setMinimumSize(self.spx(1100), self.spx(720))
        self.resize(self.spx(1320), self.spx(820))

        self.build_ui()
        self.apply_styles()
        self.retranslate()
        self.set_ready(False)
        QTimer.singleShot(0, self.start_async_imports)

    def tr(self, key, **kwargs):
        return translate(self.language, key, **kwargs)

    def spx(self, value):
        return scale_px(value, self.ui_scale)

    def sfont(self, value):
        return scale_font_px(value, self.ui_scale)

    def build_ui(self):
        page = QWidget()
        page.setObjectName("startPage")
        self.setCentralWidget(page)

        outer = QVBoxLayout(page)
        outer.setContentsMargins(self.spx(56), self.spx(36), self.spx(56), self.spx(24))
        outer.setSpacing(self.spx(24))

        top_row = QHBoxLayout()
        top_row.addStretch(1)
        self.settings_button = QPushButton()
        self.settings_button.setObjectName("startSettingsButton")
        self.settings_button.clicked.connect(self.open_settings_menu)
        top_row.addWidget(self.settings_button)
        outer.addLayout(top_row)

        body = QHBoxLayout()
        body.setSpacing(self.spx(28))
        body.addStretch(1)

        hero = QFrame()
        hero.setObjectName("startHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(self.spx(40), self.spx(38), self.spx(40), self.spx(34))
        hero_layout.setSpacing(self.spx(18))

        self.title = QLabel()
        self.title.setObjectName("startTitle")
        self.title.setWordWrap(True)
        self.subtitle = QLabel()
        self.subtitle.setObjectName("startSubtitle")
        self.subtitle.setWordWrap(True)
        hero_layout.addWidget(self.title)
        hero_layout.addWidget(self.subtitle)
        hero_layout.addSpacing(self.spx(14))

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
        self.loading_progress.setFixedHeight(self.spx(8))
        hero_layout.addWidget(self.loading_title)
        hero_layout.addWidget(self.loading_status)
        hero_layout.addWidget(self.loading_progress)

        actions = QFrame()
        actions.setObjectName("startActions")
        actions_layout = QVBoxLayout(actions)
        actions_layout.setContentsMargins(self.spx(32), self.spx(34), self.spx(32), self.spx(32))
        actions_layout.setSpacing(self.spx(14))

        self.actions_title = QLabel()
        self.actions_title.setObjectName("startSectionTitle")
        self.actions_hint = QLabel()
        self.actions_hint.setObjectName("startMuted")
        self.actions_hint.setWordWrap(True)
        actions_layout.addWidget(self.actions_title)
        actions_layout.addWidget(self.actions_hint)
        actions_layout.addSpacing(self.spx(14))

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
            button.setMinimumHeight(self.spx(50))
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
        palette = QT_THEMES.get(self.theme, QT_THEMES["light"])
        combo_arrow_icon = (Path(__file__).resolve().parent / "images" / "combo_arrow_white.svg").as_posix()
        s = self.spx
        font = self.sfont
        self.setStyleSheet(
            f"""
            QMainWindow#startWindow, QWidget#startPage {{
                background: {palette["bg"]};
                color: {palette["text"]};
                font-family: "Segoe UI";
                font-size: {font(14)}px;
            }}
            QFrame#startHero, QFrame#startActions {{
                background: {palette["panel"]};
                border: 1px solid {palette["border"]};
                border-radius: {s(10)}px;
            }}
            QFrame#startHero {{
                min-width: {s(620)}px;
            }}
            QFrame#startActions {{
                min-width: {s(360)}px;
                max-width: {s(430)}px;
            }}
            QLabel#startTitle {{
                color: {palette["title"]};
                font-size: {font(42)}px;
                font-weight: 800;
            }}
            QLabel#startSubtitle {{
                color: {palette["muted"]};
                font-size: {font(18)}px;
            }}
            QLabel#startSectionTitle {{
                color: {palette["title"]};
                font-size: {font(17)}px;
                font-weight: 700;
            }}
            QLabel#startStep {{
                color: {palette["text"]};
                font-size: {font(15)}px;
                padding: {s(2)}px 0;
            }}
            QLabel#startMuted, QLabel#startFooter {{
                color: {palette["muted"]};
            }}
            QPushButton#primaryStartButton {{
                background: {palette["metric_info"]};
                color: #ffffff;
                border: 1px solid {palette["metric_info"]};
                border-radius: {s(7)}px;
                font-size: {font(15)}px;
                font-weight: 700;
                padding: {s(10)}px {s(14)}px;
            }}
            QPushButton#primaryStartButton:hover {{
                background: {palette["metric_info"]};
            }}
            QPushButton#primaryStartButton:disabled {{
                background: {palette["button_hover"]};
                border-color: {palette["border"]};
                color: {palette["muted"]};
            }}
            QPushButton#secondaryStartButton {{
                background: {palette["button_bg"]};
                color: {palette["text"]};
                border: 1px solid {palette["border"]};
                border-radius: {s(7)}px;
                font-size: {font(15)}px;
                font-weight: 600;
                padding: {s(10)}px {s(14)}px;
            }}
            QPushButton#secondaryStartButton:hover {{
                background: {palette["button_hover"]};
            }}
            QPushButton#secondaryStartButton:disabled {{
                color: {palette["muted"]};
                background: {palette["panel_alt"]};
            }}
            QComboBox {{
                background: {palette["button_bg"]};
                color: {palette["text"]};
                border: 1px solid {palette["border"]};
                border-radius: {s(6)}px;
                padding: {s(6)}px {s(28)}px {s(6)}px {s(10)}px;
                min-width: {s(72)}px;
            }}
            QComboBox#languageCombo {{
                background: {palette["metric_info"]};
                color: #ffffff;
                border: 1px solid {palette["metric_info"]};
                border-radius: {s(7)}px;
                padding: {s(8)}px {s(34)}px {s(8)}px {s(12)}px;
                min-width: {s(128)}px;
                font-weight: 700;
            }}
            QComboBox#languageCombo:hover {{
                background: {palette["metric_info"]};
                border-color: {palette["metric_info"]};
            }}
            QComboBox#scaleCombo {{
                min-width: {s(108)}px;
            }}
            QPushButton#startSettingsButton {{
                background: {palette["metric_info"]};
                color: #ffffff;
                border: 1px solid {palette["metric_info"]};
                border-radius: {s(7)}px;
                font-size: {font(14)}px;
                font-weight: 700;
                padding: {s(8)}px {s(14)}px;
                min-width: {s(116)}px;
            }}
            QDialog#settingsMenuPanel, QWidget#settingsMenuPanel {{
                background: {palette["panel"]};
                color: {palette["text"]};
                border: 1px solid {palette["border"]};
                border-radius: {s(8)}px;
            }}
            QLabel#settingsMenuLabel {{
                color: {palette["muted"]};
                font-weight: 700;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: {s(28)}px;
                border-left: 1px solid {palette["metric_info"]};
                border-top-right-radius: {s(6)}px;
                border-bottom-right-radius: {s(6)}px;
                background: {palette["metric_info"]};
            }}
            QComboBox::down-arrow {{
                image: url("{combo_arrow_icon}");
                width: {s(10)}px;
                height: {s(6)}px;
            }}
            QComboBox#languageCombo QAbstractItemView {{
                background: {palette["panel"]};
                color: {palette["text"]};
                selection-background-color: {palette["selection"]};
                selection-color: {palette["text"]};
                border: 1px solid {palette["border"]};
            }}
            QProgressBar {{
                background: {palette["panel_alt"]};
                border: 0;
                border-radius: {s(4)}px;
            }}
            QProgressBar::chunk {{
                background: {palette["metric_info"]};
                border-radius: {s(4)}px;
            }}
            """
        )

    def retranslate(self):
        self.setWindowTitle(self.tr("app_title"))
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
        self.settings_button.setText(self.tr("toolbar_settings"))
        self.ready_note.setText(self.tr("start_ready_hint"))
        self.copyright_label.setText(self.tr("copyright"))
        self.update_loading_text()

    def change_language(self, value):
        self.language = normalize_language(value)
        self.retranslate()

    def change_theme(self, theme):
        if theme not in QT_THEMES or theme == self.theme:
            return

        self.theme = theme
        save_theme(theme)
        self.apply_styles()

    def change_ui_scale(self, mode):
        mode = normalize_ui_scale_mode(mode)
        if mode == self.ui_scale_mode:
            return

        self.ui_scale_mode = mode
        self.ui_scale = resolve_ui_scale(mode)
        save_ui_scale(mode)
        self.setMinimumSize(self.spx(1100), self.spx(720))
        self.apply_styles()
        self.ready_note.setText(self.tr("ui_scale_saved_restart"))

    def open_settings_menu(self):
        dialog = QDialog(self)
        dialog.setObjectName("settingsMenuPanel")
        dialog.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(self.spx(12), self.spx(10), self.spx(12), self.spx(10))
        layout.setSpacing(self.spx(8))

        theme_combo = self.create_settings_combo(
            [(theme, self.tr(f"qt_theme_{theme}")) for theme in QT_THEME_OPTIONS],
            self.theme,
        )
        theme_combo.currentIndexChanged.connect(lambda _index: self.change_theme(theme_combo.currentData()))
        self.add_settings_row(layout, self.tr("theme"), theme_combo)

        scale_combo = self.create_settings_combo(self.ui_scale_items(), self.ui_scale_mode)
        scale_combo.currentIndexChanged.connect(lambda _index: self.change_ui_scale(scale_combo.currentData()))
        self.add_settings_row(layout, self.tr("ui_scale"), scale_combo)

        language_combo = self.create_settings_combo(
            [(code, START_LANGUAGE_LABELS.get(code, code)) for code in SUPPORTED_LANGUAGES],
            self.language.upper(),
        )
        language_combo.currentIndexChanged.connect(lambda _index: self.change_language(language_combo.currentData()))
        self.add_settings_row(layout, self.tr("language"), language_combo)

        menu_width = self.spx(300)
        dialog.setMinimumWidth(menu_width)
        dialog.adjustSize()
        position = self.settings_button.mapToGlobal(
            QPoint(self.settings_button.width() - menu_width, self.settings_button.height())
        )
        dialog.move(position)
        dialog.exec()

    def create_settings_combo(self, items, current_value):
        combo = QComboBox()
        combo.setMinimumWidth(self.spx(168))
        for value, label in items:
            combo.addItem(label, value)
        index = combo.findData(current_value)
        combo.setCurrentIndex(max(0, index))
        return combo

    def add_settings_row(self, layout, label_text, widget):
        label = QLabel(label_text)
        label.setObjectName("settingsMenuLabel")
        layout.addWidget(label)
        layout.addWidget(widget)

    def ui_scale_items(self):
        auto_percent = int(round(resolve_ui_scale("auto") * 100))
        return [
            (mode, self.tr("ui_scale_auto", percent=auto_percent) if mode == "auto" else f"{mode}%")
            for mode in UI_SCALE_OPTIONS
        ]

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
    app.setApplicationName("Wi-Fi RF Survey Analyzer")
    window = StartWindow()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
