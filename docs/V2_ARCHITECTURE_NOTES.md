# WiFi Heatmap - V2 Architecture Notes

Last updated: 2026-05-17

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

- public release versioning is separate from the internal V2 generation:
  `v0.9.6-beta.1` is closed as the current source-tagged beta, while `v1.0.0`
  should wait for the remaining real-survey validation fixes;
- future beta release candidates should use the current minor beta line for
  validation/polish or a new minor beta for feature-level additions; do not
  regenerate exe/ZIP for every commit, only when cutting an intentional release
  candidate;
- `README.md` is public-facing repo documentation and should not expose internal
  release cadence details; keep internal planning here and in the local ignored
  `.private/AI_CHAT_HISTORY.md` handoff, with public release notes in
  `CHANGELOG.md`;
- public README wording should avoid internal-only labels where possible:
  describe the user-facing survey format/workflow, avoid AI handoff references,
  avoid local-only test baselines, and prefer public roadmap wording over
  maintainer planning notes; keep the README Help Center section high-level and
  leave option-by-option usage details inside the in-app Help Center; the
  README has been reduced to a GitHub-facing overview/quick-start structure
  rather than a second user manual;
- `qt_ui/qt_theme.py` is the source of truth for the active Qt palette values;
  the old UI palette draft document has been removed from public docs to avoid
  stale duplicated theme data;
- the Tk to Qt migration is substantially complete;
- the V2 functional scope is effectively closed for the current release: no
  known AP Group, live-map, PDF, quality-dashboard or core survey blocker is
  open;
- `v0.9.3-beta.1` adds scanner-data validation surfaced in Survey Quality:
  fallback `netsh` capture, missing channel-width details for channel-sensitive
  rows and missing 6 GHz frequency data now become point-level findings with a
  dedicated KPI, recommendation card and detail rows;
- `v0.9.3-beta.2` changes Survey Quality to scale better on larger surveys:
  the main dashboard keeps the full point table out of the first view, while
  actionable point-related KPI cards open either compact point-table overlays
  for point-evidence issues or Extra Details for structured scanner/Dominant AP
  diagnostics; Total Points and Scan OK are summary-only cards; follow-up polish in the
  same beta uses a wider three-column KPI grid, a subtle placeholder slot for
  future metrics, scrollable `What To Fix Next` content and a fixed formatted
  Survey Scope panel; filtered point-list overlays now size to whole rows, cap
  the default table at 14 visible rows, shrink for small result sets and use a
  compact single-height `# / X / Y / Issue` table with KPI-specific issue
  text; scanner Extra Details now mirror the Dominant AP finding/detail pattern
  and explicitly label counts as raw `scan rows` for the measurement point,
  while `NETSH` fallback is shown on the scanner line instead of as a duplicate
  fallback-row count; Scanner Details Extra Details default to four visible
  whole cards before scrolling so large `netsh` finding sets do not open
  oversized dialogs or show a partially clipped next card; AP Model KPI cards
  now route to their matching Extra Details for AP Memory matches, APs without
  position, AP config warnings, channel changes and Dominant AP findings, with
  metric-specific whole-card limits: Scanner Details 4, Dominant AP Findings 5,
  AP Config Warnings 5, Channel Changes 4, AP Memory Review 5 and APs Without
  Position 6; Extra Details header descriptions are also measured after layout
  at their real dialog width so longer recommendation text does not create
  inconsistent blank space above the cards;
- `v0.9.5-beta.1` is closed/tagged as a source beta for connected-client
  roaming diagnostics:
  scanner code normalizes the currently associated BSSID from `lswifi` and
  `netsh`, survey CSV and raw `.scan` rows persist optional `is_connected`
  evidence, and Survey Quality now flags possible sticky-client points when the
  laptop stayed connected to one AP group while another AP group on the same
  SSID was at least 8 dB stronger. Windows PyInstaller `onedir` executable and
  ZIP release package have been regenerated on request from this beta line.
  Latest zipped Windows release artifact:
  `dist\WifiHeatmap-v0.9.5-beta.1-win64.zip`;
