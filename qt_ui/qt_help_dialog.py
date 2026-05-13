"""Qt help center content and layout."""

from dataclasses import dataclass
from html import escape
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
)

from qt_ui.qt_theme import QT_THEMES, build_scrollbar_stylesheet
from qt_ui.scaling import widget_font, widget_px


IMAGES_DIR = Path(__file__).resolve().parent.parent / "images"


@dataclass(frozen=True)
class HelpSection:
    key: str
    nav_title: str
    title: str
    subtitle: str
    body_html: str


def open_qt_help_dialog(parent, tr):
    dialog = QDialog(parent)
    dialog.setWindowTitle(tr("help_title"))
    dialog.resize(widget_px(parent, 1120), widget_px(parent, 760))
    dialog.setMinimumSize(widget_px(parent, 900), widget_px(parent, 620))

    palette = help_palette(parent)
    sections = build_help_sections(parent, tr)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(
        widget_px(parent, 12),
        widget_px(parent, 12),
        widget_px(parent, 12),
        widget_px(parent, 12),
    )

    splitter = QSplitter(Qt.Orientation.Horizontal)
    splitter.setChildrenCollapsible(False)
    layout.addWidget(splitter)

    navigation = QListWidget()
    navigation.setObjectName("helpNavigation")
    navigation.setFixedWidth(widget_px(parent, 250))
    splitter.addWidget(navigation)

    browser = QTextBrowser()
    browser.setObjectName("helpContent")
    browser.setOpenExternalLinks(False)
    splitter.addWidget(browser)
    splitter.setStretchFactor(0, 0)
    splitter.setStretchFactor(1, 1)

    for index, section in enumerate(sections):
        item = QListWidgetItem(section.nav_title)
        item.setData(Qt.ItemDataRole.UserRole, index)
        navigation.addItem(item)

    def select_section(row):
        if row < 0:
            return
        browser.setHtml(build_help_html(parent, palette, sections[row]))
        browser.verticalScrollBar().setValue(0)

    navigation.currentRowChanged.connect(select_section)
    apply_help_dialog_style(dialog, parent, palette)
    navigation.setCurrentRow(0)

    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    dialog.exec()


def help_palette(parent):
    theme = getattr(parent, "theme", "light")
    return QT_THEMES.get(theme, QT_THEMES["light"])


def build_help_sections(parent, tr):
    return [
        HelpSection(
            "overview",
            tr("help_overview_nav"),
            tr("help_overview_title"),
            tr("help_overview_subtitle"),
            tr("help_overview_body"),
        ),
        HelpSection(
            "controls",
            tr("help_controls_nav"),
            tr("help_controls_title"),
            tr("help_controls_subtitle"),
            build_controls_body(parent, tr) + tr("help_controls_body"),
        ),
        HelpSection(
            "survey",
            tr("help_survey_nav"),
            tr("help_survey_title"),
            tr("help_survey_subtitle"),
            tr("help_survey_body"),
        ),
        HelpSection(
            "quality",
            tr("help_quality_nav"),
            tr("help_quality_title"),
            tr("help_quality_subtitle"),
            tr("help_quality_body"),
        ),
        HelpSection(
            "ap_groups",
            tr("help_ap_groups_nav"),
            tr("help_ap_groups_title"),
            tr("help_ap_groups_subtitle"),
            tr("help_ap_groups_body"),
        ),
        HelpSection(
            "live_maps",
            tr("help_live_maps_nav"),
            tr("help_live_maps_title"),
            tr("help_live_maps_subtitle"),
            tr("help_live_maps_body"),
        ),
        HelpSection(
            "reports",
            tr("help_reports_nav"),
            tr("help_reports_title"),
            tr("help_reports_subtitle"),
            tr("help_reports_body"),
        ),
        HelpSection(
            "diagnostics",
            tr("help_diagnostics_nav"),
            tr("help_diagnostics_title"),
            tr("help_diagnostics_subtitle"),
            tr("help_diagnostics_body"),
        ),
        HelpSection(
            "glossary",
            tr("help_glossary_nav"),
            tr("help_glossary_title"),
            tr("help_glossary_subtitle"),
            tr("help_glossary_body"),
        ),
    ]


