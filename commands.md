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

## Phase 2 — (not started yet)

*(commands will be added here once Phase 2 is built)*
