# -*- coding: utf-8 -*-
r"""Kameraverschiebung ueber LED-Schwerpunkte (Langachse, 2026-11-27). Anlass: die Phasenkorrelation des
Streifenbereichs (la_drift.py, Verfahren der Raumauswertung) streut hier je Bild um +-1-2 px und ihr Guetemass liegt
wegen des periodischen LED-Rasters nur bei 1-2 (Test Hep_160_S3_R1 N1), die Repo-Regel ">1 px in >=3 Bildern" ist
damit nicht trennscharf.

Verfahren: Gruenbild halber Aufloesung (drift_regions.green, beide Bayer-Gruenplaetze, schwarzwertbereinigt); je LED
(Positionen der LED-Suche, analysis/led_search_areas_with_coordinates.csv, Sensorpixel) Schwerpunkt im Fenster
+-RAD Halbpixel nach Abzug des 30-%-Perzentils des Fensters, ITER Iterationen mit nachgefuehrtem Fenster; Start je
Bild beim Median-Versatz des zeitlich vorigen Bilds (vom Referenzbild der LED-Suche vorwaerts und rueckwaerts).
Versatz = Schwerpunkt(Bild) - Schwerpunkt(Referenzbild), in Sensorpixeln; je Streifen Median ueber die LEDs mit
Signal >= SIG_MIN x Referenzsignal, dazu MAD und Anzahl. dy = laengs Bildzeile (entlang Streifen), dx = Spalte.

Aufruf (hh2-venv): python la_drift_led.py [<Lauf>:<Kamera> ...] [--workers 4] [--summary-only]
Ausgabe: out/la_drift_led.csv (je Bild und Streifen), out/la_drift_led_summary.csv
"""
import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
import la  # noqa: E402
sys.path.insert(0, str(la.REPO_LEDSA / "tools"))
from drift_regions import green  # noqa: E402

OUT = la.LA / "out" / "la_drift_led.csv"
SUMMARY = la.LA / "out" / "la_drift_led_summary.csv"
RAD, ITER, SIG_MIN, BG_PCT = 2, 3, 0.2, 30   # RAD 2: synthetischer Test 2026-11-27 (RAD 3 bei LED 2 bis 20 % zu klein)
N_MIN = 10
WIN_AFTER_VENT_S = 300.0


def centroids(g, y, x, rad=RAD):
    """Schwerpunkte (Halbpixel) um Startwerte y, x; Rueckgabe y, x, Signal."""
    o = np.arange(-rad, rad + 1)
    oy, ox = np.meshgrid(o, o, indexing="ij")
    oy, ox = oy.ravel(), ox.ravel()
    s = np.zeros(len(y))
    for _ in range(ITER):
        iy, ix = np.rint(y).astype(int), np.rint(x).astype(int)
        iy = np.clip(iy, rad, g.shape[0] - rad - 1)
        ix = np.clip(ix, rad, g.shape[1] - rad - 1)
        w = g[iy[:, None] + oy[None, :], ix[:, None] + ox[None, :]]
        w = np.clip(w - np.percentile(w, BG_PCT, axis=1, keepdims=True), 0, None)
        s = w.sum(axis=1)
        ok = s > 0
        y = np.where(ok, iy + (w * oy).sum(axis=1) / np.where(ok, s, 1), y)
        x = np.where(ok, ix + (w * ox).sum(axis=1) / np.where(ok, s, 1), x)
    return y, x, s


def _chunked(pool, folder, names, n):
    for i in range(0, len(names), n):
        yield from pool.map(lambda m: green(folder / m), names[i:i + n])


