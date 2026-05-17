# Changelog

This file tracks user-facing changes between official release builds.

The project uses semantic public release tags. `V2` is the internal survey and
architecture generation, while releases use tags such as `v0.9.0-beta.1`,
`v0.9.0-beta.2`, and later `v1.0.0`.

## Unreleased

- Started the manual Boundaries mask workflow with a Survey-tab View toggle and
  floating drawing toolbar. This first step wires the toolbar, tool state and
  two-way Grid/Boundaries switching; mask drawing, persistence and Live/PDF
  application are planned as follow-up steps.
- Made the Boundaries toolbar load lazily on first use, keeping its icon setup
  out of the startup "Loading components" path while preserving the same
  Survey-tab behavior.
- Survey CSV metadata now stores the selected measurement system, so reopening a
  metric or imperial survey no longer depends on the current global preference.
  The current survey format now requires the full aggregate/raw headers,
  `measurement_system`, an explicit `raw_data_file` metadata entry and a valid
  `.scan` sidecar, and AP aliases are read from `ap_groups` instead of the old
  duplicate `ap_aliases` metadata.
- Startup and survey lifecycle logging now marks workspace construction,
  language application, new/open/save survey phases and workspace show steps, so
  future freezes during loading leave a clearer last-known phase in the log.

## v0.9.6-beta.1 - 2026-05-17

- Live Coverage and Interference maps now smooth scan-confidence opacity instead
  of assigning it by nearest point, reducing polygonal artifacts in continuous
  overlays. Default continuous-map settings now use smoothing 5.0 and, on
  calibrated surveys, derive max distance from survey-point spacing with a
  conservative 260 px fallback when spacing cannot be estimated. Live Maps Help
  now documents the adaptive Max Distance default and its 4-point threshold.
- Added an optional Survey Bounds / Limite Rilievo control for continuous Live
  Maps and PDF exports. When enabled, the app fades the overlay outside a local
  measured-point envelope, reducing unused edge bubbles around the survey area
  without changing the underlying survey data. The Help text now notes that the
  option works best when points also follow the boundary of the area to show.
  The bounds mask intentionally keeps a strict local geometry and fade so it
  does not reopen large empty edge bubbles.
- New surveys now open with a generated, pre-scaled A4 blank plan and an active
  Grid overlay so test captures can start without a real floor plan. New survey
  creation from the start page now asks only for metric or imperial units before
  creating that default blank-plan scale. Starting a new survey while another
  survey is open now asks whether to discard changes, save, or cancel before
  asking for metric or imperial units.
  If the blank plan is still active on save, the app writes a same-name PNG next
  to the CSV and links the survey metadata to that file. Loading a real plan
  later clears the generated scale/grid state, and the obsolete blank PNG is
  deleted after the next successful save. The Grid overlay now shows its
  current step directly on the map, for example `1 square = 1 m` or
  `1 square = 3 ft`, with extra padding so the scale label does not clip at the
  right edge. Imperial grids now prefer a 3 ft step when scale permits, keeping
  the blank-plan grid close to the metric 1 m step used for practical point
  placement. Starting another new survey from an untouched generated blank
  survey now discards that empty session without forcing a save prompt.
- Polished English and Italian UI/Help wording for the 1.0 validation pass,
  normalizing technical terms such as AP dominant diagnostics, extended details,
  raw scan evidence, warnings, AP metadata and client roaming.
- Windows `onedir` executable and ZIP package were regenerated for
  `v0.9.6-beta.1`.

## v0.9.5-beta.1 - 2026-05-16

- Added a README Development Approach note documenting transparent use of
  AI-assisted coding tools while keeping project direction, field testing and
  validation manually driven.
- Started connected-client BSSID evidence for future roaming diagnostics:
  scanner code now normalizes current connection details from both `lswifi` and
  `netsh`, and `netsh` scans can mark the currently connected BSSID just like
  `lswifi` scans already did.
- Survey CSV and raw `.scan` sidecars now persist `is_connected` evidence for
  each aggregate row and raw scan sample when the scanner backend exposes the
  currently associated BSSID. The new field is optional in older V2 survey
  files.
- Survey Quality now uses connected-BSSID evidence to flag possible sticky
  client/roaming points: when the survey laptop stayed connected to one AP
  group while another AP group on the same SSID was at least 8 dB stronger, the
  point appears in a new `Client Roaming` KPI and in `Points To Review`.

## v0.9.4-beta.2 - 2026-05-16

