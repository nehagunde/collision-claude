#!/usr/bin/env bash
# Phase 2 — end-to-end: generate vehicles, summarize them, run a headless
# preview simulation, and render the animated HTML dashboard.
set -euo pipefail
cd "$(dirname "$0")/.."   # collision_claude/ root

python3 demand/generate_vehicles.py
echo
python3 demand/vehicle_summary.py
echo
bash scripts/run_phase2_preview.sh
echo
python3 demand/generate_vehicle_animation_html.py
