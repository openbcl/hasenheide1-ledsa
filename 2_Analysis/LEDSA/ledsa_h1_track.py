# -*- coding: utf-8 -*-
r"""Bewegungskorrektur fuer LEDSA-Schritt 3 (H1): LEDs bildweise verfolgen und mit LEDSAs eigener Auslese neu
extrahieren. Uebernommen aus der Hasenheide-2-Auswertung (Verfahren und Begruendung dort); Anlass Stufe 0 (2026-11-20): J1 schwenkt
in Hep_220_S1_R1 bis ~190 px quer (ledsa_h1_drift.py), C1 einige px.

Verfahren je Bild, vom Analysebild naechst dem Referenzbild der LED-Suche vorwaerts und rueckwaerts (Reihenfolge =
image_infos_analysis.csv, also Aufnahmefolge auch ueber Zaehlerueberlaeufe):
  1. Summe der drei Kanalbilder (ImageChannels, Bayer-Luecken je Kanal 0) mit 5x5-Mittel glaetten.
  2. Globale Verschiebung gegenueber den Positionen des Vorbilds: quer +-SHIFT_MAX (H1: Nachbarstreifen 24-44 px
     daneben -> kleiner als in der Hasenheide-2-Auswertung mit 26 px, sonst Sprung auf den Nachbarstreifen), laengs +-SHIFT_ALONG (< halber
     LED-Abstand 18-20 px); Kriterium = Summe der geglaetteten Werte an allen LED-Positionen.
  3. Laengsanker unteres Streifenende (wie in der Hasenheide-2-Auswertung), nur wenn alle Streifen uebereinstimmen.
  4. Jede LED auf das Maximum im Umkreis +-REFINE px nachruecken, wenn sie sich abhebt (> PEAK_FACTOR x Median der
     Umgebung); nicht gefundene LEDs folgen der mittleren Nachrueckung ihres Streifens.
  5. LEDSA generate_analysis_data(...) mit den bildweisen Positionen fuer alle drei Kanaele (gleiche Box und
     Fernfeld-Sockel wie -s3_fast) -> analysis/channel<k>/<id>_led_positions.csv; die unkorrigierte Auslese wird nach
     analysis/channel<k>_feste_positionen verschoben. Positionen je Bild: analysis/tracked_positions.csv.gz, Protokoll
     analysis/tracking_log.csv.
Aufruf (im Arbeitsordner, Conda-Env ledsa, PYTHONPATH = LEDSA-Export): python ledsa_h1_track.py
"""
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.ndimage import uniform_filter

from ledsa.core.ConfigData import ConfigData
from ledsa.core.image_reading import ImageChannels
from ledsa.data_extraction.step_3_functions import create_fit_result_file, generate_analysis_data

from ledsa_h1_paths import img_path

CHANNELS = (0, 1, 2)
SHIFT_MAX = 12
SHIFT_ALONG = 6
REFINE = 3
PEAK_FACTOR = 4.0
PAD = 40


def strip_end(a, rc, half_col=6, reach=90):
    r, c = int(round(rc[0])), int(round(rc[1]))
    r0 = max(r - reach, 0)
    win = a[r0:r + reach, max(c - half_col, 0):c + half_col + 1]
    if win.size == 0:
        return np.nan
    prof = uniform_filter(win, size=3).max(axis=1)
    thr = 0.25 * np.percentile(prof, 95)
    on = np.nonzero(prof > thr)[0]
    return float(on.max() + r0) if len(on) and np.percentile(prof, 95) > 500 else np.nan


