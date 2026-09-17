#!/usr/bin/env python3
"""Phase 2 output: summarize the generated vehicle population — a printed
table (type, group, depart time, direction/junction, reference speed) and a
histogram of the speed/type distribution, so the 100-vehicle population can
be sanity-checked before running any simulation."""
import xml.etree.ElementTree as ET
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROUTES_FILE = "sim/sumo/routes.rou.xml"
OUT_HIST = "demand/vehicle_distribution.png"


def group_from_id(vid):
    if vid.startswith("through_"):
        return "through"
    if vid.startswith("merge_"):
        return "merge"
    if vid.startswith("cross_"):
        return "crossing"
    if vid.startswith("wrongway_"):
        return "wrongway"
    return "other"


def main():
    tree = ET.parse(ROUTES_FILE)
    root = tree.getroot()

    vtype_speed = {}
    for vtype in root.findall("vType"):
        vtype_speed[vtype.get("id")] = float(vtype.get("maxSpeed"))

    vehicles = []
    for veh in root.findall("vehicle"):
        vid = veh.get("id")
        vtype = veh.get("type")
        depart = float(veh.get("depart"))
        route = veh.find("route")
        edges = route.get("edges").split()
        group = group_from_id(vid)
        # "wrongway" vehicles are through-traffic re-routed, so check that
        # case separately since generate_vehicles.py doesn't rename the id
        vehicles.append({
            "id": vid, "type": vtype, "depart": depart,
            "first_edge": edges[0], "last_edge": edges[-1],
            "n_edges": len(edges), "group": group,
            "ref_speed": vtype_speed.get(vtype, 0.0),
        })

    print(f"Total vehicles: {len(vehicles)}\n")

    print(f"{'ID':<16} {'Type':<11} {'Group':<9} {'Depart(s)':<10} "
          f"{'First edge':<14} {'Last edge':<14} {'RefSpeed(m/s)'}")
    for v in vehicles[:20]:
        print(f"{v['id']:<16} {v['type']:<11} {v['group']:<9} "
              f"{v['depart']:<10} {v['first_edge']:<14} {v['last_edge']:<14} "
              f"{v['ref_speed']}")
    if len(vehicles) > 20:
        print(f"... ({len(vehicles) - 20} more, truncated for readability)")

    print("\n--- Group counts ---")
    for g, n in sorted(Counter(v["group"] for v in vehicles).items()):
        print(f"  {g}: {n}")

    print("\n--- Vehicle-type counts ---")
    for t, n in sorted(Counter(v["type"] for v in vehicles).items()):
        print(f"  {t}: {n}")

    # Histogram: speed distribution split by type
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    types = sorted(vtype_speed.keys())
    type_counts = Counter(v["type"] for v in vehicles)
    axes[0].bar(types, [type_counts.get(t, 0) for t in types],
                color=["#3f7cb0", "#e6392b", "#4caf50", "#f2a900"])
    axes[0].set_title("Vehicle type distribution")
    axes[0].set_ylabel("Count")

    speeds = [v["ref_speed"] for v in vehicles]
    axes[1].hist(speeds, bins=8, color="#3f7cb0", edgecolor="white")
    axes[1].set_title("Reference (max) speed distribution")
    axes[1].set_xlabel("Speed (m/s)")
    axes[1].set_ylabel("Count")

    fig.tight_layout()
    fig.savefig(OUT_HIST, dpi=150)
    print(f"\nSaved: {OUT_HIST}")


if __name__ == "__main__":
    main()
