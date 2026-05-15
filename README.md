# WiFi Heatmap

Desktop application for Wi-Fi RF surveying, live map analysis, AP modeling,
survey-quality review, and PDF reporting.

WiFi Heatmap is built for practical field surveys: load a floor plan, collect
real Wi-Fi measurements, preserve raw scan evidence, model physical APs, review
survey quality, and export explainable RF maps.

## Release Status

- Current version: `v0.9.3-beta.2`
- Release type: beta / pre-release
- Active UI: PySide6
- Main entry point: `main.py`
- Current survey format: CSV plus linked `.scan` raw-data sidecar
- Latest Windows release ZIP: `WifiHeatmap-v0.9.2-beta.1-win64.zip`

The current beta is intended for real-world validation of the Qt workflow. A
stable `v1.0.0` is planned after Help Center review and broader field testing.

## Core Features

- PDF/image floor-plan loading with scale calibration.
- Measurement-point capture with repeated Wi-Fi scans.
- Raw scan preservation in a linked `.scan` sidecar file.
- Relevant SSID selection for focused quality checks and map interpretation.
- AP Group Manager for BSSID grouping, aliases, roles, metadata, expected
  channels, analysis-channel overrides, and physical AP positions.
- Persistent AP Memory for reusing known AP metadata across surveys.
- Survey Quality Dashboard with point-rescan findings, AP model diagnostics,
  clickable KPI point lists, and prioritized "what to fix next" guidance.
- Live Coverage, Interference, AP Channels, and Dominant AP maps.
- PDF export from the current live map, including diagnostic report pages where
  the selected map type supports them.
- English and Italian Help Center covering the operating workflow and detailed
  option behavior.

## Main Workflow

1. Start a new survey or open an existing survey CSV.
2. Load a floor plan image or PDF.
3. Calibrate scale when real-world distances matter.
4. Select relevant SSIDs.
5. Place measurement points on the floor plan.
6. Collect repeated Wi-Fi scans for each point.
7. Review survey quality and fix point-level issues first.
8. Review AP groups, metadata, channel overrides, and AP positions.
9. Use Live Map views to inspect coverage, interference, channels, and roaming.
10. Export the selected live map as a PDF report.

## Data Model

Surveys are stored as readable CSV files with metadata comments at the top. Raw
scan rows are stored separately:

```text
survey.csv
survey_raw_data.scan
```

The CSV stores aggregated measurement-point data. The `.scan` sidecar preserves
the raw scan samples used to build those measurements.

Stored survey metadata includes floor-plan path, scale calibration, relevant
SSIDs, AP groups, AP roles, AP metadata, AP positions, analysis-channel
overrides, and product/schema version fields.

## Wi-Fi Scanning

The scanner uses `lswifi` when available and falls back to Windows `netsh`.
Each point can run multiple scan attempts to reduce partial scan results and
beacon timing artifacts.

The data model supports 2.4 GHz, 5 GHz, and 6 GHz observations. When explicit
band/frequency data is unavailable, the app uses conservative channel-based
inference.

Survey Quality also flags points where fallback scanner data or missing
channel-width/frequency details may weaken channel-sensitive conclusions such
as Interference, 5 GHz width overlap, or future 6 GHz validation.

## AP Modeling

AP groups represent physical access points rather than isolated BSSIDs. This
prevents guest/main SSIDs from the same AP being treated as mutual interference
when the AP is modeled correctly.

Supported AP roles:

- `internal`: managed APs that belong to the surveyed network.
- `external`: neighboring APs observed during the survey.
- `interferer`: APs treated as interference sources.
- `test/hidden`: APs intentionally excluded from user-facing analysis.

AP Memory stores known aliases, roles, metadata, channel overrides, and
compatible map positions in the application data folder. When known BSSIDs are
seen again, remembered AP data can be applied automatically and remains flagged
for review until confirmed or edited.

## Quality Review

The Survey Quality Dashboard is designed to be reviewed before trusting maps.
It separates measurement-point problems from AP model/setup diagnostics.

