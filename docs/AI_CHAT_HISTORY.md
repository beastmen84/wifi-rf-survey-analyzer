# AI Chat History And Project Context

Last updated: 2026-05-10

This file is the continuity handoff for future AI chats. Read it before making
changes. It is not a full transcript: it is the technical history, decisions,
current architecture, and active rules that matter for continuing the work.

## Standing Instructions

- User language: Italian.
- Work directory: `C:\Users\beast\PycharmProjects\wifi_heatmap`.
- Shell in PyCharm is PowerShell 7.6.1.
- Do not regenerate the executable unless the user explicitly asks.
- The user asked to create a git commit after every completed set of changes.
- After every future task, update this file with what changed and any decision
  made, then commit both code and this file together.
- Prefer small, coherent steps. The app is growing and should remain easy to
  reason about.
- Current UI direction is PySide6. `main.py` is now the active Qt entry point;
  the legacy Tkinter/ttkbootstrap UI has been retired from the active codebase.
- Help text should eventually be reworked structurally, but the user chose to
  postpone that for now.
- Existing code is the source of truth. If this file and code disagree, inspect
  code and update this file.

## Project Summary

The project is a desktop Wi-Fi survey and heatmap tool. It started as a simple
script and has evolved toward a V2 "RF analysis platform":

- load a PDF/image floor plan;
- collect Wi-Fi scans at measurement points;
- store aggregated measurements plus raw scan samples;
- generate PNG maps and CSV reports;
- show live maps while adding points;
- manage AP groups, aliases, roles, and physical AP positions;
- evaluate scan/survey quality.

Entry points:

- `main.py`: lightweight PySide6 launcher/start screen. It imports the heavier
  workspace module asynchronously and enables new/open actions after loading.
- `qt_app.py`: main Qt workspace window and workflow logic.

Core UI:

- `main.py`: startup screen and async workspace loader.
- `qt_app.py`: current Qt application shell and workflow coordinator.
- `qt_floorplan.py`: Qt floorplan viewer with image/PDF loading, pan/zoom and
  point marker overlay.
- `qt_ap_groups.py`: Qt AP Group Manager for group table/search, alias edits,
  role edits, BSSID split, conflict details and saving group metadata.
- `qt_point_workflow.py`: Qt Wi-Fi scan worker and point workflow dialogs.
- `qt_map_generation.py`: Qt generated map dialog.
- `qt_quality_dashboard.py`: Qt survey quality dashboard.
- `qt_help_dialog.py`: Qt help dialog.
- `live_renderer.py`: continuous live signal/interference rendering in a worker.
- `map_rendering.py`: PNG map legend/reference helpers.

Core logic/data:

- `survey_store.py`: survey CSV, metadata, raw scan sidecar file.
- `wifi_scanner.py`: lswifi/netsh scanning and aggregation.
- `heatmap_tools.py`: map data preparation, interpolation helpers, interference logic.
- `ap_groups.py`: AP grouping, aliases, roles, serialization helpers.
- `ap_positioning.py`: physical AP position analysis.
- `quality_engine.py`: per-point quality engine.
- `map_config.py`: current map settings.
- `constants.py`: schema/version/config constants.
- `app_logging.py`: unified Qt logging setup and compatibility wrappers.

Docs:

- `docs/V2_ARCHITECTURE_NOTES.md`: V2 direction and feature areas.
- `docs/AI_CHAT_HISTORY.md`: this continuity file.

## Data Model And Storage Decisions

CSV survey format is schema V2 only.

- Legacy CSV compatibility/migration was intentionally removed.
- A valid survey CSV requires metadata:
  - `app=wifi_heatmap`
  - `schema_version=2`
- The main CSV contains aggregated rows with fields from `SURVEY_FIELDNAMES`.
- Raw scan samples are stored in a linked sidecar file named by metadata
  `raw_data_file`, defaulting to `<survey_stem>_raw_data.scan`.
