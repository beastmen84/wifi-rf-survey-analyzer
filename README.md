# WiFi Heatmap

Desktop application for Wi-Fi RF surveying, live map analysis, AP behavior
inspection, and PDF reporting.

The project is aimed at practical field surveys: collect real measurements on a
floor plan, preserve the raw scan data, model AP groups and roles, validate the
survey quality, and export maps that explain what was found.

## Current Status

- Active UI: PySide6.
- Main entry point: `main.py`.
- Main workspace: `qt_ui/qt_app.py`.
- Current survey format: V2 CSV plus a linked `.scan` raw-data sidecar.
- Legacy Tkinter UI and old PNG/CSV map export are no longer part of the active
  workflow.
- Help content still needs a final rewrite after the V2 workflow is stable.

## Main Workflow

1. Start a new survey or open an existing V2 survey CSV.
2. Load a floor plan image or PDF.
3. Optionally calibrate scale by selecting two known points and entering meters.
4. Select relevant SSIDs for quality checks and focused analysis.
5. Place measurement points on the floor plan.
6. The app performs repeated Wi-Fi scans and stores all detected networks.
7. Review points, AP groups, metadata warnings, and survey quality.
8. Use the Live Map tab for Coverage, Interference, AP Channels, and Dominant AP.
9. Export the current live map as a PDF report.

## Survey Data

Survey data is stored in a readable CSV file with metadata comments at the top.
Raw scan rows are stored in a linked sidecar file:

```text
survey.csv
survey_raw_data.scan
```

The main CSV stores aggregated point measurements. The raw sidecar preserves the
scan samples used to build those measurements.

Stored metadata can include:

- floor-plan path;
- raw sidecar path;
- scale calibration (`px_per_meter`);
- relevant SSIDs;
- AP groups, roles, aliases, metadata, and positions;
- creation/version fields.

Collected scan fields include:

- timestamp;
- point x/y coordinates;
- SSID and BSSID;
- signal percent and dBm;
- median/min/max dBm;
- raw signal samples;
- samples seen / total attempts;
- scan confidence;
- channel and channel width;
- band and frequency where available;
- optional lswifi details such as security, PMF, vendor, model, AP name,
  country code, station count, channel utilization, Wi-Fi modes, and amendments.

## Wi-Fi Scanning

The scanner uses `lswifi` when available and falls back to Windows `netsh`.
Each measurement point can run multiple scan attempts to reduce partial scan
results and beacon timing artifacts.

The scanner records all visible networks. Relevant SSIDs are a separate user
selection used to decide which networks matter for quality checks and map
interpretation.

2.4 GHz, 5 GHz, and 6 GHz bands are supported in the data model and live maps.
When explicit band/frequency data is unavailable, the app falls back to
conservative channel-based inference.

## AP Groups And Roles

The AP Group Manager builds automatic groups from detected BSSIDs, then lets the
user refine them manually.

Supported AP group data:

- alias;
- role;
- BSSID membership;
- expected bands and channels;
- vendor/model/AP name metadata;
- physical AP position on the floor plan.

Supported roles:

- `internal`: APs that belong to the surveyed network.
- `external`: neighboring APs that can be observed but are outside the managed
  network.
- `interferer`: APs that should be treated as interference sources.
- `test/hidden`: APs intentionally hidden from user-facing analysis.

Test/hidden AP groups are excluded from coverage, channel, dominant AP, and AP
group filter logic. Grouping also prevents guest/main SSIDs on the same physical
AP from being treated as mutual interference when they are modeled correctly.

## Survey Quality

The quality system flags points and project-level issues before maps are trusted.

Current checks include:

- missing relevant SSIDs;
- low scan confidence;
- unstable signal samples;
- sparse measurement data;
- AP metadata inconsistencies;
- AP group conflicts;
- AP positioning warnings for dominant AP analysis.

The Survey Quality Dashboard summarizes good/review points, relevant SSID
coverage, AP group state, and actionable warnings.

## Live Maps

The Live Map tab renders the current survey using the selected SSID, band, AP
group, and map-specific options.

Available live maps:

- Coverage;
- Interference;
- AP Channels;
- Dominant AP / roaming.

Live map behavior:

- manual update and auto update;
- app-bar zoom, pan, and fit controls;
- map-specific left options overlay;
- per-survey memory for map options;
- continuous color scale overlay for Coverage and Interference;
- discrete legends for AP Channels and Dominant AP;
- click-to-highlight and double-click-to-focus in discrete legends;
- background rendering and result caching for heavier maps;
- positioned AP markers on maps where useful.

Continuous maps support interpolation, smoothing, color scale, max distance, and
usable-signal filtering where relevant. Interference and discrete maps expose
only the options that make sense for that map type.

## PDF Export

The active export workflow is PDF export from the Live Map toolbar.

Export behavior:

- asks where to save the file;
- uses the current live map type and options;
- renders the full floor-plan extent, independent of current viewport zoom/pan;
- includes scale or legend information without overlapping the map;
- flattens map pages to avoid accidental page-image selection in PDF viewers;
- uses survey-style point sizing;
- includes positioned AP markers where applicable.

Map-specific PDF behavior:

- Coverage: map page only, no problem report.
- Interference: map page plus paged issue cards for high-risk points.
- AP Channels: map page with compact de-duplicated legend.
- Dominant AP: map page and dominant/AP-position reporting where applicable.

## Project Structure

The codebase is grouped by domain:

```text
main.py                 application entry point
app_core/               settings, logging, restart, constants, filename helpers
ap/                     AP grouping, metadata checks, conflicts, positioning
exporting/              live-map PDF export, report pages, PDF writer
maps/                   map config, heatmap math, rendering, quality engine
qt_ui/                  PySide6 UI, workspace, dialogs, live-map view
survey/                 survey CSV and raw sidecar persistence
translations/           language dictionaries and i18n helpers
wifi/                   scanner backends, band helpers, signal conversion
tests/                  unit and UI-level regression tests
```

## Installation

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux / macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running

```bash
python main.py
```

`main.py` opens a lightweight start screen and loads the heavier Qt workspace in
the background before enabling survey actions.

## Testing

Run the full test suite:

```bash
python -m pytest tests
```

Useful focused test groups:

```bash
python -m pytest tests/test_live_maps.py
python -m pytest tests/test_survey_quality.py
python -m pytest tests/test_scanner_services.py
python -m pytest tests/test_workspace_ui.py
```

## Building

Build the Windows executable with PyInstaller:

```bash
python -m PyInstaller -y WifiHeatmap.spec
```

Output:

```text
dist/WifiHeatmap/WifiHeatmap.exe
```

## Technologies

- Python
- PySide6
- PyMuPDF
- Pillow
- Pandas
- NumPy
- SciPy
- Matplotlib
- lswifi
- PyInstaller
- pytest

## Remaining Work

Near-term work is tracked in `docs/V2_ARCHITECTURE_NOTES.md`.

Current priorities include:

- validate and polish the remaining live-map PDF exports on real surveys;
- improve AP Group Manager ergonomics for large surveys;
- expand combined reporting beyond one map at a time;
- use AP metadata more deeply in diagnostics;
- rewrite Help content after the workflow stabilizes.

## Philosophy

Most professional Wi-Fi survey tools are expensive, closed-source, and difficult
to customize.

This project explores how far a transparent Python-based tool can go while
remaining understandable, inspectable, and adaptable. The goal is not only
generating good-looking heatmaps, but explaining the RF behavior and scan
reliability behind them.

## Author

Davide Marchi
