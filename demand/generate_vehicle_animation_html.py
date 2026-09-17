#!/usr/bin/env python3
"""Phase 2 output: a presentation-style animated dashboard covering the
FULL NH16 corridor at a fixed, readable scale — the canvas is wide (scrolls
left/right, not squeezed to fit one screen), so vehicles are always a clear,
comfortably-sized dot with no zooming needed.

Side roads at merge/crossing junctions are drawn as real, visible stub
branches (not just a marker dot) — a merging vehicle visibly travels down
its stub before joining the highway; a crossing vehicle visibly travels
straight through, from one side of the highway to the other.

No external map tiles/CDN dependency — inline SVG only, fully offline.

Requires:
- road/nh16.net.xml       (Phase 1)
- sim/sumo/routes.rou.xml (Phase 2, generate_vehicles.py)
- output/phase2_fcd.xml   (Phase 2, scripts/run_phase2_preview.sh,
                            --fcd-output.geo true, default lane/pos fields)
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

# Canvas is sized to the REAL route length at a fixed scale, not squeezed to
# fit the viewport — the container scrolls instead.
PIXELS_PER_KM = 70
MARGIN_X = 100
SVG_H = 560
ROAD_Y = 280
BEND_SCALE = 2200      # exaggerates real lateral highway bends for visibility
STUB_LEN = 90           # fixed pixel length of a schematic side-road stub


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


def build_projector(net, nh16_edges, svg_w):
    """Projects real (lat, lon) onto the wide schematic canvas: x follows
    position along the Srikakulam->Vizag axis (scaled to the fixed
    pixels-per-km canvas width), y follows perpendicular deviation from that
    straight line (exaggerated) so real highway bends still show."""
    pts = []
    for e in nh16_edges:
        for x, y in e.getShape():
            lon, lat = net.convertXY2LonLat(x, y)
            pts.append((lat, lon))

    north = max(pts, key=lambda p: p[0])
    south = min(pts, key=lambda p: p[0])
    dx, dy = south[1] - north[1], south[0] - north[0]
    length2 = dx * dx + dy * dy
    total_km = haversine_km(north[0], north[1], south[0], south[1])

    def project(lat, lon):
        vx, vy = lon - north[1], lat - north[0]
        t = (vx * dx + vy * dy) / length2
        t = max(0.0, min(1.0, t))
        cross = vx * dy - vy * dx
        perp = cross / math.sqrt(length2)
        px = MARGIN_X + t * (svg_w - 2 * MARGIN_X)
        py = ROAD_Y + perp * BEND_SCALE
        return px, py, t

    return project, total_km


def main():
    net = sumolib.net.readNet(NET_FILE)
    nh16_edges = [e for e in net.getEdges() if is_nh16(e)]
    nh16_ids = {e.getID() for e in nh16_edges}
    if not nh16_edges:
        raise SystemExit("No NH16 edges found — check road/nh16.net.xml")

    # first pass just to get total_km, so we can size the canvas
    _tmp_project, total_km = build_projector(net, nh16_edges, svg_w=2000)
    svg_w = max(2400, int(total_km * PIXELS_PER_KM) + 2 * MARGIN_X)
    project, total_km = build_projector(net, nh16_edges, svg_w=svg_w)
    print(f"Route length: ~{total_km:.1f} km -> canvas width {svg_w}px")

    # --- static highway path ---
    road_points = []
    for e in nh16_edges:
        for x, y in e.getShape():
            lon, lat = net.convertXY2LonLat(x, y)
            px, py, t = project(lat, lon)
            road_points.append((t, px, py))
    road_points.sort(key=lambda p: p[0])
    road_d = "M " + " L ".join(f"{px:.1f},{py:.1f}" for _, px, py in road_points)

    # --- identify each merge/crossing vehicle's side-road edge(s) and build
    #     a fixed-length schematic stub for each junction actually used ---
    tree = ET.parse(ROUTES_FILE)
    root = tree.getroot()

    # junction_id -> {"group", "x", "y", "km", "stubs": {edge_id: (outer_xy, inner_xy, length)}}
    junctions = {}
    alternate = 0
    for veh in root.findall("vehicle"):
        vid = veh.get("id")
        group = group_from_id(vid)
        if group not in ("merge", "crossing"):
            continue
        edges = veh.find("route").get("edges").split()
        side_edges = [eid for eid in edges if eid not in nh16_ids]
        if not side_edges:
            continue
        # the junction is the node shared between the side road and the highway
        junction_node = None
        for eid in side_edges:
            e = net.getEdge(eid)
            for node in (e.getFromNode(), e.getToNode()):
                node_edges = list(node.getIncoming()) + list(node.getOutgoing())
                if any(ne.getID() in nh16_ids for ne in node_edges):
                    junction_node = node
                    break
            if junction_node:
                break
        if junction_node is None:
            continue

        jid = junction_node.getID()
        jx, jy = net.convertXY2LonLat(*junction_node.getCoord())
        jpx, jpy, jt = project(jy, jx)

        if jid not in junctions:
            side = -1 if alternate % 2 == 0 else 1   # alternate stub direction, above/below
            alternate += 1
            junctions[jid] = {
                "group": group, "x": jpx, "y": jpy,
                "km": round(jt * total_km, 1), "side": side, "stubs": {},
            }

        j = junctions[jid]
        for eid in side_edges:
            e = net.getEdge(eid)
            length = e.getLength()
            if e.getToNode().getID() == jid:      # incoming: outer -> junction
                outer = (jpx - STUB_LEN * 0.7, jpy + j["side"] * STUB_LEN)
                j["stubs"][eid] = {"a": outer, "b": (jpx, jpy), "len": length}
            else:                                  # outgoing: junction -> outer
                outer = (jpx + STUB_LEN * 0.7, jpy + j["side"] * STUB_LEN)
                j["stubs"][eid] = {"a": (jpx, jpy), "b": outer, "len": length}

    print(f"Junction markers: {len(junctions)}")
    stub_edge_lookup = {}  # edge_id -> (junction_id, a_xy, b_xy, length)
    for jid, j in junctions.items():
        for eid, s in j["stubs"].items():
            stub_edge_lookup[eid] = (jid, s["a"], s["b"], s["len"])

    # --- FCD frames: main-road vehicles use the real projector; vehicles on
    #     a stub edge are interpolated along that stub instead ---
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
            vid = v.get("id")
            lane = v.get("lane", "")
            edge_id = lane.rsplit("_", 1)[0] if lane else ""
            speed_kmh = round(float(v.get("speed")) * 3.6, 1)

            if edge_id in stub_edge_lookup:
                _jid, a, b, length = stub_edge_lookup[edge_id]
                pos = float(v.get("pos", 0.0))
                f = max(0.0, min(1.0, pos / length)) if length > 0 else 0.0
                px = a[0] + f * (b[0] - a[0])
                py = a[1] + f * (b[1] - a[1])
            else:
                lon, lat = float(v.get("x")), float(v.get("y"))
                px, py, _ = project(lat, lon)

            vehicles.append({
                "id": vid, "type": v.get("type"), "group": group_from_id(vid),
                "x": px, "y": py, "speed": speed_kmh,
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

    # --- stub SVG paths (drawn once, static, behind the vehicles) ---
    stub_svg = ""
    for jid, j in junctions.items():
        color = GROUP_COLORS[j["group"]]
        for eid, s in j["stubs"].items():
            mx = (s["a"][0] + s["b"][0]) / 2
            my = (s["a"][1] + s["b"][1]) / 2
            stub_svg += (f'<line x1="{s["a"][0]:.1f}" y1="{s["a"][1]:.1f}" '
                         f'x2="{s["b"][0]:.1f}" y2="{s["b"][1]:.1f}" '
                         f'stroke="{color}" stroke-width="6" stroke-linecap="round" '
                         f'opacity="0.6"/>\n'
                         f'<circle cx="{s["a"][0]:.1f}" cy="{s["a"][1]:.1f}" r="3" '
                         f'fill="{color}"/>\n'
                         f'<text class="stub-label" x="{mx:.1f}" y="{my:.1f}" '
                         f'transform="rotate({-25 if j["side"] < 0 else 25} {mx:.1f} {my:.1f})">'
                         f'SIDE ROAD</text>\n')
        stub_svg += (f'<rect x="{j["x"]-5}" y="{j["y"]-5}" width="10" height="10" '
                     f'fill="{color}" stroke="#0f1620" stroke-width="1.5"/>\n'
                     f'<text class="junction-label" x="{j["x"]+9}" '
                     f'y="{j["y"] + (22 if j["side"] > 0 else -14)}">'
                     f'&#9670; JUNCTION ~{j["km"]}km &middot; {GROUP_LABELS[j["group"]]}</text>\n')

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
    display: flex; align-items: center; justify-content: space-between; flex-shrink: 0;
  }}
  #header h1 {{ font-size: 17px; margin: 0; }}
  #header .sub {{ font-size: 12px; color: #8fa3b8; margin-top: 2px; }}
  #clock {{ font-size: 22px; color: #4fc3f7; font-variant-numeric: tabular-nums; }}
  #body {{ flex: 1; display: flex; overflow: hidden; }}
  #canvasWrap {{
    flex: 1; overflow: auto; position: relative; background: #0f1620;
  }}
  #canvasWrap svg {{ display: block; }}
  .junction-label {{ fill: #c7d3de; font-size: 12px; font-weight: 500; }}
  .stub-label {{ fill: #c7d3de; font-size: 10px; font-style: italic; letter-spacing: 0.04em; }}
  .end-label {{ fill: #8fa3b8; font-size: 14px; font-weight: 600; }}
  #sidebar {{
    width: 270px; background: #131c28; border-left: 1px solid #22303f;
    padding: 14px; overflow-y: auto; font-size: 13px; flex-shrink: 0;
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
  .legend-line {{ width: 16px; height: 3px; }}
  #hint {{ font-size: 11px; color: #6b7f92; margin-top: 4px; }}
  .cause-row {{
    background: #1a2531; border-radius: 6px; padding: 8px 10px; margin-bottom: 8px;
  }}
  .cause-row .name {{ font-size: 12px; font-weight: 600; margin-bottom: 2px; }}
  .cause-row .desc {{ font-size: 10.5px; color: #8fa3b8; margin-bottom: 6px; }}
  .locate-btn {{
    cursor: pointer; font-size: 11px; padding: 4px 10px; border-radius: 4px;
    border: 1px solid #3f7cb0; background: transparent; color: #6fb3e0; margin-right: 6px;
  }}
  .locate-btn:hover {{ background: #3f7cb0; color: white; }}
  #controls {{
    height: 60px; background: #131c28; border-top: 1px solid #22303f;
    display: flex; align-items: center; gap: 14px; padding: 0 20px; flex-shrink: 0;
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
      <div class="sub">{sum(group_counts.values())} vehicles &middot; pure V2V (no RSU) &middot; 802.11p OCB mode &middot; ~{total_km:.0f} km corridor &mdash; scroll the map left/right to see the full route</div>
    </div>
    <div id="clock">T = 0s</div>
  </div>
  <div id="body">
    <div id="canvasWrap">
      <svg width="{svg_w}" height="{SVG_H}" viewBox="0 0 {svg_w} {SVG_H}">
        <path d="{road_d}" stroke="#3a4a5c" stroke-width="14" fill="none" stroke-linecap="round"/>
        <path d="{road_d}" stroke="#c9a227" stroke-width="2" stroke-dasharray="12 12" fill="none" opacity="0.6"/>
        {stub_svg}
        <text class="end-label" x="{MARGIN_X}" y="{SVG_H - 20}">&#9664; Srikakulam</text>
        <text class="end-label" x="{svg_w - MARGIN_X}" y="{SVG_H - 20}" text-anchor="end">Visakhapatnam &#9654;</text>
        <g id="vehicles"></g>
      </svg>
    </div>
    <div id="sidebar">
      <div class="panel">
        <h3>5 accident causes &mdash; jump to a live example</h3>
        <div class="cause-row">
          <div class="name">1. Over-speeding</div>
          <div class="desc">Rear/front TTC checks target this (logic added in Phase 4). Jumps to whichever vehicle is fastest right now.</div>
          <button class="locate-btn" onclick="locateFastest()">Locate fastest vehicle</button>
        </div>
        <div class="cause-row">
          <div class="name">2. Intersection / merging traffic</div>
          <div class="desc">10 merging + 5 crossing vehicles, real NH16 junctions.</div>
          <button class="locate-btn" onclick="locateGroup('merge')">Locate merge</button>
          <button class="locate-btn" onclick="locateGroup('crossing')">Locate crossing</button>
        </div>
        <div class="cause-row">
          <div class="name">3. Two-wheelers</div>
          <div class="desc">23 motorcycles in the fleet, most at-risk vehicle type per the accident analysis.</div>
          <button class="locate-btn" onclick="locateType('motorcycle')">Locate a motorcycle</button>
        </div>
        <div class="cause-row">
          <div class="name">4. Road classification</div>
          <div class="desc">Not a vehicle &mdash; reflected in the real NH16 network itself (Phase 1), which has genuine mixed lane counts along its length. Phase 4's alert thresholds will vary by this.</div>
        </div>
        <div class="cause-row">
          <div class="name">5. Wrong-side driving</div>
          <div class="desc">4 vehicles routed onto the oncoming carriageway &mdash; the #1 real cause of fatalities on this highway.</div>
          <button class="locate-btn" onclick="locateGroup('wrongway')">Locate wrong-way</button>
        </div>
      </div>
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
    html += """        <div class="legend-row"><span class="legend-line" style="background:#8fa3b8;opacity:0.55"></span>Side-road stub</div>
        <div id="hint">Vehicles on a stub are traveling the side road, before joining or crossing the highway.</div>
      </div>
    </div>
  </div>
  <div id="controls">
    <button id="playBtn">Play</button>
    <button class="secondary" id="resetBtn">Reset</button>
    <input type="range" id="slider" min="0" max=\"""" + str(len(frames) - 1) + """\" value="0" />
    <span id="timeLabel">t = 0s</span>
  </div>
