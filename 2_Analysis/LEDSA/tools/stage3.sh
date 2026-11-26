#!/bin/bash
# Stufe 3 (H1, LEDSA 0.13.0): run_room.sh (Referenzbilder, Leserauschen, -a je Kamera, -as Stapel, Maske, Sockel) fuer
# alle Raeume, deren Kameras fertig sind: Marke stage2_s3_ok und, falls in setup/ledsa_h1_tracking.csv "ja",
# stage2_track_ok. Raeume mit offener Nachfuehrung werden uebersprungen (spaeterer Neustart holt sie nach); fertige
# Raeume tragen die Marke runs/<Lauf>/stage3_<Raum>_ok. Ein Fehler in einem Raum bricht nur diesen Raum ab.
# Log je Raum runs/_logs/stage3/<Lauf>_<Raum>.log. Aufruf: stage3.sh [<Lauf> ...]   (ohne Argument alle Laeufe)
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
ledsa_env > /dev/null || exit 1
LOGD="$RUNS/_logs/stage3"; mkdir -p "$LOGD"
RUNLIST="$*"
[ -n "$RUNLIST" ] || RUNLIST=$(cd "$L" && grep -v "^#" setup/ledsa_h1_runs.csv | tail -n +2 | cut -d, -f1 | tr -d '\r')
TRACK_JA=$(cd "$L" && grep -v "^#" setup/ledsa_h1_tracking.csv | awk -F, '$3 == "ja" {print $1":"$2}' | tr -d '\r')
echo "Stufe 3 Start $(date '+%F %T')"
for RUN in $RUNLIST; do
  ROOMS=$(cd "$L" && "$PY" ledsa_h1_config.py rooms "$RUN" 2>/dev/null | tr -d '\r' | grep -E "^F[0-9]")
  while read -r ROOM DIRS; do
    [ -n "$ROOM" ] || continue
    if [ -f "$RUNS/$RUN/stage3_${ROOM}_ok" ]; then echo "== $RUN $ROOM schon fertig"; continue; fi
    ready=1; why=""
    for d in $DIRS; do
      CAM=${d##*_}
      [ -f "$RUNS/$RUN/$d/stage2_s3_ok" ] || { ready=0; why="$why $CAM ohne Auslese"; }
      if echo "$TRACK_JA" | grep -qx "$RUN:$CAM" && [ ! -f "$RUNS/$RUN/$d/stage2_track_ok" ]; then
        ready=0; why="$why $CAM Nachfuehrung offen"
      fi
    done
    if [ $ready = 0 ]; then echo "-- $RUN $ROOM uebersprungen:$why"; continue; fi
    LOGF="$LOGD/${RUN}_${ROOM}.log"
    t0=$(date +%s)
    if bash "$TOOLS/run_room.sh" "$RUN" "$ROOM" > "$LOGF" 2>&1 && grep -q "^FERTIG Raum $RUN $ROOM" "$LOGF"; then
      touch "$RUNS/$RUN/stage3_${ROOM}_ok"
      echo "ok $RUN $ROOM ($DIRS) $(( $(date +%s) - t0 )) s"
      grep -E "Referenzbilder|Referenzfenster|gesperrt|led_ueber|\[!\]" "$LOGF" | grep -v "SNR [25] " | head -12 | sed 's/^/   /'
    else
      echo "FEHLER $RUN $ROOM (Ende von $LOGF):"; grep -v -i warn "$LOGF" | tail -5 | sed 's/^/   /'
    fi
  done <<< "$ROOMS"
done
echo "STUFE 3 FERTIG $(date '+%F %T')"