- Help Center navigation now uses expandable section groups with automatically
  generated subsection entries from each page heading, making long pages such
  as Survey Quality, AP Groups and Live Maps easier to scan without splitting
  the content into fragile separate dialogs.
- Fixed parent-section selection in the Help Center tree so clicking a main
  page such as AP Groups keeps that page selected instead of jumping to a child
  subsection after the tree expands.

## v0.9.4-beta.1 - 2026-05-16

- Added local/zone-only coverage scope for AP groups: metadata can now persist
  normalized `coverage_scope=local` and optional `coverage_radius_m` values
  through survey save/load and AP Memory.
- AP Group Metadata now exposes Coverage Scope controls: Site-wide is the
  default, Local Area can be selected for APs or SSIDs that are intentionally
  local, Auto Area keeps radius derivation automatic, and an optional manual
  Local Radius uses the selected measurement system while still storing meters
  internally.
- Fixed Coverage Scope initialization when reopening Local Area metadata with
  automatic area enabled.
- Survey Quality now applies Local Area scope per measurement point: local-only
  SSIDs are evaluated only inside their manual radius when scale and AP
  position are available. Auto Area now estimates a temporary radius from the
  farthest usable local reading plus a small margin when AP position and scale
  are available, then falls back to per-point usable signal evidence when those
  data are missing.
- Dominant AP position diagnostics now use the same per-point scope, so APs
  marked Local Area are not considered nearest-position candidates outside
  their expected area.
- Missing Relevant Networks now reports each expected SSID absent at a point,
  after Local Area scope is applied. This keeps local SSIDs quiet outside their
  area while still warning when a local SSID is missing inside scope.

## v0.9.3-beta.2 - 2026-05-16

Beta focused on making Survey Quality scale better for larger real surveys.

- Survey Quality Help now explains the quality dashboard status, Survey Scope,
  KPI point lists, Extra Details, AP-model findings and review order more
  explicitly in both English and Italian.
- Survey Quality AP-model Extra Details now use structured multiline detail
  text for AP Memory matches, AP metadata warnings and channel-change items,
  making dense warning datasets easier to inspect visually.
- Survey Quality AP-model Extra Detail dialogs now reserve taller whole-card
  rows for multiline AP Memory, AP metadata and channel-change cards, avoiding
  clipped content or half-visible cards after the text polish.
- Survey Quality Extra Details no longer stretch sparse detail cards to fill
  empty dialog space, keeping top/bottom card padding consistent. AP Memory and
  APs Without Position detail text now distinguish remembered AP data from a
  missing physical map position.
- Survey Quality `AP Memory Review` now covers both memory-applied AP groups
  and manual AP groups whose current data differs from saved AP Memory. The
  direct AP Group shortcut was removed from the main dashboard card because
  each detail row already has its specific AP Group action.
- Survey Quality `APs Without Position` now follows the same interaction model:
  the dashboard recommendation no longer duplicates AP Group buttons, and Extra
  Details carries the row-specific Open AP Group action plus placement guidance.
  Follow-up simplification removed repeated AP labels and unused label-summary
  data from the missing-position cards.
- Survey Quality `Scanner Details Missing` Extra Details now use the same
  finding/detail structure as Dominant AP diagnostics, with separate scanner,
  checked scan-row count, missing channel-width/frequency rows and impact text.
- Survey Quality Extra Details sizing now measures the actual card widgets
  after construction instead of relying on per-category estimated row heights.
  Default dialog height is the sum of the configured visible card count,
  measured card heights, spacing and margins; sparse dialogs lock to content
  height while overflow dialogs can expand the scroll area. Follow-up fixed the
  scroll content itself by removing the trailing stretch below the last card and
  fixing each card to its measured height-for-width so internal labels do not
  stretch vertically. A final pass keeps the initial overflow height locked to
  the configured whole-card boundary even when translated header text reflows to
  a shorter rendered height. Dialog header descriptions are now fitted to their
  actual post-layout width so long recommendation text does not reserve
  phantom blank space above the cards.
- Scanner-detail wording now says `scan rows` so the count is clearly raw scan
  evidence for that measurement point, not a count of measurement points.
- The redundant fallback row count was removed from scanner details; `NETSH` is
  labeled as the fallback scanner on the scanner line instead.
- Scanner Details Extra Details now default to at most four visible cards, with
  the remaining affected points available through the dialog scroll area; the
  scroll height is fitted to whole cards so the next card is not partially
  visible.
