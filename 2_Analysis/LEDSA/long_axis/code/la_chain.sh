#!/bin/bash
# Kette je Kamera der langen Sichtachse (LEDSA 0.13.0), wie tools/run_cam.sh der Raumauswertung plus Inversion und Maske:
# config, -s1, edges (Horizont-Probe), -s2, -coord, ledz, -s3_fast -rgb, analysis (Referenzbilder), -a, noise, mask.
# Vorher: la.py scan und Fenster in setup/la_windows.csv auf "geprueft".
# Aufruf: la_chain.sh <Lauf> <Kamera> [ab_schritt]   (Schritte: config s1 edges s2 coord ledz s3 analysis a noise mask)
# Umgebung wie die Raumauswertung: tools/env.sh (LEDSA_EXPORT, LEDSA_PY, HH2_PY); Raumauswertung = ../.. oder H1_LEDSA_REPO.
set -eo pipefail
RUN=$1; CAM=$2; FROM=${3:-config}
CODE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS="${H1_LEDSA_REPO:+$(cygpath "$H1_LEDSA_REPO")/tools}"
source "${TOOLS:-$CODE/../../tools}/env.sh"
ledsa_env
POS=$("$PY" -c "import sys; sys.path.insert(0, r'$(cygpath -w "$CODE")'); import la; print(la.series('$RUN', '$CAM').position)" | tr -d '\r')
W="$CODE/../runs/$RUN/${POS}_$CAM"
mkdir -p "$W"
LOG="$W/chain_log.txt"
go=0
step() {   # step <Name> <Befehl...>
  local name=$1; shift
  [ "$name" = "$FROM" ] && go=1
  [ $go = 1 ] || return 0
  local t0=$(date +%s)
  echo "== $name $(date '+%F %T')" | tee -a "$LOG"
  "$@" >> "$LOG" 2>&1 || { echo "FEHLER in $name (s. $LOG)"; tail -5 "$LOG"; exit 1; }
  echo "   $name $(( $(date +%s) - t0 )) s" | tee -a "$LOG"
  [ "$name" = "${UNTIL:-}" ] && { echo "Halt nach $name (UNTIL)"; exit 0; }
  return 0
}
la() { (cd "$CODE" && "$PY" la.py "$@"); }
ledsa() { (cd "$W" && "$PY" -m ledsa "$@"); }
step config   la config "$RUN" "$CAM"
step s1       ledsa -s1
step edges    la edges "$RUN" "$CAM"
step s2       ledsa -s2
step coord    ledsa -coord
step ledz     la ledz "$RUN" "$CAM"
step s3       ledsa -s3_fast -rgb
step analysis la analysis "$RUN" "$CAM"
step a        ledsa -a
step noise    la noise "$RUN" "$CAM"
step mask     la mask "$RUN" "$CAM"
grep -E "Horizont|Array [01]|Referenz|Saettigung|gesperrt|sigma_sum" "$LOG" | tail -30
echo "FERTIG $RUN $CAM"
