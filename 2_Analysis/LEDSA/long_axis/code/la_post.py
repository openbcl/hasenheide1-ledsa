# -*- coding: utf-8 -*-
r"""Nachbearbeitung der Langachsen-Inversion.

Je (Lauf, Kamera, Array): farbg_sum_col_val, Kanal 1 (gruen); Maske U_B 0,2 (la.py mask; bei Leserauschen zusaetzlich
SNR 3, gesperrt wenn eines greift); Schichten ohne Strahl (Weglaenge 0 in led_array_<a>_distances_per_layer.txt) NaN;
dann wie die Raumauswertung ledsa_h1_profiles.paper_series (1-s-Raster -30...1700 s, Nullung Median [-5, +10] s,
Widmann gruen, Sigma-Clip 0,5 sigma/51 s), ABER Nullung ueber die Zeitspanne der Referenzbilder statt [-5, +10] s
(ref_span; Verdeckung um die Zuendung). Sperren: CAM_MOVED (ab t_cut), EXCLUDED (ganze Serie).
Optional (nur wenn die Umgebungsvariable H1_PRIOR098_LA gesetzt ist; nicht Teil dieses Repos): Vergleich mit einer
frueheren LEDSA-0.9.8-Auswertung derselben Serien (Ordner mit ledsa_<Lauf>_L2_array<a>_ch1.csv, sum_col_val,
Schicht-Oberkanten in der Kopfzeile, Mitte = Oberkante - 0,05 m), gleiche Nachbearbeitung ohne Maske.
Ausgabe: ../out/la_k_1s.csv.gz (lang: run, cam, array, layer, z_m, t_s, k), ../out/la_profiles.csv (Mittel +-10 s zu
Profilzeiten; src 'neu' = diese Auswertung, 'prior098' = fruehere, nur optional), ../out/la_cmp_prior098.csv (optional).
Aufruf: hh2-venv  la_post.py
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
import la  # noqa: E402
import ledsa_h1_stage0 as s0  # noqa: E402
import ledsa_h1_profiles as P  # noqa: E402

OUT = la.LA / "out"
PRIOR = Path(os.environ["H1_PRIOR098_LA"]) if os.environ.get("H1_PRIOR098_LA") else None
PROFILE_TIMES = [60, 120, 180, 240, 300, 360, 400]
MASK_MAIN = "UB0.2"
from ledsa_h1_config import SAT_MAX_PCT  # noqa: E402
tg = s0.grid()
# Kamera verschoben -> Rohwerte nach t_cut gesperrt (auch die der frueheren Auswertung: gleiche Bilder, feste
# Suchbereiche). Hep_220_S1_R2 N1: LED-Schwerpunkte (la_drift_led.py) bei 320 s noch ~0 px, ab 1280 s quer ~-5,5 px
# (dazwischen Signal zu schwach); Lichtverlust im Suchquadrat 15-23 % -> k ~0,01-0,03 1/m zu hoch (la_drift_sens.py).
# Festgelegt 2026-11-27.
CAM_MOVED = {("Hep_220_S1_R2", "N1"): 320.0}
# Ganz gesperrt (festgelegt 2026-11-27): Kamerahoehe ungeklaert (Positionstabelle 0,686 m, Bildgeometrie ~0,23 m),
# Suchbild mit Gegenstand/Person im Strahl (nur 59 von 150 LEDs von LED 2), Einzelversuch (METHODS.md).
EXCLUDED = {("Hep_160_S2_R2", "J4"): "Kamerahoehe ungeklaert, Suchbild verdeckt, Einzelversuch"}


def cut_moved(run, cam, ser):
    t_cut = CAM_MOVED.get((run, cam))
    if t_cut is None or not ser:
        return ser
    for a, (t, k, *_) in ser.items():
        k[np.asarray(t, float) > t_cut, :] = np.nan
    print(f"  {run} {cam}: Kamera verschoben -> gesperrt ab t > {t_cut:g} s")
    return ser


def ref_span(run, cam):
    """Zeitspanne der gewaehlten Referenzbilder [s] (geprueft: <= 2 % der LEDs > 20 % daneben, la.select_ref_images).
    Nullungsfenster der Langachse (Abweichung von der Raumauswertung, festgelegt 2026-11-26): Hep_220_S1_R1 N1 LED 2 ist
    von -24 bis +1 s auf 0,6-1,1 m verdeckt (Rohwert k ~ 0,5 1/m, ab +6 s 0) -> das Fenster [-5, +10] s verschiebt die
    Reihe um bis zu -0,5 1/m. In der Spanne der Referenzbilder (dort z. B. -79 bis +11 s) sind verdeckte Bilder eine
    Minderheit, der Median ist robust."""
    work = la.workdir(run, cam)
    info = pd.read_csv(work / "analysis" / "image_infos_analysis.csv")
    info.columns = ["img_id", "name", "time", "t_exp"]
    tr = info.set_index("img_id").loc[la.ref_ids(work), "t_exp"].to_numpy(float)
    return float(tr.min()) - 0.5, float(tr.max()) + 0.5


def ours(run, cam):
    work = la.workdir(run, cam)
    kdir = work / "analysis" / "extinction_coefficients" / "linear" / "farbg_sum_col_val"
    m = pd.read_csv(work / "mask.csv.gz")
    crit = [MASK_MAIN] + (["SNR3"] if "SNR3" in set(m.krit) else [])
    m = m[m.krit.isin(crit)].groupby(["led_array", "t_s", "layer"], as_index=False).gesperrt.any()
    sat = pd.read_csv(la.SETUP / "la_saturation.csv", comment="#")
    sat = sat[(sat.run == run) & (sat.cam == cam)].set_index("array").sat_frac_pct
    out = {}
    for a in (0, 1):
        if sat.get(a, 0) > SAT_MAX_PCT:          # wie die Raumauswertung (ledsa_h1_config.SAT_MAX_PCT)
            print(f"  {run} {cam} Array {a}: {sat[a]:.1f} % der LEDs gesaettigt (> {SAT_MAX_PCT:g} %) -> entfaellt")
            continue
        t, k, cen = s0.load_k(kdir / f"extinction_coefficients_linear_channel_{la.CH}_farbg_sum_col_val_led_array_{a}.csv")
        k = s0.apply_mask(t, k, m[m.led_array == a], f"{run} {cam} {a}")
        A = np.loadtxt(work / f"led_array_{a}_distances_per_layer.txt")
        k[:, A.sum(axis=0) <= 0] = np.nan
        out[a] = (t, k, cen, crit)
    return out


def prior(run):
    if PRIOR is None:
        return None
    out = {}
    for a in (0, 1):
        f = PRIOR / f"ledsa_{run}_L2_array{a}_ch1.csv"
        if not f.exists():
            return None
        with open(f, encoding="utf-8") as fh:
            tops = np.array(fh.readline().strip().split(",")[1:], float)
        d = pd.read_csv(f, header=None, skiprows=1).to_numpy(float)
        out[a] = (d[:, 0], d[:, 1:], tops - 0.05)
    return out


def process(ser, tag, win):
    """paper_series je Schicht mit Nullungsfenster win (Referenzbild-Spanne, s. ref_span); < 2 Werte -> NaN-Schicht."""
    res = {}
    for a, (t, k, cen, *_) in ser.items():
        V = []
        for j in range(len(cen)):
            try:
                if not np.isfinite(k[:, j]).any():
                    raise SystemExit
                V.append(P.paper_series(t, k[:, j].copy(), la.CH, f"{tag} A{a} S{j}", win))
            except SystemExit:
                V.append(np.full_like(tg, np.nan))
        res[a] = (np.array(V), cen)
    return res


def main():
    OUT.mkdir(exist_ok=True)
    s = la._csv("la_series.csv")
    rows_k, rows_p, rows_c = [], [], []
    for r in s.itertuples():
        work = la.workdir(r.run, r.cam)
        if (r.run, r.cam) in EXCLUDED:
            print(f"  {r.run} {r.cam}: gesperrt ({EXCLUDED[(r.run, r.cam)]})")
            continue
        if not (work / "mask.csv.gz").exists():
            print(f"  {r.run} {r.cam}: keine Maske (Kette nicht fertig)")
            continue
        win = ref_span(r.run, r.cam)
        print(f"  {r.run} {r.cam}: Nullungsfenster {win[0]:.1f} bis {win[1]:.1f} s (Referenzbilder)")
        o = process(cut_moved(r.run, r.cam, ours(r.run, r.cam)), f"{r.run} {r.cam}", win)
        pr = cut_moved(r.run, r.cam, prior(r.run)) if r.cam == "N1" else None
        A = process(pr, f"prior098 {r.run}", win) if pr else None
        for a, (V, cen) in o.items():
            for j, z in enumerate(cen):
                ok = np.isfinite(V[j])
                rows_k.append(pd.DataFrame(dict(run=r.run, cam=r.cam, array=a, layer=j, z_m=round(float(z), 4),
                                                t_s=tg[ok], k=V[j][ok])))
            for tp in PROFILE_TIMES:
                for j, z in enumerate(cen):
                    rows_p.append(dict(run=r.run, cam=r.cam, src="neu", array=a, t_s=tp, z_m=round(float(z), 4),
                                       k=P.window_mean(V[j], tg, tp)))
                if A:
                    VA, cA = A[a]
                    for j, z in enumerate(cA):
                        rows_p.append(dict(run=r.run, cam=r.cam, src="prior098", array=a, t_s=tp,
                                           z_m=round(float(z), 4), k=P.window_mean(VA[j], tg, tp)))
            if A:
                VA, cA = A[a]
                # fruehere Auswertung auf unsere Schichtmitten interpoliert (Hoehe), dann je Zeitfenster
                VAi = np.array([np.interp(cen, cA, VA[:, i], left=np.nan, right=np.nan) for i in range(len(tg))]).T
                for lo, hi in ((0, 120), (120, 300), (300, 600)):
                    w = (tg >= lo) & (tg < hi)
                    x, y = V[:, w], VAi[:, w]
                    both = np.isfinite(x) & np.isfinite(y)
                    big = both & (np.abs(x) > 0.05)
                    rows_c.append(dict(run=r.run, cam=r.cam, array=a, t_von=lo, t_bis=hi, n=int(both.sum()),
                                       med_abs_diff=float(np.median(np.abs(x[both] - y[both]))) if both.any() else np.nan,
                                       med_ratio_prior_neu=float(np.median(y[big] / x[big])) if big.any() else np.nan,
                                       neu_mean=float(np.nanmean(np.where(both, x, np.nan))) if both.any() else np.nan,
                                       prior_mean=float(np.nanmean(np.where(both, y, np.nan))) if both.any() else np.nan))
    dk = pd.concat(rows_k, ignore_index=True)
    dk.to_csv(OUT / "la_k_1s.csv.gz", index=False, float_format="%.5f")
    pd.DataFrame(rows_p).to_csv(OUT / "la_profiles.csv", index=False, float_format="%.5f")
    print(f"[ok] {OUT}")
    if rows_c:
        dc = pd.DataFrame(rows_c)
        dc.to_csv(OUT / "la_cmp_prior098.csv", index=False, float_format="%.4f")
        pd.set_option("display.width", 220)
        print(dc.round(3).to_string(index=False))
    if P.base_log:
        print(f"[!] Nullung protokolliert in {len(P.base_log)} Reihen")


if __name__ == "__main__":
    main()
