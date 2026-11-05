# Changelog

This file tracks user-facing changes between official release builds.

The project uses semantic public release tags such as `v0.9.0-beta.1`,
`v0.9.0-beta.2`, and `v1.0.0`.

## Unreleased

- Documented the proposed marker/door/window annotation workflow and deferred
  physical wall thickness/material modeling pending internal-room geometry and
  shared-wall constraint design. These are roadmap notes, not implemented tools.
- Same-color straight strokes now unite across partial overlaps and duplicate
  ink, preventing artificial endpoints from splitting selection and erasure.
  Real T/cross/curve contacts, corners, different colors and actual gaps remain
  separate. The same normalization applies to drawing, transforms, reopen and
  saving, with shared undo/redo and retained source ownership. Updated Help in
  EN/IT/FR/ES. Balanced the Grid context menu's text padding in all four themes.
- Added a per-survey grid square size to New Survey and a right-click Grid action
  for later changes. Defaults are 1 m / 3 ft; inputs use tenths of a meter or
  whole feet, with minimums of 0.1 m / 1 ft. The saved physical interval controls
  both rendered grid lines and snapping; legacy surveys keep automatic spacing.
- Select now picks nearby strokes first with a screen-space margin, or selects
  the complete boundary when clicking inside a closed region. The measurement
  panel shows the exact area in m²/ft², accounting for nested holes and circular
  edges while excluding dangling strokes. Open-space clicks preserve selection.
  Single segments show length, circles radius, and arcs length/radius/chord/
  sagitta. Selection commands appear vertically, one per line; perimeter M/R/Del
  and undo/redo use the existing shared history. Updated EN/IT/FR/ES Help.
- Line right-drag now supports any direction, including diagonals, with a fixed
  starting point and a freely moving endpoint. Corner/edge/grid snapping, Alt,
  live length, editable intersections, closed areas and undo/redo remain active.
- Grid snapping applies to the dragged radius/chord endpoints and the arc's
  bending stage. The arc passes through the selected visible grid intersection
  while keeping its chord fixed; real corners take priority. Orange guides show
  grid targets even on the provisional chord. Alt and the grid toggle immediately
  release or restore snapping. Numeric dimension steps stay at 0.01 m/ft.
- Fixed circle/arc numeric previews sticking to the grid during slow cursor
  movement: each update translates the original placement geometry instead of
  feeding the previous snapped result into the next movement. Quarter-turn and
  held rotations rebase placement without changing dimensions or cursor grip.
- Radius, chord and sagitta drags adjust continuously with grid snapping off or
  Alt held. With snapping enabled, grid intersections guide sizing and placement.
  Numeric dimension
  arrows adjust by 0.01 m/ft. During arc bending, nearby real corners constrain
  the arc to pass through the target while keeping the chord fixed. Orange guides
  show the target and Alt temporarily bypasses it. Updated EN/IT/FR/ES Help and
  contextual grid tooltips.
- New Survey starts blank sheets at 35 × 25 m or 115 × 81 ft. Switching units
  uses the matching preset until dimensions are customized, then preserves the
  physical size through conversion. Generated pixels and calibration match the
  chosen dimensions; existing surveys retain their saved geometry.
- Added Circle and Circular arc to Design Mode. Circles use radius drag or a
  numeric radius; arcs use chord drag followed by perpendicular sagitta movement
  and a confirming right click, or exact chord/sagitta/side entry. Last dimensions
  are remembered during the survey. Numeric arc previews support R tap/hold, and
  selection/double-click or the pencil action reopens their dimension editor.
  Intersections create editable curved fragments; obsolete cuts rejoin without
  flattening curves. Snapping, erasing, mixed selection, M/R/Del, shared undo/redo,
  closed-area grid fading and Boundaries Fill/Auto Fill support curved geometry.
  Tangent contacts are treated as single analytic junctions at every orientation.
  Optional parametric curve metadata preserves editable radius/chord/sagitta on
  reopen and feeds the same current geometry to PNG, Live Map and HTML exports.
  A single circle has no rotation gesture or rotation hint; group rotations move
  its center with the group without assigning an orientation to the circle.
