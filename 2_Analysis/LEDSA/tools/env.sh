#!/bin/bash
# Gemeinsame Umgebung der H1-LEDSA-Kettenskripte (per "source" eingebunden, Git-Bash unter Windows); uebernommen
# aus der Hasenheide-2-Auswertung. Ueberschreibbar per Umgebungsvariable:
#   LEDSA_EXPORT   LEDSA-Code, Release-Tag v0.13.0 (git archive), Standard %LOCALAPPDATA%\ledsa_v0130
#   H1_LEDSA_RUNS  Arbeitsordner der Laeufe, Standard 2_Analysis/LEDSA/runs (auch von den Python-Skripten gelesen)
#   LEDSA_PY       Python des Conda-Env "ledsa" (rawpy, exiv2), Standard %USERPROFILE%\.conda\envs\ledsa\python.exe
#   HH2_PY         gepinntes venv (Auswertung, Figuren), Standard %LOCALAPPDATA%\hh2_analysis_venv\Scripts\python.exe
# Bilder werden direkt unter H1_IMAGES_ROOT gelesen (keine lokalen Kopien).
TOOLS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
L="$(cd "$TOOLS/.." && pwd)"                                   # 2_Analysis/LEDSA
LAD="$(cygpath "$LOCALAPPDATA")"
LEDSA_EXPORT="${LEDSA_EXPORT:-$LAD/ledsa_v0130}"
RUNS="${H1_LEDSA_RUNS:+$(cygpath "$H1_LEDSA_RUNS")}"
RUNS="${RUNS:-$L/runs}"
PY="${LEDSA_PY:-$(cygpath "$USERPROFILE")/.conda/envs/ledsa/python.exe}"
VENV="${HH2_PY:-$LAD/hh2_analysis_venv/Scripts/python.exe}"
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1

# LEDSA aus dem Export laden und pruefen (im Env liegt zusaetzlich ein aelteres LEDSA, Dateikoepfe nennen "0.9.4")
ledsa_env() {
  export PYTHONPATH="$(cygpath -w "$LEDSA_EXPORT")"
  "$PY" -c "import ledsa, sys; f = ledsa.__file__; print('LEDSA aus', f); sys.exit(0 if f.replace(chr(92), '/').lower().startswith('$(cygpath -m "$LEDSA_EXPORT")'.lower()) else 1)" \
    || { echo "FEHLER: LEDSA nicht aus $LEDSA_EXPORT geladen"; return 1; }
}

# Arbeitsordner einer Kamera: setzt D (<Position>_<Kamera>)
cam_dir() {   # cam_dir <Lauf> <Kamera>
  local out
  out=$(cd "$L" && "$VENV" -c "import pandas as pd; s=pd.read_csv('setup/ledsa_h1_series.csv',comment='#'); r=s[(s.run=='$1')&(s.cam=='$2')].iloc[0]; print(r.position)") || return 1
  out=${out//$'\r'/}
  D="${out}_$2"
}
