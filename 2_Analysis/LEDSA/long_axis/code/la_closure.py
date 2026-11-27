# -*- coding: utf-8 -*-
r"""Schliessungstest der Langachse (2026-11-27): optische Dicke je N1-Strahl, gemessen gegen die Vorhersage aus den
gemessenen Raumprofilen der Raumauswertung (unabhaengig von FDS und LEM).

Stufe reduce (braucht die Einzelbild-Ablesung runs/<Lauf>/<Pos>_<Kamera>/analysis/channel1/, nicht im Repo):
  tau je LED und Bild = -ln(farbg / farbg_ref) (farbg_ref = Mittel ueber die LEDSA-Referenzbilder, wie
  farbg_sum_col_val in LEDSA), Strahl gueltig nach dem U_B-Kriterium der Maske (U_B 0,2; la.mask); je Profilzeit
  t (200/400/600/800 s wie inventory/ledsa_h1_profiles.csv) Median ueber die gueltigen Bilder in t +- 10 s, wenn
  mindestens die Haelfte der Bilder gueltig ist; mal Widmann gruen (Bezug 638 nm wie die Raumprofile).
  Gesperrte Zeiten (la_post.CAM_MOVED) und Serien (la_post.EXCLUDED) entfallen.   -> out/la_tau_led.csv.gz
Stufe closure (nur Repo-Daten):
  Vorhersage tau_pred = Integral k_Raum(z) ds entlang des geraden Strahls Kamera -> LED; k_Raum = Raumprofil
  derselben Versuchsreihe und Zeit (inventory/ledsa_h1_profiles.csv, Hauptinversion, Kanal 1, sonst Mittel der
  vorhandenen Kanaele; Mittel +- 10 s), waagerecht gleichfoermig je Raum angenommen. Raumgrenzen in y = Wandmitten
  der FDS-Geometrie (OBST-Maske des Grundrissschnitts z = 2,0 m im Reproduktionspaket, results/simulation/
  flow_field/ef_*.npz): F1|F2 4,31 m (Wand 4,20-4,43), F2|FC 7,76 m (7,70-7,83), FC|F3 11,14 m (11,05-11,23).
  Flur FC ohne Messung: Mitte = Mittel der Profile F2 und F3, Klammer = punktweise kleineres bzw. groesseres der
  beiden.                                                                        -> out/la_closure.csv
Aufruf (hh2-venv): python la_closure.py reduce | closure
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
import la  # noqa: E402
import ledsa_h1_stage0 as s0  # noqa: E402
from la_post import CAM_MOVED, EXCLUDED  # noqa: E402

OUT = la.LA / "out"
TIMES = [200, 400, 600, 800]
HALF = 10.0
Y_F1F2, Y_F2FC, Y_FCF3 = 4.31, 7.76, 11.14
DS = 0.01
VALID_MIN = 0.5
WID = s0.widmann(la.CH)
PROF = la.REPO_LEDSA / "inventory" / "ledsa_h1_profiles.csv"


def reduce():
    s = la._csv("la_series.csv")
    rows = []
    for r in s.itertuples():
        if (r.run, r.cam) in EXCLUDED:
            continue
        work = la.workdir(r.run, r.cam)
        d = la._all_s3(work)
        refs = la.ref_ids(work)
        ref = d[d.img_id.isin(refs)].groupby("led_id")[["farbg", "ped"]].agg({"farbg": "mean", "ped": "median"})
        s0m = d[d.img_id.isin(refs)].groupby("led_id").farbg.median()
        d = d.join(ref.rename(columns={"farbg": "Sref", "ped": "P0"}), on="led_id").join(s0m.rename("S0"), on="led_id")
        b = -np.log(d.farbg / d.S0)
        bad = ~((d.farbg > 0) & ~((b > la.B_MIN) & (la.U_B * (d.ped / d.farbg + d.P0 / d.S0) > la.DB_MAX)))
        d["tau"] = np.where(bad, np.nan, -np.log((d.farbg / d.Sref).clip(lower=1e-12))) * WID
        t_cut = CAM_MOVED.get((r.run, r.cam), np.inf)
        for a in (0, 1):
            ids = np.loadtxt(work / "analysis" / f"led_array_indices_{a:03d}.csv", dtype=int)
            for t in TIMES:
                if t > t_cut:
                    continue
                w = d[d.led_id.isin(ids) & (d.t_exp >= t - HALF) & (d.t_exp <= t + HALF)]
                g = w.groupby("led_id").tau
                frac = g.apply(lambda v: v.notna().mean())
                med = g.median().where(frac >= VALID_MIN)
                rows.append(pd.DataFrame(dict(run=r.run, cam=r.cam, array=a, t_s=t, led_id=med.index,
                                              tau=med.to_numpy(), valid_frac=frac.to_numpy())))
        print(f"[ok] {r.run} {r.cam}", flush=True)
    out = pd.concat(rows, ignore_index=True)
    out.to_csv(OUT / "la_tau_led.csv.gz", index=False, float_format="%.5f")
    print(f"[ok] {OUT / 'la_tau_led.csv.gz'} ({len(out)} Zeilen)")


def room_profile(p, run, room, t):
    q = p[(p.run == run) & (p.room == room) & (p.t_s == t)]
    if q.empty:
        return None
    if (q.channel == la.CH).any():
        q = q[q.channel == la.CH]
    g = q.groupby("z_m").k.mean().sort_index()
    return g.index.to_numpy(float), g.to_numpy(float)


def closure():
    p = pd.read_csv(PROF, comment="#")
    tau = pd.read_csv(OUT / "la_tau_led.csv.gz")
    pos = la._csv("la_positions.csv").set_index("position")
    rows = []
    for (run, cam), g in tau.groupby(["run", "cam"], sort=False):
        P = pos.loc[la.series(run, cam).position]
        c = np.array([P.x_m, P.y_m, P.z_m], float)
        co = pd.read_csv(la.workdir(run, cam) / "analysis" / "led_search_areas_with_coordinates.csv", comment="#",
                         header=None, names=["id", "row", "col", "x", "y", "z", "w", "h"]).set_index("id")
        for t, gt in g.groupby("t_s"):
            prof = {rm: room_profile(p, run, rm, t) for rm in ("F1", "F2", "F3")}
            for e in gt.dropna(subset=["tau"]).itertuples():
                led = co.loc[e.led_id, ["x", "y", "z"]].to_numpy(float)
                L = float(np.linalg.norm(led - c))
                n = max(int(np.ceil(L / DS)), 1)
                q = c[None, :] + ((np.arange(n) + 0.5) / n)[:, None] * (led - c)[None, :]
                ds = L / n
                y, z = q[:, 1], q[:, 2]
                rm = np.where(y < Y_F1F2, "F1", np.where(y < Y_F2FC, "F2", np.where(y < Y_FCF3, "FC", "F3")))
                seg = {r: float((rm == r).sum() * ds) for r in ("F1", "F2", "FC", "F3")}
                need = [r for r in ("F1", "F2", "F3") if seg[r] > 0]
                if any(prof[r] is None for r in need) or prof["F2"] is None or prof["F3"] is None:
                    continue
                kk = {r: np.interp(z, *prof[r]) for r in ("F1", "F2", "F3") if prof[r] is not None}
                base = sum(float(kk[r][rm == r].sum()) for r in need) * ds
                fc2, fc3 = kk["F2"][rm == "FC"], kk["F3"][rm == "FC"]
                fc_mid = float((0.5 * (fc2 + fc3)).sum() * ds)
                fc_lo = float(np.minimum(fc2, fc3).sum() * ds)
                fc_hi = float(np.maximum(fc2, fc3).sum() * ds)
                rows.append(dict(run=run, cam=cam, array=e.array, t_s=t, led_id=e.led_id, z_led_m=round(led[2], 4),
                                 L_m=round(L, 3), **{f"s_{r}_m": round(seg[r], 3) for r in seg}, tau_meas=e.tau,
                                 tau_pred=base + fc_mid, tau_pred_lo=base + fc_lo, tau_pred_hi=base + fc_hi,
                                 tau_pred_fc_share=fc_mid / (base + fc_mid) if base + fc_mid > 0 else np.nan))
    d = pd.DataFrame(rows)
    d["ratio"] = d.tau_meas / d.tau_pred
    with open(OUT / "la_closure.csv", "w", encoding="utf-8", newline="") as f:
        f.write("# la_closure.py: tau gemessen (x Widmann) gegen tau aus den Raumprofilen; FC = Mittel F2/F3, "
                "Klammer lo/hi; Raumgrenzen y 4,31 / 7,76 / 11,14 m\n")
        d.to_csv(f, index=False, float_format="%.5f")
    sm = summary(d)
    pd.set_option("display.width", 220)
    print(sm.to_string(index=False))


def summary(d, tau_min=0.1):
    """Je Lauf, Streifen, Zeit: Median der Verhaeltnisse ueber die LEDs mit tau_pred >= tau_min, Klammer aus lo/hi."""
    out = []
    for (run, a, t), g in d[d.tau_pred >= tau_min].groupby(["run", "array", "t_s"]):
        out.append(dict(run=run, array=a, t_s=t, n_led=len(g), ratio_med=g.ratio.median(),
                        ratio_lo=(g.tau_meas / g.tau_pred_hi).median(), ratio_hi=(g.tau_meas / g.tau_pred_lo).median(),
                        fc_share_med=g.tau_pred_fc_share.median(), tau_pred_med=g.tau_pred.median()))
    sm = pd.DataFrame(out).round(3)
    sm.to_csv(OUT / "la_closure_summary.csv", index=False)
    return sm


if __name__ == "__main__":
    {"reduce": reduce, "closure": closure}[sys.argv[1]]()
