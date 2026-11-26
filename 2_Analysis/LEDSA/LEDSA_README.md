> **Superseded.** This file describes the earlier, simplified geometry (cameras on the pane at x = 0, strips
> 0-2.5 m). The evaluation in this repository uses the camera positions of the test log with `pane_distance`
> (`setup/ledsa_h1_positions.csv`) and the strip ends in `setup/ledsa_h1_led_strips.csv`; see `METHODS.md`.
> Kept as the record of the earlier documentation. The camera ids per position in section 1.2 apply to
> Hep_220_S1_R1-R3 only (R4: upper positions only; other tests: `runs/<run>/<pos>_<cam>/`); "Hep_200" in section 5 means Hep_220; section 5 refers to an earlier evaluation (current exclusions: METHODS.md
> section 4.6). The floor plan next to
> this file labels the positions F1t/F1b (top/bottom) instead of F1U/F1L.

# README: LEDSA Camera and LED Strip Positions

This document provides a overview of the spatial configuration for the LEDSA system, including camera coordinates and LED strip placements as defined in the floorplan.

---

## 1. Camera Positions
The cameras are placed at different heights ($Z$-coordinates) across rooms **F1**, **F2**, and **F3**, as well as the corridor area (**L**). 

### 1.1 Vertical Mapping
Based on the provided dataset, the following translation for vertical positions is used:
* **U** = **Upper** (German: *O: oben*)
* **L** = **Lower** (German: *U: unten*)

### 1.2 Room-Based Cameras
| Position ID | X | X (glass pane) | Y | Z (Height) | Setup ID |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **F1U** (Upper) | -0.232 | 0.0 | 2.050 | 1.958 | J3 |
| **F1L** (Lower) | -0.058 | 0.0 | 2.060 | 1.063 | C2 |
| **F2U** (Upper) | -0.260 | 0.0 | 6.982 | 1.944 | J2 |
| **F2L** (Lower) | -0.177 | 0.0 | 6.982 | 0.888 | C3 |
| **F3U** (Upper) | -0.243 | 0.0 | 12.527 | 2.008 | J1 |
| **F3L** (Lower) | -0.181 | 0.0 | 12.527 | 1.053 | C1 |

### 1.3 Corridor (Long)
| Position ID | X | Y | Z (Height) | Setup ID |
| :--- | :--- | :--- | :--- | :--- |
| **L1** | 0.813 | 8.104 | 0.686 | J4 |
| **L2** | 0.256 | 13.607 | 0.715 | N1 |

---

## 2. LED Strip Configurations
LED strips are mounted vertically. The $Z$-coordinates indicate the strip's span from the bottom to the top.

The following table provides the exact spatial coordinates for the top and bottom of each LED strip.

| ID | Color | Position Top (X Y Z) | Position Bottom (X Y Z) | Origin |
| :--- | :--- | :--- | :--- | :--- |
| **LED F1** | R | 4.162 3.464 2.5 | 4.162 3.464 0.0 | BCL |
| **LED F1** | G | 4.126 3.317 2.5 | 4.126 3.317 0.0 | Jülich |
| **LED F1** | B | 4.126 3.291 2.5 | 4.126 3.291 0.0 | Jülich |
| **LED F1L** | G | 1.49 0 2.5 | 1.49 0 0.0 | BCL |
| **LED F2** | R | 4.52 7.37 2.5 | 4.52 7.37 0.0 | BCL |
| **LED F2** | G | 4.478 7.232 2.5 | 4.478 7.232 0.0 | Jülich |
| **LED F2** | B | 4.478 7.21 2.5 | 4.478 7.21 0.0 | Jülich |
| **LED F2L** | G | 0.732 4.44 2.5 | 0.732 4.44 0.0 | BCL |
| **LED F3** | R | 4.472 11.956 2.5 | 4.472 11.956 0.0 | Jülich |
| **LED F3** | G | 4.472 11.928 2.5 | 4.472 11.928 0.0 | Jülich |
| **LED F3** | B | 4.472 11.904 2.5 | 4.472 11.904 0.0 | Jülich |

---

## 3. Floorplan Reference

* **Sightlines:** Green dashed lines indicate the direct line-of-sight from camera positions to their targets.
* **Labels:** **F1U/L**, **F2U/L**, and **F3U/L** on the map correspond to the physical mounting points.
* **LED Types:** The map distinguishes between **LED RGB** and **LED G** (Green) installations.

---

## 4. Coordinate System & Units
* **Units:** All spatial coordinates ($X, Y, Z$) are in **meters (m)**.
* **Z-Axis:** Height above the floor level.

---

## 5. Notes to specific experiment repititions

* **Hep_160_S2_R3:** Camera F1L bigger deviation in comparison to other Repititons.
* **Hep_200_S1_R1:** Camera F2L extinction coefficients end at about 0.2 1/m.
* **Hep_200_S1_R2/3:** Camera F2L extinction coefficients not comparible. R2 only repitition comparible to other rooms.
