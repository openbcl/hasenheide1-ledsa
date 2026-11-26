#!/bin/bash
# Stufe 2 (H1): Nachfuehrung (ledsa_h1_track.py) der Serien der Gruppe 1 aus tools/stage2_order.py, Teil i von N
# (parallel zu stage2.sh). Wartet je Serie auf die Marke stage2_s3_ok der Auslese; gibt auf, wenn die Auslese ohne
# Marke fertig ist (Zeile "AUSLESE FERTIG" in runs/_logs/stage2/stage2.log). Log je Serie
# runs/_logs/stage2/track_<Lauf>_<Kamera>.log, bei Erfolg Marke <Arbeitsordner>/stage2_track_ok.
# Aufruf: stage2_track.sh <i> <N>
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
I=$1; N=$2
ledsa_env > /dev/null || exit 1
LIST=$(cd "$L" && "$VENV" tools/stage2_order.py | tr -d '\r' | awk -v i=$I -v n=$N '$2 == 1 {if (k++ % n == i) print $1}')
LOGD="$RUNS/_logs/stage2"; mkdir -p "$LOGD"
echo "Nachfuehrung Teil $I/$N Start $(date '+%F %T'): $LIST"
for rc in $LIST; do
  RUN=${rc%%:*}; CAM=${rc##*:}
  cam_dir "$RUN" "$CAM" || { echo "FEHLER $RUN $CAM: Arbeitsordner"; continue; }
  W="$RUNS/$RUN/$D"
  if [ -f "$W/stage2_track_ok" ]; then echo "== $RUN $CAM schon nachgefuehrt"; continue; fi
  while [ ! -f "$W/stage2_s3_ok" ]; do
    if grep -q -E "AUSLESE FERTIG|ABBRUCH" "$LOGD/stage2.log" 2>/dev/null; then break; fi
    sleep 60
  done
  [ -f "$W/stage2_s3_ok" ] || { echo "FEHLER $RUN $CAM: Auslese ohne Erfolg, keine Nachfuehrung"; continue; }
  echo "===== $RUN $CAM $(date '+%F %T')"
  LOGF="$LOGD/track_${RUN}_${CAM}.log"
  if (cd "$W" && "$PY" -u "$L/ledsa_h1_track.py" > "$LOGF" 2>&1) && grep -q "^\[ok\]" "$LOGF"; then
    touch "$W/stage2_track_ok"
    grep -E "Start:|^\[ok\]|\[!\]" "$LOGF" | head -8; echo "ende $(date '+%F %T')"
  else
    echo "FEHLER $RUN $CAM (Ende von $LOGF):"; grep -v -i warn "$LOGF" | tail -6
    echo "ABBRUCH Nachfuehrung Teil $I $(date '+%F %T')"; exit 2   # meist Bildablage weg; Serie bleibt ohne Marke
  fi
done
echo "NACHFUEHRUNG TEIL FERTIG $I $(date '+%F %T')"
