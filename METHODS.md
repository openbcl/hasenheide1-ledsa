# Methods: LEDSA 0.13.0 evaluation of the Hasenheide 1 tests (C7-UVCB heptane mixture)

This document describes, step by step, how the extinction-coefficient results in this repository were obtained:
which images and settings went into LEDSA, which LEDSA steps were run with which parameters, where the pipeline
deviates from a plain LEDSA run, and how the LEDSA output was post-processed into the reported profiles and
LEM comparisons. It is written for readers who know LEDSA but not this pipeline. Paths are relative to the
repository root unless they start with `runs/`, `setup/`, `inventory/`, `plots/`, `tools/`, `checks/`, `tests/` or
`fireplot/` or `stacked_results/`, or are bare script names `ledsa_h1_*.py`, which are relative to
`2_Analysis/LEDSA/`; `analysis/…` is relative to a LEDSA working folder, `ledsa/…` to the LEDSA 0.13.0 source tree. Code comments and some column values in the repository are in German; the
terms needed to read them are explained where they occur.

Contents: 1 Scope · 2 Software · 3 Inputs · 4 Processing chain · 5 Post-processing · 6 Result files ·
7 Reproduction · 8 Known deviations and limitations · 9 Long-axis camera (N1)

---

## 1. Scope

### 1.1 Tests and names

Fourteen pool-fire tests with the C7-UVCB heptane mixture (three series) are evaluated. In running text and tables tests are named
`<series>_R<n>`, numbered in the order run within the series, as in the reproduction package of the companion
article. All file and folder names, and the `run` column of every result table, keep the test-log id. The mapping
is in the root file `runs.csv` (columns `run, name, series, setup, date, t0_local`); `setup` is the instrument
configuration (S1–S4) of the test log.

| Name | Test-log id (`run`) | Pan (square side) / fuel mass | Setup |
|---|---|---|---|
| Hep_220_300_R1 … R4 | Hep_220_S1_R1 … R4 | 220 mm / 300 g | S1 |
| Hep_160_150_R1 … R3 | Hep_160_S1_R1 … R3 | 160 mm / 150 g | S1 |
| Hep_160_075_R1 … R3 | Hep_160_S2_R1 … R3 | 160 mm / 75 g | S2 |
| Hep_160_075_R4, R5 | Hep_160_S3_R1, R2 | 160 mm / 75 g | S3 |
| Hep_160_075_R6, R7 | Hep_160_S4_R1, R2 | 160 mm / 75 g | S4 |

The grouping into the three series is the regular expression table `CONFIGS` in `ledsa_h1_profiles.py`.

### 1.2 Rooms, camera positions and cameras

Rooms F1 (fire room), F2 and F3. Only the **F positions** are evaluated: each camera looks from the corridor
through a glass pane in a core hole of the corridor wall across the room onto the LED strips on the opposite wall.
Per room there is a lower (`<room>L`) and an upper (`<room>U`) position. Cameras: C1–C3 (BCL; C1 Canon EOS R50,
C2/C3 Canon EOS M50, CR3) and J1–J3 (Jülich; J1 Canon EOS 80D, CR2; J2/J3 Canon EOS R7, CR3); models and serial
numbers per series are in `setup/ledsa_h1_series.csv`. J1–J3 are cameras, not strips. The allocation changes from
test to test (`setup/ledsa_h1_series.csv`, columns `cam`, `position`):

| Test | F1 lower / upper | F2 lower / upper | F3 lower / upper |
|---|---|---|---|
| Hep_220_300_R1, R2 | C2 / J3 | C3 / J2 | C1 / J1 |
| Hep_220_300_R3 | C2 / J3 | C3 (excluded, §4.6) / J2 | C1 / J1 |
| Hep_220_300_R4 | – / J3 | – / J2 | – / J1 |
| Hep_160_150_R1, R2 | – / J3 | C1 / J2 | – / J1 |
| Hep_160_150_R3 | – / J3 | C1 / – | – / J1 |
| Hep_160_075_R1 | – / J3 | C1 (excluded; side variant, §4.6) / J2 | – / J1 |
| Hep_160_075_R2 | C2 / J3 | C1 / J2 | C3 / J1 |
| Hep_160_075_R3 | C2 (excluded) / J3 | C1 / J2 | C3 / J1 |
| Hep_160_075_R4 | – | – / C1 | C3 / – |
| Hep_160_075_R5 | C2 / – | – / C1 | C3 / – |
| Hep_160_075_R6, R7 | – | C2 / C1 | – |

This gives 57 image series (test × camera) and 37 test × room combinations. One series (Hep_160_075_R3 C2) was read
out but not inverted, so 56 series have an inversion. `photo_handover/README.md` lists C1 in Hep_220_300_R4 and C2
in Hep_160_075_R4 as series that are missing although the test log names them.

### 1.3 LED strips and channels

Each room has three vertical strips: red, green, blue (`setup/ledsa_h1_led_strips.csv`). LEDSA LED array
*a* = strip of colour *a* = camera channel *a* (0 red, 1 green, 2 blue). Only the combination channel *a* /
array *a* is used downstream, although LEDSA writes all nine channel × array combinations.

| Room | Array 0 (red) | Array 1 (green) | Array 2 (blue) |
|---|---|---|---|
| F1 | LED 1, BCL, 150 LEDs | LED 1.1, Jülich, 144 LEDs | LED 1.2, Jülich, 144 LEDs |
| F2 | LED 3, BCL, 150 LEDs | LED 3.1, Jülich, 144 LEDs | LED 3.2, Jülich, 144 LEDs |
| F3 | LED 5.1, Jülich, 144 LEDs | LED 5.2, Jülich, 144 LEDs | LED 5.3, Jülich, 144 LEDs |

LED counts per strip are `N_EXPECTED` in `ledsa_h1_s1scan.py` and `n_leds` in `setup/ledsa_h1_strip_windows.csv`.
Strip x/y and end heights: §3.3. Wavelengths used for the Widmann correction: 628 / 521 / 468 nm for channels
0 / 1 / 2 (`LAM` in `ledsa_h1_stage0.py`; as set in the code, source not in this repository; §5 step 4).

### 1.4 Not included

- The other tests of the campaign (ethanol tests, most with artificial glycol or white-oil fog; isopropanol; PUR): `ledsa_h1_setup.py` keeps only runs whose
  name starts with `Hep_`.
- The positions with a long line of sight along the building (L1, L2) and the cameras used only there:
  `ledsa_h1_setup.py` keeps only positions starting with `F`. Camera N1 at L2 is evaluated separately in
  `2_Analysis/LEDSA/long_axis/` (§9).
- The raw images, the per-image LEDSA readout `runs/*/*/analysis/channel*/` (this folder also holds LEDSA's binary
  intermediate data `all_parameters.h5`, so `.gitignore` covers it through the `channel*/` entry), the per-image
  tracked positions, the LED-search control images, LEDSA's diagnostic plots `runs/*/*/plots/` and the chain logs in
  `runs/_logs/` (these five are listed in `.gitignore`), and the earlier evaluations used for comparison in §6.4: of these, `.gitignore` lists only the
  0.10.0 stacks (`stacked_results/`); the earlier 0.13.0 evaluation lies outside the repository tree
  (`H1_PRIOR0130`, §2). The k files in `runs/` are in the repository as raw LEDSA output (unmasked, §6.3). The step
  logs of the LEDSA runs (console output redirected by the chain scripts into each working folder: `s1_log.txt`, `s2_log.txt`, `s3_log.txt`, `coord_log.txt`, `a_log.txt`, `as_log.txt`, `as_refresh_log.txt`) are
  in the repository.

---

## 2. Software and environments

| Environment | Used for | Requirements |
|---|---|---|
| LEDSA environment (conda) | LEDSA itself (`python -m ledsa …`) and the scripts that import LEDSA or read raw images in this environment (`ledsa_h1_config.py`, `ledsa_h1_s1scan.py`, `ledsa_h1_probe.py`, `ledsa_h1_track.py`; `ledsa_h1_noise.py` reads the RAW files with rawpy) | `env/requirements-ledsa-env.txt` (numpy 1.26.4) |
| Analysis environment (venv, Python 3.12) | `ledsa_h1_setup.py`, `ledsa_h1_ledz.py`, `ledsa_h1_mask.py`, `ledsa_h1_stage0.py`, `ledsa_h1_profiles.py`, `ledsa_h1_stage4.py`, `checks/*.py`, `tools/stage2_check.py`, `tools/stage2_order.py`, `tools/stage2_trackcheck.py`, `tools/plot_drift.py`; also the camera-movement scripts `ledsa_h1_drift.py`, `ledsa_h1_drift_fine.py` and `tools/drift_regions.py`, which read the RAW files here with rawpy | `env/requirements-analysis.txt` (numpy 2.5.2, pandas 3.0.5, matplotlib 3.11.1, scipy 1.18.0, rawpy 0.27.0) |

The assignment follows the call line in each script's docstring ("hh2-venv" = analysis environment, "Conda-Env
ledsa" = LEDSA environment). `ledsa_h1_mask.py` names both; the chain (`tools/run_room.sh`) runs it, like
`ledsa_h1_ledz.py`, with the analysis environment. `tools/juelich_exif.py`, `tools/juelich_list.py` and `checks/check_c1.py` name no
environment. Details, Python versions and the LaTeX requirement: `env/README.md`.

**LEDSA version.** LEDSA 0.13.0 was run from a source export (`pyproject.toml`: `version = "0.13.0"`), put on
`PYTHONPATH` by `tools/env.sh` (function `ledsa_env`). `ledsa_env` aborts unless `import ledsa` resolves inside
the export, because the conda environment also contains an older LEDSA installation. The headers of all
extinction-coefficient files say "LEDSA 0.9.4": LEDSA writes `importlib.metadata.version("ledsa")`, i.e. the
metadata of that older installation, not the version of the code that ran. The version that ran is 0.13.0.

**Shell scripts and environment variables.** The chains in `tools/*.sh` are Bash scripts (Git Bash on Windows) that
`source tools/env.sh`. Variables (defaults in parentheses):

| Variable | Read by | Meaning |
|---|---|---|
| `LEDSA_EXPORT` | `tools/env.sh` | LEDSA 0.13.0 source tree (`%LOCALAPPDATA%\ledsa_v0130`) |
| `LEDSA_PY` | `tools/env.sh` | Python of the LEDSA environment (`%USERPROFILE%\.conda\envs\ledsa\python.exe`) |
| `HH2_PY` | `tools/env.sh` | Python of the analysis environment (`%LOCALAPPDATA%\hh2_analysis_venv\Scripts\python.exe`) |
| `H1_LEDSA_RUNS` | `tools/env.sh`, `ledsa_h1_config.py` (`RUNS`); set by `tools/stage0_voll.sh` | LEDSA working folders (`2_Analysis/LEDSA/runs`) |
| `H1_IMAGES_ROOT` | `ledsa_h1_paths.py` (`img_path`, used by every script that reads raw images or writes `config.ini`), `tools/juelich_exif.py`, `tools/juelich_list.py` | root of the raw-image tree (no default; not in this repository) |
| `H2_LEDSA_DIR` | `tools/juelich_exif.py` | folder holding the EXIF reader module `rawexif` of the Hasenheide 2 evaluation (no default; not in this repository) |
| `H1_FDS_ROOT` | `checks/fds_sens_profiles.py` | FDS output (no default; not in this repository) |
| `H1_PRIOR0130` | `checks/compare_prior.py` | earlier independent LEDSA 0.13.0 evaluation (no default; not in this repository) |
| `H1_PRIOR0100` | `checks/compare_prior.py`, `checks/decompose_prior0100.py`, `ledsa_h1_stage0.py` | earlier LEDSA 0.10.0 stacks (`2_Analysis/LEDSA/stacked_results`; not in this repository) |
| `H1_VARIANT` | `ledsa_h1_config.py`, `tools/run_room.sh` | side variant (only `mitC1`, §4.6); must be unset for the main evaluation (`tools/stage3_rerun.sh` unsets it for its main loop) |
| `H1_LEDSA_FARFIELD`, `H1_NUM_SKIP_IMGS` | `ledsa_h1_config.py` | test overrides of `farfield_distances` (`150 300`) and `num_skip_imgs` (series table); not set by any chain script |
| `H1_WINDOWS_PART` | `ledsa_h1_s1scan.py` | part number `<i>`: the strip windows are written to `setup/ledsa_h1_strip_windows_part<i>.csv` instead of the main table. `tools/scan_all.sh` sets it, so it was set during the LED search of the main evaluation (§7.2) |

**Path placeholders.** Paths outside the repository are written as placeholders. Column `folder_w` of
`setup/ledsa_h1_series.csv`, the `config.ini` files in `runs/` and `tests/`, `analysis/corrupted_images.csv`, 14
`s3_log.txt`, `inventory/ledsa_h1_bad_images.csv` and the header of `inventory/ledsa_h1_juelich_abgeschnitten.csv`
give the image folders as `<H1_IMAGES_ROOT>\…`;
`ledsa_h1_paths.img_path` replaces the placeholder with `H1_IMAGES_ROOT` when a script reads images or writes a
`config.ini` (`ledsa_h1_setup.py` writes the placeholder itself). The step logs give the LEDSA source tree as
`<LEDSA_EXPORT>`, and `config_stacked.ini`, `time_alignment_led_array_*.txt` and one `as_log.txt` (`runs/Hep_160_S2_R1/stacked_F2_mitC1/`) give the
root of the working folders of the original runs as `<H1_LEDSA_RUNS>` (§8.9). These path prefixes were
replaced after the runs; apart from them, these files are the original output (in addition, the header
comment of the 16 `zerl_*/config_stacked.ini` was renamed as written by `checks/decompose_prior0100.py`, and some
note texts in `setup/` were shortened). Files written by a re-run contain the real paths again.

**Figures** are drawn with the vendored package `2_Analysis/LEDSA/fireplot/` (from
brandschutzconsult/fire-preprint-template, see `fireplot/ORIGIN.txt`). It renders text with LaTeX
(`text.usetex`), so a LaTeX installation is needed (`env/README.md`).

---

## 3. Inputs

### 3.1 Raw images and the series table

The raw images (RAW, 14 bit) are not in the repository. `setup/ledsa_h1_series.csv` defines each of the 57 series:
folder (`folder_w`), file name pattern (`name_string`), first and last image number (`first_id`, `last_id`,
4-digit file-name counters with overflow at 9999), image count, LED-search reference image (`ref_s1_id`, §4.2;
also a file-name counter),
`num_skip_imgs`, exposure, camera model and serial number (written as a float, e.g. `363034002727.0`). BCL series and the J3 series of 2025-12-09 are in
`1_Measurements/<run>/3_LEDSA/<series folder>/` of the image tree. The other Jülich series are cut out of the
day series in `2_juelichMeasurements/<date>/camJ<n>/` of the image tree. The handed-over image set is described in
`photo_handover/README.md` (German). The Jülich day series are not part of that set.

