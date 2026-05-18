# Changelog

This file tracks user-facing changes between official release builds.

The project uses semantic public release tags such as `v0.9.0-beta.1`,
`v0.9.0-beta.2`, and later `v1.0.0`.

## Unreleased

### Added

### Fixed / Changed

- Help Center navigation now visually separates main pages from subsection
  anchors, making the content list easier to scan on dense Help pages.
- Help and user-facing validation messages no longer expose the old internal
  migration label; architecture notes were renamed to
  `docs/ARCHITECTURE_NOTES.md`.
- Boundaries square brush strokes now use an axis-aligned square sweep instead
  of a thick Qt path, improving office-style straight edges and corners while
  avoiding warped joins during slow direction corrections.
- Signal Coverage point tooltips now expose point-local evidence: selected
  aggregation, samples, scan confidence, strongest reference AP and channel
  context, replacing the previous global source-row count.
- Shared map tooltip styling was refined for faster scanning, with clearer
  title spacing, aligned label/value rows and stacked formatting for long
  diagnostic values.
- AP Interference point tooltips now show confidence, serving/interferer
  signal, channel band context, overlap percentage and meaningful contributor
  or ignored-AP counts when available.
- AP Channels point tooltips now use the same readable evidence format as the
  other live maps, including signal, samples, confidence and channel band
  context.
- Dominant AP point tooltips now use the same readable evidence format as the
  other live maps, including signal, samples, confidence, second-AP context,
  roaming overlap and AP-position rows.
- Survey point and Wi-Fi AP floorplan tooltips are now aligned with live map
  tooltip styling and terminology, including translated labels and clearer
  signal, scope, role and observed AP evidence rows.
- AP Group refresh now auto-heals memory-applied `#2`/`#3` fragments when the
  survey rows show they belong to the same automatic AP group, preventing AP
  Memory from duplicating metadata across split physical APs.

## v0.9.7-beta.1 - 2026-05-18

### Added

- Manual Boundaries mask workflow on the Survey tab, with a View toggle,
  floating toolbar, draw/erase tools, circle/square brush shapes and confirmed
  clear. Boundary masks are saved next to the survey CSV as
  `<survey>.boundaries.png` and reopen with the survey.
- Saved manual Boundaries masks are applied to continuous Live Maps and PDF
  exports. When a manual mask exists, Survey Bounds is enabled and locked; when
  it does not, the existing automatic Survey Bounds option remains available.
- Survey CSV metadata now stores the selected measurement system, so metric and
  imperial surveys reopen independently from the current global preference.
- Startup and survey lifecycle logging now records workspace construction,
  language application, new/open/save phases and workspace show steps.

### Fixed / Changed

- Boundaries keeps normal floorplan controls active: zoom, pan and left-click
  selection still work, while right-drag paints or erases the mask instead of
  adding survey points. The OS cursor is only hidden while hovering over the
  actual floor plan, so it remains visible in gray viewport margins.
- Boundaries drawing now uses fixed transparency, a lighter fill, subtle
  feathered edges, zoom-accurate brush preview and native continuous strokes
  with round or square caps for smoother fast paint/erase gestures. Square
  brush drags now render recent mouse points as one joined path, avoiding
  intermediate cap artifacts during small direction corrections, and the active
  drag is redrawn from a per-gesture snapshot so the current square footprint is
  complete before mouse release. Square strokes now use a flat path plus real
  square endpoint stamps and simplify dense slow-move points, preventing leftover
  cap pixels along the stroke. Mask rendering now paints an opaque in-memory
  image through fixed item opacity and explicitly invalidates the viewport when
  transparent mask regions are restored. Active strokes repaint the affected
  viewport synchronously and Boundaries mode uses full viewport updates,
  avoiding overlap darkening, stale paint and full-pixmap rebuilds during drag.
- Boundaries toolbar icons are loaded lazily on first use, keeping them out of
  the startup "Loading components" path.
- Go to Point now zooms in when needed using a configurable Settings value
  from 100% to 200% in 10% steps, then places the selected survey point in the
  upper half of the viewport so the highlight is easier to see while the
  Measurement Points panel is open. This operational setting is available in
  the workspace Settings menu, keeping the start page settings focused on app
  appearance.
- The workspace footer now shows the current Survey Zoom percentage for easier
  operational tuning.
- The start page and workspace Settings popups now use embedded rounded panels
  with a small gap below the Settings button, avoiding native popup corner
  artifacts. Workspace Settings groups general app choices first, then
  workspace-specific options and AP Memory, with centered section headings and
  a subtle panel shadow.
