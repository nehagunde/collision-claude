#!/usr/bin/env bash
# Phase 1 — pull the real NH16 Srikakulam -> Visakhapatnam alignment from
# OpenStreetMap via the Overpass API (Overpass allows a larger bbox + tag
# filter than the plain OSM API, which is needed for a ~100 km stretch).
set -euo pipefail
cd "$(dirname "$0")/.."   # collision_claude/ root
mkdir -p road

# Bounding box (south,west,north,east) with a buffer around both endpoints.
# ref regex covers current tag (NH16) and the pre-2010 legacy tag (NH 5),
# since not all OSM edits in the area may have been updated to the new number.
#
# Two-stage query: first select the NH16 ways themselves, then select any
# secondary/tertiary road within 400 m of that alignment ("around" filter) —
# this pulls in real intersecting junctions (the roads that actually matter
# for traffic) without pulling in entire town street grids. residential/
# unclassified are deliberately excluded: an earlier version included them
# and pulled in 12,552 edges (mostly dense in-town residential lanes near
# Srikakulam/Vizag/towns along the route) — far more than needed and heavy
# to render/simulate.
cat > road/nh16_overpass.ql <<'EOF'
[out:xml][timeout:180];
way["highway"~"trunk|primary|trunk_link|primary_link"]["ref"~"NH.?16|NH.?5"](17.60,83.10,18.40,84.00) -> .nh16;
way(around.nh16:400)["highway"~"trunk|primary|secondary|tertiary|trunk_link|primary_link|secondary_link|tertiary_link"] -> .nearby;
(.nh16; .nearby;);
(._;>;);
out body;
EOF

echo "Querying Overpass API for NH16 (Srikakulam <-> Visakhapatnam)..."

# Try a couple of mirrors in case one is overloaded (the main overpass-api.de
# instance frequently returns "server too busy" errors under load).
MIRRORS=(
    "https://overpass.kumi.systems/api/interpreter"
    "https://overpass-api.de/api/interpreter"
    "https://lz4.overpass-api.de/api/interpreter"
)

# Fetch into a temp file first — never overwrite the previous good
# road/nh16.osm with a failed/partial response, so a silent failure can't
# leave stale data in place for the next step to build from unnoticed.
TMP_OSM="road/.nh16.osm.tmp"
got_data=0
for url in "${MIRRORS[@]}"; do
    echo "Trying: $url"
    # The around:400 spatial-join query is much heavier for Overpass to
    # compute than a plain ref match, so give it real time to finish (the
    # query itself declares [timeout:180] to the server) rather than
    # timing out client-side while it's still legitimately working.
    curl -sS -G "$url" \
         --ipv4 \
         --connect-timeout 10 --max-time 240 \
         --retry 1 --retry-delay 5 --retry-all-errors \
         --data-urlencode "data@road/nh16_overpass.ql" \
         -o "$TMP_OSM" || true
    if grep -q "<osm" "$TMP_OSM" 2>/dev/null; then
        echo "Got valid OSM data from $url"
        got_data=1
        break
    fi
    echo "  -> no valid OSM data from this mirror, trying next..."
done

if [ "$got_data" -ne 1 ]; then
    echo
    echo "ERROR: none of the Overpass mirrors returned valid OSM data." >&2
    echo "Last response saved at $TMP_OSM for inspection (not moved to road/nh16.osm)." >&2
    exit 1
fi

mv "$TMP_OSM" road/nh16.osm
echo
echo "Saved: road/nh16.osm"
wc -l road/nh16.osm
way_count=$(grep -c '<way ' road/nh16.osm) || way_count=0
node_count=$(grep -c '<node ' road/nh16.osm) || node_count=0
echo "Way count: $way_count"
echo "Node count: $node_count"

if [ "$way_count" -eq 0 ]; then
    echo
    echo "WARNING: 0 ways matched. The ref tag on this stretch may be tagged"
    echo "differently in OSM than expected — open road/nh16.osm or widen the"
    echo "ref regex in this script's Overpass query and re-run."
fi
