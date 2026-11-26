# -*- coding: utf-8 -*-
r"""Setup-Tabellen der H1-LEDSA-Auswertung mit LEDSA 0.13.0 (METHODS.md section 3.1) aus den belegten Quellen erzeugen.

Quellen (nur lesen):
  - Foto-Weitergabe H1 (photo_handover/ im Repo-Wurzelordner): serien.csv (Lauf, Zuendung, Serie, Kamera,
    Position), positionen.csv (Kameralage laut Labbook, pane_distance), led_streifen.csv (Streifen laut Labbook)
  - inventory/h1_exif_weitergabe.csv.gz  = Kopie von h1_exif_alle.csv der Foto-Weitergabe (ausserhalb des Repos) (EXIF je RAW der
    Weitergabe, BCL-Kameras + J3-FZJ-Auszug)
  - inventory/h1_exif_juelich.csv.gz     = EXIF der Juelich-Tagesserien J1-J3 unter <H1_IMAGES_ROOT>\2_juelichMeasurements
    (08.-10.12.; tools/juelich_exif.py, 2026-11-20), Dateiliste inventory/h1_files_juelich.tsv.gz
  - 1_Measurements/<Lauf>/1_Processed_data/<Lauf>_events.txt (Zuendung genau, Beginn Lueftung)

Umfang Stufe A (2026-11-20): die 14 Hep-Laeufe, nur F-Positionen (Kamera hinter der Scheibe in der Flurwand).
J1-J3 aus den Tagesserien (statt des FZJ-Auszugs, Bildzahlen gleich); J1 F3U, J2 F2U, J3 F1U laut positionen.csv.
Serie = zusammenhaengender Bildblock um die Zuendung (Luecke > GAP_SPLIT_S trennt; z. B. Einzelbild DSC_0331 von
Hep_160_S3_R2 C2 bei +5697 s faellt heraus), Reihenfolge nach EXIF-Zeit (nie nach Dateinamen: Zaehlerueberlauf).
Ausduennung (2026-11-20): Serien mit Median-Intervall < 1,5 s (J am 08.12., 0,99 s) jedes 5. Bild
(num_skip_imgs = 4), alle anderen voll.

Ausgabe (setup/, ueberschrieben; bricht bei fehlenden Eingaben ab):
  ledsa_h1_series.csv     je (Lauf, Kamera): Position, Raum, Ordner, Namensmuster, erste/letzte Bildnummer, Bildzahl,
                          Beginn/Ende [s], Intervall, num_skip_imgs, Belichtung
  ledsa_h1_positions.csv  Kameralagen Woche 2 (Labbook) mit pane_distance und Paper/FDS-x
  ledsa_h1_led_strips.csv Streifen je Raum mit Kanal (rot 0, gruen 1, blau 2) und Endpunkten (Labbook + Paper/FDS)
  ledsa_h1_runs.csv       je Lauf: Datum, start_time (volle Minute), Zuendung genau [s], Beginn Lueftung [s]
Aufruf: hh2-venv, python ledsa_h1_setup.py
"""
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent                        # 2_Analysis/LEDSA
REPO = HERE.parents[1]
WG = REPO / "photo_handover"                                  # Foto-Weitergabe H1 (Kopie im Repo)
# Rohbilder (nicht im Repo): folder_w beginnt mit dem Platzhalter <H1_IMAGES_ROOT>; die Leser ersetzen ihn durch die
# Umgebungsvariable H1_IMAGES_ROOT (ledsa_h1_paths.img_path)
from ledsa_h1_paths import IMG_TOKEN as IMG_ROOT                    # noqa: E402
W_MEAS = IMG_ROOT + r"\1_Measurements"
W_JUEL = IMG_ROOT + r"\2_juelichMeasurements"
GAP_SPLIT_S = 120.0
REF_S1_T = -30.0
# Abweichendes Referenzbild der LED-Suche (Zielzeit [s]), wenn das Bild bei <= -30 s verdeckt ist (Kontrollbild
# runs/<Lauf>/<Pos>_<Kamera>/s1scan.png) - Personen vor dem Streifen im Brandraum; Wahl per ledsa_h1_probe.py
# (gefundene LEDs je Zeitpunkt, Stufe 1, 2026-11-20):
#   Hep_160_S1_R2 J3: -115/-100 s 438, ab -80 s verdeckt (322/230/237)
#   Hep_160_S2_R3 J3: -122 s 422, -111 bis -15 s verdeckt (272-283), ab -3 s 438
#   Hep_220_S1_R4 J3: -220 bis -45 s 441-443, bei -33 s untere Enden verdeckt
#   Hep_160_S2_R3 C2: vor der Zuendung unruhig (318-1300 Fundstellen), +31 s 536, ab +200 s bis Ende 438 -> kritisch
#   Hep_220_S1_R1 J2: doppelte/verschmierte LED-Bilder bis ~+900 s (-30 s 470, +600 s 623, +1200 s 443), ab +1500 s
#     bis Ende 438 (2026-11-21) -> LED-Positionen aus dem sauberen Bild; Eignung der Serie in Stufe 3 pruefen
REF_S1_T_OVERRIDE = {("Hep_160_S1_R2", "J3"): -100.0, ("Hep_160_S2_R3", "J3"): -3.0,
                     ("Hep_220_S1_R4", "J3"): -60.0, ("Hep_160_S2_R3", "C2"): 200.0,
                     ("Hep_220_S1_R1", "J2"): 1600.0}
