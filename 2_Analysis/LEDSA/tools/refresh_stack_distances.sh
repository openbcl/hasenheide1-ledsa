#!/bin/bash
# Veraltete Abstandsdateien in den Stapelordnern erneuern (2026-11-24).
# LEDSA 0.13.0 (StackedExtinctionCoefficients) rechnet die Abstaende je LED und Schicht bei -as frisch im Speicher,
# schreibt led_array_<id>_distances_per_layer.txt aber nur, wenn die Datei noch fehlt -> nach der LED-Hoehenkorrektur
# (ledsa_h1_ledz.py) lagen dort die Abstaende der alten Geometrie. Je Stapelordner: alte Dateien -> *.stale, k-Dateien
# per md5 sichern, -as neu, pruefen, dass die k-Dateien bitgleich bleiben (Beleg: Inversion nutzte die neue Geometrie
# schon), dann *.stale loeschen. Aufruf: refresh_stack_distances.sh [<Glob unter runs/>, Vorgabe */stacked_*]
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
ledsa_env > /dev/null || exit 1
PAT=${1:-*/stacked_*}
for S in "$RUNS"/$PAT; do
  [ -f "$S/config_stacked.ini" ] || continue
  ls "$S"/led_array_*_distances_per_layer.txt > /dev/null 2>&1 || { echo "-- $S ohne Abstandsdatei"; continue; }
  for f in "$S"/led_array_*_distances_per_layer.txt; do mv "$f" "$f.stale"; done
  before=$(cd "$S" && find analysis -name "*.csv" -type f | sort | xargs md5sum | md5sum)
  t0=$(date +%s)
  (cd "$S" && rm -f time_alignment_led_array_*.txt && "$PY" -m ledsa -as > as_refresh_log.txt 2>&1) \
    || { echo "FEHLER $S -as"; for f in "$S"/*.stale; do mv "$f" "${f%.stale}"; done; continue; }
  after=$(cd "$S" && find analysis -name "*.csv" -type f | sort | xargs md5sum | md5sum)
  same=nein; [ "$before" = "$after" ] && same=ja
  dmax=$(cd "$S" && PYTHONPATH= "$VENV" -c "
import numpy as np,glob
m=0
for f in sorted(glob.glob('led_array_*_distances_per_layer.txt')):
    a=np.loadtxt(f); b=np.loadtxt(f+'.stale'); m=max(m,np.abs(a-b).max() if a.shape==b.shape else np.inf)
print(f'{m:.4f}')")
  echo "ok ${S#$RUNS/} $(( $(date +%s) - t0 )) s, k bitgleich: $same, max |Abstand neu - alt| $dmax m"
  [ "$same" = ja ] && rm -f "$S"/*.stale
done
echo "ABSTAENDE FERTIG $(date '+%F %T')"
