# -*- coding: utf-8 -*-
r"""LEDSA-0.13.0-Auswertung der Kameras auf der langen Sichtachse (H1): N1 an L2 (Raum F3, 7 Hep-Laeufe) und J4 an L1
(Flur FC, nur Hep_160_S2_R2; gesperrt, la_post.EXCLUDED); beide sehen die gruenen BCL-Streifen LED 4 (Suedwand F2,
y 4,44 m) und LED 2 (Suedwand F1, y 0). Ausgewertet 2026-11-26/27 (METHODS.md, Abschnitt "Long-axis camera").

Methode wie die Raumauswertung (METHODS.md; deren Module werden nur importiert, nicht geaendert),
mit diesen Abweichungen (je begruendet):
  - zwei Streifen, beide gruen: Array 0 = LED 4 (naeher), Array 1 = LED 2 (ferner), ausgewertet nur Kanal 1;
    Zuordnung im Bild ueber die LED-Teilung in px (naeherer Streifen = groessere Teilung).
  - Einzelkamera, kein Stapel; der Sichtstrahl laeuft durch F3, FC, F2 (und F1 fuer LED 2) -> k(z) ist ein
    weglaengengewichtetes Mittel ueber mehrere Raeume, keine Raumgroesse. Kein pane_distance (Labbook: keiner; N1 stand in
    einem Schutzkasten, Scheibenabstand nicht belegt -> 0; bei 9-14 m Weg vernachlaessigbar, nicht geprueft).
  - Referenzfenster: endet 20 s vor der ersten LEM-Reaktion in IRGENDEINEM Raum F1-F3 (Strahl kreuzt alle), hoechstens
    +20 s; Auswahl der Referenzbilder wie ledsa_h1_config.select_ref_images, aber nur Kanal 1 und Arrays 0/1.
  - LED-Suche: Referenzbild der Suche = spaetestes Kandidatenbild vor -30 s mit (fast) allen LEDs (Personen im Bild,
    z. B. Hep_220_S1_R1 N1 bei -14 s); Suchradius je Kamera nach der Teilung des ferneren Streifens.
  - Teilweise sichtbare Streifen: nicht gefundene End-LEDs werden aus der Zahl der Teilungen bestimmt (Luecken und
    Doppelfunde aus der oertlichen Teilung); welches Ende fehlt, steht in END_HIDDEN (Beleg dort), je Serie
    abweichend in SKIP_END; die Horizont-Probe wird je Serie als Pruefung ausgegeben.
  - Maske: N1 (Nikon D610) hat kein optisches Schwarz -> Kriterium U_B wie B4 in der Hasenheide-2-Auswertung
    (hasenheide2-ledsa METHODS.md section 6.2): Strahl ungueltig, wenn farbg <= 0 oder U_B (P/S + P0/S0) > 0,1 bei
    b > 0,1, U_B = 0,2; J4 (optisches Schwarz vorhanden?) zusaetzlich SNR 3 wie die Raumauswertung, falls vorhanden.
  - FDS entfaellt (Twin-Caches decken nur die F-Raeume ab; Z: nicht verfuegbar).

Aufruf (Conda-Env ledsa, PYTHONPATH = LEDSA-Export v0.13.0; H1_IMAGES_ROOT gesetzt):
  python la.py setup                 -> setup/la_series.csv, la_strips.csv, la_positions.csv
  python la.py scan <Lauf> <Kamera>  -> setup/la_windows.csv (Zeile je Array), runs/<Lauf>/<Pos>_<Kamera>/s1scan.png
  python la.py config <Lauf> <Kamera>
  python la.py edges <Lauf> <Kamera>   (nach -s1)
  python la.py ledz <Lauf> <Kamera>    (nach -coord)
  python la.py analysis <Lauf> <Kamera> (nach -s3_fast -rgb)
  python la.py noise <Lauf> <Kamera>   (Leserauschen, falls optisches Schwarz)
  python la.py mask <Lauf> <Kamera>    (nach -a)
"""
import configparser
import contextlib
import io
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

LA = Path(__file__).resolve().parents[1]
# Raumauswertung (2_Analysis/LEDSA); Standard: dieser Ordner liegt als long_axis/ darin. H1_IMAGES_ROOT: Rohbilder.
REPO_LEDSA = Path(os.environ.get("H1_LEDSA_REPO", Path(__file__).resolve().parents[2]))
REPO = REPO_LEDSA.parents[1]
sys.path.insert(0, str(REPO_LEDSA))
SETUP, RUNS = LA / "setup", LA / "runs"

from ledsa_h1_paths import IMG_TOKEN, img_path                  # noqa: E402

N_LED = 150                     # BCL-Streifen 150 LEDs, Teilung 1/60 m (Raumauswertung: BCL LED 1/3 n_leds 150;
                                # hasenheide2-ledsa METHODS.md: BCL-Gruen LED 2.1 "gerade" 150 LEDs; Juelich 144)
STRIPS = {0: "LED 4", 1: "LED 2"}
CH = 1
CAMS = {"N1": dict(position="L2", radius=7), "J4": dict(position="L1", radius=5)}
REF_S1_T = -30.0
POSE_PX = 5.0
PCTS = (99.875, 99.9, 99.93, 99.95, 99.96, 99.97, 99.98)
HALF_WIDTH = 9
PAD = 25
GAP_FACTOR = 1.5
FARFIELD_DISTANCES = "150 300"
INVERSION = dict(solver="linear", lambda_reg=0.5, num_layers=25, domain_bounds="0.0 2.535",
                 reference_property="farbg_sum_col_val sum_col_val", num_ref_images=10, camera_channels=str(CH))
