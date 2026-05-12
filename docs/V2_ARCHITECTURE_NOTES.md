# WiFi Heatmap - V2 Architecture Notes

Last updated: 2026-05-12

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
- the real-survey live PDF validation pass is complete for Coverage, AP
  Channels, Dominant AP and Interference; the current findings are accepted as
  real diagnostics for now rather than layout blockers;
- the EN/IT text polish pass is complete for the current UI surface: buttons,
  titles and compact labels use capitalized wording where appropriate, and
  localized compact controls are checked for fit;
- clean AP channel changes during a survey are now modeled separately from AP
  group conflicts: they do not create AP Group warnings, but channel-sensitive
  maps use the latest channel for that AP group by default and expose a
  channel-change note where the UI has a tooltip;
- AP metadata can explicitly override the analysis channel per AP group/band,
  so Interference and AP Channels can use the channel the user knows is the
  right operational model after a clean or ambiguous survey-time channel change;
- the 2026-05-12 operational test survey is a useful baseline: all 25 points
  passed quality, all raw samples came from `lswifi`, relevant AP positions were
  complete, and the remaining findings are AP setup/anomaly diagnostics rather
  than point-rescan problems.

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
- new scans can retain optional scanner detail fields:
  - `frequency_mhz`;
  - `security`;
  - `auth`;
  - `encryption`;
  - `pmf`;
  - `country_code`;
  - `spatial_streams`;
  - `stations`;
  - `channel_utilization`;
  - `wifi_modes`;
  - `amendments`;
  - `vendor`;
  - `model`;
  - `ap_name`;
- opening a raw sidecar directly is rejected.

Current format decision:

- main survey file: `<name>.csv`;
- linked raw file: `<name>_raw_data.scan`.

### Scan Aggregation And Confidence

Implemented:

- repeated lswifi/netsh scans;
- default `auto` scanning prefers `lswifi` and falls back to `netsh`;
- connected-SSID lookup follows the same rule: `lswifi` first, `netsh`
  fallback;
- aggregation per BSSID/channel;
- median dBm;
- min/max dBm;
- samples seen/total;
- scan confidence;
- raw sample retention;
- most-common optional scanner details retained on aggregated rows where
  available.

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
- conflict checks use explicit/frequency-derived scan band data, so low-number
  6 GHz channels are not treated as 2.4 GHz when the row carries band/frequency;
- warning details dialog;
- shortcut from warning details to AP group correction, with conflicting BSSIDs
  shown first;
- AP group table filters by warning state, role, band and manual/auto state;
- BSSID management dialog filters by current/other/unassigned/selected/warning
  BSSIDs, band, channel and search text;
- user-facing `Auto` / `Manual` management state;
- per-band analysis-channel override in AP metadata for channel-sensitive maps.
  The override picker is constrained to channels actually observed for that AP
  group/band and is disabled for bands not observed on the group.

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
- left click on floor plan assigns AP position while positioning mode is
  active;
- AP position is saved in survey metadata;
- dirty state updates correctly;
- dominant AP tooltips show distance to AP;
- dominant AP PDF report includes AP position status and warnings;
- live and exported dominant maps show triangle warning markers.

Current warning logic:

- strong signal too far from AP;
- weak signal too close to AP;
- unexpected dominant AP;
- missing AP position;
- no scale calibration.

Latest real-survey result:

- with AP positions added, the quality dashboard reported complete relevant AP
  positioning (`8/8`);
- detected AP metadata warnings were unexpected channel `40` on `CORR. UFF. 12`
  and unexpected channel `153` on `SINCE`;
- detected AP-position warnings were `UNEXPECTED_DOMINANT`, mostly where
  `CORR. UFF. 4` appeared dominant far from its physical marker while nearer
  APs existed. These were reviewed on Dominant AP live/PDF output and currently
  look like valid diagnostics rather than threshold bugs.

### AP Metadata

Implemented:

- metadata editor inside AP Group Manager;
- vendor;
- model;
- mounting type;
- expected bands;
- expected channels;
- per-band analysis-channel override for Interference/AP Channels;
- notes;
- guided selections for expected bands/channels instead of free text.
- analysis-channel override selection is constrained to observed AP-group
  channels so the user cannot model against a channel absent from the survey.
