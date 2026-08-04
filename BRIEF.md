# NH16 Collision-Warning Project — Spec & Decisions

**Purpose of this file:** Single source of truth for this project's goal,
locked decisions, architecture, and phase plan. Update this file when a
decision changes; treat it as the contract.

**Working rule:** Work strictly phase by phase. Pause after each phase for the
user to say "go" before starting the next. No batch-dumping multi-phase code.

**Relationship to other project:** This is a **separate, unrelated** VANET
project from `vanet_claude/` (the Visakhapatnam jam-detection/U-turn project).
Do not merge scope, corridor, vehicle counts, or code between the two. Lives
entirely under `collision_claude/`.

---

## 1. Goal

Build a working VANET collision-warning prototype that:

1. Uses the real **NH16 highway between Srikakulam and Visakhapatnam** (~100 km)
   as the road network.
2. Populates it with **100 vehicles**.
3. Tracks each vehicle's **speed and lane** continuously.
4. Simulates **V2V** (OBU↔OBU) communication only — no RSUs/infrastructure
   (see §2 for why).
5. Each vehicle broadcasts a periodic beacon (id, position, speed, lane,
   timestamp) to nearby vehicles.
6. On receipt, a vehicle computes **Time-To-Collision (TTC)** against
   same-lane and adjacent-lane neighbors, and raises an alert when TTC drops
   below a safety threshold — covering rear-approach, front-approach,
   side/blind-spot, **merge-approach** (a vehicle joining the highway from a
   side road at one of the real junctions), and **wrong-way** (a vehicle
   heading the opposite direction to its lane — see accident analysis below)
   cases.
7. Alert example: `"Vehicle approaching fast from behind, please be alert."`
   Merge case example: `"Vehicle merging from side road near <junction>,
   please be alert."` Wrong-way case (highest severity): `"Wrong-side
   vehicle approaching head-on near <location>, please be alert
   immediately."`
8. Grounded in a real accident analysis of this specific highway (guide-
   requested, completed 2026-08-02) — see
   `road/docs/accident_analysis.md`. Real NH16 data shows wrong-side/
   median-crossing driving causes over 30% of fatal accidents on this
   stretch (the single largest cause), which is why the wrong-way case
   exists as its own alert type rather than being folded into front-approach.
9. Evaluates the system with a **before/after comparison** (alerts on vs off)
   measuring near-collision events, and presents results via a **live
   dashboard**.

Deliverable context: this is an **academic presentation project** (guide-
assigned). Optimize for clarity, clean comments, and a watchable demo over
cleverness.

---

## 2. Locked decisions (do not relitigate without asking)

