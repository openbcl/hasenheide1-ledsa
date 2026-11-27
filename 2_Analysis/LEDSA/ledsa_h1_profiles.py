# -*- coding: utf-8 -*-
r"""Hoehenprofile der H1-LEDSA-Auswertung (LEDSA 0.13.0) nach der Paper-Methode.

Methode wie das Paper (Skript plot_ledsa_profiles.py des nicht oeffentlichen Paper-Repositoriums, load_stacked_ledsa,
_extract_profile, _draw_vertical_profile), ueber ledsa_h1_stage0.py (paper_series):
  - je Lauf und Raum die Hauptinversion (Stapel stacked_<Raum> bei zwei Kameras, sonst die Einzelkamera; Raeume nach
    ledsa_h1_config.rooms, also ohne CAM_EXCLUDE), Groesse farbg_sum_col_val, Array i im Kanal i;
  - gesperrte (t, Schicht) der Maske (ledsa_h1_mask.py, SNR 3) vor der Nachbearbeitung NaN;
  - 1-s-Raster, Nullung robust: Median der freien Rohwerte in [-5, +10] s statt Wert bei t = 0 (Abweichung vom
    Paper, Begruendung in paper_series), Widmann-Faktor (638/lambda)^-1.0088 (628/521/468 nm), Hampel-Filter (51, k = 3);
  - Profilzeiten 200, 400, 600, 800 s; LEDSA je Lauf als Mittel ueber +-10 s (CSV je Kanal); LEM/SICK (SICK: Spalte
    _corr) naechster Messwert, ohne Mittelung.
  - Figur (Abweichung vom Paper, festgelegt 2026-11-24): statt Mittel +- Standardabweichung ueber die Laeufe je
    Lauf eine Linie (Mittel der verfuegbaren Kanaele, bis zu drei), Stapel durchgezogen, Einzelkamera gestrichelt, je Kanal gemischt
    strichpunktiert; LEM/SICK je Lauf.
Jede Profilzeit muss vor der Lueftung des Laufs liegen (setup/ledsa_h1_runs.csv), sonst Abbruch.
Fehlende Eingaben brechen ab.

Konfigurationen (Brennstoffmasse/Wannenflaeche aus den _processed.csv-Koepfen, Gruppierung wie 2_Analysis/HRR):
  Hep_220_300 = Hep_220_S1_R1-R4; Hep_160_150 = Hep_160_S1_R1-R3; Hep_160_075 = Hep_160_S2/S3/S4.

Ausgabe: inventory/ledsa_h1_profiles.csv (je Lauf, Raum, Kanal, Zeit, Schicht), inventory/ledsa_h1_profiles_points.csv
(LEM/SICK je Lauf), plots/ledsa_h1_profiles_<Konfiguration>.pdf (+ .png zur Ansicht).
Aufruf: hh2-venv  ledsa_h1_profiles.py [csv|plot|all]
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import ledsa_h1_stage0 as s0                                     # noqa: E402
from ledsa_h1_config import VARIANT, RUNS, SAT_MAX_PCT, channel_source, rooms, saturated   # noqa: E402

PROFILE_TIMES = [200, 400, 600, 800]
HALF_S = 10.0
ROOMS = ["F1", "F2", "F3"]
CONFIGS = {"Hep_220_300": r"^Hep_220_S1_R\d$", "Hep_160_150": r"^Hep_160_S1_R\d$",
           "Hep_160_075": r"^Hep_160_S[234]_R\d$"}
OUT_K = HERE / "inventory" / "ledsa_h1_profiles.csv"
OUT_P = HERE / "inventory" / "ledsa_h1_profiles_points.csv"
PLOTS = HERE / "plots"


def config_of(run):
    hit = [c for c, rx in CONFIGS.items() if re.match(rx, run)]
    if len(hit) != 1:
        raise SystemExit(f"[--] {run}: keine eindeutige Konfiguration ({hit})")
    return hit[0]


BASE_WIN_S = (-5.0, 10.0)
base_log = []


def paper_series(t, k, ch, tag, win=BASE_WIN_S):
    """wie ledsa_h1_stage0.paper_series, aber Nullung robust: Median der freien Rohwerte (Maske) in BASE_WIN_S statt
    Wert bei t = 0 (Paper). Grund: im Brandraum F1 verdeckt die zuendende Person im Bild bei t ~ 0 die unteren LEDs
    der Kamera J3 (Hep_160_S1_R2, Hep_160_S2_R1: k bis ~5 1/m in diesem einen Bild, Maske greift nicht, weil < 50 %
    der Strahlen ungueltig; die Maske sperrt dort nur einzelne Schichten) -> Paper-Nullung verschiebt die ganze Reihe.
    Jede Reihe mit |Paper - robust| > 0,01 1/m oder gesperrtem t = 0 wird protokolliert; Zahlen je Lauf im Log."""
    tg = s0.grid()
    v = np.interp(tg, t, k, left=np.nan, right=np.nan)
    w = (t >= win[0]) & (t <= win[1]) & np.isfinite(k)
    if w.sum() < 2:
        raise SystemExit(f"[--] {tag}: < 2 freie Rohwerte in {win} s fuer die Nullung")
    base = float(np.median(k[w]))
    v0 = v[int(np.argmin(np.abs(tg)))]
    if win == BASE_WIN_S and (not np.isfinite(v0) or abs(v0 - base) > 0.01 or w.sum() < 3):
        # n_base < 3: Median aus 2 Werten = Mittel, nicht robust gegen ein verdecktes Bild -> protokollieren
        base_log.append(dict(tag=tag, base_paper=v0, base_robust=base, n_base=int(w.sum())))
    return s0.outlier_filter((v - base) * s0.widmann(ch))


def window_mean(v, tg, t):
    m = (tg >= t - HALF_S) & (tg <= t + HALF_S)
    w = v[m]
    w = w[np.isfinite(w)]
    return float(w.mean()) if w.size else np.nan


def build_csv():
    runs = pd.read_csv(HERE / "setup" / "ledsa_h1_runs.csv", comment="#")
    tg = s0.grid()
    rows_k, rows_p, sat_log = [], [], []
    sat = saturated()
    for run in runs.run:
        cfg = config_of(run)
        tv = s0.vent(run)
        if max(PROFILE_TIMES) + HALF_S >= tv:
            raise SystemExit(f"[--] {run}: Profilzeit {max(PROFILE_TIMES)} s +- {HALF_S:g} s nicht vor der Lueftung "
                             f"{tv:.0f} s")
        rr = rooms(run)
        for room in rr:
            # Marke des Neulaufs nach der Korrektur vom 2026-11-24 (LED-Hoehen nach Index); alte stage3_<Raum>_ok reicht nicht mehr
            if not (RUNS / run / f"stage3r1_{room}_ok").exists():
                raise SystemExit(f"[--] {run} {room}: Neulauf Stufe 3 nicht fertig (Marke stage3r1_{room}_ok fehlt)")
            for a in range(3):
                src = channel_source(run, room, a, sat)
                if src is None:
                    sat_log.append(f"{run} {room} Kanal {a}: alle Kameras gesaettigt -> entfaellt")
                    continue
                base, quelle, cams = src
                if "+" not in cams and len(rr[room]) == 2:
                    sat_log.append(f"{run} {room} Kanal {a}: nur {cams} (andere Kamera gesaettigt)")
                kdir = base / "analysis" / "extinction_coefficients" / "linear" / "farbg_sum_col_val"
                mask = s0.mask_for(run, room, quelle)
                if mask.empty:
                    raise SystemExit(f"[--] {run} {room}: Maske ohne Zeilen fuer {quelle}")
                f = kdir / f"extinction_coefficients_linear_channel_{a}_farbg_sum_col_val_led_array_{a}.csv"
                if not f.exists():
                    raise SystemExit(f"[--] fehlt {f}")
                t, k, cen = s0.load_k(f)
                k = s0.apply_mask(t, k, mask[mask.led_array == a], f"{run} {room} {quelle} Array {a}")
                for j, z in enumerate(cen):
                    v = paper_series(t, k[:, j], a, f"{run} {room} Array {a} Schicht {j}")
                    for tp in PROFILE_TIMES:
                        rows_k.append(dict(config=cfg, run=run, room=room, source=quelle, cams=cams, channel=a,
                                           t_s=tp, layer=j, z_m=round(float(z), 4), k=window_mean(v, tg, tp)))
        meas = pd.read_csv(REPO / "1_Measurements" / run / "1_Processed_data" / f"{run}_processed.csv", comment="#",
                           encoding="utf-8-sig")
        tm = meas["Time (s)"].to_numpy(float)
        for c in meas.columns:
            m = re.match(r"Extinction (LEM)_\d+_(F\d)_([\d.]+) \(1/m\)$", c) or \
                re.match(r"Extinction (SICK)_(F\d)_([\d.]+) IR \(1/m\)_corr$", c)
            if not m or meas[c].notna().sum() < 100:
                continue
            for tp in PROFILE_TIMES:
                i = int(np.argmin(np.abs(tm - tp)))
                rows_p.append(dict(config=cfg, run=run, room=m.group(2), instrument=m.group(1),
                                   z_m=float(m.group(3)), t_s=tp, t_sample_s=round(float(tm[i]), 2),
                                   k=float(meas[c].iloc[i])))
    dk, dp = pd.DataFrame(rows_k), pd.DataFrame(rows_p)
    with open(OUT_K, "w", encoding="utf-8", newline="") as fh:
        fh.write("# ledsa_h1_profiles.py: LEDSA 0.13.0 H1, Hauptinversion je Raum, farbg, Maske SNR 3, Paper-Methode "
                 "(Nullung robust [-5, +10] s, Widmann, Hampel-Filter), Mittel +-10 s; je Kanal ohne gesaettigte Kameras; k in 1/m\n")
        dk.to_csv(fh, index=False, float_format="%.5f")
    with open(OUT_P, "w", encoding="utf-8", newline="") as fh:
        fh.write("# ledsa_h1_profiles.py: LEM und SICK (_corr) naechster Messwert zur Profilzeit; k in 1/m\n")
        dp.to_csv(fh, index=False, float_format="%.5f")
    print(f"[ok] {OUT_K} ({len(dk)} Zeilen), {OUT_P} ({len(dp)} Zeilen)")
    print(f"Saettigung (> {SAT_MAX_PCT:g} % LEDs): " + ("; ".join(sat_log) if sat_log else "keine Wirkung"))
    if base_log:
        b = pd.DataFrame(base_log)
        print(f"[!] robuste Nullung protokolliert in {len(b)} Reihen (> 0,01 1/m vom Wert bei t = 0, t = 0 gesperrt oder "
              f"< 3 freie Rohwerte; davon {int((b.n_base < 3).sum())} mit < 3):")
        print(b.assign(raum=b.tag.str.rsplit(" Array", n=1).str[0], d=(b.base_paper - b.base_robust).abs(),
                       n2=b.n_base < 3).groupby("raum").agg(
            n=("tag", "size"), n_unter3=("n2", "sum"), max_abw=("d", "max"),
            max_robust=("base_robust", lambda x: x.abs().max())).round(3).to_string())
    n = dk.groupby(["config", "room"]).run.nunique().unstack()
    print("Laeufe je Konfiguration und Raum:\n" + n.to_string())


def plot():
    """Je Konfiguration Raster Raum x Profilzeit; je Lauf eine Linie (Mittel der verfuegbaren Kanaele, bis zu drei,
    alle Widmann-korrigiert),
    Farbe = Lauf, durchgezogen = Stapel (zwei Kameras), gestrichelt = Einzelkamera, strichpunktiert = je Kanal
    gemischt; LEM (Raute) und SICK (Quadrat) je
    Lauf in dessen Farbe. Stil: fireplot (fire-preprint-template, Ordner fireplot/), Laufnamen <Serie>_R<n> aus
    runs.csv (Konvention des Repro-Pakets hasenheide1-reproduction).

    # Caption (Figure): LEDSA extinction-coefficient profiles k(z) of the tests of one series (R1-R<n>, runs.csv) in
    #   rooms F1-F3 at t = 200, 400, 600 and 800 s (time zero of the test; ignition 0.5-2.8 s later); n = number of
    #   tests with a LEDSA result in that room. Each line is the mean over the colour channels used for that room (up
    #   to three, main source per channel), averaged over +-10 s, Widmann-corrected to 638 nm (LEM wavelength);
    #   the k axis starts at 0, so line values <= 0 (down to -0.004 1/m) lie on the axis. Solid: inversion of
    #   both cameras of the room, dashed: one camera, dash-dotted: stack in some channels, single camera in others. Markers: LEM (filled diamond) and SICK (open square, Widmann-corrected)
    #   at their heights, nearest sample without averaging, same colour as the test; drawn only for tests with a LEDSA
    #   result in that room (n) and where the instrument recorded data. The k axis range differs between the series.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    import fireplot as fp
    for f in (OUT_K, OUT_P):
        if not f.exists():
            raise SystemExit(f"[--] fehlt {f} (erst: ledsa_h1_profiles.py csv)")
    dk, dp = pd.read_csv(OUT_K, comment="#"), pd.read_csv(OUT_P, comment="#")
    names = pd.read_csv(REPO / "runs.csv", comment="#").set_index("run").name.to_dict()
    # Ein Schema fuer alle Figuren: Farbe = Nummer R<n> des Tests in seiner Serie, Linie = Quelle der Inversion
    scheme = fp.SeriesScheme(
        group_colors={nm: f"C{int(nm.rsplit('_R', 1)[1]) - 1}" for nm in names.values()},
        subgroup_linestyles={"stack": "-", "single": "--", "mixed": "-."},
        subgroup_labels={"stack": "two cameras", "single": "one camera",
                         "mixed": "mixed by channel"})
    inst_mk = {"LEM": "D", "SICK": "s"}
    # LEM gefuellt, SICK hohl und groesser (liegt oft auf derselben Hoehe wie LEM)
    inst_kw = {"LEM": dict(marker="D", ms=4, mec="black", mew=0.4),
               "SICK": dict(marker="s", ms=6.5, mfc="none", mew=1.1)}
    PLOTS.mkdir(exist_ok=True)
    with fp.paper_style(require_latex=True):
        for cfg in CONFIGS:
            k = dk[dk.config == cfg]
            p = dp[dp.config == cfg]
            runs = sorted(k.run.unique(), key=lambda r: names[r])
            # Mittel der freien Kanaele je Schicht (nach Schichtindex: Einzelkamera-Dateien runden die Schichtmitten
            # auf 0,01 m, Stapel nicht; Gruppierung nach z_m mischte in Raeumen mit gemischter Quelle)
            prof = k.groupby(["run", "room", "t_s", "layer"], as_index=False).agg(k=("k", "mean"), z_m=("z_m", "max"))
            kind = k.groupby(["run", "room"]).cams.agg(lambda c: "stack" if all("+" in x for x in c) else
                                                       ("single" if not any("+" in x for x in c) else "mixed"))
            xmax = 1.08 * max(prof.k.max(), p[p.run.isin(runs)].k.max() if len(p) else 0)
            fig, axs = plt.subplots(3, 4, figsize=fp.figsize_single(aspect=1.12), sharex=True, sharey=True)
            for r, room in enumerate(ROOMS):
                n = prof[prof.room == room].run.nunique()
                for c, tp in enumerate(PROFILE_TIMES):
                    ax = axs[r, c]
                    pr = prof[(prof.room == room) & (prof.t_s == tp)]
                    for run, g in pr.groupby("run"):
                        g = g.sort_values("z_m")
                        st = scheme.style(names[run], kind[(run, room)])
                        ax.plot(g.k, g.z_m, ls=st["linestyle"], color=st["color"], lw=0.9, zorder=3)
                        pp = p[(p.run == run) & (p.room == room) & (p.t_s == tp)]
                        for _, q in pp.iterrows():
                            ax.plot(q.k, q.z_m, ls="none", color=st["color"], zorder=10 + (q.instrument == "SICK"),
                                    **inst_kw[q.instrument])
                    if r == 0:
                        ax.text(0.5, 1.03, fr"$t = {tp}$ s", transform=ax.transAxes, ha="center", va="bottom")
                    if c == 3:
                        ax.text(1.05, 0.5, f"{room} ($n = {n}$)", transform=ax.transAxes, rotation=-90,
                                ha="left", va="center")
                    ax.set_xlim(0, xmax)
                    ax.set_ylim(0, 2.535)
                    if r == 2:
                        ax.set_xlabel(r"$k$ / m$^{-1}$")
                    if c == 0:
                        ax.set_ylabel(r"$z$ / m")
            # Legende in festen Zeilen ueber den Achsen: Tests | Linienart (Quelle) | Messgeraete
            rows = [[Line2D([], [], color=scheme.style(names[r])["color"], lw=1.5,
                            label=names[r].rsplit("_", 1)[1]) for r in runs],
                    [Line2D([], [], color="0.3", ls=scheme.subgroup_linestyles[kd], lw=0.9,
                            label=scheme.subgroup_labels[kd]) for kd in ("stack", "single", "mixed")
                     if (kind == kd).any()],
                    [Line2D([], [], ls="none", color="0.45", label=ins, **inst_kw[ins])
                     for ins in inst_mk if (p.run.isin(runs) & (p.instrument == ins)).any()]]
            fig.tight_layout()
            row_h = 1.6 * fp.TEXT_FONT_SIZE_PT / 72 / fig.get_figheight()      # eine Legendenzeile, Bruchteil
            top = max(ax.get_position().y1 for ax in axs.flat) + 1.5 * row_h    # ueber den Spaltenkoepfen
            for i, hs in enumerate(reversed([r for r in rows if r])):
                fig.legend(handles=hs, loc="lower center", ncol=len(hs), frameon=False, borderaxespad=0.0,
                           bbox_to_anchor=(0.5, top + i * row_h), columnspacing=1.2, handlelength=1.8)
            out = PLOTS / f"ledsa_h1_profiles_{cfg}"
            fp.save_pdf(fig, out)
            fig.savefig(out.with_suffix(".png"), dpi=150)
            plt.close(fig)
            print(f"[ok] {out}.pdf/.png")


if __name__ == "__main__":
    if VARIANT:
        raise SystemExit(f"[--] H1_VARIANT={VARIANT} gesetzt: Hauptauswertung nur ohne Variante rechnen")
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("csv", "all"):
        build_csv()
    if what in ("plot", "all"):
        plot()
