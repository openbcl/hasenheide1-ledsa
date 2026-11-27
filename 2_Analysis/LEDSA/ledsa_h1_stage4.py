# -*- coding: utf-8 -*-
r"""Stufe 4 der H1-LEDSA-Auswertung (LEDSA 0.13.0): Vergleich mit dem LEM je Quelle, Saettigung der Referenzbilder.

lem   Je Lauf, Raum und LEM-Hoehe, fuer jede Quelle des Raums (main = Hauptquelle je Kanal wie die Profile, Stapel bei
      zwei Kameras, jede Einzelkamera des Raums, Nebenvariante mitC1 gekennzeichnet; gesaettigte Kanaele ausgeschlossen,
      Spalte channels = verwendete Kanaele): k an der LEM-Hoehe (Schicht mit naechster Mitte) nach ledsa_h1_profiles
      (Maske SNR 3 je Quelle, robuste Nullung, Widmann, Hampel-Filter), je Kanal und Mittel der Kanaele. LEM wie
      ledsa_h1_stage0.lem (Hampel-Filter). Beide danach gleich gefiltert (gleitendes +-10-s-Mittel), erst dann
      Spitze und Plateau. Spitze in (0, Lueftung), Plateau [Lueftung - 300, Lueftung - 20] s je Lauf
      (setup/ledsa_h1_runs.csv). Dazu mittlere relative Abweichung |LEDSA/LEM - 1| ueber die Zeit mit LEM >= 20 % seiner
      Spitze, vor der Lueftung - 20 s (mard). Fehlende Eingaben brechen ab.
      -> inventory/ledsa_h1_stage4_lem.csv
sat   Saettigung: je Serie (Kamera mit config_analysis.ini) und Array/Kanal Anteil der LEDs, deren max_col_value in
      einem der Referenzbilder >= 0,98 x 16383 (14-bit-Rohdaten, Vollausschlag beobachtet 16383).
      -> inventory/ledsa_h1_saturation.csv
Aufruf: hh2-venv  ledsa_h1_stage4.py [lem|sat|all]
"""
import configparser
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ledsa_h1_stage0 as s0                                     # noqa: E402
import ledsa_h1_profiles as P                                    # noqa: E402
from ledsa_h1_config import VARIANT, RUNS, channel_source, rooms, saturated, series   # noqa: E402

OUT_LEM = HERE / "inventory" / "ledsa_h1_stage4_lem.csv"
OUT_SAT = HERE / "inventory" / "ledsa_h1_saturation.csv"
FULL = 16383
SAT_FRAC = 0.98
MARD_LEM_FRAC = 0.2
# Nebenvariante mitC1: Zeitachse = C1 (erstes Bild +30 s), Referenzbilder 30,5-40,5 s -> Nullung auf deren Fenster
VARIANT_BASE_WIN = (30.0, 45.0)


def sources(run, room, sat):
    """[(Quelle, Art, {Kanal: (Ordner, Maskendatei, Maskenquelle)})]; Art: main / stack / upper / lower / variant.
    Gesaettigte Kanaele (ledsa_h1_config.saturated, > SAT_MAX_PCT %) fehlen in jeder Quelle, die die Kamera enthaelt;
    main = Hauptquelle je Kanal wie in den Profilen (ledsa_h1_config.channel_source)."""
    cams = rooms(run)[room]
    free = lambda cs, a: all((run, c, a) not in sat for c in cs)
    mf = f"mask_{room}.csv.gz"
    out = []
    main = {}
    for a in range(3):
        cs = channel_source(run, room, a, sat)
        if cs is not None:
            main[a] = (cs[0], mf, cs[1])
    out.append(("main", "main", main))
    if len(cams) == 2:
        out.append(("+".join(cams), "stack",
                    {a: (RUNS / run / f"stacked_{room}", mf, f"stacked_{room}") for a in range(3) if free(cams, a)}))
    for cam in cams:
        pos = series(run, cam).position
        out.append((cam, "upper" if pos.endswith("U") else "lower",
                    {a: (RUNS / run / f"{pos}_{cam}", mf, cam) for a in range(3) if free([cam], a)}))
    var = RUNS / run / f"stacked_{room}_mitC1"
    if var.exists():
        out.append(("C1+J2 (mitC1)", "variant", {a: (var, f"mask_{room}_mitC1.csv.gz", f"stacked_{room}_mitC1")
                                                 for a in range(3) if free(["C1", "J2"], a)}))
    return [o for o in out if o[2]]


