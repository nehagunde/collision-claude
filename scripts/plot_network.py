#!/usr/bin/env python3
"""Phase 1 output: render the NH16 network to an image and print a lane-count
summary, so the road shape and lane counts can be sanity-checked against the
real highway without needing to open SUMO-GUI interactively."""
import sys
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sumolib

NET_FILE = "road/nh16.net.xml"
OUT_IMAGE = "road/nh16_preview.png"


def main():
    net = sumolib.net.readNet(NET_FILE)
    edges = net.getEdges()

    if not edges:
        print("No edges found in the network — check road/nh16.osm and the "
              "netconvert output for warnings.")
        sys.exit(1)

    # Color + thickness scale by lane count, so the plot reads like a real
    # road map (wider/brighter = more lanes) instead of one uniform line.
    LANE_STYLE = {
        1: dict(color="#a6c8e0", linewidth=2.0),   # single lane — thin, pale
        2: dict(color="#3f7cb0", linewidth=4.0),   # standard dual carriageway
        3: dict(color="#08306b", linewidth=6.0),   # wider junction sections
    }
    DEFAULT_STYLE = dict(color="#08306b", linewidth=7.0)

    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    lane_counts = []
    for edge in edges:
        shape = edge.getShape()
        xs = [p[0] for p in shape]
        ys = [p[1] for p in shape]
        lanes = edge.getLaneNumber()
        style = LANE_STYLE.get(lanes, DEFAULT_STYLE)
        ax.plot(xs, ys, solid_capstyle="round", zorder=2, **style)
        lane_counts.append(lanes)

    # legend, since color/thickness now carries information
    handles = [
        plt.Line2D([0], [0], **LANE_STYLE[n], solid_capstyle="round")
        for n in sorted(LANE_STYLE)
    ]
    labels = [f"{n} lane(s)" for n in sorted(LANE_STYLE)]
    ax.legend(handles, labels, loc="lower left", frameon=False, fontsize=10)

    ax.set_title("NH16 Srikakulam -> Visakhapatnam (SUMO network preview)",
                 fontsize=14, fontweight="bold")
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(OUT_IMAGE, dpi=150)
    print(f"Saved preview image: {OUT_IMAGE}")

    counts = Counter(lane_counts)
    total_edges = len(lane_counts)
    print(f"\nLane-count summary across {total_edges} edges:")
    for lanes, n in sorted(counts.items()):
        print(f"  {lanes} lane(s): {n} edges ({100 * n / total_edges:.1f}%)")


if __name__ == "__main__":
    main()