- 6 GHz expected-band metadata includes a 6 GHz channel picker; ambiguous
  low-number channels are assigned according to the selected expected band when
  possible.

Current use:

- metadata is descriptive;
- vendor/model can be prefilled for automatic AP group suggestions only when
  scan rows for that group report one unambiguous value;
- expected bands/channels are used by quality checks;
- analysis-channel overrides are explicit modeling choices used by
  channel-sensitive maps, not validation expectations;
- mounting type is not yet used by RF logic;
- 6 GHz is supported by metadata checks when scan rows include an explicit
  `band` value or frequency-derived band.

Scanner note:

- `lswifi` exposes enough data to preserve band/frequency, security, PMF, mode
  and QBSS utilization details;
- true vendor/model data is saved only when the scanner object or decoded WPS
  information elements expose it. AP name is saved separately and is not treated
  as vendor.

### Improved Interference Analysis

Implemented:

- channel-width-aware overlap logic;
- 5 GHz overlap based on MHz ranges where width is available;
- 6 GHz overlap based on MHz ranges where width is available;
- same AP group ignored as interferer;
- guest/main SSIDs on the same physical AP do not count as mutual
  interference when grouped correctly;
- clean channel-change sequences for the same AP group/BSSID set are detected
  over time; Interference uses the final observed channel/width for that AP
  group by default instead of mixing old and current channel states across the
  map;
- manual AP metadata overrides can force the analysis channel for clean or
  ambiguous channel-change sequences when the user knows the correct operating
  channel;
- ambiguous channel sequences are preserved as measured unless an explicit
  analysis-channel override is configured;
- interference reports include serving/interferer AP, channels, widths,
  confidence, overlap and diagnosis;
- tooltips include width in MHz and automatic/manual channel-change notes where
  relevant.

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
- AP Channels uses the final observed channel/width for clean AP channel
  changes by default, matching Interference behavior while keeping ambiguous
  sequences as measured unless a manual analysis-channel override is configured;
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
  matching the report-card order;
- AP Channels all-band legend colors are band-aware, avoiding collisions between
  equal/ambiguous channel numbers across 2.4/5/6 GHz;
- AP Channels PDF uses the same automatic/manual channel-change handling as the
  live AP Channels map;
- Dominant AP problem reports include AP position status/warnings, distance to
  the dominant AP and nearest physical AP context only for AP-position warning
  rows;
- Dominant AP map/report attribution follows the Interference pattern with
  numbered square callouts on the map and matching numbered cards;
- Dominant AP report cards are visually aligned with Interference cards:
  compact number badge, coordinates in parentheses and fixed-height card grid.

### Qt Migration Status

Implemented:

- PySide6 is the active UI stack;
- `main.py` is the lightweight Qt launcher/start screen;
- Qt modules live under the `qt_ui/` package; `qt_ui/qt_app.py` contains the
  main workspace shell while workflow-specific mixins cover session, floorplan,
  AP, live map, settings and point-table behavior;
- non-UI modules are grouped by domain: `app_core/`, `ap/`, `wifi/`,
  `maps/`, `exporting/`, `survey/` and `translations/`;
- legacy Tkinter entry points and Tk dialogs have been retired from the active
  codebase;
- the launcher imports the heavier workspace module in a background Qt worker
  before enabling new/open actions;
- Qt workspace covers project/session behavior, floor-plan loading, saved map
  restore, point marker overlay, pan/zoom and fit-to-window;
- Qt AP Group Manager covers group table/search/filtering, alias/role edits,
  metadata editing, BSSID management, conflict details, AP positioning and save
  behavior;
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
- PDF export requires saved survey;
- top app-bar `Generate heatmap` and the legacy PNG/CSV export workflow were removed;
- live-map export now lives beside live-map update controls;
- exported PDF names depend on survey filename, map type, band and timestamp;
- map/output files are saved beside the survey CSV;
- language selector IT/EN;
- theme selector reduced to a small set of sensible themes;
- Qt scrollbar styling is centralized in shared theme code and applied across
  the main workspace, startup window, centered file dialogs and AP Group
  dialogs;
- Measurement Points table selection uses the full theme accent with white text,
  matching the AP Group table contrast.
- EN/IT user-facing titles, buttons and compact labels have been normalized for
  the current Qt surface;
- compact localized buttons recalculate their minimum width from the active
  translation, and point-capture warning dialogs grow their minimum width when a
  translated button row needs more space;
