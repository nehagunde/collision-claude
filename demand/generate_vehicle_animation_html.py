#!/usr/bin/env python3
"""Phase 2 output: a self-contained, presentation-style animated dashboard —
matching the style of the other VANET project's schematic GUI (dark theme,
stylized road path, live stats, per-vehicle speed list, legend, play/reset/
speed controls) instead of a real map-tile view.

No external tiles or CDN map dependency at all (fixes the CartoDB-API-key
issue and the "shows half of Andhra Pradesh" problem in one move) — the road
is drawn as an inline SVG schematic, projected from the real NH16 geometry
so its bends still reflect the actual route, just abstracted like a metro
map rather than literal satellite/street imagery.

Requires:
- road/nh16.net.xml       (Phase 1)
- sim/sumo/routes.rou.xml (Phase 2, generate_vehicles.py)
- output/phase2_fcd.xml   (Phase 2, scripts/run_phase2_preview.sh,
                            --fcd-output.geo true)
"""
import json
import math
import re
import xml.etree.ElementTree as ET

import sumolib

NET_FILE = "road/nh16.net.xml"
ROUTES_FILE = "sim/sumo/routes.rou.xml"
FCD_FILE = "output/phase2_fcd.xml"
OUT_HTML = "dashboard/vehicles_preview.html"

SAMPLE_EVERY_S = 5

NH16_REF_RE = re.compile(r"NH\s*-?\s*(16|5)\b", re.IGNORECASE)

GROUP_COLORS = {
    "through": "#3f7cb0",
    "merge": "#e6890a",
    "crossing": "#8e44ad",
    "wrongway": "#e6392b",
    "other": "#7a7a7a",
}
GROUP_LABELS = {
    "through": "Through-traffic",
    "merge": "Merging",
    "crossing": "Crossing",
    "wrongway": "Wrong-way",
}

# schematic canvas geometry
SVG_W, SVG_H = 1400, 420
MARGIN_X = 90
ROAD_Y = 220
BEND_SCALE = 2200  # exaggerates real lateral bends so the schematic isn't a flat line


def is_nh16(edge):
    ref = edge.getParam("ref", "")
    if ref and NH16_REF_RE.search(ref):
        return True
    if not ref:
        etype = edge.getType() or ""
        return "trunk" in etype or "primary" in etype
    return False


def group_from_id(vid):
    for prefix, group in (("through_", "through"), ("merge_", "merge"),
                           ("cross_", "crossing"), ("wrongway_", "wrongway")):
        if vid.startswith(prefix):
            return group
    return "other"


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def build_projector(net, nh16_edges):
    """Projects real (lat, lon) onto the schematic canvas: x follows
    position along the Srikakulam->Vizag axis, y follows perpendicular
    deviation from that straight line (exaggerated) so real bends still
    show, without needing real map tiles."""
    pts = []
    for e in nh16_edges:
        for x, y in e.getShape():
            lon, lat = net.convertXY2LonLat(x, y)
            pts.append((lat, lon))

    north = max(pts, key=lambda p: p[0])   # Srikakulam end
    south = min(pts, key=lambda p: p[0])   # Visakhapatnam end
    dx, dy = south[1] - north[1], south[0] - north[0]
    length2 = dx * dx + dy * dy
    total_km = haversine_km(north[0], north[1], south[0], south[1])

    def project(lat, lon):
        vx, vy = lon - north[1], lat - north[0]
        t = (vx * dx + vy * dy) / length2
        t = max(0.0, min(1.0, t))
        cross = vx * dy - vy * dx
        perp = cross / math.sqrt(length2)
        px = MARGIN_X + t * (SVG_W - 2 * MARGIN_X)
        py = ROAD_Y + perp * BEND_SCALE
        return px, py, t

    return project, total_km


