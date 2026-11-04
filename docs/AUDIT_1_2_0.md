# 1.2.0 Release Verification

Date: 2026-11-04. Platform: Windows x64. Python: 3.15.2.

## Release scope

This release adds a receiver fixed to each survey, guided five-attempt capture,
separate acquisition reliability, signal stability and observed coverage, and
the final capture-review and Survey point-popup improvements. Relevant-network
selection precedes review, so Save accepts the measurement already reviewed.
It also includes the square upper corners of the selected central Live Map tab.

The CSV/sidecar schema remains version 2. Existing surveys stay readable; a
legacy survey chooses a receiver for future captures without relabelling old
evidence. Runtime dependency pins are unchanged from 1.1.0.

## Source verification

| Check | Result |
| --- | --- |
| Complete suite, Qt offscreen | 569 tests and 475 subtests passed, 38.94 s |
| Complete suite, native Windows Qt | 569 tests and 475 subtests passed, 42.63 s |
| Dependency consistency, `pip check` | No broken requirements |
| Essential Ruff checks, E9/F63/F7/F82 | Passed for application and tests |

The suites cover receiver identity/persistence and rejection of mismatches,
guided capture/cancellation, provisional and replacement measurements,
scope-before-review and one-save behavior, the three measurement-quality axes,
point-outline hover, RF analysis, report generation, and all four UI languages.
These are software regression checks; scan fixtures do not calibrate a receiver.

## Frozen Windows package

- Built with `WifiHeatmap.spec`, PyInstaller 6.22.3 and the configured
  `.venv315` interpreter. The `onedir` layout is retained.
- The actual EXE was launched with isolated settings and AP Memory on native
  Windows Qt. It reached `qt app module ready`, with the observed title
  `Wi-Fi RF Survey Analyzer v1.2.0`, without an error or traceback in its log.
  Only the release-check process was stopped afterward.
- All 87 bundled application modules and `main.py` were compared with the tested
  source using normalized Python code objects. Packaged version/channel are
  `1.2.0` / `stable`, including the new adapter, capture, quality and hover modules.
- Bundled legal notices, README, changelog, dependency files, image assets and
  README screenshot match the workspace. Python 3.15 and Qt PDF runtime files
  are present. Application test modules are excluded from the frozen archive.
- EXE SHA256:
  `fc12b8c6212301a11a0c0645c60d41dfc6026b0a99fe010041ca6d962ac35b27`.
- PyInstaller emits the existing `scipy.special._cdflib` hidden-import warning.
  The build and frozen startup succeed; this does not establish execution of
  every SciPy path in the packaged application.

Distribution uses `WiFiRFSurveyAnalyzer-v1.2.0-win64.zip`, a sibling SHA256 file
and `release-manifest.json` inside the application folder. The manifest records
the source commit, EXE hash, test counts and the limits of packaged validation.
Prior versioned release archives are retained.

## Remaining user trial

Computer Use reports that its native pipe is unavailable in this session.
Interactive workflows in the actual EXE have therefore not been verified by
desktop automation. Source/native Qt tests and frozen bytecode checks do not
replace that trial.

Check receiver selection and disconnection, first-point SSID selection before
review, Save/Repeat/Discard, protection of old points during cancelled rescans,
review fit at the chosen display scale, slow movement across point outlines,
and offline map/Analysis export from the packaged application.

Receiver calibration, controlled-position RF accuracy and 6 GHz hardware
validation remain separate field tasks. The historically intermittent Windows
Qt/COM diagnostic was absent from these final suites; its cause is not claimed
to be resolved. Earlier RF precision findings and their fixes remain documented
in [the 1.1.0 audit](AUDIT_1_1_0.md).
