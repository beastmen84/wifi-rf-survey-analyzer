"""Color palettes and theme ordering for the Qt interface."""

QT_THEME_OPTIONS = ("light", "soft", "dark", "contrast")

QT_THEMES = {
    "light": {
        "bg": "#F5F7FA",
        "panel": "#FFFFFF",
        "panel_alt": "#F1F5F9",
        "footer": "#F8FAFC",
        "border": "#D5DEE8",
        "text": "#25313D",
        "title": "#1F2A36",
        "muted": "#5F6B78",
        "toolbar": "#F8FAFC",
        "header": "#E8EEF5",
        "badge_bg": "#D6E6F5",
        "badge_border": "#B8D1E8",
        "badge_text": "#21496E",
        "live_bg": "#E3E8EE",
        "metric_good": "#4E8F5A",
        "metric_warning": "#D49A32",
        "metric_danger": "#C65A5A",
        "metric_info": "#3A6EA5",
        "button_bg": "#FFFFFF",
        "button_hover": "#EAF3FB",
        "save_dirty_bg": "#FFF4D6",
        "save_dirty_border": "#D49A32",
        "save_dirty_text": "#5F3F00",
        "selection": "#D6E6F5",
    },
    "soft": {
        "bg": "#F6F4EF",
        "panel": "#FFFFFF",
        "panel_alt": "#EEF3EC",
        "footer": "#F2EFE8",
        "border": "#D6D0C4",
        "text": "#2F312E",
        "title": "#262A25",
        "muted": "#767A70",
        "toolbar": "#F2EFE8",
        "header": "#E6E0D6",
        "badge_bg": "#DDE8DA",
        "badge_border": "#BFD3BA",
        "badge_text": "#3B573A",
        "live_bg": "#E0DED8",
        "metric_good": "#4F8A5B",
        "metric_warning": "#C99537",
        "metric_danger": "#B85C5C",
        "metric_info": "#5C7A5A",
        "button_bg": "#FFFFFF",
        "button_hover": "#DDE8DA",
        "save_dirty_bg": "#F5E2B8",
        "save_dirty_border": "#C99537",
        "save_dirty_text": "#5A3A00",
        "selection": "#DDE8DA",
    },
    "dark": {
        "bg": "#1E2329",
        "panel": "#262C33",
        "panel_alt": "#303741",
        "footer": "#262C33",
        "border": "#3D4652",
        "text": "#E6EAF0",
        "title": "#F2F5F8",
        "muted": "#B8C0CC",
        "toolbar": "#262C33",
        "header": "#303741",
        "badge_bg": "#334766",
        "badge_border": "#465F85",
        "badge_text": "#DDE7FF",
        "live_bg": "#151A20",
        "metric_good": "#63B37A",
        "metric_warning": "#D8A24A",
        "metric_danger": "#D36B6B",
        "metric_info": "#5C8DFF",
        "button_bg": "#303741",
        "button_hover": "#394453",
        "save_dirty_bg": "#674B1E",
        "save_dirty_border": "#D8A24A",
        "save_dirty_text": "#FFFFFF",
        "selection": "#334766",
    },
    "contrast": {
        "bg": "#202422",
        "panel": "#2A2F2C",
        "panel_alt": "#343A36",
        "footer": "#2A2F2C",
        "border": "#414A44",
        "text": "#E5E8E4",
        "title": "#F0F3EF",
        "muted": "#BCC3BC",
        "toolbar": "#2A2F2C",
        "header": "#343A36",
        "badge_bg": "#39483E",
        "badge_border": "#506555",
        "badge_text": "#DFF4E3",
        "live_bg": "#171B19",
        "metric_good": "#73C287",
        "metric_warning": "#D1A14A",
        "metric_danger": "#C86A6A",
        "metric_info": "#6FA77B",
        "button_bg": "#343A36",
        "button_hover": "#3E4A42",
        "save_dirty_bg": "#62491D",
        "save_dirty_border": "#D1A14A",
        "save_dirty_text": "#FFFFFF",
        "selection": "#39483E",
    },
}


def build_scrollbar_stylesheet(palette, scale_px, selector_prefix=""):
    prefix = f"{selector_prefix} " if selector_prefix else ""
    return f"""
            {prefix}QScrollBar:vertical {{
                background: transparent;
                width: {scale_px(13)}px;
                margin: {scale_px(3)}px {scale_px(2)}px {scale_px(3)}px {scale_px(2)}px;
                border: 0;
            }}
            {prefix}QScrollBar::handle:vertical {{
                background: {palette["badge_border"]};
                border-radius: {scale_px(5)}px;
                min-height: {scale_px(36)}px;
            }}
            {prefix}QScrollBar::handle:vertical:hover {{
                background: {palette["metric_info"]};
            }}
            {prefix}QScrollBar::add-line:vertical,
            {prefix}QScrollBar::sub-line:vertical {{
                height: 0;
                border: 0;
                background: transparent;
            }}
            {prefix}QScrollBar::add-page:vertical,
            {prefix}QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
            {prefix}QScrollBar:horizontal {{
                background: transparent;
                height: {scale_px(13)}px;
                margin: {scale_px(2)}px {scale_px(3)}px {scale_px(2)}px {scale_px(3)}px;
                border: 0;
            }}
            {prefix}QScrollBar::handle:horizontal {{
                background: {palette["badge_border"]};
                border-radius: {scale_px(5)}px;
                min-width: {scale_px(36)}px;
            }}
            {prefix}QScrollBar::handle:horizontal:hover {{
                background: {palette["metric_info"]};
            }}
            {prefix}QScrollBar::add-line:horizontal,
            {prefix}QScrollBar::sub-line:horizontal {{
                width: 0;
                border: 0;
                background: transparent;
            }}
            {prefix}QScrollBar::add-page:horizontal,
            {prefix}QScrollBar::sub-page:horizontal {{
                background: transparent;
            }}
            {prefix}QScrollBar::up-arrow:vertical,
            {prefix}QScrollBar::down-arrow:vertical,
            {prefix}QScrollBar::left-arrow:horizontal,
            {prefix}QScrollBar::right-arrow:horizontal {{
                width: 0;
                height: 0;
                background: transparent;
            }}
            """