def main():
    conf = ConfigData()
    img_dir = Path(img_path(conf["DEFAULT"]["img_directory"]))
    name = conf["DEFAULT"]["img_name_string"]
    ref_file = int(conf["find_search_areas"]["ref_img_id"])
    rot = conf.get("DEFAULT", "img_rotation")

    def read(fname):
        ic = ImageChannels(str(img_dir / fname), rotation=rot)
        a = sum(ic.channel_data_and_mask(c)[0].astype(np.float32) for c in CHANNELS)
        return a, ic

    sa = np.loadtxt(os.path.join("analysis", "led_search_areas.csv"), delimiter=",", dtype=int)
    lines = [np.loadtxt(os.path.join("analysis", f), dtype=int, ndmin=1).tolist()
             for f in sorted(os.listdir("analysis")) if f.startswith("led_array_indices_")]
    leds = np.array(sorted({i for l in lines for i in l}))
    info = pd.read_csv(os.path.join("analysis", "image_infos_analysis.csv"))
    info.columns = ["img_id", "name", "time", "t_exp"]
    ref_name = name.format(ref_file)
    t_ref = None
    infos = pd.read_csv("image_infos.csv")
    infos.columns = ["count", "name", "time", "t_exp"]
    if (infos.name == ref_name).any():
        t_ref = float(infos.loc[infos.name == ref_name, "t_exp"].iloc[0])
    k0 = int(np.argmin(np.abs(info.t_exp.to_numpy() - t_ref))) if t_ref is not None else 0
    order = list(range(k0, len(info))) + list(range(k0 - 1, -1, -1))
    print(f"Start: Analysebild {info.img_id[k0]} ({info.name[k0]}, t {info.t_exp[k0]:.1f} s), Referenzbild der "
          f"LED-Suche {ref_name} (t {t_ref} s)", flush=True)

    pos0 = sa[leds][:, 1:3].astype(float)
    for c in CHANNELS:
        src, bak = Path("analysis") / f"channel{c}", Path("analysis") / f"channel{c}_feste_positionen"
        if src.exists() and not bak.exists():
            shutil.move(str(src), str(bak))
        src.mkdir(exist_ok=True)
    # Nur Bilder ueberspringen, die LEDSA -s3 selbst verworfen hat (fehlen in der festen Auslese, z. B. abgeschnittene
    # Juelich-RAWs); jeder andere Lesefehler bricht ab (2026-11-23: ein Ausfall der Bildablage wurde sonst als Luecke uebergangen)
    have = {int(f.name.split("_")[0]) for f in (Path("analysis") / "channel0_feste_positionen").glob("*_led_positions.csv")}
    if not have:
        raise SystemExit("[--] keine feste Auslese in analysis/channel0_feste_positionen (erst -s3_fast -rgb)")
    strip_idx = [np.searchsorted(leds, l) for l in lines]
    bottom_idx = [ii[np.argmax(pos0[ii, 0])] for ii in strip_idx]
    pitch = [float(np.median(np.abs(np.diff(np.sort(pos0[ii, 0]))))) for ii in strip_idx]
    ref_img = read(ref_name)[0]
    end_off = [strip_end(ref_img, pos0[jb]) - pos0[jb, 0] for jb in bottom_idx]
    print("Laengsanker: LED-Abstand", [round(p, 1) for p in pitch], "px, Ende - unterste LED im Referenzbild",
          [round(v, 1) for v in end_off], "px", flush=True)
    positions, log, prev, skipped = {}, [], None, []
    for n, k in enumerate(order):
        start = pos0 if (k == k0 or k == k0 - 1) else prev
        if int(info.img_id[k]) not in have:   # von LEDSA -s3 verworfen: ueberspringen, Lage weiterreichen
            print(f"[!] {info.name[k]} von LEDSA -s3 verworfen, uebersprungen", flush=True)
            skipped.append(info.name[k])
            prev = start
            continue
        try:
            a, ic = read(info.name[k])
        except Exception as e:
            raise SystemExit(f"[--] {info.name[k]} nicht lesbar ({type(e).__name__}: {e}); Abbruch (Bildablage unter H1_IMAGES_ROOT pruefen)")
        r0, r1 = max(int(start[:, 0].min()) - PAD, 0), int(start[:, 0].max()) + PAD
        c0, c1 = max(int(start[:, 1].min()) - PAD, 0), int(start[:, 1].max()) + PAD
        sm = uniform_filter(a[r0:r1, c0:c1], size=5)
        rr, cc = start[:, 0].round().astype(int) - r0, start[:, 1].round().astype(int) - c0

        def score(dy, dx):
            y, x = np.clip(rr + dy, 0, sm.shape[0] - 1), np.clip(cc + dx, 0, sm.shape[1] - 1)
            return float(sm[y, x].sum())
        grid = [(dy, dx) for dy in range(-SHIFT_ALONG, SHIFT_ALONG + 1) for dx in range(-SHIFT_MAX, SHIFT_MAX + 1, 2)]
        best = max(grid, key=lambda s: score(*s))
        best = max([(best[0], best[1] + d) for d in range(-2, 3)], key=lambda s: score(*s))
        pred = start + np.array(best, float)
        corrs = []
        for kk, jb in enumerate(bottom_idx):
            e = strip_end(a, pred[jb])
            corrs.append((e - end_off[kk]) - pred[jb, 0] if np.isfinite(e) and np.isfinite(end_off[kk]) else np.nan)
        corrs = np.array(corrs)
        anchor = np.nan
        if np.isfinite(corrs).all() and np.ptp(corrs) < 6 and abs(corrs.mean()) <= 1.5 * min(pitch):
            anchor = float(corrs.mean())
            pred[:, 0] += anchor
        new = pred.copy()
        ok = np.zeros(len(leds), bool)
        for j in range(len(leds)):
            y, x = int(round(pred[j, 0])) - r0, int(round(pred[j, 1])) - c0
            w = sm[max(y - REFINE, 0):y + REFINE + 1, max(x - REFINE, 0):x + REFINE + 1]
            if w.size == 0:
                continue
            env = sm[max(y - 3 * REFINE, 0):y + 3 * REFINE + 1, max(x - 3 * REFINE, 0):x + 3 * REFINE + 1]
            if w.max() > PEAK_FACTOR * max(np.median(env), 1.0):
                dy, dx = np.unravel_index(np.argmax(w), w.shape)
                new[j] = (max(y - REFINE, 0) + dy + r0, max(x - REFINE, 0) + dx + c0)
                ok[j] = True
        for line in lines:
            jj = np.searchsorted(leds, line)
            if ok[jj].any() and (~ok[jj]).any():
                new[jj[~ok[jj]]] = pred[jj[~ok[jj]]] + np.median(new[jj[ok[jj]]] - pred[jj[ok[jj]]], axis=0)
        prev = new
        img_id = int(info.img_id[k])
        positions[img_id] = new
        sa_f = sa.copy()
        sa_f[leds, 1:3] = np.round(new).astype(int)
        for c in CHANNELS:
            data = generate_analysis_data(info.name[k], c, sa_f, lines, conf, fit_leds=False, img_channels=ic)
            create_fit_result_file(data, img_id, c)
        shift = new.mean(0) - pos0.mean(0)
        log.append((info.name[k], img_id, float(info.t_exp[k]), best[0], best[1], anchor, shift[0], shift[1],
                    ok.mean()))
        if n % 50 == 0:
            print(f"{n:4d}/{len(order)} {info.name[k]} (t {info.t_exp[k]:.0f} s): Schritt ({best[0]:+d},{best[1]:+d}) px, "
                  f"gesamt ({shift[0]:+.1f},{shift[1]:+.1f}) px, nachgerueckt {ok.sum()}/{len(leds)}", flush=True)
    rows = [(i, int(leds[j]), *positions[i][j]) for i in sorted(positions) for j in range(len(leds))]
    pd.DataFrame(rows, columns=["img_id", "led_id", "row", "col"]).to_csv(
        os.path.join("analysis", "tracked_positions.csv.gz"), index=False, float_format="%.0f")
    pd.DataFrame(log, columns=["name", "img_id", "t_exp", "step_dy", "step_dx", "anchor_row", "shift_row", "shift_col",
                               "frac_refined"]).sort_values("img_id").to_csv(
        os.path.join("analysis", "tracking_log.csv"), index=False, float_format="%.3f")
    print(f"[ok] analysis/tracked_positions.csv.gz, analysis/tracking_log.csv; uebersprungen {len(skipped)}"
          f"{': ' + ', '.join(skipped) if skipped else ''}", flush=True)


if __name__ == "__main__":
    main()
