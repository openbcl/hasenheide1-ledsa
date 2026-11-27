# -*- coding: utf-8 -*-
r"""Abbildung FDS-Vergleich Langachse (Daten out/la_fds_profiles.csv aus la_fds.py; Stil fireplot wie la_fig.py).
Zeilen: Hep_160_075 N1 (4 Laeufe), Hep_220_300 N1 (3 Laeufe), Hep_160_075_R2 J4; Spalten LED 4 / LED 2;
Farben t = 100/200/300/600 s; Messung (Mittel +-10 s) duenn durchgezogen je Lauf, FDS (gleiche LEDs, gleiche Inversion)
gestrichelt, nur an Schichten mit Messwert; x-Achse je Zeile.
Aufruf: hh2-venv  la_fds_fig.py  -> out/la_fds_profiles.pdf/.png
"""
import sys
from pathlib import Path

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
COLS = {100: "C0", 200: "C1", 300: "C2", 600: "C3"}
ARR = {0: "LED 4 (F2, near)", 1: "LED 2 (F1, far)"}
NAME = {"Hep_220_S1": "Hep_220_300", "Hep_160_S2": "Hep_160_075", "Hep_160_S3": "Hep_160_075"}
ROWS = [("075", "N1", "Hep_160_075, N1 (4 tests)"), ("300", "N1", "Hep_220_300, N1 (3 tests)")]   # J4 gesperrt (la_post.EXCLUDED)


def main():
    d = pd.read_csv(OUT / "la_fds_profiles.csv", dtype={"fire": str})
    with fp.paper_style(require_latex=True):
        fig, axs = plt.subplots(len(ROWS), 2, figsize=(fp.figsize_single(aspect=1.0)[0], 1.9 * len(ROWS)),
                                sharex="row", sharey=True, squeeze=False)
        for i, (fire, cam, lab) in enumerate(ROWS):
            for a in (0, 1):
                ax = axs[i, a]
                g = d[(d.fire == fire) & (d.cam == cam) & (d.array == a)]
                for (run, t), q in g.groupby(["run", "t_s"]):
                    q = q.sort_values("z_m")
                    ax.plot(q.k_meas, q.z_m, "-", color=COLS[t], lw=0.6)
                    ax.plot(q.k_fds.where(q.k_meas.notna()), q.z_m, "--", color=COLS[t], lw=1.0)  # nur wo gemessen
                txt = f"{lab}\n{ARR[a]}"
                if g.k_meas.notna().sum() == 0:
                    txt += "\nno result (saturated)"
                ax.text(0.97, 0.05, txt, transform=ax.transAxes, ha="right", va="bottom", fontsize=7)
                if a == 0:
                    ax.set_ylabel(r"$z$ / m")
        for ax in axs.ravel():
            ax.set_xlabel(r"$k$ / m$^{-1}$")
        axs[0, 0].set_ylim(0, 2.535)
        for row in axs:
            row[0].set_xlim(left=0)
        h = [plt.Line2D([], [], color=COLS[t], lw=0.9, label=f"{t} s") for t in COLS] + \
            [plt.Line2D([], [], color="k", ls="-", lw=0.6, label="LEDSA 0.13.0 (measured)"),
             plt.Line2D([], [], color="k", ls="--", lw=1.0, label="FDS (same rays and inversion)")]
        fig.legend(handles=h, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.0), frameon=False, fontsize=7)
        fig.tight_layout(rect=(0, 0, 1, 0.95))
        fp.save_pdf(fig, OUT / "la_fds_profiles.pdf")
        fig.savefig(OUT / "la_fds_profiles.png", dpi=150)
        plt.close(fig)
    print(f"[ok] {OUT / 'la_fds_profiles.pdf'}; R2 nach {CAM_MOVED} gesperrt (bereits in la_k_1s)")


if __name__ == "__main__":
    main()
