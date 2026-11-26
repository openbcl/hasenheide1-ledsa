# -*- coding: utf-8 -*-
"""Diagnose der Bildverschiebung (Stufe 2, Untersuchung 2026-11-23: Ursache des Drifts, kehrt er zurueck, Lichtbrechung?).
  timeseries  : je Serie Lagecheck (inventory/ledsa_h1_drift.csv, Phasenkorrelation gegen das Referenzbild der
                LED-Suche) und, falls vorhanden, Nachfuehrung (analysis/tracking_log.csv), laengs (Zeile) und quer
                (Spalte); senkrechte Linien Feuer aus / Lueftung (setup/ledsa_h1_runs.csv).
  height <Lauf>:<Kamera> : Verschiebung laengs je LED (tracked_positions.csv.gz minus Position im Referenzbild der
                LED-Suche) ueber Zeit und Hoehe z (led_search_areas_with_coordinates.csv), Mittel der drei Streifen
                je 10-cm-Klasse; dazu LEM-Extinktion im Raum als Rauchanzeiger.
  Mechanische Bewegung: gleiche Verschiebung aller Hoehen; Brechung an einer Temperaturschichtung: hoehenabhaengig.
Aufruf (hh2-venv, im Ordner 2_Analysis/LEDSA): python tools/plot_drift.py timeseries <out.png> <Lauf>:<Kamera> ...
                                               python tools/plot_drift.py height <out.png> <Lauf>:<Kamera>
"""
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

L = Path(__file__).resolve().parents[1]
REPO = L.parents[1]
PSR_MIN, ALIAS_MAX = 15.0, 12.0
S = pd.read_csv(L / "setup" / "ledsa_h1_series.csv", comment="#")
RUNS = pd.read_csv(L / "setup" / "ledsa_h1_runs.csv", comment="#").set_index("run")
DRIFT = pd.read_csv(L / "inventory" / "ledsa_h1_drift.csv")
plt.rcParams.update({"font.size": 10, "axes.labelsize": 10, "legend.fontsize": 8})


def series(rc):
    run, cam = rc.split(":")
    r = S[(S.run == run) & (S.cam == cam)].iloc[0]
    return run, cam, r, L / "runs" / run / f"{r.position}_{cam}" / "analysis"


def baseline(pos, log, r, half=30.0):
    """Bezug je LED = mittlere nachgefuehrte Position um das Referenzbild der LED-Suche (+-half s). Nicht die
    s1-Positionen: Nachfuehrung (Maximum im geglaetteten Bild) und LED-Suche definieren die LED-Mitte verschieden,
    das gab ein zeitlich festes Muster von einigen 0,1 px (2026-11-23)."""
    t_ref = float(r.ref_s1_t_s)
    ids = log.img_id[(log.t_exp - t_ref).abs() <= half]
    if ids.empty:
        ids = log.img_id[[int((log.t_exp - t_ref).abs().idxmin())]]
    b = pos[pos.img_id.isin(ids)].groupby("led_id")[["row", "col"]].mean().rename(columns={"row": "row0", "col": "col0"})
    return pos.merge(b, left_on="led_id", right_index=True)


def events(ax, run):
    for col, ls in (("fire_out_s", ":"), ("ventilation_s", "--")):
        ax.axvline(RUNS.loc[run, col], color="0.4", ls=ls, lw=0.8)