NUM_CORES = 8
REF_N, REF_MIN, REF_TOL, REF_LED_DEV, REF_LED_FRAC = 10, 5, 0.02, 0.2, 0.02
REF_MARGIN_S, REF_MAX_S, REF_K_ONSET, REF_ONSET_HOLD_S = 20.0, 20.0, 0.01, 5
REF_LOOKBACK_S, REF_LOOKBACK_MAX_S = 120.0, 300.0
# Nicht gefundene End-LEDs je Kamera und Array (festgelegt 2026-11-26, zweite Fassung):
#   N1: LED 4 (Array 0) oben 3 verdeckt, unten vollstaendig; LED 2 (Array 1) unten 9 verdeckt, oben vollstaendig.
#       Beleg: Horizont-Probe (horizon_skips) nach Entfernen der Doppelfunde: mit "LED 4 unten vollstaendig" folgen an
#       LED 2 8,6-9,7 unten fehlende LEDs bei beobachtet 9 (Hep_220_S1_R1/R3, Hep_160_S3_R1; R2 im Zwischenstand), die Gegenannahme
#       "LED 4 unten 3 fehlend" ergaebe 13-14. (Erste Fassung "alles unten" beruhte auf "150 LEDs" in Hep_220_S1_R2 N1;
#       das waren 147 LEDs + 3 Doppelfunde.) Bei Teilsicht von LED 2 (Hep_160_S2_R2/S2_R3/S3_R2) ist die Probe nicht
#       auswertbar -> dieselbe Festlegung (gleiche Kameraposition L2, gleiche Streifen).
#   J4: LED 4 vollstaendig (150); LED 2 am oberen Ende verankert (unverdeckte Bilder -92/-60/100 s: beide Streifen
#       vollstaendig, je 150; die Verdeckung im Suchbild bei -31 s war ein Gegenstand/eine Person vor der Zuendung).
#       J4 ist gesperrt (la_post.EXCLUDED): die Bildgeometrie ergibt eine Kamerahoehe von ~0,23 m gegen 0,686 m laut
#       Positionstabelle, nicht aufklaerbar (METHODS.md).
END_HIDDEN = {"N1": {0: "top", 1: "bottom"}, "J4": {0: "bottom", 1: "bottom"}}
# Abweichungen je Serie von Hand: (Lauf, Kamera) -> (unten fehlend Array 0, Array 1); Rest oben.
SKIP_END = {}
U_B, U_B_SENS, B_MIN, DB_MAX, W_MAX = 0.2, (0.1, 0.2, 0.3), 0.1, 0.1, 0.5
SNR_MIN = 3.0
FULL, SAT_FRAC = 16383, 0.98


def _csv(name):
    f = SETUP / name
    if not f.exists():
        raise SystemExit(f"[--] fehlt {f}")
    return pd.read_csv(f, comment="#")


def _write(name, d, head):
    SETUP.mkdir(parents=True, exist_ok=True)
    with open(SETUP / name, "w", encoding="utf-8", newline="") as fh:
        fh.write(f"# la.py: {head}\n")
        d.to_csv(fh, index=False)
    print(f"[ok] {SETUP / name} ({len(d)} Zeilen)")


def series(run, cam):
    s = _csv("la_series.csv")
    r = s[(s.run == run) & (s.cam == cam)]
    if len(r) != 1:
        raise SystemExit(f"[--] {run} {cam}: {len(r)} Zeilen in la_series.csv")
    return r.iloc[0]


def workdir(run, cam):
    return RUNS / run / f"{series(run, cam).position}_{cam}"


# ---------------------------------------------------------------- setup
def setup():
    import ledsa_h1_setup as su
    wg = REPO / "photo_handover"
    serien = pd.read_csv(wg / "serien.csv", encoding="utf-8-sig")
    serien = serien[serien.lauf.str.startswith("Hep_") & serien.kamera.isin(list(CAMS))]
    runs = pd.read_csv(REPO_LEDSA / "setup" / "ledsa_h1_runs.csv", comment="#").set_index("run")
    ex = pd.read_csv(REPO_LEDSA / "inventory" / "h1_exif_weitergabe.csv.gz", dtype={"subsec": str})
    ex = ex.assign(t=lambda d: su.exif_time(d))
    rows = []
    for r in serien.itertuples():
        g = ex[(ex.run == r.lauf) & (ex.series == r.serienordner)]
        subs = g["sub"].dropna().unique()
        if len(subs) > 1:
            raise SystemExit(f"[--] {r.lauf} {r.kamera}: mehrere Unterordner {subs}")
        folder = f"{su.W_MEAS}\\{r.lauf}\\3_LEDSA\\{r.serienordner}" + (f"\\{subs[0]}" if len(subs) else "")
        if g.empty:
            raise SystemExit(f"[--] keine EXIF-Zeilen fuer {r.lauf} {r.serienordner}")
        z = pd.Timestamp(f"{runs.loc[r.lauf, 'date']} {runs.loc[r.lauf, 'start_time']}")
        row = su.series_row(r.lauf, r.kamera, r.position_paper, folder, g, z)
        row.update(room=r.position_paper, date=runs.loc[r.lauf, "date"], start_time=runs.loc[r.lauf, "start_time"])
        rows.append(row)
    s = pd.DataFrame(rows).sort_values(["run", "cam"])
    _write("la_series.csv", s, "Serien N1/J4 (lange Sichtachse), aus EXIF wie ledsa_h1_setup.series_row; t relativ zu start_time")

    pos = pd.read_csv(wg / "positionen.csv", encoding="utf-8-sig")
    pos = pos[(pos.woche == 2) & pos.position_paper.isin(["L1", "L2"])]
    pos = pos[["position_paper", "position_labbook", "raum", "x_m", "y_m", "z_m"]].rename(
        columns={"position_paper": "position", "raum": "room"}).assign(pane_distance_m=0.0)
    _write("la_positions.csv", pos, "Kameralagen L1/L2 Woche 2 (positionen.csv); pane_distance 0 (keiner im Labbook)")

    led = pd.read_csv(wg / "led_streifen.csv", encoding="utf-8-sig")
    out = []
    for a, nm in STRIPS.items():
        q = led[led.led_labbook == nm]
        if len(q) != 1:
            raise SystemExit(f"[--] {nm}: {len(q)} Zeilen")
        q = q.iloc[0]
        if q.farbe != "G" or q.herkunft != "BCL":
            raise SystemExit(f"[--] {nm}: {q.farbe} {q.herkunft}, erwartet G BCL")
        out.append(dict(array=a, led=nm, room=q.raum, colour=q.farbe, channel=CH, origin=q.herkunft, n_leds=N_LED,
                        x_m=q.x_m, y_m=q.y_m, z_bottom_m=q.z_unten_m, z_top_m=q.z_oben_m))
    _write("la_strips.csv", pd.DataFrame(out), "Streifen der langen Sichtachse; Array 0 = LED 4 (naeher), 1 = LED 2")
    pd.set_option("display.width", 250)
    print(s[["run", "cam", "position", "folder_w", "first_id", "last_id", "n_img", "counter_wrap", "t_first_s",
             "t_last_s", "dt_median_s", "num_skip_imgs", "exposure"]].to_string(index=False))


