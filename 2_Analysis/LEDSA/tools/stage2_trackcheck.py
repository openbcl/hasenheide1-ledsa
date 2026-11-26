# -*- coding: utf-8 -*-
"""Stufe 2 (H1): Plausibilitaet einer Nachfuehrung (analysis/tracking_log.csv), Anlass 2026-11-23: J1 Hep_160_S1_R2
rutschte im Rauch um einen LED-Abstand (+17 bis +21 px laengs), obwohl die Kamera stand (Lagecheck 0,0 px, PSR 25).
Prueft
  1. Spruenge: Aenderung der mittleren Verschiebung zwischen aufeinanderfolgenden Bildern > JUMP_FRAC x LED-Abstand,
  2. Abgleich mit dem Lagecheck (inventory/ledsa_h1_drift.csv): an Survey-Bildern mit PSR >= PSR_MIN und |Verschiebung|
     < ALIAS_MAX (groessere Werte sind meist Aliase) Abweichung Nachfuehrung - Survey > TOL_PX.
Ausgabe je Serie eine Zeile ok/FEHLER plus Details; Exit 1 bei einem FEHLER.
Aufruf (hh2-venv, im Ordner 2_Analysis/LEDSA): python tools/stage2_trackcheck.py <Lauf>:<Kamera> [...]
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

L = Path(__file__).resolve().parents[1]
JUMP_FRAC, PSR_MIN, ALIAS_MAX, TOL_PX = 0.5, 15.0, 12.0, 2.0
s = pd.read_csv(L / "setup" / "ledsa_h1_series.csv", comment="#")
# Abgleich mit dem genauen Lagecheck (ledsa_h1_drift_fine.py, 2026-11-23; der alte rastet an 4-px-Vielfachen ein),
# nur verlaessliche Bilder (kein Randtreffer, Guete >= 1)
drift = pd.read_csv(L / "inventory" / "ledsa_h1_drift_fine.csv")
drift = drift[(drift.rand == 0) & (drift.quality >= 1.0)].assign(psr=np.inf)
ALIAS_MAX = np.inf
FRAC_MIN = 0.5      # Bilder mit weniger nachgerueckten LEDs (verdeckt/dunkel) gesondert, nicht als Sprung
bad_any = False
for rc in sys.argv[1:]:
    run, cam = rc.split(":")
    r = s[(s.run == run) & (s.cam == cam)].iloc[0]
    w = L / "runs" / run / f"{r.position}_{cam}" / "analysis"
    log_all = pd.read_csv(w / "tracking_log.csv").sort_values("img_id").reset_index(drop=True)
    blind = log_all[log_all.frac_refined < FRAC_MIN]
    log = log_all[log_all.frac_refined >= FRAC_MIN].reset_index(drop=True)
    pos = pd.read_csv(w / "tracked_positions.csv.gz")
    first = pos[pos.img_id == pos.img_id.min()].sort_values("row")
    dr = np.diff(first.row.to_numpy())
    dr = dr[dr > 5]                       # drei Streifen verschraenkt: Nachbarn gleicher Hoehe liegen < 5 px auseinander
    pitch = float(np.median(dr)) if len(dr) else 18.0
    pitch = pitch if 5 < pitch < 60 else 18.0
    d_row, d_col = np.diff(log.shift_row.to_numpy()), np.diff(log.shift_col.to_numpy())
    jumps = np.flatnonzero((np.abs(d_row) > JUMP_FRAC * pitch) | (np.abs(d_col) > JUMP_FRAC * pitch))
    ref_name = r.name_string.format(int(r.ref_s1_id))    # Survey nur vergleichbar, wenn gegen dasselbe Bild gemessen
    dv = drift[(drift.run == run) & (drift.cam == cam) & (drift.ref == ref_name) & (drift.psr >= PSR_MIN)
               & (drift.dy_px.abs() < ALIAS_MAX) & (drift.dx_px.abs() < ALIAS_MAX)]
    m = dv.merge(log, on="name", how="inner")
    # Survey misst gegen das Referenzbild der LED-Suche, die Nachfuehrung gegen pos0 (gleiches Bild) -> direkt vergleichbar
    dev = m.assign(e_row=(m.shift_row - m.dy_px).abs(), e_col=(m.shift_col - m.dx_px).abs())
    off = dev[(dev.e_row > TOL_PX) | (dev.e_col > TOL_PX)]
    ok = len(jumps) == 0 and len(off) == 0
    bad_any |= not ok
    print(f"{'ok' if ok else 'FEHLER'} {run} {cam}: {len(log)} Bilder, LED-Abstand {pitch:.0f} px, Verschiebung "
          f"laengs {log.shift_row.min():+.1f}..{log.shift_row.max():+.1f}, quer {log.shift_col.min():+.1f}.."
          f"{log.shift_col.max():+.1f} px; Spruenge > {JUMP_FRAC:.1f} Abstand: {len(jumps)}; Survey-Abgleich "
          f"{len(m)} Bilder, Abweichung > {TOL_PX:.0f} px: {len(off)}; ohne gefundene LEDs (< {FRAC_MIN:.0%} "
          f"nachgerueckt): {len(blind)}{' bei t ' + ', '.join(f'{v:.0f}' for v in blind.t_exp[:6]) + ' s' if len(blind) else ''}")
    for k in jumps[:5]:
        print(f"   Sprung {log.name[k]} -> {log.name[k + 1]} (t {log.t_exp[k]:.0f} -> {log.t_exp[k + 1]:.0f} s): "
              f"{d_row[k]:+.1f} / {d_col[k]:+.1f} px")
    for e in off.head(5).itertuples():
        print(f"   {e.name} (t {e.t_exp:.0f} s): Nachfuehrung {e.shift_row:+.1f}/{e.shift_col:+.1f}, Survey "
              f"{e.dy_px:+.1f}/{e.dx_px:+.1f} px (PSR {e.psr:.0f})")
sys.exit(1 if bad_any else 0)
