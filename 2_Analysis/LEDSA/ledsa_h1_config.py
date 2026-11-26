# -*- coding: utf-8 -*-
r"""LEDSA-0.13.0-Konfiguration der H1-Auswertung (METHODS.md), uebernommen aus der Hasenheide-2-Auswertung.

Quellen: setup/ledsa_h1_series.csv, _positions.csv, _led_strips.csv, _runs.csv (ledsa_h1_setup.py),
setup/ledsa_h1_strip_windows.csv (LED-Suche je Kamera, Vorschlag von ledsa_h1_s1scan.py, von Hand geprueft),
1_Measurements/<Lauf>/1_Processed_data/<Lauf>_processed.csv (LEM fuer das Referenzfenster).

Festlegungen (2026-11-20):
  - Zeit: start_time = volle Minute (wie Messdaten und Paper), exif_time_infront_real_time = 0 (kein belegter
    Uhrversatz), time_ref_img_* leer. LEDSA 0.13.0: Experiment_Time = (EXIF - Versatz) - start_time.
  - Geometrie: Kamera laut Labbook (x < 0, hinter der Scheibe) mit pane_distance (Mitte), Streifenenden BCL 0,055 bis
    2,535 m (Labbook), Juelich 0,1517 bis 2,535 m (oberste LED laut Labbook, 60 LEDs/m; Korrektur 2026-11-24, vorher
    Labbook 0,1 m), domain_bounds 0-2,535 m, 25 Schichten. LED-Hoehen je LED nach Index bei gleicher Teilung
    (ledsa_h1_ledz.py nach -coord); die End-Koordinaten in config.ini (edges) nutzt nur -coord, nicht -a/-as.
  - Kanaele: drei Streifen je Raum (rot BCL bzw. Juelich, gruen, blau) = Array 0/1/2 = Kanal 0/1/2 (Paper).
  - Hauptgroesse farbg_sum_col_val (farfield_distances 150 300), Nebengroesse sum_col_val, beide in einem -a-Lauf.
  - Inversion linear, lambda 0,5, 10 Referenzbilder, time_sync_tolerance 3 s (wie Paper und Hasenheide-2-Auswertung).
  - img_rotation = 0 (Sensorlage wie in der Hasenheide-2-Auswertung; jede Kamera im Kontrollbild von ledsa_h1_s1scan.py pruefen).
  - Ausduennung: num_skip_imgs aus der Serientabelle (J am 08.12. jedes 5. Bild).
  - Stapel: untere Kamera (BCL) zuerst -> Zeitachse des Stapels = Bilder der unteren Kamera.
Arbeitsordner: runs/<Lauf>/<Position>_<Kamera>/, Stapel runs/<Lauf>/stacked_<Raum>/.

Aufruf (Conda-Env ledsa, PYTHONPATH = LEDSA-Export v0.13.0):
  python ledsa_h1_config.py config <Lauf> <Kamera>      -> config.ini (fuer -s1/-s2/-coord/-s3_fast)
  python ledsa_h1_config.py edges <Lauf> <Kamera>       -> End-LEDs + 3D-Endpunkte in config.ini (nach -s1)
  python ledsa_h1_config.py analysis <Lauf> <Raum>      -> config_analysis.ini je Kamera (+ config_stacked.ini)
  python ledsa_h1_config.py rooms <Lauf>                -> Raeume des Laufs: Stapel bzw. Einzelkamera (Ausgabe fuer Skripte)
"""
import configparser
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from ledsa_h1_paths import img_path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RUNS = Path(os.environ.get("H1_LEDSA_RUNS", HERE / "runs"))
SETUP = HERE / "setup"

FARFIELD_DISTANCES = os.environ.get("H1_LEDSA_FARFIELD", "150 300")
REF_MAIN = "farbg_sum_col_val"
INVERSION = dict(solver="linear", lambda_reg=0.5, num_layers=25, domain_bounds="0.0 2.535",
                 reference_property=f"{REF_MAIN} sum_col_val", num_ref_images=10, camera_channels="0 1 2",
                 time_sync_tolerance=3)
SEARCH_RADIUS_DEFAULT, PERCENTILE_DEFAULT = 10, 99.875
NUM_CORES = 8

