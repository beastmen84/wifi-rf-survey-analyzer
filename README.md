# WiFi Heatmap

Desktop application for Wi-Fi RF surveying, live map analysis, AP behavior
inspection, survey-quality review, and PDF reporting.

The tool is built for practical field surveys: collect real measurements on a
floor plan, preserve the raw scan evidence, model physical AP groups, validate
the survey before trusting maps, and export explainable RF reports.

## Release Status

- Public version: `v0.9.1-beta.1`.
- Release type: beta / pre-release.
- Active UI: PySide6.
- Main entry point: `main.py`.
- Current survey format: CSV plus a linked `.scan` raw-data sidecar.
- Legacy Tkinter UI and the old generated PNG/CSV map export are no longer part
  of the active workflow.

The current beta is intended for real-world validation of the current Qt
workflow. A stable `v1.0.0` will follow after the Help Center review and broader
field testing are complete.

Release builds use the app icon from `images/app_icon.png`; the Windows
executable embeds the generated `images/app_icon.ico`, and the start screen
shows the same icon next to the product name.

## What It Does

- Loads a PDF/image floor plan and stores it with the survey.
- Calibrates map scale from two known-distance points.
- Captures measurement points with repeated Wi-Fi scans.
- Stores both aggregated point rows and raw scan samples.
- Tracks relevant SSIDs separately from all observed networks.
- Builds AP groups from BSSIDs and lets the user refine them manually.
- Stores AP aliases, roles, metadata, expected bands/channels, analysis channel
  overrides, and physical AP positions.
- Reuses known AP metadata through a persistent AP Memory file and flags reused
  data for review before it is treated as confirmed.
- Reviews survey quality before maps are trusted.
- Renders live Coverage, Interference, AP Channels, and Dominant AP maps.
- Exports the current live map to PDF, including issue-report pages where the
  map type has diagnostics.
- Provides an expanded Help Center in English and Italian.

## Main Workflow

1. Start a new survey or open an existing survey CSV.
2. Load a floor plan image or PDF.
3. Calibrate scale when real-world distances matter.
4. Select relevant SSIDs for quality checks and focused analysis.
5. Place measurement points on the floor plan.
6. Let the app run repeated Wi-Fi scans and store all detected networks.
7. Review survey quality, then AP groups, AP metadata, and AP positions.
8. Use Live Map views for Coverage, Interference, AP Channels, and Dominant AP.
9. Export the selected live map as a PDF report.

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
- AP groups, roles, aliases, metadata, positions, and analysis channel
  overrides;
- creation/schema/product version fields.

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
- optional `lswifi` details such as security, PMF, vendor, model, AP name,
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
- analysis channel override per observed band;
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

Clean AP channel changes during a survey are modeled separately from AP group
conflicts. Channel-sensitive maps use the latest observed channel by default,
while AP metadata can force a known-good analysis channel when the survey-time
channel change does not represent the intended operational model.

The app also keeps a persistent AP Memory file in the application data folder.
When a later survey sees known BSSIDs, the normal AP grouping runs first and
then remembered aliases, roles, metadata, analysis-channel overrides, and
compatible floor-plan positions can be applied automatically. Reused AP data is
marked as "From Memory" in AP Group Manager until the user confirms it or edits
the AP data. If a previously manual AP Group has different saved data available
in AP Memory, AP Group Manager marks it as a memory update candidate and offers
an explicit "Update From Memory" action. The workspace footer shows whether AP
Memory is empty, saved, or has memory-applied groups still waiting for
confirmation. The AP Group Manager toolbar groups memory actions under a
dedicated Memory menu, and the Settings popup can open the AP Memory folder or
clear AP Memory with an app-styled destructive-action confirmation in both the
start screen and the main workspace.

## Survey Quality

The Survey Quality Dashboard flags point-level and project-level issues before
maps are trusted.

Current checks include:

- missing relevant SSIDs;
- low scan confidence;
- unstable signal samples;
- sparse measurement data;
- AP metadata inconsistencies;
- AP metadata applied from memory and still awaiting confirmation;
- AP group conflicts;
- missing AP positions;
- dominant AP / physical-position anomalies;
- clean or ambiguous AP channel changes that affect channel-sensitive maps.

The dashboard separates point-rescan issues from AP setup/model diagnostics.
It shows KPI cards, defaults to showing only points that need review when such
points exist, and provides "what to fix next" guidance with detail dialogs and
shortcuts into the relevant map or AP metadata workflow.

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
- Dominant AP: map page plus roaming/AP-position issue reporting where
  applicable.

