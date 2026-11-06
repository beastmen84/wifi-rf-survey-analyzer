# Wi-Fi RF Survey Analyzer

Desktop application for Wi-Fi RF surveying, live map analysis, AP modeling,
survey-quality review, RF recommendations, and offline HTML reporting.

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

- Current source version: `v1.2.0`
- Release type: stable public source release
- Active UI: PySide6
- Main entry point: `main.py`
- Current survey format: CSV plus linked `.scan` raw-data sidecar
- Windows package: generated in a separate release step from the same source
  tag. Public builds use `WiFiRFSurveyAnalyzer-v<version>-win64.zip`.
- Project license: MPL 2.0 (`MPL-2.0`)

`v1.2.0` adds a fixed Wi-Fi receiver per survey, guided measurement capture and
separate acquisition reliability, signal stability and observed coverage.
Relevant networks are chosen before reviewing a capture; compact review cards
and immediate point popups make the results easier to read. `v1.1.0` introduced
the final Analysis workflow and offline HTML map and analysis reports.
The pre-release [data-accuracy audit](docs/AUDIT_1_1_0.md) records the precision
fixes and their verification, including live scan-freshness checks. Controlled
field validation, receiver calibration and 6 GHz hardware checks remain separate
from these software checks.

## Core Features

- PDF/image floor-plan loading with scale calibration.
- New surveys start with a generated, pre-scaled blank plan and grid for
  use when no real floor plan is available. Starting from the app start
  page asks for metric or imperial units, the Wi-Fi adapter and blank-sheet width
  and height before creating the scale. Starting a new survey while another is
  open first asks to save the current survey, discard changes, or cancel.
  The grid overlay shows the current square size directly on the map.
- Blank sheets start at **35 × 25 m** or **115 × 81 ft**, depending on the units.
  After customizing the dimensions, switching m/ft converts the same physical size.
  Blank-sheet dimensions are preserved with
  the generated PNG on save/reopen. Loading an external floor plan replaces the
  sheet and uses that plan's calibration. The blank sheet has a bottom-left
  Design Mode toolbar for rectangles: right-drag shows live m/ft
  dimensions; a right-click opens exact dimensions, followed by another
  right-click to place the preview. Left-drag pans. Color and undo/redo are
  available. Nearby corners and edges snap automatically, with orange target
  indicators; the grid button adds snapping to the displayed grid. Hold Alt to
  suspend snapping. Numeric placement moves the shape without changing its size.
  Grid snapping considers every real vertex, including all corners of rotated
  shapes and either endpoint of a line, and chooses the nearest valid grid
  intersection. Moving selections use their actual vertices. The orange marker
  identifies the snapped vertex; dimensions and angles remain unchanged.
  During a drag, the moving sides also align with overlapping sides of existing
  shapes, even when the cursor extends beyond them. The starting corner stays
  fixed and orange guides identify the height/width alignment.
  Select Eraser to right-click one highlighted side, or right-drag an area to
  erase every whole segment it touches on release. Red previews show the affected
  sides and their count. Each deletion can be undone/redone as one action.
  Esc cancels a draft
  before exiting the mode. Right-click capture resumes after leaving Design Mode.
  Drawings remain editable after save/reopen and appear in PNG/Live/HTML maps.
  The survey grid fades inside perimeters closed by the current segments,
  including joined, concave and overlapping shapes. Opening a perimeter with
  the eraser restores its normal grid; undo restores the closed appearance.
  This grid styling stays in the survey view and is not baked into exported maps.
  The shapes are visual plan geometry; RF findings still use measured data.
- **Grid square size** is configurable in New Survey: default **1 m** or
  **3 ft**, with **0.1 m** steps or **whole feet**. The physical size is saved in
  the survey and used by the visible grid and every snap tool. Right-click the
  main **Grid** button to change it later. Unit changes round to the input's
  precision. Older surveys keep their automatic spacing until explicitly edited.