# ---------------------------------------------------------------- scan (Referenzbild der LED-Suche, Fenster)
def _img_list(r):
    """(Bildnummer, t) der Serie nach Zeit (EXIF-Inventar), fuer Kandidaten der LED-Suche."""
    import ledsa_h1_setup as su
    ex = pd.read_csv(REPO_LEDSA / "inventory" / "h1_exif_weitergabe.csv.gz", dtype={"subsec": str})
    folder = r.folder_w.split("\\3_LEDSA\\")[1].split("\\")[0]
    g = ex[(ex.run == r.run) & (ex.series == folder)].assign(t=lambda d: su.exif_time(d))
    z = pd.Timestamp(f"{r.date} {r.start_time}")
    g = g.assign(rel=(g.t - z).dt.total_seconds()).sort_values("rel")
    g = g[(g.rel >= r.t_first_s - 0.01) & (g.rel <= r.t_last_s + 0.01)]
    return [(int(re.search(r"(\d+)\.\w+$", n).group(1)), t) for n, t in zip(g.name, g.rel)]


def _chains(img, rad, p):
    from ledsa.data_extraction.step_1_functions import find_search_areas
    from ledsa_h1_s1scan import chains
    with contextlib.redirect_stdout(io.StringIO()):
        s, thr = find_search_areas(img, rad, p)
    cs = chains(s, 2)
    desc = []
    for c in cs:
        pitch = float(np.median(np.hypot(np.diff(c[:, 1]), np.diff(c[:, 2]))))
        fit = np.polyfit(c[:, 1], c[:, 2], 2)
        resid = float(np.abs(c[:, 2] - np.polyval(fit, c[:, 1])).max())
        desc.append(dict(c=c, n=len(c), pitch=pitch, fit=fit, resid=resid, across=float(np.median(c[:, 2])),
                         rows=(int(c[:, 1].min()), int(c[:, 1].max())), cols=(int(c[:, 2].min()), int(c[:, 2].max()))))
    return s, thr, desc


