# Changelog

This file tracks user-facing changes between official release builds.

The project uses semantic public release tags. `V2` is the internal survey and
architecture generation, while releases use tags such as `v0.9.0-beta.1`,
`v0.9.0-beta.2`, and later `v1.0.0`.

## Unreleased

- Targeted Help Center review/polish, office validation fixes, and small
  release-readiness adjustments.
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