# Referenzbilder je Kamera nach ZEIT (Stufe 0, 2026-11-20; die Regel der Hasenheide-2-Auswertung "erste 20 Bilder, gleiche Bildnummern fuer
# alle Kameras" passt fuer H1 nicht: die Serien beginnen 2-8 min vor der Zuendung, in dieser Zeit aendert sich die
# Szene (Hep_220_S1_R1: J1 in den ersten ~2 min bis 34x heller, C1 Einbrueche auf ~0 und Drift 0,91-1,02), und gleiche
# Bildnummern sind bei C und J verschiedene Zeiten). Kandidaten: Bilder mit Fensterende - REF_LOOKBACK_S <= t <=
# Fensterende (Fensterende = erste LEM-Reaktion im Raum (k > REF_K_ONSET) - REF_MARGIN_S, hoechstens REF_MAX_S; ohne
# LEM im Raum 0 s). Groesse farbg_sum (sockelbereinigt), je Kanal; Basis = LED-Median ueber die Kandidaten; gueltig bei
# |rel - 1| <= REF_TOL und hoechstens REF_LED_FRAC der LEDs um > REF_LED_DEV daneben (Teilverdeckung), in allen drei
# Kanaelen. Gewaehlt: die letzten REF_N gueltigen (am naechsten an der Zuendung); < REF_MIN -> Rueckblick
# REF_LOOKBACK_MAX_S. Je Kamera eigene Liste (config_analysis.ini, im Stapel [simulation_N] ref_img_indices).
REF_N, REF_MIN, REF_TOL = 10, 5, 0.02
REF_LED_DEV, REF_LED_FRAC = 0.2, 0.02
REF_MARGIN_S, REF_MAX_S, REF_K_ONSET = 20.0, 20.0, 0.01
# LEM-Reaktion = erster Zeitpunkt, ab dem k REF_ONSET_HOLD_S Sekunden lang ununterbrochen > REF_K_ONSET (Korrektur
# 2026-11-24: Einzelwert war spikeempfindlich, z. B. Hep_160_S3_R1 F3 Basislinie 0,011-0,013 ab 3 s)
REF_ONSET_HOLD_S = 5
REF_LOOKBACK_S, REF_LOOKBACK_MAX_S = 120.0, 300.0
# Fensterende je Kamera abweichend (Stufe 3, 2026-11-23): Hep_160_S1_R2 J3 - Personen vor dem Streifen ab ~-80 s
# (ledsa_h1_probe.py, Stufe 1: -115/-100 s 438 Fundstellen, ab -80 s 322/230/237), Serie beginnt ~-124 s; mit dem
# Raumfenster (bis -4 s) sind die meisten Kandidaten verdeckt, der LED-Median verschoben, 0 gueltig. Bis -85 s: 5 gueltig
# (-115 bis -100 s) nach unveraenderter Regel.
REF_T_MAX_OVERRIDE = {("Hep_160_S1_R2", "J3"): -85.0}
# Kameras, die in der Hauptauswertung nicht in die Raum-Inversion eingehen (festgelegt 2026-11-24); die Auslese
# (Stufe 2) bleibt erhalten. Hep_160_S2_R3 C2: vor der Zuendung unruhig (farbg rel. 0,001-463, 0 gueltige
# Referenzbilder in 300 s; Stufe 1 sauber erst ab +200 s) -> F1 nur J3. Hep_160_S2_R1 C1: erstes Bild +30 s, kein Bild
# vor dem Rauch (Fenster bis +20 s, LEM F2 reagiert bei 48 s) -> F2 nur J2; Nebenvariante mit Referenzen ab +30 s nur nach
# Pruefung (Hoehenabdeckung J2, C1 frueh vs. spaet je Hoehe) und Festlegung.
# Hep_220_S1_R3 C3 (festgelegt 2026-11-25; Beleg checks/c3_r3_exclusion.py, METHODS.md section 4.6): ab ~250 s bis
# ~1450 s (Lueftung ~1202 s) deutlich weniger LED-Licht als R1/R2, bei 400-1000 s nur ~1/4-1/8 (eigene LEDs, Kanal 0-2, je Hoehenband R3/R1 bzw. R3/R2
# 0,12-0,27), annaehernd gleichmaessig ueber alle LED-Hoehen (C3 - J2, Median der Schichten 3-22, 400-1200 s: +0,30...+0,47 1/m;
# je Schicht bei 400/600/800 s +0,18...+0,65), danach voll zurueck; im Screening der 17 pruefbaren Zwei-Kamera-Raeume als gleichmaessige,
# anhaltende Stoerung ein Einzelfall -> Stoerung nahe der Kamera (Beschlag? oertlicher Rauch? ungeklaert); Nachfuehrung
# bis 1,51 px, Belichtung gleich -> F2 nur J2 (J2 R3 in 100-250 s und ab ~1050 s selbst auffaellig). Kriterium ohne LEM, post hoc formuliert (METHODS.md section 4.6);
# R3 F2 bleibt mit J2 (festgelegt 2026-11-25).
CAM_EXCLUDE = {("Hep_160_S2_R3", "C2"), ("Hep_160_S2_R1", "C1"), ("Hep_220_S1_R3", "C3")}
# Referenzfenster je Kamera fest vorgegeben (t_min, t_max, Mindestzahl), statt Rueckblick vom Raumfenster aus; Regel
# (+-2 %, <= 2 % der LEDs > 20 % daneben) unveraendert (festgelegt 2026-11-24):
# Hep_160_S2_R3 J3 - vor -5 s ~60 % der LEDs (alle unteren) verdeckt, voll sichtbar ab -3,25 s; oben/unten gleich bis
#   4,7 s, bei 8,7 s oben -1...-1,7 % (Rauch), LEM F1 ab 18 s -> -3,25/0,7/4,7 s.
# Hep_160_S2_R1 C1 (nur Nebenvariante "mitC1") - erstes Bild +30 s; oben/unten gleich bis 40 s (< 0,1 %), ab 45-50 s
#   oben dunkler -> 30,5/35,5/40,5 s.
REF_WINDOW_OVERRIDE = {("Hep_160_S2_R3", "J3"): (-4.0, 5.0, 3), ("Hep_160_S2_R1", "C1"): (30.0, 41.0, 3)}
# Nebenvarianten (Umgebungsvariable H1_VARIANT): nehmen ausgeschlossene Kameras wieder auf; Stapel und Maske bekommen
# den Variantennamen als Suffix (stacked_<Raum>_<Variante>, mask_<Raum>_<Variante>.csv.gz), die Hauptauswertung
# bleibt unberuehrt. "mitC1": Hep_160_S2_R1 F2 als Stapel C1 + J2 (festgelegt 2026-11-24).
VARIANT = os.environ.get("H1_VARIANT", "")
VARIANT_INCLUDE = {"mitC1": {("Hep_160_S2_R1", "C1")}}
if VARIANT and VARIANT not in VARIANT_INCLUDE:
    raise SystemExit(f"[--] unbekannte Variante H1_VARIANT={VARIANT}")


