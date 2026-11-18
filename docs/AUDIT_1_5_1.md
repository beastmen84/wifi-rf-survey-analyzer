# 1.5.1 Release Verification

Date: 2026-11-18. Platform: Windows x64. Python: 3.15.2.

## Scope

This patch release includes retained layer graphics and bounded validation and
geometry caches, persistent confirmed-selection highlights when entering other
controls, selection transfer across native dialog focus changes, and Ctrl/Shift
multi-selection gestures. Existing drawing dimensions, document-wide validation,
layer restrictions and undo/redo semantics are preserved. Survey CSV/raw-sidecar
schema remains 2 and dependency pins are unchanged.

## Verification

The native Windows Qt suite completed **2,888 tests and 479 subtests** in
1,953.24 seconds: **2,887 passed and one Esc-shortcut case failed**, with no
errors or skips. An isolated native rerun of the entire erasing file then passed
**all 43 tests in 24.72 seconds**, including that case. The same case also passed
individually with the offscreen renderer in 5.52 seconds. All 2,888 distinct cases
are therefore covered by passing results, but the original full run is not
represented as an uninterrupted all-pass run. The Esc failure did not reproduce
in isolation and is consistent with native window-focus sensitivity; its exact
trigger was not established. No runtime code was changed to suppress it.

All 31 locked distributions match the installed environment. `pip check`,
Ruff E9/F63/F7/F82, Python compilation and Git whitespace checks pass.
Dependency pins are unchanged.

The native run also emitted the previously observed Windows Qt/COM diagnostic
`0x8001010d` while showing a test window. The process continued; the final pytest
result and JUnit failures/errors, rather than that diagnostic alone, determine
the regression result.

Fresh source/native Qt export probes passed for imported PNG, imported PDF and
Draw Plan, using synthetic data with four points and 60 raw samples:

- A3 landscape JPEG at 9,921 by 7,016 pixels / 600 DPI, including legend JPEGs.
- Two-page PDF print output in each of the three cases, including legends.
- Six HTML maps covering signal/interference/channel/dominant and three
  analysis HTML reports.
- Imported backgrounds retain their original SHA-256 hashes.

These file-generation probes execute the source application, not the EXE.

## Test harness memory

The first suite execution was interrupted by a host IDE crash and is not counted
as a completed test run. The JVM dump recorded only 284 MiB of free physical
memory on a 32 GiB machine and a failed native allocation; PyCharm's Java heap
was below its configured 8 GiB maximum. The exact historical memory consumption
of the test process was not recorded, so the dump alone does not attribute all
system memory use to one process.

A source probe reproduced accumulated Qt widgets after the existing test
teardown: `deleteLater()` plus `processEvents()` did not flush deferred deletes
without the normal `app.exec()` event loop. The shared pytest teardown now
collects Python garbage and explicitly delivers Qt DeferredDelete events between
tests. This is test infrastructure; the frozen application's event loop and
runtime behavior are unchanged. Local IDE exclusions also keep generated builds,
packages and caches outside project indexing; these settings are not distributed.

The final suite uses process/system memory telemetry and a conservative stop
gate rather than proceeding into another system-wide memory shortage.
All 2,888 cases completed without activating the stop gate. The highest private
memory sampled after test teardown was **3.08 GiB**; the Windows peak-commit
counter captured near the end was 3.19 GiB. Periodic samples retained at least
11.25 GiB of available physical memory and 7.49 GiB of available commit capacity.

## Frozen Windows package

PyInstaller 6.22.3 built the Windows x64 onedir package with CPython 3.15.2.
All **169 bundled application modules** and `main.py` match normalized compiled
code from the release workspace. File/ProductVersion resources are `1.5.1`, with
numeric version `1.5.1.0`. Python 3.15, QtOpenGL/QtOpenGLWidgets, QtPdf,
QtPrintSupport, icons, legal notices and dependency files are included and checked.
Application test modules are excluded.

The existing optional `scipy.special._cdflib` hidden-import warning remains.
Successful source rendering/export probes do not establish execution of every
SciPy path in the frozen application.

EXE SHA-256:
`da55a90901d37344c79ceb3702139e30d1342f0730a50f72440b5c3bf23928e1`.

The actual EXE was launched with isolated preferences and AP Memory. Native
accessibility and visual inspection confirmed the 1.5.1 title/footer and Ready
state. The synthetic Draw Plan opened with four points and 60 raw samples, and
displayed wall materials, text and symbols. Print Plan rendered its clean preview
with scale and legend pagination; Save as JPEG displayed its clean page preview
and expected A4 landscape 300-DPI dimensions. The frozen log has no error or
traceback. This is a focused smoke test, not a comprehensive frozen editing,
multi-selection or file-generation campaign.

## Distribution

The portable Windows package is `WiFiRFSurveyAnalyzer-v1.5.1-win64.zip` with a
sibling SHA-256 file and a bundled `release-manifest.json`. Distribute the whole
application folder. Previous versioned archives and the original `test_data/`
directory are preserved and excluded from the new package.

Extract the complete folder and retain `_internal` beside the EXE. ZIP entries
are fully decompressed and hash-compared with the audited bundle before delivery.

## Known limits

The documented layer performance measurements belong to the earlier source
benchmark in `LAYER_PERFORMANCE_2026_11_12.md`; this release does not claim a new
timing comparison. Large scene preparation can still be CPU-expensive. Hardware
OpenGL depends on the available driver and has a software fallback. Physical
grid enclosures do not redefine editable reference rooms. Wall materials remain
descriptive and do not imply RF attenuation.

No RF scans, receiver calibration or physical printer validation were performed.
Local packaging does not publish a GitHub release.
