# -*- coding: utf-8 -*-
"""Stufe 2 (H1): Reihenfolge der Auslese aller Serien, Ausgabe je Zeile "<Lauf>:<Kamera> <Gruppe>".
Gruppen (2026-11-20/21): 1 = nachzufuehren (setup/ledsa_h1_tracking.csv, zuerst, damit die Nachfuehrung parallel
laufen kann), 2 = uebrige ohne abgeschnittene Dateien, 3 = Juelich-Serien mit abgeschnittenen RAWs im Bildbereich
(inventory/ledsa_h1_juelich_abgeschnitten.csv; zuletzt; Luecken bleiben, bis unbeschaedigte Originale vorliegen).
Aufruf (hh2-venv, im Ordner 2_Analysis/LEDSA): python tools/stage2_order.py [--summary]
"""
import re
import sys
from pathlib import Path

import pandas as pd

L = Path(__file__).resolve().parents[1]
s = pd.read_csv(L / "setup" / "ledsa_h1_series.csv", comment="#")
tr = pd.read_csv(L / "setup" / "ledsa_h1_tracking.csv", comment="#")
track = {(r.run, r.cam) for r in tr.itertuples() if str(r.nachfuehren).strip().lower() == "ja"}
ab = pd.read_csv(L / "inventory" / "ledsa_h1_juelich_abgeschnitten.csv", comment="#")
ab["id"] = ab["name"].str.extract(r"(\d+)\.CR[23]$", expand=False).astype(int)

rows = []
for r in s.itertuples():
    n_ab = 0
    if "2_juelichMeasurements" in r.folder_w:
        f = Path(r.folder_w)
        a = ab[(ab.tag == f.parent.name) & (ab.kamera == f.name)]
        lo, hi = int(r.first_id), int(r.last_id)
        n_ab = int(a.id.between(lo, hi).sum()) if lo <= hi else int(((a.id >= lo) | (a.id <= hi)).sum())
    grp = 1 if (r.run, r.cam) in track else (3 if n_ab else 2)
    rows.append((grp, r.run, r.cam, n_ab))
o = pd.DataFrame(rows, columns=["grp", "run", "cam", "n_abgeschnitten"]).sort_values(["grp", "run", "cam"], kind="stable")
if len(o) != len(s) or len({(a, b) for a, b in zip(o.run, o.cam)}) != len(s):
    raise SystemExit("[--] Serienliste nicht eindeutig")
if "--summary" in sys.argv:
    print(o.to_string(index=False))
    print(o.groupby("grp").size().to_dict(), "Serien je Gruppe;", int((o.n_abgeschnitten > 0).sum()),
          "Serien mit abgeschnittenen Dateien im Bildbereich")
else:
    for r in o.itertuples():
        print(f"{r.run}:{r.cam} {r.grp}")