THIN_BELOW_S, THIN_SKIP = 1.5, 4
J_POS = {"camJ1": ("J1", "F3U"), "camJ2": ("J2", "F2U"), "camJ3": ("J3", "F1U")}
ROOM_STRIPS = {"F1": ["LED 1", "LED 1.1", "LED 1.2"], "F2": ["LED 3", "LED 3.1", "LED 3.2"],
               "F3": ["LED 5.1", "LED 5.2", "LED 5.3"]}
CHANNEL = {"R": 0, "G": 1, "B": 2}
JUELICH_N_LED, JUELICH_LED_PER_M = 144, 60.0


def need(p):
    if not Path(p).exists():
        raise SystemExit(f"[--] Eingabe fehlt: {p}")
    return p


def exif_time(df):
    # SubSec ist Text mit fuehrenden Nullen ("05" = 0,05 s); als Zahl gelesen wurde daraus 0,50 s (Korrektur
    # 2026-11-24; betraf nur t_first_s/ref_s1_t_s/dt_median_s/counter_wrap der Tabellen, nicht LEDSA)
    raw = df.subsec.astype("string").str.replace(r"\.0$", "", regex=True).fillna("0")
    sub = ("0." + raw).astype(float)
    return pd.to_datetime(df.dto, format="%Y:%m:%d %H:%M:%S") + pd.to_timedelta(sub, unit="s")


def block(g, z):
    """Zusammenhaengender Bildblock (Luecken > GAP_SPLIT_S trennen), der die Zuendung enthaelt oder ihr am naechsten ist."""
    g = g.sort_values("t").copy()
    g["rel"] = (g.t - z).dt.total_seconds()
    g["blk"] = np.concatenate([[0], np.cumsum(np.diff(g.rel.to_numpy()) > GAP_SPLIT_S)])
    b = g.loc[g.rel.abs().idxmin(), "blk"]
    near = g[g.blk == b]
    if not (near.rel.min() <= 0 <= near.rel.max()):
        b = g.groupby("blk").rel.apply(lambda r: max(r.min(), 0) - min(r.max(), 0)).abs().idxmin()
    return g[g.blk == b], g.blk.nunique() - 1


def series_row(run, cam, pos, folder, g, z):
    blk, n_other = block(g, z)
    m = blk.name.str.extract(r"^(.*?)(\d+)(\.\w+)$")
    if m.isna().any().any() or m[0].nunique() != 1 or m[2].nunique() != 1:
        raise SystemExit(f"[--] {run} {cam}: Dateinamen ohne einheitliches Muster: {blk.name.head(3).tolist()}")
    ids = m[1].astype(int).to_numpy()
    width = m[1].str.len().iloc[0]
    wrap = int((np.diff(ids) < 0).sum())
    first, last = int(ids[0]), int(ids[-1])
    n_range = (last - first) % 9999 + 1 if width == 4 else last - first + 1
    dt = np.diff(blk.rel.to_numpy())
    dt_med = float(np.median(dt))
    # Referenzbild der LED-Suche (-s1): letztes Bild mit t <= REF_S1_T (Aufbau abgeschlossen, noch kein Rauch; Stufe 0:
    # J1 Hep_220_S1_R1 wurde nach dem zehnten Bild bewegt), sonst das erste Bild der Serie
    pre = np.flatnonzero(blk.rel.to_numpy() <= REF_S1_T_OVERRIDE.get((run, cam), REF_S1_T))
    i_ref = int(pre[-1]) if len(pre) else 0
    exp = blk.groupby(["expo", "fnum", "iso"]).size().sort_values(ascending=False)
    return dict(run=run, cam=cam, position=pos, room=pos[:2], folder_w=folder,
                name_string=f"{m[0].iloc[0]}{{:0{width}d}}{m[2].iloc[0]}", first_id=first, last_id=last,
                ref_s1_id=int(ids[i_ref]), ref_s1_t_s=round(float(blk.rel.iloc[i_ref]), 2),
                n_img=len(blk), n_range=n_range, counter_wrap=wrap, other_blocks=n_other,
                t_first_s=round(blk.rel.min(), 2), t_last_s=round(blk.rel.max(), 2), dt_median_s=round(dt_med, 2),
                max_gap_s=round(float(dt.max()), 1), num_skip_imgs=THIN_SKIP if dt_med < THIN_BELOW_S else 0,
                exposure=f"1/{1 / exp.index[0][0]:.0f} s F{exp.index[0][1]:g} ISO{exp.index[0][2]:g}",
                n_exposures=len(exp), model=blk.model.iloc[0], serial=str(blk.serial.iloc[0]))