- Intersections split editable strokes into individual fragments, including T
  joints and overlapping endpoints. Erase deletes only the chosen fragment.
  Line draws in any direction, including diagonals, by right-drag, or asks only for a length
  before cursor-following placement. **R** rotates both Line and Rectangle
  placement previews by 90 degrees while preserving their dimensions.
  Select Structure uses right-click for one fragment or a right-drag box for all touched
  fragments. **R** rotates the selection around its bounding-box center; **M**
  starts a rigid cursor-following move, confirmed with right-click or cancelled
  with Esc. R also rotates during a move. The selection's box snaps to unselected
  geometry or the optional grid; Alt suspends snapping. Edits share undo/redo,
  recompute closed areas and survive save/reopen, including older drawings.
  A click within about six screen pixels of a stroke picks the single fragment
  first; a click farther inside a closed region selects all its boundary pieces
  and shows its area in **m²/ft²**, including nested holes. Open-space clicks keep
  the selection. Single lines show length, circles radius, and arcs length,
  radius, chord and sagitta. Circular areas use analytic geometry. Selection
  commands are listed one per line in the palette and measurement panel.
  If a move, rotation or erase removes a junction, contiguous straight fragments
  with the same color rejoin automatically. Same-color straight overlaps and
  duplicates also unite, removing artificial cuts at their old endpoints. Cuts
  remain at real junctions, curve contacts, corners, gaps and color transitions;
  overlapping strokes of different colors stay separate.
  Tap and release **R** for a 90-degree turn. Hold **R** and move around the
  orange center for **5-degree steps**: the object stays frozen in place and
  shows equivalent angles such as `(+315° / -45°)`. Release R to apply, or Esc
  to restore its previous orientation. This works on selections, moving groups
  and Line/Rectangle placement previews. Out-of-sheet orientations appear red
  and are rejected. Rotated oblique strokes retain real intersections, snapping,
  partial erasing, closed-area detection and saved/exported geometry.
- Design Mode separates **Structure** from **Annotations**, with independent
  selection tools. Structure selection and the eraser affect walls and curves;
  annotation selection affects markers, doors, windows and text. **Marker** draws
  dashed freehand or grid-following paths with its own color and graphical width.
  **Door** supports single, double and sliding variants; **Window** uses a simple
  window symbol. Choose width before placement, then right-click on a straight
  wall, including oblique walls. Doors have independent hinge and opening-side
  choices shown as seven configuration icons (four single, two double, sliding).
  Only swing arcs are dashed; door leaves remain solid.
  Apertures hide only the covered wall ink: room closure, internal area
  and Boundaries Fill/Auto Fill retain the complete structural geometry.
  Select annotations to move with **M**, delete with **Del**, or edit by right
  double-click / Properties. **R** rotates markers/text by 90° or reverses a swing
  door's opening side. Attached openings follow rigid host moves; deleting their
  support also deletes them in the same undoable edit. Overlapping openings and
  invalid placements are rejected. PNG, Live Map and HTML use the same symbols.
  Structure and Annotations also have their own **eraser**: right-click removes
  one item and right-drag removes the touched items in that layer, including text
  for annotation erasing. Undo restores the same objects and their wall ink.
- With a drawing tool active, hovering over a segment shows the distances from
  endpoint **A** to the cursor and from the cursor to **B**, with matching colored
  dimension lines. Door/window previews separately report the free space before
  and after the opening, so cursor distance is not confused with jamb clearance.
  Quotes use survey m/ft units and stay out of saved/exported geometry.
  **Segment midpoints** and **room centers** are snap targets alongside corners
  and edges. Shapes, text and openings can also snap from their own center; for
  doors/windows this is the midpoint of the opening on the wall. Room centers
  stay inside usable regions, including concave rooms or rooms with holes.
  The grid toggle controls only grid snapping; drawing magnets remain active.
  **Alt** suspends both drawing and grid magnets, while hosted openings still
  require a supporting wall.
- Design Mode **Text** opens a multiline editor with font, size, bold/italic,
  alignment, color, outline and a live preview. Click the sheet with the right
  button to open it; after OK the label follows the cursor until another right
  click places it. R tap/hold rotates its placement preview. Select Annotations
  selects labels alone or with other annotations to move with M or delete with **Del**. Deletion
  is one undoable edit. Right-double-click selected text, or use **Edit selected
  text**, to reopen its editor. Text remains editable after save/reopen and
  appears consistently in generated PNGs, Live Map and both HTML report types.