- The `.scan` extension is intentional so users do not accidentally open the
  raw file as the main survey CSV.
- Opening a `_raw_data.scan` file directly is rejected.
- The floor plan path is saved in CSV metadata as `map_file`; reopening a survey
  reloads the floor plan automatically if the file still exists.
- The app keeps survey data in memory and tracks dirty state.
- Save button changes color when dirty.
- Closing/new/open flow must ask about unsaved changes.
- Heatmap/map generation requires the survey to be saved first. Output files are
  saved beside the survey CSV and named from the survey file plus map type/band
  and timestamp.

Current constants:

- `SURVEY_SCHEMA_VERSION = "2"`
- `HEATMAP_GRID_SIZE = 700`
- `HEATMAP_SMOOTHING_SIGMA = 3.0`
- `HEATMAP_MAX_DISTANCE_PX = 180`
- `WIFI_SCAN_ATTEMPTS = 5`
- `WIFI_SCAN_DELAY_SECONDS = 1.5`
- `MIN_GOOD_SCAN_NETWORKS = 4`
- `SUSPICIOUS_SCAN_RATIO = 0.5`

## Scanning And Quality Decisions

Backend behavior:

- Default scan backend is `auto`.
- `auto` tries `lswifi` first and falls back to `netsh`.
- `lswifi` is used through the Python package/API, not by spawning the packaged
  exe, to avoid opening a second executable instance.
- Both lswifi and netsh use repeated scans:
  - 5 attempts;
  - 1.5 seconds between attempts.
- Aggregation is per BSSID/channel:
  - median signal;
  - max/min signal;
  - samples seen/total;
  - scan confidence;
  - raw samples retained in `.scan`.

Relevant network workflow:

- The newer direction is: save all scanned networks, but let the user mark which
  SSIDs are relevant.
- If new SSIDs appear, the app can ask whether they are relevant.
- If relevant SSIDs are missing, warn with retry/keep/cancel style behavior.
- Point quality is based mostly on relevant SSIDs, not total visible networks.

Quality engine:

- `quality_engine.py` reports:
  - `GOOD`
  - `MISSING_RELEVANT`
  - `LOW_CONFIDENCE`
  - `UNSTABLE_SIGNAL`
  - `SPARSE_DATA`
- The points table has a quality column.
- Tooltip for quality explains breakdown per relevant SSID when useful.
- Survey Quality Dashboard summarizes points, good/review counts, missing
  relevant networks, low confidence, unstable points, AP positions.

## Map Types And Rendering

Generated PNG maps:

- Signal coverage heatmap.
- AP interference heatmap.
- AP channels map.
- Dominant AP / roaming map.

Live tab:

- Separate tab from survey data.
- Supports live signal/interference continuous rendering.
- Supports AP channels and dominant AP with real point markers and legend box.
- Supports zoom and drag.
- Tooltips show structured information.
- Legacy Tk live maps highlight the matching legend entry on hover. The Qt
  first pass has native tooltips and a static legend; hover-to-legend highlight
  is still optional/pending.
- Continuous live rendering uses a worker thread and Matplotlib Agg; GUI updates
  happen on the Tk main thread.
- Result caching/fingerprinting exists in `live_renderer.py`.
- Confidence is used as interpolation weight for continuous maps.

Visual/UX decisions:

- Right click on survey map creates a measurement point.
- Left click drag moves the map.
- Left click on empty survey map deselects selected point.
- AP positioning also uses right click when a position-pick operation is active;
  that click is consumed and must not create a measurement point.
- Point labels in generated PNG maps became reference numbers plus a reference
  table, because dense surveys make direct labels unreadable.
- On live maps labels are mostly mouseover/tooltips, not always-visible labels.

## Interference Logic

Important decision:

- Interference must use channel width when available, not only channel numbers.
- 5 GHz overlap must respect actual MHz ranges.
- lswifi can provide `channel_width_mhz`; netsh may not.
- Reports and tooltips should show channel width as MHz.

Interference map/report:

- Supports intra-SSID and all-networks mode.
- Same physical AP/group is ignored as an interferer.
- Guest SSIDs on same physical AP should not count as interference against the
  main SSID when they are in the same AP group.
- Report includes serving/interferer AP, channels, widths, dBm, confidence,
  overlap, diagnosis.
- AP group roles are now included:
  - serving role;
  - strongest interferer role;
  - count of ignored test APs.

Recent role behavior:

- AP role `Test/nascosto` is excluded from signal, AP channels, dominant AP, and
  interference analysis.
- It is excluded as serving AP and as interferer.
- It is also hidden from the live AP group filter list.

## AP Group Manager

V2 AP Group Manager is the current major direction.

Implemented:

- Auto-suggest/manual AP group model.
- AP aliases.
- Manual merge/split/duplicate via BSSID selection.
- Manual groups are stored in survey metadata.
- AP aliases are effectively part of AP group state.
- Group roles:
  - internal;
  - external;
  - interferer;
  - test/hidden.
- Physical AP position:
  - button "Posiziona su mappa";
  - right click on floor plan to store position;
  - saved in AP group metadata;
  - dirty state updated.
- AP metadata:
  - vendor;
  - model;
  - mounting type;
  - expected bands;
  - expected channels;
  - notes.
- Reset to automatic grouping.
- AP Group Manager is now Qt-based; visual refinement and dense-table workflow
  improvements remain future work.

Grouping caveat:

- Earlier grouping by BSSID middle octets caused false grouping in real tests.
- The manual AP Group Manager is the long-term answer: automatic suggestions
  are allowed, but user edits must not be overwritten for known BSSIDs.

Recent commits around AP groups:

- `23968a9` Extract AP grouping helpers.
- `73ae3d7` Prepare manual AP group model.
- `cb174e7` Add minimal AP group manager state.
- `dfd871f` Allow editing AP group BSSIDs.
- `fd74a24` Use manual AP groups in map calculations.
- `16af17a` Complete AP group manager basics.
- `ff704f7` Extract AP group manager dialog.
- `83dc857` Add AP group map positioning.
- `dad858e` Add AP group roles.
- `1d35a5d` Use AP roles in interference analysis.
- `7dfb5be` Hide test AP groups from map analysis.

## AP Positioning

Implemented:

- AP physical positions are saved per AP group.
- Dominant AP tooltips show AP distance and nearest physical AP.
- Dominant AP PNG report includes:
  - dominant AP distance px/m;
  - nearest physical AP group/label/distance;
  - AP position status;
  - AP position warnings.
- Live dominant AP and PNG dominant AP show a triangle marker when physical
  position analysis has warnings.

Current warning logic in `ap_positioning.py`:

- `STRONG_FAR`: strong signal far from AP.
- `WEAK_CLOSE`: weak signal close to AP.
- `UNEXPECTED_DOMINANT`: dominant AP is much farther than nearest positioned AP.
- If scale is not calibrated, status is `NO_SCALE`.
- If no AP position exists, status is `MISSING_POSITION`.

Distance calibration:

- User can calibrate scale by clicking two known-distance points on the map.
- The max distance default of 180 px is a rendering limit, not RF truth; in real
  environments with reinforced concrete it may need calibration/tuning.

## GUI State And Preferences

Current GUI:

- Start screen with scaled layout and icon-based help.
- Main window fullscreen by default.
- Toolbar has:
  - new/open survey;
  - save;
  - load plan;
  - AP Group/Alias manager;
  - survey quality dashboard;
  - scale calibration;
  - help;
  - generate heatmap/map;
  - theme selector;
  - language selector.
- Sidebar is intentionally lighter:
  - measurement/scan info;
  - saved/relevant network info;
  - last scan;
  - legend.
- Survey info moved to footer.
- Themes were reduced to two light and two dark themes; keep dark text/readable
  colors in mind when changing overlays or labels.
- Avoid excessive text in compact UI; prefer icons/tooltips where practical.

