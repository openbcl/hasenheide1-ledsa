#!/bin/bash
# Neulauf Stufe 3 nach der Korrektur vom 2026-11-24: LED-Hoehen nach Index (ledsa_h1_ledz.py), Juelich-Streifenenden
# 0,1517-2,535 m, Referenzbilder nur mit eigenen LEDs, LEM-Beginn mit Haltedauer. Fuer alle Raeume run_room.sh (auch
# wenn eine alte stage3-Marke existiert), Marke runs/<Lauf>/stage3r1_<Raum>_ok; danach Variante mitC1 und die
# Zerlegungsvarianten (checks/decompose_prior0100_run.sh). Wiederanlauf: fertige Raeume (Marke) werden uebersprungen.
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
unset H1_VARIANT        # Hauptschleife nie als Variante (sonst setzte sie die Hauptmarke)
LOGD="$RUNS/_logs/stage3_r1"; mkdir -p "$LOGD"
RUNLIST=$(cd "$L" && grep -v "^#" setup/ledsa_h1_runs.csv | tail -n +2 | cut -d, -f1 | tr -d '\r')
echo "Neulauf Start $(date '+%F %T')"
for RUN in $RUNLIST; do
  ROOMS=$(cd "$L" && "$VENV" ledsa_h1_config.py rooms "$RUN" 2>/dev/null | tr -d '\r' | grep -E "^F[0-9]" | cut -d' ' -f1)
  for ROOM in $ROOMS; do
    if [ -f "$RUNS/$RUN/stage3r1_${ROOM}_ok" ]; then echo "== $RUN $ROOM schon neu"; continue; fi
    t0=$(date +%s); LOGF="$LOGD/${RUN}_${ROOM}.log"
    if bash "$TOOLS/run_room.sh" "$RUN" "$ROOM" > "$LOGF" 2>&1 && grep -q "^FERTIG Raum $RUN $ROOM" "$LOGF"; then
      touch "$RUNS/$RUN/stage3r1_${ROOM}_ok"; echo "ok $RUN $ROOM $(( $(date +%s) - t0 )) s"
      grep -E "Referenzbilder|\[!\]" "$LOGF" | sed 's/^/   /'
    else
      echo "FEHLER $RUN $ROOM:"; grep -v -i warn "$LOGF" | tail -5 | sed 's/^/   /'
    fi
  done
done
if [ ! -f "$RUNS/Hep_160_S2_R1/stage3r1_F2_mitC1_ok" ]; then
  H1_VARIANT=mitC1 bash "$TOOLS/run_room.sh" Hep_160_S2_R1 F2 > "$LOGD/Hep_160_S2_R1_F2_mitC1.log" 2>&1 \
    && touch "$RUNS/Hep_160_S2_R1/stage3r1_F2_mitC1_ok" && echo "ok Variante mitC1" || echo "FEHLER Variante mitC1"
fi
(cd "$L" && PYTHONPATH= "$VENV" checks/decompose_prior0100.py "$L" make > "$LOGD/decompose_make.log" 2>&1)
bash "$L/checks/decompose_prior0100_run.sh" > "$LOGD/decompose_prior0100.log" 2>&1; grep -E "^ok|FEHLER" "$LOGD/decompose_prior0100.log" | tr '\n' ';'
echo
echo "NEULAUF FERTIG $(date '+%F %T')"
