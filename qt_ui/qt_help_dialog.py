"""Qt help dialog content and layout."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QTextBrowser, QTabWidget, QVBoxLayout, QWidget

from ui_scaling import widget_font, widget_px


def open_qt_help_dialog(parent, tr):
    dialog = QDialog(parent)
    dialog.setWindowTitle(tr("help_title"))
    dialog.resize(widget_px(parent, 920), widget_px(parent, 720))
    dialog.setMinimumSize(widget_px(parent, 760), widget_px(parent, 560))

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(widget_px(parent, 12), widget_px(parent, 12), widget_px(parent, 12), widget_px(parent, 12))

    tabs = QTabWidget()
    layout.addWidget(tabs)

    tab_specs = [
        ("help_workflow", "help_workflow_title", "help_workflow_steps"),
        ("help_live", "help_live_title", "help_live_steps"),
        ("help_heatmap", "help_heatmap_title", "help_heatmap_steps"),
        ("help_scan", "help_scan_title", "help_scan_steps"),
        ("help_commands", "help_commands", "help_commands_text"),
    ]

    for tab_key, title_key, body_key in tab_specs:
        tabs.addTab(build_help_tab(parent, tr(title_key), tr(body_key)), tr(tab_key))

    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    dialog.exec()


def build_help_tab(parent, title, body):
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)

    browser = QTextBrowser()
    browser.setOpenExternalLinks(False)
    browser.setPlainText(f"{title}\n\n{body}")
    browser.setStyleSheet(
        """
        QTextBrowser {
            background: #ffffff;
            border: 1px solid #d7dde3;
            border-radius: %dpx;
            padding: %dpx;
            color: #1f2933;
            font-family: Segoe UI;
            font-size: %.2fpt;
        }
        """ % (widget_px(parent, 6), widget_px(parent, 14), widget_font(parent, 11))
    )
    layout.addWidget(browser)
    return tab