Language:

- App supports IT and EN via `i18n.py`.
- Any user-visible text added to UI should include both translations.
- Map titles and tooltip labels should respect language.

## Important Historical Decisions

- No more compatibility work for old pre-V2 CSV files. The user accepted this
  to avoid complexity while V2 is still evolving.
- Keep raw scan data linked to survey but not as another normal CSV.
- Use all networks for storage, but relevant SSIDs for survey quality decisions.
- Keep generated PNG labels non-invasive with reference tables.
- For live map, use mouseover/tooltips instead of permanent labels.
- AP aliases/group names should be used wherever practical instead of raw BSSID.
- For interference with all networks, guest/main SSIDs from the same physical AP
  must be grouped and ignored as same physical AP.
- Do not regenerate the exe after every change.

## Recent Work Log

2026-05-10:

- Added AP group roles and role serialization.
- Applied AP roles to interference analysis and reports.
- Made `Test/nascosto` AP groups hidden from all map analysis:
  - signal coverage;
  - AP channels;
  - dominant AP;
  - interference;
  - live AP group filter.
- Added role information to live channel/dominant tooltips and dominant report.
- Added this continuity file because the original chat became very long.
- Extended Survey Quality Dashboard with AP positioning awareness:
  - visible/non-test AP position counts;
  - excluded test AP count;
  - AP position warning count;
  - point issues for suspicious dominant AP physical position.
- Added lightweight AP metadata editing in AP Group Manager. Metadata is saved
  inside AP group survey metadata and currently acts as descriptive V2 input,
  without changing map calculations yet.
- Added AP metadata consistency checks in the Survey Quality Dashboard:
  expected bands/channels from AP group metadata are compared with observed
  channels, and mismatches are reported as AP configuration warnings.
- Changed AP metadata expected bands/channels from free-text entries to guided
  checkbox selections, while preserving the same normalized metadata storage.
- Added AP Group Manager conflict warnings: groups observed on multiple channels
  in the same band are highlighted and have a details dialog, helping catch
  suspicious automatic merges without blocking manual saves.
- Refined AP Group Manager state display: the warning column now only shows
  real warnings, while the former locked flag is shown as a user-facing
  Manual/Auto management state.
- Added a faster warning-resolution path in AP Group Manager: warning details
  can open Duplicate/Split directly, with the conflicting BSSIDs shown first.
- Reworked `docs/V2_ARCHITECTURE_NOTES.md` into an updated V2 roadmap:
  completed foundation items are separated from the remaining backlog, and new
  suggested priorities were added around AP Group Manager UX, tests, reporting,
  metadata-driven diagnostics and future UI migration.
- Decided to bring PySide6 forward instead of treating it as long-term work.
  Added `main.py` as the new Qt entry point with a first project shell:
  start page, language selector, survey open/new/save, floorplan path metadata,
  survey/live tabs and point summary table. Added PySide6 to requirements and
  kept `wifi_heatmap.py` as the legacy fallback during migration.
- Added the first real Qt survey viewer functionality in `main.py`:
  QGraphicsView floorplan loading for images/PDFs, saved floorplan restore from
  survey metadata, point marker overlay, pan/zoom controls, Ctrl+wheel zoom and
  fit-to-window. The reusable viewer lives in `qt_floorplan.py`.
- Added the first Qt AP Group Manager implementation in `qt_ap_groups.py` and
  connected it from `main.py`. It migrates group listing/search, alias editing,
  alias deletion, role editing, reset automatic grouping, BSSID split, warning
  details and save-to-session behavior.
- Completed the remaining first-pass Qt AP Group Manager workflows: metadata
  editing now uses guided Qt controls for vendor/model/mounting, expected
  bands/channels and notes; AP positioning now saves current groups, closes the
  manager, and lets the user right-click the Qt floorplan to store physical AP
  position markers.