## Help Center

The app includes a Help Center with structured sections for:

- recommended survey workflow;
- map controls;
- survey/scanning behavior;
- Survey Quality Dashboard;
- AP Groups and AP metadata;
- live maps;
- PDF reports;
- diagnostics/warnings;
- glossary.

This help content is implemented in English and Italian. The remaining beta
work is a calm visual/content review in the running app, not a missing feature.
The Help Center now documents AP Memory review states, confirmation/update
actions, settings access, and AP Group Manager save behavior. Its non-control
pages describe the current Qt workflow in more detail: survey screen boxes,
Survey Quality actions, AP Group Manager layers, BSSID management, metadata,
Live Map options, PDF export behavior, warning diagnostics, and glossary terms.
The Survey help page uses compact summary cards for the main screen boxes and
explicitly explains relevant SSIDs, the `.scan` sidecar, scanner backend choice,
point-table actions, and point-placement rules.
The Survey Quality help page now mirrors the dashboard workflow with point/AP
model layers, grouped KPI explanations, priority gates, and scalable detail
dialog guidance.
The AP Groups help page now explains the evidence-to-model workflow, BSSID
Manager actions, roles, metadata, channel overrides, clean channel changes, and
AP Memory states with compact cards instead of long reference tables. Its
workflow card rows use the same spacing structure as the other Help pages.
The Live Maps help page uses the same card-based structure for toolbar actions,
map-type selection, visible option sets, option meanings, and map-reading
limits.
The PDF Reports help page now explains export save behavior, output naming,
full-map rendering, map-type page composition, diagnostic cards, and final
review checks with the same card/gate structure.
The Warnings help page now distinguishes point-rescan findings, AP model
warnings, metadata/channel warnings, channel-change behavior, and map-reading
troubleshooting with card/gate guidance.
Help tables and callouts are rendered at full content width in the Qt Help
Center with fixed accent columns, so highlighted blocks align consistently with
the surrounding page.
The recommended workflow page uses visual step cards and decision-gate rows
with consistent page margins, tuned for the Qt Help renderer. The main toolbar
follows the same validation order by placing Survey Quality before AP Groups.

## Project Structure

```text
main.py                 application entry point
app_core/               settings, logging, restart, version, constants
ap/                     AP grouping, metadata checks, conflicts, positioning
exporting/              live-map PDF export, report pages, PDF writer
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

For distribution, publish the zipped PyInstaller `onedir` folder:

```text
dist/WifiHeatmap-v0.9.1-beta.1-win64.zip
```

The `onedir` format is intentional for this PySide6/scientific stack. It starts
faster than `onefile`, avoids extracting a large app to a temp directory on each
run, and tends to be less fragile with Qt plugins and antivirus heuristics.

## Versioning And Changelog

Public releases use semantic version tags. `CHANGELOG.md` tracks user-facing
changes between official release builds.

Current release:

- `v0.9.1-beta.1`

## Roadmap

Before `v1.0.0`:

- review and polish the Help Center in the running UI;
- run broader real-world validation on operational survey data;
- fix only concrete issues found during that review/test cycle.

Near-term polish:

- validate AP Memory behavior on larger repeat surveys and add a dedicated
  memory-management view only if real usage shows it is needed.

Future expansion candidates:

- combined survey report across multiple live-map views;
- deeper AP metadata diagnostics where the rule is clear;
- real 6 GHz / Wi-Fi 6E/7 hardware validation;
- AP physical/radio/BSSID model refinement if real deployments require it;
- performance tuning only after larger real surveys expose measurable lag.

Two larger product ideas are intentionally kept out of the current beta:

- AI Advisor: an analysis panel beside each live map that reviews the survey
  evidence and proposes actionable RF changes, such as channel-width or channel
  adjustments to reduce interference. Recommendations should be grounded in the
  measured data, explain their reasoning, include confidence/assumptions, and
  remain advisory rather than silently changing the model.
- Floorplan Creator: a lightweight technical drawing board for creating a
  survey floor plan directly inside the app. The goal is not interior design,
  but functional RF geometry: scaled walls, measurements, snap, doors,
  orthogonal/shape tools, and wall thickness sufficient to produce a usable
  survey map.

## Philosophy

Most professional Wi-Fi survey tools are expensive, closed-source, and difficult
to customize.

This project explores how far a transparent Python-based tool can go while
remaining understandable, inspectable, and adaptable. The goal is not only
generating good-looking heatmaps, but explaining the RF behavior and scan
reliability behind them.

## Author

Davide Marchi
