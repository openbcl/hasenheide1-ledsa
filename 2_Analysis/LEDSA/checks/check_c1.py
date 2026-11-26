"""Pruefung C1 Hep_160_S2_R1 F2 (festgelegt 2026-11-24): taugen C1-Bilder ab +30 s als Referenz?
(a) J2 (gueltige Referenz vor der Zuendung) im selben Raum: I/I_ref je LED-Hoehe bei 25-50 s -> ist auf den
    Sichtlinien schon Rauch?  (b) C1 frueh (30-45 s) gegen spaet (letzte 60 s) je Hoehe.  (c) Zeitverlauf oben/unten.
farbg_sum_col_value (Spalte 5), Kanaele 0-2. Nur lesen, Ausgabe auf stdout + PNG nach <out> (zweites Argument)."""
import configparser, sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

RUN = Path(sys.argv[1]); OUT = Path(sys.argv[2])


def load(work, ch):
    info = pd.read_csv(work / "analysis" / "image_infos_analysis.csv")
    t = dict(zip(info.iloc[:, 0], info.iloc[:, 3]))
    rows = {}
    for f in (work / "analysis" / f"channel{ch}").glob("*_led_positions.csv"):
        i = int(f.name.split("_")[0])
        d = pd.read_csv(f, comment="#", header=None, skipinitialspace=True)
        rows[t[i]] = d.set_index(0)[5]
    return pd.DataFrame(rows).sort_index(axis=1)          # LED x Zeit


def z_of(work):
    c = pd.read_csv(work / "analysis" / "led_search_areas_with_coordinates.csv", comment="#", header=None)
    return c.set_index(0)[5]


def bands(z, edges=np.linspace(0, 2.535, 6)):
    return pd.cut(z, edges, include_lowest=True)


j2, c1 = RUN / "F2U_J2", RUN / "F2L_C1"
cfg = configparser.ConfigParser(); cfg.read(j2 / "config_analysis.ini")
refs = [int(x) for x in cfg["DEFAULT"]["ref_img_indices"].split()] if "ref_img_indices" in cfg["DEFAULT"] else None
info = pd.read_csv(j2 / "analysis" / "image_infos_analysis.csv"); tj = dict(zip(info.iloc[:, 0], info.iloc[:, 3]))
t_ref = [tj[i] for i in refs]
print(f"J2 Referenzbilder {refs} ({min(t_ref):.0f}..{max(t_ref):.0f} s)")
fig, ax = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
for ch in (0, 1, 2):
    J = load(j2, ch); C = load(c1, ch)
    zj, zc = z_of(j2).reindex(J.index), z_of(c1).reindex(C.index)
    rj = J.div(J[t_ref].mean(axis=1), axis=0)
    early = [t for t in C.columns if 30 <= t <= 45]
    late = [t for t in C.columns if t >= C.columns.max() - 60]
    rc = C[early].mean(axis=1) / C[late].mean(axis=1)
    win = [t for t in rj.columns if 25 <= t <= 50]
    print(f"\nKanal {ch}: J2 Bilder {len(win)} in 25-50 s; C1 frueh {len(early)} ({early}), spaet {len(late)} "
          f"({min(late):.0f}..{max(late):.0f} s)")
    tab = pd.DataFrame({"J2 I/Iref 25-50 s (Median)": rj[win].median(axis=1).groupby(bands(zj), observed=True).median(),
                        "J2 min": rj[win].min(axis=1).groupby(bands(zj), observed=True).median(),
                        "C1 frueh/spaet (Median)": rc.groupby(bands(zc), observed=True).median(),
                        "C1 p10": rc.groupby(bands(zc), observed=True).quantile(0.1),
                        "C1 p90": rc.groupby(bands(zc), observed=True).quantile(0.9)})
    print(tab.round(3).to_string())
    for lo, hi, ls in ((1.6, 2.6, "-"), (0, 0.9, "--")):
        sj = rj[(zj >= lo) & (zj < hi)].median()
        sc = C[(zc >= lo) & (zc < hi)].div(C[late][(zc >= lo) & (zc < hi)].mean(axis=1), axis=0).median()
        m = (sj.index > -120) & (sj.index < 200)
        ax[ch].plot(sj.index[m], sj[m], ls, color="C0", label=f"J2 / ref, z {lo}-{hi} m")
        m = sc.index < 200
        ax[ch].plot(sc.index[m], sc[m], ls, color="C3", label=f"C1 / late, z {lo}-{hi} m")
    ax[ch].axvline(48, color="grey", lw=0.8); ax[ch].set_xlabel("Time (s)"); ax[ch].set_title(f"channel {ch}")
ax[0].set_ylabel("Relative intensity (-)"); ax[0].legend(fontsize=7)
fig.tight_layout(); fig.savefig(OUT, dpi=110)
print(f"\nPNG {OUT}")
