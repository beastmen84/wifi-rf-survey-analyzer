# Wi-Fi RF Survey Analyzer

Desktop application for Wi-Fi RF surveying, live map analysis, AP modeling,
survey-quality review, RF recommendations, and PDF/HTML reporting.

Wi-Fi RF Survey Analyzer is built for practical field surveys: load a floor
plan, collect real Wi-Fi measurements, preserve raw scan evidence, model
physical APs, review survey quality, and export explainable RF maps.

![Wi-Fi RF Survey Analyzer start screen](docs/assets/readme_start.png)

## Download

- **Download latest release:** use the
  [GitHub Releases page](https://github.com/beastmen84/wifi-rf-survey-analyzer/releases/latest).
- **Windows build available:** public ZIP builds expose
  `WiFiRFSurveyAnalyzer.exe`; older beta artifacts may still contain the
  historical `WifiHeatmap.exe` name.
- **Not a penetration testing tool:** this app is intended for authorized Wi-Fi
  surveying, troubleshooting and RF analysis, not offensive assessment.

## Release Status

- Current source version: `v1.0.0`
- Release type: stable public source release
- Active UI: PySide6
- Main entry point: `main.py`
- Current survey format: CSV plus linked `.scan` raw-data sidecar
- Windows package: generated in a separate release step from the same source
  tag. Public builds use `WiFiRFSurveyAnalyzer-v<version>-win64.zip`.
- Project license: MPL 2.0 (`MPL-2.0`)

`v1.0.0` is the first stable public source release of the current Qt workflow.
Executable and ZIP artifacts are built separately from the tagged source state.
The development source also includes the upcoming Analysis and recommendations
workflow described below; see the changelog for changes since the stable release.

## Core Features

- PDF/image floor-plan loading with scale calibration.
- New surveys start with a generated, pre-scaled A4 blank plan and grid for
  quick tests when no real floor plan is available. Starting from the app start
  page asks only for metric or imperial units before creating that default
  scale; starting a new survey while another survey is open first asks to save
  the current survey, discard changes, or cancel. The grid overlay shows the
  current square size directly on the map.
- Measurement-point capture with repeated Wi-Fi scans.
- Raw scan preservation in a linked `.scan` sidecar file.
- Relevant SSID selection for focused quality checks and map interpretation.
- AP Group Manager for BSSID grouping, aliases, roles, metadata, expected
  channels, analysis-channel overrides, and physical AP positions.
- Persistent AP Memory for reusing known AP metadata across surveys.
- Survey Quality Dashboard with point-rescan findings, AP model diagnostics,
  clickable KPI point lists, and prioritized "what to fix next" guidance.
- Live Coverage, Interference, AP Channels, and Dominant AP maps.
- A final Analysis and recommendations tab with local rules for channel plans,
  coverage, AP dominance, client roaming and missing survey evidence. Findings
  explain their confidence and link back to measured points.
- Optional manual Boundaries masks for limiting continuous live maps and PDF
  exports to the useful survey area when the floor-plan shape or measured
  perimeter needs explicit control.
- Shared, sectioned tooltips for survey points, Wi-Fi AP markers and live-map
  points, with point-local signal, confidence, channel and AP evidence where
  available.
- PDF export from the current live map, including diagnostic report pages where
  the selected map type supports them.
- Complete analysis-report export as selectable-text PDF or self-contained HTML,
  including objectives, measured evidence and a numbered floor-plan overview.
- English, Italian, French and Spanish UI, Help Center and report wording,
  covering the operating workflow and detailed option behavior.

## Main Workflow

1. Start a new survey or open an existing survey CSV.
2. Choose metric or imperial units, then load a floor plan image/PDF or keep the
   generated scaled A4 plan for tests.
3. Calibrate scale when real-world distances matter.
4. Select relevant SSIDs.
5. Place measurement points on the floor plan, roughly every 2-3 m for
   precise surveys when the space allows.
6. Collect repeated Wi-Fi scans for each point.
7. Review survey quality and fix point-level issues first.
8. Review AP groups, metadata, channel overrides, and AP positions.
9. Use Live Map views to inspect coverage, interference, channels, and roaming.
10. Open Analysis and recommendations, set the coverage target and evidence
    requirements, and review the suggested actions and their supporting points.
11. Export the analysis report as PDF/HTML, or export an individual Live Map as PDF.

## Data Model

Surveys are stored as readable CSV files with metadata comments at the top. Raw
scan rows are stored separately:

```text
survey.csv
survey_raw_data.scan
```

The CSV stores aggregated measurement-point data. The linked `.scan` sidecar is
part of the current survey format and preserves the raw scan samples used to
build those measurements.

Saving prepares the CSV, raw data and any generated images before replacing
the existing files. Failed saves restore the previous file set. If the app is
interrupted during replacement, reopening the CSV recovers the pending save.
Files named `.<survey.csv>.save.*` support locking/recovery; keep pending
recovery files beside the survey until it has reopened successfully.

If a new survey is saved without replacing the generated blank plan, the app
also writes a same-name PNG beside the CSV, for example `survey.csv` and
`survey.png`. If that generated PNG is later replaced by a real floor plan and
the survey is saved again, the obsolete blank PNG is removed.

If a manual Boundaries mask is drawn, it is saved beside the survey as a
same-name `.boundaries.png` file and is reopened with the CSV. An empty or
cleared mask behaves as if no manual boundaries were present.

Stored survey metadata includes floor-plan path, raw sidecar path, scale
calibration, measurement system, relevant SSIDs, AP groups, AP roles, AP
metadata, AP positions, analysis-channel overrides, and product/schema version
fields.

## Wi-Fi Scanning

The scanner uses `lswifi` when available and falls back to Windows `netsh`.
Each point can run multiple scan attempts to reduce partial scan results and
beacon timing artifacts.

The `netsh` fallback reads English, Italian, French and Spanish field labels,
preserves explicit band information, and reports command failures or timeouts.
SSID matching is case-sensitive: `Office` and `office` remain separate networks.

The data model supports 2.4 GHz, 5 GHz, and 6 GHz observations. When explicit
band/frequency data is unavailable, the app uses conservative channel-based
inference.

Survey Quality also flags points where fallback scanner data or missing
channel-width/frequency details may weaken channel-sensitive conclusions such
as Interference, 5 GHz width overlap, or future 6 GHz validation.
When available, connected-BSSID evidence is preserved with survey data for
roaming and sticky-client diagnostics.

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
It separates measurement-point problems from AP model/setup diagnostics, so
users can fix scan evidence before interpreting live maps or PDF reports.

Current checks cover scan confidence, missing relevant networks, sparse or
unstable data, limited scanner details, connected-client roaming evidence, AP
metadata, AP Memory review states, missing AP positions, dominant-AP position
anomalies, and AP channel changes. Local-area AP groups can be scoped per
measurement point, so intentionally zone-only SSIDs are not treated as
whole-building requirements.

The dashboard uses KPI cards, filtered point lists, and detail dialogs to keep
large surveys readable. Full behavior and review guidance are documented in the
in-app Help Center.

## Live Maps And PDF Reports

Available live maps:

- Coverage
- Interference
- AP Channels
- Dominant AP / roaming

Coverage and Interference use continuous color scales. AP Channels and Dominant
AP use discrete legends with highlight/focus behavior. Map options are scoped
to the selected map type so only relevant controls are shown.

For AP Channels and Dominant AP maps, legend point lists can highlight and
focus a specific measurement point. Focus uses the configured Go to Point zoom
and centers the selected point in the live-map viewport.

Continuous Coverage and Interference maps can use Survey Bounds to reduce
visual extrapolation outside the measured area. When a manual Boundaries mask
exists, that mask defines the valid map area and Survey Bounds is enabled and
locked for live maps and PDF export.

PDF export uses the current live map type and options, renders the floor-plan
area independently from the current viewport zoom/pan, trims excessive uniform
background below the plan when safe, includes scale or legend information, and
adds diagnostic pages for Interference and Dominant AP reports when applicable.

## Survey Analysis And Recommendations

The final tab analyzes the whole current survey using deterministic local rules.
Select the relevant SSIDs and confirm AP grouping, roles and positions first.
Live Map filters do not restrict the analysis. The category filter helps browse
findings; exports include the complete report.

Set the coverage target, minimum scan confidence, minimum supporting points,
and candidate channels usable by your APs. The default 2.4 GHz candidates are
1, 6 and 11. For 5/6 GHz, enter candidates explicitly to enable precise channel
proposals; an empty list keeps that band in review mode. Objectives apply to
the current app session and are included in exports.

Channel suggestions form one coordinated plan for the observed physical APs.
Unmanaged APs remain fixed neighbors. Incomplete width/frequency evidence,
changing channels, low confidence or conflicting metadata trigger verification
guidance instead of an unsupported precise change. Dominance and roaming
findings recommend controlled checks, with a power-balance trial only when
repeated measurements and alternative coverage support it.

Every finding includes an action, evidence and its limits. These are advisory
results: the app applies no AP configuration changes and uses no AI or remote
service. Signal overlap is a modeled risk rather than a throughput/airtime
measurement. Placement checks do not predict an exact new location or power
level. Verify changes on site and repeat the referenced measurements.

PDF and HTML share the same report snapshot. Export is blocked while scanning,
analyzing or after relevant data/objectives change until the report is current.

## Help Center

The in-app Help Center is the detailed usage guide for the current Qt workflow.
It is available in English, Italian, French and Spanish and covers:

- recommended survey workflow;
- map controls;
- survey and scanning behavior;
- Survey Quality Dashboard;
- AP Groups, AP metadata, and AP Memory;
- Live Maps;
- analysis recommendations and PDF/HTML reports;
- diagnostics/warnings;
- glossary.

The README intentionally stays high-level. Detailed option behavior, warning
meaning, measurement-system effects, AP Memory states, and map/report
interpretation rules are documented inside the app.

## Project Structure

```text
main.py                 application entry point
LICENSE                 project license text
THIRD_PARTY_LICENSES    third-party dependency license summary
requirements.txt        direct development/runtime dependencies
requirements-dev.txt    runtime dependencies plus test/build tooling
requirements-lock.txt   pinned environment used for reproducible release checks
app_core/               settings, logging, restart, version, constants
ap/                     AP grouping, metadata checks, conflicts, positioning
advisor/                local recommendation rules, evidence models, presentation
exporting/              live-map PDF and analysis PDF/HTML reports
maps/                   map config, heatmap math, rendering, quality engine
qt_ui/                  PySide6 UI, workspace, dialogs, live-map view
survey/                 CSV/raw persistence and shared local-area scope rules
translations/           language dictionaries and i18n helpers
wifi/                   scanner backends, band helpers, signal conversion
tests/                  unit and UI-level regression tests
docs/                   architecture notes
```

## Installation

The development environment is validated with **CPython 3.15.2 on Windows x64**.
Create and activate a fresh Python 3.15 virtual environment.

Windows (PowerShell):

```powershell
py -3.15 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux / macOS:

```bash
python3.15 -m venv .venv
source .venv/bin/activate
```

When upgrading an existing installation, use a separate environment folder
(for example `.venv315`) and select its interpreter in your IDE. Reinstall the
dependencies there; retain the previous environment if you need a fallback.
Open a new terminal after changing the IDE interpreter so it activates the
selected environment.

Install runtime dependencies:

```bash
pip install -r requirements.txt
```

For development, tests and Windows packaging, install:

```bash
pip install -r requirements-dev.txt
```

For reproducible release validation, install the pinned environment:

```bash
pip install -r requirements-lock.txt
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
dist/WiFiRFSurveyAnalyzer/WiFiRFSurveyAnalyzer.exe
```

For distribution, publish the zipped PyInstaller `onedir` folder with the
release version in the file name:

```text
dist/WiFiRFSurveyAnalyzer-v<version>-win64.zip
```

The `onedir` format is intentional for this PySide6/scientific stack. It starts
faster than `onefile`, avoids extracting a large app to a temp directory on each
run, and tends to be less fragile with Qt plugins and antivirus heuristics.

Release builds use `images/app_icon.png` as the app/window icon source and
embed the generated `images/app_icon.ico` into the Windows executable.
Packaged Windows ZIP files also include `LICENSE`, `THIRD_PARTY_LICENSES`,
`README.md`, and `CHANGELOG.md` beside the application files.

## Versioning And Changelog

Public releases use semantic version tags. `CHANGELOG.md` tracks changes
between official release builds.

Current source release:

- `v1.0.0`

Expected Windows ZIP name:

- `WiFiRFSurveyAnalyzer-v1.0.0-win64.zip`

Historical beta ZIPs may still use the older artifact stem:

- `WifiHeatmap-v<version>-win64.zip`

## Roadmap

Possible future product areas:

- Broader recommendation rules validated against additional real surveys.
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

## Development Approach

This project was developed with extensive help from AI-assisted coding tools,
primarily OpenAI Codex/ChatGPT, to accelerate implementation, refactoring,
debugging and UI iteration.

Feature direction, real-world survey testing, RF interpretation, validation and
release decisions were driven manually through practical field use.

## License

This project is licensed under the Mozilla Public License 2.0 (`MPL-2.0`).

The software is provided as-is, without warranty of any kind. Third-party
dependencies retain their own licenses; see `THIRD_PARTY_LICENSES`.
Executable releases should point recipients to the corresponding source tag or
repository state for the released build.

## Disclaimer

This software is intended for legitimate Wi-Fi analysis, surveying and
troubleshooting activities on networks you own or are authorized to assess.

The author assumes no responsibility for misuse of the software.

## Third-Party Credits

This project uses PySide6/Qt, matplotlib, numpy, scipy, pandas, Pillow, lswifi
and related packaging/test dependencies. See
`THIRD_PARTY_LICENSES` for the current dependency license summary.

## Author

Davide Marchi