- Design Mode **Circle** uses a right drag from the center to set the radius,
  or a simple right click to enter it precisely. **Circular arc** uses a right
  drag from A to B for the chord: release, move the pointer to set the bend and
  right-click to confirm. A simple right click instead accepts the chord,
  perpendicular sagitta and side, so the same curve can be reproduced elsewhere.
  Numeric arc previews support R tap/hold; a single circle has no rotation.
  In a mixed/group selection, its center follows the group's rotation.
  Select and right-double-click a curve,
  or use the pencil action, to inspect/change its dimensions. Curves split at
  intersections, rejoin obsolete cuts, and support snapping, partial erasing,
  selection, M, R, Del and undo/redo. Closed curved perimeters also fade the grid
  and work with Boundaries Fill/Auto Fill. Their editable geometry survives
  save/reopen and appears in PNG, Live Map and HTML reports. The measurements
  panel stays at the top right of the drawing viewport, opposite the grid scale.
  With grid snapping active, radius/chord endpoints snap to visible grid
  intersections, and bending makes the arc pass through the chosen grid point
  with its chord fixed. Existing corners take priority and show an orange marker.
  Turn grid snapping off or hold Alt for continuous sizing. Numeric arrows
  adjust by 0.01 m/ft.
  Numeric previews follow slow cursor movements without sticking to the grid.
- On generated blank sheets, **Boundaries** includes **Fill** for one closed
  drawn room and **Auto Fill** for all closed drawn rooms. Fill uses a right
  click inside the area and respects nested rooms; open perimeters do not fill.
  Both add to the existing analysis mask. These controls are hidden on imported
  plans, which retain the existing brush/eraser tools.
- Measurement-point capture with repeated Wi-Fi scans.
- Fixed receiver selection, a short preparation and five scan attempts, followed
  by an explicit Save, Repeat or Discard review. Review and reports distinguish
  acquisition reliability, signal stability and observed coverage.
- Raw scan preservation in a linked `.scan` sidecar file.
- Relevant SSID selection for focused quality checks and map interpretation.
- AP Group Manager for BSSID grouping, aliases, roles, metadata, expected
  channels, analysis-channel overrides, and physical AP positions.
  Click the circle in the first column to confirm that the listed BSSIDs belong
  to one physical AP: green with a check means approved. Save to keep the change.
  Changing BSSIDs, alias, role, position or metadata clears approval; accepting
  unchanged values keeps it. Click a green circle to revoke approval.
  When AP Memory needs review, the first column shows **M** instead of a circle.
  Resolve Memory first: accept recalled data, update from memory, or keep current
  data. The circle then shows whether the group needs physical confirmation.
- Persistent AP Memory for reusing known AP metadata and physical-group approval
  across surveys. Approval is restored only for the exact same BSSIDs; a subset,
  extra BSSID or local revocation requires confirmation. Older memory records
  without approval need an initial confirmation using the circle.
- Survey Quality Dashboard with point-rescan findings, AP model diagnostics,
  clickable KPI point lists, and prioritized "what to fix next" guidance.
- Live Coverage, Interference, AP Channels, and Dominant AP maps.
- A final Analysis and recommendations tab with local rules for channel plans,
  coverage, AP dominance, client roaming and missing survey evidence. Findings
  explain their confidence and link back to measured points.
  Physical-group confirmation is requested once per group transmitting a relevant
  SSID. Other networks remain individual RF neighbors without an approval request;
  their measured channel, width and evidence quality still affect recommendations.
- Optional manual Boundaries masks for limiting continuous live maps and HTML
  exports to the useful survey area when the floor-plan shape or measured
  perimeter needs explicit control.
- Shared, sectioned tooltips for survey points, Wi-Fi AP markers and live-map
  points, with point-local signal, confidence, channel and AP evidence where
  available.
- Standalone HTML export from Live Map, with the same renderer and active
  filters, a numbered map, linked point evidence and visible diagnostic warnings.
- Complete HTML analysis reports with a concise summary, prioritized actions,
  visible evidence limits and expandable measurement/parameter sections.
  Both report types work offline as one file and support printing from the browser.