The table was generated by `ledsa_h1_setup.py` from `photo_handover/serien.csv`, `positionen.csv`,
`led_streifen.csv`, the EXIF inventories `inventory/h1_exif_weitergabe.csv.gz` (handed-over images) and
`inventory/h1_exif_juelich.csv.gz` (Jülich day series; written uncompressed by `tools/juelich_exif.py` from the file
list `inventory/h1_files_juelich.tsv.gz`, which `tools/juelich_list.py` wrote; the file list was gzipped before `tools/juelich_exif.py`
read it and its output before `ledsa_h1_setup.py` read it, according to the script comments; `ledsa_h1_setup.py` does not read the file list), and
`1_Measurements/<run>/1_Processed_data/<run>_events.txt`.
Rules in `ledsa_h1_setup.py`:

- Series = contiguous block of images that contains the time zero of the test (§3.2; the full minute, not the
  ignition) or, if none does, the block nearest to it (`block(g, z)`), ordered by EXIF time (not by file name,
  because counters overflow). A gap of more than 120 s (`GAP_SPLIT_S`) splits blocks.
- Jülich day series: images within −1200…+2700 s of the time zero, at least 50 images. J3 on 2025-12-09 is taken
  from the complete `FZJ` copy instead of the day series, because some day-series files are truncated.
  `inventory/ledsa_h1_juelich_abgeschnitten.csv` lists 50 truncated files of all Jülich cameras and days
  (2025-12-08: 37, 2025-12-09: 11, 2025-12-10: 2); 3 of them are J3 files of 2025-12-09.
- Thinning: series with a median interval below 1.5 s get `num_skip_imgs = 4` (every 5th image). This applies to
  the nine Jülich series of 2025-12-08 (Hep_220_300_R1–R3, median interval 0.99 s). All other series are used in
  full: BCL 5.00 s, Jülich on 2025-12-09/10 3.96–4.00 s, except Hep_220_300_R4 J1 with 3.45 s (`dt_median_s`).
  These committed values are affected by the SubSec error of §8.1: regenerated in memory with the current script,
  Hep_220_300_R4 J1 gives 3.39 s, and three Jülich series change from 3.96 to 3.97 s; no series crosses the 1.5-s
  thinning threshold.

The table in the repository is the one the LEDSA runs used. The current script would produce a slightly different
table (§8.1).

### 3.2 Time base

- **Time zero** of every test is the full minute in `runs.csv` (`t0_local`), identical to `start_time` in
  `setup/ledsa_h1_runs.csv` and to "Referenzzeit (gerundet)" in `<run>_events.txt`. The measurement data
  (`<run>_processed.csv`, column `Time (s)`, 1 s steps from −60 s) use the same zero.
- Ignition (`ignition_s`), flame-out (`fire_out_s`) and start of ventilation (`ventilation_s`) in
  `setup/ledsa_h1_runs.csv` come from `_events.txt` ("Zündung", "Feuer aus", "Beginn Lüftung"). Ignition is
  +0.517…+2.76 s after time zero. Ventilation starts at 900.2–901.6 s (Hep_160_075) and 1200.3–1201.9 s
  (Hep_160_150, Hep_220_300).
- LEDSA time: `config.ini` has `start_time` = time zero, `exif_time_infront_real_time = 0` and no time-reference
  image (`time_ref_img_* = None`). LEDSA's `Experiment_Time` is therefore EXIF time minus time zero.
- **No camera clock offset is applied.** A synchronisation of the camera clocks is not documented.
  `photo_handover/README.md` reports spot checks of camera on/off events against first/last images that differ by
  2.5–14 s, with no reliable offset following from them.
- Stacked inversions take their time axis from the first camera in `config_stacked.ini`, which is always the lower
  camera, reduced to the times at which the other camera has an image within `time_sync_tolerance = 3` s
  (`_intersect_time_axes` in LEDSA's `StackedExtinctionCoefficients.py`); the other camera contributes that nearest
  image. Example: Hep_220_300_R3 `stacked_F3` has 447 times, its lower camera C1 510.

### 3.3 Geometry

Coordinates in m. Origin at the marked inner corner of F1 at the corridor wall, x across the building towards the
windows, y along the building towards F3, z above floor (`photo_handover/README.md`).

**Cameras** (`setup/ledsa_h1_positions.csv`, test-log values; the glass pane is at x = 0, so cameras have x < 0):

| Position | x | y | z | `pane_distance` (range over LEDs) |
|---|---|---|---|---|
| F1U | −0.232 | 2.050 | 1.958 | 0.252 (0.241–0.264) |
| F1L | −0.058 | 2.060 | 1.063 | 0.062 (0.060–0.064) |
| F2U | −0.260 | 6.982 | 1.944 | 0.270 (0.260–0.280) |
| F2L | −0.177 | 6.982 | 0.888 | 0.182 (0.177–0.188) |
| F3U | −0.243 | 12.527 | 2.008 | 0.254 (0.245–0.264) |
| F3L | −0.181 | 12.527 | 1.053 | 0.186 (0.182–0.191) |

`pane_distance` (LEDSA ≥ 0.13) is the smoke-free part of each line of sight between camera and pane. The range
columns `pane_distance_min_m`/`_max_m` (taken from `photo_handover/positionen.csv`) correspond within about 1 mm
to a flat pane at x = 0 (the length from the camera to x = 0 along
the lines of sight to the LEDs, recomputed from the corrected LED coordinates: e.g. F1U 0.2412–0.2636 m). LEDSA takes
one value per camera (the middle of the range) for every line of sight (§8.7).

**LED strips** (`setup/ledsa_h1_led_strips.csv`): x/y per strip from the test log; tops at z = 2.535 m. Bottoms:
BCL strips 0.055 m (test log); Jülich strips 0.1517 m = 2.535 − 143/60 m, i.e. 144 LEDs at 60 LEDs/m counted down
from the top LED (`JUELICH_N_LED`, `JUELICH_LED_PER_M` in `ledsa_h1_setup.py`). The test log gives 0.100 m for the
Jülich bottom. The code comment states that this value is inconsistent with the images (lowest LED seen at about
0.13–0.15 m). `photo_handover/led_streifen.csv` and the handed-over LEDSA templates still contain 0.100 m.

**Heights of the individual LEDs.** LEDSA `-coord` places every LED by linear interpolation of its pixel position
between the two end LEDs (affine, no perspective). `ledsa_h1_ledz.py` replaces this, after `-coord` and before
`-s3`/`-a`, by equal spacing along the strip by LED index:
`z = z_top − (skip_top + k)·(z_top − z_bottom)/(n_leds − 1)`, with x, y = strip x, y. Here *k* is the index counted
from the top LED found, and gaps (LEDs not found) are detected from pixel spacing larger than 1.5× the local median
spacing. The script aborts unless the last index *k* equals `n_leds − 1 − skip_top − skip_bottom` (all `skip_*` are
0, §4.2). The corrected file is
`analysis/led_search_areas_with_coordinates.csv` (header mark `ledsa_h1_ledz.py`); LEDSA's original is kept as
`analysis/led_search_areas_with_coordinates_ledsa.csv`. On the BCL strips, where only the perspective changes, the
correction is −44.4…+1.5 mm for lower cameras and −1.1…+46.1 mm for upper cameras (corrected minus LEDSA, computed
from the two files). On the Jülich strips the change also includes the new bottom end.

**Layers:** 25 layers over `domain_bounds = 0.0 2.535` m, thickness 0.1014 m, centres 0.0507 + 0.1014·*j* m
(*j* = 0…24).

### 3.4 Transmissometer data (LEM, SICK)

`1_Measurements/<run>/1_Processed_data/<run>_processed.csv`. Columns `Extinction LEM_<n>_<room>_<z> (1/m)` and, for
SICK, `Extinction SICK_<room>_<z> IR (1/m)_corr`, 1 s steps. A column is used only if it has at least 100 values
(`LEM_MIN_N`, `ledsa_h1_stage0.py`). LEM heights: F1 and F3 2.3 m; F2 1.5 and 2.3 m (setups S1, S2), 1.9 and 2.3 m
(S3), 2.1 and 2.3 m (S4). The F1 LEM column is empty in Hep_220_300_R1 and R4. One SICK per test at 2.3 m (room by setup: F2 in S1 and
S3, F1 in S2, F3 in S4); its column is empty in Hep_160_150_R3 and in all four Hep_220_300 tests. The SICK column
is used only as a marker in the profile figure and in `inventory/ledsa_h1_profiles_points.csv`.

---

## 4. Processing chain

### 4.0 Overview

| Stage | What | Command (from `2_Analysis/LEDSA/`) | Needs images |
|---|---|---|---|
| A | setup tables | `python ledsa_h1_setup.py` (analysis env.) | no (EXIF inventories) |
| 0 | tests (thinning, tracking, comparison with an earlier stack) | `ledsa_h1_stage0.py test1/test2`, `tools/stage0_voll.sh` | yes |
| 1 | LED search windows | `tools/scan_all.sh <i> <N>` → `ledsa_h1_s1scan.py <run> <cam>`; manual check | yes |
| 2 | readout per camera (+ tracking for 12 series) | `tools/stage2.sh` → `tools/run_cam.sh <run> <cam>`; `tools/stage2_track*.sh` → `ledsa_h1_track.py` | yes |
| 3 | reference images, noise, inversions, masks | `tools/stage3_rerun.sh` → `tools/run_room.sh <run> <room>` | yes (readout) |
| 4 | saturation, profiles, LEM comparison | `tools/post_rerun.sh` → `ledsa_h1_stage4.py sat`, `ledsa_h1_profiles.py all`, `ledsa_h1_stage4.py lem`, `checks/…` | only `sat` (per-image readout) |

Status markers in `runs/`: `<pos>_<cam>/stage2_s3_ok` (readout checked), `stage2_track_ok` (tracking run completed; not the result of the tracking check),
`runs/<run>/stage3r1_<room>_ok` (final inversion of that room; `ledsa_h1_profiles.py` and `ledsa_h1_stage4.py lem`
refuse to run without it). The older markers `stage3_<room>_ok` belong to a first pass before the LED-height
correction of §3.3. Only the old first-pass script `tools/stage3.sh` sets and reads them (it skips a room whose
marker exists); none of the scripts of the result chain (§7.2) reads them. All these markers are in the
repository, and the chain scripts skip work whose marker exists (§7.2).

### 4.1 Stage 0: tests

`ledsa_h1_stage0.py` holds the shared post-processing functions (§5) and two comparisons. Its own
`paper_series` is an earlier form of §5: it nulls at the gridded value at t = 0 (if that is not finite, at the mean
of the first 10 grid values, −30…−21 s) instead of §5 step 3; Widmann correction and sigma clip are as in §5. It is
used by the stage-0 tests and (through `room_series`) by `checks/check_pedestal_k.py` and `checks/check_j2.py`.
`test1 <run> <room>` compares a new stack
(`farbg_sum_col_val`, `sum_col_val`) with an earlier LEDSA 0.10.0 stack and the LEM. `test2 <run> <room> <folder>`
compares two inversions of the same stack: raw per layer (on the common times 0 < t < ventilation, count `n_t`), and
post-processed at the LEM heights. The docstring describes `test2` as thinned (`runs/`) against full (`<folder>`);
`tools/stage0_voll.sh <run> <room> <lower folder> <upper folder>` builds the full-series counterpart in
`runs/_stage0_voll/` (gitignored, not in the repository). It only copies the lower camera's folder from `runs/`,
writes the analysis configurations (same reference images by file name as in the thinned variant) and runs `-a`
and `-as`. The full (unthinned) readout of the upper camera must already exist in
`runs/_stage0_voll/<run>/<upper folder>`; how it was created is not documented in the repository. The outputs are `inventory/ledsa_h1_stage0_*.csv` (German column names: §6). They are records of the stage-0 tests:
re-running `test1 Hep_160_S4_R1 F2` with the committed working folders (and the earlier stacks) gives slightly
different values for the new stack (ratios to the LEM up to 0.006 higher, peak times up to 5 s apart; checked
2026-11-26), so the committed table is not a reproduction target. Of the two committed
`test2` pairs, Hep_220_300_R3 F3 (stack C1 + J1, J1 thinned in `runs/`; `n_t` = 241 at the 5-s interval of the
lower camera C1 over 0 < t < 1202 s) fits a thinning test. Hep_160_075_R6 F2 cannot be one: it is a BCL stack
C2 + C1 with `num_skip_imgs` = 0 for both series, and `n_t` = 181 matches the unthinned 5-s interval over
0 < t < 900 s. What it compares is not documented (§8.12). The tests informed the settings below and are not part
of the result chain.

### 4.2 Stage 1: LED search

1. **Reference image of the LED search** (`ref_s1_id`): the last image at t ≤ −30 s (`REF_S1_T`), chosen so that
   set-up work is finished and no smoke is present; if the series has no such image, its first image
   (`ledsa_h1_setup.series_row`). The fallback applies to Hep_160_075_R1 C1 (`ref_s1_t_s` = +30.48 s) and
   Hep_160_075_R6 C2 (−29.44 s). Five series use another time (`REF_S1_T_OVERRIDE` in
   `ledsa_h1_setup.py`, chosen with `ledsa_h1_probe.py` by counting found LEDs per image):

   | Series | Target time | Reason (code comment) |
   |---|---|---|
   | Hep_160_150_R2 J3 | −100 s | persons in front of the strip from about −80 s |
   | Hep_160_075_R3 J3 | −3 s | LEDs partly covered from −111 to −15 s |
   | Hep_220_300_R4 J3 | −60 s | lower strip ends covered at −33 s |
   | Hep_160_075_R3 C2 | +200 s | unstable before ignition (camera later excluded) |
   | Hep_220_300_R1 J2 | +1600 s | double/smeared LED images until about +900 s |

2. **Strip windows** (`ledsa_h1_s1scan.py`): runs LEDSA's own `find_search_areas` (the function behind `-s1`,
   radius 10 px) on the reference image for the percentiles 99.875 … 99.99. It chains the hits into strips (neighbours
   ≤ 60 px along and ≤ 8 px across the strip; chains of at least 50 hits) and assigns each chain the colour of the
   channel with the largest median, over the chain's hits, of the box sums (`colour_of`). It proposes the lowest-ranked percentile with exactly one red, green and blue chain, ranked
   by deviation from the expected LED count plus number of stray hits. Each strip gets a window: a quadratic fit of
   column over row with a half width of 9 px, padded by 25 px. It also checks the camera position in the first and
   last image. Output: `setup/ledsa_h1_strip_windows.csv` (via `tools/scan_all.sh`: part files
   `setup/ledsa_h1_strip_windows_part<i>.csv`, merged by hand, §7.2) and a control image `s1scan.png` (not in the
   repository).
   After inspection, `status` was set by hand to `geprueft` (checked). In the committed table all 171 strips
   (57 series × 3) are `geprueft`, all with `n_found = n_leds` and `skip_top = skip_bottom = 0`. The chosen
   percentile per series is between 99.875 and 99.98.