def scan(run, cam, step_s="30"):
    from ledsa.core.image_reading import read_img_array_from_img
    r = series(run, cam)
    rad = CAMS[cam]["radius"]
    imgs = [(i, t) for i, t in _img_list(r) if t <= REF_S1_T]
    if not imgs:
        raise SystemExit(f"[--] {run} {cam}: kein Bild vor {REF_S1_T} s")
    cand, last_t = [], None
    for i, t in reversed(imgs):                      # vom spaetesten rueckwaerts, alle step_s Sekunden
        if last_t is None or last_t - t >= float(step_s):
            cand.append((i, t))
            last_t = t
    res = []
    for i, t in cand:
        path = Path(img_path(r.folder_w)) / r.name_string.format(i)
        img = read_img_array_from_img(str(path), channel=0, rotation=0)
        best = None
        for p in PCTS:
            s, thr, desc = _chains(img, rad, p)
            n_in = sum(d["n"] for d in desc)
            ok = (len(desc) == 2 and all(d["n"] <= N_LED for d in desc)
                  and max(d["pitch"] for d in desc) > 1.15 * min(d["pitch"] for d in desc))
            if ok:
                rank = (abs(2 * N_LED - n_in) + len(s) - n_in, p)
                if best is None or rank < best[0]:
                    best = (rank, p, s, desc)
        if best is None:
            print(f"  {path.name} t {t:7.1f} s: keine zwei Ketten")
            continue
        rank, p, s, desc = best
        print(f"  {path.name} t {t:7.1f} s: p {p}, {len(s)} Fundstellen, Ketten "
              + ", ".join(f"{d['n']} (Teilung {d['pitch']:.1f} px, Spalte {d['across']:.0f}, Zeilen {d['rows']})"
                          for d in desc))
        res.append(dict(img=i, t=t, p=p, s=s, desc=desc, n=sum(d["n"] for d in desc), fremd=len(s) - sum(d["n"] for d in desc)))
    if not res:
        raise SystemExit(f"[--] {run} {cam}: kein Kandidat mit zwei Ketten")
    # Kameralage: das spaeteste gueltige Bild legt sie fest (Kamera wurde vor der Zuendung teils bewegt, z. B.
    # Hep_220_S1_R1 N1 zwischen -454 und -334 s um ~950 px); nur Bilder gleicher Lage (Ketten-Spalten +-POSE_PX)
    lat = sorted(res[0]["desc"], key=lambda d: -d["pitch"])
    same = [x for x in res if all(abs(a["across"] - b["across"]) <= POSE_PX
                                  for a, b in zip(lat, sorted(x["desc"], key=lambda d: -d["pitch"])))]
    nmax = max(x["n"] for x in same)
    pick = next(x for x in same if x["n"] >= nmax - 2)         # spaetestes Bild gleicher Lage mit (fast) allen LEDs
    print(f"Wahl: Bild {pick['img']} (t {pick['t']:.1f} s), {pick['n']} LEDs in Ketten (max {nmax} bei gleicher Lage, "
          f"{len(same)}/{len(res)} Kandidaten gleicher Lage), p {pick['p']}")
    desc = sorted(pick["desc"], key=lambda d: -d["pitch"])        # naeher (groessere Teilung) = Array 0
    if not desc[0]["pitch"] > 1.15 * desc[1]["pitch"]:
        raise SystemExit(f"[--] Teilungen {desc[0]['pitch']:.1f} / {desc[1]['pitch']:.1f} px nicht eindeutig")
    gap = abs(desc[0]["across"] - desc[1]["across"])
    if gap < 2 * HALF_WIDTH + 4:
        raise SystemExit(f"[--] Streifen zu nah ({gap:.0f} px)")
    rows = []
    for a, d in enumerate(desc):
        rows.append(dict(run=run, cam=cam, array=a, led=STRIPS[a], percentile=pick["p"], radius_px=rad,
                         ref_s1_id=pick["img"], ref_s1_t_s=round(pick["t"], 2),
                         row0=d["rows"][0] - PAD, row1=d["rows"][1] + PAD, col0=d["cols"][0] - PAD,
                         col1=d["cols"][1] + PAD, fit_c2=d["fit"][0], fit_c1=d["fit"][1], fit_c0=d["fit"][2],
                         half_width_px=HALF_WIDTH, fit_resid_px=round(d["resid"], 1), n_found=d["n"], n_leds=N_LED,
                         pitch_px=round(d["pitch"], 2), across_px=round(d["across"]), status="vorschlag"))
    f = SETUP / "la_windows.csv"
    old = pd.read_csv(f, comment="#") if f.exists() else pd.DataFrame()
    if len(old):
        old = old[~((old.run == run) & (old.cam == cam))]
    _write("la_windows.csv", pd.concat([old, pd.DataFrame(rows)], ignore_index=True).sort_values(["run", "cam", "array"]),
           "Streifenfenster je Kamera (Vorschlag aus scan; status 'geprueft' nach Ansicht von s1scan.png)")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    path = Path(img_path(r.folder_w)) / r.name_string.format(pick["img"])
    img = read_img_array_from_img(str(path), channel=0, rotation=0).astype(float)
    fig, ax = plt.subplots(figsize=(10, 7))
    lo = np.percentile(img[img > 0], 50) if (img > 0).any() else 0
    ax.imshow(np.log1p(np.clip(img - lo, 0, None)), cmap="gray")
    ax.plot(pick["s"][:, 2], pick["s"][:, 1], ".", color="w", ms=1)
    for a, d in enumerate(desc):
        ax.plot(d["c"][:, 2], d["c"][:, 1], ".", ms=2, color=("lime", "orange")[a])
        ax.text(d["cols"][1] + 30, d["rows"][0], f"A{a} {STRIPS[a]} {d['n']}", color="y", fontsize=8)
    ax.text(0.01, 0.99, f"{run} {cam}: {path.name} t {pick['t']:.0f} s, p {pick['p']}", transform=ax.transAxes,
            va="top", color="y")
    w = workdir(run, cam)
    w.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(w / "s1scan.png", dpi=110)
    print(f"[ok] {w / 's1scan.png'}")


def windows(run, cam, need_checked=True):
    w = _csv("la_windows.csv")
    w = w[(w.run == run) & (w.cam == cam)].sort_values("array")
    if len(w) != 2:
        raise SystemExit(f"[--] {run} {cam}: {len(w)} Fensterzeilen")
    if need_checked and not w.status.isin(["geprueft", "auto"]).all():
        raise SystemExit(f"[--] {run} {cam}: Fenster nicht geprueft")
    return w


def approve(run, cam):
    """Automatische Freigabe ohne Ansicht: status 'auto', wenn beide Ketten <= N_LED
    LEDs, Fit-Rest <= HALF_WIDTH/2 und Teilungsverhaeltnis eindeutig (scan); Kontrollbilder s1scan.png/ends.png danach
    ansehen und auf 'geprueft' setzen. Die Horizont-Probe in edges bricht bei Mehrdeutigkeit ab."""
    f = SETUP / "la_windows.csv"
    d = pd.read_csv(f, comment="#")
    m = (d.run == run) & (d.cam == cam)
    w = d[m]
    # Fit-Rest <= HALF_WIDTH - 1: alle Fundstellen liegen sicher im Band (Hep_220_S1_R2 N1 LED 4: 7,4 px, schraeger
    # Streifen, Kontrollbild ohne Fremdpunkte)
    ok = len(w) == 2 and (w.n_found <= N_LED).all() and (w.fit_resid_px <= HALF_WIDTH - 1).all()
    if not ok:
        raise SystemExit(f"[--] {run} {cam}: automatische Pruefung nicht bestanden\n{w.to_string()}")
    d.loc[m, "status"] = "auto"
    _write("la_windows.csv", d, "Streifenfenster je Kamera (Vorschlag aus scan; status 'geprueft' nach Ansicht von "
           "s1scan.png, 'auto' = nur automatisch geprueft)")
    print(f"[ok] {run} {cam}: status auto")