def timeseries(out, rcs):
    fig, axs = plt.subplots(len(rcs), 1, figsize=(6.3, 1.55 * len(rcs)), sharex=True, squeeze=False)
    for ax, rc in zip(axs[:, 0], rcs):
        run, cam, r, w = series(rc)
        ref = r.name_string.format(int(r.ref_s1_id))
        d = DRIFT[(DRIFT.run == run) & (DRIFT.cam == cam) & (DRIFT.ref == ref)]
        if (d.dy_px.abs().max() if len(d) else 0) < 100 and (d.dx_px.abs().max() if len(d) else 0) < 100:
            d = d[(d.dy_px.abs() < ALIAS_MAX) & (d.dx_px.abs() < ALIAS_MAX)]   # Alias-Filter nur ohne echten Schwenk
        else:
            ax.text(0.99, 0.92, "unfiltered (real pan)", transform=ax.transAxes, ha="right", va="top", fontsize=8)
        for col, c in (("dy_px", "C0"), ("dx_px", "C1")):
            good = d.psr >= PSR_MIN
            ax.plot(d.t_rel_s[good], d[col][good], "o", ms=3.5, color=c)
            ax.plot(d.t_rel_s[~good], d[col][~good], "o", ms=3.5, mfc="none", color=c)
        tl = w / "tracking_log.csv"
        if tl.exists():
            t = pd.read_csv(tl).sort_values("t_exp")
            ax.plot(t.t_exp, t.shift_row, "-", lw=0.9, color="C0")
            ax.plot(t.t_exp, t.shift_col, "-", lw=0.9, color="C1")
        events(ax, run)
        ax.axhline(0, color="0.8", lw=0.6)
        ax.set_ylabel("shift (px)")
        ax.text(0.01, 0.92, f"{run} {cam}{'' if tl.exists() else ' (survey only)'}", transform=ax.transAxes,
                va="top", fontsize=8)
    axs[-1, 0].set_xlabel("time after ignition (s)")
    axs[0, 0].plot([], [], "o", ms=3.5, color="C0", label="along strip, survey")
    axs[0, 0].plot([], [], "o", ms=3.5, color="C1", label="across strip, survey")
    axs[0, 0].plot([], [], "-", color="0.3", label="tracking")
    axs[0, 0].plot([], [], "o", ms=3.5, mfc="none", color="0.3", label=f"survey PSR < {PSR_MIN:.0f}")
    axs[0, 0].legend(loc="upper right", ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"[ok] {out}")


def height(out, rc):
    run, cam, r, w = series(rc)
    pos = pd.read_csv(w / "tracked_positions.csv.gz")
    log = pd.read_csv(w / "tracking_log.csv")
    co = pd.read_csv(w / "led_search_areas_with_coordinates.csv", comment="#", header=None,
                     names=["led_id", "px", "py", "x", "y", "z", "wd", "ht"])
    p = baseline(pos, log, r).merge(co[["led_id", "z"]], on="led_id").merge(log[["img_id", "t_exp"]], on="img_id")
    p["drow"] = p.row - p.row0
    p["zb"] = (p.z / 0.1).round() * 0.1
    g = p.groupby(["t_exp", "zb"]).drow.mean().unstack("zb")
    f = REPO / "1_Measurements" / run / "1_Processed_data" / f"{run}_processed.csv"
    meas = pd.read_csv(f, comment="#", encoding="utf-8-sig")
    room = r.room
    lem = [c for c in meas.columns if re.match(rf"Extinction LEM_\d+_{room}_[\d.]+ \(1/m\)$", c)]
    fig, (a0, a1) = plt.subplots(2, 1, figsize=(6.3, 5.2), sharex=True, gridspec_kw={"height_ratios": [1, 2.2]})
    for c in lem:
        a0.plot(meas["Time (s)"], meas[c], lw=0.9, label=c.replace("Extinction ", "").replace(" (1/m)", ""))
    a0.set_ylabel("extinction (1/m)")
    a0.legend(frameon=False, loc="upper right")
    events(a0, run)
    lim = max(2.0, float(np.nanpercentile(np.abs(g.to_numpy()), 99)))
    m = a1.pcolormesh(g.index, g.columns, g.T.to_numpy(), cmap="RdBu_r", vmin=-lim, vmax=lim, shading="nearest")
    events(a1, run)
    a1.set_ylabel("LED height z (m)")
    a1.set_xlabel("time after ignition (s)")
    fig.colorbar(m, ax=a1, label="shift along strip (px)", pad=0.01)
    a1.text(0.01, 0.97, f"{run} {cam}, mean of 3 strips per 0.1 m", transform=a1.transAxes, va="top", fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"[ok] {out}")
    # Kennzahlen: Spannweite ueber die Hoehe zu ausgewaehlten Zeiten
    for t in (0, 300, 600, 900, 1200, 1500):
        k = int(np.argmin(np.abs(g.index.to_numpy() - t)))
        row = g.iloc[k]
        print(f"t {g.index[k]:6.0f} s: Verschiebung laengs unten (z<0.6) {row[row.index < 0.6].mean():+.2f}, "
              f"mitte {row[(row.index >= 0.6) & (row.index < 1.8)].mean():+.2f}, oben (z>=1.8) "
              f"{row[row.index >= 1.8].mean():+.2f} px")


