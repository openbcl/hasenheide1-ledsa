# -*- coding: utf-8 -*-
r"""Stufe 0 der H1-LEDSA-Auswertung (METHODS.md section 4.1): Vergleiche nach Paper-Methode.

Nachbearbeitung wie das Paper (Skript plot_ledsa_profiles.py des nicht oeffentlichen Paper-Repositoriums, load_stacked_ledsa):
Interpolation jeder Schichtreihe auf das 1-s-Raster t = T_START..T_END, Nullung auf den Wert bei t = 0, Widmann-Faktor
(638 / lambda)^-1.0088 mit lambda 628 / 521 / 468 nm je Kanal, Sigma-Clip 0,5 sigma, Fenster 51, min. 3 Werte; Mittel
ueber die drei Arrays (Array i im Kanal i). Hoehe -> Schicht mit naechster Mitte. Gesperrte Schichten (Maske SNR 3,
Anteil > 0,5; ledsa_h1_mask.py) vor der Nachbearbeitung NaN, fuer beide Groessen gleich.
LEM und LEDSA fuer Spitze/Plateau gleich gefiltert (Sigma-Clip wie oben, dann gleitendes +-10-s-Mittel).
Plateau = [Lueftung - 300 s, Lueftung - 20 s] je Lauf (setup/ledsa_h1_runs.csv, gemessene Lueftung).

  test1 <Lauf> <Raum>  neuer Stapel (farbg, sum) gegen die frueheren 0.10.0-Stapel (stacked_results/, sum_col_val) und LEM
  test2 <Lauf> <Raum> <Ordner voll>  Ausduennung: Stapel ausgeduennt (runs/) gegen voll (<Ordner voll>/<Lauf>/stacked_<Raum>)
Aufruf: hh2-venv. Ergebnisse auf der Konsole und in inventory/ledsa_h1_stage0_<test>_<Lauf>_<Raum>.csv.
"""
import re
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
from ledsa_h1_config import RUNS   # noqa: E402

T_START, T_END = -30, 1700
LAM = {0: 628.0, 1: 521.0, 2: 468.0}
SIG_THRESH, SIG_WIN, SIG_MINP = 0.5, 51, 3
HALF_S = 10
LEM_MIN_N = 100          # LEM-Spalte nur mit mindestens so vielen Werten (ganz leere Spalten, z. B. LEM_4 F1 220_R1/R4)
OLD = Path(os.environ.get("H1_PRIOR0100", str(HERE / "stacked_results")))   # fruehere Stapel, nicht im Repo


def widmann(ch):
    return (638.0 / LAM[ch]) ** -1.0088


def load_k(path):
    head = {}
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            if not ln.startswith("#"):
                break
            p = ln[1:].strip().split(",")
            head[p[0].strip()] = p[1:]
    centers = np.array(head["Layer_center_height[m]"], float)
    d = pd.read_csv(path, comment="#", header=None)
    return d.iloc[:, 0].to_numpy(float), d.iloc[:, 1:].to_numpy(float), centers


def sigma_clip(v):
    s = pd.Series(v)
    med = s.rolling(SIG_WIN, center=True, min_periods=SIG_MINP).median()
    res = v - med.to_numpy()
    sd = pd.Series(res).rolling(SIG_WIN, center=True, min_periods=SIG_MINP).std().to_numpy()
    out = v.copy()
    bad = np.abs(res) > SIG_THRESH * sd
    out[bad] = med.to_numpy()[bad]
    return out


def grid():
    return np.arange(T_START, T_END + 1, dtype=float)


def paper_series(t, k, ch):
    tg = grid()
    v = np.interp(tg, t, k, left=np.nan, right=np.nan)          # NaN (gesperrt) bleibt in den Nachbarintervallen NaN
    i0 = int(np.argmin(np.abs(tg)))
    base = v[i0] if np.isfinite(v[i0]) else np.nanmean(v[:10])
    return sigma_clip((v - base) * widmann(ch))


def smooth(v):
    return pd.Series(v).rolling(2 * HALF_S + 1, center=True, min_periods=HALF_S).mean().to_numpy()


MASK_TOL_S = 0.01