# Saettigung (festgelegt 2026-11-24): ein Kanal einer Serie ist ausgeschlossen, wenn in seinen Referenzbildern
# mehr als SAT_MAX_PCT % der LEDs gesaettigt sind (max_col_value >= 0,98 x 16383; inventory/ledsa_h1_saturation.csv aus
# ledsa_h1_stage4.py sat). Gesaettigte Referenz -> I_ref zu klein -> k zu klein (Stufe 4: J3 F1 Plateau/LEM gruen/blau
# 0,54-0,59 gegen rot 0,77-0,85). Je Raum und Kanal: beide Kameras frei -> Stapel; eine gesaettigt -> Einzelinversion
# der anderen (= Stapel aus dieser einen Kamera); keine frei -> Kanal entfaellt.
SAT_MAX_PCT = 5.0


def saturated():
    f = HERE / "inventory" / "ledsa_h1_saturation.csv"
    if not f.exists():
        raise SystemExit(f"[--] fehlt {f} (ledsa_h1_stage4.py sat)")
    d = pd.read_csv(f, comment="#")
    return {(r.run, r.cam, int(r.channel)) for r in d.itertuples() if r.sat_frac_pct > SAT_MAX_PCT}


def channel_source(run, room, ch, sat=None):
    """Hauptquelle eines Raums fuer Kanal ch: (Ordner, Maskenquelle, Kameras) oder None (alle Kameras gesaettigt)."""
    sat = saturated() if sat is None else sat
    cams = rooms(run)[room]
    ok = [c for c in cams if (run, c, ch) not in sat]
    if len(ok) == 2:
        return RUNS / run / stacked_name(room), stacked_name(room), "+".join(cams)
    if len(ok) == 1:
        return workdir(run, ok[0]), ok[0], ok[0]
    return None


