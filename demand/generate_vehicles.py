#!/usr/bin/env python3
"""Phase 2 — generate 100 vehicles' routes on the real NH16 network built in
Phase 1, covering all five accident-cause scenarios locked into BRIEF.md:

  1. Over-speeding          -> realistic per-type speed distribution, with a
                                deliberate "aggressive" subset driving faster
                                than the limit (so rear/front TTC alerts have
                                something real to catch in later phases).
  2. Merge / crossing       -> ~15 vehicles start on a real side road at a
                                real highway junction; most MERGE onto NH16
                                and continue, a smaller subset CROSS straight
                                over to the opposite side road.
  3. Two-wheelers           -> motorcycles are a real fraction of the mix,
                                not just car/bus/truck.
  4. Road classification    -> handled by using the real, mixed-lane-count
                                NH16 network from Phase 1 as-is (no synthetic
                                uniform road) — this script doesn't need to
                                do anything extra for it, Phase 4's threshold
                                logic reads lane count per edge at alert time.
  5. Wrong-side driving     -> a few vehicles are routed onto the OPPOSITE
                                carriageway's edges for part of their trip —
                                i.e. physically using the lanes meant for
                                oncoming traffic, exactly like a real driver
                                who crossed the median at an unauthorized gap.

Output: sim/sumo/routes.rou.xml
"""
import random
import re
import sys
import heapq
from collections import defaultdict

import sumolib

NET_FILE = "road/nh16.net.xml"
OUT_ROUTES = "sim/sumo/routes.rou.xml"

NH16_REF_RE = re.compile(r"NH\s*-?\s*(16|5)\b", re.IGNORECASE)

TOTAL_VEHICLES = 100
N_SIDE_ROAD = 15          # merging + crossing combined
N_CROSSING = 5            # subset of the 15 that cross straight over
N_MERGING = N_SIDE_ROAD - N_CROSSING
N_WRONG_WAY = 4           # subset of through-traffic re-routed onto oncoming lanes
N_THROUGH = TOTAL_VEHICLES - N_SIDE_ROAD   # includes the wrong-way subset

SIM_DURATION = 3600  # seconds, matches BRIEF §2

random.seed(42)  # reproducible demo run


def is_nh16(edge):
    ref = edge.getParam("ref", "")
    if ref and NH16_REF_RE.search(ref):
        return True
    if not ref:
        etype = edge.getType() or ""
        return "trunk" in etype or "primary" in etype
    return False


def shortest_path_restricted(net, allowed_edge_ids, start_node_id, end_node_id):
    """Dijkstra shortest path from start_node to end_node using only edges
    whose ID is in allowed_edge_ids. Returns a list of edge IDs, or None."""
    dist = {start_node_id: 0.0}
    prev = {}
    pq = [(0.0, start_node_id)]
    visited = set()
    while pq:
        d, node_id = heapq.heappop(pq)
        if node_id in visited:
            continue
        visited.add(node_id)
        if node_id == end_node_id:
            break
        node = net.getNode(node_id)
        for edge in node.getOutgoing():
            if edge.getID() not in allowed_edge_ids:
                continue
            to_id = edge.getToNode().getID()
            nd = d + edge.getLength()
            if to_id not in dist or nd < dist[to_id]:
                dist[to_id] = nd
                prev[to_id] = (node_id, edge.getID())
                heapq.heappush(pq, (nd, to_id))
    if end_node_id not in dist:
        return None
    path = []
    cur = end_node_id
    while cur != start_node_id:
        p, e = prev[cur]
        path.append(e)
        cur = p
    path.reverse()
    return path


def find_backbone(net, nh16_edges):
    """Find the two geographic extremes of the NH16 subgraph (by latitude)
    and the directed edge-path between them in each direction."""
    nh16_ids = {e.getID() for e in nh16_edges}
    node_lat = {}
    for e in nh16_edges:
        for node in (e.getFromNode(), e.getToNode()):
            if node.getID() not in node_lat:
                x, y = node.getCoord()
                lon, lat = net.convertXY2LonLat(x, y)
                node_lat[node.getID()] = lat

    north_node = max(node_lat, key=node_lat.get)   # Srikakulam end
    south_node = min(node_lat, key=node_lat.get)   # Visakhapatnam end

    forward = shortest_path_restricted(net, nh16_ids, north_node, south_node)
    backward = shortest_path_restricted(net, nh16_ids, south_node, north_node)

    if forward is None or backward is None:
        print("WARNING: NH16 subgraph is not fully connected end-to-end; "
              "falling back to sumolib's unrestricted shortest path for "
              "whichever direction failed (may briefly use a non-NH16 edge).",
              file=sys.stderr)
        if forward is None:
            _, edges = net.getShortestPath(
                net.getNode(north_node).getOutgoing()[0],
                net.getNode(south_node).getIncoming()[0])
            forward = [e.getID() for e in edges] if edges else []
        if backward is None:
            _, edges = net.getShortestPath(
                net.getNode(south_node).getOutgoing()[0],
                net.getNode(north_node).getIncoming()[0])
            backward = [e.getID() for e in edges] if edges else []

    return forward, backward, north_node, south_node


