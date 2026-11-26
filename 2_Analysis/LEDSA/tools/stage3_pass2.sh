#!/bin/bash
# Stufe 3, zweiter Durchgang (2026-11-23, Lauf ueber Nacht): wartet, bis der erste Durchgang (runs/_logs/stage3.log,
# Zeile "STUFE 3 FERTIG") und alle Nachfuehrungs-Warteschlangen beendet sind (Zeilen "FERTIG"/"ABBRUCH"/"exit" in
# runs/_logs/stage2/stage2_track_1b.log, _listA.log, _listB.log), und startet dann stage3.sh erneut; der holt die
# Raeume nach, die im ersten Durchgang wegen offener Nachfuehrung uebersprungen wurden (fertige Raeume haben eine
# Marke). Ohne Parallelbetrieb -> keine Konkurrenz um denselben Raum.
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
LOGS="$RUNS/_logs"
done_track() {
  for f in stage2_track_1b stage2_track_listA stage2_track_listB; do
    grep -q -E "FERTIG|ABBRUCH|^exit" "$LOGS/stage2/$f.log" 2>/dev/null || return 1
  done
}
echo "Warte $(date '+%F %T')"
until grep -q "STUFE 3 FERTIG" "$LOGS/stage3.log" 2>/dev/null && done_track; do sleep 120; done
echo "Start zweiter Durchgang $(date '+%F %T')"
bash "$TOOLS/stage3.sh"