# ---------------------------------------------------------------- config / edges / ledz
def config(run, cam):
    from ledsa.core.ConfigData import ConfigData
    r = series(run, cam)
    w = windows(run, cam)
    m = re.match(r"^(.*)\{:0(\d)d\}(\.\w+)$", r.name_string)
    if not m:
        raise SystemExit(f"[--] Namensmuster {r.name_string}")
    work = workdir(run, cam)
    work.mkdir(parents=True, exist_ok=True)
    cwd = os.getcwd()
    os.chdir(work)
    try:
        cfg = ConfigData(load_config_file=False, img_directory=img_path(r.folder_w) + "\\", img_name_string=r.name_string,
                         num_img_overflow=9999, first_img_experiment_id=int(r.first_id),
                         last_img_experiment_id=int(r.last_id), num_cores=NUM_CORES,
                         date=pd.Timestamp(r.date).strftime("%d.%m.%Y"), start_time=r.start_time,
                         time_diff_to_image_time=0, img_rotation=0, farfield_distances=FARFIELD_DISTANCES,
                         ref_img_id=int(w.ref_s1_id.iloc[0]), search_area_radius=int(w.radius_px.iloc[0]), channel="all",
                         pixel_value_percentile=float(w.percentile.iloc[0]), max_num_leds=600, num_arrays=2,
                         first_img_analysis_id=int(r.first_id), last_img_analysis_id=int(r.last_id),
                         num_skip_imgs=int(r.num_skip_imgs))
        cfg.save()
    finally:
        os.chdir(cwd)
    print(f"[ok] {work / 'config.ini'}: {r.name_string} {r.first_id}-{r.last_id} ({r.n_img} Bilder, Schritt "
          f"{int(r.num_skip_imgs) + 1}), Referenzbild {int(w.ref_s1_id.iloc[0])}")


DUP_FACTOR = 0.6


def _index_along(row):
    """Index je LED ab der obersten (Bildzeile aufsteigend), Luecken aus dem Pixelabstand (wie ledsa_h1_ledz).
    Doppelfunde (Abstand < DUP_FACTOR x oertliche Teilung; Hep_220_S1_R3 N1 LED 4: Punkt bei Zeile 2436 zwischen den
    LEDs bei 2429 und 2448) bekommen den Index des Vorgaengers und zaehlen nicht als LED (Korrektur 2026-11-26)."""
    o = np.argsort(row)
    d = np.diff(row[o])
    loc = pd.Series(d).rolling(9, center=True, min_periods=3).median().to_numpy()
    step = np.where(d > GAP_FACTOR * loc, np.rint(d / loc), np.where(d < DUP_FACTOR * loc, 0, 1)).astype(int)
    if (step == 0).any():
        print(f"  [!] {(step == 0).sum()} Doppelfund(e) bei Zeile(n) {row[o][1:][step == 0].tolist()} (Index des Vorgaengers)")
    return o, np.concatenate([[0], np.cumsum(step)]), int((step > 1).sum())


HORIZON_TOL = 0.5


def horizon_skips(run, cam, P):
    """Nicht gefundene End-LEDs je Array aus der Horizont-Probe: Punkte in Kamerahoehe z_c liegen in
    beiden Streifen auf derselben Bildzeile. P = [(Zeilen oben->unten, Index ab oben)] fuer Array 0/1. Fuer jede Annahme
    sb0 (unten fehlend an Array 0) folgt sb1; gueltig, wenn 0 - TOL <= sb1 <= fehlend1 + TOL. Genau eine gueltige
    Annahme verlangt, sonst Abbruch (SKIP_END von Hand). Rollwinkel nicht korrigiert (1 Grad ~ 0,5 LED bei N1)."""
    st = _csv("la_strips.csv").set_index("array")
    zc = float(_csv("la_positions.csv").set_index("position").loc[series(run, cam).position, "z_m"])
    pitch = (st.loc[0, "z_top_m"] - st.loc[0, "z_bottom_m"]) / (N_LED - 1)
    (r0, k0), (r1, k1) = P
    miss0, miss1 = N_LED - 1 - int(k0[-1]), N_LED - 1 - int(k1[-1])
    if miss0 < 0 or miss1 < 0:
        raise SystemExit(f"[--] {run} {cam}: mehr Teilungen als LEDs ({k0[-1] + 1}, {k1[-1] + 1})")
    kb0, kb1 = k0[-1] - k0, k1[-1] - k1
    ok = []
    for sb0 in range(miss0 + 1):
        z0 = st.loc[0, "z_bottom_m"] + (sb0 + kb0) * pitch            # absteigend (oben zuerst)
        row_h = float(np.interp(zc, z0[::-1], r0[::-1]))
        k_at = float(np.interp(row_h, r1, kb1)) if r1.min() <= row_h <= r1.max() else np.nan
        sb1 = (zc - st.loc[1, "z_bottom_m"]) / pitch - k_at
        flag = -HORIZON_TOL <= sb1 <= miss1 + HORIZON_TOL
        print(f"  Horizont: Array 0 unten {sb0}/{miss0} fehlend -> Zeile {row_h:.0f} -> Array 1 unten {sb1:.2f}/{miss1}"
              + ("  <- passt" if flag else ""))
        if flag:
            ok.append((sb0, min(max(int(round(sb1)), 0), miss1), sb1))
    if (run, cam) in SKIP_END:
        sb = SKIP_END[(run, cam)]
        print(f"  [!] von Hand: unten fehlend {sb} (SKIP_END)")
        return {0: (miss0 - sb[0], sb[0]), 1: (miss1 - sb[1], sb[1])}
    out = {}
    for a, miss in ((0, miss0), (1, miss1)):
        end = END_HIDDEN[cam][a]
        out[a] = (miss, 0) if end == "top" else (0, miss)
    sb0 = out[0][1]
    agree = any(o[0] == sb0 for o in ok)
    print(f"  Festlegung END_HIDDEN {cam}: Array 0 oben/unten {out[0]}, Array 1 oben/unten {out[1]}; Horizont-Probe "
          + ("stimmt zu" if agree else ("nicht auswertbar" if not ok else "WIDERSPRICHT -> Kontrollbild ansehen")))
    return out


