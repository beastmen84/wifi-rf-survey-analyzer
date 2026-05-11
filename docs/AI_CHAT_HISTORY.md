# AI Chat History And Project Context

Last updated: 2026-05-11

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

## Current State Snapshot

Read this section first in a new chat.

- Active UI is PySide6 only. `main.py` is the launcher/start screen and
  `qt_app.py` is the main workspace.
- Legacy Tkinter/ttkbootstrap files were removed from the active path. Any old
  Tk notes in the chronological work log are historical only.
- Current CSV format is schema V2 only; do not spend effort on pre-V2 CSV
  migration unless the user explicitly changes direction.
- The app stores aggregated survey rows in the main CSV and raw scan samples in
  a linked `<survey_stem>_raw_data.scan` sidecar.
- The current code test baseline after the latest live-map pass is 27 passing
  tests with `.\.venv\Scripts\python.exe -m pytest -q`.
- Latest code commit before this documentation refresh:
  `53e50c1 Keep AP marker icons sharp`.
- Current AP positioning and scale calibration pick points with left click while
  their modal map-pick mode is active; normal map dragging is disabled during
  the pick and the click must not create a measurement point.
- Normal survey point creation is still right click on the survey map.
- Do not regenerate the executable unless the user explicitly asks.

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
- `ui_scaling.py`: shared UI scaling helpers used by the Qt launcher,
  workspace and dialogs.
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
- `app_restart.py`: source/exe restart command helpers used by UI scale changes.

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
- Discrete Qt live maps use marker tooltips and legend/category panels; hover
  behavior has been refined iteratively, so inspect `qt_live_map.py` and
  `qt_floorplan.py` before changing it.
- Continuous Qt live coverage/interference maps use a right-side gradient color
  scale overlay inside the map view instead of a right-side legend panel.
- Qt live signal coverage and AP channel maps have an AP group filter. Test AP
  groups are excluded from the filter list.
- Qt live controls are now map-type-specific: coverage shows aggregation,
  interpolation, usable threshold and AP group; interference shows interference
  mode and interpolation; AP channels shows AP group; dominant AP hides the
  continuous-map controls.
- Qt live point markers are scene-sized 14 px markers like the survey view, so
  they scale with map zoom instead of staying a fixed screen size.
- Continuous live rendering uses a worker thread and Matplotlib Agg; GUI updates
  happen on the Qt main thread.
- Result caching/fingerprinting exists in `live_renderer.py`.
- Confidence is used as interpolation weight for continuous maps.

Visual/UX decisions:

- Right click on survey map creates a measurement point.
- Left click drag moves the map.
- Left click on empty survey map deselects selected point.
- Scale calibration and AP positioning use left click while their dedicated
  pick mode is active. Normal map dragging is disabled during those modes, and
  the click is consumed so it must not create a measurement point.
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
  - left click on floor plan to store position while AP placement mode is active;
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
- AP Group Manager is now Qt-based. Many dense-table and dialog refinements
  have already been done, but it remains an active UX area.

Grouping caveat:

- Earlier grouping by BSSID middle octets caused false grouping in real tests.
- The manual AP Group Manager is the long-term answer: automatic suggestions
  are allowed, but user edits must not be overwritten for known BSSIDs.

Earlier commits around AP groups:

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
  bands/channels and notes; AP positioning saves current groups, closes the
  manager, and lets the user place physical AP markers on the Qt floorplan. The
  current interaction is left-click placement while AP placement mode is active.
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
  and dominant AP live views were added in the following step.
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
- Added Qt scale calibration. The `Calibra scala` toolbar action starts a
  two-point calibration mode on the Qt floor plan, stores
  `px_per_meter` in survey metadata, updates live/export distance handling and
  avoids creating survey points while calibration is active. The current
  interaction is left-click selection while calibration mode is active.
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
- Improved the Qt survey point tooltip formatting: it now shows a clear title,
  position, best signal with relevant/all scope, row counts, timestamp and
  detected SSIDs as a short list for quicker reading.
- Added a shared Qt UI scaling layer. The launcher, main workspace and primary
  dialogs now scale window sizes, margins, controls and stylesheet dimensions
  from an automatic display scale so the app keeps a 1080p-like visual density
  on higher resolution screens such as 1440p/2K. The scale mode is stored in
  shared app settings as `ui_scale` for future user-facing control.
- Exposed the Qt UI scale setting in both the startup screen and main toolbar:
  `Auto`, `100%`, `110%`, `125%`, `150%`, `175%`. `Auto` displays the resolved
  percentage, because on Windows/Qt high-DPI systems it may resolve to 100% if
  the OS already reports logical pixels. Manual scale choices are saved and
  take full effect on the next app start.