</div>
<script>
var frames = """ + json.dumps(frames) + """;
var groupColors = """ + json.dumps(GROUP_COLORS) + """;

var svgNS = "http://www.w3.org/2000/svg";
var vehLayer = document.getElementById("vehicles");
var shapes = {};

function speedColor(kmh) {
    if (kmh > 60) return "#4caf50";
    if (kmh > 20) return "#f2a900";
    return "#e6392b";
}

function showFrame(idx) {
    var frame = frames[idx];
    var seen = {};
    var speedListHtml = "";
    frame.vehicles.slice().sort(function(a, b) { return a.speed - b.speed; }).forEach(function(v) {
        seen[v.id] = true;
        if (!shapes[v.id]) {
            var c = document.createElementNS(svgNS, "circle");
            c.setAttribute("r", "7");
            c.setAttribute("stroke", "#0f1620");
            c.setAttribute("stroke-width", "1.5");
            vehLayer.appendChild(c);
            shapes[v.id] = c;
        }
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
    });
    Object.keys(shapes).forEach(function(id) {
        if (!seen[id]) shapes[id].style.display = "none";
    });
    document.getElementById("speedList").innerHTML = speedListHtml || '<div style="color:#8fa3b8">No vehicles active</div>';
    document.getElementById("statActive").textContent = frame.vehicles.length;
    document.getElementById("clock").textContent = "T = " + frame.time + "s";
    document.getElementById("timeLabel").textContent = "t = " + frame.time + "s";
    document.getElementById("slider").value = idx;
}

