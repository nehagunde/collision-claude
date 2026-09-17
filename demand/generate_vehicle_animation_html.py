#!/usr/bin/env python3
"""Phase 2 output: turn the headless-run FCD trace into a self-contained,
animated HTML page — 100 vehicles moving on the real NH16 map, color-coded
by group (through/merge/crossing/wrong-way), with play/pause and a time
slider. Open directly in any browser, no SUMO/VM needed.

Requires output/phase2_fcd.xml, produced by scripts/run_phase2_preview.sh
with --fcd-output.geo true (so positions are already lon/lat, no sumolib
projection conversion needed here).
"""
import json
import re
import xml.etree.ElementTree as ET

FCD_FILE = "output/phase2_fcd.xml"
OUT_HTML = "dashboard/vehicles_preview.html"

SAMPLE_EVERY_S = 5  # coarser sampling keeps the embedded JS data manageable

GROUP_COLORS = {
    "through": "#3f7cb0",
    "merge": "#e6890a",
    "crossing": "#8e44ad",
    "wrongway": "#e6392b",
    "other": "#7a7a7a",
}


def group_from_id(vid):
    for prefix, group in (("through_", "through"), ("merge_", "merge"),
                           ("cross_", "crossing"), ("wrongway_", "wrongway")):
        if vid.startswith(prefix):
            return group
    return "other"


def main():
    frames = []  # list of {time, vehicles:[{id,type,group,lon,lat}]}
    all_lons, all_lats = [], []

    context = ET.iterparse(FCD_FILE, events=("end",))
    for _, elem in context:
        if elem.tag != "timestep":
            continue
        t = float(elem.get("time"))
        if t % SAMPLE_EVERY_S != 0:
            elem.clear()
            continue
        vehicles = []
        for v in elem.findall("vehicle"):
            lon, lat = float(v.get("x")), float(v.get("y"))
            vid = v.get("id")
            vehicles.append({
                "id": vid,
                "type": v.get("type"),
                "group": group_from_id(vid),
                "lon": lon, "lat": lat,
            })
            all_lons.append(lon)
            all_lats.append(lat)
        frames.append({"time": t, "vehicles": vehicles})
        elem.clear()

    if not frames:
        raise SystemExit("No timesteps found in FCD output — check the run succeeded.")

    center_lat = sum(all_lats) / len(all_lats)
    center_lon = sum(all_lons) / len(all_lons)

    print(f"Frames: {len(frames)} (sampled every {SAMPLE_EVERY_S}s)")
    print(f"Peak concurrent vehicles: {max(len(f['vehicles']) for f in frames)}")

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>NH16 Vehicles Preview</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html, body {{ margin: 0; height: 100%; font-family: sans-serif; }}
  #map {{ height: calc(100% - 56px); }}
  #controls {{
    height: 56px; display: flex; align-items: center; gap: 12px;
    padding: 0 16px; background: #1c1c1c; color: white; box-sizing: border-box;
  }}
  #playBtn {{ cursor: pointer; padding: 6px 16px; border-radius: 4px; border: none;
              background: #3f7cb0; color: white; font-size: 14px; }}
  #slider {{ flex: 1; }}
  #timeLabel {{ min-width: 90px; font-variant-numeric: tabular-nums; }}
  .legend {{
    position: absolute; top: 10px; right: 10px; z-index: 1000;
    background: white; padding: 10px 14px; border-radius: 6px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.4); font-size: 13px;
  }}
  .legend div {{ margin: 3px 0; }}
  .dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%;
          margin-right: 6px; vertical-align: middle; }}
</style>
</head>
<body>
<div id="map"></div>
<div class="legend">
  <div><span class="dot" style="background:{GROUP_COLORS['through']}"></span>Through-traffic</div>
  <div><span class="dot" style="background:{GROUP_COLORS['merge']}"></span>Merging</div>
  <div><span class="dot" style="background:{GROUP_COLORS['crossing']}"></span>Crossing</div>
  <div><span class="dot" style="background:{GROUP_COLORS['wrongway']}"></span>Wrong-way</div>
</div>
<div id="controls">
  <button id="playBtn">Play</button>
  <input type="range" id="slider" min="0" max="{len(frames) - 1}" value="0" />
  <span id="timeLabel">t = 0s</span>
</div>
<script>
var frames = {json.dumps(frames)};
var groupColors = {json.dumps(GROUP_COLORS)};

var map = L.map('map').setView([{center_lat}, {center_lon}], 10);
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
    maxZoom: 18,
    subdomains: 'abcd'
}}).addTo(map);

var markers = {{}};  // vehicle id -> L.circleMarker

function showFrame(idx) {{
    var frame = frames[idx];
    var seen = {{}};
    frame.vehicles.forEach(function(v) {{
        seen[v.id] = true;
        if (!markers[v.id]) {{
            markers[v.id] = L.circleMarker([v.lat, v.lon], {{
                radius: 5, color: groupColors[v.group] || '#7a7a7a',
                fillOpacity: 0.9, weight: 1
            }}).addTo(map).bindPopup('');
        }}
        markers[v.id].setLatLng([v.lat, v.lon]);
        markers[v.id].setStyle({{color: groupColors[v.group] || '#7a7a7a'}});
        markers[v.id].getPopup().setContent(
            v.id + '<br>type: ' + v.type + '<br>group: ' + v.group
        );
        markers[v.id].addTo(map);
    }});
    // hide vehicles not present this frame (not yet departed / already arrived)
    Object.keys(markers).forEach(function(id) {{
        if (!seen[id]) map.removeLayer(markers[id]);
    }});
    document.getElementById('timeLabel').textContent = 't = ' + frame.time + 's';
    document.getElementById('slider').value = idx;
}}

var currentIdx = 0;
var playing = false;
var playTimer = null;

function step() {{
    currentIdx = (currentIdx + 1) % frames.length;
    showFrame(currentIdx);
}}

document.getElementById('slider').addEventListener('input', function(e) {{
    currentIdx = parseInt(e.target.value, 10);
    showFrame(currentIdx);
}});

document.getElementById('playBtn').addEventListener('click', function() {{
    playing = !playing;
    this.textContent = playing ? 'Pause' : 'Play';
    if (playing) {{
        playTimer = setInterval(step, 200);
    }} else {{
        clearInterval(playTimer);
    }}
}});

showFrame(0);
</script>
</body>
</html>
"""
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved: {OUT_HTML} (open directly in any browser)")


if __name__ == "__main__":
    main()