def runs_table(serien):
    rows = []
    for run, g in serien.groupby("lauf", sort=False):
        ev = need(REPO / "1_Measurements" / run / "1_Processed_data" / f"{run}_events.txt")
        txt = Path(ev).read_text(encoding="utf-8-sig")
        def ev_time(label):
            m = re.search(rf"\|\s*(-?[\d.]+)\s*\|\s*{label}\s*$", txt, re.M)
            return float(m.group(1)) if m else np.nan
        ref = re.search(r"Referenzzeit \(gerundet\): (\d\d)\.(\d\d)\.(\d{4}) (\d\d:\d\d:\d\d)", txt)
        date = f"{ref.group(3)}-{ref.group(2)}-{ref.group(1)}"
        if ref.group(4) != g.zuendung.iloc[0]:
            raise SystemExit(f"[--] {run}: Referenzzeit events {ref.group(4)} != serien.csv {g.zuendung.iloc[0]}")
        rows.append(dict(run=run, date=date, start_time=ref.group(4), ignition_s=ev_time("Zündung"),
                         # Hep_160_S3_R1_events.txt schreibt "Beinn Lüftung" (Tippfehler in der Quelle)
                         ventilation_s=ev_time("Beg?inn Lüftung"), fire_out_s=ev_time("Feuer aus")))
    d = pd.DataFrame(rows)
    if d.ventilation_s.isna().any():
        raise SystemExit(f"[--] ohne 'Beginn Lüftung': {d[d.ventilation_s.isna()].run.tolist()}")
    return d