def build_controls_body(parent, tr):
    controls = [
        ("right-click.png", tr("help_control_right_click_title"), tr("help_control_right_click_text")),
        ("left-click.png", tr("help_control_left_click_title"), tr("help_control_left_click_text")),
        ("middle-click.png", tr("help_control_middle_click_title"), tr("help_control_middle_click_text")),
        ("scroll.png", tr("help_control_scroll_title"), tr("help_control_scroll_text")),
        ("shift.png", tr("help_control_shift_title"), tr("help_control_shift_text")),
        ("ctrl.png", tr("help_control_ctrl_title"), tr("help_control_ctrl_text")),
        ("wifi.png", tr("help_control_wifi_title"), tr("help_control_wifi_text")),
    ]

    cells = []
    for image_name, title, text in controls:
        cells.append(
            """
            <td class="control-card">
                <img src="{src}" width="{image_width}">
                <div class="control-title">{title}</div>
                <p>{text}</p>
            </td>
            """.format(
                src=control_asset_uri(image_name),
                image_width=widget_px(parent, 42),
                title=escape(title),
                text=escape(text),
            )
        )

    rows = []
    for index in range(0, len(cells), 2):
        row_cells = cells[index:index + 2]
        if len(row_cells) == 1:
            row_cells.append('<td class="control-card empty"></td>')
        rows.append("<tr>{}</tr>".format("".join(row_cells)))

    return '<table class="control-grid">{}</table>'.format("".join(rows))


def control_asset_uri(image_name):
    return (IMAGES_DIR / image_name).resolve().as_uri()