- `v0.9.6-beta.1` closes the post-`v0.9.5-beta.1` validation polish line. The
  Windows PyInstaller `onedir` executable and ZIP package were regenerated on
  request. Latest zipped Windows release artifact:
  `dist\WifiHeatmap-v0.9.6-beta.1-win64.zip`;
- post-`v0.9.5-beta.1` EN/IT wording polish normalized the most visible UI and
  Help terminology before the 1.0 validation survey: Italian now avoids weaker
  hybrid phrases such as `Finding`, `Extra Details`, `Dominant AP` and
  `metadata` where natural Italian wording is clearer, while preserving
  established technical terms such as BSSID, SSID, AP, dBm, fallback and
  override where appropriate;
- post-`v0.9.5-beta.1` new-survey workflow no longer blocks tests on an
  external plan image: a generated A4 blank PNG is loaded temporarily for new
  surveys with a practical default scale and Grid enabled. New survey creation
  from the app start page asks only for metric or imperial before that scale is
  generated. Starting a new survey from an open survey first asks whether to
  discard changes, save, or cancel, then shows the same unit choice when the
  current survey has been handled. The blank plan is materialized beside the CSV as
  `<survey_stem>.png` only if the user saves without loading a real plan. If a
  real plan is loaded later and the survey is saved, the obsolete generated PNG
  is deleted. Grid now draws a compact in-map scale label such as
  `1 square = 1 m` or `1 square = 3 ft`;
- post-`v0.9.6-beta.1` manual Boundaries mask work has started. Step 1 adds the
  Survey-tab View toggle, floating vertical toolbar, tool/shape state and Grid
  mutual exclusion, with Grid also acting as the switch back from Boundaries
  when scale is available. Follow-up steps still need raster mask drawing/erasing,
  sidecar persistence and Live/PDF mask application;
- `v0.9.4-beta.1` is closed as a source-tagged beta with the AP metadata
  foundation for
  local/zone-only coverage scope: AP group metadata now normalizes and
  persists `coverage_scope=local` plus optional `coverage_radius_m` through
  survey save/load and AP Memory. AP Group Metadata now exposes Site-wide vs
  Local Area controls, an explicit Auto Area checkbox, and an optional manual
  Local Radius displayed in the selected measurement system while stored
  internally in meters. Survey Quality now consumes this scope per measurement
  point: local-only SSIDs are evaluated inside a manual AP radius when scale and
  AP position are available. Auto Area estimates a temporary radius from the
  farthest usable local reading plus a small margin when AP position and scale
  are available, and falls back to per-point usable signal evidence otherwise.
  Missing Relevant Networks now warns for any expected SSID absent at a point
  after Local Area scope is applied, and Dominant AP position diagnostics use
  the same per-point scope to avoid local AP nearest-position noise outside the
  expected area;
- `v0.9.4-beta.2` is closed as a Help usability beta: the Help Center left
  navigation now supports expandable subsection entries generated from the page
  headings, so long pages can be scanned and jumped through without splitting
  the current content into separate fragile pages. Parent-section selection was
  stabilized after visual review so expanding a page no longer jumps to a child
  subsection;
