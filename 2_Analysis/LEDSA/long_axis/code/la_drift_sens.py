# -*- coding: utf-8 -*-
r"""Empfindlichkeit der LEDSA-Ablesung auf eine Bildverschiebung (Langachse, 2026-11-27; Abschaetzung, nicht LEDSA):
im Referenzbild der LED-Suche je LED die Summe der Gruenpixel (beide Bayer-Plaetze, schwarzwertbereinigt) im Quadrat
der Kantenlaenge 2 r + 1 um die LED-Position (r = Suchradius der Kamera, la.CAMS) gegen dasselbe Quadrat um
(dy, dx) px versetzt. Verlust = 1 - S(versetzt) / S(0), Median ueber die LEDs je Streifen; als scheinbare
Extinktion dk ~ -ln(1 - Verlust) / L mit L = Abstand Kamera-Streifen (gleicher Verlust auf allen Strahlen ->
gleichmaessiger Versatz aller Schichten; Naeherung). Ohne Hintergrundabzug (wie sum_col_val).

Aufruf (hh2-venv): python la_drift_sens.py   -> out/la_drift_sens.csv
"""
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rawpy

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
import la  # noqa: E402

SHIFTS = [(1, 0), (0, 1), (2, 0), (0, 2), (3, 0), (0, 3), (2, 2)]
OUT = la.LA / "out" / "la_drift_sens.csv"


def green_full(path):
    with open(path, "rb") as f:
        buf = f.read()
    with rawpy.imread(io.BytesIO(buf)) as r:
        a = r.raw_image_visible.astype(np.float64)
        pat, desc = r.raw_pattern, r.color_desc.decode()
        black = np.asarray(r.black_level_per_channel, dtype=np.float64)
    g = np.zeros_like(a)
    for i in range(2):
        for j in range(2):
            if desc[pat[i, j]] == "G":
                g[i::2, j::2] = np.clip(a[i::2, j::2] - black[pat[i, j]], 0, None)
    return g


def main():
    win = la._csv("la_windows.csv")
    pos = la._csv("la_positions.csv").set_index("position")
    st = la._csv("la_strips.csv").set_index("array")
    rows = []
    for (run, cam), w in win.groupby(["run", "cam"], sort=False):
        s = la.series(run, cam)
        r = la.CAMS[cam]["radius"]
        g = green_full(Path(la.img_path(s.folder_w)) / s.name_string.format(int(w.ref_s1_id.iloc[0])))
        c = pd.read_csv(la.workdir(run, cam) / "analysis" / "led_search_areas_with_coordinates.csv", comment="#",
                        header=None, names=["id", "row", "col", "x", "y", "z", "w", "h"])
        P = pos.loc[s.position]
        for a in (0, 1):
            ids = pd.read_csv(la.workdir(run, cam) / "analysis" / f"led_array_indices_{a:03d}.csv", header=None)[0]
            q = c[c.id.isin(ids)]
            L = float(np.hypot(st.loc[a, "x_m"] - P.x_m, st.loc[a, "y_m"] - P.y_m))

            def box(y, x):
                return g[y - r:y + r + 1, x - r:x + r + 1].sum()
            s0 = np.array([box(int(y), int(x)) for y, x in zip(q.row, q.col)])
            for dy, dx in SHIFTS:
                s1 = np.array([box(int(y) + dy, int(x) + dx) for y, x in zip(q.row, q.col)])
                loss = 1 - s1 / s0
                med = float(np.median(loss))
                rows.append(dict(run=run, cam=cam, array=a, radius_px=r, dy_px=dy, dx_px=dx, n_led=len(q),
                                 loss_med_pct=round(100 * med, 2), loss_p90_pct=round(100 * np.quantile(loss, 0.9), 2),
                                 L_m=round(L, 2), dk_med_per_m=round(-np.log(1 - med) / L, 5)))
        print(f"[ok] {run} {cam}", flush=True)
    d = pd.DataFrame(rows)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write("# la_drift_sens.py: Lichtverlust im LEDSA-Suchquadrat bei Versatz (dy laengs Bildzeile, dx Spalte), "
                "Referenzbild der LED-Suche; dk = -ln(1 - Verlust_Median) / L (Naeherung)\n")
        d.to_csv(f, index=False)
    pd.set_option("display.width", 250)
    print(d.to_string(index=False))


if __name__ == "__main__":
    main()