- Moved Qt appearance controls behind a compact Settings menu. The startup
  screen and main toolbar now expose one `Settings` button; the menu contains
  Theme, UI scale and Language comboboxes. This keeps the toolbar focused on
  workflow commands and avoids layout crowding from always-visible settings
  controls.
- Reworked the Settings menu implementation from `QMenu` with embedded widgets
  to a small popup `QDialog`, because comboboxes inside `QMenu` can be fragile
  on Windows. The popup still opens below and to the left of the Settings
  button, but reliably shows Theme, UI scale and Language. The main toolbar
  Settings button now uses a taller dedicated style so it aligns visually with
  the rest of the toolbar.
- Changed automatic UI scale detection to use detected screen resolution
  buckets rather than trusting only Windows/Qt logical DPI. Current mapping:
  up to 1920x1200 = 100%, up to 2560x1600 / 3440x1600 = 125%, up to
  3840x2400 = 150%, larger = 175%. Manual scale choices remain available.
- Adjusted the meaning of UI scale percentages: the resolution bucket is now
  the neutral density for that screen. Example: on a 2560x1600 display,
  `Auto (125%)` and manual `125%` both keep the current density, while manual
  `100%` reduces the UI. The Settings popup combobox dropdowns now explicitly
  style popup text and selection colors so items remain visible on themed
  backgrounds, and the popup width was reduced.
- Added maintenance around the UI scale/settings work: `ui_scaling.py`,
  `app_logging.py`, and `app_settings.py` now have module docstrings; startup
  and workspace log UI scale diagnostics on creation and when the user changes
  UI scale, plus theme changes; tests now cover device-pixel-ratio resolution
  detection, resolution buckets, relative scale percentages, and diagnostics
  formatting.
- UI scale changes now require an explicit restart confirmation. The Settings
  popup shows `Save and restart` / `Cancel`; the selected scale is saved only
  after confirmation, a replacement process is launched through
  `app_restart.py`, and the current app exits. In the workspace, scale changes
  are blocked while a Wi-Fi scan or live map render is active, and unsaved
  survey changes still go through the normal save/discard/cancel prompt before
  restart.
- Added module docstrings to all top-level Python modules that were missing
  them. This is intentionally lightweight documentation so future refactors can
  identify each file's responsibility without adding noisy per-handler comments.
  Tests now also cover source-mode and frozen-exe restart command construction.
- Scale calibration is now treated as a locked survey setting once present.
  `Calibrate scale` is disabled when `px_per_meter` exists, and a compact
  `Delete scale` action appears in the `View` app-bar header. Deleting the
  scale asks for confirmation, removes `px_per_meter`, marks the survey dirty,
  refreshes the live map state, and enables calibration again.
- AP Group Manager layout was cleaned up after the Qt theme migration. The
  dialog now uses the active theme locally, has a smaller default/minimum size,
  hides the redundant vertical row header, stretches AP group/BSSID/SSID
  columns to fill available space, keeps utility columns compact, adds tooltips
  for clipped cell content, and moves actions into compact rows so buttons no
  longer overflow or get cut off.
- AP Group Manager rows now show multi-value AP group, BSSID, and Seen SSID
  cells on separate lines instead of truncating with `(+n)`. Row height grows
  with the tallest multi-line cell. Tooltips were narrowed to content columns
  where they are useful, removing unnecessary tooltips from compact columns
  such as role, channel, and management.
- AP Group Manager follow-up cleanup: the Alias column now receives the
  remaining table width while utility columns auto-fit within compact bounds;
  Duplicate/Split now uses real `QCheckBox` widgets instead of native list-item
  check indicators so checkbox visibility follows the app theme; the metadata
  dialog was tightened with compact field layout, smaller spacing, and bounded
  All/None buttons; AP placement now uses left click during placement mode and
  suppresses normal left-drag behavior until placement is complete.
- Console logging in source-run mode now splits streams: `INFO` and lower go to
  stdout, while `WARNING`, `ERROR`, and `CRITICAL` go to stderr. This avoids
  PyCharm coloring normal informational logs red while preserving warning/error
  visibility. File logging remains unchanged.
- AP Group metadata editing was adjusted for the Qt UI: the metadata dialog is
  taller and no longer hides the notes field behind an internal scroll area, and
  expected-band/channel spacing is more uniform across channel groups. AP
  placement now uses left-click like scale calibration, disables map dragging
  while waiting for placement, and uses a smaller 20 px AP icon that scales with
  map zoom.
- AP Group Manager table sizing now treats Alias as the primary flexible column:
  utility columns remain compact, while Alias stretches into the remaining table
  width instead of staying narrow when there is unused space.
