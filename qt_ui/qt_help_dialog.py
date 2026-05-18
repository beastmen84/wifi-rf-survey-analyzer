"""Qt help center content and layout."""

import re
from dataclasses import dataclass
from html import escape, unescape
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QSplitter,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from app_core.version import (
    APP_COPYRIGHT,
    APP_LICENSE_ID,
    APP_LICENSE_NAME,
    APP_LICENSE_URL,
    APP_VERSION_LABEL,
)
from qt_ui.qt_theme import QT_THEMES, build_scrollbar_stylesheet
from qt_ui.scaling import widget_font, widget_px


IMAGES_DIR = Path(__file__).resolve().parent.parent / "images"
_TABLE_TAG_RE = re.compile(r"<table(?P<attrs>[^>]*)>", re.IGNORECASE)
_CALLOUT_ACCENT_TD_RE = re.compile(
    r"<td(?P<attrs>[^>]*\bclass=\"callout-accent-(?:info|good|warning|danger)\"[^>]*)>\s*</td>",
    re.IGNORECASE,
)
_H2_RE = re.compile(r"(<h2\b[^>]*>)(.*?)(</h2>)", re.IGNORECASE | re.DOTALL)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class HelpSubsection:
    title: str
    anchor: str


@dataclass(frozen=True)
class HelpSection:
    key: str
    nav_title: str
    title: str
    subtitle: str
    body_html: str
    subsections: tuple[HelpSubsection, ...] = ()


def open_qt_help_dialog(parent, tr):
    dialog = QDialog(parent)
    dialog.setWindowTitle(f"{tr('help_title')} {APP_VERSION_LABEL}")
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

    navigation = QTreeWidget()
    navigation.setObjectName("helpNavigation")
    navigation.setHeaderHidden(True)
    navigation.setRootIsDecorated(True)
    navigation.setItemsExpandable(True)
    navigation.setExpandsOnDoubleClick(False)
    navigation.setIndentation(widget_px(parent, 16))
    navigation.setFixedWidth(widget_px(parent, 292))
    splitter.addWidget(navigation)

    browser = QTextBrowser()
    browser.setObjectName("helpContent")
    browser.setOpenExternalLinks(False)
    splitter.addWidget(browser)
    splitter.setStretchFactor(0, 0)
    splitter.setStretchFactor(1, 1)

    for index, section in enumerate(sections):
        item = QTreeWidgetItem([section.nav_title])
        item.setData(0, Qt.ItemDataRole.UserRole, (index, ""))
        style_help_navigation_item(item, parent, is_section=True)
        navigation.addTopLevelItem(item)
        for subsection in section.subsections:
            child = QTreeWidgetItem([subsection.title])
            child.setData(0, Qt.ItemDataRole.UserRole, (index, subsection.anchor))
            style_help_navigation_item(child, parent, is_section=False)
            item.addChild(child)

    def collapse_other_sections(selected_item):
        selected_top = selected_item
        while selected_top and selected_top.parent():
            selected_top = selected_top.parent()
        for index in range(navigation.topLevelItemCount()):
            item = navigation.topLevelItem(index)
            item.setExpanded(item is selected_top)

    pressed_navigation_item = {"item": None}

    def select_section(item):
        if item is None:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        section_index, anchor = data
        collapse_other_sections(item)
        browser.setHtml(build_help_html(parent, palette, sections[section_index]))
        if anchor:
            QTimer.singleShot(0, lambda selected_anchor=anchor: browser.scrollToAnchor(selected_anchor))
        else:
            browser.verticalScrollBar().setValue(0)

    def remember_pressed_item(item, _column):
        pressed_navigation_item["item"] = item

    def handle_navigation_click(item, _column):
        selected_item = pressed_navigation_item.get("item") or item
        pressed_navigation_item["item"] = None
        navigation.setCurrentItem(selected_item)
        select_section(selected_item)

    def handle_navigation_activation(item, _column):
        navigation.setCurrentItem(item)
        select_section(item)

    navigation.itemPressed.connect(remember_pressed_item)
    navigation.itemClicked.connect(handle_navigation_click)
    navigation.itemActivated.connect(handle_navigation_activation)
    apply_help_dialog_style(dialog, parent, palette)
    navigation.setCurrentItem(navigation.topLevelItem(0))
    select_section(navigation.topLevelItem(0))

    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    dialog.exec()