- Fixed the drawing measurements panel at the top right of the viewport, aligned
  with the scale legend. It stays anchored during pointer movement and window
  resizing, with bounded wrapping. Updated EN/IT/FR/ES controls and Help.
- Fixed grid snapping for rotated shapes: every real vertex can anchor the shape,
  rather than only the first segment's start. Numeric previews, either line
  endpoint and moving selections use the nearest valid vertex/grid correction
  while preserving dimensions, angle and sheet bounds. Orange guides identify
  the actual snapped vertex, including text previews.
- AP Group status now shows either M or the physical-approval circle, with M
  taking priority. Clicking M opens its Memory actions and cannot approve the
  group. Memory-update candidates can explicitly keep their current data before
  proceeding to physical confirmation.
- Added Fill and Auto Fill to Boundaries on generated blank sheets. Fill uses
  a right click inside one closed drawn face; Auto Fill adds all closed faces to
  the existing analysis mask. Nested rooms remain distinct for Fill. Imported
  plans retain their existing brush tools without these extra controls.
- Added editable multiline Text in Design Mode, with font, size, bold/italic,
  alignment, fill/outline colors, outline width and an automatically fitted
  preview. After OK, right-click places the cursor-following label. R tap/hold,
  snapping, mixed selection and M movement work for labels. Right-double-click
  or Edit selected text reopens the editor. Del deletes selected labels and
  segments in one shared undoable operation. Glyph outlines preserve appearance
  in PNG, Live Map and HTML exports and remain editable after reopen.
- Updated English, Italian, French and Spanish Help and tooltips for the new
  drawing tools, deletion shortcut and memory-first confirmation flow.
- Replaced the physical AP confirmation command inside Alias with an accessible
  first-column circle in AP Group Manager. Click or press Space to toggle approval;
  green with a check means confirmed. Real changes to BSSIDs, alias, role, position
  or metadata clear approval; unchanged values keep it. Save persists the state.
- AP Memory now remembers physical approval for an exact BSSID membership.
  Changed/subset groups and explicit local revocations cannot inherit approval;
  historical MAC unions never count as a confirmed device. Older memory files
  remain readable and need an initial explicit approval.
- Analysis asks once per unconfirmed group transmitting a relevant SSID, with
  evidence from its real BSSIDs. Unrelated networks remain separate RF neighbors
  without requiring identity confirmation; incomplete radio evidence still blocks
  precise channel proposals. Updated all four UI/Help/report languages.
- Added two R gestures: tap/release for 90 degrees, or hold R and orbit the fixed
  orange center in 5-degree steps. The readout shows equivalent positive/negative
  angles. Releasing R applies the gesture; Esc cancels it. Numeric Line/Rectangle
  previews and selected/moving groups keep their center frozen while rotating;
  cursor following resumes without a position jump. Auto-repeat and the center
  dead zone do not introduce extra turns; clicks/panning/zoom are blocked during
  the gesture. Invalid out-of-sheet orientations appear red and are rejected.
- Extended editable geometry to oblique strokes: real finite intersections,
  collinear rejoining, point/area erasing, snapping to real vertices/finite
  projections and closed-face detection. Orthogonal data keeps its optimized
  geometry path. Rotation preserves dimensions and remains one undo action;
  current PNG/Live/HTML backgrounds include committed oblique geometry. Updated
  contextual notes and Help in EN/IT/FR/ES; dependencies/schema/version unchanged.
- Rejoin contiguous, collinear fragments of the same color when a move, rotation
  or erase removes their junction. Real T/cross junctions, corners, erased gaps,
  color changes and differently colored overlap strokes retain their cuts.
  Old saved obsolete cuts normalize on read and persist on save. Undo/redo
  restores the corresponding cuts; snapping and closed areas follow the current
  geometry. A joined segment containing stationary geometry is not automatically
  selected by a transform. EN/IT/FR/ES Help describes the behavior.
