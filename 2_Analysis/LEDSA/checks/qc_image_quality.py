"""Bildguete aller Kameras (Pruefung Ausschluss C3 R3, 2026-11-25). Nur lesen. Log:
runs/_logs/qc_image_quality.log. Je Serie (Lauf x Kamera, 57 Serien inkl. ausgeschlossener), eigene LEDs, Kanal 0-2
gemittelt:
 - farbg/ref am Serienende (letztes Bild) -> bleibender Lichtverlust (Belag/Beschlag)
 - Fleckform max/Summe relativ zur Referenz: Minimum ueber 0..Lueftung und ueber 100-250 s (alle 50 s), Wert am Ende
 - Sockelanteil ped/sum Maximum
 Referenz = Mittel der Bilder -60..-5 s (bei spaetem Start: erste 5 Bilder). max/Summe ist bei hohem Sockelanteil
kein reines Formmass. farbg_end ist nur aussagekraeftig, wenn die Serie lange nach der Lueftung endet (t_end deutlich > t_vent).
Werte > 1 sind Referenzartefakte (Referenz hier pauschal -60..-5 s, ohne REF_WINDOW_OVERRIDE der Pipeline). Keine
Schwelle: Liste zum Sichten, nicht zum automatischen Ausschluss. Gesaettigte Kanaele werden nicht ausgeschlossen
(gesaettigtes I_ref hebt farbg/ref und max/Summe an und kann einen Verlust verdecken).
Aufruf: hh2-venv checks/qc_image_quality.py <LEDSA-Ordner>"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

L = Path(sys.argv[1]); RUNS = L / "runs"
sys.path.insert(0, str(L))
import ledsa_h1_stage0 as s0


def led(d, iid):
    return pd.read_csv(d / f"{iid}_led_positions.csv", comment="#", header=None, skipinitialspace=True,
                       names=["id", "line", "sum", "avg", "max", "farbg", "ped"]).set_index("id")


ser = pd.read_csv(L / "setup" / "ledsa_h1_series.csv", comment="#")
rows = []
for r in ser.itertuples():
    an = RUNS / r.run / f"{r.position}_{r.cam}" / "analysis"
    if not (an / "image_infos_analysis.csv").exists():
        continue
    info = pd.read_csv(an / "image_infos_analysis.csv"); info.columns = [c.strip("#") for c in info.columns]
    t, ids = info["Experiment_Time[s]"].to_numpy(float), info["ID"].to_numpy(int)
    tv = s0.vent(r.run)
    refsel = ids[(t >= -60) & (t <= -5)]
    if len(refsel) == 0:
        refsel = ids[:5]
    TT = [x for x in range(0, int(tv) + 1, 50)]
    res = {"end": [], "msmin": [], "msearly": [], "msend": [], "ped": []}
    for ch in range(3):
        f0 = an / f"led_array_indices_{ch:03d}.csv"
        d = an / f"channel{ch}"
        if not f0.exists() or not d.exists():
            continue
        own = np.loadtxt(f0, dtype=int, ndmin=1)
        try:
            R = pd.concat([led(d, i) for i in refsel]).groupby(level=0).mean(numeric_only=True)
        except FileNotFoundError:
            continue
        R = R.loc[R.index.isin(own)]
        ms, mse = [], []
        for tp in TT:
            i = int(np.argmin(np.abs(t - tp)))
            if abs(t[i] - tp) > 5:
                continue
            x = led(d, ids[i]).reindex(R.index)
            ms.append(np.median((x["max"] / x["sum"]) / (R["max"] / R["sum"])))
            if 100 <= tp <= 250:
                mse.append(ms[-1])
            res["ped"].append(np.median(x.ped / x["sum"]))
        xe = led(d, ids[-1]).reindex(R.index)
        res["end"].append(np.median(xe.farbg / R.farbg))
        res["msend"].append(np.median((xe["max"] / xe["sum"]) / (R["max"] / R["sum"])))
        if ms:
            res["msmin"].append(np.min(ms))
        if mse:
            res["msearly"].append(np.min(mse))
    rows.append(dict(run=r.run, cam=r.cam, pos=r.position, t_vent=round(tv), t_end=round(float(t[-1])), farbg_end=np.mean(res["end"]),
                     maxsum_min=np.mean(res["msmin"]) if res["msmin"] else np.nan,
                     maxsum_min_100_250=np.mean(res["msearly"]) if res["msearly"] else np.nan, maxsum_end=np.mean(res["msend"]),
                     ped_share_max=np.max(res["ped"]) if res["ped"] else np.nan))
d = pd.DataFrame(rows)
pd.set_option("display.width", 200); pd.set_option("display.max_rows", 200)
print(d.sort_values("farbg_end").round(3).to_string(index=False))
