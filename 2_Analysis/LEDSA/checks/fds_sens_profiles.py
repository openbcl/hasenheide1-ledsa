"""Welche FDS-Sensitivitaetslaeufe aendern Schichtung / Hoehenprofil der Extinktion? (2026-11-24). Nur lesen.

Quelle: <H1_FDS_ROOT>\\<lauf>\\<lauf>_devc.csv (FDS-Ausgaben, nicht in diesem Repo), Linien-Devices EXT_STRIP_F1..F3
(an der LED-Leiste, 100 Punkte 0,01-2,54 m) und EXT_TREE_F1..F3 (am LEM-Ort). Profil je Zeit = Mittel +-10 s (DT_DEVC 1 s).
Kennzahlen je Lauf, Raum, Linie und Zeit (200/400/600/800 s) gegen eine Referenz:
  scale     Skalenfaktor s, der |k_run - s*k_ref| minimiert (Amplitude; z. B. Russausbeute)
  shape_pct Formabweichung |k_run - s*k_ref| / |k_ref| in % (formbereinigt, skalenfrei)
  z50_run/z50_ref  Hoehe, ab der k (gleitend ueber 5 Punkte geglaettet) dauerhaft >= 50 % seines Maximums liegt
             (Unterkante der Rauchschicht, einfache 50-%-Regel)
  dz50      z50_run - z50_ref [m]
Referenzen: Basis hep_160_075_ysmatched; zusaetzlich hep_160_075_ys030 fuer Laeufe mit bytegleichen RAMP_Q-Zeilen
(Spalte same_ramp). KORREKTUR: die RAMP_Q-Zeilen von ysmatched und ys030/den Sensitivitaets-
decks unterscheiden sich nur durch Rundung in der 4. Nachkommastelle; es gibt keine "aeltere Rampe". ys030 gegen
ysmatched ist eine weitere Rauschprobe; Bezug fuer die Einstufung ist ysmatched. Rauschboden: seed101/202/303 (und
ys030, ysrep_hi/lo, yspooled) gegen ysmatched. dz50_absmax in der Zusammenfassung ueberspringt NaN (nur sootdep_d10).
Aufruf: hh2-venv fds_sens_profiles.py <out.csv>
"""
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

Z = Path(os.environ.get("H1_FDS_ROOT") or sys.exit("[--] H1_FDS_ROOT nicht gesetzt (FDS-Ausgaben, nicht in diesem Repo)"))   # FDS-Ausgaben, nicht im Repo
TIMES = (200, 400, 600, 800)
HALF = 10
LINES = [f"EXT_{k}_{r}" for k in ("STRIP", "TREE") for r in ("F1", "F2", "F3")]


def profiles(run):
    f = Z / run / f"{run}_devc.csv"
    if not f.exists():
        raise SystemExit(f"[--] fehlt {f}")
    head = pd.read_csv(f, nrows=0, header=1).columns
    cols = ["Time"] + [c for c in head if any(re.fullmatch(fr"{l}-\d+", c) for l in LINES)]
    d = pd.read_csv(f, header=1, usecols=cols)
    out = {}
    for l in LINES:
        cs = sorted([c for c in cols if c.startswith(l + "-")], key=lambda c: int(c.rsplit("-", 1)[1]))
        if len(cs) != 100:
            raise SystemExit(f"[--] {run} {l}: {len(cs)} Punkte statt 100")
        for tp in TIMES:
            m = (d.Time >= tp - HALF) & (d.Time <= tp + HALF)
            if m.sum() < 15:
                raise SystemExit(f"[--] {run}: nur {m.sum()} Zeilen um {tp} s")
            out[(l, tp)] = d.loc[m, cs].mean().to_numpy(float)
    return out


ZP = np.linspace(0.01, 2.54, 100)


def z50(k):
    ks = pd.Series(k).rolling(5, center=True, min_periods=1).mean().to_numpy()
    if not np.isfinite(ks).any() or np.nanmax(ks) <= 0:
        return np.nan
    above = ks >= 0.5 * np.nanmax(ks)
    # unterste Hoehe, ab der alle hoeheren Punkte >= 50 % sind
    for i in range(len(ks)):
        if above[i:].all():
            return ZP[i]
    return np.nan


def compare(pr, pf):
    rows = []
    for (l, tp), k in pr.items():
        r = pf[(l, tp)]
        s = float(np.dot(k, r) / np.dot(r, r)) if np.dot(r, r) > 0 else np.nan
        rows.append(dict(line=l, t_s=tp, scale=s, shape_pct=100 * np.linalg.norm(k - s * r) / np.linalg.norm(r),
                         z50_run=z50(k), z50_ref=z50(r), dz50=z50(k) - z50(r), kmax_run=float(k.max()),
                         kmax_ref=float(r.max())))
    return rows


runs = sorted(p.name for p in Z.iterdir() if p.name.startswith("hep_160_075_"))
cache = {}
for r in runs + ["hep_160_075_ysmatched", "hep_160_075_ys030"]:
    if r not in cache:
        cache[r] = profiles(r)
        print(f"  gelesen {r}", flush=True)
ramp = {}
for r in runs:
    txt = (Z / r / f"{r}.fds").read_text(encoding="utf-8", errors="replace")
    ramp[r] = abs(hash(tuple(l for l in txt.splitlines() if "RAMP_Q" in l))) % 10**8
rows = []
for r in runs:
    if r == "hep_160_075_ysmatched":
        continue
    for ref in ("hep_160_075_ysmatched", "hep_160_075_ys030"):
        if ref == r or (ref == "hep_160_075_ys030" and ramp[r] != ramp["hep_160_075_ys030"]):
            continue
        for x in compare(cache[r], cache[ref]):
            rows.append(dict(run=r.replace("hep_160_075_", ""), ref=ref.replace("hep_160_075_", ""),
                             same_ramp=ramp[r] == ramp[ref], **x))
d = pd.DataFrame(rows)
d.to_csv(sys.argv[1], index=False, float_format="%.4f")
pd.set_option("display.width", 220)
g = d[d.line.str.startswith("EXT_STRIP")]
summ = g.groupby(["run", "ref"]).agg(shape_med=("shape_pct", "median"), shape_max=("shape_pct", "max"),
                                     dz50_absmax=("dz50", lambda x: x.abs().max()), scale_med=("scale", "median"),
                                     same_ramp=("same_ramp", "first")).round(3)
print(summ.to_string())