def apply_mask(t, k, mask_rows, tag=""):
    """Setzt gesperrte (t, Schicht) der Maske in k auf NaN (Zeitabgleich mit Toleranz MASK_TOL_S). Bricht ab, wenn eine
    gesperrte Zelle keinem Inversionszeitpunkt zugeordnet werden kann (sonst wuerde die Maske still nicht greifen), und
    umgekehrt, wenn ein Inversionszeitpunkt keine Maskenzeile hat (sonst bliebe er still ungeprueft)."""
    if (np.diff(t) <= MASK_TOL_S).any():
        raise SystemExit(f"[--] {tag}: Inversionszeiten nicht streng steigend (Abstand <= {MASK_TOL_S} s)")
    mt = np.unique(mask_rows.t_s.to_numpy(float))
    if mt.size == 0:
        raise SystemExit(f"[--] {tag}: Maske ohne Zeilen")
    jm = np.clip(np.searchsorted(mt, t), 1, max(len(mt) - 1, 1))
    dm = np.minimum(np.abs(mt[jm - 1] - t), np.abs(mt[np.minimum(jm, len(mt) - 1)] - t))
    if (dm > MASK_TOL_S).any():
        raise SystemExit(f"[--] {tag}: {int((dm > MASK_TOL_S).sum())} Inversionszeitpunkte ohne Maskenzeile "
                         f"(max |dt| {dm.max():.3f} s)")
    g = mask_rows[mask_rows.gesperrt]
    if g.empty:
        return k
    tt = g.t_s.to_numpy(float)
    j = np.searchsorted(t, tt)
    j = np.clip(j, 1, len(t) - 1)
    jj = np.where(np.abs(t[j - 1] - tt) <= np.abs(t[j] - tt), j - 1, j)
    hit = np.abs(t[jj] - tt) <= MASK_TOL_S
    if not hit.all():
        raise SystemExit(f"[--] {tag}: {int((~hit).sum())} gesperrte Maskenzeilen ohne Inversionszeitpunkt "
                         f"(max |dt| {np.abs(t[jj] - tt).max():.3f} s)")
    k[jj, g.layer.to_numpy(int)] = np.nan
    return k


def mask_for(run, room, quelle):
    f = RUNS / run / "plots_h1" / f"mask_{room}.csv.gz"
    if not f.exists():
        raise SystemExit(f"[--] fehlt {f} (ledsa_h1_mask.py flag)")
    m = pd.read_csv(f)
    return m[(m.snr == 3.0) & (m.quelle == quelle)]


def room_series(kdir, prop, heights, mask=None, pattern="extinction_coefficients_linear_channel_{c}_{p}_led_array_{a}.csv"):
    """{Hoehe: 1-s-Reihe} nach Paper-Methode, Mittel der Arrays 0-2 (Kanal = Array)."""
    out = {h: [] for h in heights}
    for a in range(3):
        f = kdir / pattern.format(c=a, p=prop, a=a)
        if not f.exists():
            raise SystemExit(f"[--] fehlt {f}")
        t, k, cen = load_k(f)
        if mask is not None:
            k = apply_mask(t, k, mask[mask.led_array == a], f"{kdir} Array {a}")
        for h in heights:
            j = int(np.argmin(np.abs(cen - h)))
            out[h].append(paper_series(t, k[:, j], a))
    return {h: np.nanmean(np.vstack(v), axis=0) for h, v in out.items()}


def lem(run, room):
    f = REPO / "1_Measurements" / run / "1_Processed_data" / f"{run}_processed.csv"
    d = pd.read_csv(f, comment="#", encoding="utf-8-sig")
    out = {}
    for c in d.columns:
        m = re.match(rf"Extinction LEM_\d+_{room}_([\d.]+) \(1/m\)$", c)
        if m and d[c].notna().sum() >= LEM_MIN_N:
            if float(m.group(1)) in out:
                raise SystemExit(f"[--] {run} {room}: zwei LEM auf {m.group(1)} m")
            out[float(m.group(1))] = sigma_clip(np.interp(grid(), d["Time (s)"].to_numpy(float), d[c].to_numpy(float),
                                                          left=np.nan, right=np.nan))
    return out


def vent(run):
    r = pd.read_csv(HERE / "setup" / "ledsa_h1_runs.csv", comment="#").set_index("run").loc[run]
    return float(r.ventilation_s)


def metrics(v, t_vent):
    tg = grid()
    s = smooth(v)
    pre = (tg > 0) & (tg < t_vent)
    ip = int(np.nanargmax(np.where(pre, s, -np.inf)))
    plat = (tg >= t_vent - 300) & (tg <= t_vent - 20)
    return dict(peak=s[ip], t_peak=tg[ip], plateau=np.nanmean(s[plat]))


def test1(run, room):
    heights = sorted(lem(run, room)) or [2.3]
    L = lem(run, room)
    tv = vent(run)
    mask = mask_for(run, room, f"stacked_{room}")
    new_dir = RUNS / run / f"stacked_{room}" / "analysis" / "extinction_coefficients" / "linear"
    sub = {"F2": "stacked"}.get(room, f"stacked_{room}") if run.startswith("Hep_160_S4") else f"stacked_{room}"
    old_dir = OLD / run / sub / "analysis" / "extinction_coefficients" / "linear"
    series = {
        "neu farbg": room_series(new_dir / "farbg_sum_col_val", "farbg_sum_col_val", heights, mask),
        "neu sum": room_series(new_dir / "sum_col_val", "sum_col_val", heights, mask),
        "neu sum ohne Maske": room_series(new_dir / "sum_col_val", "sum_col_val", heights),
        "0.10.0 sum (prior0100)": room_series(old_dir, "sum_col_val", heights),
    }
    rows = []
    for h in heights:
        ml = metrics(L[h], tv) if h in L else None
        for lab, ser in series.items():
            m = metrics(ser[h], tv)
            rows.append(dict(hoehe_m=h, quelle=lab, spitze=round(m["peak"], 3), t_spitze=m["t_peak"],
                             plateau=round(m["plateau"], 3),
                             spitze_zu_LEM=round(m["peak"] / ml["peak"], 3) if ml else np.nan,
                             plateau_zu_LEM=round(m["plateau"] / ml["plateau"], 3) if ml else np.nan))
        if ml:
            rows.append(dict(hoehe_m=h, quelle="LEM", spitze=round(ml["peak"], 3), t_spitze=ml["t_peak"],
                             plateau=round(ml["plateau"], 3), spitze_zu_LEM=1.0, plateau_zu_LEM=1.0))
    d = pd.DataFrame(rows)
    print(f"{run} {room}: Lueftung {tv:.0f} s, Plateau {tv - 300:.0f}-{tv - 20:.0f} s")
    print(d.to_string(index=False))
    out = HERE / "inventory" / f"ledsa_h1_stage0_test1_{run}_{room}.csv"
    d.to_csv(out, index=False)
    print(f"[ok] {out}")