- i18n/UI tests guard translation key parity, placeholder parity, capitalized
  title/button starts and compact localized button fit.

## Remaining Work

### 1. AP Group Manager UX Monitoring

Current status:

- the planned AP Group Manager usability pass is complete for the current V2
  scope;
- AP group table filters by warning state, role, band, manual/auto state and
  search text;
- BSSID selection dialog filters by search text, current/other/unassigned/
  selected/warning state, band and channel;
- BSSID selection dialog supports visible-row select, clear and invert actions;
- selected BSSID rows can be split into a new manual AP group;
- selected BSSID rows can be moved to an existing AP group;
- conflict warning details explain possible causes, recommended checks and
  observed band/channel/BSSID evidence;
- AP group conflict detection ignores pure channel changes where the same BSSID
  set is observed on multiple channels over time; unexpected configured channels
  remain covered by AP metadata warnings;
- AP metadata can force the channel used by channel-sensitive maps per AP
  group/band when a survey-time channel change does not match the intended
  operational model.

Remaining stance:

- keep this area in monitoring mode;
- add more AP Group UX only if a larger real survey shows a concrete bottleneck.

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
- vendor/model capability hints based on collected scan metadata and/or user
  metadata;
- AP role consistency:
  - external AP should not be selected as dominant for internal coverage;
  - test/hidden AP should remain excluded from user-facing analysis.

Keep this rule:

- metadata should assist diagnosis, not silently change measurements; the
  analysis-channel override is allowed because it is an explicit user-selected
  modeling override.

### 4. Survey Quality Engine Expansion

Possible additions:

- point spacing quality;
- coverage completeness by area;
- scan backend reliability score;
- repeated scan variance per AP group;
- "what to fix next" guidance for clean/ambiguous AP channel changes detected
  over time;
- likely mesh/roaming ambiguity detection;
- "points to rescan" recommendation list.

### 5. Live Map Validation And Final Polish

The live-map Qt implementation is now the main working surface. Remaining work
is mostly validation and targeted polish rather than migration.

Completed validation:

- Coverage, AP Channels, Dominant AP and Interference were exported from the
  latest real operational survey;
- report/legend/card alignment fixes from that pass are implemented;
- AP-position warning triangles and Dominant AP report wording are readable
  enough for the current real warnings;
- current real warnings are considered valid until new data proves otherwise.

Remaining checks:

- verify legends/scales on additional floor-plan sizes and aspect ratios;
- verify AP group filters and positioned AP markers on larger surveys;
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

Current coverage includes:

- AP group serialization/deserialization;
- manual group merge/split preservation;
- role filtering;
- channel-width overlap;
- clean/ambiguous AP channel-change detection plus automatic latest-channel and
  manual analysis-channel override behavior for Interference and AP Channels;
- 6 GHz scan parsing, band-aware filters, legends and exports with synthetic
  hardware-like rows;
- scanner detail fields and conservative AP metadata prefill;
- AP position warning logic;
- quality engine states;
- old invalid CSV rejection;
- raw `.scan` sidecar handling;
- survey save/load round-trip for V2 metadata, raw sidecar, relevant SSIDs, AP
  groups, AP positions and AP metadata;
- Qt point-save workflow from scanned networks into aggregate rows/raw rows;
- live PDF problem reports and numbered Dominant/Interference attribution.

Remaining validation:

- keep adding targeted tests with each behavioral change;
- validate real 6E/7 scans when suitable hardware is available;
- use larger real surveys to expose performance and UX limits.

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

1. Keep AP Group and live-PDF areas in monitoring mode unless new real data
   exposes a concrete issue.
2. Rework Help structure/content now that the main Qt/V2 workflows are stable
   enough to document.
3. Expand survey quality recommendations into clearer "what to fix next"
   guidance.
4. Improve combined/generated reporting beyond individual live-map exports.

Medium-term:

5. Use AP metadata more deeply in diagnostics where the rule is clear.
6. Validate 6 GHz behavior with real 6E/7 hardware data.
7. Tune performance only after larger real surveys show measurable lag.

Long-term:

8. Refine the AP physical/radio/BSSID model only if real deployments require it.
9. Add advanced RF/AI-assisted suggestions.
10. Add richer deployment/reporting outputs.

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
