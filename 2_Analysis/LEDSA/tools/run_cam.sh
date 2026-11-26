#!/bin/bash
# LEDSA-Kette je Kamera (H1, LEDSA 0.13.0): config, -s1, edges, -s2, -coord, -s3_fast -rgb (alle drei Kanaele ohne
# Fit, mit Fernfeld-Sockel), Bilder direkt aus der Bildablage (H1_IMAGES_ROOT). Vorher: ledsa_h1_s1scan.py und Fenster in
# setup/ledsa_h1_strip_windows.csv auf "geprueft". Laufzeiten je Schritt in <Arbeitsordner>/timing.txt.
# Aufruf: run_cam.sh <Lauf> <Kamera>
set -eo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
RUN=$1; CAM=$2
ledsa_env
cam_dir "$RUN" "$CAM"
W="$RUNS/$RUN/$D"
step() {   # step <Name> <Befehl...>: Laufzeit protokollieren
  local name=$1; shift; local t0=$(date +%s)
  "$@"; local rc=$?
  echo "$name $(( $(date +%s) - t0 )) s" >> "$W/timing.txt"; return $rc
}
cd "$L" && "$PY" ledsa_h1_config.py config "$RUN" "$CAM" | tail -1
rm -f "$W/timing.txt"; echo "start $(date '+%F %T')" > "$W/timing.txt"
cd "$W" && step s1 bash -c "'$PY' -m ledsa -s1 > s1_log.txt 2>&1"; grep -E "Threshold|Found|found" s1_log.txt | tail -2 || true
cd "$L" && "$PY" ledsa_h1_config.py edges "$RUN" "$CAM"
cd "$W" && step s2 bash -c "'$PY' -m ledsa -s2 > s2_log.txt 2>&1"; grep -E "not matched|Generated" s2_log.txt || true
step coord bash -c "'$PY' -m ledsa -coord > coord_log.txt 2>&1"; tail -1 coord_log.txt
# LED-Hoehen nach Index bei gleicher Teilung (Korrektur 2026-11-24)
cd "$L" && PYTHONPATH= "$VENV" ledsa_h1_ledz.py "$RUN" "$CAM"; cd "$W"
step s3 bash -c "'$PY' -m ledsa -s3_fast -rgb > s3_log.txt 2>&1"
echo "s3: $(ls analysis/channel0 | grep -c led_positions) / $(ls analysis/channel1 | grep -c led_positions) / $(ls analysis/channel2 | grep -c led_positions) Bilder (Kanal 0/1/2)"
echo "ende $(date '+%F %T')" >> "$W/timing.txt"
echo "FERTIG $RUN $CAM"