// --- "jump to a live example" locators for the 5 accident causes ---
var highlightRing = document.createElementNS(svgNS, "circle");
highlightRing.setAttribute("r", "16");
highlightRing.setAttribute("fill", "none");
highlightRing.setAttribute("stroke", "#ffffff");
highlightRing.setAttribute("stroke-width", "3");
highlightRing.style.display = "none";
vehLayer.parentNode.appendChild(highlightRing);

function scrollToXY(x) {
    var wrap = document.getElementById("canvasWrap");
    wrap.scrollTo({ left: Math.max(0, x - wrap.clientWidth / 2), behavior: "smooth" });
}

function flashAt(x, y) {
    highlightRing.setAttribute("cx", x);
    highlightRing.setAttribute("cy", y);
    highlightRing.style.display = "";
    highlightRing.style.opacity = "1";
    setTimeout(function() {
        highlightRing.style.transition = "opacity 1s";
        highlightRing.style.opacity = "0";
    }, 1800);
}

function jumpToVehicle(frameIdx, v) {
    currentIdx = frameIdx;
    showFrame(frameIdx);
    scrollToXY(v.x);
    flashAt(v.x, v.y);
}

function locateGroup(group) {
    for (var i = 0; i < frames.length; i++) {
        var v = frames[i].vehicles.find(function(v) { return v.group === group; });
        if (v) { jumpToVehicle(i, v); return; }
    }
    alert("No active " + group + " vehicle found in the sampled frames — try scrubbing the time slider manually.");
}

