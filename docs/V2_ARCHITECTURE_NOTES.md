# WiFi Heatmap - V2 Architecture Notes

Last updated: 2026-05-11

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

Current status:

- the Tk to Qt migration is substantially complete;
- Help content and structure are intentionally postponed until the V2 workflow
  is stable;
- the current focus is validating the last live-map exports and closing
  remaining V2 analysis/reporting gaps.

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
- mounting type is not yet used by RF logic;
- 6 GHz is supported by metadata checks when scan rows include an explicit
  `band` value or frequency-derived band.

### Improved Interference Analysis

Implemented:

- channel-width-aware overlap logic;
- 5 GHz overlap based on MHz ranges where width is available;
- 6 GHz overlap based on MHz ranges where width is available;
- same AP group ignored as interferer;
- guest/main SSIDs on the same physical AP do not count as mutual
  interference when grouped correctly;
- interference reports include serving/interferer AP, channels, widths,
  confidence, overlap and diagnosis;
- tooltips include width in MHz.

### Live Map View

Implemented:

- dedicated Qt live map tab;
- Coverage, Interference, AP Channels and Dominant AP views;
- worker rendering with Matplotlib Agg and Qt main-thread GUI updates;
- cached/fingerprinted rendering to avoid unnecessary redraws;
- app-bar zoom/focus controls work on the active live map;
- duplicate bottom-right live zoom controls removed;
- scale calibration controls disabled while the Live tab is active;
- map markers use scene-sized survey-style sizing;
- normal cursor by default and closed-hand cursor only while panning;
- positioned physical AP markers shown on live maps, excluding test/hidden APs;
- AP group filter highlights the matching AP marker when a position exists;
- continuous maps use a bottom-right color scale overlay bound to the viewport;
- map-specific options live in a compact left overlay with a vertical tab;
- each map exposes only values that make sense for that map;
- 6 GHz is available in live Coverage, Interference, AP Channels and Dominant
  AP band filters;
- live-map options are remembered per survey/map type;
- AP Channels and Dominant AP use legend-controlled point labels
  (`Auto` / `All` / `None`) rather than labels drawn directly on the map;
- discrete-map legends support click-to-highlight, double-click-to-focus and
  empty-map-click deselection;
- tooltips use the newer compact Qt layout;
- Coverage tooltips preserve the selected SSID;
- Interference tooltips omit empty main-interferer rows.

### Live PDF Export

Implemented:

- live export starts from the Live Map toolbar through `Export PDF`;
- export asks the user where to save the PDF;
- export uses the current live-map type and options;
- map rendering uses the full floor-plan extent, independent of viewport
  zoom/pan;
- page 1 is arranged as map first, then summary/scale/legend below the map;
- continuous Coverage and Interference exports honor color scale, smoothing and
  max-distance settings;
- live PDF export supports 6 GHz map filters, legends and Interference
  summaries;
- exported map pages are flattened to avoid accidental page-image selection in
  PDF viewers;
- map markers use survey-like sizing;
- positioned AP markers use the Wi-Fi marker on the map;
- completion popup reports only the created file path;
- Coverage export intentionally has no problem-report page;
- Interference and Dominant AP exports can add paged problem-report cards;
- AP Channels export is map-only until a diagnostic rule is defined;
- Interference report cards show risk, coordinates, serving AP/channel and main
  interferer/channel;
- Interference map page labels problem points with numbered square callouts
  matching the report-card order.

### Qt Migration Status

Implemented:

- PySide6 is the active UI stack;
- `main.py` is the lightweight Qt launcher/start screen;
- `qt_app.py` contains the main Qt workspace and workflow logic;
- legacy Tkinter entry points and Tk dialogs have been retired from the active
  codebase;
- the launcher imports the heavier workspace module in a background Qt worker
  before enabling new/open actions;
- Qt workspace covers project/session behavior, floor-plan loading, saved map
  restore, point marker overlay, pan/zoom and fit-to-window;
- Qt AP Group Manager covers group table/search, alias/role edits, metadata
  editing, BSSID split, conflict details, AP positioning and save behavior;
- Qt point creation/scanning runs scans in a background Qt thread and saves all
  detected networks;
- relevant SSID prompts, missing network dialogs, points table controls, Survey
  Quality Dashboard, scale calibration, generated map dialogs, live maps,
  settings/theme/language handling and start-screen behavior are available in
  Qt;
- Help is available in first-pass form, but the content/structure rework remains
  postponed.

### UI/Workflow Foundation

Implemented:

- fullscreen main app by default;
- start screen with scaled layout;
- toolbar-based workflow;
- balanced top app-bar sections for Project, Analysis and View actions;
- new/open/save survey handling;
- dirty-state save button highlighting;
- save prompt before close/new/open;
- map generation requires saved survey;
- top app-bar `Generate heatmap` was removed from the live-map workflow;
- live-map export now lives beside live-map update controls;
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
- dense AP tables need stronger filtering and batch-edit workflows.

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
- validate 6 GHz scan capture on real 6E/7 hardware and scanner backends:
  - new lswifi scans can preserve explicit/frequency-derived band data;
  - netsh and legacy survey rows without band/frequency can still only infer
    2.4/5 GHz from channel numbers;
  - low-number 6 GHz channels are ambiguous unless the row carries `band` or
    frequency information;
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

### 5. Live Map Validation And Final Polish

The live-map Qt implementation is now the main working surface. Remaining work
is mostly validation and targeted polish rather than migration.

Suggested next steps:

- export and review Coverage, AP Channels and Dominant AP from real surveys;
- align the remaining live PDF outputs with the current Interference export
  quality;
- verify legends/scales on different floor-plan sizes and aspect ratios;
- verify AP group filters and positioned AP markers across all live map types;
- tune performance only if large real surveys expose measurable lag;
- consider optional hover pinning later if tooltip inspection still feels
  difficult.

### 6. Generated Report Improvements

Live-map PDF export now exists, but reporting can become more complete.

Possible additions:

- combined summary report per survey;
- AP group summary table;
- quality warning export;
- interference ranking per AP group;
- dominant AP transition summary;
- AP Channels diagnostics if a clear rule is defined;
- consistent PDF output for generated/non-live map workflows where useful.

### 7. Testing And Validation

This project now has enough logic that manual testing alone is risky.

Suggested test areas:

- AP group serialization/deserialization;
- manual group merge/split preservation;
- role filtering;
- channel-width overlap;
- 6 GHz scans, filters, legends and exports using real hardware data;
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

## Suggested Next Priorities

Near-term:

1. Validate/export the remaining live map PDFs and adjust only concrete visual
   or data-logic issues found in those outputs.
2. Add more targeted tests for point scanning, survey save/load and sidecar
   handling.
3. Revisit AP Group Manager UX for large surveys after live export validation
   is complete.

Medium-term:

4. Expand survey quality recommendations.
5. Improve combined/generated reporting beyond individual live-map exports.
6. Use AP metadata more deeply in diagnostics.

Long-term:

7. Rework Help after feature workflows stabilize.
8. Add advanced RF/AI-assisted suggestions.
9. Add richer deployment/reporting outputs.

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