Current checks include missing relevant networks, low scan confidence, unstable
signals, sparse point data, limited scanner details, AP metadata warnings, AP
Memory review states, AP group conflicts, missing AP positions, dominant-AP
position anomalies, and AP channel changes that affect channel-sensitive maps.
Point-related KPI cards open fitted filtered point lists with concise
KPI-specific issue text, so larger surveys keep the main dashboard focused on
readable KPI groups, survey context, and next actions.

## Live Maps And PDF Reports

Available live maps:

- Coverage
- Interference
- AP Channels
- Dominant AP / roaming

Coverage and Interference use continuous color scales. AP Channels and Dominant
AP use discrete legends with highlight/focus behavior. Map options are scoped
to the selected map type so only relevant controls are shown.

PDF export uses the current live map type and options, renders the full
floor-plan extent, includes scale or legend information, and adds diagnostic
pages for Interference and Dominant AP reports when applicable.

## Help Center

The in-app Help Center is the detailed usage guide for the current Qt workflow.
It is available in English and Italian and covers:

- recommended survey workflow;
- map controls;
- survey and scanning behavior;
- Survey Quality Dashboard;
- AP Groups, AP metadata, and AP Memory;
- Live Maps;
- PDF reports;
- diagnostics/warnings;
- glossary.

The README intentionally stays high-level. Detailed option behavior, warning
meaning, measurement-system effects, AP Memory states, and map/report
interpretation rules are documented inside the app.

## Project Structure

```text
main.py                 application entry point
app_core/               settings, logging, restart, version, constants
ap/                     AP grouping, metadata checks, conflicts, positioning
exporting/              live-map PDF export and report pages
maps/                   map config, heatmap math, rendering, quality engine
qt_ui/                  PySide6 UI, workspace, dialogs, live-map view
survey/                 survey CSV and raw sidecar persistence
translations/           language dictionaries and i18n helpers
wifi/                   scanner backends, band helpers, signal conversion
tests/                  unit and UI-level regression tests
docs/                   architecture notes
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

`main.py` opens the start screen and loads the Qt workspace in the background
before enabling survey actions.

## Testing

Run the full test suite:

```bash
python -m pytest tests
```

Useful focused groups:

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

For distribution, publish the zipped PyInstaller `onedir` folder:

```text
dist/WifiHeatmap-v0.9.3-beta.2-win64.zip
```

The `onedir` format is intentional for this PySide6/scientific stack. It starts
faster than `onefile`, avoids extracting a large app to a temp directory on each
run, and tends to be less fragile with Qt plugins and antivirus heuristics.

Release builds use `images/app_icon.png` as the app/window icon source and
embed the generated `images/app_icon.ico` into the Windows executable.

## Versioning And Changelog

Public releases use semantic version tags. `CHANGELOG.md` tracks changes
between official release builds.

Current release:

- `v0.9.3-beta.2`

Latest Windows release ZIP:

- `WifiHeatmap-v0.9.2-beta.1-win64.zip`

## Roadmap

Before `v1.0.0`:

- finish Help Center review in the running UI;
- run broader real-world validation on operational survey data;
- fix concrete issues found during that review/test cycle.
- refine relevant-network scope for local/zone-only SSIDs.

Possible future product areas:

- AI Advisor for measured-data-based RF recommendations.
- Built-in floorplan creator for lightweight technical survey drawings.
- Combined survey report across multiple live-map views.
- Deeper AP metadata diagnostics where rules are clear.
- Further AP physical/radio/BSSID model refinement if real deployments require
  it.
- Performance tuning after larger real surveys expose measurable bottlenecks.

## Philosophy

Most professional Wi-Fi survey tools are expensive, closed-source, and difficult
to customize.

This project explores how far a transparent Python-based tool can go while
remaining understandable, inspectable, and adaptable. The goal is not only to
generate heatmaps, but to explain the RF behavior and scan reliability behind
them.

## Author

Davide Marchi
