# 1.3.0 Release Verification

Date: 2026-11-08. Platform: Windows x64. Python: 3.15.2.

## Scope

The release includes Draw Plan / Load Plan setup, metric/imperial blank-sheet and
grid dimensions, straight/curved structure, snapping, shared selection, layers,
physical thickness and per-side materials, annotation tools, AP-symbol binding,
numbered legends, fixed-origin resizing, clean print/JPEG and consistent visible
layer rendering in Live Map and HTML reports. Materials describe the plan; they
do not assign RF attenuation. The survey CSV/raw sidecar schema remains 2.
Existing unthickened vector documents remain readable; physical wall documents
use drawing/curve/layer format 2.

Pandas is updated from 3.1.0 to 3.1.1; the remaining pinned dependencies are
retained. The [upstream patch notes](https://pandas.pydata.org/docs/whatsnew/v3.1.1.html)
include corrections to CSV readers/writers and Copy-on-Write behavior. Windows
EXE version resources now follow the application version. AP Memory's stable
SHA1 identity explicitly uses `usedforsecurity=False`; existing IDs are unchanged.

## Verification

| Check | Result |
| --- | --- |
| Final full suite, native Windows Qt, pandas 3.1.1 | 2,281 tests and 479 subtests passed, 266.46 s |
| Scene lifetime regression | Failed before correction; 67 related tests passed afterward |
| Dependency consistency and locked environment | `pip check` passed; 31 pinned distributions match |
| Available stable updates | No further outdated installed packages after the pandas patch |
| Known dependency advisories, pip-audit | No known vulnerabilities in the 31 locked distributions |
| Static security review, Bandit | No high/medium findings; seven low findings reviewed |
| Ruff E9/F63/F7/F82, targeted F checks, compileall | Passed |
| Native source UI campaigns | Plan/objects 24, materials 48, resize 48, shared selection 24 cases passed |
| Existing test survey | Open/save/reopen on a private copy preserves vectors/layers; originals unchanged |
| Source export smoke | Analysis HTML, four Live Map types, print PDF and A3 600-DPI JPEG passed |

The complete suite covers drawing topology and curves, shared walls/materials,
room areas, annotations, AP binding, layer isolation, snapping, history, failed
transactions, survey compatibility, RF evidence/quality, deterministic analysis,
HTML escaping and localization. The UI campaigns span four languages, two themes,
100/125/175% scales, and metric/imperial units where applicable. They are separate
campaigns with overlapping configurations, rather than 144 unique display setups.

The extra existing-plan-to-New-Survey probe found a real scene-lifetime error:
`zoomChanged` could traverse symbol graphics destroyed by scene replacement before
the controller adopted its new pixmap. The callback now checks scene identity
before visiting items. A regression captures the Qt exception callback, exercises
active and passive layers, then confirms that a new survey's symbols still update.

Low static-security findings are reviewed band-number literals and controlled
subprocess use. The stable AP-memory digest is not an authentication mechanism;
declaring its non-security purpose preserves all existing record IDs.

One real backend check observed 14 networks on 2.4/5 GHz, with 49 raw samples from
the native lswifi path and 14 snapshot samples from netsh. This verifies operation
on the local machine at that time; netsh remains an unverified snapshot, and these
counts are not calibration or a guarantee about another adapter/environment.

## Frozen Windows package

PyInstaller 6.22.3 built the x64 onedir package with CPython 3.15.2. All **161**
bundled application code objects and `main.py` match the tested source, including
the scene-lifetime correction. Product/FileVersion resources are `1.3.0`; Python
3.15, QtPdf and QtPrintSupport runtimes, images, legal notices and dependency files
are checked. Application test modules are excluded. The existing optional
`scipy.special._cdflib` hidden-import warning remains; the checked application
rendering and analysis paths execute successfully in the frozen program.

The actual EXE was exercised through native desktop controls with isolated
preferences and AP Memory, using synthetic data: 4 points, 60 raw samples and
3 AP groups. Verified workflows:

- Startup/version, survey opening and material drawing.
- Live Map rendering, including material backgrounds; actual HTML map export.
- Analysis: 4 findings and 2 channel proposals; actual HTML report export.
- Shared structural/annotation selection, material Wall Edit and Esc cancellation.
- Clean print preview with calibrated scale and an additional legend page.
- Actual A3 landscape JPEG export at 600 DPI, including its legend image. Both
  JPEGs decode correctly at **9,921 × 7,016 px**, with 600-DPI metadata.

The frozen log contains no error/traceback. This is a focused interactive smoke
test, not exhaustive interaction coverage or a physical printer/RF field trial.

EXE SHA256:
`f1fbbc267726824586c9814126254cf12a9158f9ffb59866ecb99b0bb45fb56e`.

Distribution is `WiFiRFSurveyAnalyzer-v1.3.0-win64.zip`, with a sibling SHA256 file
and `release-manifest.json` recording the source commit and validation scope.
Archive entries are decompressed and hash-compared with the audited bundle.
Prior versioned archives are retained; survey/test files, preferences, AP Memory,
QA logs and private reports are excluded. Extract the complete folder and run
`WiFiRFSurveyAnalyzer.exe`, retaining its `_internal` directory.

## Validation limits

Software tests and passive scanner checks do not establish receiver calibration,
controlled-position RF precision or 6 GHz hardware support. Native print preview
and PDF output do not establish a physical printer's behavior. Curved usable
areas and decorative material patterns retain their documented approximations.
No external GitHub publication is implied by creation of the local release.
