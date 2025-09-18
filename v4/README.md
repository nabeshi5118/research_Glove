# Version 4 – Integrated Pressure & IMU Visualizer

A real-time UDP viewer that integrates both the pressure matrix visualization and IMU-based posture rendering for the G-CU.

---

## Overview

- Receives sensor data via **UDP**  
- **Left pane**: 11×11 pressure matrix heatmap  
- **Top-right pane**: 3D STL model visualization using the **Madgwick filter**  
- **Bottom-right pane**: Circular **bubble level** indicating roll and pitch  

---

## New Features in v4

- Expanded sensor grid from 10×9 to **11×11**  
- **Dynamic sampling period** adjustment based on actual measurement interval  
- Toggle for enabling/disabling the **magnetometer**  
- **Median-based offset correction** and baseline mV reference setting  
- CSV logging for both **raw** and **corrected** data  
- Real-time **color scale adjustment** via min/max spinboxes  
- Refactored layout using Qt Splitter for better flexibility  
- Added circular **Bubble Level Widget**

(Reference: README from v3)

---

## Status

✅ Currently under active maintenance and development  
📌 Previous versions (v1–v3) are retained for reference  

---

## Requirements

- Python 3.8 or higher  
- Required libraries:  

    ```txt  
    numpy
    pyqtgraph
    PyQt5
    ahrs
    numpy-stl
    ```  

- Installation example:  

    ```bash
    pip install numpy pyqtgraph PyQt5 ahrs numpy-stl PyOpenGL
    ```

---

## Usage

```bash  
python demo_armband_v4.py  
```

- Opens a UDP socket on port 31415 and waits for G-CU packets  
- Controlled via **Record**, **Offset**, and **Start/Stop** buttons  

---

## Notes

- CSV logs are saved under the `log/` directory with a timestamp  
- Enable offset correction **before starting** to learn from the first N frames  
- `BubbleLevelWidget` uses **QPainter** to render roll/pitch  
- To disable magnetometer, set `USING_MAGNET = False` in the source  
- Use **Ctrl-C** to exit gracefully  
