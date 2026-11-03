# Local RF Analysis And Recommendations

Status: initial implementation for the `v1.1.0` feature line

Last updated: 2026-11-03

The historical filename is retained for existing links. This feature uses
deterministic local rules, with no AI model, external API or remote data transfer.
This document supersedes the original Live Map overlay proposal.

## User Workflow

The third workspace tab, Analysis and recommendations, is the final survey step
after Survey Quality, AP modeling and Live Map inspection. Its findings cover
the whole current survey, independently of Live Map SSID/band/map filters.
Operational targets are internal APs carrying explicitly relevant SSIDs.
External/interferer APs contribute fixed neighbor evidence; test APs are excluded.

The user can adjust coverage target, scan confidence, supporting point count and
candidate channel lists. Defaults are -70 dBm, 60%, three points and 1/6/11 for
2.4 GHz. 5/6 GHz lists start empty, so those bands produce review findings until
the user supplies channels supported by the APs/site configuration. Lists are
syntactically validated; the app has no country/DFS/AP-capability database.
Objectives belong to this app session and are recorded in reports, not saved to
survey CSV metadata. The category filter affects browsing, not report scope.

Findings show confidence, an action, measured points/readings, limitations and
post-change checks. Point links return to the survey canvas/table. The existing
Live Map PDF remains separate. The new full report exports to PDF or standalone
HTML, including an optional numbered floor-plan overview.

## Architecture

- `advisor/models.py`: profile, findings, evidence and report snapshot; stable
  input fingerprint includes rows, raw evidence, groups, relevant SSIDs, scale,
  objectives, session metadata, survey name and engine version.
- `advisor/engine.py`: Qt-free rule engine, with copied inputs and no mutation
  of survey data, AP groups, overrides or AP Memory.
- `survey/scope.py`: shared Local Area relevance rules extracted from Survey
  Quality, retaining its manual/automatic radius behavior.
- `advisor/presentation.py`: escaped, localized presentation shared by interactive
  findings and both report formats. Names/SSID values cannot inject HTML.
- `qt_ui/qt_analysis.py`: coalesced background QThread work and snapshot checks.
  Old results are rejected after relevant edits/session changes. Export checks
  freshness again after the modal file dialog; scans/running work block export.
  Closing/restarting waits for active work to finish using the workspace guard.
- `exporting/analysis_report.py`: embedded floor-plan evidence, atomic HTML/PDF
  replacement and generated-PDF validation. QPdfWriter renders selectable text
  with fitting table chunks and repeated headers, keeping normal rows together.
- `translations/advisor.py`: EN/IT/FR/ES labels, actions, assumptions and Help.

## Evidence And Rules

All inputs are advisory observations of a survey snapshot, not a controller
configuration. Confidence labels are rule tiers, not calibrated probabilities.
Raw samples feed the existing Survey Quality variability/completeness checks.
Usable rows require finite coordinates and RSSI in -120..0 dBm. Invalid rows are
reported; an identifiable affected point is excluded from precise proposals.
Scan confidence also requires at least three observed samples, valid totals,
and the lower of explicit confidence and the observed/attempted ratio.

Data findings precede operational recommendations. They cover missing relevance,
sparse surveys, poor scan quality, invalid measurements, missing scale,
incomplete radio evidence and expected-channel/band metadata disagreements.

### Channel Plan

One node represents one physical AP group/band, preventing several SSIDs on the
same radio from being treated as independent APs. Nodes are connected by usable
co-observations at signals of at least -85 dBm. Edge weights sum a bounded
signal-strength factor across shared points. Spectral overlap uses the existing
map engine's channel/width model; this is not a channel-utilization measurement.

Precise changes require the configured number of overlapping points, stable
valid channels/widths for the target and its observed neighbors, adequate scan
confidence, no conflicting target metadata/override, and user candidate policy.
Unknown neighbor bands or unreliable neighbor evidence block precise changes.
2.4 GHz precise changes require 20 MHz evidence; wider widths receive review
guidance. 5/6 GHz candidates require representable width/frequency ranges, and
6 GHz nodes/neighbors additionally require explicit frequency evidence.

A deterministic coordinate-descent pass evaluates the APs together, accepts
only changes reducing node overlap by more than 10% (also lowering the total), and stops
after convergence or three passes. External AP assignments stay fixed. Final
assignments are presented once per node as a single joint plan, with the total
before/after overlap index. This is a bounded heuristic, not a globally optimal
channel planner, an airtime score or a predicted performance improvement.

Unstable channels, manual analysis overrides and wide widths have explicit
review findings. Map overrides do not replace measured channel evidence here.

### Coverage, Position And Roaming

- Weak coverage is evaluated per relevant SSID/band at trusted measured points
  against the profile target. Counts describe points, not floor-area coverage.
- Missing relevant networks follow the shared Local Area scope and trigger
  repeat-scan guidance; absence alone never proves a coverage hole.
- Dominance uses the existing AP-position checks and requires valid positions
  and scale. Advice first checks grouping, mounting, obstacles and nearby data.
- A controlled power-balance trial is suggested only for repeated strong/distant
  dominance with another AP meeting the same coverage target, no observed weak
  coverage for that SSID/band, no poor/invalid points and no target metadata
  conflict. It does not infer a dB reduction or an exact new AP position.
- Roaming observations require explicit connected-client evidence and another
  AP of the same SSID/band stronger by at least 8 dB. Client behavior remains
  an observation to verify, not proof of an AP fault.

## Validation And Limits

Regression tests use synthetic surveys for joint channel decisions, physical
grouping, scope, quality gates, metadata, scanner limitations, coverage, power,
roaming, input purity and stale workers/exports. Exports are generated in all four
languages, loaded/rasterized with Qt PDF, checked for text/evidence preservation,
normal row pagination and safe replacement failures. UI/PDF examples are visually
inspected during development. These checks do not replace field RF validation.

The scanner does not measure airtime utilization, retry rates, non-Wi-Fi
interference or throughput. There is no propagation/obstacle simulation, exact
relocation solver, automatic controller action, per-AP regulatory/capability
model or validated new-design coverage prediction. Cross-band steering is not
inferred from the same-band connected-client check. Large reports may be long
because point evidence is retained. Real 6 GHz hardware behavior remains to be
validated. Next rule expansion should follow real-survey evidence and false
positive review; keep every recommendation traceable to measurements.
