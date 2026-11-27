"""Vergleich mit frueheren Auswertungen (METHODS.md section 6.4; 2026-11-24). Nur lesen.

Quellen (je Raum, an den LEM-Hoehen und als Profil):
  prior0130  frueherer, unabhaengiger LEDSA-0.13.0-Stand (Ordner per H1_PRIOR0130; nur lesen): Einzelkameras C1-C3 in
         Hep_160_S2_R2 (farbg_sum_col_val und sum_col_val, average_images 5) und Hep_160_S2_R3 (nur sum_col_val).
         Zeitachse ueber die Bildnamen auf unsere Versuchszeit gebracht (S2_R2: dort erstes Bild = 0 s, bei uns -121,24 s).
  prior0100  fruehere Stapel LEDSA 0.10.0 (Ordner per H1_PRIOR0100, Standard 2_Analysis/LEDSA/stacked_results;
         sum_col_val): S2_R2 F1/F2/F3, S2_R3 F2/F3, S4_R1/R2 F2 (Kameras laut config_stacked.ini: untere + obere
         Position des Raums).
  neu    unsere Inversion derselben Kamera bzw. desselben Kamerapaars (Stapel), farbg und sum, und unsere Hauptquelle
         (main, je Kanal ohne gesaettigte Kanaele, mit Maske).
Gleiche Nachbearbeitung fuer alle (ledsa_h1_profiles.paper_series: robuste Nullung [-5, +10] s, bei prior0130 [-30, +15] s
(5er-Mittel), Widmann, Sigma-Clip (Ausgaben vom 2026-11-24, vor dem Wechsel zum Hampel-Filter am
2026-11-27; nicht neu erzeugt, die frueheren Staende liegen nicht im Repo);
+-10 s), ohne Maske ausser main; Kennzahlen gegen LEM wie ledsa_h1_stage4 (Spitze, Plateau, mard). Profile: mittlere
|Delta k| gegen unsere gleiche Quelle bei 200/400/600/800 s (Schichtmitten interpoliert, 0-2,5 m).
Aufruf: hh2-venv compare_prior.py <LEDSA-Ordner> <out-Ordner>  -> compare_prior_lem.csv, compare_prior_profiles.csv
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(sys.argv[1]); OUT = Path(sys.argv[2])
sys.path.insert(0, str(HERE))
import ledsa_h1_stage0 as s0                                         # noqa: E402
import ledsa_h1_profiles as P                                        # noqa: E402
from ledsa_h1_config import RUNS, channel_source, rooms, saturated, series   # noqa: E402
from ledsa_h1_paths import need_env                                  # noqa: E402

# Fruehere Staende (nicht in diesem Repo): Ordner per H1_PRIOR0130 (ohne Standard) bzw. H1_PRIOR0100
PRIOR0130 = Path(need_env("H1_PRIOR0130", "Ordner des frueheren LEDSA-0.13.0-Stands"))
PRIOR0100 = Path(os.environ.get("H1_PRIOR0100", str(HERE / "stacked_results")))
CAM_ROOM = {"C1": "F2", "C2": "F1", "C3": "F3"}         # S2-Laeufe: BCL-Kameras unten (F?L)
PRIOR0100_SEL = [("Hep_160_S2_R2", "F1", "stacked_F1"), ("Hep_160_S2_R2", "F2", "stacked_F2"),
               ("Hep_160_S2_R2", "F3", "stacked_F3"), ("Hep_160_S2_R3", "F2", "stacked_F2"),
               ("Hep_160_S2_R3", "F3", "stacked_F3"), ("Hep_160_S4_R1", "F2", "stacked"), ("Hep_160_S4_R2", "F2", "stacked")]
tg = s0.grid()


def need(f):
    if not Path(f).exists():
        raise SystemExit(f"[--] fehlt {f}")
    return f


def series_from(kdir, prop, shift=0.0, mask=None, pattern="extinction_coefficients_linear_channel_{a}_{p}_led_array_{a}.csv",
                chans=(0, 1, 2)):
    """{Kanal: (t, k[t, Schicht], Schichtmitten)} mit Zeitverschiebung und optionaler Maske."""
    out = {}
    for a in chans:
        t, k, cen = s0.load_k(need(kdir / pattern.format(a=a, p=prop)))
        if mask is not None:
            k = s0.apply_mask(t, k, mask[mask.led_array == a], f"{kdir} Array {a}")
        out[a] = (t + shift, k, cen)
    return out


PRIOR0130_BASE_WIN = (-30.0, 15.0)   # prior0130 S2_R2 mittelt je 5 Bilder (~25 s Abstand) -> im Standardfenster < 2 Werte


def processed(ser, z=None, win=P.BASE_WIN_S):
    """Mittel der Kanaele nach Paper-Nachbearbeitung; an Hoehe z (Schicht naechster Mitte) oder alle Schichten."""
    vs = []
    for a, (t, k, cen) in ser.items():
        js = [int(np.argmin(np.abs(cen - z)))] if z is not None else range(len(cen))
        vs.append(np.array([P.paper_series(t, k[:, j], a, "cmp", win) for j in js]))
    cen = next(iter(ser.values()))[2]
    return np.nanmean(vs, axis=0), cen


def prior0130_shift(run, cam):
    cols = ["id", "name", "clock", "t"]
    a = pd.read_csv(need(PRIOR0130 / run / cam / "image_infos.csv"))
    a.columns = cols
    w = RUNS / run / f"{series(run, cam).position}_{cam}"
    o = pd.read_csv(need(w / "analysis" / "image_infos_analysis.csv"))
    o.columns = cols
    m = a.merge(o, on="name", suffixes=("_a", "_o"))
    d = m.t_o - m.t_a
    if len(m) < 10 or d.std() > 0.05:
        raise SystemExit(f"[--] {run} {cam}: Zeitversatz nicht bestimmbar ({len(m)} Bilder, sd {d.std():.3f} s)")
    return float(d.median()), len(m)


def metrics_vs_lem(v, Lh, tv):
    ml, mm = s0.metrics(Lh, tv), s0.metrics(v, tv)
    sl, sv = s0.smooth(Lh), s0.smooth(v)
    win = (tg > 0) & (tg < tv - 20) & (sl >= 0.2 * ml["peak"])
    rel = sv[win] / sl[win]
    return dict(lem_peak=ml["peak"], peak_ratio=mm["peak"] / ml["peak"], plateau_ratio=mm["plateau"] / ml["plateau"],
                mard=np.nanmean(np.abs(rel - 1)) if win.any() else np.nan)


def profile(ser, win=P.BASE_WIN_S):
    v, cen = processed(ser, win=win)
    return {tp: np.array([P.window_mean(v[j], tg, tp) for j in range(len(cen))]) for tp in P.PROFILE_TIMES}, cen


def prof_diff(pa, ca, pb, cb):
    zz = np.arange(0.05, 2.5, 0.1)
    return {tp: float(np.nanmean(np.abs(np.interp(zz, ca, pa[tp]) - np.interp(zz, cb, pb[tp])))) for tp in pa}


rows_l, rows_p = [], []
sat = saturated()


def add(run, room, label, ser, ref_label=None, ref_ser=None):
    win = PRIOR0130_BASE_WIN if label.startswith("prior0130") else P.BASE_WIN_S
    L = s0.lem(run, room)
    tv = s0.vent(run)
    for h in L:
        v, _ = processed(ser, h, win)
        rows_l.append(dict(run=run, room=room, z_lem=h, source=label, **metrics_vs_lem(v[0], L[h], tv)))
    if ref_ser is not None:
        pa, ca = profile(ser, win)
        pb, cb = profile(ref_ser)
        for tp, dv in prof_diff(pa, ca, pb, cb).items():
            rows_p.append(dict(run=run, room=room, source=label, against=ref_label, t_s=tp, mean_abs_dk=dv,
                               mean_k_ref=float(np.nanmean(pb[tp]))))


# Einzelkameras des frueheren 0.13.0-Stands gegen unsere gleiche Kamera
for run, props in (("Hep_160_S2_R2", ("farbg_sum_col_val", "sum_col_val")), ("Hep_160_S2_R3", ("sum_col_val",))):
    for cam, room in CAM_ROOM.items():
        if not (PRIOR0130 / run / cam).exists():
            continue
        sh, n = prior0130_shift(run, cam)
        print(f"{run} {cam}: Zeit prior0130 + {sh:+.2f} s = unsere Versuchszeit ({n} Bilder abgeglichen)")
        w = RUNS / run / f"{series(run, cam).position}_{cam}"
        have_ours = (w / "analysis" / "extinction_coefficients").exists()
        for prop in props:
            ser_a = series_from(PRIOR0130 / run / cam / "analysis" / "extinction_coefficients" / "linear" / prop, prop, sh)
            ser_o = series_from(w / "analysis" / "extinction_coefficients" / "linear" / prop, prop) if have_ours else None
            add(run, room, f"prior0130 {cam} {prop.split('_')[0]}", ser_a, f"neu {cam} {prop.split('_')[0]}", ser_o)
            if have_ours:
                add(run, room, f"neu {cam} {prop.split('_')[0]}", ser_o)
            else:
                print(f"  {run} {cam}: bei uns nicht invertiert (ausgeschlossen)")

# Fruehere 0.10.0-Stapel gegen unseren Stapel derselben Kameras und unsere Hauptquelle
for run, room, sub in PRIOR0100_SEL:
    kb = PRIOR0100 / run / sub / "analysis" / "extinction_coefficients" / "linear"
    ser_b = series_from(kb, "sum_col_val")
    cams = rooms(run)[room]
    st = RUNS / run / f"stacked_{room}" / "analysis" / "extinction_coefficients" / "linear"
    ser_s = series_from(st / "sum_col_val", "sum_col_val") if len(cams) == 2 else None
    add(run, room, "prior0100 stack sum", ser_b, f"neu stack {'+'.join(cams)} sum" if ser_s else None, ser_s)
    if ser_s is not None:
        add(run, room, f"neu stack {'+'.join(cams)} sum", ser_s)
        add(run, room, f"neu stack {'+'.join(cams)} farbg", series_from(st / "farbg_sum_col_val", "farbg_sum_col_val"))
    main = {}
    for a in range(3):
        cs = channel_source(run, room, a, sat)
        if cs is None:
            continue
        m = s0.mask_for(run, room, cs[1])
        main.update(series_from(cs[0] / "analysis" / "extinction_coefficients" / "linear" / "farbg_sum_col_val",
                                "farbg_sum_col_val", mask=m, chans=(a,)))
    if main:
        add(run, room, f"neu main ({''.join(map(str, sorted(main)))})", main)

dl, dp = pd.DataFrame(rows_l), pd.DataFrame(rows_p)
dl.to_csv(OUT / "compare_prior_lem.csv", index=False, float_format="%.4f")
dp.to_csv(OUT / "compare_prior_profiles.csv", index=False, float_format="%.4f")
pd.set_option("display.width", 220)
print("\nGegen LEM (Mittel der Kanaele):")
print(dl.round(3).to_string(index=False))
print("\nProfile: mittlere |Delta k| gegen unsere gleiche Quelle (1/m), in Klammern mittleres k der Bezugsquelle:")
print(dp.assign(v=dp.mean_abs_dk.round(3).astype(str) + " (" + dp.mean_k_ref.round(2).astype(str) + ")")
      .pivot_table(index=["run", "room", "source"], columns="t_s", values="v", aggfunc="first").to_string())
