#!/usr/bin/env python3
"""Phase 1 output: render the NH16 network as a real, zoomable map (Leaflet +
OpenStreetMap tiles), with the highway itself highlighted distinctly from
side roads/junctions pulled in around it. Requires netconvert to have been
run with --osm.all-attributes true (see scripts/build_network.sh) so each
edge's original OSM `ref` tag is retrievable.

Opens directly in any browser (double-click the output file) — no SUMO,
Kali, or VM needed to view it, since collision_claude/ is a shared folder.
"""
import json
import re
import sys

import sumolib

NET_FILE = "road/nh16.net.xml"
OUT_HTML = "road/nh16_map.html"

NH16_REF_RE = re.compile(r"NH\s*-?\s*(16|5)\b", re.IGNORECASE)


def is_nh16(edge):
    """An edge counts as 'the highway' if its OSM ref tag matches NH16/NH5,
    falling back to highway type (trunk/primary) if the ref param wasn't
    retained (e.g. netconvert was run without --osm.all-attributes)."""
    ref = edge.getParam("ref", "")
    if ref and NH16_REF_RE.search(ref):
        return True
    if not ref:
        etype = edge.getType() or ""
        return "trunk" in etype or "primary" in etype
    return False


def main():
    net = sumolib.net.readNet(NET_FILE)
    edges = net.getEdges()
    if not edges:
        print("No edges found in the network.", file=sys.stderr)
        sys.exit(1)

    highway_lines = []
    side_lines = []
    all_lats, all_lons = [], []

    for edge in edges:
        shape = edge.getShape()
        latlon = []
        for x, y in shape:
            lon, lat = net.convertXY2LonLat(x, y)
            latlon.append([lat, lon])
            all_lats.append(lat)
            all_lons.append(lon)
        (highway_lines if is_nh16(edge) else side_lines).append(latlon)

    if not all_lats:
        print("No coordinates extracted — check the network file.", file=sys.stderr)
        sys.exit(1)

    center_lat = sum(all_lats) / len(all_lats)
    center_lon = sum(all_lons) / len(all_lons)

    print(f"Highway edges: {len(highway_lines)}   Side-road edges: {len(side_lines)}")

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>NH16 Srikakulam to Visakhapatnam</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html, body {{ margin: 0; height: 100%; font-family: sans-serif; }}
  #map {{ height: 100%; }}
  .legend {{
    position: absolute; top: 10px; right: 10px; z-index: 1000;
    background: white; padding: 10px 14px; border-radius: 6px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.4); font-size: 14px;
  }}
  .legend div {{ margin: 4px 0; }}
  .swatch {{ display: inline-block; width: 24px; height: 4px; margin-right: 8px; vertical-align: middle; }}
</style>
</head>
<body>
<div id="map"></div>
<div class="legend">
  <div><span class="swatch" style="background:#e6392b;height:5px;"></span>NH16 highway ({len(highway_lines)} edges)</div>
  <div><span class="swatch" style="background:#7a7a7a;"></span>Side roads / junctions ({len(side_lines)} edges)</div>
</div>
<script>
var map = L.map('map').setView([{center_lat}, {center_lon}], 10);
// Using CartoDB's basemap tiles instead of the raw OSM tile server: OSM's
// own tile.openstreetmap.org enforces a Referer-header policy that blocks
// requests from a locally-opened file:// page (no Referer is sent), which
// is exactly how this file is meant to be viewed.
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
    maxZoom: 18,
    subdomains: 'abcd'
}}).addTo(map);

var sideRoads = {json.dumps(side_lines)};
sideRoads.forEach(function(coords) {{
    L.polyline(coords, {{color: '#7a7a7a', weight: 2, opacity: 0.8}}).addTo(map);
}});

var highway = {json.dumps(highway_lines)};
highway.forEach(function(coords) {{
    L.polyline(coords, {{color: '#e6392b', weight: 5, opacity: 0.95}}).addTo(map);
}});
</script>
</body>
</html>
"""
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved: {OUT_HTML}  (open directly in any browser)")


if __name__ == "__main__":
    main()