- Compact Analysis controls: coverage target and report actions remain visible;
  evidence thresholds and channel candidates sit in expandable Analysis settings,
  with active values and applicable missing-channel warnings always visible.
- English, Italian, French and Spanish UI, Help Center and report wording,
  covering the operating workflow and detailed option behavior.

## Main Workflow

1. Start a new survey or open an existing survey CSV.
2. Choose metric or imperial units, a Wi-Fi adapter and the blank-sheet dimensions
   in the New Survey dialog,
   then load a floor plan image/PDF or keep the
   generated scaled blank plan.
3. Calibrate scale when real-world distances matter.
4. Place measurement points on the floor plan, roughly every 2-3 m for
   precise surveys when the space allows.
5. Hold the device still during the short preparation and five guided scans.
6. On the first capture choose relevant SSIDs before the review appears, then
   save, repeat or discard the measurement using feedback for the chosen scope.
7. Review acquisition reliability, signal stability and observed coverage
   separately. Reopen **Measurement details** from a selected saved point, then
   use Survey Quality to fix point-level issues first.
8. Review AP groups, metadata, channel overrides, and AP positions. Confirm the
   groups transmitting relevant networks using the first-column circles, then Save.
9. Use Live Map views to inspect coverage, interference, channels, and roaming.
10. Open Analysis and recommendations, set the coverage target and evidence
    requirements, and review the suggested actions and their supporting points.
11. Use **Export Map** in Live Map or **Export report** in Analysis to save
    standalone HTML. Open the
    report in a browser to inspect details, follow point links or print it.

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
calibration, measurement system, selected receiver ID/name, relevant SSIDs, AP groups, AP roles, AP
metadata, AP positions, analysis-channel overrides, and product/schema version
fields.

New captures preserve the receiver, backend, scan lifecycle and BSS observation
timestamps in CSV/raw evidence. Measurement-point metadata also retains a
successfully completed scan with zero BSS, without inventing an RSSI value.
Older surveys remain readable; missing provenance stays unknown and cannot
authorize precise operational recommendations. Rescan those points when needed.

## Wi-Fi Scanning

New Survey asks for a fixed Wi-Fi receiver alongside units. A single adapter is
preselected; with multiple adapters a connected, ready receiver is suggested.
The saved adapter ID/name is restored on reopening, and the name appears in the
workspace footer. Adapter discovery runs in the background and can be refreshed.
An adapter can scan without joining a network. If no usable receiver is found,
connect or enable one and refresh; existing surveys remain readable.

All point captures and rescans use `lswifi` with that exact receiver ID. An
absent receiver or a failed native scan never silently switches hardware or
falls back to Windows `netsh`. A different receiver requires a separate survey.
Older surveys ask for an explicit receiver before their first new capture;
their existing rows retain their original provenance.

Native captures wait for scan completion and count only fresh, unique BSS
observations across five attempts. Failed requests and cached observations do
not become new samples. Saving a point also checks its receiver against the
survey selection, including raw samples and verified empty captures.

The guided capture displays actual scan progress and keeps results provisional
until **Save point**. Relevant-network selection and any missing/new-network
choices happen before feedback is shown; Save confirms that reviewed scope
without opening another selector. Discard is available during collection; the
current native request completes before the worker releases its resources. Repeating uses a
new, fixed set of five attempts. An existing point is preserved until its
replacement is saved; the app does not automatically repeat until RSSI improves.

The review and saved-point details separate three questions:

- **Acquisition reliability:** completed attempts, unique fresh observations,
  matching receiver and raw evidence. Missing history stays unverified or
  limited; completed scans do not imply that every AP was seen five times.
- **Signal stability:** variation within each strong BSSID/SSID/band candidate,
  requiring at least three verified fresh samples. A range of 12 dB or more is
  flagged. This does not detect device movement or certify receiver calibration.
- **Observed coverage:** the strongest median RSSI per relevant SSID against an
  explicit -70 dBm reference across detected bands. A missing SSID does not
  prove absent coverage. Channel and roaming recommendations remain in Analysis.