def stacked_name(room):
    return f"stacked_{room}" + (f"_{VARIANT}" if VARIANT else "")


def mask_name(room):
    return f"mask_{room}" + (f"_{VARIANT}" if VARIANT else "") + ".csv.gz"


def _csv(name):
    f = SETUP / name
    if not f.exists():
        raise SystemExit(f"[--] fehlt: {f} (ledsa_h1_setup.py / ledsa_h1_s1scan.py)")
    return pd.read_csv(f, comment="#")


def series(run, cam):
    s = _csv("ledsa_h1_series.csv")
    r = s[(s.run == run) & (s.cam == cam)]
    if len(r) != 1:
        raise SystemExit(f"[--] {run} {cam}: {len(r)} Zeilen in ledsa_h1_series.csv")
    return r.iloc[0]


def workdir(run, cam):
    r = series(run, cam)
    return RUNS / run / f"{r.position}_{cam}"


def windows(run, cam, need_checked=True):
    w = _csv("ledsa_h1_strip_windows.csv")
    w = w[(w.run == run) & (w.cam == cam)].sort_values("array")
    if w.empty:
        raise SystemExit(f"[--] {run} {cam}: keine Zeilen in ledsa_h1_strip_windows.csv (ledsa_h1_s1scan.py)")
    if need_checked and not (w.status == "geprueft").all():
        raise SystemExit(f"[--] {run} {cam}: Streifenfenster nicht geprueft (status {w.status.unique().tolist()})")
    return w


def rooms(run):
    """{Raum: [Kameras]} des Laufs, untere Kamera zuerst (Stapel) bzw. eine Kamera (Einzelkamera-Raum)."""
    s = _csv("ledsa_h1_series.csv")
    s = s[s.run == run]
    excl = CAM_EXCLUDE - VARIANT_INCLUDE.get(VARIANT, set())
    s = s[[(run, c) not in excl for c in s.cam]]
    out = {}
    for room, g in s.groupby("room"):
        lo, up = g[g.position.str.endswith("L")].cam.tolist(), g[g.position.str.endswith("U")].cam.tolist()
        if len(lo) > 1 or len(up) > 1:
            raise SystemExit(f"[--] {run} {room}: mehrere Kameras je Hoehe {lo} {up}")
        out[room] = lo + up
    return out


def build(run, cam):
    from ledsa.core.ConfigData import ConfigData
    r = series(run, cam)
    try:
        w = windows(run, cam, need_checked=False)
        rad, pct = int(w.radius_px.iloc[0]), float(w.percentile.iloc[0])
    except SystemExit:
        rad, pct = SEARCH_RADIUS_DEFAULT, PERCENTILE_DEFAULT
    m = re.match(r"^(.*)\{:0(\d)d\}(\.\w+)$", r.name_string)
    if not m:
        raise SystemExit(f"[--] Namensmuster {r.name_string}")
    first, last = int(r.first_id), int(r.last_id)
    ref = int(r.ref_s1_id)            # Referenzbild der LED-Suche: letztes Bild bei t <= -30 s (ledsa_h1_setup.py)
    skip = int(os.environ.get("H1_NUM_SKIP_IMGS", r.num_skip_imgs))   # nur fuer Tests (Ausduennung voll/ausgeduennt)
    if skip != int(r.num_skip_imgs):
        print(f"  [!] num_skip_imgs {skip} statt {int(r.num_skip_imgs)} (H1_NUM_SKIP_IMGS, Test)")
    work = workdir(run, cam)
    work.mkdir(parents=True, exist_ok=True)
    date = pd.Timestamp(r.date)
    cwd = os.getcwd()
    os.chdir(work)
    try:
        cfg = ConfigData(load_config_file=False, img_directory=img_path(r.folder_w) + "\\", img_name_string=r.name_string,
                         num_img_overflow=9999, first_img_experiment_id=first, last_img_experiment_id=last,
                         num_cores=NUM_CORES, date=date.strftime("%d.%m.%Y"), start_time=r.start_time,
                         time_diff_to_image_time=0, img_rotation=0, farfield_distances=FARFIELD_DISTANCES,
                         ref_img_id=ref, search_area_radius=rad, channel="all", pixel_value_percentile=pct,
                         max_num_leds=1300, num_arrays=3, first_img_analysis_id=first, last_img_analysis_id=last,
                         num_skip_imgs=skip)
        cfg.save()
    finally:
        os.chdir(cwd)
    print(f"[ok] {work / 'config.ini'}: {r.name_string} {first}-{last} ({r.n_img} Bilder, Schritt "
          f"{skip + 1}), start_time {r.start_time}, Referenzbild {ref}, R {rad}, p {pct}")
    return work


