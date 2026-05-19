# AI Advisor Design

Status: planning draft for `v1.1.0`

Last updated: 2026-05-19

## Goal

AI Advisor is a local RF analysis layer for the current survey. It should read
the measured Wi-Fi evidence, explain the most relevant findings, and propose
practical actions without changing AP metadata, map settings or survey data.

The first implementation should behave like a deterministic RF advisor engine,
not a general chatbot. Recommendations must be traceable to survey evidence and
must expose assumptions, confidence and data-quality limitations.

## Core Principles

- All analysis is local. Survey data, BSSIDs, SSIDs, floor plans and scan
  evidence are not sent outside the application.
- The advisor analyzes the full survey dataset, not only the current Live Map
  filter. The selected Live Map controls the advisor mode and priority, not the
  data boundary.
- Every recommendation must cite measured evidence or clearly state why the
  evidence is incomplete.
- The advisor is advisory only. It must not silently modify AP groups, AP
  metadata, expected channels, channel overrides, floor-plan settings or map
  options.
- The advisor must prefer conservative RF guidance over aggressive
  auto-tuning-style advice.
- Low-confidence analysis is still useful when it tells the user what evidence
  is missing or which extra measurements would improve the conclusion.

## Non-Goals

- No remote LLM/API integration in the baseline `v1.1.0` scope.
- No automatic AP controller changes.
- No hidden mutation of survey data or AP metadata.
- No replacement for the Survey Quality Dashboard. The advisor should consume
  quality evidence and make it easier to act on, not duplicate the whole view.
- No multi-floor data-model changes in the initial AI Advisor scope.

## Scope Definitions

### Analysis Scope

Always the complete current survey:

- all measurement points;
- all relevant scan evidence available through the CSV and `.scan` sidecar;
- selected relevant SSIDs;
- AP groups, aliases, roles and metadata;
- AP positions;
- expected channels and analysis-channel overrides;
- scanner limitations and Survey Quality findings;
- measurement system, scale, floor-plan and boundaries metadata.

### Advisor Mode

Selected from the active Live Map:

- Signal Coverage;
- AP Interference;
- AP Channels;
- Dominant AP.

Advisor mode changes prioritization and wording. It does not hide relevant
evidence from other bands, SSIDs or interference categories.

### Current View Context

The current Live Map state can be used as context:

- selected SSID;
- selected band;
- selected aggregation;
- visible map type;
- current map options.

The UI should clearly distinguish findings related to the current view from
other relevant survey-wide findings.

## Output Model

The advisor engine should return structured data, not preformatted free text.
The UI, translations and future PDF export can then render the same report.

Suggested objects:

- `AdvisorReport`
- `AdvisorSection`
- `Finding`
- `Recommendation`
- `EvidenceRef`
- `Assumption`
- `DataQualityLimit`

Each finding should include:

- stable identifier;
- category;
- severity;
- confidence;
- title key;
- summary key;
- affected SSIDs, AP groups, bands, channels and measurement points where
  available;
- evidence references;
- recommendations;
- assumptions;
- data-quality limitations.

Suggested severity levels:

- `info`: useful observation or context;
- `notice`: worth reviewing, no clear operational issue;
- `warning`: likely RF or data-quality issue;
- `critical`: strong evidence of a major issue affecting interpretation or
  coverage.

Suggested confidence levels:

- `low`: evidence is sparse, scanner details are incomplete or AP modeling is
  uncertain;
- `medium`: evidence is usable but not complete enough for strong advice;
- `high`: multiple consistent data points support the conclusion.

## Evidence Rules

The advisor should only make operational recommendations when at least one of
these is true:

- multiple measurement points support the same conclusion;
- the finding matches explicit AP metadata or expected-channel configuration;
- the finding is already backed by Survey Quality diagnostics;
- a single point is severe enough to be useful, and the report labels it as
  localized evidence.

When evidence is weak, the advisor should prefer actions such as:

- collect more measurement points in the affected area;
- repeat scans at low-confidence points;
- confirm AP group metadata;
- place missing AP positions;
- verify channel/frequency details with a richer scanner source.

## Map-Specific Analysis

### AP Interference

Primary `v1.1.0` implementation candidate.

Useful findings:

- 2.4 GHz APs on channels outside the usual non-overlapping plan;
- co-channel and adjacent-channel overlap involving relevant SSIDs;
- internal APs contributing to interference with each other;
- external or interferer AP groups with strong observed signal;
- channel-width choices that increase overlap risk;
- points where scanner limitations weaken channel-sensitive conclusions;
- AP roles that change interpretation, such as `external`, `interferer` or
  `test/hidden`.

Example recommendations:

- review 2.4 GHz channel assignment;
- reduce channel width where overlap evidence is strong;
- verify expected channels or analysis-channel overrides;
- classify unmanaged APs correctly;
- collect more evidence where scan confidence is low.

### AP Channels

Useful findings:

- observed channels differ from expected channels;
- AP groups change channel during the survey;
- multiple internal APs cluster on the same crowded channel;
- 2.4 GHz channel plan uses overlapping channels;
- 5 GHz or 6 GHz channel evidence is incomplete.

Example recommendations:

- stabilize the channel plan;
- correct AP metadata or expected-channel configuration;
- review channel-width policy;
- re-scan points where scanner data is incomplete.

### Dominant AP

Useful findings:

- dominant AP does not match the nearest modeled AP;
- second AP is close enough in signal to suggest roaming ambiguity;
- connected-client evidence suggests sticky-client behavior;
- AP positions are missing or inconsistent with observed dominance;
- local-area AP scope affects interpretation.

Example recommendations:

- place missing AP positions;
- verify AP physical grouping;
- review transmit-power balance;
- add points near suspected roaming boundaries;
- inspect sticky-client points before changing RF design.

### Signal Coverage

Coverage advice should be more conservative than Interference or Channels.

Useful findings:

- weak coverage clusters;
- isolated weak points;
- weak areas with low scan confidence;
- possible AP placement or local-area scope influence;
- missing relevant SSID evidence.

Example recommendations:

- collect additional points around weak areas;
- verify whether the weak area is operationally relevant;
- review AP placement only when AP position and dominance evidence support it;
- avoid blind transmit-power increases unless supported by broader evidence.

## UI Concept

- Add an `AI Advisor` button in the Live Map toolbar, immediately left of
  `Export PDF`.
- Open a right-side overlay panel, visually aligned with existing settings and
  analysis panels.
- Keep the Live Map interactive while the panel is open when practical.
- Recommended sections:
  - Overview;
  - Key Findings;
  - Recommended Actions;
  - Evidence;
  - Assumptions And Limits.
- Findings should be expandable and, where evidence includes points, should
  allow focusing the related measurement point or map area.
- The panel should show that the analysis uses the full survey, while marking
  which findings are related to the current view.

## Testing Strategy

- Unit tests with synthetic surveys for each rule.
- Regression tests with private real-survey samples where available.
- Translation and placeholder parity tests once UI text is added.
- UI smoke tests for opening/closing the advisor panel and rendering empty,
  warning and high-density reports.
- No recommendation should be emitted without evidence or an explicit
  low-confidence/data-limit explanation.

## Implementation Phases

1. Define structured advisor models and an `AdvisorContext` builder.
2. Implement AP Interference advisor rules without UI.
3. Add focused tests for Interference findings and recommendation evidence.
4. Add the Live Map `AI Advisor` button and right-side overlay panel.
5. Implement AP Channels, Dominant AP and Signal Coverage modes.
6. Add translations and visual-density checks.
7. Consider optional PDF Advisor Summary only after the UI advisor proves useful.

## Future LLM Option

A future LLM layer, if ever added, should only summarize or rephrase the
structured local advisor output. It must not be the source of RF decisions, and
it must be opt-in with explicit privacy disclosure if any external service is
used.
