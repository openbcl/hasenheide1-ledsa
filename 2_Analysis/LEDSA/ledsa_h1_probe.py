# -*- coding: utf-8 -*-
r"""Sichtpruefung einer Serie: gefundene LEDs (find_search_areas wie -s1, channel all, Radius 10, Perzentil P) in
Bildern zu gegebenen Zeiten [s rel. start_time]; dient zur Wahl eines unverdeckten Referenzbilds der LED-Suche
(Stufe 1, 2026-11-20: Personen vor dem Streifen im Brandraum F1 bei ~-30 s).
Aufruf (Conda-Env ledsa): python ledsa_h1_probe.py <Lauf> <Kamera> <t1> [<t2> ...] [--p 99.95]
"""
import contextlib
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ledsa_h1_config import series   # noqa: E402
from ledsa_h1_paths import img_path   # noqa: E402


def exif_table(r):
    def t_of(df):
        sub = df.subsec.fillna(0).astype(int).astype(str).str.ljust(2, "0").str[:2].astype(int) / 100.0
        return pd.to_datetime(df.dto, format="%Y:%m:%d %H:%M:%S") + pd.to_timedelta(sub, unit="s")
    folder = Path(r.folder_w)
    if "2_juelichMeasurements" in r.folder_w:
        e = pd.read_csv(HERE / "inventory" / "h1_exif_juelich.csv.gz")
        e = e[(e.tag == folder.parent.name) & (e.kamera == folder.name)]
    else:
        e = pd.read_csv(HERE / "inventory" / "h1_exif_weitergabe.csv.gz")
        e = e[(e.run == r.run) & (e.series == folder.name) & e["sub"].isna()]
    e = e.assign(t=(t_of(e) - pd.Timestamp(f"{r.date} {r.start_time}")).dt.total_seconds())
    return e[(e.t >= r.t_first_s - 0.5) & (e.t <= r.t_last_s + 0.5)].sort_values("t")


def main(run, cam, *args):
    from ledsa.core.image_reading import read_img_array_from_img
    from ledsa.data_extraction.step_1_functions import find_search_areas
    p = 99.95
    ts = []
    it = iter(args)
    for a in it:
        if a == "--p":
            p = float(next(it))
        else:
            ts.append(float(a))
    r = series(run, cam)
    e = exif_table(r)
    for t in ts:
        row = e.iloc[int(np.argmin(np.abs(e.t.to_numpy() - t)))]
        img = read_img_array_from_img(str(Path(img_path(r.folder_w)) / row["name"]), channel=0, rotation=0)
        with contextlib.redirect_stdout(io.StringIO()):
            s, _ = find_search_areas(img, 10, p)
        # oberste LED (kleinste Zeile) und Median-Spalte: nicht periodisch -> klaeren Alias-Verdacht der Lagepruefung
        print(f"{run} {cam} t {row.t:7.1f} s {row['name']}: {len(s)} Fundstellen (p {p}), Zeilen "
              f"{int(s[:, 1].min()) if len(s) else -1}-{int(s[:, 1].max()) if len(s) else -1}, Spalte Median "
              f"{np.median(s[:, 2]) if len(s) else -1:.0f}", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
