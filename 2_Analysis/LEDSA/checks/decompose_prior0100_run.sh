#!/bin/bash
# Fuehrt -as (LEDSA 0.13.0) fuer alle Zerlegungs-Varianten aus (checks/decompose_prior0100.py make zuerst).
# Log runs/_logs/decompose_prior0100.log; Abbruch einer Variante bricht nur diese ab.
source "$(dirname "${BASH_SOURCE[0]}")/../tools/env.sh"
ledsa_env > /dev/null || exit 1
for d in "$RUNS"/Hep_160_S2_R*/zerl_F*_${1:-*}; do
  t0=$(date +%s)
  if (cd "$d" && rm -f time_alignment_led_array_*.txt && "$PY" -m ledsa -as > as_log.txt 2>&1); then
    echo "ok ${d#$RUNS/} $(( $(date +%s) - t0 )) s"
  else
    echo "FEHLER ${d#$RUNS/} (as_log.txt)"; tail -3 "$d/as_log.txt"
  fi
done
echo "ZERLEGUNG FERTIG $(date '+%F %T')"
