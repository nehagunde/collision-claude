#!/usr/bin/env bash
# Phase 1 — end-to-end: fetch OSM data, build the SUMO network, render preview.
set -euo pipefail
cd "$(dirname "$0")/.."   # collision_claude/ root

bash scripts/fetch_nh16_osm.sh
echo
bash scripts/build_network.sh
echo
python3 scripts/plot_network.py
echo
python3 scripts/generate_network_html.py
echo
python3 scripts/generate_nh16_selection.py