- Help Center, README and architecture notes now document the
  `v0.9.7-beta.1` workflow, including manual Boundaries masks,
  survey-specific units and configurable Go to Point zoom behavior.
- Current survey files now require the full aggregate/raw headers,
  `measurement_system`, an explicit `raw_data_file` metadata entry and a valid
  `.scan` sidecar. AP aliases are read from `ap_groups` instead of duplicate
  legacy metadata.

## v0.9.6-beta.1 - 2026-05-17

### Added

- Optional Survey Bounds / Limite Rilievo control for continuous Live Maps and
  PDF exports, reducing unused edge bubbles around the measured survey area.
- New surveys can start from a generated, pre-scaled A4 blank floor plan with
  active Grid overlay, so test captures no longer require manually creating a
  blank image first.
- New survey creation now asks for metric or imperial units before generating
  the blank-plan scale.
- Grid overlay now labels its current step on the map, such as `1 square = 1 m`
  or `1 square = 3 ft`.

### Fixed / Changed

- Live Coverage and Interference maps smooth scan-confidence opacity instead of
  assigning it by nearest point, reducing polygonal artifacts in continuous
  overlays.
- Continuous-map defaults now use smoothing 5.0 and derive calibrated max
  distance from survey-point spacing when enough points are available.
- Starting a new survey while another survey is open now offers Discard
  Changes, Save or Cancel, and untouched generated blank surveys are discarded
  without forcing a save prompt.
- Blank floor-plan PNGs are materialized next to the CSV on save and cleaned up
  after a real floor plan replaces them.
- Imperial grids prefer a 3 ft step when scale permits, keeping point-placement
  guidance close to the metric 1 m step.
- Grid label sizing was adjusted to avoid right-edge clipping.
- English and Italian UI/Help wording was polished for the 1.0 validation pass.
- Windows `onedir` executable and ZIP package were regenerated for
  `v0.9.6-beta.1`.

## v0.9.5-beta.1 - 2026-05-16

### Added

- README Development Approach note documenting transparent use of AI-assisted
  coding tools while keeping project direction, field testing and validation
  manually driven.
- Connected-client BSSID evidence from scanner backends, persisted in survey
  CSV rows and raw `.scan` samples when available.
- Survey Quality `Client Roaming` diagnostics for points where the survey
  laptop stayed connected to one AP while another AP on the same SSID was
  significantly stronger.

### Fixed / Changed

- Scanner code now normalizes current connection details from both `lswifi` and
  `netsh`, and `netsh` scans can mark the currently connected BSSID just like
  `lswifi` scans.
- Connected-BSSID fields remain optional for older schema-2 survey files.

## v0.9.4-beta.2 - 2026-05-16

### Added

- Help Center navigation now uses expandable section groups with automatically
  generated subsection entries from page headings.

### Fixed / Changed

- Fixed Help Center parent-section selection so clicking a main page such as AP
  Groups keeps that page selected instead of jumping to a child subsection
  after expansion.

## v0.9.4-beta.1 - 2026-05-16

### Added

- Local/zone-only coverage scope for AP groups, persisted through survey
  save/load and AP Memory.
- AP Group Metadata controls for Site-wide, Local Area, Auto Area and optional
  manual Local Radius.
- Survey Quality Local Area evaluation for local-only SSIDs, using AP position
  and scale when available.
- Dominant AP diagnostics and Missing Relevant Networks checks now apply the
  same Local Area scope rules.

### Fixed / Changed

- Fixed Coverage Scope initialization when reopening Local Area metadata with
  automatic area enabled.
- Local-only SSIDs no longer trigger warnings outside their expected area, while
  still warning when missing inside scope.

## v0.9.3-beta.2 - 2026-05-16

### Added

- Survey Quality Extra Details dialogs for AP Memory matches, APs without
  position, AP config warnings, channel changes, Dominant AP findings and
  Scanner Details.
- KPI-driven point-list overlays for low confidence, unstable signal, sparse or
  missing evidence and Points To Review.
- Expanded Survey Quality Help in English and Italian, including dashboard
  status, Survey Scope, KPI point lists, Extra Details, AP-model findings and
  review order.
- Help Center, README and architecture notes now describe KPI-driven point
  lists as the scalable way to inspect large surveys.

### Fixed / Changed

- Survey Quality dialogs now size to whole cards or whole table rows, avoiding
  clipped content, partial cards, scroll slack and phantom blank space.
- AP Memory Review now covers both memory-applied AP groups and manual AP
  groups whose current data differs from saved AP Memory.
