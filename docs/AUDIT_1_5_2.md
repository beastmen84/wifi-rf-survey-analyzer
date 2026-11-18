# 1.5.2 Release Verification

18 November 2026. Windows x64, CPython 3.15.2 and PyInstaller 6.22.3.

## Changes

Move selection accepts hidden, unlocked layers. A hidden destination keeps its
visibility and the source remains active. The transfer is a single undoable
operation. Startup and drawing buttons show a continuous focus outline, and
confirming a selection move at its original position preserves undo history.
Survey and dependency formats are unchanged.

## Source evidence

The release reuses the completed tests for these changes. The version bump,
release documents and packaging inputs were prepared afterward as requested.

- 2,889 tests and 479 subtests passed in two offscreen Qt processes. The total
  wall time was 194.50 seconds. Peak sampled Python private memory was 4.36 GiB.
- 98 focused tests passed with native Windows Qt in 42.93 seconds.
- The focus outline passed 96 render checks across four themes and display
  scales of 100%, 125%, 150% and 200%.

## Windows package

The portable Windows x64 ZIP contains `WiFiRFSurveyAnalyzer.exe`, its `_internal`
runtime, legal notices and `release-manifest.json`. The manifest records the
release commit, executable SHA-256 and package checks. The checks cover Windows
version resources, bundled code and assets, and the integrity of every ZIP entry.
Runtime verification comes from the source checks listed above.

PyInstaller reported the existing optional `scipy.special._cdflib` hidden-import
warning. The build completed successfully.

Extract the whole folder and keep `_internal` beside the EXE. Use the sibling
`.sha256` file to verify the archive.
