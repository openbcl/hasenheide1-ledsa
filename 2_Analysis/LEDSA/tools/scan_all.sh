#!/bin/bash
# Stufe 1: ledsa_h1_s1scan.py fuer alle Serien ohne Zeilen in setup/ledsa_h1_strip_windows.csv, aufgeteilt auf N
# Warteschlangen (Teil i von N). Aufruf: scan_all.sh <i> <N>   (z. B. 0 2 und 1 2 parallel)
# ledsa_h1_s1scan.py schreibt die Fenstertabelle mit Lesen-Aendern-Schreiben; zwei Warteschlangen koennten sich dabei
# ueberschreiben -> jede Warteschlange schreibt ueber H1_WINDOWS_PART in eine eigene Datei, scan_merge fuehrt zusammen.
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
I=$1; N=$2
ledsa_env > /dev/null || exit 1
LIST=$(cd "$L" && "$VENV" -c "
import pandas as pd, glob
s=pd.read_csv('setup/ledsa_h1_series.csv',comment='#')
done=set()
for f in glob.glob('setup/ledsa_h1_strip_windows*.csv'):     # Haupttabelle und Teildateien (Neustart ueberspringt Fertiges)
    done|=set(map(tuple,pd.read_csv(f,comment='#')[['run','cam']].drop_duplicates().values))
todo=[(r.run,r.cam) for r in s.itertuples() if (r.run,r.cam) not in done]
print(' '.join(f'{a}:{b}' for k,(a,b) in enumerate(todo) if k % $N == $I))" | tr -d '\r')
echo "Teil $I/$N: $(echo $LIST | wc -w) Serien"
export H1_WINDOWS_PART="$I"
mkdir -p "$RUNS/_logs/s1scan"
for rc in $LIST; do
  echo "===== ${rc%%:*} ${rc##*:} $(date '+%T')"
  LOGF="$RUNS/_logs/s1scan/${rc%%:*}_${rc##*:}.log"                 # volle Ausgabe je Serie
  if (cd "$L" && "$PY" ledsa_h1_s1scan.py "${rc%%:*}" "${rc##*:}" > "$LOGF" 2>&1); then
    grep -E "Referenzbild|WAAGE|Vorschlag|Array|Lage|\[--\]|\[!\]" "$LOGF"
  else
    echo "FEHLER ${rc} (Ende von $LOGF):"; grep -v -i warn "$LOGF" | tail -6
  fi
done
echo "TEIL FERTIG $I $(date '+%F %T')"
