# NH16 Srikakulam -> Visakhapatnam — corridor notes

**Endpoints:** Srikakulam (~18.29 N, 83.89 E) to Visakhapatnam (~17.69 N, 83.22 E),
~100 km along the coast, following the real NH16 alignment.

**Data source:** OpenStreetMap, pulled via the Overpass API (not the plain OSM
API, which caps out well below the area a 100 km stretch needs) —
`scripts/fetch_nh16_osm.sh`.

**Selection query:** two-stage. First, ways tagged `highway` in `{trunk,
primary, trunk_link, primary_link}` with a `ref` matching `NH.?16` or `NH.?5`
inside a bounding box covering both endpoints (the `NH.?5` pattern covers the
pre-2010 legacy ref, since not all OSM edits in the area may carry the
current NH16 number). Second, an Overpass `around` filter pulls in any
`secondary`/`tertiary` road (and their `_link` variants) within 400 m of that
alignment — real intersecting junctions along the highway, without pulling
in entire unrelated city grids far from it.

**History:** initial Phase 1 work only did the first stage, which meant the
network had no real side roads at all — corrected after the user asked
whether the road was really side-road-free. The first fix included
`residential`/`unclassified` in the `around` filter too, which pulled in
12,552 edges — mostly dense in-town residential street grids near
Srikakulam/Vizag/towns along the route, far more than needed and heavy to
render or simulate. Narrowed to just `secondary`/`tertiary` to keep genuine
junctions without the town-grid noise.

**Build:** `scripts/build_network.sh` runs `netconvert` on the raw extract to
produce `road/nh16.net.xml` (geometry cleanup, roundabout/ramp guessing,
junction joining, traffic-light guessing for the handful of signalised
junctions on this stretch).

**Verification:** `scripts/plot_network.py` renders `road/nh16_preview.png`
and prints a lane-count summary across all edges — used to sanity-check the
road shape against the real highway and confirm lane counts look like a
divided national highway (not a single-lane road), before building traffic
demand on top of it in Phase 2.

**If the Overpass query returns 0 ways:** the `ref` tag on this stretch may be
tagged differently than expected in OSM (e.g. missing `ref` on some segments,
or a different format). Open `road/nh16.osm` and check, or widen the regex in
`scripts/fetch_nh16_osm.sh` and re-run.