3. **LEDSA configuration and steps** (`tools/run_cam.sh <run> <cam>`, LEDSA environment, working folder
   `runs/<run>/<pos>_<cam>/`):

   ```bash
   python ledsa_h1_config.py config <run> <cam>   # writes config.ini (ConfigData)
   python -m ledsa -s1
   python ledsa_h1_config.py edges <run> <cam>    # end LEDs + 3D end points into config.ini
   python -m ledsa -s2
   python -m ledsa -coord
   python ledsa_h1_ledz.py <run> <cam>            # LED heights by index (analysis env.), §3.3
   python -m ledsa -s3_fast -rgb
   ```

   `config.ini` values set by `ledsa_h1_config.build`: `img_directory`/`img_name_string` from the series table,
   `num_img_overflow = 9999`, `first/last_img_experiment_id` and `first/last_img_analysis_id` = first/last image,
   `num_skip_imgs` from the series table, `img_rotation = 0`, `date`, `start_time` = time zero,
   `exif_time_infront_real_time = 0`, `ref_img_id = ref_s1_id`, `search_area_radius = 10`,
   `pixel_value_percentile` from the strip window, `channel = all`, `max_num_leds = 1300`, `num_arrays = 3`,
   `farfield_distances = 150 300`, `num_cores = 8`.

   `edges` takes, per strip window, the top and bottom LED found (smallest/largest image row among the LEDs whose
   column lies within the half width of the fitted curve). It writes their ids to `led_array_edge_indices` and the
   strip end coordinates to `led_array_edge_coordinates`. It aborts if found + skipped LEDs exceed the strip's LED
   count. All committed arrays have 150/144/144 LEDs (F1, F2) or 144/144/144 (F3). The exception is
   Hep_160_150_R2 J1, array 0, with 143: LEDSA `-s2` left one LED unmatched near the bottom, and `ledsa_h1_ledz.py`
   detects the gap and keeps the index count correct.

### 4.3 Stage 2: readout, camera movement and tracking

**Readout.** `-s3_fast -rgb` reads all three channels without LED fits and with the far-field pedestal
(`farfield_distances = 150 300` px). The per-image files `analysis/channel<c>/<id>_led_positions.csv` (not in the
repository) have the header `# id,line,sum_col_value,average_col_value,max_col_value,farbg_sum_col_value,
farbg_pedestal` (`ledsa_h1_mask.py`, `COLS`, uses short names for the same columns; the property names in the k
files and configs are `sum_col_val` and `farbg_sum_col_val`). `tools/stage2.sh` runs `run_cam.sh` for all series. Before each
series it does a read test of one image, and afterwards it runs `tools/stage2_check.py`. That check accepts a
readout only if each channel has as many files as analysed images minus the images LEDSA skipped. Every entry of
`analysis/corrupted_images.csv` (also metadata-read errors of images outside the analysed set) must be listed in
`inventory/ledsa_h1_juelich_abgeschnitten.csv` (Jülich RAW files truncated at MiB
boundaries). LEDSA's list of skipped files is `analysis/corrupted_images.csv` per camera.

**Camera movement surveys.** Two scripts measure the image shift against the LED-search reference image on a sample
of images (reference image + k × 100 s, plus first and last image), from the raw images, in the analysis environment:

- coarse: `ledsa_h1_drift.py` (green Bayer plane, 2 × 2 binned, i.e. a quarter of the sensor resolution; phase
  correlation with parabolic sub-pixel fit and alias resolution) → `inventory/ledsa_h1_drift.csv`,
  `ledsa_h1_drift_summary.csv`, and the RAW files it could not read → `ledsa_h1_bad_images.csv`. According to the
  docstring of `ledsa_h1_drift_fine.py` its values lock to multiples of about 4 px, so it cannot resolve 1–2 px.
- fine: `ledsa_h1_drift_fine.py` (strip region only, half resolution, phase correlation with upsampled DFT, factor
  20; search within 0.45 LED pitch around the value of the previous image; `rand = 1` if the maximum lies on the edge
  of that circle) → `inventory/ledsa_h1_drift_fine.csv`, `ledsa_h1_drift_fine_summary.csv`.

**Tracking decision.** The header of `setup/ledsa_h1_tracking.csv` gives the rule decided on 2026-11-20: track if
the position changes by more than 1 px between −30 s and ventilation + 300 s. It was applied in two steps:

1. Coarse survey, with suspected aliases checked by hand (`ledsa_h1_probe.py`): 8 series. One of them,
   Hep_160_150_R2 J1, was revoked on 2026-11-23 (4 px in only one ambiguous survey image; tracking slipped by one LED
   pitch; fine survey max 0.45 px in the reliable images; the 770-s image shows 3.9 px there too, but with quality
   0.99 < 1 it is not counted as reliable).
2. Fine survey (2026-11-23), using only reliable images (`rand = 0` and `quality ≥ 1`, the criterion also used by
   `tools/stage2_trackcheck.py`) in the window above; "movement" = a shift magnitude above 1 px in at least 3 such
   images. Column `kat` of `inventory/ledsa_h1_drift_fine_kategorien.csv`: 16 series "A >1px", 38 "B <=1px",
   3 "C unsicher" (uncertain: most images in the window unreliable, `n_qlow` 9–10 of 15; the categorisation step
   is not archived, see §6.1). Five series were added (decided on 2026-11-23 after a steady
   shift in the fine survey): Hep_160_075_R4 C3, Hep_160_150_R1 J2, Hep_160_150_R2 J2, Hep_160_075_R3 J2,
   Hep_220_300_R3 C3.

So a "> 1 px" series in the fine survey was not tracked automatically, and the header sentence of
`setup/ledsa_h1_tracking.csv` ("series without a row: < 1 px") does not hold for all untracked series.

**Tracked series (12):** Hep_220_300_R1 J1, C2, C3; Hep_220_300_R3 J2, C3; Hep_160_150_R1 J2; Hep_160_150_R2 J2;
Hep_160_075_R2 C3; Hep_160_075_R3 C3, J2; Hep_160_075_R4 C3; Hep_160_075_R6 C1 (rows with `nachfuehren = ja`; nine
are category A, three category C). Rows with `nein`: Hep_160_150_R2 J1 (revoked, above) and Hep_220_300_R1 J2 (LED
positions taken from the clean image at +1600 s instead, §8.16).

**Not tracked although > 1 px in the fine survey** (reliable images in the window; maximum shift magnitude, number of
images > 1 px; computed from `inventory/ledsa_h1_drift_fine.csv`):

| Series | Category | Reason (documented only here) |
|---|---|---|
| J3 (F1U, fire room) in Hep_220_300_R2 8.1 px (6), Hep_160_150_R2 7.9 px (7), Hep_220_300_R3 3.6 px (4), Hep_160_150_R3 3.3 px (4), Hep_160_075_R1 2.3 px (3), Hep_220_300_R1 2.1 px (4) | A | judged as disturbances rather than drift (decided on 2026-11-23): before ventilation mostly within ±1 px with isolated outliers up to about 8 px, after ventilation ±2–3 px scatter; cause assumed to be flame light (not verified). For Hep_160_150_R2 the survey is positive along the strip in all reliable images from 1096 s (0.6–3.3 px); see the test below |
| Hep_220_300_R2 C3 1.7 px (3) | A | scatter around ±1 px |
| Hep_160_150_R3 C1 6.3 px (1), Hep_160_150_R2 C1 6.0 px (1), Hep_220_300_R4 J3 1.6 px (2), Hep_220_300_R4 J2 1.6 px (2); 1.0–1.4 px in one or two images: Hep_160_075_R2 J2, J3, C1, Hep_160_150_R1 J3, Hep_160_075_R5 C3, Hep_220_300_R2 C2, Hep_220_300_R4 J1, Hep_160_075_R3 C1, C2 (C2 excluded, §4.6) | B | fewer than 3 images > 1 px |

**Test: tracking J3 in Hep_160_150_R2 (2026-11-25).** To estimate how sensitive the result is to the LED positions
of the untracked fire-room J3 series, J3 of Hep_160_150_R2 (only source of F1 in that test; in the fine survey 7.9 px in single images and a
persistent shift) was tracked afterwards with `ledsa_h1_track.py` in an isolated copy of the pipeline and the room
chain of F1 was re-run (`tools/run_room.sh`; same reference images 1–5, `config.ini` and `config_analysis.ini`
byte-identical to those of the main evaluation). The results are kept in `tests/j3_tracking_Hep_160_S1_R2/`
(k files `farbg_sum_col_val`, SNR mask, tracking log, configs) and evaluated by `checks/j3_tracking_test.py`,
which reproduces the committed stage-4 values for the untracked case and also compares the test's tracking with the
fine survey.

Per `analysis/tracking_log.csv` of the test, the mean shift of the LED boxes against the LED search (`shift_row`
along, `shift_col` across the strips) was 0.7–1.7 px along at 0–300 s, 1.3–2.5 px at 300–1200 s and 1.9–2.7 px
after 1200 s, across up to 1.3 px. This shift is the mean of the tracked LED positions minus the mean of the
LED-search positions; the positions carry over from image to image (predicted position = previous image + search
step + anchor; each LED then moves to the brightest pixel of the 5×5-smoothed channel-sum image within ±3 px of its
predicted position, integer pixels, only if that maximum exceeds 4 × the local median; otherwise it follows the
median refinement of its strip);
the global search step was 0 in all images, and the anchor (strip end vs. predicted lowest LED) was applied in 256
of 573 images with −1.67…0.00 px (mean −0.94 px). All LEDs were refined (`frac_refined` = 1) in all images except
26 before ignition (−96…+0.2 s, minimum 0.45). The reference images (ids 1–5) themselves are shifted by 0.18 px
along on average, so relative to them the boxes moved by up to about 2.5 px.

**The tracking of this test agrees with the fine survey only after about 1000 s.** With the rules of
`tools/stage2_trackcheck.py` (reliable survey images, tracking images with `frac_refined` ≥ 0.5, tolerance 2 px per
component; the tool itself needs the gitignored `tracked_positions.csv.gz` and the `runs/` layout, so
`checks/j3_tracking_test.py` repeats the comparison from `tracking_log.csv` and `inventory/ledsa_h1_drift_fine.csv`),
2 of 18 comparable images deviate by more than 2 px: 796 s (survey +0.1/+7.9 px along/across, tracking
+2.2/+0.9 px) and 896 s (survey +0.2/+7.8, tracking +1.8/+0.8). At 96–896 s the tracking is 0.86–2.11 px above
the survey along the strips, where the survey shows 0.1–0.5 px; from 1096 s the survey also shows 0.6–3.3 px
along and the two agree within about 1 px per component except 1.73 px (1296 s) and 1.52 px (1696 s) along and
1.06–1.22 px at 1196, 1496 and 1896 s (`checks/j3_tracking_test.py` prints all values). The 11 tracked series of the
main evaluation with comparable survey images stay within 1.52 px. The anchor values (strip end about 1 px off the
accumulated position) are a further hint that the per-LED refinement accumulated a shift before 1000 s that the
camera did not make; the strip-end detection depends on a threshold and on the smoke, so this is not a proof. The
test therefore measures the effect of re-placing the LED boxes by up to about 2.5 px on average (the per-LED
positions, `tracked_positions.csv.gz`, are not archived), not the effect of a confirmed
camera movement. It says nothing about shifts of the size of the single survey values of 6–8 px (if real); their
effect is not estimated.

| Quantity (mean of channels 0–2) | Fixed positions (main evaluation) | Tracked |
|---|---|---|
| Profile, median over layers of \|Δk\| at 200–1100 s | – | 0.0009–0.0028 1/m (0.9–1.2 %) |
| Profile, largest \|Δk\| (always the bottom layer, z = 0.05 m, from 400 s) | – | up to 0.022 1/m (5–7 %) |
| LEM at 2.3 m (layer 22, centre 2.28 m): peak / ratio to LEM | 0.6383 / 0.9462 | 0.6377 / 0.9453 |
| LEM at 2.3 m (layer 22, centre 2.28 m): plateau / ratio to LEM | 0.2444 / 0.8577 | 0.2410 / 0.8459 |

The other untracked series were not tested; Hep_160_150_R2 J3 has the most survey images > 1 px among the
untracked J3 series of the fine survey (7; Hep_220_300_R2 J3 has the largest single value, 8.1 px). The main
evaluation keeps the fixed positions.

For scale: `setup/ledsa_h1_tracking.csv` records
for C1 in Hep_160_075_R6 (3.9 px along the strip in the coarse survey) that tracking changed k by 2–6 % in stage 0.
This matches `inventory/ledsa_h1_stage0_test2_Hep_160_S4_R1_F2_hoehen.csv` (maximum filtered difference 2.5 % of the
peak at 2.1 m and 5.7 % at 2.3 m), if that file compares tracked with fixed positions. It cannot be a thinning test
(§4.1), which fits this reading, but the repository does not document it (§8.12). See §8.19.

**Tracking** (`ledsa_h1_track.py`, run in the working folder after `-s3_fast -rgb`; `tools/stage2_track.sh`,
`tools/stage2_track_list.sh`). Image by image, forwards and backwards from the analysis image closest to the
LED-search reference image:

1. global shift that maximises the smoothed sum of the three channel images at all LED positions (grid ±6 px along
   the strip in 1-px steps and ±12 px across in 2-px steps, then ±2 px across around the best grid point);
2. optional anchor at the lower strip ends, used only if all strips agree;
3. each LED moved to the local maximum within ±3 px if it stands out (> 4 × local median); LEDs not found follow
   the median shift of their strip;
4. readout with LEDSA's own `generate_analysis_data` (same box, same far-field pedestal) at the per-image positions.

The fixed-position readout is moved to `analysis/channel<c>_feste_positionen`. Per-image positions go to
`analysis/tracked_positions.csv.gz` (not in the repository) and the log to `analysis/tracking_log.csv` (in the
repository for the 12 series). `tools/stage2_trackcheck.py` checks for jumps of more than half an LED pitch between
consecutive images and for deviations of more than 2 px from reliable fine-survey values.

### 4.4 Stage 3: reference images, read noise, inversions, masks

`tools/stage3_rerun.sh` runs `tools/run_room.sh <run> <room>` for every room of every test and sets the marker
`stage3r1_<room>_ok`. It then runs the side variant `mitC1` and the decomposition variants (§6.4). Per room,
`run_room.sh` does:

```bash
python ledsa_h1_ledz.py <run> <cam>                 # per camera; idempotent
python ledsa_h1_config.py analysis <run> <room>     # reference images, config_analysis.ini, config_stacked.ini
python ledsa_h1_noise.py <run> <cam> [<cam>]        # read noise (LEDSA environment, rawpy)
python -m ledsa -a                                  # per camera, in runs/<run>/<pos>_<cam>/
python -m ledsa -as                                 # two-camera rooms, in runs/<run>/stacked_<room>/
python ledsa_h1_mask.py flag <run> <room>           # validity mask
python ledsa_h1_mask.py pedestal <run> <cam>        # far-field pedestal check
```

