"""Beleg fuer den Ausschluss von C3 in Hep_220_S1_R3 F2 (festgelegt 2026-11-25; ledsa_h1_config.CAM_EXCLUDE, METHODS.md section 4.6).
Nur lesen, unabhaengig von CAM_EXCLUDE (liest die Inversionen von C3, J2 und Stapel direkt). Log:
runs/_logs/c3_r3_exclusion.log. Vergleich mit R1/R2 (gleiche Konfiguration Hep_220_300, gleiche Kameras). Kanaele: alle
freien (Saettigung <= 5 %, wie die Pipeline; hier 0-2 in allen drei Laeufen).
  A  Zeitverlauf: Median ueber die Schichten 3-22 je Kamera (Paper-Methode wie Profile, +-10 s) und Differenz C3 - J2;
     zusaetzlich C3 - J2 je Schicht (3-22) bei 400/600/800 s
  B  Rohsignal je Bild, nur LEDs des eigenen Streifens (Array = Kanal, wie die Referenzregel): Median ueber die LEDs von
     farbg/ref, (max/sum)/(max/sum)_ref (Fleckform), Fernfeld-Sockel/ref; ref = Mittel der Bilder mit -60 <= t <= -5 s;
     dazu Verhaeltnis R3/R1 und R3/R2 von farbg/ref je Hoehenband (5 Baender) im Mittel +-10 s
  C  Profile je Quelle (C3, J2, Stapel) bei 400/600/800 s
  D  Stufe-4-Kennzahlen (wie ledsa_h1_stage4.lem) fuer C3, J2 und Stapel an den LEM-Hoehen
  E  Nachfuehrung C3 R3 (tracking_log): Verschiebung und Anteil verfeinerter LEDs; LED-Abstand im Bild
  F  Screening aller Zwei-Kamera-Raeume (auch ausgeschlossene Kameras): untere - obere Einzelkamera, Median ueber Zeit
     [300 s, Lueftung - 20 s] je Schicht 3-22, dann Median/Spanne ueber die Schichten -> ist R3 C3 ein Einzelfall?
  G  Belichtung C3 R1-R3 aus EXIF (inventory/h1_exif_weitergabe.csv.gz)
Wiederholbarkeit: braucht in runs/Hep_220_S1_R3/plots_h1/mask_F2.csv.gz die Zeilen fuer C3 und stacked_F2 (Maske vom
2026-11-24). Ein erneutes `ledsa_h1_mask.py flag` mit dem aktuellen CAM_EXCLUDE schriebe nur noch J2.
Aufruf: hh2-venv checks/c3_r3_exclusion.py <LEDSA-Ordner>
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(sys.argv[1])
sys.path.insert(0, str(HERE))
import ledsa_h1_config as C                                      # noqa: E402
import ledsa_h1_stage0 as s0                                     # noqa: E402
import ledsa_h1_profiles as P                                    # noqa: E402
import ledsa_h1_stage4 as S4                                     # noqa: E402
from ledsa_h1_config import RUNS, saturated, series              # noqa: E402

warnings.filterwarnings("ignore", category=RuntimeWarning)   # leere Schichten (alles maskiert) -> NaN, gewollt
pd.set_option("display.width", 230)
pd.set_option("display.max_rows", 300)
RUNS3 = ["Hep_220_S1_R1", "Hep_220_S1_R2", "Hep_220_S1_R3"]
SRC = {"C3": "F2L_C3", "J2": "F2U_J2", "stacked_F2": "stacked_F2"}
CAMS = {"C3": ["C3"], "J2": ["J2"], "stacked_F2": ["C3", "J2"]}
tg = s0.grid()
sat = saturated()
free = lambda run, cams, a: all((run, c, a) not in sat for c in cams)


def kfile(base, a, prop="farbg_sum_col_val"):
    return base / f"analysis/extinction_coefficients/linear/{prop}" / \
        f"extinction_coefficients_linear_channel_{a}_{prop}_led_array_{a}.csv"


def layers(run, room, quelle, base, a, prop="farbg_sum_col_val"):
    """[Schicht] -> 1-s-Reihe (Paper-Methode, robuste Nullung), Maske SNR 3 der Quelle."""
    m = s0.mask_for(run, room, quelle)
    if m.empty:
        raise SystemExit(f"[--] {run} {room}: Maske ohne Zeilen fuer {quelle}")
    t, k, cen = s0.load_k(kfile(base, a, prop))
    k = s0.apply_mask(t, k, m[m.led_array == a], f"{run} {room} {quelle} {a}")
    return [P.paper_series(t, k[:, j], a, "", P.BASE_WIN_S) for j in range(len(cen))], cen


def src_layers(run, src):
    """Mittel der freien Kanaele: Schichten x Zeit, Schichtmitten, Kanaele."""
    chs = [a for a in range(3) if free(run, CAMS[src], a)]
    per = [layers(run, "F2", src, RUNS / run / SRC[src], a) for a in chs]
    return np.nanmean(np.stack([np.vstack(p[0]) for p in per]), axis=0), per[0][1], chs


L3 = {(run, src): src_layers(run, src) for run in RUNS3 for src in SRC}
print("Kanaele je Quelle: " + "; ".join(f"{r[-2:]} {s} ch{''.join(map(str, v[2]))}" for (r, s), v in L3.items()))

print("\n======== A Zeitverlauf, Median Schichten 3-22 [1/m]")
A = {}
for run in RUNS3:
    for src in ("C3", "J2"):
        A[f"{run[-2:]}_{src}"] = s0.smooth(np.nanmedian(L3[(run, src)][0][3:23], axis=0))
a = pd.DataFrame(A, index=tg)
for r in ("R1", "R2", "R3"):
    a[f"{r}_C3-J2"] = a[f"{r}_C3"] - a[f"{r}_J2"]
print(a.loc[[t for t in range(0, 1701, 50) if t in a.index]].round(2).to_string())
w = (a.index >= 400) & (a.index <= 1200)
print("C3 - J2 (Median Schichten 3-22) in 400-1200 s (min/max): " + "; ".join(
    f"{r} {a.loc[w, f'{r}_C3-J2'].min():+.2f}/{a.loc[w, f'{r}_C3-J2'].max():+.2f}" for r in ("R1", "R2", "R3")))
print("Lueftung: " + ", ".join(f"{r[-2:]} {s0.vent(r):.0f} s" for r in RUNS3))
print("C3 - J2 je Schicht 3-22 (+-10 s) bei 400/600/800 s, Spanne ueber die Schichten:")
for run in RUNS3:
    lc, lj = L3[(run, "C3")][0], L3[(run, "J2")][0]
    print(f"  {run}: " + "; ".join(
        f"{tp} s {min(P.window_mean(lc[j] - lj[j], tg, tp) for j in range(3, 23)):+.2f}..."
        f"{max(P.window_mean(lc[j] - lj[j], tg, tp) for j in range(3, 23)):+.2f}" for tp in (400, 600, 800)))

# Abschnitte B und H brauchen die Auslese je Bild (analysis/channel*/), die nicht im Repo liegt (.gitignore);
# ohne sie werden B und H uebersprungen, A und C-G laufen aus den committeten Daten.
READOUT = (RUNS / RUNS3[0] / SRC["C3"] / "analysis" / "channel0").is_dir()
TIMES = [-30, 100, 200, 250, 300, 350, 400, 500, 600, 800, 1000, 1200, 1300, 1400, 1500, 1650]


def led(d, iid):
    return pd.read_csv(d / f"{iid}_led_positions.csv", comment="#", header=None, skipinitialspace=True,
                       names=["id", "line", "sum", "avg", "max", "farbg", "ped"]).set_index("id")


if not READOUT:
    print("\n======== B uebersprungen: Auslese je Bild (analysis/channel*/) fehlt")
else:
    print("\n======== B Rohsignal, nur LEDs des eigenen Streifens (Median ueber LEDs)")
    B, BAND = [], []
    for run in RUNS3:
        for src in ("C3", "J2"):
            an = RUNS / run / SRC[src] / "analysis"
            info = pd.read_csv(an / "image_infos_analysis.csv")
            info.columns = [c.strip("#") for c in info.columns]
            t, ids = info["Experiment_Time[s]"].to_numpy(float), info["ID"].to_numpy(int)
            coord = np.loadtxt(an / "led_search_areas_with_coordinates.csv", delimiter=",", ndmin=2)
            zled = pd.Series(coord[:, 5], index=coord[:, 0].astype(int))
            for ch in range(3):
                own = np.loadtxt(an / f"led_array_indices_{ch:03d}.csv", dtype=int, ndmin=1)
                d = an / f"channel{ch}"
                R = pd.concat([led(d, i) for i in ids[(t >= -60) & (t <= -5)]]).groupby(level=0).mean(numeric_only=True)
                R = R.loc[R.index.isin(own)]
                for tp in TIMES:
                    x = led(d, ids[int(np.argmin(np.abs(t - tp)))]).reindex(R.index)
                    B.append(dict(ch=ch, cam=f"{run[-2:]}_{src}", t=tp, farbg_rel=np.median(x.farbg / R.farbg),
                                  maxsum_rel=np.median((x["max"] / x["sum"]) / (R["max"] / R["sum"])),
                                  ped_rel=np.median(x.ped / R.ped), ped_share=np.median(x.ped / x["sum"])))
                bands = pd.cut(zled.reindex(R.index), 5, labels=False)
                for tp in (400, 600, 800, 1000):
                    sel = ids[np.abs(t - tp) <= 10]
                    X = pd.concat([led(d, i).reindex(R.index).farbg / R.farbg for i in sel], axis=1).mean(axis=1)
                    for bnd, g in X.groupby(bands):
                        BAND.append(dict(run=run[-2:], cam=src, ch=ch, t=tp, band=int(bnd),
                                         z=f"{zled.reindex(g.index).min():.2f}-{zled.reindex(g.index).max():.2f}",
                                         rel=g.median()))
    b = pd.DataFrame(B)
    for col in ("farbg_rel", "maxsum_rel", "ped_rel", "ped_share"):
        for ch in range(3):
            print(f"--- {col}, Kanal {ch}")
            print(b[b.ch == ch].pivot_table(index="t", columns="cam", values=col).round(4).to_string())
    w = b.t.between(400, 1200)
    for col in ("farbg_rel", "maxsum_rel", "ped_rel", "ped_share"):
        print(f"{col} 400-1200 s (min/max ueber Kanaele 0-2 und Zeiten): " + "; ".join(
            f"{c} {g[col].min():.3f}-{g[col].max():.3f}" for c, g in b[w].groupby("cam")))
    bd = pd.DataFrame(BAND)
    print("max/Summe ist bei hohem Sockelanteil (ped/sum) kein reines Formmass (Hintergrund in der Box-Summe); nur bei"
          " kleinem Sockelanteil als Fleckform lesen.")
    for cam in ("C3", "J2"):
        pv = bd[bd.cam == cam].pivot_table(index=["ch", "t", "band"], columns="run", values="rel")
        pv["R3/R1"] = pv.R3 / pv.R1
        pv["R3/R2"] = pv.R3 / pv.R2
        print(f"{cam} farbg/ref je Hoehenband (+-10 s; Band 0 = unten), Verhaeltnis R3/R1 und R3/R2:")
        print(pv.round(3).to_string())
        for ch in range(3):
            q = pv.loc[ch][["R3/R1", "R3/R2"]]
            sp = q.groupby(level="t").agg(lambda x: x.max() - x.min()).max().max()
            print(f"  {cam} Kanal {ch}: R3/R1 und R3/R2 {q.min().min():.3f}-{q.max().max():.3f}; groesste Spanne ueber die "
                  f"Baender zu einem Zeitpunkt {sp:.3f}")


print("\n======== C Profile je Quelle [1/m]")
Cr = []
for (run, src), (V, cen, _) in L3.items():
    for j, z in enumerate(cen):
        for tp in (400, 600, 800):
            Cr.append(dict(run=run[-2:], src=src[:2], layer=j, z=round(float(z), 2), t=tp, k=P.window_mean(V[j], tg, tp)))
c = pd.DataFrame(Cr)
for tp in (400, 600, 800):
    p = c[c.t == tp].pivot_table(index=["layer", "z"], columns=["run", "src"], values="k")
    p.columns = [f"{r}_{s}" for r, s in p.columns]
    print(f"--- t = {tp} s"); print(p.round(2).to_string())
cc = c[c.layer.between(3, 22)]
print("Schichten 3-22: " + "; ".join(f"{tp} s C3 R3 {g.k.min():.2f}-{g.k.max():.2f}"
                                     for tp, g in cc[(cc.run == "R3") & (cc.src == "C3")].groupby("t")))
c7 = c[c.layer.between(7, 12) & (c.src == "st")]
print("Stapel Schichten 7-12 (z 0,76-1,27 m), 400-800 s: " + "; ".join(
    f"{r} {g.k.min():.2f}-{g.k.max():.2f}" for r, g in c7.groupby("run")))

print("\n======== D Stufe-4-Kennzahlen an den LEM-Hoehen")
for run in RUNS3:
    tv = s0.vent(run)
    Lm = s0.lem(run, "F2")
    for src in SRC:
        V, cen, chs = L3[(run, src)]
        for h in Lm:
            v = V[int(np.argmin(np.abs(cen - h)))]
            ml, mm = s0.metrics(Lm[h], tv), s0.metrics(v, tv)
            sl, sv = s0.smooth(Lm[h]), s0.smooth(v)
            win = (tg > 0) & (tg < tv - 20) & (sl >= S4.MARD_LEM_FRAC * ml["peak"])
            print(f"  {run} z={h} {src:10s} ch{''.join(map(str, chs))}: Spitze/LEM {mm['peak'] / ml['peak']:.3f}, "
                  f"Plateau/LEM {mm['plateau'] / ml['plateau']:.3f}, mard {np.nanmean(np.abs(sv[win] / sl[win] - 1)):.3f}"
                  f"; 400/600/800 s LEM {', '.join(f'{sl[tg == x][0]:.2f}' for x in (400, 600, 800))} LEDSA "
                  f"{', '.join(f'{sv[tg == x][0]:.2f}' for x in (400, 600, 800))}")

print("Gegenprobe ohne Hintergrundabzug (sum_col_val, sonst gleich), C3 R3:")
tv3 = s0.vent("Hep_220_S1_R3")
Lm3 = s0.lem("Hep_220_S1_R3", "F2")
per3 = [layers("Hep_220_S1_R3", "F2", "C3", RUNS / "Hep_220_S1_R3" / SRC["C3"], a_, "sum_col_val")
        for a_ in range(3) if free("Hep_220_S1_R3", ["C3"], a_)]
V3 = np.nanmean(np.stack([np.vstack(p_[0]) for p_ in per3]), axis=0)
for h in Lm3:
    v = V3[int(np.argmin(np.abs(per3[0][1] - h)))]
    ml, mm = s0.metrics(Lm3[h], tv3), s0.metrics(v, tv3)
    print(f"  z={h} C3 sum_col_val: Spitze/LEM {mm['peak'] / ml['peak']:.3f}, Plateau/LEM {mm['plateau'] / ml['plateau']:.3f}")

print("\n======== E Nachfuehrung C3 R3")
tl = pd.read_csv(RUNS / "Hep_220_S1_R3" / "F2L_C3" / "analysis" / "tracking_log.csv")
for lo, hi in ((-60, 0), (0, 250), (250, 1200), (1200, 1700)):
    g = tl[tl.t_exp.between(lo, hi)]
    print(f"  {lo}...{hi} s: shift_row {g.shift_row.min():+.2f}...{g.shift_row.max():+.2f} px, shift_col "
          f"{g.shift_col.min():+.2f}...{g.shift_col.max():+.2f} px, frac_refined {g.frac_refined.min():.2f}-"
          f"{g.frac_refined.max():.2f}")
li = np.loadtxt(RUNS / "Hep_220_S1_R3" / "F2L_C3" / "analysis" / "led_search_areas_with_coordinates.csv",
                delimiter=",", ndmin=2)
own0 = np.loadtxt(RUNS / "Hep_220_S1_R3" / "F2L_C3" / "analysis" / "led_array_indices_000.csv", dtype=int, ndmin=1)
r0 = li[np.isin(li[:, 0].astype(int), own0)]
print(f"  LED-Abstand im Bild (Median, Streifen 0): {np.median(np.abs(np.diff(r0[np.argsort(r0[:, 0])][:, 1]))):.1f} px")

print("\n======== F Screening Zwei-Kamera-Raeume: untere - obere Einzelkamera [1/m]")
runs = pd.read_csv(HERE / "setup" / "ledsa_h1_runs.csv", comment="#").run
save = set(C.CAM_EXCLUDE)
rows = []
for run in runs:
    C.CAM_EXCLUDE.clear()
    try:
        rr = C.rooms(run)
    finally:
        C.CAM_EXCLUDE.update(save)
    tv = s0.vent(run)
    for room, cams in rr.items():
        if len(cams) != 2:
            continue
        chs = [a for a in range(3) if free(run, cams, a)]
        ser, skip = {}, []
        for cam in cams:
            base = RUNS / run / f"{series(run, cam).position}_{cam}"
            per = []
            for a_ in chs:
                try:
                    per.append(np.vstack(layers(run, room, cam, base, a_)[0][3:23]))
                except SystemExit as e:
                    skip.append(f"{cam} ch{a_}: {str(e)[:60]}")
            if per:
                ser[cam] = np.nanmean(np.stack(per), axis=0)
        if skip:
            print(f"  [skip] {run} {room}: " + "; ".join(skip))
        if len(ser) < 2 or not chs:
            print(f"  [nicht pruefbar] {run} {room} {cams}: " + ("keine freie Kanaele (Saettigung)" if not chs
                                                                 else "eine Kamera ohne Reihe"))
            continue
        ww = (tg >= 300) & (tg <= tv - 20)
        dl = np.nanmedian((ser[cams[0]] - ser[cams[1]])[:, ww], axis=1)
        lvl = np.nanmedian(ser[cams[1]][:, ww])
        rows.append(dict(run=run, room=room, unten=cams[0], oben=cams[1], ch="".join(map(str, chs)),
                         median=np.nanmedian(dl), schicht_min=np.nanmin(dl), schicht_max=np.nanmax(dl),
                         anteil_pos=np.mean(dl > 0), k_oben=lvl, relativ=np.nanmedian(dl) / lvl,
                         ausgeschlossen=(run, cams[0]) in save or (run, cams[1]) in save))
sc = pd.DataFrame(rows).sort_values("median", ascending=False)
print(sc.round(3).to_string(index=False))
o = sc[~((sc.run == "Hep_220_S1_R3") & (sc.room == "F2"))]
print(f"ohne R3 F2: |Median| max {o['median'].abs().max():.3f} 1/m, |relativ| max {o.relativ.abs().max():.3f}; "
      f"R3 F2: Median {sc[(sc.run == 'Hep_220_S1_R3') & (sc.room == 'F2')]['median'].iloc[0]:+.3f}")

print("\n======== G Belichtung C3 (EXIF)")
ex = pd.read_csv(HERE / "inventory" / "h1_exif_weitergabe.csv.gz", comment="#")
for run in RUNS3:
    g = ex[(ex.run == run) & ex.series.astype(str).str.contains("C3")]
    print(f"  {run}: Serien {sorted(g.series.unique())}, Bilder {len(g)}, Belichtung {sorted(g.expo.round(6).unique())} s, "
          f"Blende {sorted(g.fnum.unique())}, ISO {sorted(g.iso.unique())}")

if not READOUT:
    print("\n======== H uebersprungen: Auslese je Bild (analysis/channel*/) fehlt")
else:
    print("\n======== H Zeitverlauf Bildguete F2 R1-R3 (eigene LEDs, Kanal 0-2 gemittelt, alle 50 s): farbg/ref, max/Summe "
          "relativ, Sockelanteil ped/sum")
    TT = list(range(0, 1701, 50))
    H = {}
    for run in RUNS3:
        for src in ("C3", "J2"):
            an = RUNS / run / SRC[src] / "analysis"
            info = pd.read_csv(an / "image_infos_analysis.csv")
            info.columns = [c.strip("#") for c in info.columns]
            t, ids = info["Experiment_Time[s]"].to_numpy(float), info["ID"].to_numpy(int)
            acc = {q: {tp: [] for tp in TT} for q in ("farbg", "maxsum", "ped/sum")}
            for ch in range(3):
                own = np.loadtxt(an / f"led_array_indices_{ch:03d}.csv", dtype=int, ndmin=1)
                d = an / f"channel{ch}"
                R = pd.concat([led(d, i) for i in ids[(t >= -60) & (t <= -5)]]).groupby(level=0).mean(numeric_only=True)
                R = R.loc[R.index.isin(own)]
                for tp in TT:
                    i = int(np.argmin(np.abs(t - tp)))
                    if abs(t[i] - tp) > 5:
                        continue
                    x = led(d, ids[i]).reindex(R.index)
                    acc["farbg"][tp].append(np.median(x.farbg / R.farbg))
                    acc["maxsum"][tp].append(np.median((x["max"] / x["sum"]) / (R["max"] / R["sum"])))
                    acc["ped/sum"][tp].append(np.median(x.ped / x["sum"]))
            for q, v in acc.items():
                H[(q, f"{run[-2:]}_{src}")] = {tp: np.mean(x) if x else np.nan for tp, x in v.items()}
    h = pd.DataFrame(H)
    for q in ("farbg", "maxsum", "ped/sum"):
        print(f"--- {q}")
        print(h[q].round(3).to_string())