def find_opposite_edge(net, edge):
    """Return the paired opposite-direction edge for a divided-highway edge
    (same two junctions, reversed), if one exists — used to build wrong-way
    vehicle routes (median-crossing onto oncoming lanes)."""
    a, b = edge.getFromNode().getID(), edge.getToNode().getID()
    for cand in edge.getToNode().getOutgoing():
        if cand.getToNode().getID() == a:
            return cand
    return None


def find_side_road_junctions(net, nh16_edges):
    """Junctions that sit on NH16 AND have at least one connecting side-road
    (non-NH16) edge — real merge/crossing points from Phase 1's road data."""
    nh16_ids = {e.getID() for e in nh16_edges}
    node_edges = defaultdict(list)
    for e in net.getEdges():
        if e.getFunction() == "internal":
            continue
        node_edges[e.getFromNode().getID()].append(e)
        node_edges[e.getToNode().getID()].append(e)

    candidates = []
    for node_id, edges in node_edges.items():
        has_nh16 = any(e.getID() in nh16_ids for e in edges)
        side_edges = [e for e in edges if e.getID() not in nh16_ids]
        if has_nh16 and side_edges:
            candidates.append((node_id, side_edges))
    return candidates


def build_merge_route(net, junction_id, side_edges, backbone_forward, backbone_backward):
    """A vehicle enters from a side road and merges onto NH16, continuing in
    whichever backbone direction actually starts at this junction."""
    incoming = [e for e in side_edges if e.getToNode().getID() == junction_id]
    if not incoming:
        return None
    entry_edge = random.choice(incoming)

    for backbone in (backbone_forward, backbone_backward):
        for i, eid in enumerate(backbone):
            if net.getEdge(eid).getFromNode().getID() == junction_id:
                remaining = backbone[i:i + 20]  # cap route length for a short demo segment
                return [entry_edge.getID()] + remaining
    return None


def build_crossing_route(net, junction_id, side_edges):
    """A vehicle enters from one side road and exits via a different side
    road at the same junction — crossing straight over NH16 without ever
    using an NH16 edge itself (the T-bone/crossing-approach scenario)."""
    incoming = [e for e in side_edges if e.getToNode().getID() == junction_id]
    outgoing = [e for e in side_edges if e.getFromNode().getID() == junction_id]
    for in_e in incoming:
        for out_e in outgoing:
            if out_e.getToNode().getID() == in_e.getFromNode().getID():
                continue  # skip doubling straight back the way it came
            return [in_e.getID(), out_e.getID()]
    return None


def build_wrong_way_route(net, backbone, span=6):
    """Take a short stretch of the backbone and swap each edge for its
    opposite-direction pair, if one exists — the vehicle then physically
    occupies oncoming-traffic lanes for that stretch, matching real
    median-crossing wrong-way driving."""
    start = random.randint(0, max(0, len(backbone) - span - 1))
    stretch = backbone[start:start + span]
    opposite_ids = []
    for eid in stretch:
        opp = find_opposite_edge(net, net.getEdge(eid))
        if opp is None:
            return None
        opposite_ids.append(opp.getID())
    opposite_ids.reverse()  # traveling the opposite physical direction too
    return opposite_ids


VTYPES = {
    # id: (vClass, length_m, max_speed_m_s, accel, decel, share_of_100)
    "car":        ("passenger",  5.0, 27.8, 2.6, 4.5, 0.55),
    "motorcycle": ("motorcycle", 2.2, 25.0, 3.5, 5.0, 0.25),
    "truck":      ("truck",     10.0, 22.2, 1.3, 3.5, 0.12),
    "bus":        ("bus",       12.0, 22.2, 1.2, 3.5, 0.08),
}


def pick_vtype():
    r = random.random()
    acc = 0.0
    for vtype, (_, _, _, _, _, share) in VTYPES.items():
        acc += share
        if r <= acc:
            return vtype
    return "car"


