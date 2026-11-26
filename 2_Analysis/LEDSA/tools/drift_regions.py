# -*- coding: utf-8 -*-
"""Verschiebung getrennt nach Bildbereichen (Untersuchung 2026-11-23: Ursache des Drifts, Lichtbrechung?).
Bewegt sich die Kamera, verschieben sich LED-Streifen und Hintergrund gleich; bewegt sich nur der Streifen (oder wird
nur sein Licht abgelenkt), nur der Streifenbereich. Zusaetzlich Abgleich mit der Nachfuehrung (tracking_log.csv).
Verfahren: Gruen beider Bayer-Plaetze bei halber Aufloesung, log1p, Bandpass (Gauss 0,7 - Gauss 6), Hann-Fenster,
Phasenkorrelation mit Subpixel per hochgetasteter DFT (Guizar-Sicairos et al. 2008, Faktor 20) -> keine Bindung
an Rasterpunkte wie im Lagecheck (4er-Binning + Parabel). Bereiche: Streifen = Spalten der Streifenfenster +-60 px,
Hintergrund links/rechts = Spaltenbaender ohne Streifen (Streifen +-300 px ausgespart).
Aufruf (hh2-venv, im Ordner 2_Analysis/LEDSA): python tools/drift_regions.py <Lauf>:<Kamera> [t1 t2 ...]
"""
import configparser
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rawpy
from scipy.ndimage import gaussian_filter

L = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(L))
from ledsa_h1_paths import img_path   # noqa: E402
UPS = 20


def green(path):
    with open(path, "rb") as f:
        buf = f.read()
    with rawpy.imread(io.BytesIO(buf)) as r:
        a = r.raw_image_visible.astype(np.float32)
        pat, desc = r.raw_pattern, r.color_desc.decode()
        black = np.asarray(r.black_level_per_channel, dtype=np.float32)
    h, w = (a.shape[0] // 2) * 2, (a.shape[1] // 2) * 2
    g = np.zeros((h // 2, w // 2), np.float32)
    for i in range(2):
        for j in range(2):
            if desc[pat[i, j]] == "G":
                g += np.clip(a[i:h:2, j:w:2] - black[pat[i, j]], 0, None)
    return g


def prep(g):
    g = np.log1p(g)
    g = gaussian_filter(g, 0.7) - gaussian_filter(g, 6.0)
    return g * np.outer(np.hanning(g.shape[0]), np.hanning(g.shape[1]))


def upsampled_dft(data, ups, n, off):
    """DFT von data auf einem n x n-Gitter um off (in hochgetasteten Einheiten), Matrixform nach Guizar-Sicairos."""
    ny, nx = data.shape
    kc = np.fft.ifftshift(np.arange(nx)) - nx // 2
    kr = np.fft.ifftshift(np.arange(ny)) - ny // 2
    col = np.exp(-2j * np.pi / (nx * ups) * (np.arange(n) - off[1])[:, None] * kc[None, :])
    row = np.exp(-2j * np.pi / (ny * ups) * (np.arange(n) - off[0])[:, None] * kr[None, :])
    return row @ data @ col.T


def register(ref, img, max_shift=40):
    F, G = np.fft.fft2(ref), np.fft.fft2(img)
    R = F * G.conj()
    R /= np.abs(R) + 1e-20
    c = np.fft.ifft2(R).real
    c = np.fft.fftshift(c)
    cy, cx = c.shape[0] // 2, c.shape[1] // 2
    sub = c[cy - max_shift:cy + max_shift + 1, cx - max_shift:cx + max_shift + 1]
    iy, ix = np.unravel_index(np.argmax(sub), sub.shape)
    peak = sub[iy, ix]
    m = sub.copy()
    m[max(iy - 3, 0):iy + 4, max(ix - 3, 0):ix + 4] = -np.inf
    second = np.max(m)
    s0 = np.array([iy - max_shift, ix - max_shift], float)
    n = int(np.ceil(UPS * 1.5))
    off = n // 2 - s0 * UPS
    up = upsampled_dft(R.conj(), UPS, n, off).conj().real
    jy, jx = np.unravel_index(np.argmax(up), up.shape)
    s = s0 + (np.array([jy, jx]) - n // 2) / UPS
    return -s[0], -s[1], float(peak / second) if second > 0 else np.inf   # Vorzeichen: img gegen ref


def main(rc, times):
    run, cam = rc.split(":")
    s = pd.read_csv(L / "setup" / "ledsa_h1_series.csv", comment="#")
    r = s[(s.run == run) & (s.cam == cam)].iloc[0]
    w = L / "runs" / run / f"{r.position}_{cam}"
    conf = configparser.ConfigParser()
    conf.read(w / "config.ini")
    img_dir = Path(img_path(conf["DEFAULT"]["img_directory"].strip()))
    win = pd.read_csv(L / "setup" / "ledsa_h1_strip_windows.csv", comment="#")
    win = win[(win.run == run) & (win.cam == cam)]
    c0, c1 = int(win.col0.min()) // 2, int(win.col1.max()) // 2         # halbe Aufloesung
    r0, r1 = int(win.row0.min()) // 2, int(win.row1.max()) // 2
    log = pd.read_csv(w / "analysis" / "tracking_log.csv").sort_values("t_exp")
    ref_name = r.name_string.format(int(r.ref_s1_id))
    g_ref = green(img_dir / ref_name)
    H, W = g_ref.shape
    regions = {"strip": (slice(max(r0 - 40, 0), min(r1 + 40, H)), slice(max(c0 - 30, 0), min(c1 + 30, W))),
               "bg_left": (slice(0, H), slice(max(c0 - 150 - 900, 0), max(c0 - 150, 0))),
               "bg_right": (slice(0, H), slice(min(c1 + 150, W), min(c1 + 150 + 900, W)))}
    regions = {k: v for k, v in regions.items() if (v[1].stop - v[1].start) > (40 if k == "strip" else 200)}
    pref = {k: prep(g_ref[v]) for k, v in regions.items()}
    print(f"{run} {cam}: Referenz {ref_name} (t {r.ref_s1_t_s:.0f} s); Verschiebung in Sensorpixeln "
          f"(laengs = Zeile, quer = Spalte), Guete = Spitze / zweithoechste Spitze")
    rows = []
    for t in times:
        k = int(np.argmin(np.abs(log.t_exp.to_numpy() - t)))
        name, te = log.name.iloc[k], log.t_exp.iloc[k]
        g = green(img_dir / name)
        out = [f"t {te:6.0f} s {name}:"]
        for key, sl in regions.items():
            dy, dx, q = register(pref[key], prep(g[sl]))
            out.append(f"{key} {2 * dy:+.2f}/{2 * dx:+.2f} (G {q:.1f})")
            rows.append((te, key, 2 * dy, 2 * dx, q))
        out.append(f"| Nachfuehrung {log.shift_row.iloc[k]:+.2f}/{log.shift_col.iloc[k]:+.2f}")
        print("  " + "  ".join(out), flush=True)
    return pd.DataFrame(rows, columns=["t", "region", "d_row", "d_col", "quality"])


if __name__ == "__main__":
    ts = [float(x) for x in sys.argv[2:]] or [0, 300, 600, 900, 1200, 1500]
    main(sys.argv[1], ts)
