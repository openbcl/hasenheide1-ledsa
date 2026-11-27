"""Effect of tracking the fire-room upper camera J3 on the result, for Hep_160_S1_R2 (= Hep_160_150_R2) F1.

The main evaluation did not track the J3 series at F1U (METHODS.md section 4.3). This test tracked J3 of Hep_160_S1_R2
(ledsa_h1_track.py) in an isolated copy of the pipeline, re-ran the room chain for F1 (tools/run_room.sh: reference
images, read noise, LEDSA -a, mask) and kept the results in tests/j3_tracking_Hep_160_S1_R2/ (k files
farbg_sum_col_val, SNR mask, tracking log, configs; config.ini and config_analysis.ini byte-identical to those of
the main evaluation). Here both are post-processed like the pipeline (ledsa_h1_profiles.paper_series,
SNR-3 mask of the respective run, ledsa_h1_stage0.metrics at the LEM layer); the "fixed" values reproduce
inventory/ledsa_h1_stage4_lem.csv.

Run (analysis environment): python checks/j3_tracking_test.py .
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(HERE))
import ledsa_h1_stage0 as s0          # noqa: E402
import ledsa_h1_profiles as P         # noqa: E402

warnings.filterwarnings("ignore", category=RuntimeWarning)
SRC = {"fixed": HERE / "runs" / "Hep_160_S1_R2", "tracked": HERE / "tests" / "j3_tracking_Hep_160_S1_R2"}
RUN, ROOM, CAM, POS = "Hep_160_S1_R2", "F1", "J3", "F1U_J3"
PROP = "farbg_sum_col_val"
tg = s0.grid()
T_VENT = s0.vent(RUN)


def series(root):
    m = pd.read_csv(root / "plots_h1" / f"mask_{ROOM}.csv.gz")
    m = m[(m.snr == 3.0) & (m.quelle == CAM)]
    out, cen = [], None
    for a in range(3):
        f = root / POS / "analysis/extinction_coefficients/linear" / PROP / \
            f"extinction_coefficients_linear_channel_{a}_{PROP}_led_array_{a}.csv"
        t, k, cen = s0.load_k(f)
        k = s0.apply_mask(t, k, m[m.led_array == a], f"{root.name} {a}")
        out.append(np.vstack([P.paper_series(t, k[:, j], a, "", P.BASE_WIN_S) for j in range(len(cen))]))
    return np.stack(out), cen           # (channel, layer, time)


S = {k: series(v) for k, v in SRC.items()}
cen = S["fixed"][1]
assert np.allclose(cen, S["tracked"][1])
print(f"{RUN} {ROOM} {CAM}: {len(cen)} layers, ventilation {T_VENT:.0f} s")
print("\nProfiles (mean of channels 0-2, +-10 s), tracked - fixed:")
rows = []
for tp in (200, 400, 600, 800, 1000, 1100):
    a = np.array([P.window_mean(np.nanmean(S["fixed"][0][:, j], axis=0), tg, tp) for j in range(len(cen))])
    b = np.array([P.window_mean(np.nanmean(S["tracked"][0][:, j], axis=0), tg, tp) for j in range(len(cen))])
    d = b - a
    jm = int(np.nanargmax(np.abs(d)))
    rows.append(dict(t_s=tp, median_k_fixed=np.nanmedian(a), median_abs_dk=np.nanmedian(np.abs(d)),
                     median_rel_pct=100 * np.nanmedian(np.abs(d) / np.abs(a)), max_abs_dk=np.abs(d[jm]),
                     z_at_max=cen[jm], rel_at_max_pct=100 * np.abs(d[jm]) / np.abs(a[jm])))
print(pd.DataFrame(rows).round(4).to_string(index=False))
print("\nLEM comparison (as ledsa_h1_stage4.py lem: nearest layer, Hampel filter, +-10 s smoothing):")
for z, lv in s0.lem(RUN, ROOM).items():
    j = int(np.argmin(np.abs(cen - z)))
    ml = s0.metrics(lv, T_VENT)
    for name, (arr, _) in S.items():
        for ch in (0, 1, 2, "mean"):
            v = np.nanmean(arr[:, j], axis=0) if ch == "mean" else arr[ch, j]
            mv = s0.metrics(v, T_VENT)
            print(f"  z_lem {z} m, layer {j} ({cen[j]:.3f} m), {name:7s} channel {ch}: peak {mv['peak']:.4f} at "
                  f"{mv['t_peak']:.0f} s, plateau {mv['plateau']:.4f}; ratio to LEM {mv['peak'] / ml['peak']:.4f} / "
                  f"{mv['plateau'] / ml['plateau']:.4f}")

# Tracking of the test against the fine survey, same rules as tools/stage2_trackcheck.py (which needs the gitignored
# tracked_positions.csv.gz and the runs/ layout): reliable survey images (rand == 0, quality >= 1) measured against
# the reference image of the LED search, tracking images with frac_refined >= 0.5, tolerance 2 px per component.
ser = pd.read_csv(HERE / "setup" / "ledsa_h1_series.csv", comment="#")
r = ser[(ser.run == RUN) & (ser.cam == CAM)].iloc[0]
ref_name = r.name_string.format(int(r.ref_s1_id))
log = pd.read_csv(SRC["tracked"] / POS / "analysis" / "tracking_log.csv")
drift = pd.read_csv(HERE / "inventory" / "ledsa_h1_drift_fine.csv")
dv = drift[(drift.run == RUN) & (drift.cam == CAM) & (drift.ref == ref_name) & (drift.rand == 0) & (drift.quality >= 1.0)]
m = dv.merge(log[log.frac_refined >= 0.5], on="name").assign(e_row=lambda d: d.shift_row - d.dy_px,
                                                            e_col=lambda d: d.shift_col - d.dx_px)
off = m[(m.e_row.abs() > 2.0) | (m.e_col.abs() > 2.0)]
print(f"\nTracking of the test vs. fine survey (reference {ref_name}): {len(m)} comparable images, "
      f"{len(off)} deviate by > 2 px")
print(m[["name", "t_exp", "shift_row", "shift_col", "dy_px", "dx_px", "e_row", "e_col"]].round(2).to_string(index=False))
a = log[log.anchor_row.notna()]               # NaN = anchor not applied
print(f"\nAlong-strip anchor active in {len(a)} of {len(log)} images, anchor_row {a.anchor_row.min():.2f} .. "
      f"{a.anchor_row.max():.2f} px (mean {a.anchor_row.mean():.2f}); search step non-zero in "
      f"{int(((log.step_dy != 0) | (log.step_dx != 0)).sum())} images")