def set_edges(run, cam):
    """End-LEDs je Streifen aus analysis/led_search_areas.csv (-s1) in den geprueften Fenstern, 3D-Endpunkte laut
    Labbook (setup/ledsa_h1_led_strips.csv). Pruefung: gefundene LEDs + Ausschluss <= LEDs im
    Streifen, sonst Abbruch (sonst werden die Hoehen gestaucht)."""
    r = series(run, cam)
    work = workdir(run, cam)
    w = windows(run, cam)
    sa = pd.read_csv(work / "analysis" / "led_search_areas.csv", comment="#", header=None, names=["id", "row", "col"])
    st = _csv("ledsa_h1_led_strips.csv")
    st = st[st.room == r.room].set_index("array")
    idx, coords, used = [], [], set()
    for q in w.itertuples():
        # Band um den Fit Spalte(Zeile) (ledsa_h1_s1scan.py; schraege/gekruemmte Streifen, Nachbarstreifen 24-44 px)
        col_fit = np.polyval([q.fit_c2, q.fit_c1, q.fit_c0], sa.row.to_numpy(float))
        s = sa[(sa.row >= q.row0) & (sa.row <= q.row1) & (np.abs(sa.col - col_fit) <= q.half_width_px)]
        if used & set(s.id):
            raise SystemExit(f"[--] {run} {cam}: Fenster von Array {q.array} ueberlappt ein anderes")
        used |= set(s.id)
        top, bot = s.loc[s.row.idxmin()], s.loc[s.row.idxmax()]
        p = st.loc[q.array]
        if p.led != q.led:
            raise SystemExit(f"[--] {run} {cam}: Array {q.array} ist {p.led}, Fenster nennt {q.led}")
        sk_t, sk_b, n_led = int(q.skip_top), int(q.skip_bottom), int(q.n_leds)
        if len(s) + sk_t + sk_b > n_led:
            raise SystemExit(f"[--] {run} {cam} {q.led}: {len(s)} gefunden + Ausschluss {sk_t}/{sk_b} > {n_led} LEDs "
                             f"im Streifen")
        if len(s) + sk_t + sk_b < n_led:
            print(f"  [!] {q.led}: {len(s)} gefunden + Ausschluss {sk_t}/{sk_b} < {n_led} -> Luecken im Streifen "
                  f"(nicht gefundene LEDs zwischen den Enden)")
        p_top = np.array([p.x_m, p.y_m, p.z_top_m], float)
        p_bot = np.array([p.x_m, p.y_m, p.z_bottom_m], float)
        if sk_t or sk_b:
            p_top, p_bot = (p_top + sk_t / (n_led - 1) * (p_bot - p_top), p_bot + sk_b / (n_led - 1) * (p_top - p_bot))
        idx.append(f"{int(top.id)} {int(bot.id)}")
        coords.append(" ".join(f"{v:.4f}" for v in (*p_top, *p_bot)))
        print(f"  Array {q.array} {q.led:8s} {len(s):4d} LEDs, oben ID {int(top.id)} (Zeile {top.row}), unten ID "
              f"{int(bot.id)} (Zeile {bot.row}), Ausschluss {sk_t}/{sk_b}, z {p_bot[2]:.4f}-{p_top[2]:.4f} m")
    txt = (work / "config.ini").read_text(encoding="utf-8")
    txt = re.sub(r"(led_array_edge_indices = ).*", lambda m: m.group(1) + "\n" + "\n".join(f"\t    {v}" for v in idx), txt)
    txt = re.sub(r"(led_array_edge_coordinates = ).*", lambda m: m.group(1) + "\n" + "\n".join(f"\t    {v}" for v in coords), txt)
    (work / "config.ini").write_text(txt, encoding="utf-8")
    print(f"[ok] Endpunkte in {work / 'config.ini'}")