| # | Decision | Value |
|---|----------|-------|
| Corridor | Full NH16 Srikakulam → Visakhapatnam (~100 km), real alignment from OpenStreetMap. Includes real intersecting side roads/junctions within ~400 m of the highway (not just the highway line in isolation) — decided 2026-07-30 after confirming the initial Phase 1 extraction had excluded them. |
| Vehicle cohort | Fixed 100 vehicles, sparse over the full stretch (deliberate choice — realistic highway density over full-stretch-sparse alternative). Staggered depart times, both directions. No rolling spawn. **Split (decided 2026-08-02):** ~85 "through-traffic" vehicles travel the highway end-to-end (route forced to highway edges only, not shortest-path over the whole graph, so they can't accidentally drift onto side roads); ~15 "merging" vehicles start on a side road and join the highway at one of the real junctions from Phase 1, then continue on the highway afterward (no exiting back onto a side road — confirmed simplest behavior is sufficient). The merging group is what makes the side roads functionally meaningful, not just decorative, and is what enables the merge-approach alert case in §3. |
| Vehicle type mix | Car/bus/truck plus **motorcycles/two-wheelers** (added 2026-08-02 after the accident analysis — real NH16 data specifically calls out two-wheelers as bearing a disproportionate share of deaths on this highway, e.g. in the Anakapalli stretch). A small number of vehicles are also configured as **wrong-way** vehicles (route onto the opposite-direction carriageway at a median-opening point), mirroring the #1 real cause of fatal accidents on this highway (see `road/docs/accident_analysis.md`). |
| Vehicle data source | 100% simulator-generated (SUMO car-following/lane-changing models), calibrated to real NH16 speed rules (~100 km/h cars, ~80 km/h trucks/buses) and a realistic vehicle-type mix. **Not** pulled from any live traffic API — no public real-time source gives per-vehicle position/speed/lane at the granularity collision detection needs. |
| Communication architecture | **Pure V2V, no RSUs.** Collision warning is a time-critical, short-range problem between nearby vehicles — infrastructure relay would add latency without benefit. (Contrast with the jam-detection project, which needs RSUs to bridge distance for area-wide alerts.) |
| Collision-detection metric | **Time-To-Collision (TTC)** = distance ÷ relative closing speed, not a raw speed threshold. Per-vehicle-type threshold (trucks get a longer safe TTC than cars, reflecting braking distance). |
| Response mode | Closed-loop: on receiving an alert, the at-risk vehicle reacts via TraCI (brake or lane-appropriate response), not just a passive log message. |
| Host vs target | Files authored on Windows at `C:\Users\NEHAGUNDE\Desktop\collision_claude\`. Runs inside the same Kali Linux VM used for the other project (SUMO + NS-3 only practical on Linux). Exact shared-folder mount path to be confirmed in Phase 0. |
| SUMO / NS-3 versions | Verified in Phase 0: SUMO 1.25.0, ns-3-dev at commit `698c627c3` (mainline `master`). |
| 802.11p implementation | ns-3's `wifi` module in **OCB mode** (`WIFI_STANDARD_80211p`, "Outside the Context of a BSS") — the legacy `wave` module has been removed from this ns-3-dev checkout upstream (unmaintained), and OCB mode on the `wifi` module is the modern, actively-maintained way to get the same 802.11p V2V radio behavior. We don't need WAVE's extra IEEE 1609 stack (multi-channel switching, WSMP) since our beacons are simple periodic broadcasts. |
| SUMO ↔ NS-3 coupling | TraCI bridge, same pattern as the other project: Python supervisor talks to SUMO via `traci`; NS-3 runs as a separate process consuming mobility snapshots. |
| Language split | C++ for the NS-3 WAVE/802.11p app (Python bindings are only partially maintained on this ns-3-dev install). Python for everything else: vehicle generation, TraCI supervisor, TTC/collision logic, evaluation, dashboard feed. |
| Demo mode | SUMO-GUI on, color-coded vehicles (green = normal, alert-color = warning triggered). Headless flag also supported for the before/after evaluation runs. |
| Sim duration | Proposed default **3600 s** (1 simulated hour, roughly matching real transit time end-to-end at highway speed). Configurable via launcher flag — confirm in Phase 0. |
| Evaluation runs | Two runs per experiment: alerts **off** (baseline) and alerts **on**, same seed/demand, to produce the before/after near-collision comparison. |

---

## 3. Collision-warning rule (fixed spec)

For every beacon received from a neighbor vehicle, compute:

```
TTC = distance_to_neighbor / relative_closing_speed   (undefined/∞ if not closing)
```

Checked against five neighbor relationships:

- **Same lane, neighbor behind, closing** → rear-approach check
- **Same lane, neighbor ahead, closing** → front-approach check
- **Adjacent lane, closing** → side/blind-spot check
- **Merging vehicle approaching a highway junction, closing on nearest
  highway vehicle (or vice versa)** → merge-approach check. This is the case
  that actually uses the side roads/junctions from Phase 1 — a "merging"
  vehicle (see §2 vehicle cohort split) joining the highway from a side road.
- **Neighbor's heading is opposite to the expected direction of its own
  lane** → wrong-way check (added 2026-08-02, see
  `road/docs/accident_analysis.md`). This is independent of distance/closing
  speed thresholds below — a genuine wrong-way vehicle is always
  highest-severity regardless of TTC, since it's the #1 real cause of fatal
  accidents on this highway (>30% of fatalities, per the accident analysis).

An **ALERT** is raised when `TTC < threshold` (wrong-way case: always, per
above), where the threshold is per-vehicle-type (trucks/buses use a longer
threshold than cars, reflecting real braking distance — exact values to be
set in Phase 4 from published braking-distance references).

Alert payload format (V2V beacon + alert):

```
BEACON  { vehicle_id, position, speed, lane, heading, timestamp }
ALERT   { target_vehicle_id, source_vehicle_id, relation (rear|front|side|merge|wrongway),
          ttc, severity, junction_id (for merge only), timestamp }
```

(`heading` added to the beacon payload — needed for the wrong-way check.)

Human-readable rendering: `"Vehicle approaching fast from behind, please be alert."`
(with `front`/`side` variants as appropriate). Merge case: `"Vehicle merging
from side road near <junction>, please be alert."` Wrong-way case (highest
severity): `"Wrong-side vehicle approaching head-on near <location>, please
be alert immediately."`

