# -*- coding: utf-8 -*-
r"""Abbildung Schliessungstest (out/la_closure.csv aus la_closure.py; Stil fireplot wie la_fig.py).
(a) LED 4, (b) LED 2: gemessene optische Dicke (x Widmann) gegen die Vorhersage aus den Raumprofilen, je LED mit
tau_pred >= 0,1, doppelt-logarithmisch; Farbe = Zeit, Marker = Serie; durchgezogen 1:1, gestrichelt +-30 %.
Aufruf: hh2-venv  la_closure_fig.py  -> out/la_closure.pdf/.png
"""
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

OUT = la.LA / "out"
COLS = {200: "C0", 400: "C1", 600: "C2", 800: "C3"}
MARK = {"Hep_160": "o", "Hep_220": "s"}
NAME = {"Hep_160": "Hep\\_160\\_075", "Hep_220": "Hep\\_220\\_300"}
ARR = {0: "LED 4 (F2, near)", 1: "LED 2 (F1, far)"}
TAU_MIN = 0.1


def main():
    d = pd.read_csv(OUT / "la_closure.csv", comment="#")
    d = d[d.tau_pred >= TAU_MIN]
    lim = (0.08, 10.0)
    with fp.paper_style(require_latex=True):
        fig, axs = plt.subplots(1, 2, figsize=fp.figsize_single(aspect=0.5), sharex=True, sharey=True)
        for a, ax in zip((0, 1), axs):
            g = d[d.array == a]
            for (ser, t), q in g.groupby([g.run.str[:7], "t_s"]):
                ax.scatter(q.tau_pred, q.tau_meas, s=3, marker=MARK[ser], color=COLS[t], alpha=0.5, lw=0,
                           rasterized=True)
            x = np.array(lim)
            ax.plot(x, x, "k-", lw=0.7)
            for f in (0.7, 1.3):
                ax.plot(x, f * x, "k--", lw=0.5)
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_xlim(lim)
            ax.set_ylim(lim)
            ax.set_aspect("equal")
            ax.text(0.04, 0.96, f"({'ab'[a]}) {ARR[a]}", transform=ax.transAxes, ha="left", va="top", fontsize=8)
            ax.set_xlabel(r"$\tau_\mathrm{rooms}$ / 1")
        axs[0].set_ylabel(r"$\tau_\mathrm{meas}$ / 1")
        h = [plt.Line2D([], [], color=COLS[t], marker="o", ls="", ms=4, label=f"{t} s") for t in COLS] + \
            [plt.Line2D([], [], color="0.4", marker=MARK[s], ls="", ms=4, label=NAME[s]) for s in MARK]
        fig.legend(handles=h, loc="upper center", ncol=6, bbox_to_anchor=(0.5, 1.02), frameon=False, fontsize=7,
                   handletextpad=0.2, columnspacing=0.8)
        fig.tight_layout(rect=(0, 0, 1, 0.92))
        fp.save_pdf(fig, OUT / "la_closure.pdf")
        fig.savefig(OUT / "la_closure.png", dpi=150)
        plt.close(fig)
    print(f"[ok] {OUT / 'la_closure.pdf'}")


if __name__ == "__main__":
    main()