- Help content and structure have an expanded V2 Help Center implementation;
  the Recommended Workflow page has received the first visual-density polish
  pass with step cards, decision-gate rows and Qt-compatible accent-column
  callouts; spacing, vertical card gaps and page margins are tuned for the
  limitations of QTextBrowser; the non-control pages now follow the same
  structured pattern and explain current Survey, Survey Quality, AP Group/AP
  Memory, Live Map, PDF, warning and glossary workflows from the Qt
  implementation; the AP Group page now uses an evidence-to-model guide with
  compact cards for BSSID management, roles, metadata, channel overrides, clean
  channel changes and AP Memory states, with workflow-card spacer rows aligned
  to the rest of the Help renderer; the Live Maps page has been converted from
  reference tables to card-based toolbar, map-choice, visible-option,
  option-meaning and reading-limit guidance; the PDF Reports page now explains
  save-before-export behavior, output naming, full-map rendering, map-type page
  composition, diagnostic cards and pre-send checks with the same card/gate
  structure; the Warnings page now separates point-rescan findings, AP
  identity/position warnings, metadata/channel warnings, channel-change behavior
  and troubleshooting/review order with card/gate guidance; remaining closeout
  is user review of the Help pages in the running app and a short EN/IT smoke
  pass;
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
- AP Memory is included in `v0.9.1-beta.1`: the app creates a persistent
  `ap_memory.memory` file in the application data folder, matches remembered AP
  data by known BSSID after normal AP grouping, applies missing aliases, roles,
  metadata, analysis-channel overrides and compatible map positions, and flags
  reused groups as `From Memory` until the user confirms or edits them; if a
  manual AP Group already has local metadata but AP Memory contains different
  saved data, AP Group Manager marks it as a memory-update candidate and exposes
  `Update From Memory`; AP Group save seeds the memory even when the survey
  metadata itself did not change, and the workspace footer shows
  empty/saved/to-confirm memory status; the Settings popup exposes AP Memory
  folder/open and clear actions, with destructive confirmation before clearing;
- the 2026-05-12 operational test survey is a useful baseline: all 25 points
  passed quality, all raw samples came from `lswifi`, relevant AP positions were
  complete, and the remaining findings are AP setup/anomaly diagnostics rather
  than point-rescan problems.
- the Survey Quality Dashboard now separates point-rescan issues from AP setup
  diagnostics, defaults to showing only points with findings when findings
  exist, and includes a prioritized "what to fix next" panel with expandable
  per-problem detail rows.
- the main workspace navigation and dashboard KPI area have been polished for
  the current Qt surface; remaining UI changes should be treated as targeted
  polish rather than V2 architecture work.
- `images/app_icon.png` is now the application/window icon source and
  `images/app_icon.ico` is generated from it for the Windows PyInstaller EXE;
  both assets preserve transparent rounded corners. The start screen also
  places the icon next to the product name.

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
  - `is_connected`;
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

- styled grouped metric cards for survey points, scan quality and AP model
  health;
- separate scan-OK/points-to-review counts, with Points To Review acting as the
  actionable point-review list and including AP-position/Dominant AP findings
  when the point itself needs inspection;
- point-related KPI cards open either filtered point-table overlays or
  recommendation Extra Details, keeping the main dashboard focused on counts and
  next actions instead of a long table;
- KPI cards use a stable three-column grid; Survey Points uses one row, while
  Scan Quality and AP Model use two rows with a subtle placeholder card in the
  final empty slot so card widths and reserved space stay consistent;
- KPI point-list overlays size the table to whole rows, avoiding half-visible
  rows at the default size and reducing empty table area for small filters;
- point-list overlay height is calculated without a horizontal scrollbar because
  the compact Issue column elides overflow and exposes full text through the
  tooltip;
- short point-list overlays lock vertical resize once all matching rows are
  visible, while longer lists let manual vertical resize grow the table area
  rather than the header area;
- KPI point-list overlays intentionally show only point number, coordinates and
  issue text, because the overlay is for finding and navigating diagnostics, not
  duplicating the full Survey point table;
- KPI point-list overlays scope the Issue column to the selected KPI, so
  Points To Review and point-evidence views do not mix unrelated diagnostics;
- overlay issue wording has been shortened for readability: Points To Review
  lists the affected KPI cards to inspect; quality KPI issue text is filtered by
  the selected status so Low Scan Confidence does not include Unstable Signal
  details and formats low confidence/unstable signal findings as user-facing
  diagnostics such as confidence percentage and dB variation;
- Total Points and Scan OK are not clickable because their filtered point tables
  do not add useful diagnostic context;
- Scanner Details and Dominant AP point-list issues use highlighted scanner/AP
  values and include the key context needed to decide what to inspect next;
- Scanner Details Missing and Dominant AP Findings KPI cards open their
  recommendation Extra Details dialogs instead of duplicating a poorer compact
  point table;
