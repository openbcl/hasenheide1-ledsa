# -*- coding: utf-8 -*-
"""LED-Hoehen je LED nach Index bei gleicher Teilung (festgelegt 2026-11-24).

LEDSA 0.13.0 (-coord, ledpositions/coordinates.py) setzt die 3D-Lage jeder LED linear nach dem Pixelabstand zwischen
den beiden End-LEDs (affine Abbildung, ohne Perspektive). Bei geneigter Kamera ist die Abbildung projektiv: die
mittleren LEDs liegen bei unteren Kameras 10-44 mm zu hoch, bei oberen 31-45 mm zu tief (Pruefung
2026-11-24, alle Arrays), im Stapel bekommt dieselbe LED in beiden Kameras bis 8 cm verschiedene Hoehen.
Wird -coord erneut ausgefuehrt, erkennt das Skript die frische LEDSA-Datei an der fehlenden Kennung in der Kopfzeile
und erneuert die Sicherung; geschrieben wird nur bei geaendertem Inhalt. Die LEDs eines Streifens haben aber
gleiche Teilung. Dieses Skript schreibt analysis/led_search_areas_with_coordinates.csv je Kamera neu:
  z = z_top - (skip_top + k) * (z_top - z_bottom) / (n_leds - 1),  x, y = Streifen laut setup/ledsa_h1_led_strips.csv,
k = Index der LED ab der obersten gefundenen LED entlang des Streifens (Bildzeile = erste Pixelkoordinate aufsteigend;
Luecken = nicht gefundene LEDs werden aus dem Pixelabstand gegen die oertliche Teilung erkannt und mitgezaehlt).
Spalte 'height' (2D) = z, 'width' bleibt. Das LEDSA-Original wird als led_search_areas_with_coordinates_ledsa.csv
gesichert, sobald die aktuelle Datei frische LEDSA-Ausgabe ist (ohne Kennung MARK in der Kopfzeile); sonst ist die
Sicherung die Quelle (idempotent). Fehlt die Sicherung bei schon korrigierter Datei -> Abbruch.
Pruefungen: letzte LED muss Index n_leds - 1 - skip_bottom treffen; Pixelspalten der Sicherung = led_search_areas.csv;
Abbruch sonst.
Streifenenden: setup/ledsa_h1_led_strips.csv (Juelich-Streifen 2026-11-24 korrigiert, s. ledsa_h1_setup.py).
Aufruf: ledsa_h1_ledz.py <Lauf> <Kamera> | all      (hh2-venv)
"""
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ledsa_h1_config import RUNS, _csv, series, windows, workdir   # noqa: E402

GAP_FACTOR = 1.5
MARK = "ledsa_h1_ledz.py"                  # Kennung in der Kopfzeile der korrigierten Datei


def fix(run, cam, verbose=True):
    r = series(run, cam)
    work = workdir(run, cam)
    a_dir = work / "analysis"
    cur = a_dir / "led_search_areas_with_coordinates.csv"
    orig = a_dir / "led_search_areas_with_coordinates_ledsa.csv"
    if not cur.exists():
        raise SystemExit(f"[--] fehlt {cur} (-coord)")
    # Sicherung erneuern, wenn die aktuelle Datei frische LEDSA-Ausgabe ist (-coord erneut gelaufen)
    with open(cur, encoding="utf-8") as fh:
        fresh = MARK not in fh.readline()
    if not fresh and not orig.exists():
        raise SystemExit(f"[--] {orig} fehlt, aktuelle Datei ist schon korrigiert -> -coord neu ausfuehren")
    if fresh:
        orig.write_bytes(cur.read_bytes())
    c = np.loadtxt(orig, delimiter=",", ndmin=2)
    if not np.array_equal(c[:, 0], np.arange(len(c))):
        raise SystemExit(f"[--] {orig}: LED-IDs nicht 0..N-1 (LEDSA liest die Zeile = ID)")
    sa = np.loadtxt(a_dir / "led_search_areas.csv", delimiter=",", ndmin=2)
    if sa.shape[0] != c.shape[0] or not np.array_equal(sa[:, :3], c[:, :3]):
        raise SystemExit(f"[--] {orig}: Pixelpositionen passen nicht zu led_search_areas.csv (Sicherung veraltet?)")
    st = _csv("ledsa_h1_led_strips.csv")
    st = st[st.room == r.room].set_index("array")
    w = windows(run, cam).set_index("array")
    out = c.copy()
    done = set()
    for a in st.index:
        ids = np.loadtxt(a_dir / f"led_array_indices_{a:03d}.csv", dtype=int, ndmin=1)
        p = st.loc[a]
        n_led, sk_t, sk_b = int(w.loc[a, "n_leds"]), int(w.loc[a, "skip_top"]), int(w.loc[a, "skip_bottom"])
        row = c[ids, 1]
        o = np.argsort(row)                       # oben zuerst (kleinste erste Pixelkoordinate, wie set_edges)
        ids_o, row_o = ids[o], row[o]
        d = np.diff(row_o)
        loc = pd.Series(d).rolling(9, center=True, min_periods=3).median().to_numpy()
        step = np.where(d > GAP_FACTOR * loc, np.rint(d / loc), 1).astype(int)
        k = np.concatenate([[0], np.cumsum(step)])
        if k[-1] != n_led - 1 - sk_t - sk_b:
            raise SystemExit(f"[--] {run} {cam} Array {a}: letzter Index {k[-1]} != {n_led - 1 - sk_t - sk_b} "
                             f"({len(ids)} LEDs gefunden, Luecken {int((step > 1).sum())})")
        pitch = (p.z_top_m - p.z_bottom_m) / (n_led - 1)
        z = p.z_top_m - (sk_t + k) * pitch
        dz = z - c[ids_o, 5]
        out[ids_o, 3], out[ids_o, 4], out[ids_o, 5], out[ids_o, 7] = p.x_m, p.y_m, z, z
        done |= set(ids_o.tolist())
        if verbose:
            print(f"  {run} {cam} Array {a}: {len(ids)} LEDs, Luecken {int((step > 1).sum())}, z {z.min():.4f}-"
                  f"{z.max():.4f} m, Aenderung gegen LEDSA {1000 * dz.min():+.0f}...{1000 * dz.max():+.0f} mm")
    if len(done) != len(c):
        print(f"  [!] {run} {cam}: {len(c) - len(done)} LEDs in keinem Array (unveraendert)")
    buf = io.StringIO()
    buf.write("# LED id, pixel position x, pixel position y, x, y, z, width, height  "
              f"(z nach LED-Index bei gleicher Teilung: {MARK}; LEDSA-Original *_ledsa.csv)\n")
    np.savetxt(buf, out, fmt="%d,%d,%d,%f,%f,%f,%f,%f")
    new = buf.getvalue().encode("utf-8")
    # nur bei geaendertem Inhalt schreiben (sonst baut LEDSA die Binaerdaten wegen neuerer mtime neu)
    if cur.read_bytes() != new:
        cur.write_bytes(new)
    elif verbose:
        print(f"  {run} {cam}: unveraendert")


if __name__ == "__main__":
    if sys.argv[1] == "all":
        s = _csv("ledsa_h1_series.csv")
        for r in s.itertuples():
            if (workdir(r.run, r.cam) / "analysis" / "led_search_areas_with_coordinates.csv").exists():
                fix(r.run, r.cam)
    else:
        fix(sys.argv[1], sys.argv[2])
