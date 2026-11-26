"""Transmissionskennzahl (Rechenweg vom 2026-11-25, archiviert): Minimum ueber
230-300 s des LED-Medians farbg/I_ref (I_ref = Mittel der Referenzbilder der Pipeline aus config_analysis.ini), LEDs
mit z >= 2 m; Varianten eigene LEDs / alle LEDs; je Kanal; Mittel der Kanaele. Nur lesen. Log:
runs/_logs/transmission_low_cams.log. Aufruf: hh2-venv checks/transmission_low_cams.py <LEDSA-Ordner>"""
import configparser
import sys
from pathlib import Path
import numpy as np
import pandas as pd
L = Path(sys.argv[1])


def led(d, iid):
    a = np.loadtxt(d / f"{iid}_led_positions.csv", delimiter=",", comments="#", ndmin=2)
    return pd.Series(a[:, 5], index=a[:, 0].astype(int))


for run in ("Hep_220_S1_R1", "Hep_220_S1_R2", "Hep_220_S1_R3", "Hep_220_S1_R4"):
    for pos in ("F2L_C3", "F1L_C2"):
        w = L / "runs" / run / pos
        if not w.exists():
            continue
        an = w / "analysis"
        cp = configparser.ConfigParser(inline_comment_prefixes="#"); cp.read(w / "config_analysis.ini")
        sec = [s for s in cp.sections() + ["DEFAULT"] if cp.has_option(s, "ref_img_indices")][0]
        ref = [int(x) for x in cp.get(sec, "ref_img_indices").split()]
        info = pd.read_csv(an / "image_infos_analysis.csv"); info.columns = [c.strip("#") for c in info.columns]
        t, ids = info["Experiment_Time[s]"].to_numpy(float), info["ID"].to_numpy(int)
        sel = ids[(t >= 230) & (t <= 300)]
        coord = np.loadtxt(an / "led_search_areas_with_coordinates.csv", delimiter=",", ndmin=2)
        z = pd.Series(coord[:, 5], index=coord[:, 0].astype(int))
        out = {}
        for ch in range(3):
            d = an / f"channel{ch}"
            own = set(np.loadtxt(an / f"led_array_indices_{ch:03d}.csv", dtype=int, ndmin=1))
            R = pd.concat([led(d, i) for i in ref], axis=1).mean(axis=1)
            for var in ("own", "all"):
                keep = [i for i in R.index if z.get(i, -1) >= 2.0 and (var == "all" or i in own)]
                vals = [np.median(led(d, i).reindex(keep) / R.reindex(keep)) for i in sel]
                out[(var, ch)] = (min(vals), max(vals))
        s = "; ".join(f"{v} ch{c} min {a*100:.2f} max {b*100:.2f}" for (v, c), (a, b) in out.items())
        mo = np.mean([out[("own", c)][0] for c in range(3)]); ma = np.mean([out[("all", c)][0] for c in range(3)])
        print(f"{run} {pos} n_img={len(sel)}: {s} | Mittel Kanaele min own {mo*100:.2f} all {ma*100:.2f}")