**Reference images** (`ledsa_h1_config.ref_window`, `select_ref_images`; values in the constants `REF_*`). They are
chosen per camera by time; image numbers differ between cameras.

1. Window end `t_max` = first LEM reaction in the room minus 20 s, capped at +20 s. The first LEM reaction is the
   first t > 0 from which an LEM column of the room stays above 0.01 1/m for 5 consecutive samples (5 s). Rooms
   without LEM data (F1 of Hep_220_300_R1, R4) use `t_max = 0` s.
2. Candidates: images with `t_max − 120 s ≤ t ≤ t_max` that have a readout in all three channels.
3. Per channel, using only the LEDs of the camera's own strip (array = channel) and `farbg_sum_col_val`: the base
   intensity of each LED is its median over the candidates. An image is valid if the median over the LEDs of
   I/I_base deviates from 1 by at most 0.02, and at most 2 % of the LEDs deviate by more than 20 %. The image must
   be valid in all three channels.
4. The 10 valid images with the highest image ids (closest to the end of the window) are taken. With fewer than 5 valid images
   the look-back is extended to 300 s; with still fewer than 5 the script aborts.

Exceptions: `REF_T_MAX_OVERRIDE` sets `t_max` = −85 s for Hep_160_150_R2 J3 (persons in front of the strip).
`REF_WINDOW_OVERRIDE` sets fixed windows (t_min, t_max, minimum count), with the same validity rule:
Hep_160_075_R3 J3 −4…5 s, 3 images (LEDs covered before −5 s), and Hep_160_075_R1 C1 30…41 s, 3 images (series
starts at +30 s; used only in the side variant). Result: 53 of the 56 inverted series have 10 reference images,
Hep_160_150_R2 J3 has 5 (−115.5…−99.8 s), and the two fixed windows have 3. The ids are in `ref_img_indices` of each
`config_analysis.ini`, and are repeated per camera in `[simulation_N]` of `config_stacked.ini`. They are the running
ids of `analysis/image_infos_analysis.csv` after thinning, not file-name counters (e.g. Hep_220_300_R3 J2: ids 79–88
= `2C6A4848.CR3` … `2C6A4893.CR3`); `first_id`, `last_id` and `ref_s1_id` (columns of
`setup/ledsa_h1_series.csv`) and, in `config.ini`, `first_img_experiment_id`, `last_img_experiment_id`,
`first_img_analysis_id`, `last_img_analysis_id` and `ref_img_id` are file-name counters.

**Reference windows extend past ignition in most series.** Because the window ends 20 s before the first LEM reaction (capped
at +20 s), it reaches into the burn wherever the LEM reacts late. In 41 of the 56 inverted series (including the
side-variant C1 of Hep_160_075_R1, 30.5–40.5 s) the last reference image is after t = 0 (computed from
`ref_img_indices` and `image_infos_analysis.csv`). In F2 and F3 the reference images typically span about
−30…+17 s (last image +8.6…+20.0 s; e.g. Hep_220_300_R3 J2 −27.9…+17.1 s, Hep_220_300_R3 J1 −24.8…+20.0 s). In F1
the LEM reacts at 16–21 s (no LEM in Hep_220_300_R1/R4: window end 0 s), so the windows end at −4…+1 s (except the overrides above: J3 of Hep_160_150_R2 ends at −85 s,
`REF_T_MAX_OVERRIDE`; J3 of Hep_160_075_R3 at +5 s, fixed window). Smoke that reaches parts of a line of sight before the LEM
reacts is therefore not excluded by construction; its effect is not quantified (§8.20). Special case
Hep_160_075_R4 F3: the column `Extinction LEM_2_F3_2.3 (1/m)` reads 0.0106–0.0136 1/m from 3 to 16 s, so the 5-s hold
is met at 3 s (first LEM reaction), `t_max` = −17 s and the C3 reference images are at −66.1…−21.0 s.