- missing relevant network information;
- low confidence/unstable point information;
- sparse-data count surfaced as its own dashboard metric;
- AP positioning awareness;
- AP metadata consistency checks;
- AP configuration warning list;
- prioritized "what to fix next" guidance for missing relevant networks, sparse
  scans, low confidence, unstable signal, AP position warnings, missing AP
  positions and AP metadata warnings;
- "what to fix next" cards stay compact and expose scalable detail dialogs;
- detail dialogs list each affected AP group or measurement point on its own
  row with contextual actions such as live AP Channels, Interference, Dominant
  AP, AP metadata, AP Group Manager or point focus;
- detail dialogs use domain-specific counts and concise observed/expected
  wording so large AP metadata and channel-change lists stay readable;
- Dominant AP detail rows include dominant AP, closest physical AP, distance
  and finding context while keeping point-list issue text compact;
- clean/ambiguous AP channel changes are surfaced in the quality dashboard so
  the user can verify the latest-channel default or set an explicit analysis
  channel override;
- setup-only AP diagnostics use a setup warning state instead of implying that
  measurement points need to be rescanned;
- fullscreen dashboard presentation, compact metric cards, KPI-driven
  point-table overlays, scrollable recommendation cards, fixed Survey Scope
  context and stronger table selection contrast.

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
- user-facing `From Memory` management state, status marker and confirmation
  action for AP groups whose metadata was applied from AP Memory;
- user-facing `Memory Update` management state, strikethrough memory status
  marker and explicit `Update From Memory` action for manual AP groups whose
  current local metadata differs from AP Memory;
- compact AP Group Manager footer toolbar with `Memory` and `Alias` menus,
  a separator before the core AP editing commands, and diagnostic/reset actions
  aligned to the right;
- workspace footer AP Memory status with the memory file path in the tooltip;
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
- continuous map confidence opacity is smoothed across the grid rather than
  assigned by nearest survey point, avoiding polygonal opacity artifacts when
  neighboring scans have different confidence values;
- continuous maps can optionally apply Survey Bounds, a Delaunay-based local
  point-envelope alpha mask that fades the rendered layer outside the measured
  survey area while preserving the original point data;
- calibrated continuous-map defaults derive max distance from survey-point
  spacing percentiles, clamped to a conservative range, instead of using a fixed
  meter value for every survey density;
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
- Help is available with expanded workflow-aligned content; the Controls page
  still deserves its own final review pass, and the broader Help Center needs a
  running-app EN/IT smoke review before V2 closeout.

### UI/Workflow Foundation

Implemented:

- fullscreen main app by default;
- start screen with scaled layout;
- toolbar-based workflow;
- balanced top app-bar sections for Project, Analysis and View actions;
- new/open/save survey handling;
- new surveys ask for metric or imperial units before creating the generated,
  pre-scaled A4 blank plan and Grid, so points can be captured for tests before
  a real plan is available without immediately invalidating scale. From the app
  start page this unit prompt has no Cancel button; from an open survey, New
  first asks whether to discard changes, save, or cancel, then shows the same
  no-Cancel unit prompt if the current survey is closed. Saving while that
  generated plan is still active writes
  a same-name PNG beside the CSV, while loading a real plan clears generated
  scale/grid state, marks the generated PNG for deletion, and removes it after
  the next successful save; the Grid overlay displays its current square size
  directly on the map and prefers 3 ft rather than 5 ft for imperial grids when
  the map scale permits, keeping it close to the 1 m metric step;
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
  matching the AP Group table contrast;
- EN/IT user-facing titles, buttons and compact labels have been normalized for
  the current Qt surface;
- compact localized buttons recalculate their minimum width from the active
  translation, and point-capture warning dialogs grow their minimum width when a
  translated button row needs more space;
- i18n/UI tests guard translation key parity, placeholder parity, capitalized
  title/button starts and compact localized button fit;
- main workspace Survey/Live Map navigation uses full-width Qt tabs with
  theme-aware active gradients, centered split-adjacent labels and a faded
  active underline.
- the Analysis toolbar follows the recommended validation flow by placing
  Survey Quality before AP Groups.

