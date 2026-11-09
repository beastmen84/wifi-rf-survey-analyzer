# 1.4.0 Release Verification

Date: 2026-11-09. Platform: Windows x64. Python: 3.15.2.

## Release scope

The release adds Load Plan annotation layers, text, free markers, desks,
numbered symbols, racks and Wi-Fi AP symbols above the original image/PDF.
Structure, walls, doors/windows, sheet resizing and structural fills remain
Draw Plan-only. Both modes support layers, legends, rack/switch/port inventory,
clean print/JPEG and visible overlays in Live Map and HTML exports.

Design Mode has consistent vector icons, readable captions, an active-tool
indicator and scrolling on short viewports. The toolbar adapts to larger UI
scales. Recommendations leads with concrete actions and folds supporting
evidence on request. JPEG exports center and proportionally fit the plan.

The follow-up control audit corrected direct placement of symbol-bound APs,
mode switching and capture/layer guards, JPEG collisions with the source
(including automatic legend filenames), and transparent PDF margins. These
changes preserve AP links and one-step undo/redo. Materials and inventory remain
descriptive; they do not assign RF attenuation. The survey CSV/sidecar schema
remains 2. Configured rack inventories use annotation format 2 / layer format 3;
existing earlier documents remain readable.

## Source verification

The control audit on `7f1f5bd` passed **2,402 tests and 479 subtests** on native
Windows Qt in 275.71 seconds, before changing release metadata to 1.4.0.
The 96 Load Plan UI cases span PNG/PDF, four languages, four themes and
100/125/175% scales; the 48 Draw Plan UI cases cover the same languages, themes
and scales. Eight isolated mocked-capture runs passed all 38 cases each
(304 tests). All 31 locked distributions match the installed environment and
`pip check` reports no conflicts. No dependency pins change for this release.

After changing release metadata, **73 workspace/version tests and 27 subtests**
passed in 14.17 seconds. This is a targeted release check; the complete suite
above was run on the audited feature code before the version bump. README
references to Load Plan symbols/legends and rack inventory have been aligned
with the shipped behavior.

Additional native Qt/source export probes passed for imported PNG, imported PDF
and a saved 1.3.0 drawing, each with 4 points and 60 raw samples:

- A3 landscape JPEG at **9,921 × 7,016 px / 600 DPI**, plus one matching legend
  JPEG per survey. All six images decode with the expected dimensions/DPI.
- Two-page print PDFs including legends for all three surveys.
- Six HTML map exports: signal/interference/channel/dominant for the PNG case,
  plus signal maps for PDF and Draw Plan. Three analysis HTML reports.
- Rack/switch/port legend content, white unpainted PDF margins and unchanged
  imported source bytes.

These export probes run the source application with native Qt and synthetic
data; they are distinct from the actual frozen EXE check below.

## Frozen Windows package

PyInstaller 6.22.3 built the Windows x64 onedir package with CPython 3.15.2.
All **166 bundled application modules** and `main.py` match normalized compiled
code from the release workspace. Required annotation, AP-binding, rack,
recommendation and export modules are included. Application test modules are
excluded. Product/FileVersion strings are `1.4.0`, with numeric version
`1.4.0.0`. Python 3.15, QtPdf, QtPrintSupport, images, legal notices, dependency
files and bundled documentation are checked against the workspace.

The existing optional `scipy.special._cdflib` hidden-import warning remains.
The build, source analysis/rendering/export probes and frozen startup succeed;
this does not assert execution of every SciPy path in the frozen application.

The actual EXE was launched through native Windows desktop automation with
isolated preferences and AP Memory. Its title/footer report **v1.4.0**. Opening
the saved imported-PNG survey succeeds and displays **4 points, 60 raw samples
and 3 AP groups**, the imported background, annotations, rack and AP overlays.
The frozen log contains no error or traceback.

Further desktop input was blocked by unavailable coordinate geometry and
repeated input interlocks in the automation channel. **Interactive frozen
validation is limited to startup and survey opening**; editing, print preview
and exports were not exercised interactively in the EXE for this release.
Source/native Qt tests and frozen code comparison provide separate evidence
and do not replace those interactions.

EXE SHA256:
`74d1a16a0ffdefb0eabb8c26353a36a82a60c789adcfc3b2ad747b1311a40473`.

Distribution is `WiFiRFSurveyAnalyzer-v1.4.0-win64.zip`, with a sibling SHA256
file and `release-manifest.json` recording the source commit and validation
scope. Packaging fully decompresses the archive and compares every entry's
SHA256 with the audited bundle. Previous versioned archives, `test_data/`, QA
fixtures, preferences, AP Memory and runtime logs are excluded from the new
package. Extract the complete folder and keep `_internal` beside the EXE.

## Validation limits

The earlier isolated native abort has not been reproduced in the final control
suite or eight capture stress runs; its cause is still undetermined.
Automated and interactive software checks do not establish receiver calibration,
controlled-position RF precision or 6 GHz hardware support. Print preview and
file exports do not establish a physical printer's behavior. No new RF scan is
required for this release. Prior versioned archives and the local pre-existing
`test_data/` directory are preserved. Creation of the local release does not
publish it to GitHub.
