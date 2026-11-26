#!/bin/bash
# Stufe 2 (H1): Nachfuehrung einer ausdruecklichen Serienliste (wie stage2_track.sh, aber ohne Aufteilung ueber
# stage2_order.py; angelegt 2026-11-23 fuer die nach dem genauen Lagecheck neu aufgenommenen Serien, waehrend die
# laufenden stage2_track.sh-Warteschlangen ihre Listen schon festgelegt hatten). Wartet je Serie auf stage2_s3_ok,
# danach tools/stage2_trackcheck.py. Aufruf: stage2_track_list.sh <Lauf>:<Kamera> [...]
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
ledsa_env > /dev/null || exit 1
LOGD="$RUNS/_logs/stage2"; mkdir -p "$LOGD"
echo "Nachfuehrung Liste Start $(date '+%F %T'): $*"
for rc in "$@"; do
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
    grep -E "^\[ok\]" "$LOGF"
    (cd "$L" && PYTHONPATH= "$VENV" tools/stage2_trackcheck.py "$RUN:$CAM" | tr -d '\r') || echo "PRUEFUNG FEHLER $RUN $CAM (s. oben)"
    echo "ende $(date '+%F %T')"
  else
    echo "FEHLER $RUN $CAM (Ende von $LOGF):"; grep -v -i warn "$LOGF" | tail -6
    echo "ABBRUCH Nachfuehrung Liste $(date '+%F %T')"; exit 2
  fi
done
echo "NACHFUEHRUNG LISTE FERTIG $(date '+%F %T')"
