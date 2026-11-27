# -*- coding: utf-8 -*-
r"""Abbildungen der Langachsen-Auswertung (Stil fireplot wie die Raumauswertung; Daten ../out aus la_post.py).
  la_profiles.pdf/.png  je N1-Lauf (Zeilen) und Streifen (Spalten LED 4 nah / LED 2 fern): k(z) zu 120/240/360 s
                        (Mittel +-10 s), durchgezogen; fruehere 0.9.8-Auswertung gestrichelt, nur wenn in
                        la_profiles.csv vorhanden (optional, la_post.py)
  la_timeseries.pdf/.png je Lauf: k(t) an z ~ 2,3 / 1,5 / 0,5 m, LED 4 und LED 2
Aufruf: hh2-venv  la_fig.py"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
import la  # noqa: E402
sys.path.insert(0, str(la.REPO_LEDSA))
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import fireplot as fp  # noqa: E402
from la_post import CAM_MOVED  # noqa: E402

OUT = la.LA / "out"
TIMES = [120, 240, 360]
COLS = {120: "C0", 240: "C1", 360: "C2"}
ZS = [2.3, 1.5, 0.5]
ARR = {0: "LED 4 (F2, near)", 1: "LED 2 (F1, far)"}


def main():
    p = pd.read_csv(OUT / "la_profiles.csv")
    k = pd.read_csv(OUT / "la_k_1s.csv.gz")
    keys = sorted({(r.run, r.cam) for r in p.itertuples()}, key=lambda x: (x[1] == "J4", x[0]))
    with fp.paper_style(require_latex=True):
        fig, axs = plt.subplots(len(keys), 2, figsize=(fp.figsize_single(aspect=1.0)[0], 1.45 * len(keys)),
                                sharex=True, sharey=True, squeeze=False)
        for i, (run, cam) in enumerate(keys):
            for a in (0, 1):
                ax = axs[i, a]
                for t in TIMES:
                    for src, ls in (("neu", "-"), ("prior098", "--")):
                        g = p[(p.run == run) & (p.cam == cam) & (p.array == a) & (p.t_s == t) & (p.src == src)]
                        if len(g):
                            ax.plot(g.k, g.z_m, ls=ls, color=COLS[t], lw=0.9 if src == "neu" else 0.8)
                ax.text(0.97, 0.05, f"{run} {cam}\n{ARR[a]}", transform=ax.transAxes, ha="right", va="bottom", fontsize=7)
                if (run, cam) in CAM_MOVED:
                    ax.text(0.97, 0.30, f"camera moved:\nexcluded after {CAM_MOVED[(run, cam)]:g} s",
                            transform=ax.transAxes, ha="right", va="bottom", fontsize=6.5)
                if a == 0:
                    ax.set_ylabel(r"$z$ / m")
        for ax in axs[-1]:
            ax.set_xlabel(r"$k$ / m$^{-1}$")
        axs[0, 0].set_ylim(0, 2.535)
        axs[0, 0].set_xlim(left=0)
        h = [plt.Line2D([], [], color=COLS[t], lw=0.9, label=f"{t} s") for t in TIMES] + \
            [plt.Line2D([], [], color="k", ls="-", lw=0.9, label="LEDSA 0.13.0 (this evaluation)")]
        if (p.src == "prior098").any():
            h.append(plt.Line2D([], [], color="k", ls="--", lw=0.8, label="LEDSA 0.9.8 (earlier evaluation)"))
        fig.legend(handles=h, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.0), frameon=False, fontsize=7)
        fig.tight_layout(rect=(0, 0, 1, 0.97))
        fp.save_pdf(fig, OUT / "la_profiles.pdf")
        fig.savefig(OUT / "la_profiles.png", dpi=150)
        plt.close(fig)

        fig, axs = plt.subplots(len(keys), 2, figsize=(fp.figsize_single(aspect=1.0)[0], 1.45 * len(keys)),
                                sharex=True, sharey=True, squeeze=False)
        for i, (run, cam) in enumerate(keys):
            for a in (0, 1):
                ax = axs[i, a]
                g = k[(k.run == run) & (k.cam == cam) & (k.array == a)]
                if g.empty:
                    ax.text(0.5, 0.5, "no result (saturated)", transform=ax.transAxes, ha="center", va="center", fontsize=7)
                    continue
                # feste Schichtmitten (alle Schichten aus la_profiles.csv), volles 1-s-Raster mit Luecken (gesperrt = NaN)
                zc = np.sort(p[(p.run == run) & (p.cam == cam) & (p.array == a)].z_m.unique())
                tg = np.arange(-30, 1701, dtype=float)
                for z, c in zip(ZS, ("C3", "C4", "C5")):
                    zz = zc[np.argmin(np.abs(zc - z))]
                    q = g[np.isclose(g.z_m, zz)].set_index("t_s").k.reindex(tg)
                    ax.plot(tg, q.to_numpy(), color=c, lw=0.7)
                ax.text(0.97, 0.92, f"{run} {cam}, {ARR[a]}", transform=ax.transAxes, ha="right", va="top", fontsize=7)
                if (run, cam) in CAM_MOVED:
                    ax.text(0.97, 0.70, f"camera moved: excluded after {CAM_MOVED[(run, cam)]:g} s",
                            transform=ax.transAxes, ha="right", va="top", fontsize=6.5)
                if a == 0:
                    ax.set_ylabel(r"$k$ / m$^{-1}$")
        for ax in axs[-1]:
            ax.set_xlabel(r"$t$ / s")
        axs[0, 0].set_xlim(-30, 900)
        axs[0, 0].set_ylim(bottom=0)
        h = [plt.Line2D([], [], color=c, lw=0.9, label=f"$z \\approx {z}$ m") for z, c in zip(ZS, ("C3", "C4", "C5"))]
        fig.legend(handles=h, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.0), frameon=False, fontsize=7)
        fig.tight_layout(rect=(0, 0, 1, 0.97))
        fp.save_pdf(fig, OUT / "la_timeseries.pdf")
        fig.savefig(OUT / "la_timeseries.png", dpi=150)
        plt.close(fig)
    print(f"[ok] {OUT / 'la_profiles.pdf'}, {OUT / 'la_timeseries.pdf'}")


if __name__ == "__main__":
    main()