def edges(run, cam):
    work = workdir(run, cam)
    w = windows(run, cam)
    sa = pd.read_csv(work / "analysis" / "led_search_areas.csv", comment="#", header=None, names=["id", "row", "col"])
    st = _csv("la_strips.csv").set_index("array")
    idx, coords, used, rows, sel = [], [], set(), [], []
    for q in w.itertuples():
        col_fit = np.polyval([q.fit_c2, q.fit_c1, q.fit_c0], sa.row.to_numpy(float))
        s = sa[(sa.row >= q.row0) & (sa.row <= q.row1) & (np.abs(sa.col - col_fit) <= q.half_width_px)]
        if used & set(s.id):
            raise SystemExit(f"[--] Fenster ueberlappen")
        used |= set(s.id)
        o, k, n_gap = _index_along(s.row.to_numpy(float))
        sel.append((q, s, o, k, n_gap))
    skips = horizon_skips(run, cam, [(s.row.to_numpy(float)[o], k) for q, s, o, k, n_gap in sel])
    for q, s, o, k, n_gap in sel:
        sk_t, sk_b = skips[q.array]
        p = st.loc[q.array]
        pitch = (p.z_top_m - p.z_bottom_m) / (N_LED - 1)
        top, bot = s.iloc[o[0]], s.iloc[o[-1]]
        z_t, z_b = p.z_top_m - sk_t * pitch, p.z_bottom_m + sk_b * pitch
        idx.append(f"{int(top.id)} {int(bot.id)}")
        coords.append(f"{p.x_m:.4f} {p.y_m:.4f} {z_t:.4f} {p.x_m:.4f} {p.y_m:.4f} {z_b:.4f}")
        rows.append(dict(run=run, cam=cam, array=q.array, n_found=len(s), n_span=int(k[-1]) + 1, gaps=n_gap,
                         skip_top=sk_t, skip_bottom=sk_b, z_top=round(z_t, 4), z_bottom=round(z_b, 4),
                         row_top=int(top.row), col_top=int(top.col), row_bottom=int(bot.row), col_bottom=int(bot.col)))
        print(f"  Array {q.array} {p.led}: {len(s)} LEDs gefunden, Spanne {int(k[-1]) + 1} Teilungen, Luecken {n_gap}, "
              f"Ausschluss oben/unten {sk_t}/{sk_b} -> z {z_b:.3f}-{z_t:.3f} m")
    txt = (work / "config.ini").read_text(encoding="utf-8")
    # ganzen Block ersetzen (Kopfzeile + eingerueckte Fortsetzungszeilen; Korrektur 2026-11-26: beim zweiten edges-Lauf
    # blieben die alten Zeilen stehen -> doppelte Eintraege, -s2 bricht ab)
    for key, vals in (("led_array_edge_indices", idx), ("led_array_edge_coordinates", coords)):
        txt, n = re.subn(rf"([ \t]*{key} = )[^\n]*(?:\n[ \t]+[^ \t#\n=][^\n=]*)*",
                         lambda m: m.group(1) + "\n" + "\n".join(f"\t    {v}" for v in vals), txt)
        if n != 1:
            raise SystemExit(f"[--] {key}: {n} Treffer in config.ini")
    (work / "config.ini").write_text(txt, encoding="utf-8")
    f = SETUP / "la_edges.csv"
    old = pd.read_csv(f, comment="#") if f.exists() else pd.DataFrame()
    if len(old):
        old = old[~((old.run == run) & (old.cam == cam))]
    _write("la_edges.csv", pd.concat([old, pd.DataFrame(rows)], ignore_index=True).sort_values(["run", "cam", "array"]),
           "End-LEDs je Array: gefunden, Spanne in Teilungen, Ausschluss oben/unten (SKIP_END), z der Enden")


def ledz(run, cam):
    """LED-Hoehen nach Index bei gleicher Teilung (wie ledsa_h1_ledz.fix, Tabellen dieser Auswertung)."""
    work = workdir(run, cam)
    a_dir = work / "analysis"
    cur, orig = a_dir / "led_search_areas_with_coordinates.csv", a_dir / "led_search_areas_with_coordinates_ledsa.csv"
    mark = "la.py ledz"
    with open(cur, encoding="utf-8") as fh:
        fresh = mark not in fh.readline()
    if fresh:
        orig.write_bytes(cur.read_bytes())
    elif not orig.exists():
        raise SystemExit(f"[--] {orig} fehlt")
    c = np.loadtxt(orig, delimiter=",", ndmin=2)
    if not np.array_equal(c[:, 0], np.arange(len(c))):
        raise SystemExit("[--] LED-IDs nicht 0..N-1")
    st = _csv("la_strips.csv").set_index("array")
    e = _csv("la_edges.csv")
    e = e[(e.run == run) & (e.cam == cam)].set_index("array")
    out = c.copy()
    for a in st.index:
        ids = np.loadtxt(a_dir / f"led_array_indices_{a:03d}.csv", dtype=int, ndmin=1)
        p = st.loc[a]
        sk_t, sk_b = int(e.loc[a, "skip_top"]), int(e.loc[a, "skip_bottom"])
        # Index verankert an den End-LEDs aus edges (Korrektur 2026-11-26: -s2 ordnet einzelne LEDs keinem Array zu,
        # Hep_220_S1_R2 N1 LED 4 149 statt 150; fehlt eine End-LED, wuerde der Index sonst verrutschen)
        rows_m = c[ids, 1].astype(float)
        anchors = [float(e.loc[a, r]) for r in ("row_top", "row_bottom") if r in e.columns
                   and not np.isclose(rows_m, float(e.loc[a, r]), atol=0.5).any()]
        if anchors:
            print(f"  [!] Array {a}: End-LED(s) bei Zeile {anchors} nicht im Array (-s2) -> als Anker gezaehlt")
        rows_all = np.concatenate([rows_m, anchors])
        o_all, k_all, n_gap = _index_along(rows_all)
        member = o_all < len(rows_m)
        o, k = o_all[member], k_all[member]
        if k_all[-1] != N_LED - 1 - sk_t - sk_b:
            raise SystemExit(f"[--] Array {a}: letzter Index {k_all[-1]} != {N_LED - 1 - sk_t - sk_b}")
        if len(ids) < int(e.loc[a, "n_found"]):
            print(f"  [!] Array {a}: {int(e.loc[a, 'n_found']) - len(ids)} LED(s) von -s2 nicht zugeordnet")
        pitch = (p.z_top_m - p.z_bottom_m) / (N_LED - 1)
        z = p.z_top_m - (sk_t + k) * pitch
        ids_o = ids[o]
        dz = z - c[ids_o, 5]
        out[ids_o, 3], out[ids_o, 4], out[ids_o, 5], out[ids_o, 7] = p.x_m, p.y_m, z, z
        print(f"  Array {a}: {len(ids)} LEDs, Luecken {n_gap}, z {z.min():.4f}-{z.max():.4f} m, gegen LEDSA "
              f"{1000 * dz.min():+.0f}...{1000 * dz.max():+.0f} mm")
    buf = io.StringIO()
    buf.write(f"# LED id, pixel position x, pixel position y, x, y, z, width, height  (z nach Index: {mark})\n")
    np.savetxt(buf, out, fmt="%d,%d,%d,%f,%f,%f,%f,%f")
    new = buf.getvalue().encode("utf-8")
    if cur.read_bytes() != new:
        cur.write_bytes(new)


