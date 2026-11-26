# Stufe 0 (2026-11-20) in einem Arbeitsordner ausserhalb des Repos gelaufen; Ausgaben danach gzip-komprimiert nach inventory/ uebernommen.
"""EXIF der Juelich-RAW-Dateien (nur lesen) in den Lauffenstern [Zuendung - 20 min, Zuendung + 45 min] nach Dateizeit
(+ alle Dateien mit Dateizeit ausserhalb des Aufnahmetags, weil dort die Dateizeit nicht die Aufnahmezeit ist).
Ausgabe: inventory/h1_exif_juelich.csv (danach gzip). Leser: rawexif der Hasenheide-2-Auswertung (Ordner per H2_LEDSA_DIR; nicht in
diesem Repo). Rohbilder per H1_IMAGES_ROOT."""
import os, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parents[1] / "inventory"   # Ein-/Ausgabe in inventory/
H2 = Path(os.environ.get("H2_LEDSA_DIR") or sys.exit("[--] H2_LEDSA_DIR nicht gesetzt (Ordner mit rawexif; nicht in diesem Repo)"))
sys.path.insert(0, str(H2))
import rawexif  # noqa: E402

ROOT = Path(os.environ.get("H1_IMAGES_ROOT") or sys.exit("[--] H1_IMAGES_ROOT nicht gesetzt (Wurzel des Rohbildbaums)")) / "2_juelichMeasurements"
S = pd.read_csv(Path(__file__).resolve().parents[3] / "photo_handover" / "serien.csv", encoding="utf-8-sig").drop_duplicates("lauf")
S = S[S.datum_v.str[:5].isin(["08.12", "09.12", "10.12"])]
S["z"] = pd.to_datetime("2025-12-" + S.datum_v.str[:2] + " " + S.zuendung)

d = pd.read_csv(HERE / "h1_files_juelich.tsv.gz", sep="\t")
d = d[~d.name.str.startswith("._") & d.name.str.upper().str.endswith((".CR2", ".CR3"))].copy()
d["mt"] = pd.to_datetime(d.mtime)
same = d.mt.dt.strftime("%Y-%m-%d") == d.tag
keep = ~same
for r in S.itertuples():
    rel = (d.mt - r.z).dt.total_seconds()
    keep |= same & (rel > -1200) & (rel < 2700)
d = d[keep]
print(f"{len(d)} Dateien", flush=True)


def one(row):
    p = ROOT / row.tag / row.kamera / row.name
    try:
        t = rawexif.read(str(p))
    except Exception as e:                                    # noqa: BLE001
        t = {"err": repr(e)}
    return dict(tag=row.tag, kamera=row.kamera, name=row.name, bytes=row.bytes, mtime=row.mtime,
                model=t.get("Model"), serial=t.get("BodySerialNumber"), dto=t.get("DateTimeOriginal"),
                subsec=t.get("SubSecTimeOriginal"), offset=t.get("OffsetTimeOriginal"), expo=t.get("ExposureTime"),
                fnum=t.get("FNumber"), iso=t.get("ISO"), err=t.get("err"))


t0 = time.time()
rows = []
with ThreadPoolExecutor(max_workers=4) as ex:
    for i, r in enumerate(ex.map(one, d.itertuples()), 1):
        rows.append(r)
        if i % 1000 == 0:
            print(f"{i}/{len(d)} ({time.time() - t0:.0f} s)", flush=True)
out = pd.DataFrame(rows)
if out.empty:
    raise SystemExit("keine Zeilen")
out.to_csv(HERE / "h1_exif_juelich.csv", index=False)
print(f"fertig {len(out)} in {time.time() - t0:.0f} s, Fehler {out.err.notna().sum()}", flush=True)