- AP Model KPI cards now open their matching Extra Details dialogs for AP
  Memory matches, APs without position, AP config warnings, channel changes,
  and Dominant AP findings. Detail dialogs use metric-specific whole-card
  limits: Scanner Details 4, Dominant AP Findings 5, AP Config Warnings 5,
  Channel Changes 4, AP Memory Review 5, and APs Without Position 6.
- Survey Quality tests now exercise every Extra Details dialog type with
  below-limit, exact-limit and overflow fake detail sets, checking whole-card
  default sizing, overflow behavior and the absence of scroll slack below the
  final card.
- Windows `onedir` executable and ZIP package were regenerated for
  `v0.9.3-beta.2`.
- Survey Quality no longer shows the full measurement-point table in the main
  dashboard view.
- Actionable KPI cards now open the most useful diagnostic view: Points To
  Review, low confidence, unstable signal and missing/sparse point evidence open
  compact point-table overlays, while Scanner Details Missing and Dominant AP
  Findings open Extra Details. Total Points and Scan OK remain summary-only
  cards.
- Removed the main `Show Only Points With Findings` control because filtering is
  now driven by the selected KPI.
- KPI cards now use a wider three-column layout with a subtle placeholder card
  for future metrics, and Survey Scope is pinned as a formatted context panel
  at the bottom of the recommendation column.
- The `What To Fix Next` panel shows all recommendation cards inside its own
  scroll area instead of hiding one behind a `+N more` summary.
- Filtered point-list overlays now size their table to whole rows, defaulting
  to at most 14 visible rows and shrinking automatically for small result sets.
- Point-list overlays now use a compact `# / X / Y / Issue` table with
  single-height rows; the aggregate card is now `Points To Review`, which points
  users to the affected KPI cards. Quality KPI issue text is filtered by the
  selected status, so Low Scan Confidence does not include Unstable Signal
  details.
- Points To Review now includes points that only have Dominant AP findings.
  Scanner Details and Dominant AP KPI clicks open their richer Extra Details
  dialogs instead of duplicating those diagnostics in a compact point table.
- Point-list overlay windows now fit full single-height rows without the
  horizontal scrollbar adding empty space or cutting the last row, and quality
  issue text now uses clearer diagnostic wording such as confidence percentage
  and signal variation. Short point lists lock their height; longer point lists
  grow the table area when the overlay is resized.
- Help Center, README and V2 notes now describe KPI-driven point lists as the
  scalable way to inspect large surveys.

## v0.9.3-beta.1 - 2026-05-15

Beta focused on scanner-data validation after the first broad office survey.

- Survey Quality now flags measurement points collected with fallback `netsh`
  scanner data.
- Survey Quality now flags channel-sensitive rows missing channel width and
  6 GHz rows missing frequency data.
- Added a dedicated `Scanner Details Missing` KPI, recommendation card and
  detail rows so these findings stay separate from low signal confidence or AP
  model diagnostics.
- Help Center, README and V2 notes now document limited scanner details as a
  rescan reason before relying on Interference, 5 GHz width-overlap or 6 GHz
  interpretation.

## v0.9.2-beta.1 - 2026-05-14

Beta focused on Help Center polish, gesture documentation, measurement-system
settings, and release-readiness. Windows release artifacts are built as a
PyInstaller `onedir` executable plus ZIP package.

- Targeted Help Center review/polish, office validation fixes, and small
  release-readiness adjustments.
- Recommended Workflow help page now uses a visual step-card layout, clearer
  decision-gate rows, and AP Memory context in the AP modeling phase.
- Recommended Workflow callouts now use a Qt-compatible accent-column layout,
  and the main toolbar now places Survey Quality before AP Groups to match the
  recommended validation flow.
- Recommended Workflow card spacing has been tuned for QTextBrowser so cards
  no longer crowd the scrollbar and the sequence reads less like a heavy table.
- Recommended Workflow blocks now share the same left and right content margins.
- Recommended Workflow card rows use a tighter vertical gap.
- Controls Help now separates left click from left-click drag, removes the AP
  Wi-Fi marker from the controls list, and shows Ctrl/Shift as implemented
  wheel-modifier combinations.
- App icon PNG/ICO assets now preserve transparent rounded corners for Windows
  executable embedding instead of baking white corners into the icon.
- Windows `onedir` executable and ZIP package were regenerated for
  `v0.9.2-beta.1`.
- Settings now include a metric/imperial measurement-system preference. Survey
  scale remains stored internally as `px_per_meter`, while calibration input,
  Live Map Max Distance, AP-position tooltips and dominant-AP PDF report
  distances follow the selected display system. Changing measurement system
  after scale calibration prompts the user and clears the current survey scale
  so it can be calibrated again.