def help_palette(parent):
    theme = getattr(parent, "theme", "light")
    return QT_THEMES.get(theme, QT_THEMES["light"])


def build_help_sections(parent, tr):
    return [
        build_help_section(
            "overview",
            tr("help_overview_nav"),
            tr("help_overview_title"),
            tr("help_overview_subtitle"),
            tr("help_overview_body"),
        ),
        build_help_section(
            "controls",
            tr("help_controls_nav"),
            tr("help_controls_title"),
            tr("help_controls_subtitle"),
            build_controls_body(parent, tr) + tr("help_controls_body"),
        ),
        build_help_section(
            "survey",
            tr("help_survey_nav"),
            tr("help_survey_title"),
            tr("help_survey_subtitle"),
            tr("help_survey_body"),
        ),
        build_help_section(
            "quality",
            tr("help_quality_nav"),
            tr("help_quality_title"),
            tr("help_quality_subtitle"),
            tr("help_quality_body"),
        ),
        build_help_section(
            "ap_groups",
            tr("help_ap_groups_nav"),
            tr("help_ap_groups_title"),
            tr("help_ap_groups_subtitle"),
            tr("help_ap_groups_body"),
        ),
        build_help_section(
            "live_maps",
            tr("help_live_maps_nav"),
            tr("help_live_maps_title"),
            tr("help_live_maps_subtitle"),
            tr("help_live_maps_body"),
        ),
        build_help_section(
            "reports",
            tr("help_reports_nav"),
            tr("help_reports_title"),
            tr("help_reports_subtitle"),
            tr("help_reports_body"),
        ),
        build_help_section(
            "diagnostics",
            tr("help_diagnostics_nav"),
            tr("help_diagnostics_title"),
            tr("help_diagnostics_subtitle"),
            tr("help_diagnostics_body"),
        ),
        build_help_section(
            "glossary",
            tr("help_glossary_nav"),
            tr("help_glossary_title"),
            tr("help_glossary_subtitle"),
            tr("help_glossary_body"),
        ),
        build_help_section(
            "legal",
            tr("help_legal_nav"),
            tr("help_legal_title"),
            tr("help_legal_subtitle"),
            tr(
                "help_legal_body",
                version=APP_VERSION_LABEL,
                copyright=APP_COPYRIGHT,
                license_name=APP_LICENSE_NAME,
                license_id=APP_LICENSE_ID,
                license_url=APP_LICENSE_URL,
            ),
        ),
    ]