In all five cases, the at-risk vehicle's closed-loop response (§2) applies —
it slows down after receiving the alert, not just logs it.

---

## 5. Architecture — three parts

### Part 1 — Road & Demand generation (Python, one-time/static)
- Pulls NH16 Srikakulam→Vizag OSM data, runs `netconvert` → `corridor.net.xml`.
- Generates 100 vehicles' routes (`.rou.xml`): ~85 through-traffic (forced
  highway-only route, both directions) + ~15 merging (start on a side road,
  join the highway at a real junction, continue on highway afterward) — with
  realistic speed/type mix and staggered departures.

### Part 2 — Simulation Node (SUMO + NS-3, V2V only)
- SUMO runs the microsimulation; tracks per-vehicle speed/lane every step.
- NS-3 `wifi` module in OCB/802.11p mode (ad-hoc, no infrastructure nodes)
  simulates the wireless beacon exchange between nearby OBUs, including
  realistic packet loss/range.
- TraCI bridge feeds mobility one way; alert-triggered vehicle responses flow
  back (closed-loop).
- TTC/collision logic (Python) sits on the beacon-receive path.

### Part 3 — Evaluation & Dashboard
- Runs the alerts-off / alerts-on comparison, logs near-collision counts,
  warning lead-time, false-positive rate, message delivery ratio.
