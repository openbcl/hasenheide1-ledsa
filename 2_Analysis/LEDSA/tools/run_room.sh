#!/bin/bash
# Raum-Kette nach run_cam.sh aller Kameras des Raums (H1, LEDSA 0.13.0):
#   analysis-Konfiguration (gemeinsame Referenzbilder, config_analysis.ini je Kamera, config_stacked.ini bei zwei
#   Kameras) -> Leserauschen (ledsa_h1_noise.py) -> -a je Kamera (farbg_sum_col_val + sum_col_val, 3 Kanaele x
#   3 Arrays) -> -as (Stapel) -> Maske (ledsa_h1_mask.py flag) -> Sockelpruefung je Kamera.
# Aufruf: run_room.sh <Lauf> <Raum>   (Nebenvariante: H1_VARIANT=<Name>, s. ledsa_h1_config.py; Stapel dann
# stacked_<Raum>_<Name>)
set -eo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
RUN=$1; ROOM=$2
STK="stacked_${ROOM}${H1_VARIANT:+_$H1_VARIANT}"
ledsa_env > /dev/null
echo "===== Raum $RUN $ROOM $(date '+%F %T')"
DIRS=$(cd "$L" && "$PY" ledsa_h1_config.py rooms "$RUN" | tr -d '\r' | awk -v r="$ROOM" '$1 == r {$1 = ""; print}')
[ -n "$DIRS" ] || { echo "FEHLER: Raum $ROOM nicht in $RUN"; exit 1; }
CAMS0=""; for d in $DIRS; do CAMS0="$CAMS0 ${d##*_}"; done
# LED-Hoehen nach Index bei gleicher Teilung (ledsa_h1_ledz.py, Korrektur 2026-11-24; idempotent, Quelle *_ledsa.csv)
for c in $CAMS0; do cd "$L" && PYTHONPATH= "$VENV" ledsa_h1_ledz.py "$RUN" "$c"; done
cd "$L" && "$PY" ledsa_h1_config.py analysis "$RUN" "$ROOM"
CAMS=""; for d in $DIRS; do CAMS="$CAMS ${d##*_}"; done
# Variante: nur die neu aufgenommenen Kameras rechnen (Rauschen, -a, Sockel); Hauptauswertung bleibt unberuehrt
VARCAMS=""; [ -n "$H1_VARIANT" ] && VARCAMS=$(cd "$L" && "$PY" ledsa_h1_config.py varcams "$RUN" | tr -d '\r')
[ -n "$H1_VARIANT" ] && CAMS="$VARCAMS"
cd "$L" && "$PY" ledsa_h1_noise.py "$RUN" $CAMS
for d in $DIRS; do
  if [ -n "$H1_VARIANT" ] && ! echo " $VARCAMS " | grep -q " ${d##*_} "; then
    echo "$d -a uebersprungen (Variante: Kamera der Hauptauswertung)"; continue
  fi
  t0=$(date +%s)
  (cd "$RUNS/$RUN/$d" && "$PY" -m ledsa -a > a_log.txt 2>&1) || { echo "FEHLER $d -a (a_log.txt)"; exit 1; }
  echo "$d -a ok ($(( $(date +%s) - t0 )) s)"
done
if [ "$(echo $DIRS | wc -w)" -eq 2 ]; then
  t0=$(date +%s)
  (cd "$RUNS/$RUN/$STK" && rm -f time_alignment_led_array_*.txt && "$PY" -m ledsa -as > as_log.txt 2>&1) \
    || { echo "FEHLER $STK -as (as_log.txt)"; exit 1; }
  echo "$STK -as ok ($(( $(date +%s) - t0 )) s)"
  grep -h -A2 "Alignment result" "$RUNS/$RUN/$STK"/time_alignment_led_array_0.txt 2>/dev/null | tail -2 || true
fi
cd "$L" && PYTHONPATH= "$VENV" ledsa_h1_mask.py flag "$RUN" "$ROOM"
for c in $CAMS; do cd "$L" && PYTHONPATH= "$VENV" ledsa_h1_mask.py pedestal "$RUN" "$c"; done
echo "FERTIG Raum $RUN $ROOM $(date '+%F %T')"
