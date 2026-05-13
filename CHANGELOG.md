# Changelog

This file tracks user-facing changes between official release builds.

The project uses semantic public release tags. `V2` is the internal survey and
architecture generation, while releases use tags such as `v0.9.0-beta.1`,
`v0.9.0-beta.2`, and later `v1.0.0`.

## Unreleased

- Planned `v0.9.0-beta.N` line: targeted Help Center review/polish, office
  validation fixes, and small release-readiness adjustments.
- Planned `v0.9.1-beta.1` candidate: AP Profile Library for exporting/importing
  AP Group metadata across surveys.

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
