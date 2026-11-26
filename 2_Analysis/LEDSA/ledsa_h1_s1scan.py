# -*- coding: utf-8 -*-
r"""LED-Suche (-s1) einer H1-Kamera vorab einstellen (uebernommen aus der Hasenheide-2-Auswertung, fuer drei Streifen je Raum).

1. Referenzbild wie ledsa_h1_config.build (ref_s1_id aus setup/ledsa_h1_series.csv: letztes Bild bei t <= -30 s), Bayer-Bild ungefiltert wie LEDSA -s1 mit
   channel = all (read_img_array_from_img), img_rotation 0; find_search_areas (identisch zu -s1) je Perzentil in PCTS.
2. Fundstellen zu Streifen verketten: zwei LEDs gehoeren zusammen, wenn sie entlang der Streifenrichtung hoechstens
   LINK_ALONG px und quer hoechstens LINK_ACROSS px auseinander liegen (Gruen und Blau haengen in H1 nur 2-3 cm
   nebeneinander; eine feste Querluecke wie in der Hasenheide-2-Auswertung wuerde sie zusammenlegen). Ketten mit >= MIN_LEDS Fundstellen.
3. Farbe je Kette: Mittel der Box-Summen (Radius R) in den Kanaelen 0/1/2 (read_channel_data_from_img);
   Farbe = Kanal mit dem groessten Anteil. Erwartet: je Raum ein roter, ein gruener, ein blauer Streifen
   (setup/ledsa_h1_led_strips.csv, Array = Kanal).
4. Vorschlag = kleinstes Perzentil mit genau drei Ketten verschiedener Farbe und wenigsten Fremdpunkten.
   Abstand der Ketten quer zum Streifen [px] wird ausgegeben (Fernfeld-Baender 150-300 px).
Ausgabe: Tabelle, Kontrollbild runs/<Lauf>/<Pos>_<Kamera>/s1scan.png, Zeilen in setup/ledsa_h1_strip_windows.csv
(status "vorschlag"; nach Ansicht des Kontrollbilds von Hand auf "geprueft" setzen; n_leds = erwartete LED-Zahl,
skip_top/skip_bottom = nicht gefundene End-LEDs).
Erwartete LED-Zahl je Streifen: BCL 150, Juelich 144 (fruehere 0.10.0-Stapel, stacked_results/report.md: "2 x 150 LEDs (300 total
for array 0) and 2 x 144 LEDs per array", F2 Hep_160_S4) - an den Fundzahlen pruefen.
Aufruf (Conda-Env ledsa, PYTHONPATH = LEDSA-Export): python ledsa_h1_s1scan.py <Lauf> <Kamera> [<Perzentil>]
"""
import contextlib
import io
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ledsa_h1_config import PERCENTILE_DEFAULT, SEARCH_RADIUS_DEFAULT, SETUP, series, workdir  # noqa: E402
from ledsa_h1_paths import img_path  # noqa: E402

SHIFT_MATCH_PX, SHIFT_WARN_PX = 15.0, 2.0


def shift_check(path_ref_pts, path, pct, rad, label):
    """Kameralage: LEDs im Pruefbild (gleiches Perzentil) gegen die Referenzlagen; mittlere Verschiebung der Paare
    naechster Nachbarn (<= SHIFT_MATCH_PX) und Anteil wiedergefundener Referenz-LEDs."""
    from ledsa.core.image_reading import read_img_array_from_img
    from ledsa.data_extraction.step_1_functions import find_search_areas
    img = read_img_array_from_img(str(path), channel=0, rotation=0)
    with contextlib.redirect_stdout(io.StringIO()):
        s, _ = find_search_areas(img, rad, pct)
    ref = path_ref_pts
    dist, j = cKDTree(s[:, 1:3]).query(ref[:, 1:3], distance_upper_bound=SHIFT_MATCH_PX)
    ok = np.isfinite(dist)
    d = s[j[ok], 1:3] - ref[ok, 1:3]
    dr, dc = (np.median(d[:, 0]), np.median(d[:, 1])) if ok.any() else (np.nan, np.nan)
    frac = ok.mean()
    warn = (not ok.any()) or frac < 0.9 or max(abs(dr), abs(dc)) > SHIFT_WARN_PX
    print(f"  Lage {label} ({path.name}): {100 * frac:.0f} % der Referenz-LEDs innerhalb {SHIFT_MATCH_PX:.0f} px, "
          f"Verschiebung Zeile {dr:+.1f} / Spalte {dc:+.1f} px" + ("  [!] Lage pruefen" if warn else ""))
    return dict(label=label, image=path.name, matched_pct=round(100 * frac, 1), d_row_px=dr, d_col_px=dc, warn=warn)

PCTS = (99.875, 99.9, 99.93, 99.95, 99.96, 99.97, 99.98, 99.985, 99.99)
LINK_ALONG, LINK_ACROSS = 60.0, 8.0
MIN_LEDS = 50
PAD = 25
HALF_WIDTH = 9       # halbe Breite des Streifenbands quer zum Fit [px] (Streifenabstand Gruen/Blau >= 24 px)
N_EXPECTED = {"BCL": 150, "Jülich": 144}
COLOUR = {0: "R", 1: "G", 2: "B"}


