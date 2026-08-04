#!/usr/bin/env bash
# Phase 1 — convert the raw OSM extract into a SUMO network.
set -euo pipefail
cd "$(dirname "$0")/.."   # collision_claude/ root

if [ ! -f road/nh16.osm ]; then
    echo "road/nh16.osm not found — run scripts/fetch_nh16_osm.sh first." >&2
    exit 1
fi

netconvert \
    --osm-files road/nh16.osm \
    --output-file road/nh16.net.xml \
    --geometry.remove \
    --roundabouts.guess \
    --ramps.guess \
    --junctions.join \
    --tls.guess-signals \
    --tls.discard-simple \
    --remove-edges.isolated \
    --osm.all-attributes true

echo "Built: road/nh16.net.xml"
