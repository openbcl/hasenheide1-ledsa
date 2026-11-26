#!/bin/bash
# Stufe 2 (H1, LEDSA 0.13.0): Auslese aller Serien (run_cam.sh) in der Reihenfolge von tools/stage2_order.py
# (zuerst die nachzufuehrenden, zuletzt Juelich-Serien mit abgeschnittenen RAWs). Je Serie: Lesetest einer Bilddatei
# aus der Bildablage, alte Auslese der Stufen 0/1 entfernen (analysis/channel*, Nachfuehrungsdateien; sie beruhen teils auf alten
# Referenzbildern der LED-Suche), run_cam.sh mit Log runs/_logs/stage2/<Lauf>_<Kamera>.log, bei Erfolg Marke
# <Arbeitsordner>/stage2_s3_ok (Neustart ueberspringt Fertiges; Hintergrundjobs brachen in Stufe 0 dreimal still ab).
# Aufruf: stage2.sh   (Ausgabe in eine Logdatei umleiten)
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
ledsa_env > /dev/null || exit 1
LIST=$(cd "$L" && "$VENV" tools/stage2_order.py | tr -d '\r' | awk '{print $1}')
[ -n "$LIST" ] || { echo "FEHLER: keine Serienliste"; exit 1; }
LOGD="$RUNS/_logs/stage2"; mkdir -p "$LOGD"
echo "Stufe 2 Auslese Start $(date '+%F %T'), $(echo $LIST | wc -w) Serien"
for rc in $LIST; do
  RUN=${rc%%:*}; CAM=${rc##*:}
  cam_dir "$RUN" "$CAM" || { echo "FEHLER $RUN $CAM: Arbeitsordner"; continue; }
  W="$RUNS/$RUN/$D"
  if [ -f "$W/stage2_s3_ok" ]; then echo "== $RUN $CAM schon fertig"; continue; fi
  f=$(cd "$L" && "$VENV" -c "import pandas as pd; from ledsa_h1_paths import img_path; s=pd.read_csv('setup/ledsa_h1_series.csv',comment='#'); r=s[(s.run=='$RUN')&(s.cam=='$CAM')].iloc[0]; print(img_path(r.folder_w) + chr(92) + r.name_string.format(int(r.ref_s1_id)))")
  f=$(cygpath "${f//$'\r'/}")
  t0=$(date +%s.%N); cat "$f" > /dev/null; rc=$?; t1=$(date +%s.%N); sz=$(stat -c %s "$f" 2>/dev/null || echo 0)
  if [ $rc -ne 0 ] || [ "$sz" -lt 1000000 ]; then   # Bildablage weg (2026-11-23): Warteschlange anhalten statt Luecken erzeugen
    echo "ABBRUCH $(date '+%F %T'): Lesetest Bildablage fehlgeschlagen ($f, rc $rc, $sz Byte)"; exit 2
  fi
  echo "===== $RUN $CAM $(date '+%F %T'), Lesetest Bildablage $(awk -v z=$sz -v a=$t0 -v b=$t1 'BEGIN{printf "%.1f MB/s", z/1e6/(b-a)}')"
  # corrupted_images.csv mit entfernen: LEDSA haengt an, alte Eintraege (z. B. Ausfall der Bildablage 2026-11-23) taeuschten sonst
  # stage2_check.py
  rm -rf "$W"/analysis/channel0* "$W"/analysis/channel1* "$W"/analysis/channel2* \
         "$W/analysis/tracked_positions.csv.gz" "$W/analysis/tracking_log.csv" "$W/stage2_track_ok" \
         "$W/analysis/corrupted_images.csv"
  LOGF="$LOGD/${RUN}_${CAM}.log"
  if bash "$TOOLS/run_cam.sh" "$RUN" "$CAM" > "$LOGF" 2>&1 && grep -q "^FERTIG $RUN $CAM" "$LOGF"; then
    if CHK=$(cd "$L" && PYTHONPATH= "$VENV" tools/stage2_check.py "$W" | tr -d '\r'); then
      touch "$W/stage2_s3_ok"
    else
      CHK="$CHK -> keine Marke; Lesetest der naechsten Serie entscheidet ueber Abbruch"
    fi
    echo "$CHK"
    grep -E "not matched" "$LOGF" | tr '\n' ' '; tr '\n' ' ' < "$W/timing.txt"; echo
  else
    echo "FEHLER $RUN $CAM (Ende von $LOGF):"; grep -v -i warn "$LOGF" | tail -6
  fi
done
echo "AUSLESE FERTIG $(date '+%F %T')"
