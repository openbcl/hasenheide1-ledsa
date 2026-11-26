"""Pruefung der vier auffaelligen Laeufe in den Profilen (2026-11-24). Nur lesen.
Je Fall (Lauf, Raum): (a) k-Profile bei den auffaelligen Zeiten aus jeder verfuegbaren Inversion (Stapel, Einzelkameras),
farbg gegen sum, gleiche Nachbearbeitung wie ledsa_h1_profiles.py (Maske, robuste Nullung, Widmann, Sigma-Clip, +-10 s;
Mittel der drei Kanaele); (b) Rohtransmission I/I_ref je LED ueber der LED-Hoehe (je Kamera, Kanal = Array, farbg,
Bild naechst der Zeit), Ausreisser-LEDs (I/I_ref > 1,05 oder Sprung gegen die Nachbar-LEDs > 0,15); (c) Saettigung:
max_col_value in den Referenzbildern (Anteil LEDs nahe am Maximum der Kamera).
Aufruf: hh2-venv check_outliers.py <LEDSA-Ordner> <png-Ordner>"""
import configparser
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(sys.argv[1]); OUT = Path(sys.argv[2])
sys.path.insert(0, str(HERE))
import ledsa_h1_stage0 as s0                     # noqa: E402
import ledsa_h1_profiles as P                    # noqa: E402
from ledsa_h1_config import RUNS                 # noqa: E402

CASES = [("Hep_220_S1_R3", "F2", (400, 600, 800)), ("Hep_220_S1_R4", "F3", (400, 600)),
         ("Hep_160_S3_R2", "F1", (400, 600)), ("Hep_160_S1_R3", "F2", (400,))]
tg = s0.grid()


def k_profile(kdir, prop, mask, t_list):
    out = {}
    for tp in t_list:
        chans = []
        for a in range(3):
            t, k, cen = s0.load_k(kdir / f"extinction_coefficients_linear_channel_{a}_{prop}_led_array_{a}.csv")
            if mask is not None:
                k = s0.apply_mask(t, k, mask[mask.led_array == a], f"{kdir} Array {a}")
            chans.append([P.window_mean(P.paper_series(t, k[:, j], a, "x"), tg, tp) for j in range(len(cen))])
        out[tp] = (cen, np.nanmean(np.array(chans), axis=0))
    return out


def raw_rel(work, t_list):
    c = configparser.ConfigParser(); c.read(work / "config_analysis.ini")
    refs = [int(x) for x in c["DEFAULT"]["ref_img_indices"].split()]
    info = pd.read_csv(work / "analysis" / "image_infos_analysis.csv")
    t = dict(zip(info.iloc[:, 0], info.iloc[:, 3]))
    z = pd.read_csv(work / "analysis" / "led_search_areas_with_coordinates.csv", comment="#", header=None).set_index(0)[5]
    get = lambda i, ch: pd.read_csv(work / "analysis" / f"channel{ch}" / f"{i}_led_positions.csv", comment="#",
                                    header=None, skipinitialspace=True).set_index(0)
    out, sat = {}, {}
    for a in range(3):
        idx = np.loadtxt(work / "analysis" / f"led_array_indices_{a:03d}.csv", dtype=int)
        R = [get(i, a).loc[lambda d: d.index.isin(idx)] for i in refs]
        ref = pd.concat([r[5] for r in R], axis=1).mean(axis=1)
        mx = pd.concat([r[4] for r in R], axis=1).max(axis=1)
        sat[a] = mx
        for tp in t_list:
            i = min(t, key=lambda j: abs(t[j] - tp))
            r = get(i, a)[5].reindex(ref.index) / ref
            out[(a, tp)] = pd.DataFrame({"z": z.reindex(r.index).values, "rel": r.values}, index=r.index).sort_values("z")
    return out, sat, refs


rows = []
for run, room, t_list in CASES:
    R = RUNS / run
    mfile = R / "plots_h1" / f"mask_{room}.csv.gz"
    m = pd.read_csv(mfile); m = m[m.snr == 3.0]
    srcs = {}
    if (R / f"stacked_{room}").exists() and (R / f"stacked_{room}" / "analysis").exists() \
            and room in __import__("ledsa_h1_config").rooms(run) and len(__import__("ledsa_h1_config").rooms(run)[room]) == 2:
        srcs["stacked"] = (R / f"stacked_{room}", f"stacked_{room}")
    for d in sorted(R.glob(f"{room}?_*")):
        cam = d.name.split("_")[1]
        if (d / "analysis" / "extinction_coefficients").exists():
            srcs[cam] = (d, cam)
    fig, ax = plt.subplots(2, len(t_list), figsize=(4.2 * len(t_list), 8), squeeze=False)
    for col_i, tp in enumerate(t_list):
        for lab, (base, q) in srcs.items():
            mq = m[m.quelle == q] if q in set(m.quelle) else None
            kd = base / "analysis" / "extinction_coefficients" / "linear"
            for prop, ls in (("farbg_sum_col_val", "-"), ("sum_col_val", ":")):
                cen, v = k_profile(kd / prop, prop, mq, [tp])[tp]
                ax[0, col_i].plot(v, cen, ls, label=f"{lab} {prop.split('_')[0]}")
                rows.append(dict(run=run, room=room, t_s=tp, source=lab, prop=prop,
                                 k_low=np.nanmean(v[cen < 1.25]), k_high=np.nanmean(v[cen >= 1.25]),
                                 k_max=np.nanmax(v), z_kmax=cen[np.nanargmax(v)]))
        ax[0, col_i].set_title(f"{run} {room} t={tp} s: k (Mittel Kanaele)", fontsize=8)
        ax[0, col_i].legend(fontsize=6)
    for lab, (base, q) in srcs.items():
        if lab == "stacked":
            continue
        rel, sat, refs = raw_rel(base, t_list)
        for col_i, tp in enumerate(t_list):
            for a in range(3):
                d = rel[(a, tp)]
                ax[1, col_i].plot(d.rel, d.z, ".", ms=2, label=f"{lab} array {a}")
                nb = (d.rel - d.rel.rolling(5, center=True, min_periods=3).median()).abs()
                bad = d[(d.rel > 1.05) | (nb > 0.15)]
                print(f"{run} {room} {lab} t={tp} Array {a}: I/Iref Median {d.rel.median():.3f}, "
                      f"Ausreisser {len(bad)}: " + ", ".join(f"LED {i} z={r.z:.2f} rel={r.rel:.2f}" for i, r in bad.head(8).iterrows()))
            ax[1, col_i].set_title(f"{lab}: I/I_ref je LED (Bild naechst t)", fontsize=8)
            ax[1, col_i].legend(fontsize=6)
        for a in range(3):
            mx = sat[a]
            print(f"{run} {room} {lab} Referenz {refs[0]}..{refs[-1]} Array {a}: max_col_value max {mx.max():.0f}, "
                  f"p99 {mx.quantile(.99):.0f}, Median {mx.median():.0f}")
    fig.tight_layout(); fig.savefig(OUT / f"outlier_{run}_{room}.png", dpi=90); plt.close(fig)
d = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print(d.round(3).to_string(index=False))
d.to_csv(OUT / "outlier_summary.csv", index=False)