- Split actual editable strokes at finite cross/T intersections and collinear
  overlap endpoints before uniting same-color straight ink. Colors and the
  earliest stroke direction are preserved; the eraser can remove a single
  fragment between real cuts. Existing
  drawings receive cuts on read, persisted on save with transaction rollback.
- Added Line with right-drag measurement and a single-length m/ft
  dialog for cursor-following placement. R rotates Line and Rectangle placement
  previews by 90 degrees without changing dimensions; invalid orientations are
  rejected without clipping. Esc cancels provisional edits.
- Added Select with single-fragment click or touched-fragment marquee. R rotates
  the selection about its bounding-box center; M starts a rigid moving preview,
  right-click places it and Esc cancels. R also rotates during movement. The
  selection box snaps to unselected geometry/grid, with Alt bypass. Confirmed
  transforms split new intersections, refresh closed areas and share undo/redo.
  Keyboard commands respect dialogs/text fields. The two-row tool palette and
  EN/IT/FR/ES Help cover the expanded editor; PNG/Live/HTML use the committed model.
- Added blank-sheet width/height to New Survey, with m/ft conversion and bounded
  raster allocation. Custom dimensions, a common physical scale and the actual
  PNG size survive save/reopen; importing a floor plan replaces the blank sheet.
- Added a bottom-left Design Mode toolbar exclusively for generated blank sheets,
  including reopened surveys. Rectangle drawing, stroke color and undo/redo are
  available, along with optional grid snapping and automatic shape snapping.
  Independent-segment erasing is also available.
  Opening Design Mode suspends right-click point capture; it coordinates with Boundaries
  and the points panel, closes with Escape and updates across all themes/languages.
- Updated EN/IT/FR/ES labels and Help to describe configurable sheets and the
  toolbar's current capabilities, removing the fixed A4 description.
- Aligned the blank-sheet section with the rest of New Survey and replaced native
  numeric spin arrows with themed SVG chevrons and compact hover/press controls.
  The Design Mode palette fits its wrapped note at the current font/scale.
- Added right-drag rectangles with live m/ft dimensions and numeric placement
  after a simple right-click. Left-drag pans; Esc cancels a provisional shape
  before exiting Design Mode. Shapes stay within the sheet and do not record RF
  points. Save/reopen retains four independent editable segments per rectangle;
  undo/redo is available for placements, with complete save-failure rollback.
- Generated PNGs, Live Map and both HTML exports show the current drawing,
  including unsaved edits and undo. Exact vector fingerprints prevent stale
  cached backgrounds after small changes. Drawing geometry has no RF attenuation
  effect; boundaries and data-collection rules remain separate.
- Added nearby corner/edge snapping with deterministic target priority and
  zoom-independent screen tolerance. Grid snapping uses the displayed m/ft grid
  interval. Numeric rectangles translate without resizing; all results stay
  inside the sheet. Orange markers, alignment guides and dimension labels show
  active targets. Alt temporarily bypasses all snapping. Preview updates follow
  grid toggles; turning the grid off also turns grid snapping off.
- Added the Design Mode eraser: right-click deletes one highlighted segment;
  right-drag previews a red area and deletes whole segments it touches on release.
  Red highlights and a localized count identify the affected sides. Esc cancels;
  left-drag pans. Deletions share the drawing undo/redo history and update snap
  targets, saved PNGs, Live Map and HTML exports, including an entirely cleared
  sheet. Empty selections leave the document/history unchanged. Help is aligned
  in English, Italian, French and Spanish. Undo/redo use explicit themed curved
  arrows so their icons remain visible across Windows styles.
- Added closed-perimeter grid fading from the current segment graph, including
  concave, adjacent, nested and overlapping shapes. T/cross intersections and
  collinear overlaps are recognized; open gaps stay open. Erasing an outer side
  restores the normal grid in the opened area; undo/redo and reopen update it.
  The effect is derived in the survey view and changes neither RF data nor PNG/
  Live/HTML backgrounds. Dense drawings exceeding the topology limit retain the
  normal grid and show a status message.