- Added first-pass Qt point creation/scanning: right-clicking the Qt floorplan
  starts an Auto Wi-Fi scan in a background Qt thread, saves all detected
  networks through `SurveySession.add_points`, manages relevant SSID prompts in
  Qt, and keeps point quality/delete/focus controls in the Qt points table.
  `qt_point_workflow.py` now contains the scan worker and point-related dialogs.
- Added the first real Qt live map preview for continuous maps. The `Mappa live`
  tab now has SSID, band, map type, aggregation, usable-threshold, interference
  mode, auto-update and manual update controls. Signal coverage and AP
  interference render in a background Qt thread through `qt_live_map.py`, using
  the existing AP group role/filter logic and the shared live renderer. Channel
  and dominant AP live views still need to be migrated in a later step.
- Added Qt live AP Channels and Dominant AP map modes. Discrete modes use real
  measurement markers on the floor plan, AP aliases/groups, AP roles, channel
  width when available, AP-position warning triangles for dominant AP, and a Qt
  swatch legend panel.
- Added first-pass Qt generated map export. The `Genera heatmap` toolbar action
  now opens a Qt dialog, defaults to the current live-map choices, enforces save
  before export, and generates signal, interference, channel and dominant AP
  PNGs plus the existing CSV reports where relevant. Export rendering lives in
  `map_exporter.py`, while the Qt dialog lives in `qt_map_generation.py`.
- Added first-pass Qt Survey Quality Dashboard. The `Qualità` toolbar action now
  opens `qt_quality_dashboard.py`, showing summary metrics, relevant-network
  quality, AP position warnings, AP metadata warnings, an issues-only filter and
  point focus back to the survey tab.
- Added the first lightweight core test suite in `tests/test_core_logic.py`.
  It uses stdlib `unittest` and covers manual AP group overrides, interference
  ignoring same-physical-AP BSSIDs, missing relevant SSID quality state, and AP
  metadata channel warnings.
- Added Qt scale calibration. The `Calibra scala` toolbar action now starts a
  right-click two-point calibration mode on the Qt floor plan, stores
  `px_per_meter` in survey metadata, updates live/export distance handling and
  avoids creating survey points while calibration is active.
- Added first-pass Qt Help dialog. The toolbar now has a Help action that opens
  translated workflow, live map, generated map, scan and command tabs using the
  existing help text.
- Added first-pass Qt theme selector. The workspace toolbar now exposes four
  internal palettes, two light and two dark, with explicit styling for toolbar,
  tabs, tables, combo boxes, status panels and tooltips. Also removed an unused
  Qt placeholder method left over from earlier migration steps.
- Added Qt dirty-state feedback for Save. The generated toolbar save button now
  changes to a warning palette while the current survey has unsaved changes and
  exposes translated clean/dirty tooltips.
- Added a Qt `Azzera rilevanti` control in the Survey summary. It clears both
  relevant and known SSID metadata, marks the session dirty, refreshes point
  quality immediately and disables itself when there is nothing to clear.
- Added Qt survey-point selection from the floorplan: left-clicking a marker
  selects and scrolls to the matching table row, while left-clicking empty map
  space clears the point selection without blocking map drag behavior.
- Moved Qt theme palette data from `main.py` to `qt_theme.py`, keeping behavior
  unchanged while reducing the size of the main window module.
- Updated `WifiHeatmap.spec` to build the executable from the Qt entry point
  `main.py` instead of the legacy Tkinter launcher `wifi_heatmap.py`.
- Fixed an executable crash risk during Qt point creation: Auto scan now uses
  `netsh` inside frozen builds by default, while source runs can still use
  `lswifi`; removed Tkinter messagebox usage from `wifi_scanner.py`, excluded
  Tkinter/ttkbootstrap from the PyInstaller build, and added a small
  `wifi_heatmap_error.log` unhandled-exception logger next to the exe.
- Restored `lswifi` as the primary Auto backend inside the exe after user
  feedback. Stabilized the Qt scan worker cleanup so the QThread is not cleared
  until it has actually finished, and added step-by-step point creation logging
  to `wifi_heatmap_error.log` for scan, validation and point save phases.
