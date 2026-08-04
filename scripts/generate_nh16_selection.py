#!/usr/bin/env python3
"""Phase 1 output: write a SUMO/netedit selection file listing exactly the
NH16 highway edges (same ref-matching logic as generate_network_html.py), so
they can be selected and given a custom highlight color inside netedit or
sumo-gui — matching the red/gray distinction in nh16_map.html exactly.

Usage inside netedit/sumo-gui: Edit -> Selection -> Load, pick
road/nh16_selection.txt, then apply a color to the current selection.
"""
import re
import sys

import sumolib

NET_FILE = "road/nh16.net.xml"
OUT_SELECTION = "road/nh16_selection.txt"

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
    edges = net.getEdges()
    if not edges:
        print("No edges found in the network.", file=sys.stderr)
        sys.exit(1)

    nh16_ids = [e.getID() for e in edges if is_nh16(e)]

    with open(OUT_SELECTION, "w", encoding="utf-8") as f:
        for eid in nh16_ids:
            f.write(f"edge:{eid}\n")

    print(f"NH16 edges selected: {len(nh16_ids)} / {len(edges)} total")
    print(f"Saved: {OUT_SELECTION}")
    print("In netedit/sumo-gui: Edit -> Selection -> Load, choose this file,")
    print("then use the selection color tool to highlight it.")


if __name__ == "__main__":
    main()
