# -*- coding: utf-8 -*-
r"""Leserauschen der LED-Box-Summe je Lauf, Kamera und Kanal (Gueltigkeitsmaske, METHODS.md section 4.4).
Uebernommen aus der Hasenheide-2-Auswertung (dort ein Kanal) auf die drei Kanaele der H1-Auswertung.

Formel wie LEDSA 0.12.0 (noise_sum_col_value, in 0.13.0 entfernt; Test in der Hasenheide-2-Auswertung: je LED ueber den Lauf praktisch konstant):
    sigma_sum = sqrt( sum_c n_c (sigma_c s_c)^2 ),  s_c = Weiss / (Weiss - Schwarz_c)
sigma_c / Schwarz_c = Standardabweichung / Mittel des optischen Schwarz (linker Sensorrand) je Bayer-Farbe,
n_c = Pixel der Bayer-Farbe c in der 2R x 2R-Box (Kanal 1 = beide Gruen je R^2, Kanal 0/2 = R^2). Mittel ueber die
Referenzbilder (ref_img_indices der config_analysis.ini, sonst die ersten 10 Analysebilder). Ohne optischen Rand
(< 8 px, wie LEDSA) NaN. Alle Kameras der Stufe A (C1-C3, J1-J3) haben einen Rand (Pruefung 2026-11-20: 144-264 px).
Ausgabe: inventory/ledsa_h1_read_noise.csv (Zeilen je (Lauf, Kamera, Kanal), vorhandene ersetzt).
Aufruf (Conda-Env ledsa, rawpy): python ledsa_h1_noise.py <Lauf> <Kamera> [<Kamera> ...]
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rawpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ledsa_h1_config import series, workdir   # noqa: E402
from ledsa_h1_paths import img_path   # noqa: E402

OUT = HERE / "inventory" / "ledsa_h1_read_noise.csv"
MIN_OPTICAL_BLACK_WIDTH = 8
N_FALLBACK = 10
COLORS = {0: (0,), 1: (1, 3), 2: (2,)}           # raw_colors: 0 R, 1 G, 2 B, 3 G2


def optical_black(path):
    with rawpy.imread(str(path)) as raw:
        sz = raw.sizes
        if sz.left_margin < MIN_OPTICAL_BLACK_WIDTH:
            return None
        rows = np.s_[sz.top_margin:sz.top_margin + sz.height]
        m = raw.raw_image[rows, :sz.left_margin].astype(np.float64)
        col = raw.raw_colors[rows, :sz.left_margin]
        mean = np.array([m[col == c].mean() for c in range(4)])
        std = np.array([m[col == c].std() for c in range(4)])
        white = float(raw.white_level)
    return std, white / (white - mean)


def noise(run, cam):
    r, work = series(run, cam), workdir(run, cam)
    R = int(re.search(r"search_area_radius = (\d+)", (work / "config.ini").read_text(encoding="utf-8")).group(1))
    info = pd.read_csv(work / "analysis" / "image_infos_analysis.csv")
    info.columns = ["img_id", "name", "time", "t_exp"]
    ca = work / "config_analysis.ini"
    m = re.search(r"ref_img_indices = ([\d ]+)\s*$", ca.read_text(encoding="utf-8"), re.M) if ca.exists() else None
    ids = [int(v) for v in m.group(1).split()] if m else info.img_id.head(N_FALLBACK).tolist()
    vals = {ch: [] for ch in COLORS}
    for name in info.set_index("img_id").loc[ids, "name"]:
        ob = optical_black(Path(img_path(r.folder_w)) / name)
        if ob is None:
            break
        std, scale = ob
        for ch, cs in COLORS.items():
            vals[ch].append(np.sqrt(sum(R * R * (std[c] * scale[c]) ** 2 for c in cs)))
    rows = []
    for ch, v in vals.items():
        v = np.array(v)
        rows.append(dict(run=run, cam=cam, channel=ch, radius_px=R, n_img=len(v),
                         sigma_sum=float(v.mean()) if len(v) else np.nan,
                         cv=float(v.std() / v.mean()) if len(v) > 1 else np.nan, optical_black=len(v) > 0,
                         ref_from="config_analysis" if m else "erste 10"))
        print(f"  {run} {cam} Kanal {ch}: R {R}, {len(v)} Bilder, sigma_sum "
              + (f"{rows[-1]['sigma_sum']:.2f} (VK {rows[-1]['cv']:.3f})" if len(v) else "- (kein optisches Schwarz)"))
    return rows


def main(run, *cams):
    if not cams:
        raise SystemExit("Aufruf: ledsa_h1_noise.py <Lauf> <Kamera> [...]")
    new = pd.DataFrame([row for c in cams for row in noise(run, c)])
    key = ["run", "cam", "channel"]
    old = pd.read_csv(OUT, comment="#") if OUT.exists() else pd.DataFrame(columns=new.columns)
    keep = old[~old.set_index(key).index.isin(new.set_index(key).index)] if len(old) else old
    d = pd.concat([keep, new], ignore_index=True).sort_values(key)
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        fh.write("# ledsa_h1_noise.py: Leserauschen der Box-Summe je Kanal (optisches Schwarz, Formel LEDSA 0.12.0), "
                 "Mittel ueber die Referenzbilder; NaN = kein optisches Schwarz\n")
        d.to_csv(fh, index=False, float_format="%.4g")
    print(f"[ok] {OUT}")


if __name__ == "__main__":
    main(*sys.argv[1:])