## Remaining Work

Closeout assessment:

- no known V2 blocker remains in the survey core, AP Group workflow, live maps,
  live PDF reports, channel-change handling or Survey Quality Dashboard;
- the Help System rework has an expanded Help Center implementation and needs
  final review/polish before V2 closeout;
- the other items below are monitoring or post-V2 expansion candidates and
  should not block calling the current V2 workflow complete.

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

Post-V2 candidate checks:

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

Current implemented expansion:

- the dashboard now provides prioritized "what to fix next" guidance;
- sparse-data points are counted explicitly;
- scan-review counts are separated from AP setup diagnostics;
- AP metadata, missing-position, dominant-AP and channel-change
  recommendations use expandable detail rows so large surveys do not overload
  the main dashboard;
- detail rows include shortcuts into the live map, AP metadata, AP Group
  Manager and point-focus workflows.
- local/zone-only AP coverage scope is applied before point-quality evaluation,
  so SSIDs marked Local Area are not treated as whole-building expectations.
  A manual radius uses scale and AP position. Auto Area first estimates a local
  radius from the farthest usable local reading plus a small margin when AP
  position and scale are available, then falls back to per-point usable signal
  evidence if the spatial data are missing. Dominant AP position diagnostics use
  the same per-point scope, so local APs outside their expected area are not
  used as nearest-position candidates.
- Missing Relevant Networks now evaluates missing expected SSIDs after that
  per-point scope is known. A global relevant SSID absent at a point is a
  warning; a Local Area SSID outside scope is ignored; a Local Area SSID inside
  scope but absent is a warning.

Post-V2 possible additions:

- point spacing quality;
- coverage completeness by area;
- scan backend reliability score;
- repeated scan variance per AP group;
- likely mesh/roaming ambiguity detection;
- richer point-spacing or area-completeness recommendation lists.

### 5. Live Map Validation And Final Polish

The live-map Qt implementation is now the main working surface. Remaining work
is monitoring and targeted polish rather than migration or release-blocking V2
work.

Completed validation:

- Coverage, AP Channels, Dominant AP and Interference were exported from the
  latest real operational survey;
- report/legend/card alignment fixes from that pass are implemented;
- AP-position warning triangles and Dominant AP report wording are readable
  enough for the current real warnings;
- current real warnings are considered valid until new data proves otherwise.

Post-V2 monitoring checks:

- verify legends/scales on additional floor-plan sizes and aspect ratios;
- verify AP group filters and positioned AP markers on larger surveys;
- tune performance only if large real surveys expose measurable lag;
- consider optional hover pinning later if tooltip inspection still feels
  difficult.

### 6. Generated Report Improvements

Live-map PDF export now exists and covers the V2 closeout needs. Reporting can
become more complete as a post-V2 reporting track.

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

Expanded V2 Help Center content is implemented.

Implemented:

- two-column Help Center with vertical navigation and formatted HTML content;
- workflow-first overview instead of a feature-list-only help page;
- controls cheat sheet using the existing image assets and current V2 gestures,
  including separate left-click, left-drag and wheel-modifier combinations;
- global measurement-system preference with metric default and imperial display
  option; survey CSV metadata stores both `px_per_meter` and
  `measurement_system`, so a reopened survey uses its own unit context instead
  of the current global preference. Calibration input, live Max Distance labels,
  AP-position tooltips and PDF report distances use the selected display
  system; changing measurement system after a survey has calibrated scale
  prompts the user and clears `px_per_meter` so scale must be recalibrated in
  the chosen system;
- dedicated sections for Survey/Scans, Survey Quality, AP Groups, Live Maps,
  PDF Reports, Warnings and Glossary;
- detailed workflow gates, point capture guidance, raw sidecar/aggregation,
  scanner backend behavior and relevant SSID logic;
- survey screen boxes, point-table actions and saved/raw data meaning;
- generated A4 blank plan behavior for new surveys, pre-scaled blank-plan grid,
  same-name PNG save behavior when no real plan has been loaded, and cleanup
  when a generated blank plan is later replaced;
