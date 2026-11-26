#!/bin/bash
# Stufe 0, Test Ausduennung (METHODS.md section 4.1): derselbe Stapel mit voller J-Serie im Testordner
# runs/_stage0_voll. Untere Kamera: Kopie der Auslese aus runs/ (identisch). Referenzbilder der vollen J-Serie = dieselben
# Bilder (Dateinamen) wie in der ausgeduennten Variante, damit sich nur die Bildfolge unterscheidet.
# Aufruf: stage0_voll.sh <Lauf> <Raum> <Ordner unten> <Ordner oben>   (nach run_room.sh der ausgeduennten Variante)
set -eo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
RUN=$1; ROOM=$2; LO=$3; UP=$4
ledsa_env > /dev/null
V="$L/runs/_stage0_voll/$RUN"
rm -rf "$V/$LO" && cp -r "$RUNS/$RUN/$LO" "$V/"
export H1_LEDSA_RUNS="$(cygpath -m "$L/runs/_stage0_voll")"
cd "$L" && "$PY" ledsa_h1_config.py analysis "$RUN" "$ROOM" | grep -E "Referenzbilder|\[ok\]"
"$VENV" - "$RUNS/$RUN" "$V" "$LO" "$UP" "$ROOM" <<'EOF'
import re, sys
from pathlib import Path
import pandas as pd
thin, full, lo, up, room = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]
def refs(work):
    m = re.search(r"ref_img_indices = ([\d ]+)\s*$", (work / "config_analysis.ini").read_text(encoding="utf-8"), re.M)
    return [int(v) for v in m.group(1).split()]
def infos(work):
    d = pd.read_csv(work / "analysis" / "image_infos_analysis.csv"); d.columns = ["id", "name", "time", "t"]; return d
for cam_dir in (lo, up):
    ti, fi = infos(thin / cam_dir), infos(full / cam_dir)
    names = ti.set_index("id").loc[refs(thin / cam_dir), "name"].tolist()
    ids = fi.set_index("name").loc[names, "id"].tolist()
    s = " ".join(map(str, ids))
    f = full / cam_dir / "config_analysis.ini"
    f.write_text(re.sub(r"(ref_img_indices = )[\d ]+", lambda m: m.group(1) + s, f.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"{cam_dir}: Referenzbilder {names[0]}..{names[-1]} -> img_id {s}")
    st = full / f"stacked_{room}" / "config_stacked.ini"
    txt = st.read_text(encoding="utf-8")
    sec = 0 if cam_dir == lo else 1
    txt = re.sub(rf"(\[simulation_{sec}\][^\[]*?ref_img_indices = )[\d ]+", lambda m: m.group(1) + s, txt, flags=re.S)
    st.write_text(txt, encoding="utf-8")
EOF
for d in "$LO" "$UP"; do (cd "$V/$d" && "$PY" -m ledsa -a > a_log.txt 2>&1) && echo "$d -a ok"; done
(cd "$V/stacked_$ROOM" && rm -f time_alignment_led_array_*.txt && "$PY" -m ledsa -as > as_log.txt 2>&1) && echo "stacked_$ROOM -as ok"
echo "FERTIG stage0_voll $RUN $ROOM $(date '+%F %T')"