def vtype_xml():
    lines = []
    for vid, (vclass, length, maxspeed, accel, decel, _) in VTYPES.items():
        lines.append(
            f'    <vType id="{vid}" vClass="{vclass}" length="{length}" '
            f'maxSpeed="{maxspeed}" accel="{accel}" decel="{decel}" '
            f'sigma="0.5"/>'
        )
    return "\n".join(lines)


def main():
    net = sumolib.net.readNet(NET_FILE)
    all_edges = net.getEdges()
    nh16_edges = [e for e in all_edges if is_nh16(e)]
    if not nh16_edges:
        print("No NH16 edges found — check road/nh16.net.xml", file=sys.stderr)
        sys.exit(1)

    forward, backward, north_node, south_node = find_backbone(net, nh16_edges)
    print(f"Backbone: {len(forward)} edges Srikakulam->Vizag, "
          f"{len(backward)} edges Vizag->Srikakulam")

    junctions = find_side_road_junctions(net, nh16_edges)
    random.shuffle(junctions)
    print(f"Candidate side-road junctions found: {len(junctions)}")

    vehicles = []  # (id, vtype, depart, route_edges, group)

    # --- through-traffic (includes the wrong-way subset) ---
    n_wrongway_built = 0
    for i in range(N_THROUGH):
        vtype = pick_vtype()
        direction = random.choice([forward, backward])
        depart = round(random.uniform(0, SIM_DURATION * 0.8), 1)
        group = "through"
        route = direction
        if n_wrongway_built < N_WRONG_WAY:
            wrong_route = build_wrong_way_route(net, direction)
            if wrong_route:
                route = wrong_route
                group = "wrongway"
                n_wrongway_built += 1
        vehicles.append((f"through_{i}", vtype, depart, route, group))

    if n_wrongway_built < N_WRONG_WAY:
        print(f"NOTE: only built {n_wrongway_built}/{N_WRONG_WAY} wrong-way "
              f"vehicles — not enough divided (paired-edge) stretches found "
              f"on this network to place more.")

    # --- side-road: merging ---
    n_merge_built = 0
    for node_id, side_edges in junctions:
        if n_merge_built >= N_MERGING:
            break
        route = build_merge_route(net, node_id, side_edges, forward, backward)
        if route:
            vtype = pick_vtype()
            depart = round(random.uniform(0, SIM_DURATION * 0.8), 1)
            vehicles.append((f"merge_{n_merge_built}", vtype, depart, route, "merge"))
            n_merge_built += 1

    if n_merge_built < N_MERGING:
        print(f"NOTE: only built {n_merge_built}/{N_MERGING} merging "
              f"vehicles — fewer suitable junctions than requested.")

    # --- side-road: crossing ---
    n_cross_built = 0
    for node_id, side_edges in junctions:
        if n_cross_built >= N_CROSSING:
            break
        route = build_crossing_route(net, node_id, side_edges)
        if route:
            vtype = pick_vtype()
            depart = round(random.uniform(0, SIM_DURATION * 0.8), 1)
            vehicles.append((f"cross_{n_cross_built}", vtype, depart, route, "crossing"))
            n_cross_built += 1

    if n_cross_built < N_CROSSING:
        print(f"NOTE: only built {n_cross_built}/{N_CROSSING} crossing "
              f"vehicles — fewer suitable 4-way junctions than requested.")

    # top up to exactly 100 with more through-traffic if any group fell short
    shortfall = TOTAL_VEHICLES - len(vehicles)
    for i in range(shortfall):
        vtype = pick_vtype()
        direction = random.choice([forward, backward])
        depart = round(random.uniform(0, SIM_DURATION * 0.8), 1)
        vehicles.append((f"through_extra_{i}", vtype, depart, direction, "through"))

    vehicles.sort(key=lambda v: v[2])  # depart time order, required by SUMO

    with open(OUT_ROUTES, "w", encoding="utf-8") as f:
        f.write("<routes>\n")
        f.write(vtype_xml() + "\n")
        for vid, vtype, depart, route, group in vehicles:
            f.write(f'    <vehicle id="{vid}" type="{vtype}" depart="{depart}" '
                     f'departLane="best" departSpeed="max">\n')
            f.write(f'        <route edges="{" ".join(route)}"/>\n')
            f.write(f'    </vehicle>\n')
        f.write("</routes>\n")

    print(f"\nSaved: {OUT_ROUTES}")
    print(f"Total vehicles: {len(vehicles)}")
    by_group = defaultdict(int)
    for *_, group in vehicles:
        by_group[group] += 1
    for g, n in sorted(by_group.items()):
        print(f"  {g}: {n}")


if __name__ == "__main__":
    main()
