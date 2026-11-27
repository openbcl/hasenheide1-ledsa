"""Zerlegung des Schritts prior0100 (fruehere Stapel, LEDSA 0.10.0) -> neu (0.13.0, sum_col_val) (festgelegt 2026-11-24).

Die frueheren Stapel (stacked_results/*/config_stacked.ini) unterscheiden sich von unseren in: (pane) kein pane_distance (Wege
bis zur Kamera im Rauch), (geo) untere Kamera x = 0 statt ~-0,18 m (domain_bounds 0-2,5 statt 0-2,535 m nicht pruefbar, s. make), (ref) keine
ref_img_indices -> erste num_ref_images = 10 Bilder (LEDSA 0.13.0, StackedExtinctionCoefficients: "first N"; Verhalten
in 0.10.0 nicht geprueft). Je Variante wird nur der Stapel (-as, sum_col_val) mit LEDSA 0.13.0 aus unseren Auslesen neu
invertiert, in runs/<Lauf>/zerl_<Raum>_<Variante>/ (Hauptauswertung unberuehrt); Variante all = alle drei.
  make   schreibt die config_stacked.ini der Varianten (hh2-venv)
  eval   vergleicht an den LEM-Hoehen (wie compare_prior: robuste Nullung, Widmann, Sigma-Clip, +-10 s, ohne Maske; Ausgaben vor dem Wechsel
         zum Hampel-Filter am 2026-11-27, nicht neu erzeugt)
Aufruf: hh2-venv decompose_prior0100.py <LEDSA-Ordner> make|eval [<out-Ordner>]
"""
import configparser
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(sys.argv[1]); WHAT = sys.argv[2]
sys.path.insert(0, str(HERE))
# Fruehere Stapel (nicht in diesem Repo): Ordner per H1_PRIOR0100
OLD = Path(os.environ.get("H1_PRIOR0100", str(HERE / "stacked_results")))
from ledsa_h1_config import RUNS                                    # noqa: E402

ROOMS = [("Hep_160_S2_R2", "F2", "stacked_F2"), ("Hep_160_S2_R2", "F3", "stacked_F3"),
         ("Hep_160_S2_R3", "F2", "stacked_F2"), ("Hep_160_S2_R3", "F3", "stacked_F3")]
VARIANTS = ["pane", "geo", "ref", "all"]


def make():
    for run, room, bsub in ROOMS:
        ours_f = RUNS / run / f"stacked_{room}" / "config_stacked.ini"
        boer = configparser.ConfigParser(); boer.read(OLD / run / bsub / "config_stacked.ini")
        for v in VARIANTS:
            c = configparser.ConfigParser(); c.read(ours_f, encoding="utf-8")     # frisch lesen: DEFAULT bleibt getrennt
            c["DEFAULT"]["reference_property"] = "sum_col_val"
            c["DEFAULT"]["output_path"] = "."
            parts = {"pane", "geo", "ref"} if v == "all" else {v}
            for i in (0, 1):
                s = f"simulation_{i}"
                if "pane" in parts:
                    c.remove_option(s, "pane_distance")
                if "geo" in parts:
                    c[s]["camera_position"] = boer[s]["camera_position"]
                if "ref" in parts:
                    c.remove_option(s, "ref_img_indices")
            # domain_bounds bleibt 0-2,535 m: mit deren 0-2,5 m bricht LEDSA 0.13.0 ab (InconsistentDistanceError, oberste
            # LED bei z = 2,535 m liegt ausserhalb); die LED-Koordinaten der 0.10.0-Stapel (vermutlich bis 2,5 m) liegen nicht vor.
            d = RUNS / run / f"zerl_{room}_{v}"
            d.mkdir(exist_ok=True)
            with open(d / "config_stacked.ini", "w", encoding="utf-8") as fh:
                fh.write(f"# Zerlegung prior0100 -> neu, Variante {v} ({', '.join(sorted(parts))} wie prior0100); "
                         f"checks/decompose_prior0100.py\n")
                c.write(fh)
            print(f"[ok] {d / 'config_stacked.ini'}")


def evaluate(out):
    import ledsa_h1_stage0 as s0
    import ledsa_h1_profiles as P
    tg = s0.grid()

    def ser_mean_at(kdir, h):           # wie compare_prior: Mittel der Kanaele an Hoehe h, Paper-Nachbearbeitung
        vs = []
        for a in range(3):
            f = kdir / f"extinction_coefficients_linear_channel_{a}_sum_col_val_led_array_{a}.csv"
            if not f.exists():
                raise SystemExit(f"[--] fehlt {f}")
            t, k, cen = s0.load_k(f)
            vs.append(P.paper_series(t, k[:, int(np.argmin(np.abs(cen - h)))], a, "zerl"))
        return np.nanmean(vs, axis=0)

    def vs_lem(v, Lh, tv):
        ml, mm = s0.metrics(Lh, tv), s0.metrics(v, tv)
        sl, sv = s0.smooth(Lh), s0.smooth(v)
        win = (tg > 0) & (tg < tv - 20) & (sl >= 0.2 * ml["peak"])
        return dict(peak_ratio=mm["peak"] / ml["peak"], plateau_ratio=mm["plateau"] / ml["plateau"],
                    mard=float(np.nanmean(np.abs(sv[win] / sl[win] - 1))))

    rows = []
    for run, room, bsub in ROOMS:
        srcs = {"prior0100": OLD / run / bsub,
                "neu": RUNS / run / f"stacked_{room}"}
        srcs.update({v: RUNS / run / f"zerl_{room}_{v}" for v in VARIANTS})
        for lab, base in srcs.items():
            kd = base / "analysis" / "extinction_coefficients" / "linear"
            kd = kd if lab == "prior0100" else kd / "sum_col_val"
            L = s0.lem(run, room); tv = s0.vent(run)
            for h in L:
                rows.append(dict(run=run, room=room, z_lem=h, variant=lab, **vs_lem(ser_mean_at(kd, h), L[h], tv)))
    d = pd.DataFrame(rows)
    d.to_csv(out / "decompose_prior0100.csv", index=False, float_format="%.4f")
    pd.set_option("display.width", 200)
    for col in ("plateau_ratio", "peak_ratio"):
        print(col)
        print(d.pivot_table(index=["run", "room", "z_lem"], columns="variant", values=col)
              [["prior0100", "all", "pane", "geo", "ref", "neu"]].round(3).to_string())


if __name__ == "__main__":
    if WHAT == "make":
        make()
    else:
        evaluate(Path(sys.argv[3]))
