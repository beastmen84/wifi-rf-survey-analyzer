# WiFi Heatmap

A Python desktop application for real-world Wi‑Fi heatmap surveying and visualization.

The project focuses on practical RF analysis using live Wi‑Fi measurements collected directly from real environments rather than simulations.

It supports:

- Interactive floorplan-based surveys
- Multi-band Wi‑Fi scanning
- Live heatmap rendering
- Real-time map updates while surveying
- 2.4 GHz and 5 GHz analysis
- Interference visualization
- AP grouping and filtering
- CSV-based survey persistence
- Exportable rendered heatmaps

The application is designed as an experimentation-driven RF visualization tool inspired by professional Wi‑Fi survey software while remaining lightweight, transparent, and fully customizable.

---

# Current Features

## Interactive Survey Workflow

- Load custom floorplans/maps
- Place measurement points directly on the map
- Store exact coordinates for each scan
- Open and continue existing surveys
- Multi-language UI support
- Optimized desktop UI with scalable layout

---

# Live Heatmap System

The application already includes a live rendering pipeline.

Heatmaps update dynamically while measurements are collected, allowing immediate visualization of:

- Coverage evolution
- Weak zones
- Signal transitions
- Interference areas
- AP dominance

The live rendering engine includes:

- Cached rendering
- Incremental updates
- Distance masking
- Signal interpolation
- Spatial smoothing
- Adaptive transparency
- Real-time point overlays

---

# Wi‑Fi Scanning

The scanner performs multiple scans per survey point to reduce inconsistent detections.

Collected information includes:

- SSID
- BSSID
- Signal strength (RSSI / dBm)
- Channel
- Band
- Channel width
- PHY type

Networks are handled using BSSID-aware logic rather than relying only on SSID names.

This is especially important for:

- Dual-band environments
- Enterprise Wi‑Fi deployments
- Mesh systems
- Multi-AP installations

---

# Heatmap Types

## Signal Heatmaps

Separate rendering for:

- 2.4 GHz
- 5 GHz
- Combined analysis

Features include:

- Interpolation
- Signal smoothing
- Configurable rendering
- Distance-aware masking
- Adjustable color scales
- Signal threshold filtering

---

## Interference Heatmaps

The application also supports interference-oriented visualization.

Interference analysis includes:

- Risk calculation
- Spatial interpolation
- Visual interference scoring
- Band-specific interference mapping

---

# Rendering Engine

The rendering pipeline is built around:

- NumPy
- Pandas
- Matplotlib
- PIL

The renderer includes:

- Grid caching
- Result caching
- Bilinear rendering
- Distance alpha masking
- Heatmap smoothing
- Point collapsing/aggregation
- Live image payload generation

---

# Data Storage

Survey data is stored in CSV format.

This allows:

- Reproducibility
- Debugging
- Offline analysis
- External processing
- Future algorithm improvements

The project intentionally keeps the measurement format transparent and inspectable.

---

# Real RF Challenges Explored

The project intentionally investigates difficult real-world Wi‑Fi surveying problems such as:

- Inconsistent scan results
- Missing AP detections
- Beacon timing issues
- Dual-band ambiguity
- Spatial interpolation artifacts
- Driver limitations on Windows
- Temporal RSSI fluctuations

Rather than hiding these problems, the project aims to expose and progressively improve their handling.

---

# Technologies Used

- Python
- Tkinter
- ttkbootstrap
- NumPy
- Pandas
- Matplotlib
- Pillow
- Windows WLAN APIs / LSWiFi-related tooling

---

# Installation

## Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/wifi_heatmap.git
cd wifi_heatmap
```

## Create Virtual Environment

```bash
python -m venv .venv
```

### Windows

```bash
.venv\\Scripts\\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Running the Application

```bash
python wifi_heatmap.py
```

---

# Typical Workflow

1. Load a floorplan image
2. Move through the environment
3. Click measurement positions on the map
4. Perform Wi‑Fi scans
5. Watch the live heatmaps update
6. Analyze signal/interference distribution
7. Export final maps

---

# Example Use Cases

- Office Wi‑Fi analysis
- AP placement validation
- Dead-zone identification
- 2.4 GHz vs 5 GHz comparison
- Educational RF analysis
- Wireless experimentation
- Home network optimization

---

# Planned Improvements

Future development may include:

- Confidence scoring per measurement
- Median/variance-based aggregation
- Advanced RF statistics
- Enhanced AP visualization
- Internal floorplan editor
- Improved interpolation controls
- Scan diagnostics tools
- Additional live analytics

---

# Project Philosophy

Most professional Wi‑Fi survey tools are:

- Expensive
- Closed-source
- Difficult to customize

This project explores how far a transparent Python-based solution can go while remaining understandable and adaptable.

The goal is not just generating pretty heatmaps, but understanding the underlying RF behavior and scan reliability challenges.

---

# Author

Davide Marchi

Experimental Wi‑Fi heatmapping and RF visualization project focused on real-world environments and practical wireless analysis.