- Survey Quality KPI meanings, "what to fix next" guidance, AP setup
  diagnostics, dashboard controls, scalable detail dialogs and point-rescan
  recommendations;
- AP Group Manager layers, filters, BSSID management, roles, metadata,
  AP Memory states, clean/ambiguous channel changes and manual
  analysis-channel override;
- Live Map toolbar/options behavior, map-type-specific controls, option memory,
  interpretation limits and channel-change handling;
- PDF report structure, live-export save behavior, numbered callouts,
  map-type page rules and when warnings are diagnostics rather than survey
  errors;
- warning troubleshooting patterns and expanded glossary;
- EN/IT translations and tests for section availability.
- AP Memory clear/delete confirmations now use the same themed Qt dialog styling
  from both the start screen and the main workspace settings popup.
- Help Center content now covers AP Memory states, confirm/update workflows,
  settings access, and the fact that closing AP Group Manager with the window X
  behaves like Cancel rather than Save.
- The Recommended Workflow overview page now uses visual step cards and
  compact decision-gate rows instead of a dense operational table; its callouts
  use table-based accent columns because QTextBrowser does not reliably render
  modern left-border styling on block elements. The workflow cards use explicit
  spacer cells and the same full content width as the other blocks so margins
  line up while preserving a central gap.
- The Controls Help page now separates simple left click from left-click drag
  and displays Ctrl/Shift as modifier combinations with the wheel instead of
  standalone actions. Shift + wheel now pans map views horizontally so the help
  page matches implemented behavior, and the Wi-Fi/AP marker is no longer shown
  as a control.
- The non-control Help pages now use the same table/callout pattern and were
  checked against the current Qt code behavior instead of older text notes.
  Coverage includes Survey boxes/actions, Quality controls, AP Group Manager
  layers, BSSID Manager, AP Memory confirm/update states, metadata channel
  override limits, Live Map option visibility, PDF export behavior, warning
  troubleshooting and grouped glossary terms.
- The Survey Help page has been visually tightened after screenshot review:
  the opening survey screen box table is now a compact 2x3 summary-card grid,
  "Saved Networks" wording has been corrected to Relevant SSIDs, `.scan` is
  explained as a sidecar that users normally do not open directly, Auto scanner
  is called out as the recommended default, and good point placement is a
  highlighted field-rule block.
- The Help renderer now normalizes tables to full content width with
  Qt-compatible width/cell spacing attributes, so tables and callouts do not end
  at the text length or crowd the scrollbar. Callout accent cells also receive
  explicit HTML widths so list-heavy callouts keep the same slim left accent as
  simple one-line callouts. Scanner backend names on the Survey page are plain
  table text rather than badge-style highlights.
- The Survey Quality Help page has been reorganized as an operational dashboard
  guide: point quality and AP model are shown as two decision layers, KPI
  meanings are grouped like the real dashboard, "what to fix first" is expressed
  as priority gates, and detail dialogs are explained as the scalable path for
  large surveys. The latest wording pass also documents dashboard status,
  Survey Scope, point-list overlays versus Extra Details, AP-model findings and
  the recommended review order.
- The Glossary Help page remains as a final terminology reference but is now
  grouped into Wi-Fi evidence, AP model, quality/warnings, memory/persistence
  and live-map/report terms instead of a single long table.
- Survey Quality AP-model Extra Details were visually tightened after the
  all-warning synthetic dataset review: AP Memory matches, AP metadata warnings
  and channel-change items now use structured multiline label/value text
  instead of compact pipe-separated detail strings. Their dialog row-height
  estimates were adjusted at the same time so the existing whole-card fit logic
  does not clip the taller cards or expose partial next cards.
- Follow-up quality detail polish fixed sparse detail-card stretching in
  dialogs, so card content keeps a stable top margin instead of being vertically
  centered inside extra space. `AP Memory Review` now explains both memory
  states: `M` for data applied from memory, and struck-through `M` for manual
  AP data that differs from saved memory. `APs Without Position` explicitly
  shows AP group/label and the missing physical-position data.