def style_help_navigation_item(item, parent, is_section):
    font = QFont("Segoe UI")
    font.setPointSizeF(widget_font(parent, 10.8 if is_section else 9.5))
    font.setBold(is_section)
    item.setFont(0, font)
    item.setTextAlignment(0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    item.setSizeHint(0, QSize(0, widget_px(parent, 34 if is_section else 27)))


def build_help_section(key, nav_title, title, subtitle, body_html):
    return HelpSection(
        key,
        nav_title,
        title,
        subtitle,
        body_html,
        extract_help_subsections(key, body_html),
    )


def extract_help_subsections(section_key, body_html):
    subsections = []
    for index, match in enumerate(_H2_RE.finditer(body_html), start=1):
        title = unescape(_HTML_TAG_RE.sub("", match.group(2))).strip()
        if title:
            subsections.append(HelpSubsection(title, f"{section_key}-{index}"))
    return tuple(subsections)


def add_help_subsection_anchors(body_html, subsections):
    subsection_iter = iter(subsections)

    def replace(match):
        try:
            subsection = next(subsection_iter)
        except StopIteration:
            return match.group(0)
        return f'<a name="{escape(subsection.anchor)}"></a>{match.group(0)}'

    return _H2_RE.sub(replace, body_html)


def build_controls_body(parent, tr):
    controls = [
        (("right-click.png",), tr("help_control_right_click_title"), tr("help_control_right_click_text")),
        (("left-click.png",), tr("help_control_left_click_title"), tr("help_control_left_click_text")),
        (("left-click_2.png",), tr("help_control_left_drag_title"), tr("help_control_left_drag_text")),
        (("scroll.png",), tr("help_control_scroll_title"), tr("help_control_scroll_text")),
        (("ctrl.png", "scroll.png"), tr("help_control_ctrl_title"), tr("help_control_ctrl_text")),
        (("shift.png", "scroll.png"), tr("help_control_shift_title"), tr("help_control_shift_text")),
    ]

    cells = []
    for image_names, title, text in controls:
        icon_html = '<span class="control-plus">+</span>'.join(
            '<img src="{src}" width="{image_width}">'.format(
                src=control_asset_uri(image_name),
                image_width=widget_px(parent, 38),
            )
            for image_name in image_names
        )
        cells.append(
            """
            <td class="control-card">
                <div class="control-icon-row">{icon_html}</div>
                <div class="control-title">{title}</div>
                <p>{text}</p>
            </td>
            """.format(
                icon_html=icon_html,
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
    radius = widget_px(parent, 8)
    gap = widget_px(parent, 12)
    padding = widget_px(parent, 18)
    right_padding = padding + widget_px(parent, 14)

    body_html = add_help_subsection_anchors(section.body_html, section.subsections)
    body_html = normalize_help_tables(body_html, callout_accent_width=widget_px(parent, 6))

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
            padding: {padding}px {right_padding}px {padding}px {padding}px;
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
            background: {palette["panel_alt"]};
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
        .callout-label {{
            color: {palette["title"]};
            font-weight: 800;
        }}
        b, strong {{
            color: {palette["metric_info"]};
            font-weight: 800;
        }}
        .callout.good b, .callout.good strong {{
            color: {palette["metric_good"]};
        }}
        .callout.warning b, .callout.warning strong {{
            color: {palette["metric_warning"]};
        }}
        .callout.danger b, .callout.danger strong {{
            color: {palette["metric_danger"]};
        }}
        .section-card {{
            border: 1px solid {palette["border"]};
            border-radius: {radius}px;
            background: {palette["panel_alt"]};
            padding: {widget_px(parent, 12)}px;
            margin: {gap}px 0;
        }}
        .insight-card {{
            border-left: {widget_px(parent, 5)}px solid {palette["metric_info"]};
        }}
        .callout-table {{
            border-collapse: collapse;
            width: 100%;
            margin: {gap}px 0;
        }}
        .callout-table td {{
            border: 0;
            padding: 0;
        }}
        .callout-table td.callout-accent-info,
        .callout-table td.callout-accent-good,
        .callout-table td.callout-accent-warning,
        .callout-table td.callout-accent-danger {{
            width: {widget_px(parent, 6)}px;
            padding: 0;
        }}
        .callout-table td.callout-accent-info {{
            background: {palette["metric_info"]};
        }}
        .callout-table td.callout-accent-good {{
            background: {palette["metric_good"]};
        }}
        .callout-table td.callout-accent-warning {{
            background: {palette["metric_warning"]};
        }}
        .callout-table td.callout-accent-danger {{
            background: {palette["metric_danger"]};
        }}
        .callout-table td.callout-content {{
            background: {palette["panel_alt"]};
            color: {palette["text"]};
            padding: {widget_px(parent, 9)}px {widget_px(parent, 12)}px;
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
        .workflow-grid {{
            border-collapse: collapse;
            width: 100%;
            margin: {widget_px(parent, 7)}px 0 {gap}px 0;
        }}
        .workflow-grid td.workflow-card {{
            width: 50%;
            border: 1px solid {palette["border"]};
            border-radius: {radius}px;
            background: {palette["panel_alt"]};
            padding: {widget_px(parent, 13)}px {widget_px(parent, 14)}px;
        }}
        .workflow-grid td.workflow-gap {{
            width: {widget_px(parent, 14)}px;
            border: 0;
            background: transparent;
            padding: 0;
        }}
        .workflow-grid td.workflow-vertical-gap {{
            height: {widget_px(parent, 6)}px;
            border: 0;
            background: transparent;
            padding: 0;
        }}
        .survey-grid {{
            border-collapse: collapse;
            width: 100%;
            margin: {widget_px(parent, 7)}px 0 {gap}px 0;
        }}
        .survey-grid td.survey-card {{
            width: 33%;
            border: 1px solid {palette["border"]};
            border-radius: {radius}px;
            background: {palette["panel_alt"]};
            padding: {widget_px(parent, 11)}px {widget_px(parent, 12)}px;
        }}
        .survey-grid td.survey-gap {{
            width: {widget_px(parent, 10)}px;
            border: 0;
            background: transparent;
            padding: 0;
        }}
        .survey-grid td.survey-vertical-gap {{
            height: {widget_px(parent, 6)}px;
            border: 0;
            background: transparent;
            padding: 0;
        }}
        .survey-card-title {{
            color: {palette["metric_info"]};
            font-size: {widget_font(parent, 11.5):.2f}pt;
            font-weight: 800;
        }}
        .survey-card-use {{
            color: {palette["muted"]};
        }}
        .step-label {{
            color: {palette["metric_info"]};
            font-size: {widget_font(parent, 9.5):.2f}pt;
            font-weight: 800;
        }}
        .step-title {{
            color: {palette["title"]};
            font-size: {widget_font(parent, 12.5):.2f}pt;
            font-weight: 800;
            margin-top: {widget_px(parent, 2)}px;
            margin-bottom: {widget_px(parent, 4)}px;
        }}
        .step-gate {{
            border-top: 1px solid {palette["border"]};
            color: {palette["text"]};
            margin-top: {widget_px(parent, 7)}px;
            padding-top: {widget_px(parent, 7)}px;
        }}
        .gate-list {{
            border: 1px solid {palette["border"]};
            border-radius: {radius}px;
            background: {palette["panel_alt"]};
            margin: {widget_px(parent, 7)}px 0 {gap}px 0;
            padding: {widget_px(parent, 5)}px {widget_px(parent, 10)}px;
        }}
        .gate-row {{
            border-left: {widget_px(parent, 4)}px solid {palette["metric_info"]};
            margin: {widget_px(parent, 6)}px 0;
            padding: {widget_px(parent, 5)}px {widget_px(parent, 8)}px;
            background: {palette["panel"]};
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
        .control-icon-row {{
            margin-bottom: {widget_px(parent, 6)}px;
        }}
        .control-card img {{
            margin-right: {widget_px(parent, 6)}px;
            vertical-align: middle;
        }}
        .control-plus {{
            color: {palette["muted"]};
            font-size: {widget_font(parent, 12):.2f}pt;
            font-weight: 800;
            padding-right: {widget_px(parent, 6)}px;
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
            <h1>{escape(section.title)}</h1>
            <p class="subtitle">{escape(section.subtitle)}</p>
            {body_html}
        </div>
    </body>
    </html>
    """


def normalize_help_tables(body_html, callout_accent_width=6):
    def replace(match):
        attrs = match.group("attrs") or ""
        lower_attrs = attrs.lower()
        additions = []
        if "width=" not in lower_attrs:
            additions.append('width="100%"')
        if "cellspacing=" not in lower_attrs:
            additions.append('cellspacing="0"')
        if "cellpadding=" not in lower_attrs:
            additions.append('cellpadding="0"')
        if additions:
            attrs = f"{attrs} {' '.join(additions)}"
        return f"<table{attrs}>"

    def replace_callout_accent(match):
        attrs = match.group("attrs") or ""
        if "width=" not in attrs.lower():
            attrs = f'{attrs} width="{callout_accent_width}"'
        return f"<td{attrs}>&nbsp;</td>"

    normalized_html = _TABLE_TAG_RE.sub(replace, body_html)
    return _CALLOUT_ACCENT_TD_RE.sub(replace_callout_accent, normalized_html)


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
        QTreeWidget#helpNavigation {{
            background: {palette["toolbar"]};
            border: 1px solid {palette["border"]};
            border-radius: {s(8)}px;
            padding: {s(6)}px;
            outline: 0;
        }}
        QTreeWidget#helpNavigation::item {{
            color: {palette["text"]};
            padding: {s(7)}px {s(8)}px;
            border-radius: {s(6)}px;
            margin: {s(1)}px 0;
        }}
        QTreeWidget#helpNavigation::item:hover {{
            background: {palette["button_hover"]};
        }}
        QTreeWidget#helpNavigation::item:selected {{
            background: {palette["metric_info"]};
            color: #FFFFFF;
            font-weight: 700;
        }}
        QTreeWidget#helpNavigation::branch {{
            background: transparent;
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
        {build_scrollbar_stylesheet(palette, s, "QTreeWidget#helpNavigation")}
        """
    )