def main():
    serien = pd.read_csv(need(WG / "serien.csv"), encoding="utf-8-sig")
    serien = serien[serien.lauf.str.startswith("Hep_")]
    runs = runs_table(serien)
    z_of = {r.run: pd.Timestamp(f"{r.date} {r.start_time}") for r in runs.itertuples()}

    ex_wg = pd.read_csv(need(HERE / "inventory" / "h1_exif_weitergabe.csv.gz"), dtype={"subsec": str})
    ex_wg = ex_wg[ex_wg["sub"].isna()].assign(t=lambda d: exif_time(d))
    rows = []
    # J3 am 09.12.: vollstaendige FZJ-Ordner der Weitergabe statt 2_juelichMeasurements (dort sind u. a. 7K7A7873/8636/
    # 9108.CR3 auf MiB-Grenzen abgeschnitten, FZJ-Kopie vollstaendig; Stufe 0, 2026-11-20)
    sel = serien[serien.position_paper.str.startswith("F") & (serien.kamera.isin(["C1", "C2", "C3"])
                                                            | (serien.serienordner == "FZJ"))]
    for r in sel.itertuples():
        g = ex_wg[(ex_wg.run == r.lauf) & (ex_wg.series == r.serienordner)]
        if g.empty:
            raise SystemExit(f"[--] keine EXIF-Zeilen fuer {r.lauf} {r.serienordner}")
        rows.append(series_row(r.lauf, r.kamera, r.position_paper,
                               f"{W_MEAS}\\{r.lauf}\\3_LEDSA\\{r.serienordner}", g, z_of[r.lauf]))

    ex_j = pd.read_csv(need(HERE / "inventory" / "h1_exif_juelich.csv.gz"), dtype={"subsec": str})
    if ex_j.err.notna().any():
        raise SystemExit("[--] EXIF-Lesefehler in h1_exif_juelich")
    ex_j = ex_j.assign(t=lambda d: exif_time(d))
    for run, z in z_of.items():
        for kam, (cam, pos) in J_POS.items():
            if any((x["run"] == run) and (x["cam"] == cam) for x in rows):
                continue                                   # J3 09.12. schon aus dem FZJ-Ordner
            g = ex_j[(ex_j.kamera == kam) & (ex_j.tag == z.strftime("%Y-%m-%d"))]
            rel = (g.t - z).dt.total_seconds()
            g = g[(rel > -1200) & (rel < 2700)]
            if len(g) < 50:
                continue
            day = z.strftime("%Y-%m-%d")
            rows.append(series_row(run, cam, pos, f"{W_JUEL}\\{day}\\{kam}", g, z))
    s = pd.DataFrame(rows).sort_values(["run", "room", "position", "cam"])
    s = s.merge(runs[["run", "date", "start_time"]], on="run")

    pos = pd.read_csv(need(WG / "positionen.csv"), encoding="utf-8-sig")
    pos = pos[(pos.woche == 2) & pos.position_paper.str.startswith("F")]
    pos = pos[["position_paper", "position_labbook", "raum", "x_m", "y_m", "z_m", "pane_distance_m",
               "pane_distance_min_m", "pane_distance_max_m", "x_paper_fds_m"]].rename(
        columns={"position_paper": "position", "raum": "room"})
    missing = set(s.position) - set(pos.position)
    if missing:
        raise SystemExit(f"[--] Positionen ohne Koordinaten: {missing}")

    led = pd.read_csv(need(WG / "led_streifen.csv"), encoding="utf-8-sig")
    led = led[led.woche.astype(str).str.contains("2")]
    out = []
    for room, names in ROOM_STRIPS.items():
        for i, nm in enumerate(names):
            q = led[led.led_labbook == nm]
            if len(q) != 1:
                raise SystemExit(f"[--] Streifen {nm}: {len(q)} Zeilen in led_streifen.csv (Woche 2)")
            q = q.iloc[0]
            z_bot = q.z_unten_m
            if q.herkunft.startswith("J"):
                # Juelich-Streifen (festgelegt 2026-11-24): 144 LEDs mit 60 LEDs/m (Teilung 1/60 m,
                # Bildauswertung 16,7-17,0 mm, geeicht am BCL-Streifen; Labbook 0,100-2,535 m ergaebe 17,0 mm und ist
                # mit den Bildern unvereinbar: unterste LED dort bei ~0,13-0,15 m). Oberste LED bei z_oben (2,535 m).
                z_bot = round(q.z_oben_m - (JUELICH_N_LED - 1) / JUELICH_LED_PER_M, 4)
            out.append(dict(room=room, array=i, led=nm, colour=q.farbe, channel=CHANNEL[q.farbe], origin=q.herkunft,
                            x_m=q.x_m, y_m=q.y_m, z_bottom_m=z_bot, z_top_m=q.z_oben_m,
                            z_bottom_paper_m=q.z_unten_paper_fds_m, z_top_paper_m=q.z_oben_paper_fds_m))
    strips = pd.DataFrame(out)
    if not (strips.array == strips.channel).all():
        raise SystemExit("[--] Array-Reihenfolge != Kanal (rot, gruen, blau erwartet)")

    for name, d, head in [
        ("ledsa_h1_series.csv", s, "Serien Stufe A (13 Hep-Laeufe, F-Positionen), aus EXIF; t relativ zu start_time"),
        ("ledsa_h1_positions.csv", pos, "Kameralagen Woche 2 laut Labbook (positionen.csv der Weitergabe)"),
        ("ledsa_h1_led_strips.csv", strips, "LED-Streifen Woche 2 je Raum, Array = Kanal (led_streifen.csv)"),
        ("ledsa_h1_runs.csv", runs, "Laeufe: start_time = volle Minute; Zuendung/Lueftung/Feuer aus aus _events.txt [s]")]:
        f = HERE / "setup" / name
        if d.empty:
            raise SystemExit(f"[--] {name}: keine Zeilen")
        with open(f, "w", encoding="utf-8", newline="") as fh:
            fh.write(f"# ledsa_h1_setup.py: {head}\n")
            d.to_csv(fh, index=False)
        print(f"[ok] {f} ({len(d)} Zeilen)")
    pd.set_option("display.width", 250)
    print(s[["run", "cam", "position", "first_id", "last_id", "n_img", "n_range", "counter_wrap", "other_blocks",
             "t_first_s", "t_last_s", "dt_median_s", "max_gap_s", "num_skip_imgs", "n_exposures"]].to_string(index=False))


if __name__ == "__main__":
    main()