def profile(out, rc, times=(300, 600, 900, 1200, 1500), half=30.0):
    """Verschiebung laengs und quer ueber z zu festen Zeiten (Mittel +-half s, je LED, dann 0,1-m-Klassen), Gerade
    a + b z je Zeit. Deutung: Massstab (Brennweite/Fokus) -> laengs linear in z; Drehung um die optische Achse -> quer
    linear in z; Brechung an einer Temperaturschichtung -> laengs nicht linear, auf die heisse Schicht beschraenkt."""
    run, cam, r, w = series(rc)
    pos = pd.read_csv(w / "tracked_positions.csv.gz")
    log = pd.read_csv(w / "tracking_log.csv")
    co = pd.read_csv(w / "led_search_areas_with_coordinates.csv", comment="#", header=None,
                     names=["led_id", "px", "py", "x", "y", "z", "wd", "ht"])
    p = baseline(pos, log, r).merge(co[["led_id", "z"]], on="led_id").merge(log[["img_id", "t_exp"]], on="img_id")
    p["drow"], p["dcol"] = p.row - p.row0, p.col - p.col0
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(6.3, 3.6), sharey=True)
    cmap = plt.get_cmap("viridis")
    print(f"{run} {cam}: Gerade a + b z je Zeit (b in px/m), Rest = Mittel(Messung - Gerade) in z >= 2,2 m bzw. RMS")
    for k, t in enumerate(times):
        q = p[(p.t_exp - t).abs() <= half]
        if q.empty:
            continue
        led = q.groupby("led_id").agg(z=("z", "first"), drow=("drow", "mean"), dcol=("dcol", "mean"))
        led["zb"] = (led.z / 0.1).round() * 0.1
        prof = led.groupby("zb")[["drow", "dcol"]].mean()
        c = cmap(k / max(len(times) - 1, 1))
        res = []
        for ax, col in ((a0, "drow"), (a1, "dcol")):
            b, a = np.polyfit(prof.index, prof[col], 1)
            ax.plot(prof[col], prof.index, "o", ms=3, color=c, label=f"{t:.0f} s" if col == "drow" else None)
            zz = np.array([prof.index.min(), prof.index.max()])
            ax.plot(a + b * zz, zz, "-", lw=0.8, color=c)
            rest = prof[col] - (a + b * prof.index)
            res.append((a, b, float(rest[prof.index >= 2.2].mean()), float(np.sqrt((rest ** 2).mean()))))
        print(f"  t {t:5.0f} s: laengs a {res[0][0]:+.2f} b {res[0][1]:+.2f} Rest oben {res[0][2]:+.2f} RMS "
              f"{res[0][3]:.2f}; quer a {res[1][0]:+.2f} b {res[1][1]:+.2f} Rest oben {res[1][2]:+.2f} RMS {res[1][3]:.2f}")
    a0.set_xlabel("shift along strip (px)")
    a1.set_xlabel("shift across strip (px)")
    a0.set_ylabel("LED height z (m)")
    a0.legend(frameon=False, fontsize=8, loc="best")
    a0.text(0.02, 0.02, f"{run} {cam}", transform=a0.transAxes, fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"[ok] {out}")


if __name__ == "__main__":
    if sys.argv[1] == "timeseries":
        timeseries(sys.argv[2], sys.argv[3:])
    elif sys.argv[1] == "profile":
        profile(sys.argv[2], sys.argv[3])
    else:
        height(sys.argv[2], sys.argv[3])
