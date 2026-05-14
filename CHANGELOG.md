# Changelog

This file tracks user-facing changes between official release builds.

The project uses semantic public release tags. `V2` is the internal survey and
architecture generation, while releases use tags such as `v0.9.0-beta.1`,
`v0.9.0-beta.2`, and later `v1.0.0`.

## Unreleased

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
- Help Center non-control sections now use the same visual/content pattern and
  document the current Survey, Quality, AP Group, AP Memory, Live Map, PDF,
  warning, and glossary workflows from the Qt implementation.
- Survey Help now uses compact summary cards for survey screen boxes and
  clearer sidecar/relevant-SSID/point-placement guidance.
- Survey Quality Help now reads as a dashboard guide with two decision layers,
  grouped KPI cards, prioritized fix gates, and scalable detail-dialog guidance.
- Help Center tables and callouts now normalize to full content width in the Qt
  renderer, callout accent columns keep a fixed Qt-compatible width, and scanner
  backend labels are plain table text instead of badges.
- Help Center now documents AP Memory review states, confirm/update workflows,
  settings access, and AP Group Manager save behavior.
- Possible future AP Memory management view only if larger repeat-survey usage
  shows a real need for explicit cleanup or conflict review.

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