- Produces comparison chart(s) (pandas + matplotlib/seaborn).
- Live HTML/JS dashboard: color-coded map + scrolling alert feed, reading
  from a JSON log the simulation writes as it runs (same lightweight pattern
  as the other project's `vanet_gui_live.html` — no heavy frontend framework).

---

## 6. Project directory layout (proposed)

```
collision_claude/
├── BRIEF.md                      # this file
├── README.md                     # written in the final phase
├── requirements.txt
├── road/
│   ├── nh16.osm
│   ├── nh16.net.xml
│   └── docs/corridor_notes.md
├── demand/                       # Part 1 — Python
│   └── generate_vehicles.py
├── sim/                          # Part 2 — SUMO + NS-3
│   ├── sumo/
│   │   ├── collision.sumocfg
│   │   └── routes.rou.xml
│   ├── ns3/
│   │   ├── collision-scenario.cc
│   │   ├── v2v-beacon-app.cc
│   │   └── v2v-beacon-app.h
│   └── bridge/
│       ├── traci_supervisor.py
│       └── ttc_collision_logic.py
├── evaluation/                   # Part 3
│   ├── run_comparison.py         # alerts-off vs alerts-on
│   ├── metrics.py
│   └── results/
├── dashboard/
│   └── live_dashboard.html
├── output/
│   ├── results.csv               # per-vehicle speed/lane/alert history
│   ├── alerts.log
│   └── comparison_chart.png
└── scripts/
    ├── install_kali.sh
    └── run_demo.sh
```

---

## 7. Phases (work strictly in this order, pause between each)

Every phase must end with a **visible, verifiable output** — not just code
that exists unseen. See §8 for the standing rule and the "Output:" line under
each phase for what that phase must show.

- **Phase 0 — Setup & verification.** Confirm SUMO/NS-3/WAVE module on the
  Kali VM, confirm shared-folder mount path for `collision_claude/`, create
  directory tree, `requirements.txt`. No simulation code.
  **Output:** printed tool-version check (`sumo --version`, `ns3 --version`,
  WAVE module presence) and a directory listing showing the created tree.
- **Phase 1 — Road network.** Pull NH16 Srikakulam→Vizag from OSM, run
  `netconvert` → `nh16.net.xml`, sanity-check lane counts against the real
  highway.
  **Output:** a rendered image/screenshot of the generated network (via
  `netedit`/SUMO-GUI or `sumolib` plot) so the road shape can be visually
  checked against the real NH16 alignment, plus a short lane-count summary.
- **Phase 2 — Vehicle demand.** Generate 100 vehicles' routes: ~85
  through-traffic (highway-only, both directions) + ~15 merging (start on a
  side road, join the highway at a real junction, continue on the highway),
  with a realistic vehicle-type mix — car/bus/truck **plus
  motorcycles/two-wheelers** (added 2026-08-02 per the accident analysis) —
  and staggered departures. Also include a small number of **wrong-way
  vehicles** (routed onto the opposite-direction carriageway at a
  median-opening point), grounded in real NH16 data showing this as the #1
  cause of fatal accidents on this highway (`road/docs/accident_analysis.md`).
  Also run a quick standalone headless `sumo` simulation (no NS-3/TraCI yet —
  that's Phase 3) purely to record vehicle movement, and render it as a
  self-contained HTML page (real NH16 map via Leaflet/OSM tiles, vehicles
  animated along it, color-coded by type/group, play/pause control) —
  presentable on its own, no VM or SUMO-GUI needed to view it. This becomes
  the seed for the full dashboard extended with alerts in Phase 6.
  **Output:** a summary table/printout of the 100 generated vehicles (type,
  group, depart time, direction/junction, initial speed), a histogram of the
  speed/type distribution, and `dashboard/vehicles_preview.html`.
- **Phase 3 — SUMO + NS-3 V2V coupling.** `collision.sumocfg`,
  `collision-scenario.cc`, `v2v-beacon-app.{cc,h}` (`wifi` module in
  OCB/802.11p mode, ad-hoc, no RSU nodes), `traci_supervisor.py` bridge.
  Mobility → beacons flowing, no collision logic yet.
  **Output:** a sample log excerpt showing real beacons being sent/received
  between specific vehicle IDs (with position/speed/lane payload), proving
  the SUMO↔NS-3 bridge and V2V exchange actually work end to end.
- **Phase 4 — TTC collision-warning logic.** Implement the rule from §4 (all
  five relation types, including merge-approach for the merging vehicle
  group and wrong-way for the wrong-way vehicle group from Phase 2),
  per-vehicle-type thresholds, closed-loop slow-down response via TraCI.
  **Output:** a sample log/console trace of at least one real TTC calculation
  and one triggered ALERT for each relation type (with the human-readable
  message) — including at least one real merge-approach case and one
  wrong-way case — plus a SUMO-GUI run/screenshot showing an alerted vehicle
  visually flagged and slowing down.
- **Phase 5 — Evaluation.** Alerts-off vs alerts-on comparison runs, metrics
  (near-collision count reduction, lead-time, false-positive rate, delivery
  ratio), comparison chart.
  **Output:** the actual comparison chart image plus the printed metrics
  table (near-collision counts before/after, lead-time, false-positive rate,
  delivery ratio) from a real run — not placeholder numbers.
- **Phase 6 — Dashboard & output.** Live HTML/JS dashboard, `results.csv`,
  `alerts.log`, end-to-end `README.md` with run instructions.
  **Output:** the dashboard opened and shown running against real log data
  (screenshot or live view), plus the final `results.csv`/`alerts.log`
  contents and the README.

---

## 8. Hard rules

- **Phase gate.** End every phase with "Phase N complete — ready for Phase
  N+1?" and stop. Do not start the next phase until the user says "go".
- **Show output every phase.** No phase is "done" on code existing alone —
  each phase must run and display real output (a log excerpt, a rendered
  image/screenshot, a printed table/chart, a console trace) proving that
  phase's work actually functions, per the "Output:" line listed under each
  phase in §7. Never report a phase complete without showing this.
- **No RSUs.** This project is pure V2V — do not introduce infrastructure
  nodes into the architecture.
- **No live traffic API calls** for vehicle data — simulator-generated only
  (see §2).
- **Relative paths only** in code.
- **Comment for clarity** — this is a presentation project. Explain the
  *why* of non-obvious logic (TTC formula, threshold choice, WAVE app
  structure). Skip narration of obvious code.
- **Minimal dependencies**, prefer apt-installable on Kali.
- **Kali is the runtime.** All scripts target Linux (forward slashes, bash).
- **Keep separate from `vanet_claude/`** — no shared files, no merged
  decisions, unless the user explicitly says to combine the two projects.

---

## 9. Where to start

On "go", begin **Phase 0** only:

1. ~~Verify SUMO, ns-3-dev, and the WAVE/802.11p module are available~~ —
   done: SUMO 1.25.0 and ns-3-dev (`698c627c3`) confirmed; WAVE module absent
   upstream, 802.11p will use the `wifi` module's OCB mode instead (see §2).
2. Confirm the shared-folder mount path for `collision_claude/` (likely
   `/home/kali/collision_claude/`, to confirm).
3. List Python libs needed (`traci`, `sumolib`, `pandas`, `matplotlib`, etc.)
   and produce `requirements.txt`.
4. Create the directory tree from §6, with placeholder files where useful.
5. Stop. Ask the user to confirm Phase 0 before starting Phase 1.