def ref_window(run, room, margin=REF_MARGIN_S):
    """Ende des Referenzfensters [s]: erste LEM-Reaktion im Raum minus margin, hoechstens REF_MAX_S; ohne LEM 0 s."""
    f = REPO / "1_Measurements" / run / "1_Processed_data" / f"{run}_processed.csv"
    meas = pd.read_csv(f, comment="#", encoding="utf-8-sig")
    t = meas["Time (s)"].to_numpy(float)
    first = []
    for c in meas.columns:
        if re.match(rf"Extinction LEM_\d+_{room}_[\d.]+ \(1/m\)$", c):
            k = meas[c].to_numpy(float)
            above = pd.Series((t > 0) & (k > REF_K_ONSET)).rolling(REF_ONSET_HOLD_S).min().to_numpy() == 1
            i = np.flatnonzero(above)
            if len(i):
                first.append(t[i[0] - REF_ONSET_HOLD_S + 1])
    if not first:
        print(f"  Referenzfenster bis 0 s (keine LEM-Reaktion in {room})")
        return 0.0
    w = min(min(first) - margin, REF_MAX_S)
    print(f"  Referenzfenster bis {w:.0f} s (erste LEM-Reaktion in {room} bei {min(first):.0f} s)")
    return w


def select_ref_images(work, t_max, fixed=None):
    """Referenzbilder einer Kamera (img_id) nach Zeit, s. REF_*; braucht -s3 (Spalte farbg_sum = Spalte 5)."""
    info = pd.read_csv(work / "analysis" / "image_infos_analysis.csv")
    t = info.set_index(info.columns[0])[info.columns[3]]
    have = set.intersection(*[{int(f.name.split("_")[0]) for f in (work / "analysis" / f"channel{ch}").glob(
        "*_led_positions.csv")} for ch in (0, 1, 2)])        # von LEDSA uebersprungene (beschaedigte) Bilder fehlen
    ref_min = REF_MIN
    for look in ((None,) if fixed else (REF_LOOKBACK_S, REF_LOOKBACK_MAX_S)):
        if fixed:
            t_lo, t_max, ref_min = fixed
            look = t_max - t_lo
            print(f"  [!] {work.name}: festes Referenzfenster [{t_lo:.1f}, {t_max:.1f}] s, mindestens {ref_min} "
                  f"(REF_WINDOW_OVERRIDE)")
        cand = [i for i in t.index if t_max - look <= t[i] <= t_max and i in have]
        if not cand:
            print(f"  [!] {work.name}: keine Bilder in [{t_max - look:.0f}, {t_max:.0f}] s (erstes Bild bei "
                  f"{t.min():.0f} s)")
            sel = []
            continue
        ok_all = set(cand)
        for ch in (0, 1, 2):
            rows = []
            for i in cand:
                d = pd.read_csv(work / "analysis" / f"channel{ch}" / f"{i}_led_positions.csv", comment="#", header=None,
                                skipinitialspace=True)
                if d.shape[1] < 7:
                    raise SystemExit(f"[--] {work.name}: Schritt 3 ohne Fernfeld-Sockel")
                rows.append(d.set_index(0)[5].rename(i))
            s = pd.concat(rows, axis=1)
            # nur die LEDs des eigenen Streifens (Array = Kanal); die fremden Streifen sehen im Kanal nur Uebersprechen
            # (Korrektur 2026-11-24: vorher alle 438-450 LEDs bewertet)
            own = np.loadtxt(work / "analysis" / f"led_array_indices_{ch:03d}.csv", dtype=int, ndmin=1)
            s = s.loc[s.index.isin(own)]
            led_rel = s.div(s.median(axis=1), axis=0)
            rel, part = led_rel.median(), ((led_rel - 1).abs() > REF_LED_DEV).mean()
            ok = {i for i in cand if abs(rel[i] - 1) <= REF_TOL and part[i] <= REF_LED_FRAC}
            print(f"  {work.name} Kanal {ch}: {len(cand)} Bilder in [{t_max - look:.0f}, {t_max:.0f}] s, farbg rel. "
                  f"{rel.min():.3f}-{rel.max():.3f}, gueltig {len(ok)}")
            ok_all &= ok
        sel = sorted(ok_all)[-REF_N:]
        if len(sel) >= ref_min:
            break
        print(f"  [!] {work.name}: nur {len(sel)} gueltige Referenzbilder, Rueckblick {REF_LOOKBACK_MAX_S:.0f} s")
    if len(sel) < ref_min:
        raise SystemExit(f"[--] {work.name}: nur {len(sel)} gueltige Referenzbilder (< {ref_min})")
    print(f"  {work.name}: Referenzbilder {sel} (t {t[sel[0]]:.0f} bis {t[sel[-1]]:.0f} s)")
    return sel