The point table labels acquisition reliability explicitly and shows the three
axes for the selected point and in its tooltip. Offline HTML exports retain the
same distinctions in expandable point details. The Analysis report uses its
configured coverage target; point details and Live Map use the -70 dBm reference.
These presentation checks do not replace the RF engine's recommendation guards.

Preparation and scanning use a compact dialog; review expands only when needed.
Review cards place the main result on the left and smaller, wrapped details on
the right. Selected SSIDs are visible in the coverage card. Useful warnings are
shown directly; routine cache-exclusion notes and repeated explanations do not
need an extra disclosure. The review fits its content when screen space allows;
scrolling is retained for genuine overflow, without a redundant details toggle.
Survey hover summaries show up to four SSID names and a remaining
count; the point table retains the full list. Survey tooltips appear immediately
over the painted point, including its selection outline, and stay stationary
while the pointer remains there. They close immediately on exit or map gestures.
The popup does not intercept mouse input, has no automatic expiry and does not
use the standard Qt tooltip delay. In overlapping markers it retains the current
point until that point's outline is left. Pan, zoom and refresh close the popup.

The `netsh` compatibility/diagnostic scanner reads English, Italian, French and Spanish field labels,
preserves explicit band information, and reports command failures or timeouts.
It is an unverified snapshot with estimated dBm, so it cannot establish fresh
independent samples or authorize precise RF changes. Reports distinguish these
estimates from driver RSSI. SSID identity preserves case, spaces and original
bytes, and hidden BSS remain available as RF evidence.

The data model supports 2.4 GHz, 5 GHz, and 6 GHz observations. When explicit
band/frequency data is unavailable, the app uses conservative channel-based
inference only when the primary channel identifies a unique band. Contradictory
band/frequency evidence and unsupported channel geometry remain unknown. HT40
needs its secondary-channel direction; 80+80 and ambiguous 320 MHz layouts do
not produce a numerical overlap claim.

Survey Quality also flags points where fallback scanner data or missing
channel-width/frequency details may weaken channel-sensitive conclusions such
as Interference, 5 GHz width overlap, or future 6 GHz validation.
When available, connected-BSSID evidence is preserved with survey data for
roaming and sticky-client diagnostics.

## AP Modeling

AP groups represent physical access points rather than isolated BSSIDs. This
prevents guest/main SSIDs from the same AP being treated as mutual interference
when the AP is modeled correctly.

Automatic MAC-based groups are proposals. Verify their BSSIDs against the real
equipment, then use **Confirm physical AP group** in the group's alias menu.
Renaming an automatic group does not confirm physical identity. Unconfirmed
groups do not hide RF neighbors or authorize physical AP changes.

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
users can fix scan evidence before interpreting live maps or HTML reports.

Current checks cover scan confidence, missing relevant networks, sparse or
unstable data, limited scanner details, connected-client roaming evidence, AP
metadata, AP Memory review states, missing AP positions, dominant-AP position
anomalies, and AP channel changes. Local-area AP groups can be scoped per
measurement point, so intentionally zone-only SSIDs are not treated as
whole-building requirements.

The dashboard uses KPI cards, filtered point lists, and detail dialogs to keep
large surveys readable. Full behavior and review guidance are documented in the
in-app Help Center.

## Live Maps And HTML Reports

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
locked for live maps and report export.

HTML export uses the current live map renderer and options, includes the full
floor plan independently of viewport zoom/pan, and embeds the image and legend.
Numbered points open their evidence. A summary highlights weak measured signals,
interference risk or dominant-AP warnings; unknown RF geometry stays explicit.

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

HTML reports preserve the current analysis snapshot. Export is blocked while scanning,
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
- analysis recommendations and offline HTML reports;
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
exporting/              live-map and analysis HTML reports, legacy PDF helpers
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

- `v1.2.0`

Expected Windows ZIP name:

- `WiFiRFSurveyAnalyzer-v1.2.0-win64.zip`

Historical beta ZIPs may still use the older artifact stem:

- `WifiHeatmap-v<version>-win64.zip`

## Roadmap

Possible future product areas:

- Physical wall thickness/materials, subject to a room model preserving internal
  dimensions and shared-wall relationships.
- Broader recommendation rules validated against additional real surveys.
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
