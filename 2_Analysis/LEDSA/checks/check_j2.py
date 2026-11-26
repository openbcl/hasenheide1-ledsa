"""Drei Pruefungen J2 Hep_220_S1_R1: (1) Helligkeit vor der Zuendung, (2) Sprung +900...+1500 s,
(3) F2 C3+J2 / nur C3 / nur J2 gegen LEM (Paper-Methode, Masken, LEM und LEDSA gleich gefiltert). Nur lesen.
Aufruf: hh2-venv check_j2.py <LEDSA-Ordner> <png-Praefix>"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

HERE = Path(sys.argv[1]); PNG = sys.argv[2]
sys.path.insert(0, str(HERE))
import ledsa_h1_stage0 as s0
from ledsa_h1_config import RUNS

RUN, ROOM = "Hep_220_S1_R1", "F2"
R = RUNS / RUN


def per_image(work, ch, refs):
    info = pd.read_csv(work / "analysis" / "image_infos_analysis.csv")
    t = dict(zip(info.iloc[:, 0], info.iloc[:, 3]))
    rows = {}
    for f in (work / "analysis" / f"channel{ch}").glob("*_led_positions.csv"):
        i = int(f.name.split("_")[0])
        rows[i] = pd.read_csv(f, comment="#", header=None, skipinitialspace=True).set_index(0)[5]
    s = pd.DataFrame(rows).sort_index(axis=1)
    z = pd.read_csv(work / "analysis" / "led_search_areas_with_coordinates.csv", comment="#", header=None).set_index(0)[5]
    r = s.div(s[refs].mean(axis=1), axis=0)
    return pd.DataFrame({"t": [t[i] for i in r.columns], "med": r.median().values,
                         "oben": r[z.reindex(r.index) >= 1.6].median().values,
                         "unten": r[z.reindex(r.index) < 0.9].median().values,
                         "aus20": ((r - 1).abs() > 0.2).mean().values}).sort_values("t")


def refs_of(work):
    import configparser
    c = configparser.ConfigParser(); c.read(work / "config_analysis.ini")
    return [int(x) for x in c["DEFAULT"]["ref_img_indices"].split()]


# (1) + (2)
fig, ax = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
for cam, col in (("F2U_J2", "C0"), ("F2L_C3", "C3")):
    w = R / cam
    d = per_image(w, 1, refs_of(w))       # Kanal 1 (gruen) als Beispiel; Kanal 0/2 unten in Zahlen
    pre = d[d.t < 0]
    print(f"(1) {cam} Kanal 1 vor der Zuendung ({len(pre)} Bilder, {pre.t.min():.0f}..{pre.t.max():.0f} s): Median rel. "
          f"{pre.med.min():.3f}..{pre.med.max():.3f}, Anteil LEDs >20 % daneben max {pre.aus20.max():.3f}; "
          f"Bilder ausserhalb +-2 %: {int(((pre.med - 1).abs() > 0.02).sum())}")
    for ch in (0, 2):
        dd = per_image(w, ch, refs_of(w)); pp = dd[dd.t < 0]
        print(f"    Kanal {ch}: Median rel. {pp.med.min():.3f}..{pp.med.max():.3f}, ausserhalb +-2 %: "
              f"{int(((pp.med - 1).abs() > 0.02).sum())}")
    ax[0].plot(d.t, d.oben, color=col, label=f"{cam[-2:]} upper LEDs (z >= 1.6 m)")
    ax[0].plot(d.t, d.unten, "--", color=col, label=f"{cam[-2:]} lower LEDs (z < 0.9 m)")
ax[0].set_ylabel("Relative intensity, green (-)"); ax[0].legend(fontsize=8)
for x in (900, 1500):
    for a in ax:
        a.axvline(x, color="grey", lw=0.8)

# (3)
L = s0.lem(RUN, ROOM); H = sorted(L); tv = s0.vent(RUN)
mask = pd.read_csv(R / "plots_h1" / f"mask_{ROOM}.csv.gz"); mask = mask[mask.snr == 3.0]
src = {"C3+J2 stacked": (R / f"stacked_{ROOM}", "stacked_F2"), "C3 only": (R / "F2L_C3", "C3"),
       "J2 only": (R / "F2U_J2", "J2")}
tg = s0.grid()
rows = []
ser = {}
for lab, (base, q) in src.items():
    kd = base / "analysis" / "extinction_coefficients" / "linear" / "farbg_sum_col_val"
    ser[lab] = s0.room_series(kd, "farbg_sum_col_val", H, mask[mask.quelle == q])
for h in H:
    ml = s0.metrics(L[h], tv)
    rows.append(dict(z_m=h, source="LEM", peak=ml["peak"], t_peak=ml["t_peak"], plateau=ml["plateau"]))
    for lab in src:
        m = s0.metrics(ser[lab][h], tv)
        late = (tg >= 900) & (tg <= 1500)
        rows.append(dict(z_m=h, source=lab, peak=m["peak"], t_peak=m["t_peak"], plateau=m["plateau"],
                         peak_LEM=m["peak"] / ml["peak"], plateau_LEM=m["plateau"] / ml["plateau"]))
out = pd.DataFrame(rows)
print(f"\n(3) {RUN} {ROOM}, Lueftung {tv:.0f} s, Plateau {tv - 300:.0f}-{tv - 20:.0f} s, farbg, Maske SNR 3, +-10 s")
print(out.round(3).to_string(index=False))
# Sprung: J2 minus C3 an 2.3 m (bzw. hoechster LEM-Hoehe) ueber die Zeit
h = max(H)
dif = s0.smooth(ser["J2 only"][h]) - s0.smooth(ser["C3 only"][h])
for a, b in ((300, 600), (600, 900), (900, 1200), (1200, 1500), (1500, 1700)):
    m = (tg >= a) & (tg < b)
    print(f"(2) J2 - C3 bei {h} m, {a}-{b} s: Mittel {np.nanmean(dif[m]):+.3f} 1/m, Spanne {np.nanmin(dif[m]):+.3f}..{np.nanmax(dif[m]):+.3f}")
for lab, col in zip(src, ("k", "C3", "C0")):
    ax[1].plot(tg, s0.smooth(ser[lab][h]), color=col, lw=1, label=lab)
ax[1].plot(tg, s0.smooth(L[h]), color="grey", lw=1.5, label="LEM")
ax[1].set_ylabel(f"Extinction coefficient at {h} m (1/m)"); ax[1].set_xlabel("Time (s)"); ax[1].legend(fontsize=8)
fig.tight_layout(); fig.savefig(PNG + ".png", dpi=110); print(PNG + ".png")