- AP Group metadata channel editing was redesigned to save vertical space. The
  dialog now shows one row per expected band with a band checkbox, a channel
  picker button enabled only for selected bands with known channel lists, and a
  right-side summary of active channels. The picker opens a compact checkbox
  dialog for that band's channels and still writes the same `expected_bands` and
  `expected_channels` metadata fields.
- AP Group Duplicate/Split now uses a resizable table instead of a one-line
  checkbox label per BSSID. BSSID, seen SSIDs, channels, and any other assigned
  group are split into columns, while membership in the currently edited group is
  represented by the checkbox itself.
- The AP metadata channel picker now sizes itself from the number of channels in
  the selected band, so the 2.4 GHz picker is compact while the 5 GHz picker can
  remain larger for its longer channel list.
- Dialog placement is now centralized through a Qt event filter in
  `qt_windowing.py`. Every top-level `QDialog`, including custom dialogs and
  standard message/input boxes, is centered on first show relative to its parent
  window or the active screen. The filter is installed by both `main.py` and the
  direct `qt_app.py` entry point.
- Settings popup panels intentionally opt out of global dialog centering through
  `SKIP_CENTERING_PROPERTY`, because they should remain anchored below their
  toolbar/start-screen buttons. AP Group Split table checkbox cell containers
  are explicitly transparent so they inherit the table row color instead of
  showing a stale panel-colored square.
- The main toolbar Settings button height is now tied to the same app-bar
  control height used by the section cards, avoiding the slightly shorter
  standalone button appearance.
- AP Group Manager table tooltips were removed from both the main AP group table
  and Duplicate/Split table because the current column sizing keeps content
  readable without hover-only duplicates.
- AP Group Manager table selection now uses the theme accent color with white
  text instead of the softer row-selection tint, making the selected row clearly
  distinguishable from alternating row backgrounds.
- Survey Quality Dashboard now starts with an operational status banner:
  consistent survey, early/limited data, review recommended, or AP setup
  attention. The point table centers numeric columns, stretches SSID/Issue
  columns, sets consistent row height, and auto-selects the first visible row so
  `Go to point` is immediately actionable.
- Survey Quality follow-up: the dashboard table now disables cell focus styling
  like the measurement table, metric labels were expanded from abbreviations to
  descriptive names, and `Go to point` opens the measurement-points overlay
  before selecting the target point.
- The measurement-points overlay now uses `Rescan point` / `Rimisura punto`
  instead of the previous refresh-only wording. It reruns Wi-Fi scanning at the
  selected point position and replaces the old point only after the new scan is
  accepted, so retry/cancel leaves the existing measurement intact.
- Survey Quality now builds an effective AP group list from saved AP groups plus
  automatically detected groups from survey rows. This keeps `AP without
  position` accurate even before the user has opened/saved AP Group Manager in a
  new survey.
- Qt window behavior now includes app-wide modal dimming: when a program dialog
  opens, its parent window receives a soft overlay so attention stays on the
  active dialog. Nested dialogs dim their immediate parent as well. Toolbar/start
  settings popups intentionally opt out because they are anchored menus.
- File open/save actions now use centered Qt file dialogs instead of the native
  static Windows dialogs, because the native dialogs cannot be centered
  reliably through Qt.
- The centered Qt file dialogs have a dedicated stylesheet and view tuning so
  they do not inherit oversized global button widths/padding from the main app.
  Keep future file-dialog styling scoped to `QFileDialog#centeredFileDialog`.
  File-dialog tool buttons, combo boxes and line edits are forced to the same
  control height, and the file table stretches the Date Modified column to avoid
  an unstyled empty header area.
  File selection in the centered file dialog has explicit hover/selected colors
  and the file table uses full-row selection.
- Survey Quality AP position setup counters are scoped to relevant SSIDs when
  relevant networks are defined: `AP without position` and the `AP positions`
  ratio count only AP groups that have at least one row for a relevant SSID.
  With no relevant SSIDs defined, the dashboard keeps the previous all-AP
  fallback.
- Survey Quality top area was reorganized: the nine numeric metrics are shown
  as a compact 3x3 grid on the left, while the context details are shown as a
  label/value panel on the right instead of long pipe-separated sentences.
  The right panel intentionally avoids duplicating metric counts already present
  in the boxes and keeps only operational details/lists.
- The app remembers the last successfully opened or saved survey CSV path in
  app settings. `Open existing survey` from both the start screen and workspace
  opens in that directory; first save of a new survey uses the same directory as
  the initial suggestion.
- Survey summary now has `Manage` / `Gestisci` next to `Clear` for relevant
  networks. It opens a checkbox dialog over all SSIDs already seen or known in
  the survey, preselects current relevant SSIDs, persists the updated relevant
  set, and recalculates existing row `is_relevant` flags so earlier points are
  reinterpreted consistently.
- Fixed a `Manage relevant` save crash caused by the relevant-network dialog
  storing its initial selection in an attribute with the same name as the method
  used to return the selected SSIDs.
