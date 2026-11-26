#!/bin/bash
# Abgeleitete Datenprodukte nach dem Neulauf (Korrektur 2026-11-24), in Abhaengigkeitsreihenfolge:
# Saettigung -> Profile -> Stufe 4 -> Sockel-Wirkung -> Vergleich bisherige Staende -> Zerlegung. Log je Schritt in
# runs/_logs/post_rerun/. Bricht beim ersten Fehler ab.
set -eo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
LOGD="$RUNS/_logs/post_rerun"; mkdir -p "$LOGD"
cd "$L"
export PYTHONPATH=
run() { local n=$1; shift; echo "== $n $(date '+%T')"; "$@" > "$LOGD/$n.log" 2>&1 || { echo "FEHLER $n"; tail -5 "$LOGD/$n.log"; exit 1; }; }
run sat        "$VENV" ledsa_h1_stage4.py sat
run profiles   "$VENV" ledsa_h1_profiles.py all
run stage4_lem "$VENV" ledsa_h1_stage4.py lem
run pedestal_k "$VENV" checks/check_pedestal_k.py "$L" inventory/ledsa_h1_pedestal_k_effect.csv
TMP="$LOGD/compare_prior_out"; mkdir -p "$TMP"
run compare    "$VENV" checks/compare_prior.py "$L" "$TMP"
cp "$TMP/compare_prior_lem.csv" inventory/ledsa_h1_compare_prior_lem.csv
cp "$TMP/compare_prior_profiles.csv" inventory/ledsa_h1_compare_prior_profiles.csv
run decompose  "$VENV" checks/decompose_prior0100.py "$L" eval inventory
echo "POST FERTIG $(date '+%F %T')"
