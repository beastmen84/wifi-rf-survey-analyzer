# WiFi Heatmap – V2 Vision & Architecture Notes

## General Direction

The goal of V2 is not simply adding more visual features, but improving:

- RF data reliability
- survey quality evaluation
- AP intelligence
- realism of collected data interpretation
- advanced workflow usability

The application should progressively evolve from:

```text
"heatmap drawing tool"
```

to:

```text
"Wi‑Fi survey and RF analysis platform"
```

---

# Core Philosophy of V2

The application should:

- collect raw Wi‑Fi measurements
- evaluate data quality
- identify inconsistencies
- understand AP relationships
- distinguish APs, radios and BSSIDs
- help the user validate the survey itself

The heatmap becomes the result of a validated RF dataset, not just interpolated colors.

---

# Main V2 Areas

## 1. AP Group Manager

### Problem

Enterprise and advanced Wi‑Fi environments generate multiple BSSIDs:

- multiple radios
- guest networks
- virtual interfaces
- locally administered MACs
- mesh/repeater behavior

Simple grouping logic is not always reliable.

### Proposed Solution

Introduce a dedicated AP Group Manager.

### Features

- automatic grouping suggestions
- manual merge/split of AP groups
- editable AP aliases
- save grouping inside survey project
- mark AP as:
  - internal
  - external
  - interferer
  - hidden/test AP

### Example

```text
AP Group: IT OFFICE
Members:
- 78:8c:b5:ee:c1:2a
- 7a:8c:b5:ee:c1:2b
```

---

## 2. AP Positioning on Map

### New Capability

Allow manually placing APs directly on the floorplan.

### Why Important

Knowing physical AP position allows:

- validating signal behavior
- detecting anomalous coverage
- understanding roaming
- validating dominant AP regions
- identifying unrealistic interpolations

### Possible Logic

Examples:

```text
Strong signal too far from AP
Weak signal too close to AP
Unexpected dominant AP
```

---

## 3. AP Metadata System

Each AP group may include metadata:

```text
Vendor
Model
Mounting type
Band support
Expected channels
Expected radios
Notes
```

### AI-Assisted Suggestions

Future possibility:

- infer vendor/model
- suggest expected capabilities
- suggest expected band/channel behavior

User should always confirm suggestions manually.

---

# 4. Raw Scan Storage

## Current Limitation

Only aggregated scan results are preserved.

This reduces debugging capability.

## Proposed V2 Structure

### raw_scans.csv

Store every scan attempt individually:

```text
point_id
scan_attempt
timestamp
ssid
bssid
channel
band
signal_dbm
backend
```

### aggregated_points.csv

Store processed/merged results separately.

---

# 5. Data Quality Engine

One of the most important V2 systems.

## Per-network statistics

For each AP/network:

```text
samples_seen
samples_total
median_dbm
mean_dbm
max_dbm
min_dbm
variance
range_db
channel_consistency
```

## Quality Classification

Examples:

```text
GOOD
UNSTABLE
LOW CONFIDENCE
MISSING EXPECTED BAND
CHANNEL CONFLICT
OUTLIER
```

---

# 6. Confidence-Aware Rendering

Current confidence:

```text
samples_seen / samples_total
```

V2 should use confidence as interpolation weight.

### Example

```text
High confidence point:
strong influence on heatmap

Low confidence point:
reduced influence
```

### Benefits

- fewer artifacts
- fewer false hotspots
- more realistic interpolation
- unstable readings affect map less

---

# 7. Survey Quality Dashboard

Dedicated survey validation panel.

## Example Information

```text
Total points
Good points
Unstable points
Suspicious points
Coverage completeness
Missing expected bands
Dominant AP conflicts
```

## Goal

Help the user identify:

- points to rescan
- unreliable measurements
- suspicious AP behavior

---

# 8. Improved Interference Analysis

Current interference maps can evolve into:

- co-channel interference analysis
- adjacent-channel interference
- AP overlap quality
- roaming overlap zones
- AP density analysis

---

# 9. UI Evolution

## Current Situation

Tkinter + ttkbootstrap works well for V1.

However, V2 may eventually require:

- advanced tables
- dockable panels
- complex dashboards
- large interactive datasets
- advanced filtering
- multi-panel workflows

## Recommended Future Direction

Potential migration toward PySide6 (Qt for Python).

Reasons:

- stronger desktop architecture
- advanced widgets
- scalable layouts
- better threading support
- professional dashboard workflows
- better support for complex data interfaces
- long-term maintainability for large applications

Suggested approach:

```text
1. Refactor core logic first
2. Separate UI from RF engine
3. Keep rendering/scan logic UI-independent
4. Migrate UI gradually later
```

---

# Suggested V2 Priorities

## Highest Priority

1. AP Group Manager
2. Raw scan storage
3. Data Quality Engine
4. Confidence-aware rendering

## Medium Priority

5. Survey Quality Dashboard
6. AP positioning system
7. Advanced interference analysis

## Long-Term

8. UI migration to PySide6
9. Internal floorplan editor
10. Advanced AI-assisted RF analysis

---

# Final Vision

The long-term vision is a tool capable of:

- collecting real RF data
- understanding AP relationships
- evaluating survey reliability
- detecting anomalies
- visualizing realistic Wi‑Fi behavior
- helping users improve Wi‑Fi deployments

rather than simply generating colored heatmaps.