def build_help_html(parent, palette, section):
    font_size = widget_font(parent, 10.5)
    title_size = widget_font(parent, 22)
    heading_size = widget_font(parent, 14)
    small_size = widget_font(parent, 9.5)
    radius = widget_px(parent, 8)
    gap = widget_px(parent, 12)
    padding = widget_px(parent, 18)

    return f"""
    <html>
    <head>
    <style>
        body {{
            margin: 0;
            background: {palette["panel"]};
            color: {palette["text"]};
            font-family: Segoe UI, Arial, sans-serif;
            font-size: {font_size:.2f}pt;
            line-height: 1.42;
        }}
        .page {{
            padding: {padding}px;
        }}
        .eyebrow {{
            color: {palette["metric_info"]};
            font-size: {small_size:.2f}pt;
            font-weight: 700;
            text-transform: uppercase;
            margin-bottom: {widget_px(parent, 4)}px;
        }}
        h1 {{
            color: {palette["title"]};
            font-size: {title_size:.2f}pt;
            margin: 0 0 {widget_px(parent, 4)}px 0;
        }}
        h2 {{
            color: {palette["title"]};
            font-size: {heading_size:.2f}pt;
            margin: {widget_px(parent, 18)}px 0 {widget_px(parent, 7)}px 0;
        }}
        p {{
            margin: {widget_px(parent, 6)}px 0;
        }}
        ul, ol {{
            margin-top: {widget_px(parent, 6)}px;
            margin-bottom: {widget_px(parent, 10)}px;
        }}
        li {{
            margin-bottom: {widget_px(parent, 5)}px;
        }}
        .subtitle {{
            color: {palette["muted"]};
            font-size: {widget_font(parent, 11.5):.2f}pt;
            margin-bottom: {gap}px;
        }}
        .callout {{
            border: 1px solid {palette["badge_border"]};
            border-left: {widget_px(parent, 5)}px solid {palette["metric_info"]};
            border-radius: {radius}px;
            background: {palette["badge_bg"]};
            color: {palette["text"]};
            padding: {widget_px(parent, 11)}px {widget_px(parent, 13)}px;
            margin: {gap}px 0;
        }}
        .callout.warning {{
            border-left-color: {palette["metric_warning"]};
        }}
        .callout.good {{
            border-left-color: {palette["metric_good"]};
        }}
        .callout.danger {{
            border-left-color: {palette["metric_danger"]};
        }}
        .section-card {{
            border: 1px solid {palette["border"]};
            border-radius: {radius}px;
            background: {palette["panel_alt"]};
            padding: {widget_px(parent, 12)}px;
            margin: {gap}px 0;
        }}
        .pill {{
            display: inline-block;
            color: {palette["badge_text"]};
            background: {palette["badge_bg"]};
            border: 1px solid {palette["badge_border"]};
            border-radius: {widget_px(parent, 10)}px;
            padding: {widget_px(parent, 2)}px {widget_px(parent, 7)}px;
            font-weight: 700;
            white-space: nowrap;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: {gap}px 0;
        }}
        th {{
            background: {palette["header"]};
            color: {palette["title"]};
            text-align: left;
            font-weight: 700;
            padding: {widget_px(parent, 7)}px;
            border: 1px solid {palette["border"]};
        }}
        td {{
            vertical-align: top;
            padding: {widget_px(parent, 8)}px;
            border: 1px solid {palette["border"]};
        }}
        .control-grid td {{
            width: 50%;
        }}
        .control-card {{
            background: {palette["panel_alt"]};
            border: 1px solid {palette["border"]};
            border-radius: {radius}px;
        }}
        .control-card.empty {{
            background: transparent;
            border: 0;
        }}
        .control-card img {{
            float: left;
            margin-right: {widget_px(parent, 10)}px;
        }}
        .control-title {{
            color: {palette["title"]};
            font-weight: 800;
            margin-bottom: {widget_px(parent, 3)}px;
        }}
        code {{
            color: {palette["title"]};
            background: {palette["panel_alt"]};
            border: 1px solid {palette["border"]};
            padding: 1px 4px;
        }}
    </style>
    </head>
    <body>
        <div class="page">
            <div class="eyebrow">{escape(section.nav_title)}</div>
            <h1>{escape(section.title)}</h1>
            <p class="subtitle">{escape(section.subtitle)}</p>
            {section.body_html}
        </div>
    </body>
    </html>
    """


def apply_help_dialog_style(dialog, parent, palette):
    s = lambda value: widget_px(parent, value)
    dialog.setStyleSheet(
        f"""
        QDialog {{
            background: {palette["bg"]};
            color: {palette["text"]};
            font-family: Segoe UI;
            font-size: {widget_font(parent, 10.5):.2f}pt;
        }}
        QListWidget#helpNavigation {{
            background: {palette["toolbar"]};
            border: 1px solid {palette["border"]};
            border-radius: {s(8)}px;
            padding: {s(6)}px;
            outline: 0;
        }}
        QListWidget#helpNavigation::item {{
            color: {palette["text"]};
            padding: {s(9)}px {s(10)}px;
            border-radius: {s(6)}px;
            margin: {s(1)}px 0;
        }}
        QListWidget#helpNavigation::item:hover {{
            background: {palette["button_hover"]};
        }}
        QListWidget#helpNavigation::item:selected {{
            background: {palette["metric_info"]};
            color: #FFFFFF;
            font-weight: 700;
        }}
        QTextBrowser#helpContent {{
            background: {palette["panel"]};
            border: 1px solid {palette["border"]};
            border-radius: {s(8)}px;
        }}
        QSplitter::handle {{
            background: transparent;
            width: {s(10)}px;
        }}
        {build_scrollbar_stylesheet(palette, s, "QTextBrowser#helpContent")}
        {build_scrollbar_stylesheet(palette, s, "QListWidget#helpNavigation")}
        """
    )