- Main Survey Quality dashboard was simplified: the full measurement-point table
  and the global `Show Only Points With Findings` control were removed in favor
  of KPI-specific drill-downs.
- KPI cards now open the most useful diagnostic view for each finding type, and
  `Points To Review` includes points with Dominant AP findings.
- Scanner-detail wording now distinguishes raw `scan rows` from measurement
  points and labels `NETSH` as fallback scanner evidence.
- Survey Quality layout was widened and reorganized around KPI cards, a
  bottom-pinned Survey Scope panel and a scrollable `What To Fix Next` panel.
- Windows `onedir` executable and ZIP package were regenerated for
  `v0.9.3-beta.2`.

## v0.9.3-beta.1 - 2026-05-15

### Added

- Survey Quality diagnostics for fallback `netsh` scanner data.
- Survey Quality diagnostics for channel-sensitive rows missing channel width
  and 6 GHz rows missing frequency data.
- Dedicated `Scanner Details Missing` KPI, recommendation card and detail rows.

### Fixed / Changed

- Help Center, README and architecture notes now document limited scanner
  details as a rescan reason before relying on Interference, 5 GHz
  width-overlap or 6 GHz interpretation.

## v0.9.2-beta.1 - 2026-05-14

### Added

- Metric/imperial measurement-system preference. Survey scale remains stored as
  `px_per_meter`, while calibration input, Live Map Max Distance, AP-position
  tooltips and dominant-AP PDF report distances follow the selected display
  system.
- Expanded Help Center coverage for Survey, Quality, AP Groups, AP Memory, Live
  Maps, PDF Reports, Warnings and Glossary workflows.
- Recommended Workflow help page with visual step cards and AP Memory context.
- Windows release artifacts built as a PyInstaller `onedir` executable plus ZIP
  package.

### Fixed / Changed

- Changing measurement system after scale calibration prompts the user and
  clears the current survey scale so it can be calibrated again.
- Main toolbar now places Survey Quality before AP Groups to match the
  recommended validation flow.
- Controls Help now documents left click, left-drag and Ctrl/Shift wheel
  modifiers as implemented.
- Help Center visual layout was normalized for Qt rendering, including card
  spacing, callout widths, tables and scanner backend labels.
- App icon PNG/ICO assets now preserve transparent rounded corners for Windows
  executable embedding.

## v0.9.1-beta.1 - 2026-05-14

### Added

- Persistent AP Memory for AP aliases, roles, metadata, analysis-channel
  overrides and compatible floor-plan positions.
- Automatic AP Memory application after normal AP grouping when known BSSIDs are
  seen again.
- "From Memory" review state in AP Group Manager and Survey Quality.
- Memory-update detection for manual AP groups whose local AP data differs from
  the saved AP Memory record.
- Workspace footer status for AP Memory state and memory file location.
- Settings actions to open the AP Memory folder or clear AP Memory.
- Custom application/window icon and Windows executable icon.

### Fixed / Changed

- AP Group Manager toolbar now groups memory actions under a Memory menu and
  alias actions under an Alias menu.
- Start screen shows the application icon next to the product name.
- AP Group save seeds or updates AP Memory even when survey metadata was
  otherwise unchanged.
- Clear-memory confirmation uses themed Qt dialog styling in both the start
  screen and main workspace.

## v0.9.0-beta.1 - 2026-05-13

### Added

- Initial public beta for the completed Qt workflow.
- PySide6 desktop UI with startup window and main workspace.
- Current survey CSV format with linked `.scan` raw-data sidecar.
- Repeated Wi-Fi scan capture with `lswifi` primary support and `netsh`
  fallback.
- Relevant SSID workflow.
- AP Group Manager with BSSID grouping, aliases, roles, metadata, expected
  bands/channels, analysis channel overrides and physical AP positions.
- Survey Quality Dashboard with KPI cards, point-review diagnostics, AP
  setup/model diagnostics and "what to fix next" guidance.
- Live Map tab with Coverage, Interference, AP Channels and Dominant AP views.
- Live PDF export from the current map view, including Interference and
  Dominant AP issue-report pages where applicable.
- Shared Qt theme styling, scrollbar styling, stronger table selection and
  polished Survey/Live Map navigation tabs.
- Expanded EN/IT Help Center for the current workflow.
- Public product version metadata exposed through Qt and release assets.

### Fixed / Changed

- Legacy Tkinter UI is retired from the active workflow.
- Old generated PNG/CSV map export path is retired in favor of live PDF export.
- Public release assets use PyInstaller `onedir` ZIP packaging rather than
  `onefile`.