function locateType(vtype) {
    for (var i = 0; i < frames.length; i++) {
        var v = frames[i].vehicles.find(function(v) { return v.type === vtype; });
        if (v) { jumpToVehicle(i, v); return; }
    }
    alert("No active " + vtype + " found in the sampled frames.");
}

function locateFastest() {
    var best = null, bestIdx = -1;
    for (var i = 0; i < frames.length; i++) {
        frames[i].vehicles.forEach(function(v) {
            if (!best || v.speed > best.speed) { best = v; bestIdx = i; }
        });
    }
    if (best) jumpToVehicle(bestIdx, best);
}

var currentIdx = 0, playing = false, playTimer = null;

function step() {
    currentIdx = (currentIdx + 1) % frames.length;
    showFrame(currentIdx);
}

document.getElementById("slider").addEventListener("input", function(e) {
    currentIdx = parseInt(e.target.value, 10);
    showFrame(currentIdx);
});

document.getElementById("playBtn").addEventListener("click", function() {
    playing = !playing;
    this.textContent = playing ? "Pause" : "Play";
    if (playing) { playTimer = setInterval(step, 200); }
    else { clearInterval(playTimer); }
});

document.getElementById("resetBtn").addEventListener("click", function() {
    playing = false;
    clearInterval(playTimer);
    document.getElementById("playBtn").textContent = "Play";
    currentIdx = 0;
    showFrame(0);
});

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
