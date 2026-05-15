# Changelog

This file tracks user-facing changes between official release builds.

The project uses semantic public release tags. `V2` is the internal survey and
architecture generation, while releases use tags such as `v0.9.0-beta.1`,
`v0.9.0-beta.2`, and later `v1.0.0`.

## Unreleased

- Survey Quality `Scanner Details Missing` Extra Details now use the same
  finding/detail structure as Dominant AP diagnostics, with separate scanner,
  checked scan-row count, missing channel-width/frequency rows and impact text.
- Scanner-detail wording now says `scan rows` so the count is clearly raw scan
  evidence for that measurement point, not a count of measurement points.

## v0.9.3-beta.2 - 2026-05-15

Beta focused on making Survey Quality scale better for larger real surveys.

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
