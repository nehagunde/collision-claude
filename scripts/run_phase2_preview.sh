#!/usr/bin/env bash
# Phase 2 — run a plain headless SUMO simulation (no NS-3/TraCI yet, that's
# Phase 3) purely to record vehicle movement for the preview animation.
set -euo pipefail
cd "$(dirname "$0")/.."   # collision_claude/ root

if [ ! -f sim/sumo/routes.rou.xml ]; then
    echo "sim/sumo/routes.rou.xml not found — run demand/generate_vehicles.py first." >&2
    exit 1
fi

sumo -c sim/sumo/collision.sumocfg \
     --fcd-output output/phase2_fcd.xml \
     --fcd-output.geo true \
     --step-length 1

echo "Saved: output/phase2_fcd.xml"
wc -l output/phase2_fcd.xml
