# Hasenheide 1 – LEDSA evaluation

Evaluation of the camera-based LED extinction measurements (LEDSA, LED Smoke Analysis) of the Hasenheide 1 fire
tests (December 2025): 14 pool-fire tests with the C7-UVCB heptane mixture in a three-room apartment, rooms F1 (fire room), F2 and F3, each
seen by up to two cameras through a glass pane in the corridor wall. The evaluation uses LEDSA 0.13.0 and produces vertical
extinction-coefficient profiles k(z, t) per room and test, compared with the co-located laser extinction meters (LEM)
and the SICK transmissometers.

The experiments, the transmissometer data and the a-priori FDS simulations are published separately:

- M. Osburg, J. Schelhorn, A. Troff, W. Węgrzyński, A. Belt, L. Arnold, *Measuring and Modelling Smoke Light
  Extinction in Well-Ventilated, Multi-Room Compartment Fires: Co-located Transmissometry and A-priori FDS
  Validation*, Fire Safety Journal 167 (2027) 104997, <https://doi.org/10.1016/j.firesaf.2026.104997>
- Reproduction package of that article (code, reduced data, FDS input files):
  <https://github.com/openbcl/hasenheide1-reproduction>, <https://doi.org/10.5281/zenodo.24054120>

LEDSA: <https://github.com/FireDynamics/LEDSmokeAnalysis>; method: Arnold et al., Fire and Materials 45 (2021)
1075–1084, <https://doi.org/10.1002/fam.2841>; Börger et al., Fire Safety Journal 141 (2023) 103929,
<https://doi.org/10.1016/j.firesaf.2023.103929>; Börger et al., Fire Technology 60 (2024) 19–45,
<https://doi.org/10.1007/s10694-023-01470-z>.

**How the results were obtained, step by step: [`METHODS.md`](METHODS.md).**

## Test names

Tests are named `<series>_R<n>` as in the reproduction package, numbered in the order run within the series
(`Hep_160_075_R4` = fourth test with the 160 mm pan and 75 g fuel). File and folder names keep the ids of the test
log (`Hep_160_S3_R1`). [`runs.csv`](runs.csv) maps one to the other.

| Series | Pan (square side) | Fuel mass | Tests |
|---|---|---|---|
| `Hep_160_075` | 160 mm | 75 g | R1–R7 |
| `Hep_160_150` | 160 mm | 150 g | R1–R3 |
| `Hep_220_300` | 220 mm | 300 g | R1–R4 |

## Contents

```
README.md, METHODS.md, LICENSE, CITATION.cff, runs.csv, .gitattributes, .gitignore
env/                         software environments (pip freeze of both Python environments, LEDSA version,
                             ledsa_tree_hash.py)
photo_handover/              description of the LEDSA raw images as handed over to the LEDSA developers (German, kept
                             verbatim): README.md, HERLEITUNG.md (sources), serien.csv (image series), positionen.csv
                             (cameras), led_streifen.csv (LED strips), configs/ (LEDSA 0.13.0 start templates, for 33 of
                             the 57 series evaluated here; not the configurations used here), floor plan and section; covers the whole
                             campaign (also the ethanol, isopropanol and PUR tests not evaluated here)
1_Measurements/              copy of the processed H1 test data (LEM/SICK, events, metadata) underlying the
                             companion article; its reproduction package holds reduced time series of the same
                             measurements (cite the article and package for these data); the records here end at
                             t = 1800 s, for 8 tests the time series of the reproduction package run longer (to
                             1802–3600 s); where both exist, the values are identical
    experiment_metadata.txt  test metadata of the whole campaign ("Heptane" in this file and in the
                             _processed.csv headers means the C7-UVCB heptane mixture)
    <run>/1_Processed_data/
        <run>_processed.csv  LEM/SICK time series (input: reference-image window, comparison with LEM/SICK)
        <run>_events.txt     ignition, flame-out, start of ventilation
2_Analysis/Plans/            camera/LED plans, floor plan, sections
2_Analysis/LEDSA/
    ledsa_h1_*.py            pipeline (configuration, LED search, tracking, profiles, stage-4 comparison, ...)
    setup/                   series, test times (ignition, ventilation, flame-out), camera positions, LED strips,
                             strip windows, tracking decisions
    tools/                   shell chains (env.sh, run_cam.sh, ...) and helpers
    checks/                  checks and evidence scripts
    inventory/               result and inventory tables
    plots/                   profile figures per series
    tests/j3_tracking_Hep_160_S1_R2/   test: J3 of Hep_160_150_R2 tracked (k files, mask, configs, logs; not part of the
                             main evaluation; compared by checks/j3_tracking_test.py, METHODS.md section 4.3)
    fireplot/                figure style (from brandschutzconsult/fire-preprint-template, MIT; see ORIGIN.txt)
    LEDSA_README.md, LEDSA_Floorplan.pdf, LEDSA_Section.pdf   earlier position documentation (superseded, kept;
                             this floor plan labels F1t/F1b, the one in photo_handover/ F1U/F1L)
    runs/<run>/<pos>_<cam>/  LEDSA working folder per camera: config.ini, config_analysis.ini, LED search and
                             coordinates, LEDSA step logs, extinction coefficients (analysis/extinction_coefficients/)
    runs/<run>/stacked_F<i>/ two-camera (stacked) inversions per room
    runs/<run>/plots_h1/     masks mask_F<i>.csv.gz (signal-to-noise mask, to be applied to the raw k files;
                             use rows snr = 3 of the matching quelle and led_array; blocked cells have
                             gesperrt = True, keyed by t_s and layer (METHODS.md section 5); C1 of Hep_160_075_R1 only
                             in runs/Hep_160_S2_R1/plots_h1/mask_F2_mitC1.csv.gz)
    long_axis/               separate evaluation of camera N1, which looked along the building at two strips in
                             rooms F2 and F1 (path means over several rooms; comparison with FDS and closure with
                             the room profiles): code/, setup/, runs/, out/ (METHODS.md section 9)
    runs/Hep_160_S2_R1/stacked_F2_mitC1/   side variant with an excluded camera (not in the main evaluation)
    runs/Hep_160_S2_R*/zerl_F*_*/          decomposition variants of the comparison with earlier stacks
    runs/<run>/stage3r1_*_ok, runs/<run>/<pos>_<cam>/stage2_*_ok   marker files of the batch scripts; delete them only
                             before re-running the LEDSA chain (METHODS.md section 7.2): ledsa_h1_profiles.py and
                             ledsa_h1_stage4.py require stage3r1_<room>_ok; runs/<run>/stage3_F*_ok are obsolete markers
```

