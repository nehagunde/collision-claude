# NH16 Collision-Warning — Command Log

Run these in order inside Kali. Updated after every phase — only the final,
working commands are kept here (not the troubleshooting attempts).

---

## One-time / every VM restart: mount the shared folder

The `/mnt/hgfs` mount does not persist across a VM reboot — run this again
whenever `~/collision_claude` looks empty or missing:

```bash
sudo vmhgfs-fuse .host:/ /mnt/hgfs -o allow_other
ls /mnt/hgfs/
```

If `~/collision_claude` isn't there (only needed the very first time, or if
the symlink got lost):
```bash
ln -s /mnt/hgfs/collision_claude ~/collision_claude
```

---

## Phase 0 — Setup & verification

```bash
cd ~/collision_claude
chmod +x scripts/*.sh
bash scripts/verify_setup.sh
```

**Result:** confirmed SUMO 1.25.0, Python 3.13.12, ns-3-dev (`698c627c3`,
mainline), all required Python libraries, and the shared-folder mount.
WAVE module is absent from this ns-3-dev checkout (removed upstream) — 802.11p
will use the `wifi` module's OCB mode instead in a later phase.

---

## Phase 1 — Road network (NH16 Srikakulam -> Visakhapatnam)

Install the one extra dependency needed for the map/selection scripts:
```bash
sudo apt install -y python3-pyproj
```

Fetch OSM data, build the SUMO network, and generate all preview outputs
(this can take a couple of minutes — the query is intentionally slow to
compute, not stuck):
```bash
cd ~/collision_claude
bash scripts/build_road.sh
```

This one command runs all of:
- `scripts/fetch_nh16_osm.sh` — pulls NH16 + real intersecting
  secondary/tertiary side roads from OpenStreetMap
- `scripts/build_network.sh` — `netconvert` -> `road/nh16.net.xml`
- `scripts/plot_network.py` — static preview image, `road/nh16_preview.png`
- `scripts/generate_network_html.py` — interactive map,
  `road/nh16_map.html` (NH16 highlighted red, side roads gray)
- `scripts/generate_nh16_selection.py` — `road/nh16_selection.txt`, a
  netedit/sumo-gui selection file for the same highlighting inside SUMO's
  own viewer

**View the HTML map** (works in any browser, no SUMO needed):
```bash
firefox ~/collision_claude/road/nh16_map.html
```

**View in netedit**, with the same NH16 highlight applied manually:
```bash
netedit road/nh16.net.xml
```
Then: Edit -> Selection -> Load -> `road/nh16_selection.txt`, then colour the
selection.

**View in sumo-gui** (same selection steps as netedit):
```bash
sumo-gui -n road/nh16.net.xml
```

**Result:** 268 NH16 edges, 1,264 real side-road/junction edges, both
verified against the real highway shape.

---

## Phase 2 — Vehicle demand (100 vehicles, all 5 accident causes)

```bash
cd ~/collision_claude
chmod +x scripts/*.sh
bash scripts/build_demand.sh
```

This one command runs all of:
- `demand/generate_vehicles.py` — builds `sim/sumo/routes.rou.xml`: ~85
  through-traffic (highway-only, both directions), ~10 merging + ~5
  crossing side-road vehicles at real junctions, a subset of through-traffic
  re-routed onto oncoming lanes for wrong-way driving, realistic
  car/motorcycle/truck/bus mix
- `demand/vehicle_summary.py` — printed table + `demand/vehicle_distribution.png`
  (type and reference-speed histograms)
- `scripts/run_phase2_preview.sh` — plain headless `sumo` run (no NS-3 yet),
  records `output/phase2_fcd.xml`
- `demand/generate_vehicle_animation_html.py` — animated map,
  `dashboard/vehicles_preview.html` (100 vehicles moving on the real NH16
  map, color-coded by group, play/pause + time slider)

**View the animated preview** (works in any browser, no SUMO needed):
```bash
firefox ~/collision_claude/dashboard/vehicles_preview.html
```

**Note printed by the script if it happens:** it may report building fewer
merge/crossing/wrong-way vehicles than requested if the real NH16 network
doesn't have enough suitable junctions/divided-carriageway stretches — it
tops up the difference with extra through-traffic and prints exactly what
it built, so the real count is always visible, not silently wrong.