- Help Center non-control sections now use the same visual/content pattern and
  document the current Survey, Quality, AP Group, AP Memory, Live Map, PDF,
  warning, and glossary workflows from the Qt implementation.
- Survey Help now uses compact summary cards for survey screen boxes and
  clearer sidecar/relevant-SSID/point-placement guidance.
- Survey Quality Help now reads as a dashboard guide with two decision layers,
  grouped KPI cards, prioritized fix gates, and scalable detail-dialog guidance.
- AP Groups Help now reads as an evidence-to-model guide with compact cards for
  BSSID management, roles, metadata, channel overrides, clean channel changes,
  and AP Memory states.
- AP Groups Help workflow-card rows now use the same spacer markup as the other
  Help pages, avoiding visible blank cells between card rows.
- Live Maps Help now uses card-based sections for toolbar actions, map choices,
  visible option sets, option meanings, and map-reading limits; Point Labels
  wording now matches the actual AP Channels/Dominant AP controls.
- PDF Reports Help now uses card/gate sections for save-before-export behavior,
  output naming, full-map rendering, map-type page composition, diagnostic
  cards, and pre-send review checks.
- Warnings Help now uses card/gate sections to distinguish point-rescan
  findings, AP model warnings, metadata/channel warnings, channel-change
  behavior, troubleshooting patterns, and review order.
- Glossary Help now uses grouped reference cards for Wi-Fi evidence, AP model,
  quality/warnings, memory/persistence, and live-map/report terminology instead
  of a single long table.
- Help Center tables and callouts now normalize to full content width in the Qt
  renderer, callout accent columns keep a fixed Qt-compatible width, and scanner
  backend labels are plain table text instead of badges.
- Help Center now documents AP Memory review states, confirm/update workflows,
  settings access, and AP Group Manager save behavior.

## v0.9.1-beta.1 - 2026-05-14

Feature beta focused on AP Memory and repeat-survey AP metadata reuse.

### Added

- Persistent AP Memory file for remembering AP aliases, roles, metadata,
  analysis-channel overrides, and compatible floor-plan positions across
  surveys.
- Automatic AP Memory application after normal AP grouping when known BSSIDs are
  seen again.
- "From Memory" review state in AP Group Manager and Survey Quality so reused
  AP data stays visible until confirmed or edited.
- Explicit memory-update detection for manual AP groups whose local AP data
  differs from the saved AP Memory record.
- Workspace footer status for AP Memory state and memory file location.
- Settings actions to open the AP Memory folder or clear AP Memory.
- Custom application/window icon and Windows executable icon.

### Changed

- AP Group Manager toolbar now groups memory actions under a dedicated Memory
  menu and alias actions under an Alias menu.
- Start screen now shows the application icon next to the product name.
- AP Group save seeds/updates AP Memory even when the open survey metadata was
  otherwise unchanged.
- Clear-memory confirmation uses the app's themed Qt dialog styling in both the
  start screen and main workspace.

### Known Beta Closeout

- Final Help Center visual/content review is still pending.
- Full office validation pass is still pending before `v1.0.0`.

## v0.9.0-beta.1 - 2026-05-13

Initial public beta for the completed V2 workflow.

### Added

- PySide6 desktop UI with startup window and main workspace.
- V2 survey CSV format with linked `.scan` raw-data sidecar.
- Repeated Wi-Fi scan capture with `lswifi` primary support and `netsh`
  fallback.
- Relevant SSID workflow.
- AP Group Manager with BSSID grouping, aliases, roles, metadata, expected
  bands/channels, analysis channel overrides, and physical AP positions.
- Survey Quality Dashboard with KPI cards, point-review diagnostics, AP
  setup/model diagnostics, and "what to fix next" guidance.
- Live Map tab with Coverage, Interference, AP Channels, and Dominant AP views.
- Live PDF export from the current map view, including Interference and
  Dominant AP issue-report pages where applicable.
- Shared Qt theme styling, scrollbar styling, stronger table selection, and
  polished Survey/Live Map navigation tabs.
- Expanded EN/IT Help Center for the V2 workflow.
- Public product version metadata exposed through Qt and release assets.

### Changed

- Legacy Tkinter UI is retired from the active workflow.
- Old generated PNG/CSV map export path is retired in favor of live PDF export.
- Public release assets use PyInstaller `onedir` ZIP packaging rather than
  `onefile`.

### Known Beta Closeout

- Final Help Center visual/content review is still pending.
- Full office validation pass is still pending before `v1.0.0`.
