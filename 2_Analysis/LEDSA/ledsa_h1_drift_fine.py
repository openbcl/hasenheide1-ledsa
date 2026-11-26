# -*- coding: utf-8 -*-
r"""Lagecheck mit genauer Methode (2026-11-23): Verschiebung des LED-Streifenbereichs gegen das Referenzbild der
LED-Suche, Stichprobe wie ledsa_h1_drift.py (Referenz + k x 100 s, erstes/letztes Bild).

Anlass: ledsa_h1_drift.py rechnet auf 4x4 gebinnten Bildern mit Parabel-Subpixel; die Werte rasten an Vielfachen von
4 px ein (Hep_160_S2_R2 C3: Lagecheck -0,1/-0,3 px bis 666 s und -3,7 px am Ende, Streifenbereich und Nachfuehrung
uebereinstimmend -1,1...-2,4 px; tools/drift_regions.py). Hier: Gruen beider Bayer-Plaetze bei halber Aufloesung,
nur der Streifenbereich (Fenster aus setup/ledsa_h1_strip_windows.csv +-60 px quer, +-80 px laengs), log1p, Bandpass,
Hann, Phasenkorrelation mit hochgetasteter DFT (Faktor 20, an kuenstlich verschobenen Bildern auf 0,01 px geprueft).
Alias (LED-Raster periodisch): Suche je Bild nur im Umkreis 0,45 x LED-Abstand um den Wert des zeitlich vorigen Bilds,
vom Referenzbild vorwaerts und rueckwaerts; liegt das Maximum am Rand des Suchkreises -> Spalte rand = 1 (groessere
Bewegung, z. B. Schwenk; dann Wert unsicher). Unlesbare Dateien: bekannt abgeschnittene uebersprungen, sonst Abbruch.

Aufruf (hh2-venv): python ledsa_h1_drift_fine.py [--only <Lauf>[:<Kamera>]] [--force] [--workers 4]
Ausgabe: inventory/ledsa_h1_drift_fine.csv (je Bild), inventory/ledsa_h1_drift_fine_summary.csv (je Serie; Fenster
-30 s bis Lueftung + 300 s wie ledsa_h1_drift.py, dazu "vor Lueftung" -30 s bis Lueftung).
"""
import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))
from ledsa_h1_drift import exif_times, samples   # noqa: E402
from drift_regions import green, prep, upsampled_dft, UPS   # noqa: E402
from ledsa_h1_paths import img_path   # noqa: E402

INV = HERE / "inventory"
OUT = INV / "ledsa_h1_drift_fine.csv"
SUMMARY = INV / "ledsa_h1_drift_fine_summary.csv"
MARGIN_ACROSS, MARGIN_ALONG = 60, 80          # Sensorpixel
SEARCH_FRAC = 0.45
WIN_AFTER_VENT_S = 300.0


def corr(F_ref, img):
    G = np.fft.fft2(img)
    R = F_ref * G.conj()
    R /= np.abs(R) + 1e-20
    return R, np.fft.fftshift(np.fft.ifft2(R).real)


