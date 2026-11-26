# Stufe 0 (2026-11-20) in einem Arbeitsordner ausserhalb des Repos gelaufen; Ausgaben danach gzip-komprimiert nach inventory/ uebernommen.
"""Dateiliste der Juelich-Tagesserien (nur lesen): Tag, Kamera, Name, Groesse, mtime -> inventory/h1_files_juelich.tsv (danach gzip)."""
import os, sys, time
from datetime import datetime

ROOT = (os.environ.get("H1_IMAGES_ROOT") or sys.exit("[--] H1_IMAGES_ROOT nicht gesetzt (Wurzel des Rohbildbaums)")) + r"\2_juelichMeasurements"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "inventory", "h1_files_juelich.tsv")  # danach gzip

t0 = time.time()
n = 0
with open(OUT, "w", encoding="utf-8") as f:
    f.write("tag\tkamera\tname\tbytes\tmtime\n")
    for day in sorted(os.listdir(ROOT)):
        for cam in sorted(os.listdir(os.path.join(ROOT, day))):
            p = os.path.join(ROOT, day, cam)
            k = 0
            with os.scandir(p) as it:
                for e in it:
                    if e.is_dir(follow_symlinks=False):
                        f.write(f"{day}\t{cam}\t{e.name}/\t\t\n")
                        continue
                    st = e.stat(follow_symlinks=False)
                    f.write(f"{day}\t{cam}\t{e.name}\t{st.st_size}\t"
                            f"{datetime.fromtimestamp(st.st_mtime).isoformat(timespec='seconds')}\n")
                    k += 1
            n += k
            print(f"{day} {cam}: {k} Dateien ({time.time() - t0:.0f} s)", flush=True)
print(f"fertig: {n} Dateien -> {OUT}", flush=True)
