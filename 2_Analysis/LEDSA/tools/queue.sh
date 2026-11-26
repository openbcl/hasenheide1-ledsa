#!/bin/bash
# Warteschlange: run_cam.sh fuer mehrere Kameras nacheinander, vorher Lesetest einer Bilddatei der Bildablage (die Ablage brach am
# 19.11. phasenweise auf 0,03-0,12 MB/s ein; normal 40-86 MB/s). Aufruf: queue.sh "<Lauf> <Kamera>" ["<Lauf> <Kamera>" ...]
# Fuer Parallelbetrieb mehrfach mit verschiedenen Kameras starten (Ausgabe in eine Logdatei umleiten).
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
for rc in "$@"; do
  set -- $rc
  f=$(cd "$L" && "$VENV" -c "import pandas as pd; from ledsa_h1_paths import img_path; s=pd.read_csv('setup/ledsa_h1_series.csv',comment='#'); r=s[(s.run=='$1')&(s.cam=='$2')].iloc[0]; print(img_path(r.folder_w) + '\\\\' + r.name_string.format(int(r.first_id)))")
  f=${f//$'\r'/}
  t0=$(date +%s.%N); cat "$(cygpath "$f")" > /dev/null; t1=$(date +%s.%N)
  sz=$(stat -c %s "$(cygpath "$f")")
  echo "===== $1 $2 $(date '+%F %T'), Lesetest Bildablage $(awk -v z=$sz -v a=$t0 -v b=$t1 'BEGIN{printf "%.1f MB/s", z/1e6/(b-a)}')"
  bash "$TOOLS/run_cam.sh" "$1" "$2" 2>&1 | grep -v -i "warn" || echo "FEHLER $1 $2"
done
echo "QUEUE FERTIG $(date '+%F %T')"
