# WiFi Heatmap

A desktop application for creating Wi‑Fi heatmaps from real-world signal measurements.

The project is focused on practical indoor wireless analysis and was developed around real survey scenarios rather than synthetic simulations.

It allows the user to:

- Load a floorplan/map image
- Place measurement points directly on the map
- Scan nearby Wi‑Fi networks
- Generate separate heatmaps for:
  - 2.4 GHz
  - 5 GHz
  - Combined networks
- Export generated maps as PNG images
- Analyze signal coverage spatially
- Compare multiple APs and bands

The application is designed with extensibility in mind and is progressively evolving toward more advanced RF analysis features.

---

# Features

## Current Features

### Interactive Floorplan Mapping
- Load custom maps/floorplans
- Click directly on the image to place survey points
- Visual feedback for measurement positions
- Coordinate-based point storage

### Wi‑Fi Scanning
- Multiple scan attempts per measurement point
- Aggregation of scan results
- Detection of:
  - SSID
  - BSSID
  - Channel
  - Band
  - RSSI / Signal strength
  - Channel width
  - PHY type

### Heatmap Generation
Generate dedicated heatmaps for:

- 2.4 GHz only
- 5 GHz only
- Combined view

Includes:

- Signal interpolation
- Gradient coloring
- Adjustable rendering
- PNG export

### CSV Data Storage
Measurements are stored in CSV format for:

- Reproducibility
- Debugging
- External analysis
- Future processing improvements

### Multi-Scan Aggregation Logic
The scanner performs multiple scans per point and merges results to reduce inconsistent readings.

Networks are distinguished using:

- BSSID
- Channel
- SSID

rather than relying only on SSID names.

---

# Project Goals

This project started as a practical tool for visualizing Wi‑Fi coverage in office environments.

The long-term objective is to progressively move toward more advanced RF survey capabilities similar to professional tools while remaining lightweight and understandable.

Planned improvements include:

- Scan confidence scoring
- Median-based signal aggregation
- Measurement quality diagnostics
- Real-time preview tabs
- Advanced interpolation
- Spatial smoothing
- Missing-band detection
- Interactive floorplan editor
- AP visualization tools
- Live heatmap updates during measurements

---

# Why This Project Exists

Most professional Wi‑Fi survey tools are:

- Expensive
- Closed-source
- Complex
- Hard to customize

This project explores how far a custom Python-based solution can go using:

- Real Wi‑Fi scans
- Open logic
- Flexible rendering
- Transparent processing

while still remaining practical for real environments.

---

# Technical Notes

## Wi‑Fi Scanning Limitations

Wi‑Fi scanning on Windows is inherently imperfect.

Even with advanced libraries, scan results can vary because of:

- Driver behavior
- Beacon timing
- Dual-band handling
- WLAN API limitations
- Temporal fluctuations
- Roaming logic

The project therefore focuses heavily on:

- Multiple scan attempts
- Data aggregation
- Signal consistency
- Future confidence scoring

rather than trusting single-scan results.

---

# Technologies Used

- Python
- PyQt / GUI framework
- NumPy
- Pandas
- Matplotlib
- Pillow
- Wi‑Fi scanning libraries (LSWiFi / Windows WLAN APIs)

---

# Installation

## Clone the Repository

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

# Basic Workflow

1. Load a floorplan image
2. Select your current physical position
3. Perform Wi‑Fi scans
4. Add measurement points
5. Repeat across the environment
6. Generate heatmaps
7. Export results

---

# Example Use Cases

- Office Wi‑Fi analysis
- Home coverage optimization
- AP placement testing
- Dead zone detection
- 2.4 GHz vs 5 GHz comparison
- Educational RF experiments
- Heatmap visualization research

---

# Current Challenges

The project intentionally explores several difficult aspects of Wi‑Fi surveying:

- Inconsistent scans
- Missing AP detections
- Temporal RSSI variation
- Dual-band ambiguity
- Spatial interpolation accuracy
- Windows WLAN limitations

These are active development areas.

---

# Future Ideas

## Real-Time Heatmap Preview
Live updating heatmaps while taking measurements.

## Internal Map Editor
Ability to create floorplans directly inside the application.

## Confidence Visualization
Visual representation of scan reliability.

## AP Tracking
Visualize individual access points separately.

## Advanced RF Metrics
Potential future support for:

- Noise estimation
- SNR visualization
- Stability metrics
- Variance maps

---

# Contributing

Contributions, ideas, and RF experimentation feedback are welcome.

This project is heavily experimentation-driven and practical feedback from real environments is extremely valuable.

---

# License

This project is currently private / experimental.

Add your preferred license here if the repository becomes public.

---

# Author

Davide Marchi

Developed as a practical and experimental Wi‑Fi heatmapping project focused on real-world environments and RF behavior analysis.