def lem_table():
    runs = pd.read_csv(HERE / "setup" / "ledsa_h1_runs.csv", comment="#").run
    tg = s0.grid()
    rows = []
    sat = saturated()
    for run in runs:
        tv = s0.vent(run)
        cfg = P.config_of(run)
        for room in rooms(run):
            if not (RUNS / run / f"stage3r1_{room}_ok").exists():     # Neulauf nach der Korrektur vom 2026-11-24 (wie Profile)
                raise SystemExit(f"[--] {run} {room}: Neulauf Stufe 3 nicht fertig (Marke stage3r1_{room}_ok fehlt)")
            L = s0.lem(run, room)
            if not L:
                print(f"  {run} {room}: kein LEM")
                continue
            for src, art, chmap in sources(run, room, sat):
                per_ch = {}
                for a, (base, mfile, mq) in chmap.items():
                    mf = RUNS / run / "plots_h1" / mfile
                    if not mf.exists():
                        raise SystemExit(f"[--] fehlt {mf}")
                    m = pd.read_csv(mf)
                    m = m[(m.snr == 3.0) & (m.quelle == mq)]
                    if m.empty:
                        raise SystemExit(f"[--] {mf}: keine Zeilen fuer {mq}")
                    kd = base / "analysis" / "extinction_coefficients" / "linear" / "farbg_sum_col_val"
                    f = kd / f"extinction_coefficients_linear_channel_{a}_farbg_sum_col_val_led_array_{a}.csv"
                    if not f.exists():
                        raise SystemExit(f"[--] fehlt {f}")
                    t, k, cen = s0.load_k(f)
                    k = s0.apply_mask(t, k, m[m.led_array == a], f"{run} {room} {src} Array {a}")
                    for h in L:
                        j = int(np.argmin(np.abs(cen - h)))
                        per_ch.setdefault(h, {})[a] = (P.paper_series(t, k[:, j], a, f"{run} {room} {src} {a}",
                                                                      VARIANT_BASE_WIN if art == "variant" else P.BASE_WIN_S),
                                                       cen[j])
                for h, chs in per_ch.items():
                    ml = s0.metrics(L[h], tv)
                    sl = s0.smooth(L[h])
                    win = (tg > 0) & (tg < tv - 20) & (sl >= MARD_LEM_FRAC * ml["peak"])
                    zc0 = next(iter(chs.values()))[1]
                    for ch, (v, zc) in list(chs.items()) + [("mean", (np.nanmean([c[0] for c in chs.values()], axis=0),
                                                                     zc0))]:
                        mm = s0.metrics(v, tv)
                        sv = s0.smooth(v)
                        rel = sv[win] / sl[win]
                        rows.append(dict(config=cfg, run=run, room=room, z_lem=h, z_layer=round(float(zc), 3),
                                         source=src, kind=art, channel=ch, lem_peak=ml["peak"],
                                         lem_t_peak=ml["t_peak"], lem_plateau=ml["plateau"], peak=mm["peak"],
                                         t_peak=mm["t_peak"], plateau=mm["plateau"],
                                         peak_ratio=mm["peak"] / ml["peak"], plateau_ratio=mm["plateau"] / ml["plateau"],
                                         mard=np.nanmean(np.abs(rel - 1)) if win.any() else np.nan,
                                         n_mard_s=int(np.isfinite(rel).sum()), vent_s=tv,
                                         channels="ch" + "".join(str(c) for c in sorted(chs))))
    d = pd.DataFrame(rows)
    with open(OUT_LEM, "w", encoding="utf-8", newline="") as fh:
        fh.write("# ledsa_h1_stage4.py lem: LEDSA je Quelle gegen LEM an der LEM-Hoehe; beide Hampel-Filter + +-10 s; Spitze "
                 "(0, Lueftung), Plateau [Lueftung-300, Lueftung-20] s; mard = mittlere |LEDSA/LEM-1| bei LEM >= 20 % "
                 "Spitze vor Lueftung-20 s; k in 1/m\n")
        d.to_csv(fh, index=False, float_format="%.4f")
    print(f"[ok] {OUT_LEM} ({len(d)} Zeilen)")
    mean = d[d.channel == "mean"]
    pd.set_option("display.width", 220)
    print("\nMittel der Kanaele, je Art der Quelle (Median [p10, p90], n):")
    for col in ("peak_ratio", "plateau_ratio", "mard"):
        g = mean.groupby("kind")[col]
        print(f"  {col}: " + "; ".join(f"{k} {v.median():.2f} [{v.quantile(.1):.2f}, {v.quantile(.9):.2f}] n={v.count()}"
                                       for k, v in g))
    print("\nje Kamera (Einzelinversion), Mittel der Kanaele:")
    single = mean[mean.kind.isin(["upper", "lower"])]
    print(single.groupby("source")[["peak_ratio", "plateau_ratio", "mard"]].agg(["median", "count"]).round(2).to_string())
    print("\nje Kanal (alle Quellen):")
    print(d[d.channel != "mean"].groupby("channel")[["peak_ratio", "plateau_ratio", "mard"]].median().round(3).to_string())