- Extended drag snapping to the moving sides of the entire draft rectangle,
  allowing height/width alignment beyond an existing segment's endpoint when
  their spans overlap. The initial corner remains fixed. Orange guides and an
  Alignment label identify the target; Alt suspends it. Numeric placement keeps
  its fixed dimensions. EN/IT/FR/ES instructions and Help describe both additions.

## v1.2.0 - 2026-11-04

- Relevant-network selection now happens before the capture review, including
  the first point. Feedback uses the chosen scope immediately and Save confirms
  the reviewed measurement in one step. Missing/new-network choices also precede
  review; cancellation/retry continue to preserve existing points.
- Removed the redundant review disclosure. Scope is visible in the coverage card,
  useful notes are inline and the dialog fits its content to avoid tiny scroll
  ranges. Scrolling remains available for genuinely long content/small screens.
- Reduced preparation/scanning dialog height and made review cards use two
  columns: primary status on the left, smaller wrapped details on the right.
- Bounded Survey hover summaries to four network names plus a remaining count.
  Survey popups appear immediately over the painted point and its black outline,
  remain stationary without expiring and close immediately on exit. A dedicated
  input-transparent popup avoids competing Qt tooltip delays and slow-edge
  flicker. Overlapping points retain the current popup until its outline is left;
  AP hover retains priority where an AP marker is under the pointer.
- Added guided point capture: a short preparation, real five-attempt progress,
  cooperative discard, and an explicit Save / Repeat / Discard review. Results
  remain provisional; failed/discarded rescans preserve previous measurements.
- Separated acquisition reliability, per-BSSID signal stability and observed
  coverage in the review, saved-point details/tooltips and offline HTML reports.
  The point table now labels acquisition reliability explicitly. Missing history
  and insufficient samples stay uncertain; weak Wi-Fi can be measured reliably.
  Expanded Help and UI wording in English, Italian, French and Spanish.
- New Survey now selects a fixed Wi-Fi adapter alongside measurement units,
  showing its name/status with asynchronous discovery and a refresh action.
  The receiver ID/name is saved in survey metadata, restored on reopening and
  shown in the workspace footer. New points and rescans use only that receiver;
  missing hardware or native scan failures never switch receivers or fall back
  to netsh. Point persistence also rejects mismatched raw/capture identities.
  Older surveys ask for a receiver before their first new measurement, without
  relabelling previous data. Help and all four UI languages describe this flow.
- Squared both upper corners of the central Live Map tab, keeping its uniform
  selected highlight and the rounded outer corners of the workspace tab bar.

## v1.1.0 - 2026-11-04

### Added

- Added shared offline HTML report styling with summary cards, prioritized
  findings, expandable evidence, linked Live Map points and browser printing
  that includes collapsed measurements and restores the reading state afterward.
- Added HTML exports for all four Live Map types using the screen renderer,
  current filters, legends and boundary masks. Important quality/unknown-risk
  warnings remain visible without opening the technical details.
- Added a final Analysis and recommendations tab, with background local analysis
  of the whole survey and configurable coverage/evidence/channel objectives.
- Added coordinated channel-plan proposals, observed overlap and width reviews,
  weak/missing network findings, AP-position/dominance checks, controlled power
  trial guidance and connected-client roaming observations. Precise proposals
  require sufficient stable evidence and explicit 5/6 GHz candidate channels.
- Findings show measured evidence, confidence, assumptions and point links.
  Data-quality and metadata inconsistencies are presented before RF actions.
- Added complete HTML analysis reports with a numbered floor-plan overview,
  joint-plan summary and measured evidence. Reports use the same analysis
  snapshot and reject stale data. Browser printing can save the complete report as PDF.
- Added English, Italian, French and Spanish UI/report/Help wording and automated
  rule, worker, export, pagination and translation regression checks.

### Fixed / Changed

- Live Map uses **Export Map**, and Analysis uses **Export report**, with HTML as their workspace
  export format. Images/styles/controls are embedded in one portable file;
  no server or network access is required. Existing PDF generation helpers are
  retained internally for compatibility; workspace printing uses the browser.
