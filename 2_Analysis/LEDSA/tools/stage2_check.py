# -*- coding: utf-8 -*-
"""Stufe 2 (H1): Pruefung einer Auslese nach run_cam.sh, Anlass Ausfall der Bildablage 2026-11-23 (LEDSA -s3 verwirft unlesbare
Bilder still in analysis/corrupted_images.csv; ein Netzausfall sah so aus wie abgeschnittene Dateien).
ok nur, wenn
  1. je Kanal 0/1/2 Auslesedateien + verworfene Bilder = Zeilen in analysis/image_infos_analysis.csv,
  2. jedes verworfene Bild in inventory/ledsa_h1_juelich_abgeschnitten.csv steht (bekannt abgeschnitten).
Ausgabe eine Zeile; Exit 0 = ok, 1 = FEHLER. Aufruf (hh2-venv): python tools/stage2_check.py <Arbeitsordner>
"""
import sys
from pathlib import Path

import pandas as pd

L = Path(__file__).resolve().parents[1]
w = Path(sys.argv[1])
info = pd.read_csv(w / "analysis" / "image_infos_analysis.csv")
n_img = len(info)
analysed = set(info.iloc[:, 1].astype(str))
cf = w / "analysis" / "corrupted_images.csv"
bad = pd.read_csv(cf) if cf.exists() else pd.DataFrame(columns=["image_path", "error_type", "error_message"])
# LEDSA listet auch Fehler beim Lesen der Metadaten aller Bilder (nicht nur der ausgewerteten); Bildzahl nur ueber die
# ausgewerteten, Bekanntheit ueber alle
bad_all = {Path(p.replace("\\", "/")).name for p in bad.image_path}
bad_names = bad_all & analysed
ab = pd.read_csv(L / "inventory" / "ledsa_h1_juelich_abgeschnitten.csv", comment="#")
known = set(ab["name"])
unknown = sorted(bad_all - known)
counts = [len(list((w / "analysis" / f"channel{c}").glob("*_led_positions.csv"))) for c in (0, 1, 2)]
msg = (f"{w.parent.name} {w.name}: Auslese {counts[0]}/{counts[1]}/{counts[2]} von {n_img} Bildern, verworfen "
       f"{len(bad_names)} ausgewertete / {len(bad_all)} insgesamt (davon unbekannt {len(unknown)})")
problems = []
if any(c + len(bad_names) != n_img for c in counts):
    problems.append("Bildzahl passt nicht")
if unknown:
    problems.append(f"unbekannt verworfen: {', '.join(unknown[:5])}{' ...' if len(unknown) > 5 else ''} "
                    f"({'; '.join(sorted(set(bad.error_type)))})")
if problems:
    print(f"FEHLER {msg}; " + "; ".join(problems))
    sys.exit(1)
print(f"ok {msg}")