def measure(keys, workers):
    win = la._csv("la_windows.csv")
    pool = ThreadPoolExecutor(workers)
    for run, cam in keys:
        t0 = time.time()
        s = la.series(run, cam)
        w = win[(win.run == run) & (win.cam == cam)]
        wd = la.workdir(run, cam) / "analysis"
        folder = Path(la.img_path(s.folder_w))
        info = pd.read_csv(wd / "image_infos_analysis.csv")
        info.columns = ["id", "name", "clock", "t_s"]
        info = info.sort_values("t_s")
        t_ref = float(w.ref_s1_t_s.iloc[0])
        ref_name = s.name_string.format(int(w.ref_s1_id.iloc[0]))
        c = pd.read_csv(wd / "led_search_areas_with_coordinates.csv", comment="#", header=None,
                        names=["id", "row", "col", "x", "y", "z", "w", "h"])
        arr = {a: pd.read_csv(wd / f"led_array_indices_{a:03d}.csv", header=None)[0].tolist() for a in (0, 1)}
        led = pd.concat([c[c.id.isin(ids)].assign(array=a) for a, ids in arr.items()], ignore_index=True)
        # Sensorpixel -> Halbpixel: Halbpixel i deckt Sensorzeilen 2i, 2i+1 (Mitte 2i + 0,5)
        y0, x0 = (led.row.to_numpy(float) - 0.5) / 2, (led.col.to_numpy(float) - 0.5) / 2
        yr, xr, sr = centroids(green(folder / ref_name), y0, x0)
        rows = []
        for part in (info[info.t_s >= t_ref], info[info.t_s < t_ref].iloc[::-1]):
            prev = {a: np.zeros(2) for a in (0, 1)}
            for e, g in zip(part.itertuples(), _chunked(pool, folder, part.name.tolist(), 2 * workers)):
                for a in (0, 1):
                    m = (led.array == a).to_numpy()
                    yi, xi, si = centroids(g, yr[m] + prev[a][0] / 2, xr[m] + prev[a][1] / 2)
                    dy, dx = 2 * (yi - yr[m]), 2 * (xi - xr[m])
                    ok = si >= SIG_MIN * sr[m]
                    n = int(ok.sum())
                    if n >= N_MIN:
                        mdy, mdx = float(np.median(dy[ok])), float(np.median(dx[ok]))
                        prev[a] = np.array([mdy, mdx])
                        mad = float(np.median(np.hypot(dy[ok] - mdy, dx[ok] - mdx)))
                    else:
                        mdy = mdx = mad = np.nan
                    rows.append(dict(run=run, cam=cam, array=a, name=e.name, ref=ref_name, t_ref_s=t_ref, t_s=e.t_s,
                                     dy_px=round(mdy, 3), dx_px=round(mdx, 3), mad_px=round(mad, 3), n_led=n,
                                     n_led_all=int(m.sum())))
        d = pd.DataFrame(rows)
        if OUT.exists():
            old = pd.read_csv(OUT)
            old = old[~((old.run == run) & (old.cam == cam))]
            d = pd.concat([old, d], ignore_index=True)
        d.sort_values(["run", "cam", "array", "t_s"]).to_csv(OUT, index=False)
        print(f"[ok] {run} {cam}: {len(info)} Bilder, {time.time() - t0:.0f} s", flush=True)
    pool.shutdown()


def summarize():
    d = pd.read_csv(OUT)
    runs = pd.read_csv(la.REPO_LEDSA / "setup" / "ledsa_h1_runs.csv", comment="#").set_index("run")
    out = []
    for (run, cam, a), g in d.groupby(["run", "cam", "array"], sort=False):
        g = g.assign(d_px=np.hypot(g.dy_px, g.dx_px))
        vent = float(runs.loc[run, "ventilation_s"])
        w = g[(g.t_s >= -30) & (g.t_s <= vent + WIN_AFTER_VENT_S)]
        v = w.dropna(subset=["dy_px"])
        pre = g[(g.t_s < -30)].dropna(subset=["dy_px"])
        out.append(dict(run=run, cam=cam, array=a, ventilation_s=vent, n_fenster=len(w), n_gemessen=len(v),
                        max_d_px=round(v.d_px.max(), 2) if len(v) else np.nan,
                        p95_d_px=round(v.d_px.quantile(0.95), 2) if len(v) else np.nan,
                        min_dy_px=round(v.dy_px.min(), 2) if len(v) else np.nan,
                        max_dy_px=round(v.dy_px.max(), 2) if len(v) else np.nan,
                        min_dx_px=round(v.dx_px.min(), 2) if len(v) else np.nan,
                        max_dx_px=round(v.dx_px.max(), 2) if len(v) else np.nan,
                        mad_med_px=round(v.mad_px.median(), 2) if len(v) else np.nan,
                        max_d_vor_px=round(pre.d_px.max(), 2) if len(pre) else np.nan,
                        t_letzt_gemessen_s=v.t_s.max() if len(v) else np.nan))
    sm = pd.DataFrame(out)
    with open(SUMMARY, "w", encoding="utf-8", newline="") as f:
        f.write(f"# la_drift_led.py: LED-Schwerpunkte gegen Referenzbild der LED-Suche, Median je Streifen, Sensorpixel; "
                f"Fenster -30 s bis Lueftung + {WIN_AFTER_VENT_S:.0f} s; gemessen = >= {N_MIN} LEDs mit Signal >= "
                f"{SIG_MIN} x Referenz; max_d_vor = vor -30 s\n")
        sm.to_csv(f, index=False)
    pd.set_option("display.width", 250)
    print(sm.to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("keys", nargs="*")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--summary-only", action="store_true")
    a = ap.parse_args()
    if not a.summary_only:
        s = la._csv("la_series.csv")
        keys = [tuple(k.split(":")) for k in a.keys] or list(zip(s.run, s.cam))
        measure(keys, a.workers)
    summarize()
