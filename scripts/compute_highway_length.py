#!/usr/bin/env python3
"""Prints the total length of the NH16 highway edges in our built network
(the same is_nh16 logic used by the map/selection scripts), plus the
straight-line distance between the two endpoints for comparison."""
import re

import sumolib

NET_FILE = "road/nh16.net.xml"
NH16_REF_RE = re.compile(r"NH\s*-?\s*(16|5)\b", re.IGNORECASE)


def is_nh16(edge):
    ref = edge.getParam("ref", "")
    if ref and NH16_REF_RE.search(ref):
        return True
    if not ref:
        etype = edge.getType() or ""
        return "trunk" in etype or "primary" in etype
    return False


def main():
    net = sumolib.net.readNet(NET_FILE)
    edges = [e for e in net.getEdges() if is_nh16(e)]

    total_m = sum(e.getLength() for e in edges)
    print(f"NH16 edges: {len(edges)}")
    print(f"Total highway edge length (sum of all edges, both directions "
          f"counted separately): {total_m/1000:.1f} km")

    # Rough one-direction estimate: divided highways store each direction as
    # a separate edge, so the point-to-point distance is roughly half this
    # if the road is fully divided along its length.
    print(f"Approx one-direction distance (total / 2): {total_m/2000:.1f} km")


if __name__ == "__main__":
    main()
