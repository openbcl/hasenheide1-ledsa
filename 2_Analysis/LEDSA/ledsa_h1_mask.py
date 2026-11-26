# -*- coding: utf-8 -*-
r"""Gueltigkeit der LEDSA-Strahlen und Schichten (H1, LEDSA 0.13.0), uebernommen aus der Hasenheide-2-Auswertung.

Kriterium (Startwerte aus der Hasenheide-2-Auswertung; fuer H1 nach Stufe 0 zu bestaetigen):
  Strahl ungueltig, wenn farbg_sum < SNR x sigma_sum (Leserauschen der Box-Summe je Lauf/Kamera/Kanal,
  inventory/ledsa_h1_read_noise.csv, ledsa_h1_noise.py) oder farbg_sum nicht endlich (kein Fernfeld-Band).
  Schicht ungueltig, wenn der Weglaengen-Anteil ungueltiger Strahlen > W_MAX (0,5); gestapelt beide Kameras zusammen
  (Bildpaare per Experiment_Time, Toleranz 3 s wie -as).
  Dieselbe Maske gilt fuer die Nebengroesse sum_col_val (nicht schwaecher).
Array i wird im Kanal i ausgewertet (rot/gruen/blau, Paper). Alle Kameras der Stufe A haben optisches Schwarz; ohne
sigma bricht das Skript ab (kein stiller Rueckfall).

Aufrufe (hh2-venv oder ledsa-Env):
  python ledsa_h1_mask.py flag <Lauf> <Raum>
      -> runs/<Lauf>/plots_h1/mask_<Raum>.csv.gz (snr, quelle, led_array, t_s, layer, anteil, gesperrt) + Zusammenfassung
  python ledsa_h1_mask.py pedestal <Lauf> <Kamera>
      -> Fernfeld-Sockel / Box-Summe in den Referenzbildern je Array (Median, p95, Anteil > 1 %), Anteil LEDs
         ohne Sockel; Zeilen in inventory/ledsa_h1_pedestal_check.csv
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ledsa_h1_config import INVERSION, RUNS, mask_name, rooms, stacked_name, workdir   # noqa: E402

NOISE = HERE / "inventory" / "ledsa_h1_read_noise.csv"
PED_OUT = HERE / "inventory" / "ledsa_h1_pedestal_check.csv"
SNR_MIN, SNR_SENS, W_MAX = 3.0, (2.0, 3.0, 5.0), 0.5
TOL_S = float(INVERSION["time_sync_tolerance"])
COLS = {5: ["led_id", "line", "sum", "avg", "max"], 7: ["led_id", "line", "sum", "avg", "max", "farbg", "ped"]}


def sigma(run, cam, ch):
    if not NOISE.exists():
        raise SystemExit(f"[--] fehlt {NOISE} (ledsa_h1_noise.py)")
    d = pd.read_csv(NOISE, comment="#")
    r = d[(d.run == run) & (d.cam == cam) & (d.channel == ch)]
    if len(r) != 1 or not np.isfinite(r.sigma_sum.iloc[0]):
        raise SystemExit(f"[--] kein Leserauschen fuer {run} {cam} Kanal {ch}")
    return float(r.sigma_sum.iloc[0])


def load_sums(work, ch):
    rows = []
    for f in (work / "analysis" / f"channel{ch}").glob("*_led_positions.csv"):
        d = pd.read_csv(f, comment="#", header=None, skipinitialspace=True)
        if d.shape[1] not in COLS:
            raise SystemExit(f"[--] {f}: {d.shape[1]} Spalten (erwartet 7 mit Fernfeld-Sockel)")
        d.columns = COLS[d.shape[1]]
        if "ped" not in d:
            raise SystemExit(f"[--] {f}: ohne Fernfeld-Sockel (farfield_distances?)")
        d["img_id"] = int(f.name.split("_")[0])
        rows.append(d[["img_id", "led_id", "sum", "farbg", "ped"]])
    if not rows:
        raise SystemExit(f"[--] keine Schritt-3-Dateien in {work / 'analysis' / f'channel{ch}'}")
    return pd.concat(rows, ignore_index=True)


def ref_ids(work):
    ca = work / "config_analysis.ini"
    m = re.search(r"ref_img_indices = ([\d ]+)\s*$", ca.read_text(encoding="utf-8"), re.M) if ca.exists() else None
    return [int(v) for v in m.group(1).split()] if m else list(range(1, 11))


def times(work):
    info = pd.read_csv(work / "analysis" / "image_infos_analysis.csv")
    info.columns = ["img_id", "name", "time", "t_exp"]
    return info[["img_id", "t_exp"]]


def layer_fraction(s, work, arr):
    ids = np.loadtxt(work / "analysis" / f"led_array_indices_{arr:03d}.csv", dtype=int)[::-1]
    A = np.loadtxt(work / f"led_array_{arr}_distances_per_layer.txt")
    bad = s[s.led_id.isin(ids)].pivot(index="t_exp", columns="led_id", values="bad").reindex(columns=ids)
    F = bad.to_numpy(float)
    return bad.index.to_numpy(float), F @ A, np.ones_like(F) @ A


def flag(run, room):
    cams = rooms(run)[room]
    works = [workdir(run, c) for c in cams]
    out, summ = [], []
    for arr in range(3):
        ch = arr
        tabs = []
        for cam, work in zip(cams, works):
            s = load_sums(work, ch).merge(times(work), on="img_id")
            tabs.append((cam, work, s, sigma(run, cam, ch)))
        for snr in SNR_SENS:
            per = []
            for cam, work, s, sig in tabs:
                s = s.assign(bad=~(s.farbg >= snr * sig))          # NaN (kein Band) -> ungueltig
                per.append((cam,) + layer_fraction(s, work, arr))
                summ.append(dict(snr=snr, kamera=cam, array=arr, sigma=round(sig, 2),
                                 strahlen_ungueltig_pct=round(100 * s.bad.mean(), 2),
                                 farbg_nan_pct=round(100 * s.farbg.isna().mean(), 2)))
            srcs = [(c, t, b / tot) for c, t, b, tot in per]
            if len(per) == 2:
                (_, t0, b0, n0), (_, t1, b1, n1) = per
                j = np.abs(t1[None, :] - t0[:, None]).argmin(axis=1)
                ok = np.abs(t1[j] - t0) <= TOL_S
                srcs.insert(0, (stacked_name(room), t0[ok], (b0[ok] + b1[j[ok]]) / (n0[ok] + n1[j[ok]])))
            for lab, t, w in srcs:
                n_t, n_l = w.shape
                w = w.ravel()
                out.append(pd.DataFrame(dict(snr=snr, quelle=lab, led_array=arr, t_s=np.repeat(t, n_l),
                                             layer=np.tile(np.arange(n_l), n_t), anteil=w, gesperrt=w > W_MAX)))
    d = pd.concat(out, ignore_index=True)
    f = RUNS / run / "plots_h1" / mask_name(room)
    f.parent.mkdir(exist_ok=True)
    d.to_csv(f, index=False, float_format="%.4f")
    print(pd.DataFrame(summ).to_string(index=False))
    main = stacked_name(room) if len(cams) == 2 else cams[0]
    for (snr, arr), g in d[d.quelle == main].groupby(["snr", "led_array"]):
        inv = g.gesperrt
        print(f"SNR {snr:g} Array {arr}: {main} gesperrt {100 * inv.mean():.1f} % der (t, Schicht)"
              + (f", Zeitspanne {g[inv].t_s.min():.0f}-{g[inv].t_s.max():.0f} s" if inv.any() else ""))
    print(f"[ok] {f}")


def pedestal(run, cam):
    """Fernfeld-Sockel (N x Sockel je Pixel, Spalte ped) / Box-Summe in den Referenzbildern, je Array."""
    work = workdir(run, cam)
    refs = ref_ids(work)
    rows = []
    for arr in range(3):
        ids = np.loadtxt(work / "analysis" / f"led_array_indices_{arr:03d}.csv", dtype=int)
        s = load_sums(work, arr)
        s = s[s.img_id.isin(refs) & s.led_id.isin(ids)]
        q = (s.ped / s["sum"]).to_numpy(float)
        fin = np.isfinite(q)
        rows.append(dict(run=run, cam=cam, array=arr, channel=arr, n_ref=len(refs), n_led=len(ids),
                         ped_frac_median_pct=round(100 * np.median(q[fin]), 3) if fin.any() else np.nan,
                         ped_frac_p95_pct=round(100 * np.percentile(q[fin], 95), 3) if fin.any() else np.nan,
                         led_ueber_1pct=round(100 * np.mean(q[fin] > 0.01), 1) if fin.any() else np.nan,
                         ohne_sockel_pct=round(100 * (~fin).mean(), 2)))
    d = pd.DataFrame(rows)
    print(d.to_string(index=False))
    key = ["run", "cam", "array"]
    old = pd.read_csv(PED_OUT, comment="#") if PED_OUT.exists() else pd.DataFrame(columns=d.columns)
    keep = old[~old.set_index(key).index.isin(d.set_index(key).index)] if len(old) else old
    with open(PED_OUT, "w", encoding="utf-8", newline="") as fh:
        fh.write("# ledsa_h1_mask.py pedestal: Fernfeld-Sockel / Box-Summe in den Referenzbildern (LEDSA-Faustregel "
                 "< ~1 %), je Array im eigenen Kanal\n")
        pd.concat([keep, d], ignore_index=True).sort_values(key).to_csv(fh, index=False)
    print(f"[ok] {PED_OUT}")


if __name__ == "__main__":
    {"flag": flag, "pedestal": pedestal}[sys.argv[1]](*sys.argv[2:])
