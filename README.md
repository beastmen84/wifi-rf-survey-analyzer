# WiFi Heatmap

A Python desktop application for real-world Wi-Fi heatmap surveying and RF visualization.

The project focuses on practical analysis from live Wi-Fi measurements collected directly in real environments. It is intended as a transparent, customizable alternative to closed survey tools, with emphasis on scan reliability, AP behavior, and map readability.

## Current Features

### Survey Workflow

- Start a new survey or open an existing CSV survey.
- Load a floorplan image or PDF.
- Store the floorplan path in survey metadata so reopening the CSV reloads the map automatically.
- Place measurement points directly on the floorplan.
- Delete the selected point or the last point.
- Pan, zoom, and fit the floorplan.
- Save on demand, with dirty-state tracking and save prompt on close.
- Export generated maps in the same folder as the saved survey CSV.

### User Interface

- PySide6 UI with a lightweight launcher in `main.py` and the main workspace in `qt_app.py`.
- Start screen with new/open/exit actions and visual mouse shortcut help.
- Main UI split into survey and live map tabs.
- Toolbar controls for saving, opening CSV, AP aliases, scale calibration, help, map generation, theme, and language.
- English and Italian language selector.
- Theme selector.
- Help dialog with workflow, live map, heatmap, and scan guidance.
- Centered modal dialogs.

### Wi-Fi Scanning

- Automatic scan backend selection.
- lswifi support with fallback behavior.
- Multiple scan attempts per point.
- Delay between scan attempts to reduce partial WLAN scan results.
- Aggregation by BSSID and channel.
- Median, min, max, and sample list for RSSI values.
- Confidence fields per measurement.
- Suspicious scan warning when a new scan sees far fewer networks than the previous good scan.
- Relevant SSID workflow: all networks are saved, while selected SSIDs drive warnings and quality checks.

Collected fields include:

- timestamp
- x/y coordinates
- SSID
- BSSID
- signal percent
- signal dBm
- median/max/min dBm
- raw signal samples
- samples seen / total
- scan confidence
- channel
- channel width
- radio / PHY type

### Data Storage

Survey data is stored in a readable CSV file with metadata comments at the top.

Metadata can include:

- floorplan path
- remembered capture filter
- AP aliases
- scale calibration (`px_per_meter`)
- app creation fields

The current application expects V2 survey CSV files created by this tool.

### AP Aliases

- Dedicated AP alias dialog.
- Search and sortable columns.
- Inline alias editing.
- Alias state persisted in CSV metadata.
- Aliases are used in tooltips, legends, AP channel maps, dominant AP maps, and interference analysis where available.

### Scale Calibration

- Toolbar action to calibrate the map scale.
- Select two known points on the floorplan and enter the real distance in meters.
- Stores `px_per_meter` in the survey metadata.
- Distance controls switch from pixels to meters when a survey is calibrated.
- The calibrated distance is used by live maps and generated PNG maps.

## Live Map System

The application includes a live rendering pipeline that updates while measurements are collected.

Live map types:

- Signal coverage
- AP interference
- AP channels
- Dominant AP / roaming view

Live map features:

- Separate survey and live map tabs.
- Auto-update and manual refresh.
- Live zoom and pan.
- AP group filter for signal and channel views.
- Band selection.
- Interference mode selection.
- Smoothing, interpolation, aggregation, color scale, usability threshold, and max distance controls where relevant.
- Mouseover tooltips for point details.
- Missing-data markers.
- Horizontal scale/legend area based on the active map type.
- Background rendering for heavier live maps.
- Grid caching and result caching.

## Generated Map Types

### Signal Coverage

- 2.4 GHz, 5 GHz, or combined view.
- Interpolation.
- Smoothing.
- Distance-aware masking.
- Adjustable color scale.
- Optional threshold filter for usable coverage.
- Export to PNG.

### AP Interference

- Band-specific interference maps.
- Intra-SSID or all-SSID analysis.
- Channel overlap awareness.
- Channel width support where available.
- Risk percentage visualization.
- Worst-point summary dialog.
- CSV report export.
- Reference table below the generated map for highlighted points.

### AP Channels

- Real-point map without interpolation.
- Points colored by AP/channel.
- Channel-width labels where available.
- Reference table for labels.
- AP aliases supported.

### Dominant AP / Roaming

- Real-point map showing the strongest AP group at each measurement point.
- Roaming overlap detection.
- Reference table for labels.
- AP aliases supported.

## Rendering Engine

The rendering pipeline uses:

- NumPy
- Pandas
- SciPy
- Matplotlib
- Pillow

The renderer includes:

- High-resolution interpolation grid
- Grid caching
- Result caching
- Distance alpha masking
- Spatial smoothing
- Point collapsing / aggregation
- Live image payload generation
- Background worker rendering for live continuous maps

## Real RF Challenges Addressed

The project explicitly handles or exposes several practical Wi-Fi survey problems:

- Inconsistent scan results from Windows WLAN scans.
- Missing AP detections.
- Beacon timing issues.
- Dual-band ambiguity.
- Multi-BSSID / multi-SSID enterprise deployments.
- Guest SSIDs sharing the same physical AP/channel.
- Spatial interpolation artifacts.
- Channel overlap and channel width uncertainty.
- Temporal RSSI fluctuations.
- Dense point labeling readability.

## Technologies Used

- Python
- PySide6
- PyMuPDF
- Pillow
- Pandas
- NumPy
- SciPy
- Matplotlib
- lswifi
- PyInstaller

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/wifi_heatmap.git
cd wifi_heatmap
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Running the Application

The application entry point is:

```bash
python main.py
```

`main.py` shows the startup screen quickly and loads the heavier Qt workspace
components in the background before enabling the survey actions.

## Building the Executable

```bash
python -m PyInstaller -y WifiHeatmap.spec
```

The Windows build output is generated under:

```text
dist/WifiHeatmap/WifiHeatmap.exe
```

## Typical Workflow

1. Start a new survey or open an existing CSV.
2. Load the floorplan.
3. Optionally calibrate the scale if a known real distance is available.
4. Move through the environment.
5. Right-click the measurement positions on the map.
6. Save the survey.
7. Use the live map tab while collecting data.
8. Generate final PNG maps and CSV reports.

## Example Use Cases

- Office Wi-Fi analysis
- AP placement validation
- Dead-zone identification
- 2.4 GHz vs 5 GHz comparison
- Channel overlap analysis
- Roaming / dominant AP analysis
- Educational RF analysis
- Home network optimization

## Planned Improvements

Future development may include:

- Richer live-map defaults shared with the PNG generation dialog.
- More advanced RF statistics and quality indicators.
- Better scan diagnostics and troubleshooting guidance.
- Configurable AP grouping rules beyond the current automatic grouping.
- Optional project/session settings file.
- More performance tuning for very large surveys.
- Internal floorplan annotation tools.

## Project Philosophy

Most professional Wi-Fi survey tools are expensive, closed-source, and difficult to customize.

This project explores how far a transparent Python-based solution can go while remaining understandable and adaptable.

The goal is not only generating good-looking heatmaps, but understanding the underlying RF behavior and scan reliability challenges.

## Author

Davide Marchi

Experimental Wi-Fi heatmapping and RF visualization project focused on real-world environments and practical wireless analysis.