- Simplified the Analysis page: coverage target and update/export actions stay
  visible, while confidence, minimum points and channel candidates move into
  expandable settings. Active values and missing candidate warnings remain
  visible. Updated report Help and EN/IT/FR/ES wording.
- The selected central Live Map tab now has a uniform background and underline;
  edge-tab gradients remain confined to the first and last workspace tabs.
- Migrated the development environment to CPython 3.15.2 with PySide6 6.12.0,
  NumPy 2.5.4, SciPy 1.18.1, pandas 3.1.0, Matplotlib 3.11.2 and lswifi 0.5.0.
  Updated pytest/PyInstaller and the complete pinned dependency snapshot;
  refreshed installation instructions and third-party version notices.
- Extracted Local Area relevance rules so Survey Quality and recommendation
  analysis apply the same coverage scope.
- Replaced the original advisor-overlay draft with the implemented final-tab
  workflow in `docs/AI_ADVISOR_DESIGN.md`. No AI or remote service is involved.
- Native acquisition now waits for scan-complete/failure notifications and
  rejects cached/repeated BSS observations. Receiver identity, exact timestamps
  and scan outcomes survive saving; each capture uses one receiver and a fixed
  five-attempt denominator. Mixed-receiver surveys block precise advice.
- Preserved hidden SSIDs, whitespace, placeholder-like names and original SSID
  bytes, including embedded NUL. Partial raw evidence no longer hides known
  aggregate signal instability, and incomplete evidence blocks precise advice.
- Validated finite measurement inputs and radio consistency. Ambiguous bands,
  missing HT40 direction, discontiguous 80+80 and unsupported 320 MHz geometry
  remain unknown instead of producing false zero-overlap conclusions.
- Shared conservative scan-confidence rules across maps, quality and reports.
  Old surveys with unknown freshness remain readable without receiving implicit
  full confidence. Reports identify direct driver RSSI versus estimated dBm.
- Separated automatic AP-group proposals from confirmed physical identity.
  Added an explicit physical-group confirmation action; renaming alone does not
  suppress neighbors. Power trials require distinct locations at least 2 m
  apart and alternative coverage at every measured location served by the AP.
- Retained verified zero-BSS scans as measurement points, with an empty outcome
  and no fabricated signal. Failed/unverified captures cannot claim absence;
  rescans preserve the original point until the replacement validates.
- Added regression coverage for all eleven precision-audit findings and updated
  the audit with before/after hardware evidence and remaining validation limits.

### Known Limits

- Controlled moving-position/AP-change field tests, absolute-RSSI reference
  calibration and 6 GHz/6E/7 hardware validation remain outstanding. Unsupported
  RF geometry is gated conservatively; see `docs/AUDIT_1_1_0.md` for evidence.
- The previously observed intermittent native Qt/COM `0x8001010d` diagnostic
  remains unexplained. It did not appear in the final native correction run;
  that result does not establish a fix.

### Maintenance Included Since v1.0.0

- Updated Pillow to 13.0.0 and setuptools to 84.2.1 for security fixes,
  included in the pinned Python 3.15 dependency stack above.
- Survey saves now stage CSV, raw scan data and generated images, restore the
  previous file set on write errors, and recover interrupted saves on reopening.
  Preferences and AP Memory also use atomic single-file replacement.
- Preserved case-sensitive SSID identity across relevance, quality, live maps
  and PDF reports, including live-preview cache keys.
- Fixed `netsh` fallback parsing for English, Italian, French and Spanish,
  explicit 6 GHz bands and multiple adapter connection states. Added bounded
  command waits and distinct translated failure/timeout messages.
- Clear the previous floor plan when the newly opened survey's plan is missing.
- Discard live-render results from previous sessions/options, snapshot render
  inputs and wait for thread completion before enabling another render or exit.
- Preserve multiline CSV fields whose continuation lines begin with `#`.
- Size AP coverage controls using polished widget/font metrics.

## v1.0.0 - 2026-05-18

Stable public source release for the current Qt workflow. Windows executable
and ZIP artifacts are generated in a separate packaging step from this source
state.