**LEDSA's own normalisation warning.** For every reference-image set, LEDSA compares each LED's value in each
reference image with its mean over the reference images and warns if the relative deviation exceeds 0.075
(`check_intensity_normalization` in `ledsa/data_extraction/data_integrity.py`; the message prints the tolerance
rounded as "8%": "In the process of normalisation N value(s) exceed(s) 8% tolerance of relative deviation against
mean intensities! You might check the reference images."). The logs in `runs/` contain 574 such warnings (4 more in the test folder of §4.3): 290 in
55 of the 56 `a_log.txt` and 284 in the 35 `as_log.txt` (stacks, side variant and decomposition variants;
`as_refresh_log.txt` repeats the 284), with N = 1…634 (median 56) per warning. They were not acted on
individually; no script of the pipeline reads them. The selection of reference images uses its own validity rule
(step 3 above: median ratio, own strip, `farbg_sum_col_val`), which the LEDSA check does not replace.

**Inversion settings** (`INVERSION` in `ledsa_h1_config.py`; identical in all 56 `config_analysis.ini` files and
all stacks):

| Parameter | Value |
|---|---|
| `solver` / `lambda_reg` | `linear` / 0.5 |
| `num_layers` / `domain_bounds` | 25 / `0.0 2.535` |
| `reference_property` | `farbg_sum_col_val sum_col_val` (main quantity first, both in one `-a` run) |
| `num_ref_images` / `ref_img_indices` | 10 / per camera, see above (10 is written also where only 5 or 3 indices are given; LEDSA ignores `num_ref_images` when indices are given, `ExperimentData.load_config_parameters`) |
| `camera_channels` / `led_array_indices` | `0 1 2` / `0 1 2` |
| `average_images` | `False` |
| `camera_position` / `pane_distance` | per position, §3.3 |
| temperature correction | none (`reduction_file_channel_* = None`) |
| stacks: `time_sync_tolerance` | 3 s |
| stacks: order | `[simulation_0]` = lower camera, `[simulation_1]` = upper camera; `[led_arrays]` *j* = `0:j 1:j` |

**Read noise** (`ledsa_h1_noise.py` → `inventory/ledsa_h1_read_noise.csv`), per test, camera and channel: the noise
of the box sum, with the formula of LEDSA 0.12.0:

σ_sum = sqrt( Σ_c n_c (σ_c · s_c)² ),  s_c = W / (W − B_c).

Here σ_c and B_c are the standard deviation and mean of the optical-black margin (left sensor margin) of Bayer
colour c, W is the white level, and n_c = R² pixels per Bayer colour in the 2R × 2R box (R = 10). Channel 1 sums
both greens. The value is averaged over the camera's reference images. All six cameras have an optical-black margin.

**Validity mask** (`ledsa_h1_mask.py flag` → `runs/<run>/plots_h1/mask_<room>.csv.gz`). A ray (LED) is invalid in an
image if `farbg_sum_col_val < SNR · σ_sum`. The script also treats a non-finite value as invalid ("no far-field
band"), but with LEDSA 0.13.0 this case does not occur: an LED without a far-field level gets pedestal 0 and keeps
its plain sum, `farbg_sum_col_val` = `sum_col_val` (`ledsa/data_extraction/step_3_functions.py`). A missing band
level is first filled from neighbouring LEDs of the same strip (running median over 15 LEDs, then running mean over
5, `smooth_along_strip` in `farfield_background.py`), and the lower of the two sides is used, so the pedestal is
missing only where no LED within these windows has a level on either side. Such LEDs would show as
`farbg_pedestal` = 0 in the per-image readout, which is not in the repository; their number is not quantified.
For each image and layer, the invalid fraction is the path length of invalid rays in that layer divided by the total path length in the layer.
Path lengths come from the camera's `led_array_<a>_distances_per_layer.txt`. For a stack, both cameras are pooled,
pairing images by nearest time within 3 s. A (time, layer) cell is blocked (`gesperrt = True`) if the fraction
exceeds 0.5. The mask is written for SNR 2, 3 and 5; **SNR 3 is used**. The same mask applies to
`sum_col_val`. Columns: `snr, quelle` (source: camera, `stacked_<room>` or `stacked_<room>_mitC1`), `led_array,
t_s, layer, anteil` (fraction), `gesperrt` (blocked).

**Pedestal check** (`ledsa_h1_mask.py pedestal` → `inventory/ledsa_h1_pedestal_check.csv`): far-field pedestal
(N × pedestal per pixel) divided by the box sum in the reference images, per camera and array. The rule of thumb in
the code is < ~1 %. An LED without a far-field level enters with pedestal 0 (see the validity mask above), i.e. as a
ratio of 0, not as a missing value.

**Stack distance files.** For stacks, LEDSA 0.13.0 writes `stacked_*/led_array_<a>_distances_per_layer.txt` only
if the file is missing, although it recomputes the distances in memory. `tools/refresh_stack_distances.sh` deleted
and regenerated these files after the LED-height correction. It checked that the k files stay bit-identical,
i.e. the inversion had already used the corrected geometry.

### 4.5 Stage 4 input: saturation

`ledsa_h1_stage4.py sat` → `inventory/ledsa_h1_saturation.csv`. For each inverted series and array: take the maximum
of `max_col_value` over the camera's reference images, per LED of the own strip. An LED counts as saturated if this
maximum is ≥ 0.98 × 16383. **A series × channel is excluded if more than 5 % of its LEDs are saturated**
(`SAT_MAX_PCT`, `ledsa_h1_config.saturated`). Saturated LEDs below that fraction stay in the inversion. The
inversions themselves contain all channels; the exclusion acts afterwards, through the choice of the main source
(§4.7). Excluded series × channel (14 of 168):

| Test | Camera: channels (saturated LED fraction, %) |
|---|---|
| Hep_160_075_R2 | J3: 0 (78), 1 (100), 2 (100); J2: 2 (100); J1: 2 (33.3); C2: 2 (13.2) |
| Hep_160_075_R3 | J3: 0 (74), 1 (100), 2 (100); J1: 2 (34.0) |
| Hep_160_075_R5 | C2: 2 (6.9) |
| Hep_220_300_R4 | J3: 1 (95.8), 2 (100); J2: 2 (97.9) |

### 4.6 Excluded cameras and the side variant

`CAM_EXCLUDE` in `ledsa_h1_config.py`. An excluded camera keeps its readout but does not enter the room inversion
used as main source:

| Camera | Reason (code comment / evidence) |
|---|---|
| Hep_160_075_R3 C2 (F1L) | unstable before ignition (relative `farbg` 0.001–463, 0 valid reference images in 300 s; LED search clean only from +200 s). Not inverted; its folder still has the uncorrected LEDSA geometry. |
| Hep_160_075_R1 C1 (F2L) | first image at +30 s, no image before smoke (first LEM reaction in F2 at 56 s with the 5-s rule of §4.4; 48 s with a single value above 0.01 1/m). F2 main source = J2 alone. |
| Hep_220_300_R3 C3 (F2L) | disturbed camera, criterion below. F2 main source = J2 alone. |

**Criterion for the Hep_220_300_R3 C3 exclusion.** The criterion was formulated after the deviation had been
noticed in the profile figure and against the LEM. It does not use the LEM. A camera is excluded if (i) over a long
time it receives much less LED light than the same camera at the same position in the other tests of the same
series, at all LED heights, (ii) the other camera of the same room receives a normal amount of light, (iii) in a
screening of all two-camera rooms it is the only camera that deviates uniformly from the other camera of its room,
and (iv) exposure and camera movement are ruled out as causes. Evidence:

- Screening (`checks/c3_r3_exclusion.py`, section F; computed from the committed k files and masks): for each
  two-camera room, lower minus upper single-camera inversion, median over time [300 s, ventilation − 20 s], then
  median over layers 3–22, after averaging the free channels first; "relative" = this median divided by the
  median k of the upper camera over the same layers and time window. Hep_220_300_R3 F2: +0.357 1/m. All 16 other checkable rooms:
  |median| ≤ 0.043 1/m (≤ 12.3 % relative). Three rooms are not checkable: Hep_160_075_R1 F2 (no C1 mask rows in
  the main mask), and Hep_160_075_R2/R3 F1 (no channel free of saturation in both cameras).
- C3 − J2 (median over layers 3–22, ±10 s) in 400–1200 s: +0.30…+0.47 1/m in R3, against −0.09…+0.02 (R1) and
  −0.03…+0.17 (R2); per layer at 400/600/800 s: +0.18…+0.65, +0.21…+0.44, +0.25…+0.41 1/m (section A).
- Tracking of C3 in R3 (`runs/Hep_220_S1_R3/F2L_C3/analysis/tracking_log.csv`): within −60…1700 s (the window of
  section E), |`shift_row`| ≤ 1.51 px and |`shift_col`| ≤ 0.28 px, per component (LED pitch in the image 20 px).
  Outside that window: after 1700 s |`shift_row`| up to 1.56 px; the largest magnitude, 2.43 px (1.95 px row,
  1.45 px column), is in the first image at −492.65 s. Exposure of C3 identical in R1–R3 (1/400 s, f/18, ISO 100)
  (sections E, G).
- Light received by C3 in R3 relative to R1/R2: about 1/4–1/8 at 400–1000 s (ratio per height band 0.12–0.27),
  according to the comment at `CAM_EXCLUDE` and `checks/sister_light_ratio.py`. This needs the per-image readout; checked
  against the archived output of `checks/c3_r3_exclusion.py` section B (C3, R3/R1 and R3/R2 per height band,
  channels 0-2: 0.119-0.268), which is not part of this repository.

Sections B and H of `checks/c3_r3_exclusion.py`, `checks/sister_light_ratio.py`, `checks/qc_image_quality.py` and
`checks/transmission_low_cams.py` need the per-image readout; in `checks/c3_r3_exclusion.py` sections B and H are
skipped when `analysis/channel*/` is missing. The `CAM_EXCLUDE` comment notes that J2 in the same
room itself shows anomalies at 100–250 s and after about 1050 s; F2 of Hep_220_300_R3 was nevertheless kept with
J2 as main source. The inversions of the excluded C3 (`runs/Hep_220_S1_R3/F2L_C3/`) and the stack with it
(`runs/Hep_220_S1_R3/stacked_F2/`, mask rows `C3` and `stacked_F2` in `mask_F2.csv.gz`) remain in the repository
as evidence and are not used by the profiles or the stage-4 table.

**Side variant `mitC1`** (`H1_VARIANT=mitC1 tools/run_room.sh Hep_160_S2_R1 F2`): stack C1 + J2 for
Hep_160_075_R1 F2. It uses C1 reference images 30.5–40.5 s (fixed window above) and writes to
`runs/Hep_160_S2_R1/stacked_F2_mitC1/`, mask `runs/Hep_160_S2_R1/plots_h1/mask_F2_mitC1.csv.gz`. Only C1 is recomputed (config,
noise, `-a`). In the stage-4 table it appears as `kind = variant`, nulled over 30–45 s (`VARIANT_BASE_WIN`). It is
not used in the profiles.

### 4.7 Main source per room and channel

`ledsa_h1_config.channel_source(run, room, channel)`: if both cameras of the room are free (not excluded, channel not
saturated), the stack; if one is free, the single-camera inversion of that camera; if none, the channel is dropped.
Rooms with one camera use that camera. Result (column `cams` of `inventory/ledsa_h1_profiles.csv`; "+" = stack,
lower camera first):

| Test | F1 ch 0 / 1 / 2 | F2 ch 0 / 1 / 2 | F3 ch 0 / 1 / 2 |
|---|---|---|---|
| Hep_220_300_R1, R2 | C2+J3 (all) | C3+J2 (all) | C1+J1 (all) |
| Hep_220_300_R3 | C2+J3 (all) | J2 (all) | C1+J1 (all) |
| Hep_220_300_R4 | J3 / – / – | J2 / J2 / – | J1 (all) |
| Hep_160_150_R1, R2 | J3 (all) | C1+J2 (all) | J1 (all) |
| Hep_160_150_R3 | J3 (all) | C1 (all) | J1 (all) |
| Hep_160_075_R1 | J3 (all) | J2 (all) | J1 (all) |
| Hep_160_075_R2 | C2 / C2 / – | C1+J2 / C1+J2 / C1 | C3+J1 / C3+J1 / C3 |
| Hep_160_075_R3 | – (no source) | C1+J2 (all) | C3+J1 / C3+J1 / C3 |
| Hep_160_075_R4 | – | C1 (all) | C3 (all) |
| Hep_160_075_R5 | C2 / C2 / – | C1 (all) | C3 (all) |
| Hep_160_075_R6, R7 | – | C2+C1 (all) | – |

36 test × room combinations have a source (103 room × channel series). The stack is the main source in at least
one channel in 16 rooms.

---

## 5. Post-processing to the reported quantities

All of this is in `ledsa_h1_stage0.py` (`grid`, `widmann`, `LAM`, `load_k`, `sigma_clip`, `smooth`, `metrics`,
`apply_mask`, `mask_for`, `lem`, `vent`), `ledsa_h1_profiles.py` (`paper_series`, `window_mean`),
`ledsa_h1_config.py` (`channel_source`: main source per room and channel) and `ledsa_h1_stage4.py` (`sources`:
list of sources per room; mard). Only the main quantity `farbg_sum_col_val` of channel *a* /
array *a* is used. Steps for one layer series k(t) of one source and channel:

1. **Mask:** cells blocked in the SNR-3 mask of that source are set to NaN before anything else. Mask times are
   matched to k times within 0.01 s. The code aborts if a blocked cell or a k time cannot be matched.
2. **1-s grid:** linear interpolation onto t = −30 … 1700 s in 1 s steps (`np.interp`; NaN outside the series; a
   NaN sample makes the adjacent intervals NaN).
3. **Nulling (deviation from a plain t = 0 nulling):** the baseline is the median of the unmasked *raw* values (not
   the gridded ones) with −5 s ≤ t ≤ +10 s (`BASE_WIN_S`), subtracted from the gridded series. It aborts with fewer
   than 2 values in the window. Reason (docstring): in F1 the person igniting the fire covers the lower LEDs of J3
   in the image at t ≈ 0; nulling at the single value at t = 0 would shift the whole series. The side variant uses
   30–45 s. With images every 4–5 s the window holds 3–5 raw values; in 38 of the 2575 layer series of the profiles
   it holds only 2, so the median is their mean and not robust (37 in Hep_160_075_R3 F2, 1 in Hep_160_150_R2 F1;
   computed from the committed k files and masks).
4. **Widmann correction to 638 nm:** multiply by (638/λ)^(−1.0088), λ = 628 / 521 / 468 nm for channel 0 / 1 / 2,
   i.e. by K_m(0.638 µm)/K_m(λ) with the Widmann correlation K_m = 4.8081·λ^(−1.0088), λ in µm (Widmann, J.F., 2003,
   Combustion Science and Technology 175(12), 2299–2308, doi:10.1080/714923279). 638 nm is the LEM wavelength (as
   stated in the companion article), so the corrected LEDSA values are comparable with the LEM. The LED wavelengths
   628 / 521 / 468 nm are as set in the code (`LAM` in `ledsa_h1_stage0.py`); their source is not in this repository.
5. **Sigma clip:** running median m and running standard deviation s of the residual over 51 samples (centred,
   at least 3). Values with |k − m| > 0.5·s are replaced by m. With a threshold of 0.5 s this replaces about half of
   the values (median 52 %, 5–95 % range 42–58 % of the finite 1-s values per layer series, computed as for step 3),
   so in effect it smooths with a running 51-s median rather than removing isolated outliers.

The **LEM** series is interpolated to the same grid and sigma-clipped the same way (no nulling, no Widmann
correction).

**Profiles** (`ledsa_h1_profiles.py csv` → `inventory/ledsa_h1_profiles.csv`): for the main source (§4.7) of every room and channel, every layer,
the mean of the finite processed values within ±10 s of t = 200, 400, 600, 800 s after time zero. The script aborts
if 800 + 10 s is not before ventilation. LEM/SICK values in `inventory/ledsa_h1_profiles_points.csv` are the
**nearest sample** to each profile time (not averaged).

**Profile figure** (`ledsa_h1_profiles.py plot` → `plots/ledsa_h1_profiles_<series>.pdf/.png`): one grid per series,
rows = rooms F1–F3, columns = 200/400/600/800 s. One line per test: the mean over the channels available in the CSV,
grouped by layer index; where channels were dropped (§4.5, §4.7) a line averages fewer than three channels. Colour =
test number; line style solid = stack in all channels, dashed = single camera in all channels, dash-dotted = mixed by
channel (stack in some channels, single camera in others). The k axis starts at 0 and its range differs between the
series. `inventory/ledsa_h1_profiles.csv` has no NaN (0 of 10 300 rows), so the lines have no gaps; 149 of the 3600
plotted channel means are ≤ 0 (down to −0.004 1/m) and lie on the axis at k = 0, which can look like a line ending
there.
LEM (filled diamond) and SICK (open square; column `Extinction SICK_<room>_<height> IR (1/m)_corr`, documented in the
README of the measurement data (H1 test-data repository) as "Corrected by Widmann-Correlation") at their heights in the colour of the test, as nearest sample without averaging, only for tests with a LEDSA
result in that room and where the instrument recorded data. The row label gives n, the number of tests with a LEDSA result in
that room.

**Stage-4 comparison with the LEM** (`ledsa_h1_stage4.py lem` → `inventory/ledsa_h1_stage4_lem.csv`). For every
room with LEM data, every LEM height and every source:

- Sources (`kind`): `main` (main source per channel, §4.7), `stack` (if both cameras exist; only channels free in
  both), `lower`/`upper` (each single-camera inversion; only its free channels), `variant` (`mitC1`). Each source
  uses its own mask rows.
- Layer: the layer whose centre (as written in the k file header) is closest to the LEM height (`z_layer`). Per
  channel the processed series of that layer; `channel = mean` is the NaN-mean over the processed channel series.
- Both LEDSA and LEM are smoothed with a centred running mean over 21 samples (±10 s, at least 10 values;
  `smooth`). Then, on the smoothed series:
  - **peak** = maximum over 0 < t < t_vent, with its time `t_peak`;
  - **plateau** = mean over t_vent − 300 s ≤ t ≤ t_vent − 20 s;
  - `peak_ratio`, `plateau_ratio` = LEDSA / LEM;
  - **mard** = mean of |LEDSA/LEM − 1| over 0 < t < t_vent − 20 s where the smoothed LEM is ≥ 20 % of its peak
    (`MARD_LEM_FRAC`); `n_mard_s` = number of finite seconds used.

  t_vent = `ventilation_s` of the test. LEM columns with fewer than 100 values are ignored, so F1 of
  Hep_220_300_R1/R4 has no row. Result: 560 rows, 34 rooms, 48 room × LEM-height combinations of `kind = main`.

Note that profiles use the ±10 s mean of finite values at four times (`window_mean`), whereas stage 4 uses the
running ±10 s mean with a minimum count (`smooth`). The LEM is averaged in stage 4 but not in the profile points.

---

## 6. Result files

All tables are CSV (`inventory/h1_files_juelich.tsv.gz`: tab-separated); a first line starting with `#` is a comment. k in 1/m, z in m, t in s relative to time zero
(§3.2). The `run` column always holds the test-log id; map it to names with `runs.csv`.

German column names and values: `quelle` source, `anteil` fraction, `gesperrt` blocked, `hoehe_m` height,
`spitze`/`t_spitze` peak / its time, `*_zu_LEM` ratio to the LEM, `groesse` quantity (reference property), `voll`
full, `aus` thinned (*ausgedünnt*), `gefiltert` filtered, `nachfuehren` track (`ja`/`nein` = yes/no), `begruendung`
reason, `n_gut` reliable images, `ueber1` above 1 px, `kat` category, `rand` edge, `fenster` window, `vor_lueftung`
before ventilation, `max_d_vor_px` (drift summary) largest shift before the evaluation window, `ohne_sockel` without pedestal, `ueber_1pct` above 1 %, `tag` day, `kamera` camera, `lage`
image position (camera-position check), `geprueft` checked. In the outputs of `checks/compare_prior.py`, `checks/decompose_prior0100.py` and
`ledsa_h1_stage0.py test1`, `neu` (new) labels this evaluation, `ohne Maske` without mask, `prior0130 …` the earlier 0.13.0
evaluation and `prior0100 …` / `0.10.0 sum (prior0100)` the earlier 0.10.0 stacks (§6.4).

### 6.1 `2_Analysis/LEDSA/inventory/`

| File | Produced by | Content |
|---|---|---|
| `ledsa_h1_profiles.csv` | `ledsa_h1_profiles.py csv` | profiles: `config` (series), `run, room, source` (`stacked_<room>` or camera), `cams`, `channel` (0–2), `t_s` (200/400/600/800), `layer` (0–24), `z_m` (layer centre), `k` (±10 s mean, §5). 10 300 rows. `z_m` is taken from the k-file header, so it is rounded to 0.01 m for single-camera sources (0.05, 0.15, …) and not for stacks (0.0507, 0.1521, …); join or group by `layer` (as for the k files, §6.3). |
| `ledsa_h1_profiles_points.csv` | same | LEM and SICK nearest sample: `config, run, room, instrument, z_m, t_s, t_sample_s, k` (252 rows) |
| `ledsa_h1_stage4_lem.csv` | `ledsa_h1_stage4.py lem` | LEM comparison (§5): `config, run, room, z_lem, z_layer, source, kind, channel, lem_peak, lem_t_peak, lem_plateau, peak, t_peak, plateau, peak_ratio, plateau_ratio, mard, n_mard_s, vent_s, channels`. `z_layer` is the header centre rounded to 3 decimals, so the same layer appears as e.g. 2.28 (single camera) and 2.281 (stack); for `channel = mean` it is the centre of the first channel's source. The table has no `layer` column: match by `z_lem`, or recover the layer as round((`z_layer` − 0.0507)/0.1014). |
| `ledsa_h1_saturation.csv` | `ledsa_h1_stage4.py sat` | per series × channel: `n_led, max_value, median_max, sat_frac_pct` (168 rows) |
| `ledsa_h1_read_noise.csv` | `ledsa_h1_noise.py` | `sigma_sum` per run, camera, channel (§4.4) |
| `ledsa_h1_pedestal_check.csv` | `ledsa_h1_mask.py pedestal` | far-field pedestal / box sum in the reference images (median, p95, % of the LED values in the reference images > 1 %). `ohne_sockel_pct` counts non-finite ratios; with LEDSA 0.13.0 an LED without far field has pedestal 0, so the column cannot detect a missing band (all 168 values 0.0, §4.4) |
| `ledsa_h1_pedestal_k_effect.csv` | `checks/check_pedestal_k.py` | per single-camera inversion of the cameras used in the main evaluation (not the excluded C3 of Hep_220_300_R3 and C1 of Hep_160_075_R1; 76 rows) and LEM height (2.3 m where the room has no LEM): peak and plateau (§5 definitions) of the mean of the three channels, `farbg_sum_col_val` vs `sum_col_val`; without mask and without the saturation exclusion, and nulled at t = 0 instead of §5 step 3 (`ledsa_h1_stage0.room_series`/`paper_series`); `ped_med_pct` = median over the three arrays and `ped_red_pct` = value of array 0 (red) of
`ped_frac_median_pct` in `ledsa_h1_pedestal_check.csv`; `peak_ratio`/`plat_ratio` = farbg / sum here (in
`ledsa_h1_stage4_lem.csv` they are LEDSA / LEM) |
| `ledsa_h1_drift.csv`, `_drift_summary.csv` | `ledsa_h1_drift.py` | coarse camera-movement survey (§4.3) |
| `ledsa_h1_drift_fine.csv`, `_drift_fine_summary.csv` | `ledsa_h1_drift_fine.py` | fine survey of the strip region (§4.3) |
| `ledsa_h1_drift_fine_kategorien.csv` | no script in the repository (made by a script that was not archived) | per series: reliable images in the window (`n_gut`), their maximum shift (`max_gut`), number > 1 px (`n_gut_ueber1`), category `kat` (§4.3). The column `nachfuehren` is an intermediate state of 2026-11-23, not the final decision: it is empty for the tracked series Hep_220_300_R3 C3, Hep_160_150_R1 J2 and Hep_160_075_R3 J2, and `nein` for the tracked series Hep_160_150_R2 J2 and Hep_160_075_R4 C3; the decision is `setup/ledsa_h1_tracking.csv` |
| `ledsa_h1_bad_images.csv` | `ledsa_h1_drift.py` (appends) | RAW files that rawpy could not read (2); no header row (columns: path, error, script) |
| `ledsa_h1_juelich_abgeschnitten.csv` | no script in the repository (made by a script that was not archived) | truncated RAW files of the Jülich day series (50, §3.1); read by `tools/stage2_check.py`, `tools/stage2_order.py`, `ledsa_h1_drift_fine.py` |
| `h1_exif_weitergabe.csv.gz`, `h1_exif_juelich.csv.gz` | EXIF inventories: `h1_exif_weitergabe` is a copy of `h1_exif_alle.csv`, written when the photo handover was created, outside this repository (docstring of `ledsa_h1_setup.py`); `h1_exif_juelich` by `tools/juelich_exif.py` | inputs of `ledsa_h1_setup.py` |
| `h1_files_juelich.tsv.gz` | `tools/juelich_list.py` | file list of the Jülich day series; input of `tools/juelich_exif.py` |
| `ledsa_h1_stage0_test1_*.csv`, `ledsa_h1_stage0_test2_*.csv` | `ledsa_h1_stage0.py` | stage-0 tests (§4.1) |
| `ledsa_h1_compare_prior_lem.csv`, `ledsa_h1_compare_prior_profiles.csv` | `checks/compare_prior.py` | comparison with two earlier evaluations (§6.4) |
| `decompose_prior0100.csv` | `checks/decompose_prior0100.py eval` | decomposition of the difference to the earlier 0.10.0 stacks (§6.4) |
| `fds_sens_profiles.csv` | `checks/fds_sens_profiles.py` | effect of FDS sensitivity runs on the stratification (needs FDS output) |

### 6.2 `2_Analysis/LEDSA/plots/` and `setup/`

| File | Content |
|---|---|
| `plots/ledsa_h1_profiles_Hep_220_300.pdf/.png`, `_Hep_160_150`, `_Hep_160_075` | profile figures (§5) |
| `setup/ledsa_h1_runs.csv` | per test: date, `start_time` (= time zero), `ignition_s`, `ventilation_s`, `fire_out_s` |
| `setup/ledsa_h1_series.csv` | image series (§3.1) |
| `setup/ledsa_h1_positions.csv` | camera positions and `pane_distance` (§3.3); `position_labbook` = test-log name (there U = lower, O = upper) |
| `setup/ledsa_h1_led_strips.csv` | strips per room: array, colour, channel, origin, x, y, `z_bottom_m`, `z_top_m`; `*_paper_m` = simplified 0–2.5 m geometry not used here |
| `setup/ledsa_h1_strip_windows.csv` | LED-search windows and percentile per series and strip (§4.2) |
| `setup/ledsa_h1_tracking.csv` | tracking decision per series (§4.3): `run, cam, nachfuehren` (`ja`/`nein`), `begruendung` (reason) |

### 6.3 LEDSA working folders in `runs/`

```
runs/<run>/<pos>_<cam>/                  e.g. runs/Hep_220_S1_R3/F2U_J2/
    config.ini, config_analysis.ini, image_infos.csv
    led_array_<a>_distances_per_layer.txt   path length behind the pane per LED (rows) and layer (columns), m;
                                            row sum = |LED − camera| − pane_distance; rows in reverse
                                            order of analysis/led_array_indices_00<a>.csv (LEDSA calc_distance_array
                                            iterates the LEDs reversed; ledsa_h1_mask.py reverses the ids, [::-1])
    *_log.txt, timing.txt, stage2_*_ok
    analysis/image_infos_analysis.csv       ID, Name, Time[s] (EXIF clock), Experiment_Time[s]
    analysis/led_search_areas.csv           LED id, pixel row, pixel column
    analysis/led_array_indices_00<a>.csv    LED ids of array a
    analysis/led_search_areas_with_coordinates.csv        corrected (§3.3): id, pixel row, pixel column, x, y, z, width, height
    analysis/led_search_areas_with_coordinates_ledsa.csv  LEDSA -coord original
    analysis/tracking_log.csv               tracked series only
    analysis/corrupted_images.csv           RAW files LEDSA could not read, including some outside the analysed
                                            set; 6 analysed images in 3 series were skipped (Hep_160_150_R1 J1: 1,
                                            Hep_220_300_R1 J1: 2, Hep_220_300_R4 J1: 3)
    analysis/extinction_coefficients/linear/<property>/
        extinction_coefficients_linear_channel_<c>_<property>_led_array_<a>.csv
runs/<run>/stacked_<room>/                same layout of extinction_coefficients; config_stacked.ini,
                                          time_alignment_led_array_<a>.txt, led_array_<a>_distances_per_layer.txt
runs/<run>/plots_h1/mask_<room>.csv.gz    validity masks (§4.4)
runs/Hep_160_S2_R1/stacked_F2_mitC1/      side variant (§4.6)
runs/Hep_160_S2_R{2,3}/zerl_F{2,3}_{pane,geo,ref,all}/   decomposition variants (§6.4)
```

`<property>` is `farbg_sum_col_val` (main) or `sum_col_val`. A single-camera k file has LEDSA's header lines
(channel and array, `num_of_layers` and borders, camera position and `pane_distance`, reference property, reference
images, solver, layer bottoms/tops/centres). A stack k file has one line instead of the first four
(`# Stacked inversion | sim0:arr0 | sim1:arr0 | pane_distance: sim0 …, sim1 … | solver: … | ref_prop: … | ref_imgs:
sim0 […], sim1 […] | …`, without camera positions and `num_of_layers`), then the layer lines. Both then have one row
per image: `Experiment_Time[s]` (relative to time zero, §3.2), then k of layers 0–24. These files are raw LEDSA output: no
mask, no nulling, no Widmann correction, no filtering. Single-camera files round the layer centres in the header
to 0.01 m; stack files do not. Join or group by layer index, not by `z_m`. For stacks the time axis is that of the
lower camera, limited to times with a partner image of the upper camera within 3 s (§3.2).

**LEDSA state flag.** Each camera folder contains an empty `.reorder_leds.flag`. LEDSA `-s2` sets it after
renumbering the LEDs by strip; `-s1` removes it, and `-s2` stops while it exists ("run step S1 again";
`ledsa/data_extraction/DataExtractor.py`). A re-run therefore starts with `-s1`, as `tools/run_cam.sh` does.

**Test folder** `2_Analysis/LEDSA/tests/j3_tracking_Hep_160_S1_R2/` (§4.3): `F1U_J3/config.ini`,
`config_analysis.ini`, `a_log.txt` (LEDSA `-a`), `track_test.log` (console output of `ledsa_h1_track.py`),
`analysis/tracking_log.csv` (per image: `shift_row`/`shift_col` = mean displacement of the tracked LED positions
along/across the strips against the LED search, `step_dy`/`step_dx` = global search step, `anchor_row` = along-strip
anchor correction, NaN = not applied, `frac_refined` = fraction of refined LEDs), `analysis/extinction_coefficients/linear/farbg_sum_col_val/`
(same format as in `runs/`), and `plots_h1/mask_F1.csv.gz` of the test. It is not part of the main evaluation.

### 6.4 Comparisons with earlier evaluations (documentation only)

`checks/compare_prior.py` compares, at the LEM heights (mean of the three channels) and as profiles, against (i) the
earlier independent LEDSA 0.13.0 evaluation (single cameras C1–C3 at the lower positions of Hep_160_075_R2, both
quantities, and Hep_160_075_R3, `sum_col_val` only) and (ii) the earlier LEDSA 0.10.0 stacks of
Hep_160_075_R2/R3/R6/R7. The `source` column identifies the evaluation and quantity (`neu` = this evaluation, §6).
The post-processing is that of §5 without mask and without the saturation exclusion, i.e. all three channels, for
all sources except `neu main` (main source per channel, masked; §4.7). So, e.g., `neu stack C2+J3` of
Hep_160_075_R2 F1 contains J3, which is saturated in all channels (§4.5). There are two further deviations for the
earlier 0.13.0 evaluation: its nulling window is −30…+15 s (`PRIOR0130_BASE_WIN`; according to the docstring that evaluation averages 5 images in Hep_160_075_R2, about
25 s apart, so the §5 window would hold fewer than 2 values; the window is applied to all its series), and its time
axis is shifted per camera onto ours by matching image names (`prior0130_shift`; according
to the docstring its first image is 0 s in Hep_160_075_R2, which is −121.24 s here for C1). The time axis of the
0.10.0 stacks is used as it is (no shift). According to `photo_handover/README.md` ("Bezug zum LEDSA-Paper"), F2U
of Hep_160_S4_R2 (= Hep_160_075_R7) is shifted by +11 s in that earlier evaluation so that both cameras start
together; `compare_prior.py` compares exactly this stack without undoing or applying that shift. How the shift
enters the earlier stack's time axis and pairing, and its effect on the comparison, are not quantified. The profile
comparison interpolates both onto layer centres 0.05…2.45 m. `checks/decompose_prior0100.py make|eval` re-inverts our
readout of Hep_160_075_R2/R3 F2/F3 with LEDSA 0.13.0 using `sum_col_val` and the configuration differences of the
earlier 0.10.0 stacks, one at a time: no `pane_distance` (`pane`), `camera_position` of both cameras taken from the
0.10.0 configurations (`geo`; in the committed `zerl_*_geo/config_stacked.ini` this differs from ours only in the
lower camera, x = 0 instead of −0.177 m in F2 and −0.181 m in F3), first 10 images as reference (`ref`), and all
three together (`all`). In `decompose_prior0100.csv`, `variant = neu` is our stack (`sum_col_val`) and `prior0100` the
0.10.0 stack. `eval` post-processes all of them like `compare_prior.py`: mean of all three channels (including
saturated ones), no mask, §5 nulling (−5…+10 s) and smoothing, peak/plateau/mard against the LEM as in stage 4 at
the layer nearest to the LEM height. Folders are `runs/<run>/zerl_<room>_<variant>/`. Two differences
of the 0.10.0 stacks are not decomposed: their `domain_bounds` 0–2.5 m (LEDSA 0.13.0 aborts with it, because the top
LED at 2.535 m lies outside) and their LED heights (presumably the simplified 0–2.5 m strips; their LED coordinates
are not available; not verified). Both scripts need the earlier evaluations, which are not in the repository.

### 6.5 How to compare another evaluation

- **Which values:** for a like-for-like LEDSA comparison, the raw k files of §6.3 (per camera or stack;
  `farbg_sum_col_val` or `sum_col_val`; channel *a* with array *a*). For the post-processed values, see
  `inventory/ledsa_h1_profiles.csv` or `inventory/ledsa_h1_stage4_lem.csv`. To recompute them from the raw k files,
  apply all steps of §5 in order: SNR-3 mask; 1-s grid −30…1700 s; nulling by the median of the unmasked *raw*
  values in −5…+10 s (not the value at t = 0; 30–45 s for the side variant); Widmann factor to 638 nm; sigma clip
  (running median and standard deviation over 51 samples, threshold 0.5·s with s the running standard deviation, which acts as a running-median smoother);
  then the ±10 s mean of finite values (profiles) or the running ±10 s mean and metrics (stage 4). Main source per
  channel and saturation exclusion: §4.5, §4.7.
- **Time:** `Experiment_Time` = EXIF time − time zero (full minute, `runs.csv` `t0_local`). Ignition is at
  `ignition_s` (§3.2). No camera clock offset is applied. An evaluation that sets the first image as zero, or uses
  a clock offset (e.g. the +11 s shift of F2U in Hep_160_075_R7 in the earlier 0.10.0 evaluation, §6.4), is
  shifted against these files.
- **Heights:** layer *j* spans 0.1014·*j* … 0.1014·(*j*+1) m. LED heights are those of the corrected coordinate files
  (Jülich strips 0.1517–2.535 m, BCL 0.055–2.535 m, equal spacing by index), not LEDSA's `-coord` heights.
- **Geometry:** cameras at the test-log positions behind the pane (x < 0) with `pane_distance`; see
  `config_analysis.ini` / `config_stacked.ini`.
- **Channel ↔ strip:** channel 0 = red strip (BCL in F1/F2, Jülich in F3), 1 = green, 2 = blue (Jülich).
- **Reference images:** per camera in `config_analysis.ini` (`ref_img_indices` = running ids of
  `analysis/image_infos_analysis.csv` after thinning, not file-name counters; names and times there). In most series
  they extend after ignition, typically to about +17 s (§4.4).
- **LED positions:** 12 series were read out with per-image tracked LED positions (§4.3; `setup/ledsa_h1_tracking.csv`,
  `nachfuehren = ja`): Hep_160_150_R1 J2, Hep_160_150_R2 J2, Hep_160_075_R2 C3, Hep_160_075_R3 C3, Hep_160_075_R3 J2, Hep_160_075_R4 C3, Hep_160_075_R6 C1, Hep_220_300_R1 C2, C3, J1, Hep_220_300_R3 C3, J2. All other series use the fixed positions of the LED search. The per-image
  positions (`tracked_positions.csv.gz`) are not archived; `analysis/tracking_log.csv` per series gives the mean
  shift per image.
- **Handed-over templates:** `photo_handover/configs/` are not the configurations used here; they differ in the
  reference images, the LED-search reference image and percentile, the LED heights, the image rotation and the
  image range in three series (§8.18).
  Use the `config*.ini` files in `runs/`.
- **Masks and saturation:** the raw k files include blocked cells and saturated channels. Use `mask_<room>.csv.gz`
  (SNR 3, matching `quelle`) and `inventory/ledsa_h1_saturation.csv` (> 5 %) to apply the same selection.

---

## 7. Reproduction

### 7.1 From the committed data (no images)

Analysis environment, `PYTHONPATH` empty, `H1_VARIANT` and `H1_LEDSA_RUNS` unset, LaTeX available:

```bash
cd 2_Analysis/LEDSA
python ledsa_h1_profiles.py all
python ledsa_h1_stage4.py lem
python checks/check_pedestal_k.py . inventory/ledsa_h1_pedestal_k_effect.csv
```

These regenerate `inventory/ledsa_h1_profiles.csv`, `inventory/ledsa_h1_profiles_points.csv`,
`inventory/ledsa_h1_stage4_lem.csv` and `inventory/ledsa_h1_pedestal_k_effect.csv` byte-identically on Windows
(on Linux/macOS pandas writes LF instead of CRLF line endings; compare ignoring them), from the
committed k files, masks, saturation table, pedestal table, setup tables and `_processed.csv` files. The figures
(`plots/*.pdf`, `*.png`) are drawn with `fireplot`; two consecutive runs with different `PYTHONHASHSEED` gave
byte-identical PDFs on the toolchain in `env/` (MiKTeX). Byte identity holds for this toolchain only (Matplotlib, TeX
distribution, fonts).

With the earlier evaluations available (`H1_PRIOR0130`, `H1_PRIOR0100`):

```bash
python checks/compare_prior.py . <outdir>          # writes <outdir>/compare_prior_lem.csv, compare_prior_profiles.csv
python checks/decompose_prior0100.py . eval inventory  # writes inventory/decompose_prior0100.csv
```

The inventory names `ledsa_h1_compare_prior_lem.csv` and `ledsa_h1_compare_prior_profiles.csv` come from the copy
step in `tools/post_rerun.sh`. With the earlier evaluations available, these outputs reproduced the committed files byte-identically
(checked on 2026-11-25 on the machine of the evaluation).

The screening and sections A, C–G of `checks/c3_r3_exclusion.py` also run from the committed data; sections B and
H are skipped when `analysis/channel*/` is missing.

`python checks/j3_tracking_test.py .` (tracking test of §4.3) also runs from the committed data and prints the
values of the table in §4.3; its "fixed" rows equal the Hep_160_S1_R2 F1 rows of `inventory/ledsa_h1_stage4_lem.csv`.

### 7.2 What needs more than the repository

| Step | Needs |
|---|---|
| stages 0–3 (`ledsa_h1_s1scan.py`, `ledsa_h1_probe.py`, `tools/run_cam.sh`, `ledsa_h1_track.py`, `ledsa_h1_noise.py`, LEDSA `-s1 … -s3_fast`) | raw images |
| LEDSA `-a`, `-as`; `ledsa_h1_mask.py flag/pedestal`; `ledsa_h1_stage4.py sat`; `ledsa_h1_config.py analysis` (reference images) | per-image readout `analysis/channel*/` and LEDSA's binary data (regenerated from the images) |
| `ledsa_h1_drift.py`, `ledsa_h1_drift_fine.py`, `tools/drift_regions.py` | raw images |
| `tools/plot_drift.py height`, `tools/plot_drift.py profile` | per-image tracked positions (`tracked_positions.csv.gz`; mode `profile` is not named in the docstring); `timeseries` runs from the committed survey and tracking logs |
| `tools/stage2_trackcheck.py` | per-image tracked positions `analysis/tracked_positions.csv.gz` (gitignored; used for the LED pitch) and the `runs/<run>/<pos>_<cam>/` layout; for the tracking test the same survey comparison is in `checks/j3_tracking_test.py` |
| `tools/stage0_voll.sh` | the per-image readout in `runs/` and a full (unthinned) readout of the upper camera in `runs/_stage0_voll/<run>/<upper folder>`, whose creation is not documented (§4.1) |
| `checks/sister_light_ratio.py`, `qc_image_quality.py`, `transmission_low_cams.py`, `check_c1.py`, `check_j2.py`, `check_outliers.py` (raw part), `c3_r3_exclusion.py` B/H | per-image readout |
| `ledsa_h1_setup.py` | only repository files (EXIF inventories, `photo_handover/`, `_events.txt`), but see §8.1 |
| `checks/compare_prior.py`, `checks/decompose_prior0100.py`, `ledsa_h1_stage0.py test1` | the earlier evaluations (`H1_PRIOR0130`, `H1_PRIOR0100`) |
| `ledsa_h1_stage0.py test2` | the counterpart inversions in `runs/_stage0_voll/` (built by `tools/stage0_voll.sh`, see above; gitignored) |
| `checks/fds_sens_profiles.py` | FDS output (`H1_FDS_ROOT`) |

Further helper scripts (one line each, from their headers):
`tools/queue.sh` runs `run_cam.sh` for several cameras in turn after a read test of one image file;
`tools/stage3_pass2.sh` waits for the first stage-3 pass and the tracking queues to finish and then restarts
`tools/stage3.sh` for the rooms skipped so far; `checks/decompose_prior0100_run.sh` runs `-as` for all decomposition
variants (after `checks/decompose_prior0100.py make`).

Order for a full re-run from the images (do not re-run `ledsa_h1_setup.py`, §8.1): `tools/scan_all.sh <i> <N>` →
merge and check the strip windows → `tools/stage2.sh` and the tracking scripts (`tools/stage2_track.sh <i> <N>`,
`tools/stage2_track_list.sh <run>:<cam> …` for an explicit list (an addition; `stage2_track.sh` already covers the 12
series with `nachfuehren = ja`), then `tools/stage2_trackcheck.py <run>:<cam> …`; the tracking scripts wait per series for
`stage2_s3_ok`; the line "AUSLESE FERTIG" or "ABBRUCH" in `runs/_logs/stage2/stage2.log` ends the wait for series
whose readout failed, so redirect the output of `stage2.sh` to that file, otherwise they wait indefinitely) → `tools/stage3_rerun.sh` →
`tools/refresh_stack_distances.sh` and `tools/refresh_stack_distances.sh '*/zerl_*'` (decomposition variants) →
`tools/post_rerun.sh`. Start `tools/stage3_rerun.sh` only after all tracking queues have finished: unlike the old
`tools/stage3.sh`, it does not check `stage2_track_ok`. `post_rerun.sh` runs `sat`, profiles, stage 4, pedestal
effect, `compare_prior` and decomposition; the last two need the earlier evaluations. Before re-running LEDSA on
another machine, set `H1_IMAGES_ROOT` to the root of the image tree (§2; do not regenerate
`setup/ledsa_h1_series.csv`, §8.1). Under it the folders `1_Measurements\<run>\3_LEDSA\<series folder>` and
`2_juelichMeasurements\<date>\camJ<n>` must exist as given in `folder_w` (`tools/stage2_order.py`,
`ledsa_h1_drift.py` and `ledsa_h1_probe.py` parse these endings). Set, if needed, `H1_LEDSA_RUNS` (not read by
`tools/stage2_trackcheck.py`, which `tools/stage2_track_list.sh` calls inside the chain, and by helpers outside
the chain, e.g. `tools/drift_regions.py`, `tools/plot_drift.py`,
`checks/j3_tracking_test.py`, `checks/qc_image_quality.py`, `checks/sister_light_ratio.py`,
`checks/transmission_low_cams.py`, which always use `2_Analysis/LEDSA/runs/`; `tools/stage0_voll.sh` always writes to
`2_Analysis/LEDSA/runs/_stage0_voll/` and sets `H1_LEDSA_RUNS` for its own calls). The decomposition step inside
`tools/stage3_rerun.sh` (`checks/decompose_prior0100.py make`) needs the earlier 0.10.0 stacks (`H1_PRIOR0100`);
without them it stops with a `KeyError` after rewriting only
`runs/Hep_160_S2_R2/zerl_F2_pane/config_stacked.ini` (rooms are the outer loop, variants `pane`, `geo`, … the inner); `stage3_rerun.sh` then still runs
`checks/decompose_prior0100_run.sh`, which deletes the time-alignment reports in all `zerl_*` folders and runs `-as`
with the committed `zerl_*` configurations (whose `path` entries are the placeholder `<H1_LEDSA_RUNS>`, §2), so
`-as` fails for the 15 variants that `make` did not rewrite and recomputes `Hep_160_S2_R2/zerl_F2_pane`
(overwriting its committed k files). The main results are not affected. Do not edit the `config*.ini` files:
the chain rewrites them (§8.9). Points to watch:

- **Strip windows.** `tools/scan_all.sh` skips every series that already has rows in
  `setup/ledsa_h1_strip_windows*.csv` (so move the committed table away first). Each queue sets `H1_WINDOWS_PART`
  and writes `setup/ledsa_h1_strip_windows_part<i>.csv`. In the main evaluation these part files were merged into
  `setup/ledsa_h1_strip_windows.csv` by hand; there is no merge script (the `scan_merge` named in the comment of
  `scan_all.sh` is not in the repository). `status = geprueft` is then set by hand after inspecting `s1scan.png`.
- **Markers.** `tools/stage2.sh` skips series with `stage2_s3_ok`, `tools/stage2_track.sh` and
  `tools/stage2_track_list.sh` skip series with `stage2_track_ok` (`stage2.sh` deletes this marker when it re-reads a
  series), and `tools/stage3_rerun.sh` skips rooms with `runs/<run>/stage3r1_<room>_ok` and the side variant with
  `runs/Hep_160_S2_R1/stage3r1_F2_mitC1_ok`. All these markers are in the repository, so delete them before
  re-running. The older markers `runs/*/stage3_F*_ok` are read only by the old first-pass script `tools/stage3.sh`
  (also restarted by `tools/stage3_pass2.sh`), not by these scripts.

---

## 8. Known deviations and limitations

1. **Setup table vs. current setup script.** `setup/ledsa_h1_series.csv` is the table the LEDSA runs used. It was
   made before a fix in `ledsa_h1_setup.py.exif_time`: the EXIF `SubSec` field has leading zeros, and reading it as
   a number turned "05" (0.05 s) into 0.5 s. Re-running the current script on the repository inputs changes the
   derived columns `ref_s1_t_s` (4 series), `t_first_s` (3), `t_last_s` (6), `dt_median_s` (4), `max_gap_s` (7)
   and `counter_wrap` (7). It also changes one LEDSA input: for Hep_220_300_R4 J3, `first_id` becomes 6745 instead
   of 6746 (`n_range` 470 instead of 469), i.e. one extra image at about −221 s. The `ref_s1_id` values do not
   change. If the table is regenerated, that series must be re-run, and its image ids shift by one. The committed
   row lists `n_img = 470` with `first_id … last_id` covering 469 images; LEDSA analysed 469. The code comment at
   `exif_time` in `ledsa_h1_setup.py` says the SubSec error did not affect LEDSA; the `first_id` change above
   contradicts it. The same SubSec parsing is still in `ledsa_h1_drift.py` (`exif_times`, also used by
   `ledsa_h1_drift_fine.py`) and `ledsa_h1_probe.py`: there a value "0X" is read as X/10 s instead of X/100 s (e.g. "09"
   → 0.90 s instead of 0.09 s; 1942 of 29 601 rows of `inventory/h1_exif_juelich.csv.gz` and 3420 of 37 895 rows of
   `inventory/h1_exif_weitergabe.csv.gz` affected), so sample selection and `t_rel_s` in
   `inventory/ledsa_h1_drift*.csv` can be off by up to 0.81 s; k is not affected.
2. **Header comments of the setup tables.** `setup/ledsa_h1_led_strips.csv` contains a sentence on the Jülich bottom
   end ("Juelich z_bottom = z_top - 143/60 m …") that the script does not write; the data rows have the same content
   as the script output (the committed file has LF line endings, a re-run on Windows writes CRLF). The header of `setup/ledsa_h1_series.csv` says "13 Hep-Laeufe" (a fixed string in
   `ledsa_h1_setup.py`), but the table covers 14 tests.
3. **Camera clocks are not synchronised** (§3.2). LEDSA and LEM share the same nominal zero, but each camera's
   EXIF clock may be offset by an unknown amount.
4. **Nulling** uses the median of unmasked raw values in −5…+10 s instead of the value at t = 0 (§5 step 3). In 38
   layer series (37 of them in Hep_160_075_R3 F2) only 2 raw values are in the window, so the baseline is their mean.
5. **Profile points vs. stage 4:** profile LEM/SICK points are nearest samples, LEDSA profile values are ±10 s means.
   Stage 4 averages both. The sigma clip (threshold 0.5·s, s = running standard deviation) replaces about half of the values by the running 51-s
   median, i.e. it acts as smoothing (§5 step 5). It acts on 1 Hz LEM samples and on LEDSA values interpolated from
   4–5 s images, so it does not act identically on both.
6. **LEDSA `-coord` heights** are affine (no perspective) and are replaced by `ledsa_h1_ledz.py` (§3.3).
   The committed `config.ini` files (`led_array_edge_coordinates`) still hold the Jülich bottom 0.100 m; a re-run
   writes 0.1517 m (`ledsa_h1_config.set_edges` reads `setup/ledsa_h1_led_strips.csv`). Only `-coord` reads this,
   and `run_cam.sh` re-runs `ledsa_h1_ledz.py` after every `-coord`, so k does not depend on it.
7. **Constant `pane_distance`** (LEDSA's model: the same smoke-free length on every line of sight of a camera). The
   pane is flat at x = 0 (§3.3), so the true smoke-free length is |x_camera| · L / (x_LED − x_camera) for a line of
   sight of length L. True minus LEDSA's constant value: F1U −10.8…+11.6 mm, F2U −9.7…+10.4 mm, F3U −9.2…+9.1 mm,
   lower positions within ±6.1 mm; at most 0.25 % of the smoke path (computed from the corrected LED coordinates and
   the camera positions).
8. **Stack distance files** are not refreshed by LEDSA when the geometry changes (§4.4); they were regenerated with
   `tools/refresh_stack_distances.sh`. The k files were not affected.
9. **Paths:** `config.ini` holds the image folders as `<H1_IMAGES_ROOT>\…`, and `config_stacked.ini` and
   `time_alignment_led_array_*.txt` hold the original working folders as `<H1_LEDSA_RUNS>\…` (placeholders, §2).
   For the main evaluation, hand edits are pointless, because the chain rewrites all three (the
   `zerl_*` variants are rewritten only by `checks/decompose_prior0100.py make`, which needs the earlier stacks): `run_cam.sh` regenerates `config.ini`
   from `folder_w` (`ledsa_h1_config.build`: `img_directory = img_path(r.folder_w)`, i.e. with `H1_IMAGES_ROOT` filled in), `ledsa_h1_config.py analysis` (in
   `run_room.sh`) writes `config_stacked.ini` with `path` = the working folder under `RUNS` (`H1_LEDSA_RUNS`), and
   `run_room.sh` deletes the time-alignment reports before `-as` (LEDSA writes them only if missing). To re-run, set
   `H1_IMAGES_ROOT`; do not regenerate `setup/ledsa_h1_series.csv` with `ledsa_h1_setup.py`, which would also
   change the image sequence of Hep_220_300_R4 J3 (§8.1).
10. **Saturation:** series × channels with ≤ 5 % saturated LEDs stay in the inversion.
11. **Excluded and unused folders:** `runs/Hep_160_S2_R3/F1L_C2/` (excluded, uncorrected geometry, no inversion),
    `runs/Hep_220_S1_R3/F2L_C3/` and `runs/Hep_220_S1_R3/stacked_F2/` (excluded, kept as evidence). Re-running
    `ledsa_h1_mask.py flag Hep_220_S1_R3 F2` with the current `CAM_EXCLUDE` would drop the `C3`/`stacked_F2` mask
    rows that `checks/c3_r3_exclusion.py` needs. The C3 exclusion criterion was formulated after the deviation was
    seen (§4.6).
12. **Stage-0 `test2` files:** their column names (`*_aus_zu_voll`, `kmax_voll`) refer to "thinned vs. full", but
    the function only compares two inversions of the same stack, and the pairs are not recorded. Hep_220_300_R3 F3
    (`n_t` = 241, J1 thinned in `runs/`) fits a thinning test. Hep_160_075_R6 F2 cannot be one: both series of the
    BCL stack C2 + C1 have `num_skip_imgs` = 0, and `n_t` = 181 matches the unthinned 5-s interval (§4.1).
13. **BCL strip spacing:** the BCL strips are placed between 0.055 and 2.535 m with 150 LEDs, i.e. 16.64 mm spacing.
    The LED density of the BCL strips was not verified independently.
14. **Truncated Jülich RAW files** are skipped by LEDSA (`analysis/corrupted_images.csv`); their list is
    `inventory/ledsa_h1_juelich_abgeschnitten.csv`.
15. **Thinning:** the Jülich series of 2025-12-08 use every 5th image (§3.1). In the stacks of these tests, the
    upper-camera image is matched to the lower-camera image within 3 s.
16. **Hep_220_300_R1 J2:** double/smeared LED images until about +900 s (code comment in `ledsa_h1_setup.py`). LED
    positions were found in the image at +1600 s. Its reference images (−33.2…+16.8 s) lie in the smeared phase.
    The comments in `ledsa_h1_setup.py` and `setup/ledsa_h1_tracking.csv` still say "check suitability in stage 3".
    That check is `checks/check_j2.py` (brightness before ignition, jump during +900…+1500 s, stack / C3 / J2
    against the LEM; needs the per-image readout); its output is not in the repository. The camera was kept (decided
    on 2026-11-24 after these three checks; result not verified). From the committed data, the LEM comparison in
    `inventory/ledsa_h1_stage4_lem.csv` (F2, mean of channels, peak / plateau ratio, mard) gives at 1.5 m J2 alone
    0.977 / 0.967 / 0.099, C3 alone 0.940 / 0.833 / 0.160, stack 0.968 / 0.908 / 0.096, and at 2.3 m J2 1.052 /
    0.872 / 0.072, C3 0.974 / 0.889 / 0.149, stack 1.027 / 0.865 / 0.071.
17. **Hep_160_150_R2 J1 array 0** has 143 instead of 144 LEDs (one not matched by `-s2`).
18. **`2_Analysis/LEDSA/LEDSA_README.md`** is an older description (cameras at x = 0, strips 0–2.5 m) and is not
    used by this pipeline. The same holds for the handed-over templates in `photo_handover/configs/` (start values,
    according to `photo_handover/README.md`). Templates exist for 33 of the 57 series (BCL cameras and the J3 `FZJ`
    series; none for the Jülich day series); a key-by-key comparison of these 33 `config.ini` and 32 `config_analysis.ini`
    pairs (Hep_160_075_R3 C2 was not inverted) and the two template stacks with the files in `runs/` gives:
    - `ref_img_indices`: `None` in all templates, so LEDSA would take the first 10 analysis images
      (`ExtinctionCoefficients.calc_and_set_ref_intensities`), e.g. Hep_160_075_R2 C1 (`251210_V_01_C1`)
      −121.2…−76.3 s; here time-based per camera, up to about +17 s (§4.4).
    - `ref_img_id` (LED search): the 10th image of the series in the templates (e.g. 10), here the last image at
      t ≤ −30 s or an override (§4.2; e.g. 19 for that series).
    - `pixel_value_percentile`: 99.875 in all 99 `config.ini` templates under `photo_handover/configs/` (all tests of
      the campaign, including those not evaluated here), here 99.875–99.98 per series (§4.2; different in 26 of the
      33 pairs).
    - LED heights: the templates rely on the affine `-coord` heights; here `ledsa_h1_ledz.py` replaces them (§3.3).
      `led_array_edge_coordinates` themselves are identical, with the Jülich bottom 0.100 m in both (§8.6).
    - `img_rotation = auto` in the templates, 0 here.
    - Image range: the templates include a single image after a gap of more than 120 s in Hep_160_075_R5 C2
      (`last_img_*_id` 331 instead of 330) and Hep_160_075_R6 C2 (315 instead of 314), and start Hep_220_300_R4 J3 at
      6745 instead of 6746 (§8.1).
    - Not relevant for the result: relative instead of absolute paths, empty `led_array_edge_indices` (to be
      filled after `-s1`), `num_cores` 4 instead of 8.
    - Identical in all pairs: `camera_position`, `pane_distance`, `num_skip_imgs` (only the thinned Jülich series of
      2025-12-08 have `num_skip_imgs` > 0, and they have no template), time settings (`date`, `start_time`,
      `exif_time_infront_real_time`, `time_ref_img_*`), `search_area_radius`, `farfield_distances`, `channel`,
      `max_num_leds`, `num_arrays`, and all inversion parameters (`reference_property`, `camera_channels`,
      `led_array_indices`, solver, `lambda_reg`, layers, `domain_bounds`, temperature correction).
19. **Untracked camera movement.** Not every series with > 1 px in the fine survey was tracked (§4.3): the fire-room
    upper cameras J3 in six tests (up to 8.1 px, judged as disturbances, cause not verified), Hep_220_300_R2 C3
    (1.7 px), and series with single images up to 6.3 px (C1 in Hep_160_150_R2/R3). The effect on k of not tracking
    them itself is not measured. A sensitivity test for one series (J3 of Hep_160_150_R2, §4.3; LED boxes re-placed
    by up to about 2.5 px, the tracking agrees with the fine survey only after about 1000 s, shifts of 6–8 px not
    covered) gave: profiles about 1 % in the median over the layers, up to 5–7 % in the bottom layer;
    LEM-height plateau −1.4 %, peak −0.1 %. Where tracking was compared with fixed positions in stage 0 (C1 Hep_160_075_R6, 3.9 px), it changed k by 2–6 % (§4.3).
20. **Reference images after ignition** (§4.4). In 41 of the 56 inverted series the last reference image is after
    t = 0, up to +20.0 s in the main evaluation (+40.5 s in the side variant). Hep_160_075_R4 F3 is the opposite
    case: a low LEM reading from 3 s ends the window at −17 s (C3 reference images −66.1…−21.0 s). The effect of smoke
    in the reference images on k is not quantified.

---

## 9. Long-axis camera (N1)

A separate evaluation of the camera that looked along the building, in `2_Analysis/LEDSA/long_axis/` (paths in
this section are relative to that folder). It uses the modules of the room evaluation without changing them and
follows its chain (§4, §5) except where stated. Code comments are in German, as in the rest of the pipeline.

### 9.1 Camera, strips and tests

- **Camera N1** (Nikon D610, 60 mm lens, no optical black) at position L2 in room F3, x = 0.256 m, y = 13.607 m,
  z = 0.715 m (`setup/la_positions.csv`, from `photo_handover/positionen.csv`). Seven tests: Hep_220_300_R1–R3
  (`Hep_220_S1_R1`–`R3`), Hep_160_075_R2, R3 (`Hep_160_S2_R2`, `R3`) and Hep_160_075_R4, R5 (`Hep_160_S3_R1`,
  `R2`); the run ids in the files are those of `runs.csv`.
- **Strips:** LED 4 on the window wall of room F2 (x = 0.732 m, y = 4.44 m; LEDSA array 0, the nearer strip) and
  LED 2 on the window wall of the fire room F1 (x = 1.49 m, y = 0; array 1), both green BCL strips with 150 LEDs
  from z = 0.055 to 2.535 m (`setup/la_strips.csv`); only channel 1 (green) is evaluated. In the image the two
  strips are told apart by their LED pitch in pixels.
- **Path:** the rays run 9.2 m (LED 4) and 13.7 m (LED 2) through F3, the corridor FC and F2 (LED 2 also F1). The
  retrieved k(z) is therefore a path-length-weighted mean over several rooms, not a room value.
- **Camera J4** (Canon EOS 80D) at position L1 in the corridor was used in Hep_160_075_R2 only. It is **excluded**
  (`code/la_post.py`, `EXCLUDED`): the row at which both complete strips show the same height gives a camera
  height of about 0.23 m against 0.686 m in the position table, which could not be resolved, and the image used
  for the LED search (−31 s) had an object in the line of sight, so only 59 of the 150 LEDs of LED 2 were found.
  Its rows remain in the setup tables; its working folder is not in the repository.

### 9.2 Deviations from the room evaluation

- **LED search** (`code/la.py scan`): reference image = the latest image before −30 s with both chains complete
  in the same camera pose (persons were in the image shortly before ignition in some tests); search radius 7 px,
  set by the pitch of the farther strip. The search windows of all series were checked on the control images
  (`setup/la_windows.csv`, status `geprueft`; the control images are not in the repository).
- **Partly visible strips** (`code/la.py edges`, `ledz`): LED indices follow from the local pitch, with gaps
  (> 1.5 pitches) and double detections (< 0.6 pitch, which get the index of the previous LED and are not
  counted). The LEDs not found at the strip ends are, for N1, the top 3 of LED 4 and the bottom 9 of LED 2
  (`END_HIDDEN`). A horizon test supports this: points at the camera height lie on one image row in both strips;
  with these assignments the inferred number of hidden LEDs at the bottom of LED 2 is 8.6–9.7 in the tests where
  the bottom end is visible, against 13–14 for the alternative. In Hep_160_075_R2, R3 and R5 the middle of LED 2 is
  hidden; only the top segment (55–65 LEDs, z ≥ 1.47–1.60 m) is used, and the short segments below it are not.
- **Reference images** (`code/la.py analysis`): the window ends 20 s before the first LEM reaction in any of the
  rooms F1–F3 (the rays cross all of them), at most at +20 s; selection as in §4.4, for channel 1 and arrays 0/1.
- **Mask** (`code/la.py mask`): N1 has no optical black, so the SNR criterion of §4.4 is not available. A ray is
  invalid if `farbg` ≤ 0 or if U_B (P/S + P0/S0) > 0.1 at an optical depth above 0.1, with U_B = 0.2 (P pedestal,
  S signal, index 0 = reference); a layer is masked at a time if more than half of its path length lies on invalid
  rays (variants U_B = 0.1 and 0.3 in `mask.csv.gz`). No N1 series has saturated LEDs (`setup/la_saturation.csv`).
- **Nulling** (`code/la_post.py`): the median over the time span of the reference images instead of [−5, +10] s,
  because in Hep_220_300_R1 a person occluded part of LED 2 from −24 to +1 s (raw k ≈ 0.5 m⁻¹ on 0.6–1.1 m); the
  rest of the post-processing is that of §5 (1-s grid, Widmann factor for green, sigma clip).
- **Dense smoke:** in Hep_220_300, LED 2 is masked from about 130 s on and LED 4 from about 200 to 500 s.

### 9.3 Camera movement

`code/la_drift_led.py` measures the shift of every image against the LED-search reference image from the LED
centroids (green plane at half resolution, window ±2 half-pixels, three iterations, median over the LEDs with at
least 20 % of the reference signal). On synthetically shifted copies of the reference image it recovers shifts to
0.02 px. The phase correlation of §4.3 was not used: on these strip images its single values scatter by ±1–2 px.
Results (`out/la_drift_led_summary.csv`, window −30 s to ventilation + 300 s): Hep_160_075 a slow drift along the
strips of up to 1.6–2.4 px, across at most 0.7 px; Hep_220_300_R1 and R3 at most 1.4 and 1.8 px (measurable only
until about 245 s and from about 1320 s, the LED signal in between being 0.1–0.5 % of the reference);
Hep_220_300_R2 shifted across by about −5.5 px (single values −3.7 to −6.5 px) between 320 s (still about 0) and
1280 s. `code/la_drift_sens.py` estimates the effect from the light lost from the search square in the reference
image (`out/la_drift_sens.csv`): 1 px costs at most 1.3 %, 3 px at most 6 % (along LED 2, whose pitch of 12 px is
smaller than the 15-px square, a shift along the strip can also add light from the neighbouring LED), i.e. at most
about 0.007 m⁻¹ over these path lengths; 5–6 px across cost 13–23 %. **Hep_220_300_R2 is therefore excluded after
320 s** (`code/la_post.py`, `CAM_MOVED`).

### 9.4 Comparison with FDS

`code/la_fds.py` uses the FDS extinction sections of the reproduction package of the companion article
(`results/simulation/flow_field/ef_<fire>_t<time>.npz`; environment variable `H1_REPRO_ROOT`): two vertical
sections along the whole apartment at x = 0.55 m and x = 1.25 m, z = 0–2.55 m, at t = 100, 200, 300 and 600 s,
for the fires Hep_160_075 and Hep_220_300. For every LED the optical depth along the straight ray from the camera
is integrated through the field, interpolated linearly in x between the two sections (outside them the nearer
one), and inverted with the same layer matrix (`led_array_<a>_distances_per_layer.txt`; recomputed from the
geometry, it agrees to 10⁻¹⁵ m) and the same solver as LEDSA (NNLS with second-difference penalty, λ = 0.5). The
horizontal distribution across the building is not resolved; at z = 2.0 m, the ray integral through the two
sections differs from that through the horizontal FDS section by −1.8 to +2.4 % from 200 s on (up to +23 % at
100 s for LED 4, where there is hardly any smoke on the rays), and 1.8 % of the LED-2 ray length lies in
obstruction cells of both sections (set to zero). Outputs: `out/la_fds_profiles.csv`, `out/la_fds_check.csv`,
figure `out/la_fds_profiles.pdf`.

### 9.5 Closure with the room profiles

`code/la_closure.py` compares the measured optical depth of each N1 ray with the one predicted from the room
profiles of the same test (`inventory/ledsa_h1_profiles.csv`, main source, channel 1 or else the mean of the
available channels, ±10 s means at 200, 400, 600 and 800 s), integrated along the ray with each room taken as
horizontally uniform. Stage `reduce` needs the per-image readout (not in the repository): τ = −ln(farbg/farbg_ref)
per LED and image (reference = mean over the reference images, as in LEDSA), rays invalid by the U_B criterion
left out, median over ±10 s if at least half of the images are valid, times the Widmann factor for green
(`out/la_tau_led.csv.gz`). Stage `closure` uses only repository data. Room boundaries along the building are the
wall centres of the FDS geometry (obstruction mask of the horizontal section): F1|F2 at y = 4.31 m, F2|FC at
7.76 m, FC|F3 at 11.14 m. The corridor FC (3.4 m of each ray) has no camera; it is taken as the mean of the F2 and
F3 profiles, bracketed by the smaller and the larger of the two. LED 2 needs an F1 profile, which Hep_160_075_R3
and R4 do not have. Results (`out/la_closure.csv`, `out/la_closure_summary.csv`, figure `out/la_closure.pdf`;
LED-time samples with a predicted τ ≥ 0.1): where the predicted τ is at least 1, measured over predicted is 1.03 in
the median (interquartile range 0.94–1.14) and within ±30 % in 93 % of the samples (both strips, 7 tests); for
smaller τ, on rays near the layer interface at 200–400 s, N1 reads more than predicted (median 1.29 for LED 4,
1.55 for LED 2). Where τ ≥ 1 the corridor bracket spans 9 % of the prediction (median).

### 9.6 Files and reproduction

```
long_axis/
    code/la.py               setup, LED search (scan/approve), config, edges (horizon test), ledz, analysis
                             (reference images), noise, mask
    code/la_chain.sh         chain per camera (LEDSA -s1 ... -a, as tools/run_cam.sh plus inversion and mask)
    code/la_crops.py         control image of the strip ends
    code/la_post.py          post-processing -> out/la_k_1s.csv.gz, out/la_profiles.csv
    code/la_fig.py           out/la_profiles.pdf, out/la_timeseries.pdf
    code/la_fds.py, la_fds_fig.py          comparison with FDS (§9.4)
    code/la_closure.py, la_closure_fig.py  closure with the room profiles (§9.5)
    code/la_drift_led.py, la_drift_sens.py camera movement (§9.3)
    setup/                   series, positions, strips, search windows, strip ends, read noise, saturation
    runs/<run>/L2_N1/        LEDSA working folders (as runs/ of the room evaluation, §6.3; plus mask.csv.gz)
    out/                     results and figures
```

From the committed data (hh2 environment, `H1_REPRO_ROOT` set for `la_fds.py`): `la_post.py`, `la_fig.py`,
`la_fds.py`, `la_fds_fig.py`, `la_closure.py closure`, `la_closure_fig.py`. They reproduce the committed outputs.
Raw images (`H1_IMAGES_ROOT`) are needed for the LEDSA chain, `la_drift_led.py`, `la_drift_sens.py` and
`la_crops.py`; the per-image readout for `la_closure.py reduce`. The setup tables are the ones the runs used.

### 9.7 Limitations

- Path means over several rooms; the corridor is not measured, so the closure brackets it (§9.5).
- Hep_220_300: large parts of the profiles are masked in dense smoke (§9.2); Hep_220_300_R2 ends at 320 s (§9.3).
- The FDS comparison rests on two vertical sections and four output times (§9.4).
- One camera position; J4 is excluded (§9.1).