- `AP Memory Review` dashboard recommendation now keeps navigation inside Extra
  Details: the main card no longer shows a direct `AP Group: ...` button because
  the detail row already carries the AP-specific action.
- `APs Without Position` now follows the same scalable interaction pattern: the
  dashboard recommendation reports the aggregate count, while Extra Details
  explains the missing physical position and exposes the row-specific Open AP
  Group action. Follow-up simplification removed the unused short AP label
  summary and repeated label field from each missing-position card.
- Extra Details dialog sizing was consolidated around measured card widgets.
  The previous per-metric estimated row-height constants were removed; each
  dialog now builds its cards, measures their real height at the available
  width, then sizes the scroll area to the configured visible card count plus
  layout spacing/margins. Sparse dialogs lock to content height, while overflow
  dialogs keep the default whole-card fit and can expand the scroll area.
  Follow-up removed the trailing layout stretch from the scroll content and
  fixes each card to its measured height-for-width, preventing both scrollable
  blank space below the last card and vertically stretched card content. The
  initial overflow window height is also corrected after header reflow so
  translated dialog text cannot donate extra height to the scroll area and show
  a partial next card.
- Extra Details sizing now has explicit fake-data regression coverage for all
  detail types. Tests open each dialog below its limit, exactly at its limit and
  above its limit, then verify full-card boundaries, overflow behavior and no
  extra scrollable blank space after the last card.

Remaining closeout:

- review wording and visual density in the real UI;
- refine section ordering and formatting only if visual inspection shows a real
  readability problem;
- keep text concise and visual where possible.
- complete the manual Boundaries mask workflow one step at a time: raster draw
  and erase, save/load sidecar, Live/PDF application and Help text.

## Suggested Next Priorities

V2 closeout:

1. Review `v0.9.6-beta.1` Help navigation, Local Area scope, Client Roaming,
   blank-plan workflow and continuous map bounds diagnostics in the running UI
   against real survey data, especially intentionally local office-router SSIDs, and
   tune Auto Area or connected-client thresholds only if the evidence shows
   false positives or false negatives.
2. Review the new Help Center in the running UI and polish wording/formatting
   where real screenshots show a problem.
3. Do a short EN/IT Help and UI smoke pass after the Help review.

Monitoring:

5. Keep AP Group, live PDF and Survey Quality in monitoring mode unless new
   real data exposes a concrete issue.
6. Validate AP Memory behavior on repeat surveys, especially large AP sets,
   copied memory files and floor-plan position reuse.
7. Validate 6 GHz behavior with real 6E/7 hardware data when available.
8. Tune performance only after larger real surveys show measurable lag.

Post-V2 expansion:

10. Improve combined/generated reporting beyond individual live-map exports.
11. Add a dedicated AP Memory management view only if real use needs explicit
   review, cleanup or conflict resolution beyond the current automatic
   apply/confirm flow.
12. Use AP metadata more deeply in diagnostics where the rule is clear.
13. Refine the AP physical/radio/BSSID model only if real deployments require it.
14. Add an AI Advisor next to each live map. It should analyze the measured
    survey evidence and propose actionable RF changes, such as channel-width or
    channel adjustments to reduce interference. Recommendations must remain
    grounded in visible survey data, explain assumptions/confidence, and stay
    advisory rather than silently mutating AP metadata or map settings.
15. Add a lightweight Floorplan Creator for technical RF floor maps. Scope
    should be scaled geometry, snap, wall thickness, simple shapes, doors and
    measurements; it should not become an interior-design tool.
16. Add richer deployment/reporting outputs.

## Final Vision

The long-term goal remains a tool capable of:

- collecting real RF data;
- preserving evidence behind every aggregate value;
- understanding AP relationships;
- evaluating survey reliability;
- detecting anomalies;
- explaining generated maps;
- advising on corrective RF actions when evidence is strong enough;
- creating simple survey-ready floor plans when no drawing is available;
- helping users improve Wi-Fi deployments.

The tool should make the survey more trustworthy, not just make prettier
heatmaps.
