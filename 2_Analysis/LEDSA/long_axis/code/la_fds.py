# -*- coding: utf-8 -*-
r"""FDS-Vergleich der Langachse (2026-11-27; Abschaetzung, kein voller Twin).

Hinweis (2026-11-27): Das LEDSA-Paper nutzt diese Abschaetzung nicht; es rechnet den Vergleich aus der
3D-Extinktionsausgabe der FDS-Basislaeufe entlang derselben Strahlen neu (METHODS.md Abschnitt 9.4, Hinweis).

Daten: FDS-Extinktionsschnitte des Reproduktionspakets (openbcl/hasenheide1-reproduction, Umgebungsvariable
H1_REPRO_ROOT), results/simulation/flow_field/ef_<075|150|300>_t<100|200|300|600>.npz (FDS ysmatched): zwei senkrechte y-z-Ebenen ueber die ganze Wohnungslaenge, K0 bei
x = 0,55 m und K1 bei x = 1,25 m (z 0-2,55 m, Raster 0,05 m), dazu der waagerechte Schnitt Kxy bei z = 2,0 m; je Brand
nur t = 100/200/300/600 s. Zuordnung (hasenheide1-ledsa runs.csv): Hep_160_S2/S3 = Hep_160_075 -> '075',
Hep_220_S1 = Hep_220_300 -> '300'.

Vorwaertsmodell: je LED gerader Strahl Kamera -> LED (Kamera la_positions.csv, LED x/y/z aus
analysis/led_search_areas_with_coordinates.csv), optische Dicke tau = Integral K ds, Schritt DS; K(x, y, z) linear
zwischen den Ebenen in x (ausserhalb 0,55-1,25 m die naechste Ebene), bilinear in (y, z); OBST-Zellen einer Ebene ->
nur die andere; in beiden OBST -> 0 (Anteil ausgegeben). Inversion wie LEDSA 0.13.0 linear
(ExtinctionCoefficientsLinear: NNLS auf [A; sqrt(lambda) L], L = zweite Differenz, lambda = la.INVERSION) mit der
LEDSA-Weglaengenmatrix led_array_<a>_distances_per_layer.txt (gleiche LEDs wie die Messung; eigene Geometrie gegen die
Datei geprueft); Schichten ohne Strahl NaN. Messung: out/la_k_1s.csv.gz, Mittel +-10 s um t (wie la_profiles).

Naeherung der zwei Ebenen: die Strahlen liegen bei x 0,26-0,73 m (LED 4) bzw. 0,26-1,49 m (LED 2); Querverteilung in
x nicht erfasst. Pruefung bei z = 2,0 m: tau entlang der (x, y)-Spur im waagerechten Schnitt Kxy gegen tau aus den
Ebenen bei z = 2,0 m (Spalte plane_bias_z2).

Aufruf (hh2-venv): python la_fds.py   -> out/la_fds_profiles.csv, out/la_fds_check.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator
from scipy.optimize import nnls

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
import la  # noqa: E402

from ledsa_h1_paths import need_env  # noqa: E402
# FDS-Schnitte aus dem Reproduktionspaket openbcl/hasenheide1-reproduction (H1_REPRO_ROOT = dessen Wurzel)
FLOW = Path(need_env("H1_REPRO_ROOT", "Wurzel des Reproduktionspakets hasenheide1-reproduction")) / "results" / \
    "simulation" / "flow_field"
FIRE = {"Hep_220_S1": "300", "Hep_160_S2": "075", "Hep_160_S3": "075"}
TIMES = [100, 200, 300, 600]
X0, X1 = 0.55, 1.25
DS = 0.01
OUT = la.LA / "out"


def fire_of(run):
    return FIRE[run.rsplit("_", 1)[0]]


class Field:
    def __init__(self, tag, t):
        d = np.load(FLOW / f"ef_{tag}_t{t}.npz")
        self.t = float(d["tact"])
        mk = lambda y, z, K: RegularGridInterpolator((np.asarray(z, float), np.asarray(y, float)),
                                                       np.asarray(K, float), bounds_error=False, fill_value=np.nan)
        self.k0, self.o0 = mk(d["y0"], d["z0"], d["K0"]), mk(d["y0"], d["z0"], d["obst0"].astype(float))
        self.k1, self.o1 = mk(d["y1"], d["z1"], d["K1"]), mk(d["y1"], d["z1"], d["obst1"].astype(float))
        self.kxy = RegularGridInterpolator((np.asarray(d["x"], float), np.asarray(d["yP"], float)),
                                           np.asarray(d["Kxy"], float), bounds_error=False, fill_value=np.nan)
        self.oxy = RegularGridInterpolator((np.asarray(d["x"], float), np.asarray(d["yP"], float)),
                                           d["obstxy"].astype(float), bounds_error=False, fill_value=np.nan)

    def planes(self, x, y, z):
        p = np.column_stack([z, y])
        a, b = self.k0(p), self.k1(p)
        oa, ob = self.o0(p) > 0.5, self.o1(p) > 0.5
        a = np.where(oa | ~np.isfinite(a), np.nan, a)
        b = np.where(ob | ~np.isfinite(b), np.nan, b)
        w = np.clip((x - X0) / (X1 - X0), 0, 1)
        k = np.where(np.isfinite(a) & np.isfinite(b), (1 - w) * a + w * b, np.where(np.isfinite(a), a, b))
        bad = ~np.isfinite(k)
        return np.where(bad, 0.0, k), bad


def ray_pts(c, p):
    L = float(np.linalg.norm(p - c))
    n = max(int(np.ceil(L / DS)), 1)
    s = (np.arange(n) + 0.5) / n
    return c[None, :] + s[:, None] * (p - c)[None, :], L / n


def layer_matrix(cam, leds, bounds):
    """Weglaenge je LED und Schicht (gerader Strahl), zum Abgleich mit der LEDSA-Datei."""
    A = np.zeros((len(leds), len(bounds) - 1))
    for i, p in enumerate(leds):
        z0, z1 = cam[2], p[2]
        L = float(np.linalg.norm(p - cam))
        for j in range(len(bounds) - 1):
            lo, hi = bounds[j], bounds[j + 1]
            if abs(z1 - z0) < 1e-12:
                A[i, j] = L if lo <= z0 < hi else 0.0
            else:
                f0, f1 = sorted([(lo - z0) / (z1 - z0), (hi - z0) / (z1 - z0)])
                A[i, j] = L * max(0.0, min(f1, 1.0) - max(f0, 0.0))
    return A


def invert(A, tau, lam):
    n = A.shape[1]
    L = np.zeros((n - 2, n))
    for i in range(n - 2):
        L[i, i:i + 3] = (1, -2, 1)
    x, _ = nnls(np.vstack((A, np.sqrt(lam) * L)), np.hstack((tau, np.zeros(n - 2))))
    return x


def main():
    lam = float(la.INVERSION["lambda_reg"])
    lo, hi = map(float, la.INVERSION["domain_bounds"].split())
    nl = int(la.INVERSION["num_layers"])
    bounds = np.linspace(lo, hi, nl + 1)
    zc = 0.5 * (bounds[:-1] + bounds[1:])
    s = la._csv("la_series.csv")
    pos = la._csv("la_positions.csv").set_index("position")
    k = pd.read_csv(OUT / "la_k_1s.csv.gz")
    fields = {(tag, t): Field(tag, t) for tag in set(FIRE.values()) for t in TIMES}
    rows, chk = [], []
    from la_post import EXCLUDED
    for r in s.itertuples():
        if (r.run, r.cam) in EXCLUDED:
            continue
        wd = la.workdir(r.run, r.cam)
        P = pos.loc[r.position]
        cam = np.array([P.x_m, P.y_m, P.z_m], float)
        c = pd.read_csv(wd / "analysis" / "led_search_areas_with_coordinates.csv", comment="#", header=None,
                        names=["id", "row", "col", "x", "y", "z", "w", "h"]).set_index("id")
        tag = fire_of(r.run)
        for a in (0, 1):
            ids = pd.read_csv(wd / "analysis" / f"led_array_indices_{a:03d}.csv", header=None)[0].to_numpy()
            ids = np.sort(ids)
            leds = c.loc[ids, ["x", "y", "z"]].to_numpy(float)
            A_file = np.loadtxt(wd / f"led_array_{a}_distances_per_layer.txt")
            A_own = layer_matrix(cam, leds, bounds)
            dev = float(np.abs(A_file - A_own).max()) if A_file.shape == A_own.shape else np.inf
            if dev > 1e-3:
                raise SystemExit(f"[--] {r.run} {r.cam} A{a}: Weglaengen weichen ab ({dev:.3g} m, Form "
                                 f"{A_file.shape} / {A_own.shape})")
            norays = A_file.sum(axis=0) <= 0
            for t in TIMES:
                F = fields[(tag, t)]
                tau, badf, tau_xy, tau_pl = [], [], [], []
                for p in leds:
                    q, ds = ray_pts(cam, p)
                    kk, bad = F.planes(q[:, 0], q[:, 1], q[:, 2])
                    tau.append(kk.sum() * ds)
                    badf.append(bad.mean())
                    # Pruefung der Ebenen-Naeherung bei z = 2,0 m entlang derselben (x, y)-Spur
                    kxy = F.kxy(q[:, :2])
                    oxy = F.oxy(q[:, :2]) > 0.5
                    kp, badp = F.planes(q[:, 0], q[:, 1], np.full(len(q), 2.0))
                    ok = np.isfinite(kxy) & ~oxy & ~badp
                    tau_xy.append(kxy[ok].sum() * ds)
                    tau_pl.append(kp[ok].sum() * ds)
                kf = invert(A_file, np.array(tau), lam)
                kf[norays] = np.nan
                g = k[(k.run == r.run) & (k.cam == r.cam) & (k.array == a) & (k.t_s >= t - 10) & (k.t_s <= t + 10)]
                km = g.groupby("layer").k.mean() if len(g) else pd.Series(dtype=float)
                for j in range(nl):
                    rows.append(dict(run=r.run, cam=r.cam, array=a, fire=tag, t_s=t, t_fds_s=round(F.t, 2), layer=j,
                                     z_m=round(zc[j], 4), k_fds=kf[j], k_meas=km.get(j, np.nan)))
                tx, tp = np.array(tau_xy), np.array(tau_pl)
                chk.append(dict(run=r.run, cam=r.cam, array=a, fire=tag, t_s=t, n_led=len(leds),
                                A_dev_m=dev, obst_frac_max=round(float(np.max(badf)), 4),
                                tau_med=round(float(np.median(tau)), 4),
                                plane_bias_z2=round(float(np.median(tp / tx) - 1), 4) if (tx > 0).any() else np.nan))
        print(f"[ok] {r.run} {r.cam} (FDS {tag})", flush=True)
    d = pd.DataFrame(rows)
    d.to_csv(OUT / "la_fds_profiles.csv", index=False, float_format="%.5f")
    ck = pd.DataFrame(chk)
    ck.to_csv(OUT / "la_fds_check.csv", index=False)
    pd.set_option("display.width", 220)
    print(ck.to_string(index=False))


if __name__ == "__main__":
    main()
