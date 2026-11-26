"""Lichtverlust-Kriterium (Ausschluss C3 Hep_220_S1_R3 F2, METHODS.md section 4.6) auf alle Serien angewandt (Rechenweg vom
2026-11-25, archiviert). Nur lesen. Log: runs/_logs/sister_light_ratio.log.
Je Serie: farbg/ref (Median ueber eigene LEDs, Kanal 0-2 gemittelt), ref = Mittel der Bilder -60..-5 s (sonst erste 5),
zu Zeiten 300..min(Lueftung-20, 1150) s alle 50 s; dazu 5 Hoehenbaender. Dann Verhaeltnis zum Median der Schwesterserien
(gleiche Konfiguration, gleiche Position, gleiche Kamera). Grenzen: Stoerungen, die alle Schwestern teilen, findet der
Vergleich nicht; eine Serie mit kaputter Referenz verfaelscht das Verhaeltnis ihrer Schwestern.
Referenz pauschal -60..-5 s (ohne REF_WINDOW_OVERRIDE/REF_T_MAX_OVERRIDE der Pipeline); gesaettigte Kanaele nicht
ausgeschlossen (gesaettigtes I_ref kann einen Verlust verdecken).
Aufruf: hh2-venv checks/sister_light_ratio.py <LEDSA-Ordner>"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

L = Path(sys.argv[1]); RUNS = L / "runs"
runs = pd.read_csv(L / "setup" / "ledsa_h1_runs.csv", comment="#").set_index("run")
ser = pd.read_csv(L / "setup" / "ledsa_h1_series.csv", comment="#")
CFG = lambda r: "Hep_220_300" if r.startswith("Hep_220_S1") else ("Hep_160_150" if r.startswith("Hep_160_S1") else "Hep_160_075")


def led(d, iid):
    a = np.loadtxt(d / f"{iid}_led_positions.csv", delimiter=",", comments="#", ndmin=2)
    return pd.DataFrame({"farbg": a[:, 5], "sum": a[:, 2], "ped": a[:, 6]}, index=a[:, 0].astype(int))


rows = []
for r in ser.itertuples():
    an = RUNS / r.run / f"{r.position}_{r.cam}" / "analysis"
    if not (an / "image_infos_analysis.csv").exists():
        continue
    info = pd.read_csv(an / "image_infos_analysis.csv"); info.columns = [c.strip("#") for c in info.columns]
    t, ids = info["Experiment_Time[s]"].to_numpy(float), info["ID"].to_numpy(int)
    tv = float(runs.loc[r.run, "ventilation_s"])
    refsel = ids[(t >= -60) & (t <= -5)]
    if len(refsel) == 0:
        refsel = ids[:5]
    coord = np.loadtxt(an / "led_search_areas_with_coordinates.csv", delimiter=",", ndmin=2)
    zled = pd.Series(coord[:, 5], index=coord[:, 0].astype(int))
    TT = list(range(300, int(min(tv - 20, 1150)) + 1, 50))
    acc = {tp: {"all": [], **{b: [] for b in range(5)}} for tp in TT}
    for ch in range(3):
        f0 = an / f"led_array_indices_{ch:03d}.csv"; d = an / f"channel{ch}"
        if not f0.exists():
            continue
        own = np.loadtxt(f0, dtype=int, ndmin=1)
        try:
            R = pd.concat([led(d, i) for i in refsel]).groupby(level=0).mean()
        except (FileNotFoundError, OSError):
            continue
        R = R.loc[R.index.isin(own)]
        bands = pd.cut(zled.reindex(R.index), 5, labels=False)
        for tp in TT:
            i = int(np.argmin(np.abs(t - tp)))
            if abs(t[i] - tp) > 5:
                continue
            x = led(d, ids[i]).reindex(R.index)
            q = x.farbg / R.farbg
            acc[tp]["all"].append(np.median(q))
            for b, g in q.groupby(bands):
                acc[tp][int(b)].append(np.median(g))
    for tp in TT:
        rec = dict(config=CFG(r.run), run=r.run, cam=r.cam, pos=r.position, t=tp)
        for k, v in acc[tp].items():
            rec[f"q_{k}"] = np.mean(v) if v else np.nan
        rows.append(rec)
d = pd.DataFrame(rows)
res = []
for (cfg, pos, cam), g in d.groupby(["config", "pos", "cam"]):
    rr = g.run.unique()
    for run in rr:
        own = g[g.run == run].set_index("t")
        oth = g[g.run != run]
        if oth.empty:
            res.append(dict(config=cfg, pos=pos, cam=cam, run=run, n_sis=0)); continue
        med = oth.groupby("t")[[c for c in g.columns if c.startswith("q_")]].median()
        rat = (own[med.columns] / med).dropna(how="all")
        rec = dict(config=cfg, pos=pos, cam=cam, run=run, n_sis=len(rr) - 1, n_t=len(rat),
                   ratio_med=rat.q_all.median(), ratio_min=rat.q_all.min(), ratio_max=rat.q_all.max(),
                   frac_t_below_05=(rat.q_all < 0.5).mean())
        bm = rat[[f"q_{b}" for b in range(5)]].median()
        rec["band_min"], rec["band_max"] = bm.min(), bm.max()
        res.append(rec)
e = pd.DataFrame(res).sort_values("ratio_med")
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 300)
print(e.round(3).to_string(index=False))
