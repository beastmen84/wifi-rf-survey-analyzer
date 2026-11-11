# 1.5.0 Release Verification

Date: 2026-11-11. Platform: Windows x64. Python: 3.15.2.

## Scope

This release includes the drawing, wall topology and navigation improvements
since 1.4.0. Hardware OpenGL is used when available, with a software fallback.
Prepared grid masks, bounded room caches and spatial wall-face indexing reduce
repeated work. Exact form dimensions and fixed neighboring rooms are preserved;
an incompatible placement is rejected rather than moving existing rooms.

Wall priorities and material Apply to all sides, thickness-aware openings,
jamb clearances, useful line lengths and cleanup after adjacent-room deletion
share the existing persistence and undo/redo model. Grid fading recognizes
physical enclosures, including curved joins; it does not join reference lines
or redefine editable rooms. Materials remain descriptive, without RF attenuation.
Survey CSV/raw-sidecar schema remains 2; no dependency pins change.

## Verification

The final full suite on native Windows Qt passed **2,846 tests and 479 subtests**
in 691.75 seconds after changing release metadata to 1.5.0. The 31 locked
distributions match the installed environment, `pip check` reports no conflicts,
and Ruff E9/F63/F7/F82 passes. Dependency pins are unchanged.

The preceding topology campaign passed 10,000 generated graphs, and 108 native
GPU navigation comparisons at effective DPR 1 / 1.25 / 1.5 / 2. Twelve physical
enclosure regressions passed on both native and headless software renderers.
These checks are documented in the source tree's topology/performance and grid
enclosure audits; they are separate from the final full-suite count above.

Fresh source/native Qt export probes passed for imported PNG, imported PDF and
Draw Plan, using synthetic data with four points and 60 raw samples:

- A3 landscape JPEG at 9,921 by 7,016 pixels / 600 DPI, including matching legend
  JPEGs. All images decode at the expected size and resolution.
- Multi-page PDF print output including legends.
- Six HTML maps across the cases, including signal/interference/channel/dominant,
  and three analysis HTML reports.
- Imported backgrounds retain their original SHA-256 hashes.

These export probes execute the source application, not the frozen EXE.

## Frozen Windows package

PyInstaller 6.22.3 built the Windows x64 onedir package with CPython 3.15.2.
All **168 bundled application modules** and `main.py` match normalized compiled
code from the tested workspace. File/ProductVersion resources are `1.5.0`, with
numeric version `1.5.0.0`. QtOpenGLWidgets and QtOpenGL extension modules and DLLs,
QtPdf, QtPrintSupport, Python 3.15, icons, legal notices and dependency files are
included and checked. Application test modules are excluded.

The existing optional `scipy.special._cdflib` hidden-import warning remains.
The source analysis/rendering/export checks succeed; this does not establish
execution of every SciPy path in the frozen application.

EXE SHA-256:
`ece274eb5686f76bc22216523c1b03c88c5c0e5e5d7772849e9afb22d28e584a`.

The actual EXE was started with isolated preferences and AP Memory. Native
accessibility reports the 1.5.0 title/footer and Ready startup state. The desktop
was locked during capture, preventing visual inspection and further interaction.
Frozen validation is therefore limited to startup metadata: no survey-opening,
editing, preview or export interaction is claimed for this EXE. The computer-use
safety workflow requires stopping input when the desktop is locked.

Distribution is `WiFiRFSurveyAnalyzer-v1.5.0-win64.zip`, with a sibling SHA-256
file and a bundled `release-manifest.json` identifying the source commit and
validation scope. Every ZIP entry is fully decompressed and hash-compared with
the audited bundle. Earlier archives and original project files are preserved.
Extract the complete folder and retain `_internal` beside the EXE.

## Known limits

The measured improvement on the supplied plan was about 3.25 times for pan and
2.04 times for insertion/review. Rectangle preview remained about 27% slower
than the former software renderer in that measurement. Full preparation of a
400-room synthetic scene still took about five seconds. These are measurements
of the Qt event loop on the tested integrated GPU, not monitor FPS guarantees
or a comparison with Draw.io. See the topology/performance audit for methodology.

Physically closed grid areas do not automatically become editable reference
rooms. Real gaps remain open. The local corrected survey is excluded from the
release, as are all private projects, settings, AP Memory and QA fixtures.

No RF field calibration or physical printer test is implied by software checks.
Local packaging does not publish a GitHub release.