# ---------------------------------------------------------------- Referenzbilder, config_analysis
def ref_window(run):
    f = REPO / "1_Measurements" / run / "1_Processed_data" / f"{run}_processed.csv"
    meas = pd.read_csv(f, comment="#", encoding="utf-8-sig")
    t = meas["Time (s)"].to_numpy(float)
    first = {}
    for c in meas.columns:
        m = re.match(r"Extinction LEM_\d+_(F\d)_[\d.]+ \(1/m\)$", c)
        if m:
            k = meas[c].to_numpy(float)
            above = pd.Series((t > 0) & (k > REF_K_ONSET)).rolling(REF_ONSET_HOLD_S).min().to_numpy() == 1
            i = np.flatnonzero(above)
            if len(i):
                first[c] = t[i[0] - REF_ONSET_HOLD_S + 1]
    if not first:
        return 0.0
    c0 = min(first, key=first.get)
    w = min(first[c0] - REF_MARGIN_S, REF_MAX_S)
    print(f"  Referenzfenster bis {w:.0f} s (erste LEM-Reaktion {first[c0]:.0f} s, {c0})")
    return w


def _s3(work, ids):
    rows = []
    for i in ids:
        d = pd.read_csv(work / "analysis" / f"channel{CH}" / f"{i}_led_positions.csv", comment="#", header=None,
                        skipinitialspace=True)
        if d.shape[1] < 7:
            raise SystemExit("[--] Schritt 3 ohne Fernfeld-Sockel")
        d.columns = ["led_id", "line", "sum", "avg", "max", "farbg", "ped"][:d.shape[1]]
        rows.append(d.assign(img_id=i))
    return pd.concat(rows, ignore_index=True)


def select_ref_images(work, t_max):
    info = pd.read_csv(work / "analysis" / "image_infos_analysis.csv")
    t = info.set_index(info.columns[0])[info.columns[3]]
    have = {int(f.name.split("_")[0]) for f in (work / "analysis" / f"channel{CH}").glob("*_led_positions.csv")}
    own = np.concatenate([np.loadtxt(work / "analysis" / f"led_array_indices_{a:03d}.csv", dtype=int, ndmin=1) for a in (0, 1)])
    sel = []
    for look in (REF_LOOKBACK_S, REF_LOOKBACK_MAX_S):
        cand = [i for i in t.index if t_max - look <= t[i] <= t_max and i in have]
        if not cand:
            continue
        d = _s3(work, cand)
        s = d[d.led_id.isin(own)].pivot(index="led_id", columns="img_id", values="farbg")
        led_rel = s.div(s.median(axis=1), axis=0)
        rel, part = led_rel.median(), ((led_rel - 1).abs() > REF_LED_DEV).mean()
        ok = sorted(i for i in cand if abs(rel[i] - 1) <= REF_TOL and part[i] <= REF_LED_FRAC)
        print(f"  {len(cand)} Bilder in [{t_max - look:.0f}, {t_max:.0f}] s, farbg rel. {rel.min():.3f}-{rel.max():.3f}, "
              f"gueltig {len(ok)}")
        sel = ok[-REF_N:]
        if len(sel) >= REF_MIN:
            break
    if len(sel) < REF_MIN:
        raise SystemExit(f"[--] nur {len(sel)} gueltige Referenzbilder")
    print(f"  Referenzbilder {sel} (t {t[sel[0]]:.0f} bis {t[sel[-1]]:.0f} s)")
    return sel


def analysis(run, cam):
    from ledsa.analysis.ConfigDataAnalysis import ConfigDataAnalysis
    work = workdir(run, cam)
    refs = select_ref_images(work, ref_window(run))
    p = _csv("la_positions.csv").set_index("position").loc[series(run, cam).position]
    cwd = os.getcwd()
    os.chdir(work)
    try:
        ConfigDataAnalysis(load_config_file=False, camera_position=f"{p.x_m:g} {p.y_m:g} {p.z_m:g}",
                           num_layers=INVERSION["num_layers"], domain_bounds=INVERSION["domain_bounds"],
                           led_array_indices="0 1", num_ref_images=INVERSION["num_ref_images"],
                           ref_img_indices=" ".join(map(str, refs)), camera_channels=INVERSION["camera_channels"],
                           num_cores=NUM_CORES, reference_property=INVERSION["reference_property"],
                           solver=INVERSION["solver"], lambda_reg=INVERSION["lambda_reg"],
                           pane_distance=float(p.pane_distance_m)).save()
    finally:
        os.chdir(cwd)
    print(f"[ok] {work / 'config_analysis.ini'}")


def ref_ids(work):
    m = re.search(r"ref_img_indices = ([\d ]+)\s*$", (work / "config_analysis.ini").read_text(encoding="utf-8"), re.M)
    return [int(v) for v in m.group(1).split()]