- Fixed Qt live-map crash risk when switching from discrete maps to continuous
  coverage/interference maps. Live rendering now keeps the QThread reference
  until the thread has actually finished, logs render start/end/failure, and
  signal interpolation now falls back to nearest-neighbor when RBF/linear cannot
  build a surface from sparse or collinear points.
- Replaced the temporary `wifi_heatmap_error.log` writer with unified Qt
  logging in `app_logging.py`. Logs now go to rotating `wifi_heatmap_qt.log`
  with timestamp, severity and component names (`main`, `live_map`,
  `wifi_scanner`, `unhandled`), and Python warnings are captured into the same
  file.
- Retired the legacy Tkinter/ttkbootstrap UI from the active codebase. Removed
  `wifi_heatmap.py`, `app.py`, legacy Tk dialogs/helpers and the `ttkbootstrap`
  dependency. `main.py` is now the documented application entry point.
- Performed a follow-up cleanup after retiring Tk: removed the unused live-map
  placeholder translation key, renamed the start-screen badge key away from
  migration wording, and removed `ttkbootstrap` from PyInstaller excludes.
- Reworked Qt startup structure: moved the full workspace window from
  `main.py` to `qt_app.py`, made `main.py` a lightweight launcher with a
  redesigned start screen, disabled survey actions until the workspace module is
  loaded, and added an indeterminate startup progress bar backed by a Qt worker
  thread. Runtime `.log` files are ignored by git.
- Refined the Qt startup language control: removed the separate "Lingua"
  label, switched the startup dropdown to full language names, gave it a
  stronger filled style, and changed the start badge from a GUI-library label
  to a product/workflow label.
- Updated startup positioning: English is now the default language, the product
  name is `Wi-Fi RF Survey Analyzer`, startup copy now references RF analysis,
  relevant networks, roaming, AP groups and quality, and the green badge was
  removed entirely.
- Started the main Qt GUI redesign after the startup page pass. Replaced the
  native `QToolBar/QAction` command strip with a custom in-page app bar split
  into Project, View, Analysis and Settings sections, preserving the existing
  command behavior while making spacing, colors and hierarchy easier to refine.
  The Survey tab summary area was also changed from plain label rows into
  compact status cards for CSV, map, points, raw scans, AP groups and relevant
  networks.
- Added `pytest` to the project dependencies and installed it in the local
  virtual environment. Existing `unittest` tests are now also runnable through
  `python -m pytest`, which collected 4 tests successfully.
- Reworked the Qt Survey tab layout so the floorplan is the focal element:
  the points table is now hidden by default behind a floating overlay handle,
  opens over the bottom of the floorplan with a compact 6-row default height,
  and can be dragged upward/downward from its resize control. Theme colors were
  also remapped to the four palette concepts documented in
  `docs/UI_COLOR_PALETTES.md`: Sand Blue, Soft Olive, Slate Blue and Graphite
  Green.
- Refined the first Qt workspace redesign pass after visual review: made the
  Survey summary cards thinner, gave numeric cards narrower widths and shorter
  AP-group wording, reduced the beige strength of the Sand Blue palette, and
  improved relevant-network selection checkboxes. The connected SSID is now
  sorted to the top and preselected whenever Windows reports it and it appears
  in the scan.
- Fixed the visible rectangular patches under text in Qt cards and toolbar
  sections by making labels and checkboxes transparent over their parent
  surfaces. The Sand Blue palette was cooled further toward neutral
  gray/blue surfaces so beige is no longer dominant in the main theme.
- Reduced the Survey summary strip again by moving the `Clear relevant` action
  into the top-right of the relevant-networks card, tightening card padding,
  and narrowing numeric summary cards. This preserves the floorplan as the main
  visual area.
- Styled Qt combo-box arrows to use the active theme accent color, matching the
  `Generate heatmap` primary action color across themes.
