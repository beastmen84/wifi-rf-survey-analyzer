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
- Current UI direction is PySide6. `main.py` is the new Qt entry point, while
  `wifi_heatmap.py` remains the legacy Tkinter/ttkbootstrap entry point during
  migration.
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

- `main.py`: new PySide6 V2 entry point.
- `wifi_heatmap.py`: legacy Tkinter start screen and application launch during
  migration.

Core UI:

- `app.py`: main application. Still large, but several areas have been extracted.
- `main.py`: current Qt shell/prototype; it should progressively absorb real
  workflows instead of adding more complex GUI to `app.py`.
- `qt_floorplan.py`: Qt floorplan viewer with image/PDF loading, pan/zoom and
  point marker overlay.
- `qt_ap_groups.py`: Qt AP Group Manager migration in progress; currently
  handles group table/search, alias edits, role edits, BSSID split, conflict
  details and saving group metadata.
- `ap_group_dialog.py`: AP Group Manager.
- `survey_quality_dialog.py`: survey quality dashboard.
- `modal_dialogs.py`: shared modal dialog behavior.
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
- Hovering a point highlights the matching legend entry.
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
- AP Group Manager is intentionally not perfect visually in ttkbootstrap; later
  PySide6 could improve complex table behavior.

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
  details and save-to-session behavior. Metadata editing and AP positioning are
  still pending in Qt.

Recent commits:

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

1. Improve AP Group Manager workflows:
   complete the remaining Qt migration for metadata editing and AP positioning.
2. Continue PySide6 migration in `main.py`, with point creation/scanning as the
   next major workflow to move.
3. Add lightweight tests around AP groups, quality and interference before
   larger V2 refactors.
4. Decide whether mounting metadata should influence AP position warnings or
   remain documentation only.
5. Improve live map performance only if user sees real lag on large surveys.
6. Rework Help structure later, after the feature set stabilizes.

## Verification Patterns Used

Typical checks after code edits:

```powershell
.\.venv\Scripts\python.exe -m py_compile .\app.py .\heatmap_tools.py .\live_renderer.py .\i18n.py
git diff --check
git status --short
```

For logic changes, run a small `python -c` test with a synthetic DataFrame.
Recent tests checked that:

- a `test` AP stronger than others is ignored;
- the visible AP becomes dominant/serving;
- test APs are counted as ignored in interference;
- role columns are preserved in outputs.