- A real office V2 survey showed the quality dashboard was too strict on mesh
  SSIDs: a weak, non-dominant BSSID seen once could mark the whole point as low
  confidence. Quality confidence is now evaluated on the dominant candidates
  for each relevant SSID, matching the logic already used for signal stability.
- Confirmed `Best dBm` in the quality dashboard already comes from relevant
  networks when present. The dashboard table now labels the SSID column as
  relevant SSIDs and only shows relevant SSIDs seen at that point.
- Quality dashboard labels were tightened after the relevant-SSID column saved
  horizontal space: `Low conf.` is now written out as `Low confidence` /
  `Bassa confidenza`, and table headers use dedicated title-case labels.
- Hardened Qt modal dimming. The delayed dim push now ignores dialogs that have
  already closed/hidden, tracks active dialogs by token instead of a fragile
  counter, and removes dim overlays through an idempotent cleanup path.
- Aligned the Qt app bar View buttons without changing text-button sizing:
  `+` and `-` now have their own fixed height and no extra vertical padding.
- AP position markers now keep the original high-resolution `images/wifi.png`
  pixmap and scale the graphics item instead of pre-rendering it to 20x20,
  preventing pixelated AP icons when the map is zoomed.
- Audited this handoff file for the next chat: refreshed the date, added a
  current-state snapshot, corrected stale Tk/right-click notes, updated recent
  commits and replaced old verification commands with the current compile/test
  baseline.
- Started the Qt live-map refinement pass using a real office V2 test survey:
  live point markers now use the same 14 px scene-sized behavior as survey
  markers, continuous coverage/interference legends now render as vertical
  color scales, and the live controls include an AP group filter for coverage
  and AP channel views. Added tests for live marker sizing and gradient legend
  painting.
- Continued the Qt live-map refinement: coverage/interference no longer reserve
  a sidebar for the color scale, because the colorbar is now a compact overlay
  hosted by `LiveMapView`; the second live control row is pruned per map type;
  and live continuous maps expose the same RBF/Linear interpolation choice used
  by generated map export.

Recent commits:

- `67d16b9` Refine Qt live map controls and legend.
- `53e50c1` Keep AP marker icons sharp.
- `c836d44` Constrain app bar icon height only.
- `fb423ef` Align app bar icon buttons.
- `b4d31f1` Harden modal dimming cleanup.
- `456f045` Polish quality dashboard labels.
- `a94f6c3` Show relevant SSIDs in quality table.
- `f4026e5` Refine survey quality confidence.
- `8f603e0` Fix relevant network manager save.
- `769f95c` Add relevant network manager.
- `ab5ba52` Remember last survey directory.
- `3ca4758` Avoid duplicate quality detail counts.
- `590ca3e` Reorganize quality dashboard summary.
- `0c8ec4a` Highlight centered file dialog selection.
- `35f1a75` Align centered file dialog controls.
- `c37c710` Scope quality AP position counts to relevant SSIDs.
- `d7bc7d2` Tune centered file dialog styling.
- `a415364` Center file dialogs and dim modal parents.
- `04e015b` Rescan selected survey points.
- `c76451d` Refine survey quality workflow.
- `5fa18a3` Clarify survey quality dashboard.

## Likely Next Steps

Good next steps, in likely order:

1. Continue Qt visual refinement only where it improves the real workflow:
   survey map focus, AP Group Manager readability, Quality Dashboard clarity,
   live map tooltips/legends and consistent dialog sizing.
2. Add targeted tests around point scanning, survey save/load with raw `.scan`
   sidecar, relevant SSID changes, AP group metadata and AP positioning.
3. Validate the current workflow with a fresh real survey before adding large
   features, because old CSV migration support was intentionally removed.
4. Decide whether mounting metadata should influence AP position warnings or
   remain documentation only.
5. Improve live map performance only if the user sees real lag on large surveys;
   do not trade away map quality prematurely.
6. Rework Help structure later, after the Qt layout and feature set stabilize.

## Verification Patterns Used

Typical checks after code edits:

```powershell
.\.venv\Scripts\python.exe -m compileall -q .
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
git status --short
```

For logic changes, prefer committed tests in `tests/test_core_logic.py` over
one-off scripts. A small `python -c` check is acceptable as a quick local probe,
but should not replace real tests when behavior is being fixed.

Current tests cover, among other things:

- a `test` AP stronger than others is ignored;
- the visible AP becomes dominant/serving;
- test APs are counted as ignored in interference;
- role columns are preserved in outputs;
- AP metadata/channel warnings;
- UI scale and restart command helpers;
- dialog/windowing behavior;
- AP marker icon scaling;
- live marker sizing and live gradient legend painting/overlay behavior.