# ---------------------------------------------------------------- Rauschen, Saettigung, Maske
def noise(run, cam):
    from ledsa_h1_noise import optical_black
    r, work = series(run, cam), workdir(run, cam)
    R = int(re.search(r"search_area_radius = (\d+)", (work / "config.ini").read_text(encoding="utf-8")).group(1))
    info = pd.read_csv(work / "analysis" / "image_infos_analysis.csv")
    info.columns = ["img_id", "name", "time", "t_exp"]
    v = []
    for name in info.set_index("img_id").loc[ref_ids(work), "name"]:
        ob = optical_black(Path(img_path(r.folder_w)) / name)
        if ob is None:
            break
        std, scale = ob
        v.append(np.sqrt(sum(R * R * (std[c] * scale[c]) ** 2 for c in (1, 3))))
    sig = float(np.mean(v)) if v else np.nan
    print(f"  {run} {cam} Kanal {CH}: R {R}, {len(v)} Bilder, sigma_sum " + (f"{sig:.2f}" if v else "- (kein optisches Schwarz)"))
    f = SETUP / "la_read_noise.csv"
    old = pd.read_csv(f, comment="#") if f.exists() else pd.DataFrame()
    if len(old):
        old = old[~((old.run == run) & (old.cam == cam))]
    _write("la_read_noise.csv", pd.concat([old, pd.DataFrame([dict(run=run, cam=cam, channel=CH, radius_px=R, n_img=len(v),
                                                                   sigma_sum=sig)])], ignore_index=True),
           "Leserauschen der Box-Summe Kanal 1 (optisches Schwarz wie ledsa_h1_noise); NaN = kein optisches Schwarz")


def _all_s3(work):
    rows = []
    for f in (work / "analysis" / f"channel{CH}").glob("*_led_positions.csv"):
        d = pd.read_csv(f, comment="#", header=None, skipinitialspace=True)
        d.columns = ["led_id", "line", "sum", "avg", "max", "farbg", "ped"][:d.shape[1]]
        rows.append(d[["led_id", "sum", "max", "farbg", "ped"]].assign(img_id=int(f.name.split("_")[0])))
    info = pd.read_csv(work / "analysis" / "image_infos_analysis.csv")
    info.columns = ["img_id", "name", "time", "t_exp"]
    return pd.concat(rows, ignore_index=True).merge(info[["img_id", "t_exp"]], on="img_id")


def mask(run, cam):
    """Maske je (t, Schicht) und Array: U_B-Kriterium (alle Kameras) und, falls Leserauschen vorhanden, SNR 3."""
    work = workdir(run, cam)
    s = _all_s3(work)
    refs = ref_ids(work)
    s0 = s[s.img_id.isin(refs)].groupby("led_id")[["farbg", "ped"]].median().rename(columns={"farbg": "S0", "ped": "P0"})
    s = s.join(s0, on="led_id")
    b = -np.log(s.farbg / s.S0)
    sat = []
    for a in (0, 1):
        ids = np.loadtxt(work / "analysis" / f"led_array_indices_{a:03d}.csv", dtype=int)
        r0 = s[s.img_id.isin(refs) & s.led_id.isin(ids)]
        frac = r0.groupby("led_id")["max"].max().ge(SAT_FRAC * FULL).mean()
        sat.append(dict(run=run, cam=cam, array=a, sat_frac_pct=round(100 * frac, 2)))
        print(f"  Saettigung Array {a}: {100 * frac:.1f} % der LEDs (max >= {SAT_FRAC} x {FULL}) in den Referenzbildern")
    nz = SETUP / "la_read_noise.csv"
    sig = np.nan
    if nz.exists():
        d = pd.read_csv(nz, comment="#")
        d = d[(d.run == run) & (d.cam == cam)]
        sig = float(d.sigma_sum.iloc[0]) if len(d) else np.nan
    crit = [(f"UB{u:g}", ~((s.farbg > 0) & ~((b > B_MIN) & (u * (s.ped / s.farbg + s.P0 / s.S0) > DB_MAX))))
            for u in U_B_SENS]
    if np.isfinite(sig):
        crit.append(("SNR3", ~(s.farbg >= SNR_MIN * sig)))
    from ledsa_h1_mask import layer_fraction
    out = []
    for name, bad in crit:
        sb = s.assign(bad=bad.to_numpy())
        for a in (0, 1):
            t, bf, tot = layer_fraction(sb, work, a)
            w = bf / np.where(tot > 0, tot, np.nan)
            n_t, n_l = w.shape
            out.append(pd.DataFrame(dict(krit=name, led_array=a, t_s=np.repeat(t, n_l), layer=np.tile(np.arange(n_l), n_t),
                                         anteil=w.ravel(), gesperrt=w.ravel() > W_MAX)))
            print(f"  {name} Array {a}: Strahlen ungueltig {100 * sb[sb.led_id.isin(np.loadtxt(work / 'analysis' / f'led_array_indices_{a:03d}.csv', dtype=int))].bad.mean():.1f} %, "
                  f"(t, Schicht) gesperrt {100 * np.nanmean(w > W_MAX):.1f} %")
    d = pd.concat(out, ignore_index=True)
    f = work / "mask.csv.gz"
    d.to_csv(f, index=False, float_format="%.4f")
    f2 = SETUP / "la_saturation.csv"
    old = pd.read_csv(f2, comment="#") if f2.exists() else pd.DataFrame()
    if len(old):
        old = old[~((old.run == run) & (old.cam == cam))]
    _write("la_saturation.csv", pd.concat([old, pd.DataFrame(sat)], ignore_index=True), "Saettigung je Array in den Referenzbildern")
    print(f"[ok] {f}")


if __name__ == "__main__":
    {"setup": setup, "scan": scan, "approve": approve, "config": config, "edges": edges, "ledz": ledz, "analysis": analysis,
     "noise": noise, "mask": mask}[sys.argv[1]](*sys.argv[2:])
