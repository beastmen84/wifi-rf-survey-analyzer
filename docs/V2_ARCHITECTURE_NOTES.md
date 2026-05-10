# WiFi Heatmap - V2 Architecture Notes

Last updated: 2026-05-10

This document is the forward-looking V2 roadmap. Completed items are kept only
as context; the actionable backlog is in the "Remaining Work" section.

## V2 Direction

V2 is not just a better heatmap renderer. The target is a Wi-Fi survey and RF
analysis platform that:

- stores reliable raw measurements;
- evaluates survey quality before trusting maps;
- understands AP groups, aliases, roles, radios and BSSIDs;
- detects inconsistent RF behavior;
- helps the user correct survey/modeling problems;
- produces maps that are explainable, not only visually appealing.

The heatmap should be the result of a validated RF dataset, not just
interpolated colors.

## Implemented V2 Foundation

These areas were part of the original V2 plan and are now substantially
implemented.

### Raw Scan Storage

Implemented:

- repeated scans per measurement point;
- raw scan samples retained in a linked sidecar file;
- sidecar extension changed to `.scan` to avoid confusing it with the main CSV;
- main CSV contains aggregated survey rows;
- raw sidecar path is stored in survey metadata;
- opening a raw sidecar directly is rejected.

Current format decision:

- main survey file: `<name>.csv`;
- linked raw file: `<name>_raw_data.scan`.

### Scan Aggregation And Confidence

Implemented:

- repeated lswifi/netsh scans;
- aggregation per BSSID/channel;
- median dBm;
- min/max dBm;
- samples seen/total;
- scan confidence;
- raw sample retention.

Confidence is also used by continuous/live rendering as interpolation weight.

### Relevant SSID Workflow

Implemented direction:

- save all visible networks;
- let the user mark relevant SSIDs;
- warn when relevant SSIDs are missing;
- base point quality mostly on relevant SSIDs rather than on total visible
  networks.

### Data Quality Engine

Implemented:

- per-point quality state;
- quality tooltip with useful breakdown;
- relevant SSID awareness;
- missing relevant network detection;
- low confidence detection;
- unstable signal detection;
- sparse data detection.

Current quality states include:

- `GOOD`
- `MISSING_RELEVANT`
- `LOW_CONFIDENCE`
- `UNSTABLE_SIGNAL`
- `SPARSE_DATA`

### Survey Quality Dashboard

Implemented:

- summary of good/review points;
- missing relevant network information;
- low confidence/unstable point information;
- AP positioning awareness;
- AP metadata consistency checks;
- AP configuration warning list.

### AP Group Manager

Implemented:

- automatic AP group suggestions;
- saved manual AP groups;
- manual BSSID merge/split;
- alias management;
- roles:
  - internal;
  - external;
  - interferer;
  - test/hidden;
- reset to automatic grouping;
- manual groups are stored in survey metadata;
- user edits are preserved for known BSSIDs;
- new BSSIDs can still be added automatically;
- conflict warning when one AP group is observed on multiple channels in the
  same band;
- warning details dialog;
- shortcut from warning details to Duplicate/Split, with conflicting BSSIDs
  shown first;
- user-facing `Auto` / `Manual` management state.

Important decision:

- simple automatic grouping can be wrong in real deployments;
- AP Group Manager is the authority;
- automatic grouping is a suggestion, not the final truth.

### AP Roles In Analysis

Implemented:

- `Test/hidden` AP groups are excluded from:
  - signal coverage;
  - AP channels;
  - dominant AP;
  - interference;
  - live AP group filters.
- AP roles are included in relevant tooltips/reports.

### AP Positioning

Implemented:

- AP physical position saved per AP group;
- right click on floor plan assigns AP position while positioning mode is
  active;
- AP position is saved in survey metadata;
- dirty state updates correctly;
- dominant AP tooltips show distance to AP;
- dominant AP PNG report includes AP position status and warnings;
- live and generated dominant maps show triangle warning markers.

Current warning logic:

- strong signal too far from AP;
- weak signal too close to AP;
- unexpected dominant AP;
- missing AP position;
- no scale calibration.

### AP Metadata

Implemented:

- metadata editor inside AP Group Manager;
- vendor;
- model;
- mounting type;
- expected bands;
- expected channels;
- notes;
- guided selections for expected bands/channels instead of free text.

Current use:

- metadata is descriptive;
- expected bands/channels are used by quality checks;
- mounting type is not yet used by RF logic.

### Improved Interference Analysis

Implemented:

- channel-width-aware overlap logic;
- 5 GHz overlap based on MHz ranges where width is available;
- same AP group ignored as interferer;
- guest/main SSIDs on the same physical AP do not count as mutual
  interference when grouped correctly;
- interference reports include serving/interferer AP, channels, widths,
  confidence, overlap and diagnosis;
- tooltips include width in MHz.

### Live Map View

Implemented:

- separate live map tab;
- signal/interference continuous rendering;
- AP channels and dominant AP marker views;
- live zoom and drag;
- structured mouseover tooltips;
- hover legend highlight;
- cached/fingerprinted rendering;
- worker rendering with Matplotlib Agg and Tk main-thread GUI updates.

### UI/Workflow Foundation

Implemented:

- fullscreen main app by default;
- start screen with scaled layout;
- toolbar-based workflow;
- new/open/save survey handling;
- dirty-state save button highlighting;
- save prompt before close/new/open;
- map generation requires saved survey;
- generated PNG/report names depend on survey filename, map type, band and
  timestamp;
- map/output files are saved beside the survey CSV;
- language selector IT/EN;
- theme selector reduced to a small set of sensible themes.

## Remaining Work

### 1. AP Group Manager UX For Large Surveys

Why it matters:

- real surveys can contain many BSSIDs;
- manual split/merge must stay fast and understandable;
- ttkbootstrap tree/table behavior is limited.

Suggested next steps:

- improve BSSID selection dialog for large lists;
- add filters by SSID, channel, band, role, current group and warning state;
- add quick actions:
  - select only warning BSSIDs;
  - invert selection;
  - split selected into new group;
  - move selected to existing group;
- add clearer conflict explanation by band/channel;
- consider a dedicated "unassigned/new BSSID" view.

### 2. AP Group Model Refinement

Current model is physical-AP oriented. Future RF logic may need to distinguish:

- physical AP;
- radio;
- BSSID;
- SSID/service;
- band/channel operation.

Reason:

- the same physical AP can legitimately operate different radios/channels;
- false warnings can happen if a physical AP group contains separate radios;
- interference and roaming logic may become more accurate if radios are modeled
  explicitly.

Conservative next step:

- keep the current AP group model;
- add optional per-BSSID/radio metadata later only if real tests show that the
  current model blocks correct analysis.

### 3. AP Metadata Usage In RF Checks

Currently metadata is partly descriptive and partly used for expected
band/channel checks.

Useful next checks:

- mounting type influencing AP position warnings;
- expected radio count;
- expected channel width;
- vendor/model capability hints;
- AP role consistency:
  - external AP should not be selected as dominant for internal coverage;
  - test/hidden AP should remain excluded from user-facing analysis.

Keep this rule:

- metadata should assist diagnosis, not silently change measurements.

### 4. Survey Quality Engine Expansion

Possible additions:

- point spacing quality;
- coverage completeness by area;
- scan backend reliability score;
- repeated scan variance per AP group;
- channel change detection over time;
- likely mesh/roaming ambiguity detection;
- "points to rescan" recommendation list.

### 5. Live View V2

Current live view is useful, but it can become the main working surface.

Potential upgrades:

- preserve live map options as defaults for PNG generation;
- faster switching between map types;
- per-map option panels;
- live overlay for quality warnings;
- live overlay for AP positions;
- live AP group filter improvements;
- optional hover pinning so a tooltip can stay open while inspecting details.

### 6. Generated Report Improvements

The generated maps are now useful, but reports can become more actionable.

Possible additions:

- combined summary report per survey;
- AP group summary table;
- quality warning export;
- interference ranking per AP group;
- dominant AP transition summary;
- PDF report generation later.

### 7. Testing And Validation

This project now has enough logic that manual testing alone is risky.

Suggested test areas:

- AP group serialization/deserialization;
- manual group merge/split preservation;
- role filtering;
- channel-width overlap;
- AP position warning logic;
- quality engine states;
- old invalid CSV rejection;
- raw `.scan` sidecar handling.

Priority:

- add lightweight unit tests before larger V2 refactors.

### 8. Help System Rework

Postponed intentionally.

Needed later:

- restructure help by workflow rather than feature list;
- add a dedicated live map help tab;
- add AP Group Manager help;
- explain relevant SSIDs, raw scans, confidence and quality states;
- keep text concise and visual where possible.

### 9. PySide6 Migration

Decision updated:

- PySide6 migration should happen early, while the tool is not yet distributed;
- the existing Tkinter/ttkbootstrap UI remains available during the migration;
- new complex GUI work should target Qt instead of making `app.py` larger.

Reason:

- AP Group Manager, live maps and quality dashboards need stronger table,
  layout and interaction primitives than Tkinter comfortably provides;
- postponing the migration would make every future GUI feature more expensive
  to port;
- the current user base is still controlled, so this is the right moment for a
  heavy UI change.

PySide6 is the target UI stack for:

- complex editable tables;
- dockable panels;
- multi-panel dashboards;
- larger datasets;
- richer validation workflows.

Current first step:

- `main.py` is the new PySide6 entry point;
- `wifi_heatmap.py` remains the legacy Tkinter entry point during migration;
- `main.py` already starts with project/session shell behavior and the first
  Qt survey viewer pieces: floorplan loading, saved map restore, point marker
  overlay, pan/zoom and fit-to-window.
- `qt_ap_groups.py` contains the first Qt AP Group Manager migration: group
  table/search, alias/role edits, metadata editing, BSSID split, conflict
  details, AP positioning from the Qt floorplan and save behavior are available.
- Qt point creation/scanning is also available in first-pass form: right-click
  on the Qt floorplan starts an Auto scan in a background Qt thread, relevant
  SSID prompts are Qt dialogs, all detected networks are saved, and the Qt
  points table includes quality/focus/delete controls.
- `qt_point_workflow.py` contains the Qt scan worker and relevant/missing
  network dialogs.
- Qt live map, generated map export, Survey Quality Dashboard, scale
  calibration, Help and the toolbar theme selector are now available in
  first-pass form.

Recommended migration sequence:

```text
1. Keep Tkinter stable as fallback
2. Build the Qt shell in main.py
3. Move survey state, loading/saving and floorplan viewing to Qt
4. Move AP Group Manager to Qt
5. Move live map tab to Qt
6. Move quality dashboard and map generation dialogs to Qt
7. Move remaining smaller workflow dialogs/actions to Qt
8. Retire Tkinter only after feature parity is acceptable
```

## Suggested Next Priorities

Near-term:

1. Continue Qt feature parity for any small utility actions still only present
   in the legacy UI.
2. Add more targeted tests for point scanning, survey save/load and sidecar
   handling.
3. Keep using the legacy Tkinter entry point as fallback until Qt parity is
   acceptable.

Medium-term:

4. Expand survey quality recommendations.
5. Improve generated reporting.
6. Use AP metadata more deeply in diagnostics.

Long-term:

9. Retire the Tkinter UI when Qt reaches practical feature parity.
10. Rework Help after feature workflows stabilize.
11. Add advanced RF/AI-assisted suggestions.
12. Add richer deployment/reporting outputs.

## Final Vision

The long-term goal remains a tool capable of:

- collecting real RF data;
- preserving evidence behind every aggregate value;
- understanding AP relationships;
- evaluating survey reliability;
- detecting anomalies;
- explaining generated maps;
- helping users improve Wi-Fi deployments.

The tool should make the survey more trustworthy, not just make prettier
heatmaps.