def chains(s, axis):
    """Fundstellen (id, row, col) zu Ketten verbinden; axis = Querachse (2 = Spalte bei senkrechten Streifen)."""
    along = 1 if axis == 2 else 2
    pts = np.c_[s[:, along] / LINK_ALONG, s[:, axis] / LINK_ACROSS]
    pairs = cKDTree(pts).query_pairs(1.0, p=np.inf, output_type="ndarray")
    from scipy.sparse import coo_matrix
    n = len(s)
    g = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(n, n)) if len(pairs) else coo_matrix((n, n))
    _, lab = connected_components(g, directed=False)
    out = [s[lab == k] for k in np.unique(lab)]
    return [c[np.argsort(c[:, along])] for c in out if len(c) >= MIN_LEDS]


def colour_of(c, chan_imgs, rad):
    sums = []
    for img in chan_imgs:
        v = [img[max(r - rad, 0):r + rad + 1, max(q - rad, 0):q + rad + 1].sum() for _, r, q in c.astype(int)]
        sums.append(np.median(v))
    sums = np.array(sums, float)
    frac = sums / sums.sum()
    return COLOUR[int(frac.argmax())], frac


def main(run, cam, pct_force=None):
    from ledsa.core.image_reading import read_channel_data_from_img, read_img_array_from_img
    from ledsa.data_extraction.step_1_functions import find_search_areas
    r = series(run, cam)
    ref = int(r.ref_s1_id)
    path = Path(img_path(r.folder_w)) / r.name_string.format(ref)
    rad = SEARCH_RADIUS_DEFAULT
    img = read_img_array_from_img(str(path), channel=0, rotation=0)
    chan = [read_channel_data_from_img(str(path), c, rotation=0).astype(float) for c in (0, 1, 2)]
    print(f"{run} {cam} ({r.position}): Referenzbild {path.name} (t {r.ref_s1_t_s:.0f} s), {img.shape}, "
          f"Suchradius {rad} px")
    strips = pd.read_csv(SETUP / "ledsa_h1_led_strips.csv", comment="#")
    strips = strips[strips.room == r.room].set_index("colour")
    pcts = (float(pct_force),) if pct_force else PCTS
    res = {}
    for p in pcts:
        with contextlib.redirect_stdout(io.StringIO()):
            s, thr = find_search_areas(img, rad, p)
        res[p] = (s, thr)
    s_hi = res[pcts[-1]][0]
    axis = 2 if np.ptp(s_hi[:, 1]) >= np.ptp(s_hi[:, 2]) else 1
    print(f"Streifen {'senkrecht' if axis == 2 else 'WAAGERECHT (Kamera gedreht? img_rotation pruefen)'}")
    best = None
    for p in pcts:
        s, thr = res[p]
        cs = chains(s, axis)
        desc = []
        for c in cs:
            col, frac = colour_of(c, chan, rad)
            along = 1 if axis == 2 else 2
            pitch = float(np.median(np.hypot(np.diff(c[:, 1]), np.diff(c[:, 2]))))
            fit = np.polyfit(c[:, along], c[:, axis], 2)        # Querlage ueber Laengslage (schraeg/gekruemmt)
            resid = float(np.abs(c[:, axis] - np.polyval(fit, c[:, along])).max())
            desc.append(dict(c=c, n=len(c), colour=col, frac=frac, pitch=pitch, fit=fit, resid=resid,
                             across=float(np.median(c[:, axis])),
                             rows=(int(c[:, 1].min()), int(c[:, 1].max())), cols=(int(c[:, 2].min()), int(c[:, 2].max()))))
        cols = sorted(d["colour"] for d in desc)
        ok = cols == ["B", "G", "R"]
        n_in = sum(d["n"] for d in desc)
        print(f"  p {p:7.3f}: Schwelle {thr:8.0f}, {len(s):5d} Fundstellen, Ketten "
              + ", ".join(f"{d['colour']} {d['n']} (quer {d['across']:.0f}, Abstand {d['pitch']:.1f}, "
                          f"Anteile {'/'.join(f'{v:.2f}' for v in d['frac'])})" for d in desc)
              + ("  <- passt" if ok else ""))
        if ok:
            dev = sum(abs(d["n"] - N_EXPECTED[strips.loc[d["colour"], "origin"]]) for d in desc)
            rank = (dev + len(s) - n_in, p)          # Abweichung von der erwarteten LED-Zahl + Fremdpunkte
            if best is None or rank < best[2]:
                best = (p, desc, rank)
    if best is None:
        print("[--] kein Perzentil liefert genau drei Streifen R/G/B; Kontrollbild ansehen, ggf. Perzentil angeben")
        p_show, desc = pcts[-1], []
    else:
        p_show, desc, rank = best
        across = sorted((d["across"], d["colour"]) for d in desc)
        print(f"\nVorschlag p {p_show} ({rank[0]} Fremdpunkte); Reihenfolge quer: "
              + " | ".join(f"{c} {a:.0f}" for a, c in across)
              + "; Abstaende quer [px]: " + ", ".join(f"{across[i + 1][0] - across[i][0]:.0f}" for i in range(len(across) - 1)))
        if axis != 2:
            raise SystemExit("[--] waagerechte Streifen: Fenster-Fit nur fuer senkrechte Streifen umgesetzt")
        gaps = [across[i + 1][0] - across[i][0] for i in range(len(across) - 1)]
        half = HALF_WIDTH
        if min(gaps) < 2 * half + 4:
            raise SystemExit(f"[--] Streifen zu nah ({min(gaps):.0f} px) fuer Halbbreite {half} px")
        pts = np.vstack([d["c"] for d in desc])
        checks = [shift_check(pts, Path(img_path(r.folder_w)) / r.name_string.format(int(i)), p_show, rad, lab)
                  for lab, i in (("erstes Bild", r.first_id), ("letztes Bild", r.last_id))]
        shift_note = "; ".join(f"{c['label']} {c['matched_pct']:.0f} % / {c['d_row_px']:+.1f} / {c['d_col_px']:+.1f} px"
                               for c in checks)
        rows = []
        for d in sorted(desc, key=lambda d: strips.loc[d["colour"], "array"]):
            q = strips.loc[d["colour"]]
            n_exp = N_EXPECTED[q["origin"]]
            arr = int(q["array"])                    # q.array waere die pandas-Eigenschaft Series.array
            rows.append(dict(run=run, cam=cam, array=arr, led=q["led"], colour=d["colour"], percentile=p_show,
                             radius_px=rad, row0=d["rows"][0] - PAD, row1=d["rows"][1] + PAD,
                             col0=d["cols"][0] - PAD, col1=d["cols"][1] + PAD,
                             fit_c2=d["fit"][0], fit_c1=d["fit"][1], fit_c0=d["fit"][2], half_width_px=half,
                             fit_resid_px=round(d["resid"], 1), n_found=d["n"], n_leds=n_exp,
                             skip_top=0, skip_bottom=0, pitch_px=round(d["pitch"], 1), across_px=round(d["across"]),
                             ref_img=path.name, lage=shift_note,
                             lage_warn=any(c["warn"] for c in checks), status="vorschlag", note=""))
            flag = "" if d["n"] == n_exp else f"  [!] {d['n']} gefunden, erwartet {n_exp}"
            print(f"  Array {arr} {q['led']:8s} {d['colour']}: {d['n']} LEDs, Zeilen {d['rows']}, Spalten {d['cols']}, "
                  f"Fit-Rest max {d['resid']:.1f} px{flag}")
            if d["resid"] > half / 2:
                print(f"  [!] Fit-Rest {d['resid']:.1f} px > halbe Bandbreite/2 -> Kontrollbild pruefen")
        part = os.environ.get("H1_WINDOWS_PART")       # Parallelbetrieb (tools/scan_all.sh): eigene Teildatei
        f = SETUP / (f"ledsa_h1_strip_windows_part{part}.csv" if part else "ledsa_h1_strip_windows.csv")
        old = pd.read_csv(f, comment="#") if f.exists() else pd.DataFrame()
        if len(old):
            old = old[~((old.run == run) & (old.cam == cam))]
        new = pd.concat([old, pd.DataFrame(rows)], ignore_index=True).sort_values(["run", "cam", "array"])
        with open(f, "w", encoding="utf-8", newline="") as fh:
            fh.write("# ledsa_h1_s1scan.py: Streifenfenster je Kamera (Vorschlag; status 'geprueft' nach Ansicht von "
                     "s1scan.png); n_leds erwartet, skip_* = nicht gefundene End-LEDs\n")
            new.to_csv(fh, index=False)
        print(f"[ok] {f}")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    s = res[p_show][0]
    fig, ax = plt.subplots(figsize=(10, 7))
    v = img.astype(float)
    lo = np.percentile(v[v > 0], 50)
    ax.imshow(np.log1p(np.clip(v - lo, 0, None)), cmap="gray")
    ax.plot(s[:, 2], s[:, 1], ".", color="w", ms=1)
    for d in desc:
        ax.plot(d["c"][:, 2], d["c"][:, 1], ".", ms=2, color={"R": "r", "G": "lime", "B": "deepskyblue"}[d["colour"]])
        ax.text(d["cols"][1] + 30, d["rows"][0], f"{d['colour']} {d['n']}", color="y", fontsize=8)
    ax.text(0.01, 0.99, f"{run} {cam} {r.position}: p {p_show}, {len(s)} Fundstellen", transform=ax.transAxes,
            va="top", color="y")
    work = workdir(run, cam)
    work.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(work / "s1scan.png", dpi=110)
    print(f"[ok] {work / 's1scan.png'}")


if __name__ == "__main__":
    main(*sys.argv[1:])