def locate(R, c, center, radius):
    """Maximum der Korrelation im Kreis um center (Verschiebung img gegen ref, halbe Aufloesung), dann hochgetastet."""
    cy, cx = c.shape[0] // 2, c.shape[1] // 2
    yy, xx = np.mgrid[0:c.shape[0], 0:c.shape[1]]
    # Korrelationsspitze liegt bei -Verschiebung (Konvention von register in drift_regions.py)
    m = np.hypot(yy - (cy - center[0]), xx - (cx - center[1])) <= radius
    cm = np.where(m, c, -np.inf)
    iy, ix = np.unravel_index(np.argmax(cm), cm.shape)
    on_rim = np.hypot(iy - (cy - center[0]), ix - (cx - center[1])) > radius - 1.0
    s0 = np.array([iy - cy, ix - cx], float)
    n = int(np.ceil(UPS * 1.5))
    up = upsampled_dft(R.conj(), UPS, n, n // 2 - s0 * UPS).conj().real
    jy, jx = np.unravel_index(np.argmax(up), up.shape)
    s = s0 + (np.array([jy, jx]) - n // 2) / UPS
    peak = c[iy, ix]
    ring = c[max(iy - 12, 0):iy + 13, max(ix - 12, 0):ix + 13].copy()
    ring[9:16, 9:16] = -np.inf
    q = float(peak / ring[np.isfinite(ring)].max()) if np.isfinite(ring).any() and ring[np.isfinite(ring)].max() > 0 \
        else np.inf
    return -s[0], -s[1], q, bool(on_rim)


def measure(only=None, force=False, workers=4):
    s = pd.read_csv(HERE / "setup" / "ledsa_h1_series.csv", comment="#")
    win = pd.read_csv(HERE / "setup" / "ledsa_h1_strip_windows.csv", comment="#")
    ab = set(pd.read_csv(INV / "ledsa_h1_juelich_abgeschnitten.csv", comment="#")["name"])
    if only:
        run, _, cam = only.partition(":")
        s = s[(s.run == run) & ((s.cam == cam) if cam else True)]
    done = pd.read_csv(OUT) if OUT.exists() and not force else pd.DataFrame()
    if len(done) and only:
        done = done[~done.set_index(["run", "cam"]).index.isin(list(zip(s.run, s.cam)))]
    rows = [done] if len(done) else []
    ex = exif_times()
    pool = ThreadPoolExecutor(workers)

    def load(path):
        try:
            return green(path)
        except Exception as e:
            if Path(path).name in ab:
                return None
            raise SystemExit(f"[--] {path} nicht lesbar ({type(e).__name__}: {e}); Abbruch (Bildablage unter H1_IMAGES_ROOT pruefen)")

    for r in s.itertuples():
        if len(done) and ((done.run == r.run) & (done.cam == r.cam)).any():
            continue
        t0 = time.time()
        w = win[(win.run == r.run) & (win.cam == r.cam)]
        pitch = float(w.pitch_px.median())
        rs = slice(max(int(w.row0.min()) - MARGIN_ALONG, 0) // 2, (int(w.row1.max()) + MARGIN_ALONG) // 2)
        cs = slice(max(int(w.col0.min()) - MARGIN_ACROSS, 0) // 2, (int(w.col1.max()) + MARGIN_ACROSS) // 2)
        ref_name = r.name_string.format(int(r.ref_s1_id))
        F_ref = np.fft.fft2(prep(load(Path(img_path(r.folder_w)) / ref_name)[rs, cs]))
        smp = samples(r, ex).sort_values("t_rel_s")
        imgs = dict(zip(smp.name, pool.map(load, [Path(img_path(r.folder_w)) / n for n in smp.name])))
        radius = SEARCH_FRAC * pitch / 2.0                   # halbe Aufloesung
        out = []
        for part in (smp[smp.t_rel_s >= r.ref_s1_t_s], smp[smp.t_rel_s < r.ref_s1_t_s].iloc[::-1]):
            prev = np.zeros(2)
            for e in part.itertuples():
                g = imgs[e.name]
                if g is None:
                    continue
                R, c = corr(F_ref, prep(g[rs, cs]))
                dy, dx, q, rim = locate(R, c, prev, radius)
                prev = np.array([dy, dx])
                out.append(dict(run=r.run, cam=r.cam, position=r.position, name=e.name, ref=ref_name,
                                t_ref_s=r.ref_s1_t_s, t_rel_s=round(e.t_rel_s, 1), dy_px=round(2 * dy, 2),
                                dx_px=round(2 * dx, 2), quality=round(q, 2), rand=int(rim)))
        d = pd.DataFrame(out).sort_values("t_rel_s")
        rows.append(d)
        pd.concat(rows, ignore_index=True).to_csv(OUT, index=False)
        print(f"[ok] {r.run} {r.cam} ({r.position}): {len(d)} Bilder, max |d| {np.hypot(d.dy_px, d.dx_px).max():.2f} px, "
              f"Rand {int(d.rand.sum())}, {time.time() - t0:.0f} s", flush=True)
    pool.shutdown()


def summarize():
    d = pd.read_csv(OUT)
    runs = pd.read_csv(HERE / "setup" / "ledsa_h1_runs.csv", comment="#").set_index("run")
    out = []
    for (run, cam), g in d.groupby(["run", "cam"], sort=False):
        g = g.assign(d_px=np.hypot(g.dy_px, g.dx_px))
        vent = runs.loc[run, "ventilation_s"]
        w = g[(g.t_rel_s >= -30) & (g.t_rel_s <= vent + WIN_AFTER_VENT_S)]
        v = g[(g.t_rel_s >= -30) & (g.t_rel_s <= vent)]
        out.append(dict(run=run, cam=cam, position=g.position.iloc[0], n=len(g), n_fenster=len(w),
                        max_d_fenster_px=round(w.d_px.max(), 2) if len(w) else np.nan,
                        max_dy_fenster_px=round(w.dy_px.abs().max(), 2) if len(w) else np.nan,
                        max_dx_fenster_px=round(w.dx_px.abs().max(), 2) if len(w) else np.nan,
                        max_d_vor_lueftung_px=round(v.d_px.max(), 2) if len(v) else np.nan,
                        rand_fenster=int(w.rand.sum()), min_quality_fenster=round(w.quality.min(), 2) if len(w) else np.nan,
                        last_dy_px=g.dy_px.iloc[-1], last_dx_px=g.dx_px.iloc[-1]))
    sm = pd.DataFrame(out)
    with open(SUMMARY, "w", encoding="utf-8", newline="") as f:
        f.write("# ledsa_h1_drift_fine.py: Streifenbereich gegen Referenzbild der LED-Suche, Sensorpixel; Fenster -30 s bis "
                f"Lueftung + {WIN_AFTER_VENT_S:.0f} s; vor_lueftung -30 s bis Lueftung; rand = Maximum am Suchkreisrand\n")
        sm.to_csv(f, index=False)
    pd.set_option("display.width", 250)
    print(sm.to_string(index=False))


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