### Added

- Added the MPL 2.0 project `LICENSE`, a `THIRD_PARTY_LICENSES` dependency
  notice file, README license/disclaimer sections, and an in-app Help legal
  section for public release preparation.
- Added French and Spanish localization for the UI, Help Center, tooltips and
  report wording, with automated checks for translation parity, placeholders,
  critical technical terms, compact label length and PDF problem-page rendering.
- Added pinned runtime dependencies, a `requirements-dev.txt` test/build
  environment file, and a `requirements-lock.txt` for reproducible release
  validation.
- Added a README screenshot plus public-download, Windows-build and
  authorized-use notes near the top of the project page.

### Fixed / Changed

- Packaged Windows builds are configured to include the release legal and
  project documentation files beside the application bundle.
- PDF floor-plan rasterization now uses PySide6 QtPdf instead of PyMuPDF,
  removing the AGPL/commercial PyMuPDF dependency from runtime, test and
  packaged release requirements.
- Public-facing project naming now consistently uses
  "Wi-Fi RF Survey Analyzer"; Windows build outputs use the
  `WiFiRFSurveyAnalyzer` artifact name while historical beta ZIP names remain
  documented as historical artifacts.

## v0.9.8-beta.2 - 2026-05-18

### Added

### Fixed / Changed

- Live PDF map pages now trim excessive uniform floorplan background below the
  last visible content while preserving a small bottom margin and any points/AP
  markers that fall in that area. The crop is based on the repeated background
  color at the bottom of the floorplan, not on assuming a white page.
- AP Channels and Dominant AP PDF map-page info bands now grow when the
  discrete legend has many entries, reducing the chance that useful legend
  items are collapsed into a `+N` overflow marker.

## v0.9.8-beta.1 - 2026-05-18

### Added

- Boundaries toolbar now includes `+`/`-` brush-size controls with 10 px steps
  and a 20-120 px range, making large floorplan masks faster to draw while
  keeping fine control available.
- Signal Coverage point tooltips now expose point-local evidence: selected
  aggregation, samples, scan confidence, strongest reference AP and channel
  context, replacing the previous global source-row count.
- AP Interference point tooltips now show confidence, serving/interferer
  signal, channel band context, overlap percentage and meaningful contributor
  or ignored-AP counts when available.
- AP Channels point tooltips now use the same readable evidence format as the
  other live maps, including signal, samples, confidence and channel band
  context.
- Dominant AP point tooltips now use the same readable evidence format as the
  other live maps, including signal, samples, confidence, second-AP context,
  roaming overlap and AP-position rows.
- AP Channels and Dominant AP legend point double-click now uses the configured
  focus zoom and centers the selected live-map point in the viewport.

### Fixed / Changed

- Help Center navigation now visually separates main pages from subsection
  anchors, making the content list easier to scan on dense Help pages.
- Help and user-facing validation messages no longer expose the old internal
  migration label; architecture notes were renamed to
  `docs/ARCHITECTURE_NOTES.md`.
- Boundaries square brush strokes now use an axis-aligned square sweep instead
  of a thick Qt path, improving office-style straight edges and corners while
  avoiding warped joins during slow direction corrections.
- Shared map tooltip styling was refined for faster scanning, with clearer
  title spacing, aligned label/value rows and stacked formatting for long
  diagnostic values.
- Survey point and Wi-Fi AP floorplan tooltips are now aligned with live map
  tooltip styling and terminology, including translated labels and clearer
  signal, scope, role and observed AP evidence rows.
- The live-map footer now reports `Live Map Zoom` while the Live tab is active,
  keeping it distinct from Survey Zoom.
- AP Group refresh now auto-heals memory-applied `#2`/`#3` fragments when the
  survey rows show they belong to the same automatic AP group, preventing AP
  Memory from duplicating metadata across split physical APs.
- Open Survey now starts from the saved full CSV path when it still exists, so
  the last survey is preselected instead of only opening the parent directory.
- Automated UI tests now isolate application settings, preventing test runs
  from overwriting the real last-survey preference.

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
