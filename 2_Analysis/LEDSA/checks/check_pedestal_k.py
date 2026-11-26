"""Fernfeld-Sockel, Wirkung auf k: je Lauf und Kamera (Einzelinversion) Spitze und Plateau an den LEM-Hoehen des Raums nach
Paper-Methode (ohne Maske, gleich fuer beide), farbg_sum_col_val (Sockel abgezogen) gegen sum_col_val (ohne Abzug).
Daneben der Sockelanteil aus inventory/ledsa_h1_pedestal_check.csv (Median ueber Arrays). Nur lesen.
Aufruf: hh2-venv check_pedestal_k.py <LEDSA-Ordner> <out.csv>"""
import sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(sys.argv[1]); sys.path.insert(0, str(HERE))
import ledsa_h1_stage0 as s0
from ledsa_h1_config import RUNS, rooms

ped = pd.read_csv(HERE / "inventory" / "ledsa_h1_pedestal_check.csv", comment="#")
runs = pd.read_csv(HERE / "setup" / "ledsa_h1_runs.csv", comment="#").run
rows = []
for run in runs:
    tv = s0.vent(run)
    for room, cams in rooms(run).items():
        L = s0.lem(run, room)
        H = sorted(L) or [2.3]
        for cam in cams:
            d = [p for p in (RUNS / run).glob(f"*_{cam}")][0]
            base = d / "analysis" / "extinction_coefficients" / "linear"
            if not (base / "farbg_sum_col_val").exists():
                continue
            a = s0.room_series(base / "farbg_sum_col_val", "farbg_sum_col_val", H)
            b = s0.room_series(base / "sum_col_val", "sum_col_val", H)
            pc = ped[(ped.run == run) & (ped.cam == cam)]
            for h in H:
                ma, mb = s0.metrics(a[h], tv), s0.metrics(b[h], tv)
                rows.append(dict(run=run, room=room, cam=cam, z_m=h,
                                 ped_med_pct=round(pc.ped_frac_median_pct.median(), 2),
                                 ped_red_pct=round(pc[pc.array == 0].ped_frac_median_pct.iloc[0], 2) if len(pc) else np.nan,
                                 peak_farbg=round(ma["peak"], 3), peak_sum=round(mb["peak"], 3),
                                 plat_farbg=round(ma["plateau"], 3), plat_sum=round(mb["plateau"], 3),
                                 peak_ratio=round(ma["peak"] / mb["peak"], 3),
                                 plat_ratio=round(ma["plateau"] / mb["plateau"], 3)))
out = pd.DataFrame(rows)
out.to_csv(sys.argv[2], index=False)
pd.set_option("display.width", 200)
print(out.to_string(index=False))
print("\nJe Kamera: Verhaeltnis farbg/sum (Spitze, Plateau) Median und Spanne")
print(out.groupby("cam")[["ped_med_pct", "peak_ratio", "plat_ratio"]].agg(["median", "min", "max"]).round(3).to_string())