def sat_table():
    s = pd.read_csv(HERE / "setup" / "ledsa_h1_series.csv", comment="#")
    rows = []
    for r in s.itertuples():
        work = RUNS / r.run / f"{r.position}_{r.cam}"
        ini = work / "config_analysis.ini"
        if not ini.exists():
            print(f"  {r.run} {r.cam}: keine config_analysis.ini (nicht invertiert)")
            continue
        c = configparser.ConfigParser(); c.read(ini)
        refs = [int(x) for x in c["DEFAULT"]["ref_img_indices"].split()]
        for a in range(3):
            idx = np.loadtxt(work / "analysis" / f"led_array_indices_{a:03d}.csv", dtype=int)
            mx = None
            for i in refs:
                f = work / "analysis" / f"channel{a}" / f"{i}_led_positions.csv"
                if not f.exists():
                    raise SystemExit(f"[--] fehlt {f}")
                d = pd.read_csv(f, comment="#", header=None, skipinitialspace=True).set_index(0)[4]
                d = d[d.index.isin(idx)]
                mx = d if mx is None else np.maximum(mx, d)
            rows.append(dict(run=r.run, cam=r.cam, array=a, channel=a, n_led=len(mx), max_value=float(mx.max()),
                             median_max=float(mx.median()),
                             sat_frac_pct=round(100 * float((mx >= SAT_FRAC * FULL).mean()), 2)))
    d = pd.DataFrame(rows)
    with open(OUT_SAT, "w", encoding="utf-8", newline="") as fh:
        fh.write(f"# ledsa_h1_stage4.py sat: max_col_value der LEDs in den Referenzbildern; gesaettigt = >= {SAT_FRAC} x "
                 f"{FULL}\n")
        d.to_csv(fh, index=False)
    print(f"[ok] {OUT_SAT} ({len(d)} Zeilen)")
    hit = d[d.sat_frac_pct > 0]
    print(f"Serien x Kanal mit gesaettigten LEDs: {len(hit)} von {len(d)}")
    print(hit.sort_values("sat_frac_pct", ascending=False).to_string(index=False))


if __name__ == "__main__":
    if VARIANT:
        raise SystemExit(f"[--] H1_VARIANT={VARIANT} gesetzt: Hauptauswertung nur ohne Variante rechnen")
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("sat", "all"):
        sat_table()
    if what in ("lem", "all"):
        lem_table()