def main():
    net = sumolib.net.readNet(NET_FILE)
    nh16_edges = [e for e in net.getEdges() if is_nh16(e)]
    if not nh16_edges:
        raise SystemExit("No NH16 edges found — check road/nh16.net.xml")

    project, total_km = build_projector(net, nh16_edges)
    print(f"Route length (endpoint-to-endpoint): ~{total_km:.1f} km")

    # --- schematic road path (drawn once, static) ---
    road_points = []
    for e in nh16_edges:
        for x, y in e.getShape():
            lon, lat = net.convertXY2LonLat(x, y)
            px, py, t = project(lat, lon)
            road_points.append((t, px, py))
    road_points.sort(key=lambda p: p[0])
    road_path_xy = [[px, py] for _, px, py in road_points]

    # --- junction markers: the real junctions our merge/crossing vehicles use ---
    tree = ET.parse(ROUTES_FILE)
    root = tree.getroot()
    junctions = {}
    for veh in root.findall("vehicle"):
        vid = veh.get("id")
        group = group_from_id(vid)
        if group not in ("merge", "crossing"):
            continue
        first_edge_id = veh.find("route").get("edges").split()[0]
        edge = net.getEdge(first_edge_id)
        node = edge.getToNode()
        if node.getID() in junctions:
            continue
        x, y = node.getCoord()
        lon, lat = net.convertXY2LonLat(x, y)
        px, py, t = project(lat, lon)
        junctions[node.getID()] = {
            "x": px, "y": py, "km": round(t * total_km, 1), "group": group,
        }
    print(f"Junction markers: {len(junctions)}")

    # --- FCD frames ---
    frames = []
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
            px, py, _ = project(lat, lon)
            vid = v.get("id")
            vehicles.append({
                "id": vid, "type": v.get("type"), "group": group_from_id(vid),
                "x": px, "y": py, "speed": round(float(v.get("speed")) * 3.6, 1),  # -> km/h
            })
        frames.append({"time": t, "vehicles": vehicles})
        elem.clear()

    if not frames:
        raise SystemExit("No timesteps found in FCD output — check the run succeeded.")

    print(f"Frames: {len(frames)} (sampled every {SAMPLE_EVERY_S}s)")
    print(f"Peak concurrent vehicles: {max(len(f['vehicles']) for f in frames)}")

    group_counts = {}
    for v in root.findall("vehicle"):
        g = group_from_id(v.get("id"))
        group_counts[g] = group_counts.get(g, 0) + 1

    road_d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in road_path_xy)

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>NH16 Collision-Warning — Vehicle Preview</title>
<style>
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; height: 100%; background: #0f1620; color: #e8edf2;
                font-family: 'Segoe UI', sans-serif; }}
  #layout {{ display: flex; flex-direction: column; height: 100%; }}
  #header {{
    padding: 14px 20px; background: #131c28; border-bottom: 1px solid #22303f;
    display: flex; align-items: center; justify-content: space-between;
  }}
  #header h1 {{ font-size: 17px; margin: 0; }}
  #header .sub {{ font-size: 12px; color: #8fa3b8; margin-top: 2px; }}
  #clock {{ font-size: 22px; color: #4fc3f7; font-variant-numeric: tabular-nums; }}
  #body {{ flex: 1; display: flex; overflow: hidden; }}
  #canvasWrap {{ flex: 1; position: relative; }}
  svg {{ width: 100%; height: 100%; }}
  .junction-label {{ fill: #8fa3b8; font-size: 11px; }}
  #sidebar {{
    width: 260px; background: #131c28; border-left: 1px solid #22303f;
    padding: 14px; overflow-y: auto; font-size: 13px;
  }}
  .panel {{ margin-bottom: 18px; }}
  .panel h3 {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em;
               color: #8fa3b8; margin: 0 0 8px; }}
  .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
  .stat-box {{ background: #1a2531; border-radius: 6px; padding: 8px; text-align: center; }}
  .stat-box .n {{ font-size: 20px; font-weight: 600; color: #4fc3f7; }}
  .stat-box .l {{ font-size: 10px; color: #8fa3b8; }}
  .speed-row {{ display: flex; align-items: center; gap: 6px; margin: 4px 0; font-size: 11px; }}
  .speed-row .dot {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}
  .speed-row .id {{ width: 74px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .speed-row .bar-bg {{ flex: 1; background: #1a2531; border-radius: 3px; height: 6px; overflow: hidden; }}
  .speed-row .bar {{ height: 100%; border-radius: 3px; }}
  .speed-row .kmh {{ width: 44px; text-align: right; color: #8fa3b8; }}
  .legend-row {{ display: flex; align-items: center; gap: 8px; margin: 5px 0; font-size: 12px; }}
  .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; }}
  #controls {{
    height: 60px; background: #131c28; border-top: 1px solid #22303f;
    display: flex; align-items: center; gap: 14px; padding: 0 20px;
  }}
  button {{ cursor: pointer; padding: 7px 18px; border-radius: 5px; border: none;
            background: #3f7cb0; color: white; font-size: 13px; }}
  button.secondary {{ background: #2a3a4a; }}
  #slider {{ flex: 1; }}
  #timeLabel {{ min-width: 90px; text-align: right; font-variant-numeric: tabular-nums; color: #8fa3b8; }}
</style>
</head>
<body>
<div id="layout">
  <div id="header">
    <div>
      <h1>NH16 Collision-Warning — Vehicle Preview (Phase 2)</h1>
      <div class="sub">{sum(group_counts.values())} vehicles &middot; pure V2V (no RSU) &middot; 802.11p OCB mode &middot; ~{total_km:.0f} km corridor</div>
    </div>
    <div id="clock">T = 0s</div>
  </div>
  <div id="body">
    <div id="canvasWrap">
      <svg viewBox="0 0 {SVG_W} {SVG_H}">
        <path d="{road_d}" stroke="#3a4a5c" stroke-width="10" fill="none" stroke-linecap="round"/>
        <path d="{road_d}" stroke="#c9a227" stroke-width="1.5" stroke-dasharray="10 10" fill="none" opacity="0.6"/>
        <text x="{MARGIN_X}" y="{SVG_H - 18}" fill="#8fa3b8" font-size="12">&#9664; Srikakulam</text>
        <text x="{SVG_W - MARGIN_X}" y="{SVG_H - 18}" fill="#8fa3b8" font-size="12" text-anchor="end">Visakhapatnam &#9654;</text>
        <g id="junctions">
"""
    for jid, j in junctions.items():
        color = GROUP_COLORS[j["group"]]
        html += (f'          <rect x="{j["x"]-4}" y="{j["y"]-4}" width="8" height="8" '
                 f'fill="{color}" stroke="#0f1620" stroke-width="1"/>\n'
                 f'          <text class="junction-label" x="{j["x"]+7}" y="{j["y"]-8}">'
                 f'~{j["km"]}km</text>\n')
    html += """        </g>
        <g id="vehicles"></g>
      </svg>
    </div>
    <div id="sidebar">
      <div class="panel">
        <h3>Live stats</h3>
        <div class="stat-grid">
          <div class="stat-box"><div class="n" id="statActive">0</div><div class="l">Active now</div></div>
          <div class="stat-box"><div class="n" id="statTotal">""" + str(sum(group_counts.values())) + """</div><div class="l">Total vehicles</div></div>
        </div>
      </div>
      <div class="panel">
        <h3>Vehicle speeds</h3>
        <div id="speedList"></div>
      </div>
      <div class="panel">
        <h3>Legend</h3>
"""
    for g, color in GROUP_COLORS.items():
        if g == "other":
            continue
        html += (f'        <div class="legend-row"><span class="legend-dot" '
                 f'style="background:{color}"></span>{GROUP_LABELS[g]} '
                 f'({group_counts.get(g, 0)})</div>\n')
    html += f"""      </div>
    </div>
  </div>
  <div id="controls">
    <button id="playBtn">Play</button>
    <button class="secondary" id="resetBtn">Reset</button>
    <input type="range" id="slider" min="0" max="{len(frames) - 1}" value="0" />
    <span id="timeLabel">t = 0s</span>
  </div>
</div>
<script>
var frames = {json.dumps(frames)};
var groupColors = {json.dumps(GROUP_COLORS)};

var svgNS = "http://www.w3.org/2000/svg";
var vehLayer = document.getElementById("vehicles");
var shapes = {{}};  // id -> <circle>

function speedColor(kmh) {{
    if (kmh > 60) return "#4caf50";
    if (kmh > 20) return "#f2a900";
    return "#e6392b";
}}

function showFrame(idx) {{
    var frame = frames[idx];
    var seen = {{}};
    var speedListHtml = "";
    frame.vehicles.slice().sort(function(a, b) {{ return a.speed - b.speed; }}).forEach(function(v) {{
        seen[v.id] = true;
        if (!shapes[v.id]) {{
            var c = document.createElementNS(svgNS, "circle");
            c.setAttribute("r", "5");
            c.setAttribute("stroke", "#0f1620");
            c.setAttribute("stroke-width", "1");
            vehLayer.appendChild(c);
            shapes[v.id] = c;
        }}
        var c = shapes[v.id];
        c.setAttribute("cx", v.x);
        c.setAttribute("cy", v.y);
        c.setAttribute("fill", groupColors[v.group] || "#7a7a7a");
        c.style.display = "";

        var pct = Math.min(100, (v.speed / 120) * 100);
        speedListHtml += '<div class="speed-row">' +
            '<span class="dot" style="background:' + (groupColors[v.group] || "#7a7a7a") + '"></span>' +
            '<span class="id">' + v.id + '</span>' +
            '<span class="bar-bg"><span class="bar" style="width:' + pct + '%;background:' + speedColor(v.speed) + '"></span></span>' +
            '<span class="kmh">' + v.speed + '</span>' +
        '</div>';
    }});
    Object.keys(shapes).forEach(function(id) {{
        if (!seen[id]) shapes[id].style.display = "none";
    }});
    document.getElementById("speedList").innerHTML = speedListHtml || '<div style="color:#8fa3b8">No vehicles active</div>';
    document.getElementById("statActive").textContent = frame.vehicles.length;
    document.getElementById("clock").textContent = "T = " + frame.time + "s";
    document.getElementById("timeLabel").textContent = "t = " + frame.time + "s";
    document.getElementById("slider").value = idx;
}}

var currentIdx = 0, playing = false, playTimer = null;

function step() {{
    currentIdx = (currentIdx + 1) % frames.length;
    showFrame(currentIdx);
}}

document.getElementById("slider").addEventListener("input", function(e) {{
    currentIdx = parseInt(e.target.value, 10);
    showFrame(currentIdx);
}});

document.getElementById("playBtn").addEventListener("click", function() {{
    playing = !playing;
    this.textContent = playing ? "Pause" : "Play";
    if (playing) {{ playTimer = setInterval(step, 200); }}
    else {{ clearInterval(playTimer); }}
}});

document.getElementById("resetBtn").addEventListener("click", function() {{
    playing = false;
    clearInterval(playTimer);
    document.getElementById("playBtn").textContent = "Play";
    currentIdx = 0;
    showFrame(0);
}});

showFrame(0);
</script>
</body>
</html>
"""
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved: {OUT_HTML} (open directly in any browser, fully offline)")


if __name__ == "__main__":
    main()