**Not every k file in `runs/` belongs to the evaluation.** The result of a room and channel comes from its
main source (METHODS.md section 4.7; column `cams` of `inventory/ledsa_h1_profiles.csv`); channels with more than
5 % saturated LEDs (`inventory/ledsa_h1_saturation.csv`) are dropped; so J3 of Hep_160_075_R2 and R3
(`runs/Hep_160_S2_R2/F1U_J3/`, `runs/Hep_160_S2_R3/F1U_J3/`) contributes no channel. Kept but not used: C3 of Hep_220_300_R3
(`runs/Hep_220_S1_R3/F2L_C3/`) and its stack `stacked_F2/`, C1 of Hep_160_075_R1 (`runs/Hep_160_S2_R1/F2L_C1/`, used
only in the side variant `stacked_F2_mitC1/`), the only stack that is main source in no channel
(`runs/Hep_160_S2_R2/stacked_F1/`), and the decomposition variants `zerl_*`. C2 of Hep_160_075_R3
(`runs/Hep_160_S2_R3/F1L_C2/`) was excluded before the inversion and has no k files (METHODS.md section 4.6).

Not included: the raw images (see `photo_handover/README.md` and `setup/ledsa_h1_series.csv` for folders and file
names; the file list and checksums of the images named in `photo_handover/README.md`, `dateiliste.tsv` and
`SHA256SUMS.txt`, went with the images and are not part of this repository), the per-image LEDSA readout
(`analysis/channel*/`, regenerated from the images), the logs of the batch runs (`runs/_logs/`; the LEDSA step logs
per camera are included), the per-image tracked LED positions of the 12 tracked series
(`analysis/tracked_positions.csv.gz`), the LED-search control images (`s1scan.png`), LEDSA's diagnostic plots
(`runs/*/*/plots/`), the stage-0 test folders (`runs/_stage0_*/`; their results are in
`inventory/ledsa_h1_stage0_*.csv`), and the earlier evaluations used for comparison.

Code comments and docstrings are partly German; dates in them ("festgelegt 2026-11-24", "Korrektur …") mark when a
choice was made or corrected. `METHODS.md` is the reference for every decision. Paths outside the repository are
written as placeholders (`<H1_IMAGES_ROOT>`, `<LEDSA_EXPORT>`, `<H1_LEDSA_RUNS>`; METHODS.md section 2), except in
`photo_handover/`, which keeps the original paths as handed over.

**Long paths (Windows).** The longest relative path has 188 characters. Clone into a short folder or run
`git config --global core.longpaths true`.

## Reproducing the results

With the analysis environment and LaTeX, from the committed data alone. Set up the environment with Python 3.12
(`python -m venv .venv`, then `pip install -r env/requirements-analysis.txt`); run with `PYTHONPATH` empty and
`H1_VARIANT` and `H1_LEDSA_RUNS` unset:

```bash
cd 2_Analysis/LEDSA
python ledsa_h1_profiles.py all     # -> inventory/ledsa_h1_profiles*.csv, plots/ledsa_h1_profiles_*.pdf/.png
python ledsa_h1_stage4.py lem       # -> inventory/ledsa_h1_stage4_lem.csv
python checks/check_pedestal_k.py . inventory/ledsa_h1_pedestal_k_effect.csv
python checks/c3_r3_exclusion.py .      # evidence for the exclusion of C3 in Hep_220_300_R3 (prints only)
python checks/j3_tracking_test.py .     # tracking sensitivity test, METHODS.md section 4.3 (prints only)
```

Run them from `2_Analysis/LEDSA` (the `.` is that folder). NumPy prints RuntimeWarnings ("Mean of empty slice")
for layers or times without valid values; they are expected. On Windows the first three commands reproduce the
committed tables byte for byte; on Linux/macOS pandas writes LF instead of CRLF line endings, so compare with
`git diff --ignore-cr-at-eol`; the figure PDFs and PNGs are byte-identical on the same
toolchain (Matplotlib, TeX distribution, fonts; see `env/README.md`). Without LaTeX, use
`python ledsa_h1_profiles.py csv` (tables only). The full chain from the raw images (LED search, tracking, readout,
inversions) is described in `METHODS.md`; it needs the images and the LEDSA environment.

Long-axis camera (METHODS.md section 9), from `2_Analysis/LEDSA/long_axis/code`, with `H1_REPRO_ROOT` set to a
checkout of the reproduction package of the companion article (for the FDS sections):

```bash
python la_post.py; python la_fig.py; python la_fds.py; python la_fds_fig.py
python la_closure.py closure; python la_closure_fig.py
```

## Comparing another evaluation

The per-camera and stacked extinction coefficients are in
`2_Analysis/LEDSA/runs/<run>/<pos>_<cam>/analysis/extinction_coefficients/linear/<property>/` and
`.../stacked_F<i>/analysis/...` in the LEDSA output format; the profiles used for the figures are in
`2_Analysis/LEDSA/inventory/ledsa_h1_profiles.csv`, the comparison with LEM in
`inventory/ledsa_h1_stage4_lem.csv`. Time is relative to the time zero of the test (`runs.csv`, `t0_local`; the same value is `start_time` in `setup/ledsa_h1_runs.csv`), heights
in m above floor. Use only channel a with LED array a (red strip = channel 0, green = 1, blue = 2); the
inversion has 25 layers of 0.1014 m over 0–2.535 m, so join or group by the column `layer`, not by `z_m` (single-camera
files round the layer centres to 0.01 m, stacks do not; `inventory/ledsa_h1_stage4_lem.csv` has no `layer`
column: match it by `z_lem`, METHODS.md section 6.1). Stacked files use the time axis of the lower camera, limited
to times with an image of the upper camera within 3 s. 12 series were read out with per-image tracked LED
positions (`setup/ledsa_h1_tracking.csv`, `nachfuehren = ja`), all others with the fixed positions of the LED search. Folder names use U = upper and L = lower camera (`F1U_J3` = upper camera in F1); the test log
(labbook) uses U for the lower position (`setup/ledsa_h1_positions.csv`, column `position_labbook`). The k files in
`runs/` are raw LEDSA output (no mask, no nulling, no Widmann correction; the
post-processing is in `METHODS.md` section 5). The headers of the k files say "LEDSA 0.9.4": LEDSA writes the version of an installed package
that was present but not used; the code that ran is LEDSA 0.13.0 (`env/README.md`).

The reported results use the property `farbg_sum_col_val` (box sum minus LEDSA's far-field pedestal); the
`sum_col_val` k files are kept for comparison. The configurations that were used are the `config*.ini` files in
`runs/`, not the start templates in `photo_handover/configs/` (they differ in reference images, LED-search
settings, image rotation and, in three series, the image range). The LED heights used are not in `config.ini`:
`ledsa_h1_ledz.py` overwrites `analysis/led_search_areas_with_coordinates.csv` after LEDSA `-coord` (METHODS.md
section 3.3), so re-running `-coord` from `config.ini` alone gives different heights. In particular, the Jülich
strips span 0.1517–2.535 m here (`setup/ledsa_h1_led_strips.csv`), whereas `photo_handover/led_streifen.csv` and
`config.ini` give 0.100 m as the lower end. Checklist for comparing: `METHODS.md` section 6.5.

## Licence and citation

Code (`*.py`, `*.sh`): MIT. Data, configurations, documentation and figures: CC BY 4.0. Details in [`LICENSE`](LICENSE); `2_Analysis/LEDSA/fireplot/` keeps its own MIT License. How to cite: [`CITATION.cff`](CITATION.cff).
