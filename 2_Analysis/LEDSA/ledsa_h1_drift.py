# -*- coding: utf-8 -*-
r"""Kameralage aller H1-LEDSA-Serien (Stichprobe) gegen das Referenzbild der LED-Suche, uebernommen
aus der Hasenheide-2-Auswertung (dort Methode, Validierung und Wahl von PSR_MIN, LAMBDA_PX, OUTLIER_PX begruendet).

Anlass (Stufe 0, 2026-11-20): J1 in Hep_220_S1_R1 vor der Zuendung bewegt (LEDs bei -19 s nicht mehr in den Boxen
des Referenzbilds bei -476 s) und am Laufende nur 31 % der LEDs wiedergefunden; C1 Hep_160_S4_R1 -6/+3 px, C1
Hep_220_S1_R1 +6 px quer am Ende. LEDSA -s3 setzt feste Suchbereiche (Radius 10 px) voraus.

Verfahren wie in der Hasenheide-2-Auswertung: Bayer-Gruen, 2x2 gebinnt (1/4 Sensoraufloesung), 3x3-Median, log1p, Bandpass (Gauss 1 - Gauss 8
Binpixel), Hann-Fenster, Phasenkorrelation gegen das Referenzbild, Subpixel per Parabel, Suche +-MAX_SHIFT_PX,
Kandidaten-Spitzen fuer die Alias-Aufloesung (LED-Raster periodisch), Viterbi; Guete PSR. Abweichend davon:
Referenz = Referenzbild der LED-Suche (ledsa_h1_series.csv ref_s1_id, t <= -30 s) statt 10. Bild; die Alias-
Aufloesung startet am Referenzbild (d = 0) und laeuft vorwaerts und rueckwaerts getrennt.
Stichprobe: je Serie die Bilder naechst an t = Referenz + k x STEP_S (EXIF-Zeit aus inventory/h1_exif_*.csv.gz).

Aufruf (hh2-venv): python ledsa_h1_drift.py [--only <Lauf>[:<Kamera>]] [--force] [--workers 4]
Ausgabe: inventory/ledsa_h1_drift.csv (je Bild), inventory/ledsa_h1_drift_summary.csv (je Serie; Kennwerte im
Auswertefenster -30 s bis Lueftung + 300 s und davor).
"""
import argparse
import io
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import rawpy
from scipy.ndimage import gaussian_filter, maximum_filter, median_filter

from ledsa_h1_paths import img_path

HERE = Path(__file__).resolve().parent
INV = HERE / "inventory"
OUT = INV / "ledsa_h1_drift.csv"
SUMMARY = INV / "ledsa_h1_drift_summary.csv"
MAX_SHIFT_PX, BIN, EXCL = 600, 4, 3
PSR_MIN, CAND_FRAC, N_CAND, LAMBDA_PX = 8.0, 0.5, 8, 10.0
PSR_ROBUST, MED_WIN, OUTLIER_PX = 15.0, 5, 5.0
STEP_S = 100.0
WIN_AFTER_VENT_S = 300.0


BAD = INV / "ledsa_h1_bad_images.csv"