def test2(run, room, full_root):
    """Ausduennung: gleicher Stapel ausgeduennt (runs/) gegen voll; Rohdaten (ohne Filter) je Schicht auf gemeinsamen
    Zeiten (Zeitachse = untere Kamera, in beiden gleich) und gefilterte Reihen an den LEM-Hoehen."""
    full = Path(full_root) / run / f"stacked_{room}" / "analysis" / "extinction_coefficients" / "linear"
    thin = RUNS / run / f"stacked_{room}" / "analysis" / "extinction_coefficients" / "linear"
    tv = vent(run)
    rows = []
    for prop in ("farbg_sum_col_val", "sum_col_val"):
        for a in range(3):
            fn = f"extinction_coefficients_linear_channel_{a}_{prop}_led_array_{a}.csv"
            t1, k1, cen = load_k(thin / prop / fn)
            t2, k2, _ = load_k(full / prop / fn)
            common, i1, i2 = np.intersect1d(np.round(t1, 2), np.round(t2, 2), return_indices=True)
            k1, k2 = k1[i1], k2[i2]
            kmax = np.nanmax(k2[(common > 0) & (common < tv)], axis=0)
            dk = np.abs(k1 - k2)
            pre = (common > 0) & (common < tv)
            for j in range(k1.shape[1]):
                rows.append(dict(groesse=prop, array=a, layer=j, z_m=round(cen[j], 3), n_t=int(pre.sum()),
                                 kmax_voll=round(kmax[j], 3),
                                 dk_median_rel_kmax_pct=round(100 * np.nanmedian(dk[pre, j]) / kmax[j], 2),
                                 dk_p95_rel_kmax_pct=round(100 * np.nanpercentile(dk[pre, j], 95) / kmax[j], 2),
                                 dk_max_rel_kmax_pct=round(100 * np.nanmax(dk[pre, j]) / kmax[j], 2)))
    d = pd.DataFrame(rows)
    g = d[d.kmax_voll > 0.1].groupby("groesse")[["dk_median_rel_kmax_pct", "dk_p95_rel_kmax_pct", "dk_max_rel_kmax_pct"]]
    print(f"{run} {room} roh, Schichten mit k_max > 0,1 1/m, 0 < t < Lueftung {tv:.0f} s, |k_ausgeduennt - k_voll| / k_max:")
    print(g.median().round(2).to_string())
    print("schlechteste Schicht:")
    print(g.max().round(2).to_string())
    L = lem(run, room)
    heights = sorted(L) or [2.3]
    rows2 = []
    for prop in ("farbg_sum_col_val", "sum_col_val"):
        s_thin = room_series(thin / prop, prop, heights)
        s_full = room_series(full / prop, prop, heights)
        for h in heights:
            mt, mf = metrics(s_thin[h], tv), metrics(s_full[h], tv)
            diff = np.nanmax(np.abs(smooth(s_thin[h]) - smooth(s_full[h])))
            rows2.append(dict(groesse=prop, hoehe_m=h, spitze_aus_zu_voll=round(mt["peak"] / mf["peak"], 4),
                              plateau_aus_zu_voll=round(mt["plateau"] / mf["plateau"], 4),
                              t_spitze_aus=mt["t_peak"], t_spitze_voll=mf["t_peak"],
                              max_diff_gefiltert_rel_spitze_pct=round(100 * diff / mf["peak"], 2)))
    d2 = pd.DataFrame(rows2)
    print("Paper-Methode an den LEM-Hoehen (ohne Maske):")
    print(d2.to_string(index=False))
    out = HERE / "inventory" / f"ledsa_h1_stage0_test2_{run}_{room}.csv"
    d.to_csv(out, index=False)
    d2.to_csv(out.with_name(out.stem + "_hoehen.csv"), index=False)
    print(f"[ok] {out}")


if __name__ == "__main__":
    {"test1": test1, "test2": test2}[sys.argv[1]](*sys.argv[2:])