- Adjusted the combo-box styling after visual testing: the right dropdown
  segment now takes the theme accent color and uses an explicit white SVG arrow
  (`images/combo_arrow_white.svg`) instead of relying on a fragile CSS triangle.
- Refined the floating points table: removed visible grid separation so row
  selection reads as a continuous row instead of isolated colored cells, made
  compact technical columns resize to content within fixed bounds, kept the
  `Networks` column as the stretch column, and added full-cell tooltips for
  truncated content.
- Updated `docs/UI_COLOR_PALETTES.md` to match the actual Qt palettes currently
  implemented in `qt_theme.py`, including the cooled Sand Blue values and the
  active theme keys/names.
- Refined the floating points table UX: only the `Networks` column now has a
  tooltip, all other columns are center-aligned, the collapsed measurement
  points handle no longer draws a surrounding panel frame, and floorplan drag
  resets the cursor to the normal arrow after mouse release.
- Restored the collapsed measurement-points button shape after removing the
  surrounding overlay frame by increasing the collapsed overlay size and
  enforcing a pill-shaped minimum button size.
- Added shared application settings in `app_settings.py`. The selected Qt theme
  is now persisted in the user's app settings folder, defaults to `light`
  (Sand Blue) when no saved config exists, is restored by both the startup
  launcher and the main workspace, and is saved whenever the user changes it.
  The startup page now styles itself from the active Qt palette instead of
  hard-coded colors.
- Refined survey point markers in the Qt floorplan: markers are larger, use
  muted green/yellow/orange/red signal colors, still scale naturally with map
  zoom, and can now be highlighted again when selected from the measurements
  table. Point summary `best_signal_dbm` now prefers rows marked relevant when
  available, falling back to all networks only when a point has no relevant
  rows.
- Removed the extra current-cell focus rectangle from the floating measurements
  table so only the full selected row is visually highlighted.
- Added automatic floorplan fit after every plan load, covering both explicit
  `Load plan` usage and loading the map associated with an existing survey.
- Changed Qt scale calibration interaction to use left-click for the two
  calibration points. While calibration is active, normal left-drag map panning
  is temporarily disabled and the cursor stays as a crosshair until calibration
  completes or is cancelled.

Recent commits:

- `d3cf068` Add Qt discrete live maps.
- `58d4a3a` Add Qt live map preview.
- `ce08bea` Add AI chat continuity notes.
- `7dfb5be` Hide test AP groups from map analysis.
- `1d35a5d` Use AP roles in interference analysis.
- `dad858e` Add AP group roles.
- `235c699` Add survey quality dashboard.
- `82a62b5` Use scan confidence in continuous rendering.
- `261ef02` Update help for AP positioning.
- `f1cfc07` Show AP position warnings in dominant PNG.
- `7b45326` Add AP position fields to dominant report.
- `0995279` Use triangle markers for AP position warnings.
- `826b92c` Highlight AP position warnings in live map.
- `162958a` Add AP position analysis to dominant tooltips.
- `cea47b6` Reposition AP placement action.

## Likely Next Steps

Good next steps, in likely order:

1. Add more targeted tests as new V2 modules are split out, especially around
   point scanning and survey save/load.
2. Decide whether mounting metadata should influence AP position warnings or
   remain documentation only.
3. Improve live map performance only if user sees real lag on large surveys.
4. Rework Help structure later, after the feature set stabilizes.
5. Continue visual redesign on the Qt-only UI.

## Verification Patterns Used

Typical checks after code edits:

```powershell
.\.venv\Scripts\python.exe -m py_compile .\main.py .\heatmap_tools.py .\live_renderer.py .\i18n.py
git diff --check
git status --short
```

For logic changes, run a small `python -c` test with a synthetic DataFrame.
Recent tests checked that:

- a `test` AP stronger than others is ignored;
- the visible AP becomes dominant/serving;
- test APs are counted as ignored in interference;
- role columns are preserved in outputs.