def prep(path):
    """Gefiltertes Spektrum; None bei unlesbarer RAW-Datei (Zeile in inventory/ledsa_h1_bad_images.csv)."""
    with open(path, "rb") as f:
        buf = f.read()
    try:
        with rawpy.imread(io.BytesIO(buf)) as r:
            a = r.raw_image_visible.astype(np.float32)
            pat = r.raw_pattern
            black = np.asarray(r.black_level_per_channel, dtype=np.float32)
            desc = r.color_desc.decode()
    except rawpy.LibRawError as e:
        with open(BAD, "a", encoding="utf-8") as fh:
            fh.write(f"{path},{type(e).__name__}: {e},ledsa_h1_drift.py\n")
        print(f"     [!] unlesbar: {path} ({type(e).__name__})", flush=True)
        return None
    h, w = (a.shape[0] // 4) * 4, (a.shape[1] // 4) * 4
    g = np.zeros((h // 2, w // 2), np.float32)
    for i in range(2):
        for j in range(2):
            c = pat[i, j]
            if desc[c] == "G":
                g += np.clip(a[i:h:2, j:w:2] - black[c], 0, None)
    g = g.reshape(h // 4, 2, w // 4, 2).sum((1, 3))
    g = np.log1p(median_filter(g, 3))
    g = gaussian_filter(g, 1.0) - gaussian_filter(g, 8.0)
    win = np.outer(np.hanning(g.shape[0]), np.hanning(g.shape[1])).astype(np.float32)
    return np.fft.rfft2(g * win)


def phase_corr(f_ref, f_img, shape):
    r = f_ref.conj() * f_img
    r /= np.abs(r) + 1e-20
    c = np.fft.fftshift(np.fft.irfft2(r, s=shape))
    cy, cx = shape[0] // 2, shape[1] // 2
    m = MAX_SHIFT_PX // BIN
    sub = c[cy - m:cy + m + 1, cx - m:cx + m + 1]
    iy, ix = np.unravel_index(np.argmax(sub), sub.shape)
    peak = sub[iy, ix]
    masked = sub.copy()
    masked[max(iy - EXCL, 0):iy + EXCL + 1, max(ix - EXCL, 0):ix + EXCL + 1] = -np.inf
    side = masked[np.isfinite(masked)]
    psr = (peak - side.mean()) / side.std()

    def para(v_m, v_0, v_p):
        d = v_m - 2 * v_0 + v_p
        return 0.0 if d == 0 else 0.5 * (v_m - v_p) / d

    def sub_px(jy, jx):
        fy = para(sub[jy - 1, jx], sub[jy, jx], sub[jy + 1, jx]) if 0 < jy < sub.shape[0] - 1 else 0.0
        fx = para(sub[jy, jx - 1], sub[jy, jx], sub[jy, jx + 1]) if 0 < jx < sub.shape[1] - 1 else 0.0
        return (jy - m + fy) * BIN, (jx - m + fx) * BIN
    loc = (sub == maximum_filter(sub, size=2 * EXCL + 1)) & (sub >= CAND_FRAC * peak)
    ky, kx = np.nonzero(loc)
    order = np.argsort(-sub[ky, kx])[:N_CAND]
    cands = "|".join("{:.1f}:{:.1f}:{:.2f}".format(*sub_px(ky[i], kx[i]), sub[ky[i], kx[i]] / peak) for i in order)
    dy, dx = sub_px(iy, ix)
    return dy, dx, float(psr), cands


def viterbi(g):
    """Kandidatenfolge mit minimalen Kosten (|Sprung| + LAMBDA_PX x (1 - rel. Spitzenhoehe)), Start bei d = 0."""
    if g.empty:
        return g
    K = [np.array([[float(v) for v in t.split(":")] for t in str(c).split("|")]) for c in g.cands]
    cost = np.hypot(*K[0][:, :2].T) + LAMBDA_PX * (1 - K[0][:, 2])
    back = []
    for a, b in zip(K[:-1], K[1:]):
        step = np.hypot(b[:, None, 0] - a[None, :, 0], b[:, None, 1] - a[None, :, 1]) + cost[None, :]
        back.append(np.argmin(step, axis=1))
        cost = step.min(axis=1) + LAMBDA_PX * (1 - b[:, 2])
    j = int(np.argmin(cost))
    path = [j]
    for bk in reversed(back):
        j = int(bk[j])
        path.append(j)
    path.reverse()
    g = g.copy()
    g["dy_px"] = [k[j, 0] for k, j in zip(K, path)]
    g["dx_px"] = [k[j, 1] for k, j in zip(K, path)]
    return g


def valid(g, t_ref):
    g = g[g.psr >= PSR_MIN].copy()
    g["dy_raw"], g["dx_raw"] = g.dy_px, g.dx_px
    fwd = viterbi(g[g.t_rel_s >= t_ref].sort_values("t_rel_s"))
    bwd = viterbi(g[g.t_rel_s < t_ref].sort_values("t_rel_s", ascending=False))
    g = pd.concat([bwd, fwd]).sort_values("t_rel_s")
    if g.empty:
        return g
    my = g.dy_px.rolling(MED_WIN, center=True, min_periods=1).median()
    mx = g.dx_px.rolling(MED_WIN, center=True, min_periods=1).median()
    return g[np.hypot(g.dy_px - my, g.dx_px - mx) <= OUTLIER_PX]


def exif_times():
    def t_of(df):
        sub = df.subsec.fillna(0).astype(int).astype(str).str.ljust(2, "0").str[:2].astype(int) / 100.0
        return pd.to_datetime(df.dto, format="%Y:%m:%d %H:%M:%S") + pd.to_timedelta(sub, unit="s")
    a = pd.read_csv(INV / "h1_exif_weitergabe.csv.gz")
    a = a[a["sub"].isna()]
    a = a.assign(key=a.run + "|" + a.series, t=t_of(a))[["key", "name", "t"]]
    b = pd.read_csv(INV / "h1_exif_juelich.csv.gz")
    b = b.assign(key=b.tag + "|" + b.kamera, t=t_of(b))[["key", "name", "t"]]
    return pd.concat([a, b], ignore_index=True)


def samples(r, ex):
    folder = Path(r.folder_w)
    key = (f"{r.run}|{folder.name}" if "1_Measurements" in r.folder_w else f"{folder.parent.name}|{folder.name}")
    e = ex[ex.key == key].copy()
    z = pd.Timestamp(f"{r.date} {r.start_time}")
    e["t_rel_s"] = (e.t - z).dt.total_seconds()
    e = e[(e.t_rel_s >= r.t_first_s - 0.5) & (e.t_rel_s <= r.t_last_s + 0.5)]
    targets = np.arange(r.ref_s1_t_s, r.t_first_s - STEP_S / 2, -STEP_S)[1:].tolist() + \
        np.arange(r.ref_s1_t_s, r.t_last_s + STEP_S / 2, STEP_S)[1:].tolist() + [r.t_first_s, r.t_last_s]
    idx = sorted({int(np.argmin(np.abs(e.t_rel_s.to_numpy() - t))) for t in targets})
    return e.iloc[idx]


def measure(only=None, force=False, workers=4):
    s = pd.read_csv(HERE / "setup" / "ledsa_h1_series.csv", comment="#")
    if only:
        run, _, cam = only.partition(":")
        s = s[(s.run == run) & ((s.cam == cam) if cam else True)]
    done = pd.read_csv(OUT) if OUT.exists() and not force else pd.DataFrame()
    rows = [done] if len(done) else []
    ex = exif_times()
    pool = ThreadPoolExecutor(workers)
    for r in s.itertuples():
        if len(done) and ((done.run == r.run) & (done.cam == r.cam)).any():
            continue
        t0 = time.time()
        ref_name = r.name_string.format(int(r.ref_s1_id))
        f_ref = prep(Path(img_path(r.folder_w)) / ref_name)
        shape = (f_ref.shape[0], (f_ref.shape[1] - 1) * 2)
        smp = samples(r, ex)
        out = []
        for e, f_img in zip(smp.itertuples(), pool.map(prep, [Path(img_path(r.folder_w)) / n for n in smp.name])):
            if f_img is None or f_img.shape != f_ref.shape:
                continue
            dy, dx, psr, cands = phase_corr(f_ref, f_img, shape)
            out.append(dict(run=r.run, cam=r.cam, position=r.position, name=e.name, ref=ref_name,
                            t_ref_s=r.ref_s1_t_s, t_rel_s=round(e.t_rel_s, 1), dy_px=round(dy, 1), dx_px=round(dx, 1),
                            psr=round(psr, 1), cands=cands))
        d = pd.DataFrame(out)
        rows.append(d)
        pd.concat(rows, ignore_index=True).to_csv(OUT, index=False)
        v = valid(d, r.ref_s1_t_s)
        mx = np.hypot(v.dy_px, v.dx_px).max() if len(v) else np.nan
        print(f"[ok] {r.run} {r.cam} ({r.position}): {len(d)} Bilder, gueltig {len(v)}, max |d| {mx:.1f} px, "
              f"{time.time() - t0:.0f} s", flush=True)
    pool.shutdown()


def summarize():
    if not OUT.exists():
        raise SystemExit(f"[--] fehlt {OUT}")
    d = pd.read_csv(OUT)
    runs = pd.read_csv(HERE / "setup" / "ledsa_h1_runs.csv", comment="#").set_index("run")
    out = []
    for (run, cam), g in d.groupby(["run", "cam"], sort=False):
        v = valid(g, g.t_ref_s.iloc[0])
        v = v.assign(d_px=np.hypot(v.dy_px, v.dx_px))
        t_end = runs.loc[run, "ventilation_s"] + WIN_AFTER_VENT_S
        w = v[(v.t_rel_s >= -30) & (v.t_rel_s <= t_end)]
        pre = v[v.t_rel_s < -30]
        out.append(dict(run=run, cam=cam, position=g.position.iloc[0], n=len(g), n_valid=len(v),
                        n_valid_fenster=len(w), max_d_fenster_px=round(w.d_px.max(), 1) if len(w) else np.nan,
                        max_dy_fenster_px=round(w.dy_px.abs().max(), 1) if len(w) else np.nan,
                        max_dx_fenster_px=round(w.dx_px.abs().max(), 1) if len(w) else np.nan,
                        max_d_psr15_fenster_px=round(w.d_px[w.psr >= PSR_ROBUST].max(), 1)
                        if (w.psr >= PSR_ROBUST).any() else np.nan,
                        max_d_vor_px=round(pre.d_px.max(), 1) if len(pre) else np.nan,
                        last_dy_px=v.dy_px.iloc[-1] if len(v) else np.nan,
                        last_dx_px=v.dx_px.iloc[-1] if len(v) else np.nan))
    sm = pd.DataFrame(out)
    with open(SUMMARY, "w", encoding="utf-8", newline="") as f:
        f.write(f"# ledsa_h1_drift.py: Lage gegen das Referenzbild der LED-Suche (t <= -30 s), gueltige Werte (PSR >= "
                f"{PSR_MIN}, Alias aufgeloest, Medianpruefung); Fenster = -30 s bis Lueftung + {WIN_AFTER_VENT_S:.0f} s; "
                f"Sensorpixel\n")
        sm.to_csv(f, index=False)
    pd.set_option("display.width", 250)
    print(sm.to_string(index=False))
    return sm


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--summary-only", action="store_true")
    a = ap.parse_args()
    if not a.summary_only:
        measure(a.only, a.force, a.workers)
    summarize()
