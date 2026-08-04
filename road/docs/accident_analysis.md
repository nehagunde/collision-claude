# NH16 (Srikakulam <-> Visakhapatnam) — Accident Analysis

Guide-requested step, completed 2026-08-02: analyze real accident patterns on
this specific highway before designing the collision-warning system, so the
system targets scenarios that actually occur here rather than generic
assumptions.

## Scale of the problem on this corridor

- Srikakulam district portion: 2,588 accidents over 29 months (Jan 2015 -
  May 2017) — ~90/month, 27 deaths/month.
- Wider Icchapuram-Vempadu 330 km stretch (NHAI, contains our corridor):
  ~3 fatal accidents per day.
- Visakhapatnam district: NH16 alone accounts for **over 70%** of all road
  accidents in the district, ~300 deaths/year, 800+ permanently disabled.
- 40+ identified black-spot locations in Vizag district alone; Nakkapalli and
  Yelamanchali (Rural) police areas have 14 between them. Lankelapalem ->
  Tagarapuvalasa records the highest concentration.

## Accident scenario list (real causes, ranked by how often they're cited)

1. **Wrong-side / wrong-direction driving via unauthorized median openings.**
   The single largest cause — **over 30% of fatal accidents** on the Vizag
   stretch happen because drivers cross the median and drive against traffic
   to reach a destination instead of using a proper U-turn. Nakkapalli alone
   sees 5-6 such accidents/month from unauthorized crossings.
2. **Local traffic merging in, conflicting with through traffic.** Poorly
   designed side-road access points cause frequent conflicts between local
   traffic (mostly two-wheelers) joining the highway and fast-moving through
   traffic (mostly goods vehicles).
3. **Speeding and negligent driving / tailgating.** Cited generally as a
   primary cause alongside the above.
4. **Two-wheelers bear a disproportionate share of deaths** — specifically
   called out for the Anakapalli portion of NH16.
5. **Chain-reaction crashes from a single point failure.** Documented case:
   a tire burst sent an SUV into the opposite lane, it hit a two-wheeler,
   then was run over by a truck — 11 dead in one incident.
6. Secondary/infrastructure factors (not directly addressable by V2V
   communication, noted as a scope limitation): poor lighting, road damage,
   rain/drainage issues at night.

## Mapping to the collision-warning system's alert cases

| Real cause | System coverage |
|---|---|
| Tailgating / rear-end | Rear-approach case (TTC, same lane, vehicle behind) |
| Sudden braking / erratic vehicle ahead (e.g. tire-burst chain reaction) | Front-approach case (TTC, same lane, vehicle ahead) |
| Local traffic merging in | Merge-approach case (TTC, vehicle joining from side road at a real junction) |
| **Wrong-side / head-on driving via median crossing** | **New: wrong-way case** (added after this analysis — see below) |
| Two-wheelers over-represented in deaths | Vehicle-type mix updated to include motorcycles (see below) |

**Two design changes made directly because of this analysis** (previously
only 4 alert cases and a car/bus/truck-only vehicle mix were planned):

- **Wrong-way alert case (5th case):** a vehicle detects another vehicle
  broadcasting a heading opposite to its lane's expected direction of travel
  — a genuine wrong-way vehicle, not just a fast one. This is the
  highest-severity alert given it's the top real cause of fatalities here.
  Alert example: `"Wrong-side vehicle approaching head-on near <location>,
  please be alert immediately."` Implemented in SUMO by routing a small
  number of vehicles onto the opposite-direction carriageway at a
  median-opening point, mirroring the real-world behavior.
- **Vehicle mix now includes motorcycles/two-wheelers**, not just car/bus/
  truck, since they're specifically over-represented in NH16 deaths.

## Sources

- [Alarming rise in road mishaps on NH-16](https://www.thehansindia.com/posts/index/Andhra-Pradesh/2017-06-19/Alarming-rise-in-road-mishaps-on-NH-16/307308)
- [NH-16 turns into a death trap](https://www.deccanchronicle.com/150724/nation-current-affairs/article/nh-16-turns-death-trap)
- [Visakhapatnam Road Accident: Four Killed as Car Hits Stopped Lorry on NH16](https://www.andhrajyothy.com/2026/andhra-pradesh/visakhapatnam-road-accident-four-killed-as-car-hits-stopped-lorry-on-nh16-1543268.html)
- [Is the National Highway-16 in Visakhapatnam safe enough for travellers?](https://www.yovizag.com/national-highway-16-visakhapatnam-safety/)
- [Accidents rise as roads crumble - The Hindu](https://www-thehindu-com.translate.goog/news/cities/Visakhapatnam/accidents-rise-as-roads-crumble/article65483984.ece?_x_tr_sl=en&_x_tr_tl=bn&_x_tr_hl=bn&_x_tr_pto=tc)
- [NH-16, Two-Wheelers Account For Bulk of Road Deaths in Anakapalli](https://www.deccanchronicle.com/southern-states/andhra-pradesh/nh-16-two-wheelers-account-for-bulk-of-road-deaths-in-anakapalli-1936526)
- [Eleven dead road accident near NH16](https://www.deccanherald.com/india/eleven-dead-road-accident-near-2058692)
