# WiFi Heatmap Tool - UI Color Palettes

This document tracks the active Qt palettes used by `qt_theme.py`.

The visual direction is:

- keep the floorplan, heatmaps, AP markers and RF data visually dominant;
- avoid pure black, pure white, neon accents and saturated "gaming" colors;
- use soft panels, restrained accent colors and readable contrast;
- prefer subtle separators over heavy borders.

## Active Theme Options

`QT_THEME_OPTIONS = ("light", "soft", "dark", "contrast")`

| Theme key | UI name | Intent |
|---|---|---|
| `light` | Sand Blue | Default light theme, now cooled toward neutral gray/blue |
| `soft` | Soft Olive | Warmer light theme with muted green accents |
| `dark` | Slate Blue | Default dark theme with restrained blue accents |
| `contrast` | Graphite Green | Calm dark theme with muted green accents |

---

# LIGHT THEME 1 - Sand Blue

Current default light theme. It is intentionally less beige than the original concept.

## Backgrounds

| Key | Color | Usage |
|---|---|---|
| `bg` | `#F5F7FA` | Main window background |
| `panel` | `#FFFFFF` | Primary panels and dialogs |
| `panel_alt` | `#F1F5F9` | Cards, alternate table rows |
| `footer` | `#F8FAFC` | Footer/status surfaces |
| `toolbar` | `#F8FAFC` | App command bar |
| `header` | `#E8EEF5` | Table headers |
| `live_bg` | `#E3E8EE` | Floorplan/view background |

## Text And Borders

| Key | Color |
|---|---|
| `text` | `#25313D` |
| `title` | `#1F2A36` |
| `muted` | `#5F6B78` |
| `border` | `#D5DEE8` |

## Accent And State Colors

| Key | Color |
|---|---|
| `metric_info` | `#3A6EA5` |
| `button_hover` | `#EAF3FB` |
| `selection` | `#D6E6F5` |
| `metric_good` | `#4E8F5A` |
| `metric_warning` | `#D49A32` |
| `metric_danger` | `#C65A5A` |
| `save_dirty_bg` | `#FFF4D6` |
| `save_dirty_border` | `#D49A32` |
| `save_dirty_text` | `#5F3F00` |

---

# LIGHT THEME 2 - Soft Olive

Warmer light theme with muted green accents. This is the place where a soft beige feel is acceptable.

## Backgrounds

| Key | Color | Usage |
|---|---|---|
| `bg` | `#F6F4EF` | Main window background |
| `panel` | `#FFFFFF` | Primary panels and dialogs |
| `panel_alt` | `#EEF3EC` | Cards, alternate table rows |
| `footer` | `#F2EFE8` | Footer/status surfaces |
| `toolbar` | `#F2EFE8` | App command bar |
| `header` | `#E6E0D6` | Table headers |
| `live_bg` | `#E0DED8` | Floorplan/view background |

## Text And Borders

| Key | Color |
|---|---|
| `text` | `#2F312E` |
| `title` | `#262A25` |
| `muted` | `#767A70` |
| `border` | `#D6D0C4` |

## Accent And State Colors

| Key | Color |
|---|---|
| `metric_info` | `#5C7A5A` |
| `button_hover` | `#DDE8DA` |
| `selection` | `#DDE8DA` |
| `metric_good` | `#4F8A5B` |
| `metric_warning` | `#C99537` |
| `metric_danger` | `#B85C5C` |
| `save_dirty_bg` | `#F5E2B8` |
| `save_dirty_border` | `#C99537` |
| `save_dirty_text` | `#5A3A00` |

---

# DARK THEME 1 - Slate Blue

Recommended dark theme. Technical, readable and neutral enough for colorful RF overlays.

## Backgrounds

| Key | Color | Usage |
|---|---|---|
| `bg` | `#1E2329` | Main window background |
| `panel` | `#262C33` | Primary panels and dialogs |
| `panel_alt` | `#303741` | Cards, alternate table rows |
| `footer` | `#262C33` | Footer/status surfaces |
| `toolbar` | `#262C33` | App command bar |
| `header` | `#303741` | Table headers |
| `live_bg` | `#151A20` | Floorplan/view background |

## Text And Borders

| Key | Color |
|---|---|
| `text` | `#E6EAF0` |
| `title` | `#F2F5F8` |
| `muted` | `#B8C0CC` |
| `border` | `#3D4652` |

## Accent And State Colors

| Key | Color |
|---|---|
| `metric_info` | `#5C8DFF` |
| `button_hover` | `#394453` |
| `selection` | `#334766` |
| `metric_good` | `#63B37A` |
| `metric_warning` | `#D8A24A` |
| `metric_danger` | `#D36B6B` |
| `save_dirty_bg` | `#674B1E` |
| `save_dirty_border` | `#D8A24A` |
| `save_dirty_text` | `#FFFFFF` |

---

# DARK THEME 2 - Graphite Green

Calm dark theme with a softer graphite/green identity.

## Backgrounds

| Key | Color | Usage |
|---|---|---|
| `bg` | `#202422` | Main window background |
| `panel` | `#2A2F2C` | Primary panels and dialogs |
| `panel_alt` | `#343A36` | Cards, alternate table rows |
| `footer` | `#2A2F2C` | Footer/status surfaces |
| `toolbar` | `#2A2F2C` | App command bar |
| `header` | `#343A36` | Table headers |
| `live_bg` | `#171B19` | Floorplan/view background |

## Text And Borders

| Key | Color |
|---|---|
| `text` | `#E5E8E4` |
| `title` | `#F0F3EF` |
| `muted` | `#BCC3BC` |
| `border` | `#414A44` |

## Accent And State Colors

| Key | Color |
|---|---|
| `metric_info` | `#6FA77B` |
| `button_hover` | `#3E4A42` |
| `selection` | `#39483E` |
| `metric_good` | `#73C287` |
| `metric_warning` | `#D1A14A` |
| `metric_danger` | `#C86A6A` |
| `save_dirty_bg` | `#62491D` |
| `save_dirty_border` | `#D1A14A` |
| `save_dirty_text` | `#FFFFFF` |

---

# UI Notes

## Borders

Use low-contrast 1px borders only where they help separate panels. Avoid heavy boxed layouts.

## Radius

- Small controls: `4px` to `6px`
- Cards/panels: `6px` to `10px`
- Dialogs: `10px` to `12px`

## Typography

Primary UI font remains Segoe UI through the Qt stylesheet.

Avoid condensed, futuristic or decorative fonts. Use monospace only for raw values if a future view needs it.

## Heatmap Visualization

The generated and live maps already use strong red/yellow/green/cyan/blue data colors. UI accents should remain desaturated and secondary so RF data stays visually dominant.