def analysis_configs(run, room):
    from ledsa.analysis.ConfigDataAnalysis import ConfigDataAnalysis
    cams = rooms(run)[room]
    works = [workdir(run, c) for c in cams]
    t_max = ref_window(run, room)
    for cam in cams:
        if (run, cam) in REF_T_MAX_OVERRIDE:
            print(f"  [!] {cam}: Fensterende {REF_T_MAX_OVERRIDE[(run, cam)]:.0f} s statt {t_max:.0f} s (REF_T_MAX_OVERRIDE)")
    refs = {cam: " ".join(map(str, select_ref_images(work, REF_T_MAX_OVERRIDE.get((run, cam), t_max),
                                                     REF_WINDOW_OVERRIDE.get((run, cam)))))
            for cam, work in zip(cams, works)}
    pos = _csv("ledsa_h1_positions.csv").set_index("position")
    sims = []
    for cam, work in zip(cams, works):
        ref_str = refs[cam]
        p = pos.loc[series(run, cam).position]
        xyz = f"{p.x_m:g} {p.y_m:g} {p.z_m:g}"
        if VARIANT and (run, cam) not in VARIANT_INCLUDE[VARIANT]:
            # Variante: config_analysis.ini der Hauptauswertung nicht anfassen (Korrektur 2026-11-24); nur im Stapel verwenden
            sims.append((work, xyz, float(p.pane_distance_m), ref_str))
            continue
        cwd = os.getcwd()
        os.chdir(work)
        try:
            ConfigDataAnalysis(load_config_file=False, camera_position=xyz, num_layers=INVERSION["num_layers"],
                               domain_bounds=INVERSION["domain_bounds"], led_array_indices="0 1 2",
                               num_ref_images=INVERSION["num_ref_images"], ref_img_indices=ref_str,
                               camera_channels=INVERSION["camera_channels"], num_cores=NUM_CORES,
                               reference_property=INVERSION["reference_property"], solver=INVERSION["solver"],
                               lambda_reg=INVERSION["lambda_reg"], pane_distance=float(p.pane_distance_m)).save()
        finally:
            os.chdir(cwd)
        sims.append((work, xyz, float(p.pane_distance_m), ref_str))
    if len(sims) == 1:
        print(f"[ok] config_analysis.ini in {works[0].name} (Einzelkamera)")
        return
    st = RUNS / run / stacked_name(room)
    st.mkdir(parents=True, exist_ok=True)
    c = configparser.ConfigParser()
    c["DEFAULT"] = {k: str(INVERSION[k]) for k in ("solver", "lambda_reg", "num_layers", "domain_bounds",
                                                   "reference_property", "num_ref_images", "camera_channels",
                                                   "time_sync_tolerance")}
    c["DEFAULT"].update(num_cores="1", output_path=".")
    for i, (work, xyz, pane, rs) in enumerate(sims):
        c[f"simulation_{i}"] = {"path": str(work), "camera_position": xyz, "pane_distance": f"{pane:g}",
                                "ref_img_indices": rs}
    c["led_arrays"] = {str(j): " ".join(f"{i}:{j}" for i in range(len(sims))) for j in range(3)}
    with open(st / "config_stacked.ini", "w", encoding="utf-8") as fh:
        fh.write(f"# H1 {run} Raum {room}: gestapelte Inversion {' + '.join(cams)} (untere zuerst = Zeitachse; "
                 f"ledsa_h1_config.py)\n")
        c.write(fh)
    print(f"[ok] config_analysis.ini in {', '.join(w.name for w in works)}; {st / 'config_stacked.ini'}")


def print_varcams(run):
    """Kameras, die die gesetzte Variante (H1_VARIANT) in diesem Lauf neu aufnimmt (nur diese rechnet run_room.sh -a)."""
    print(" ".join(c for r, c in sorted(VARIANT_INCLUDE.get(VARIANT, set())) if r == run))


def print_rooms(run):
    for room, cams in rooms(run).items():
        print(room, " ".join(f"{series(run, c).position}_{c}" for c in cams))


if __name__ == "__main__":
    {"config": build, "edges": set_edges, "analysis": analysis_configs, "rooms": print_rooms,
     "varcams": print_varcams}[sys.argv[1]](*sys.argv[2:])
