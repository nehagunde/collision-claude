# Related Research Papers — NH16 Accident Causes & VANET Collision Warning

Guide-requested, 2026-08-02: replace/supplement the news-report-based
accident analysis with actual research papers. Compiled via web search;
access notes below (some are paywalled beyond the abstract).

---

## D. General highway accident causation, India (not region-specific)

Added 2026-08-02 — guide clarified the causal grounding should come from
general highway accident-causation research (India-wide, mixed-traffic
conditions), not just NH16/Vizag-specific news reports. Vizag/NH16 is only
the implementation testbed, not the scope of the causal analysis. Mix of
foundational reviews + recent (2024-2025) studies, per guide's preference.

### Foundational / review papers

**"A Systematic Review on Road Traffic Accident: Causes and Control Measures"**
ResearchGate. A systematic review (surveys many individual studies rather
than one dataset) — good for citing the *overall landscape* of established
accident causes and control measures.
https://www.researchgate.net/publication/370004806_A_Systematic_Review_on_Road_Traffic_Accident_Causes_and_Control_Measures

**"Road Traffic Accidents in India: Issues and Challenges"**
ScienceDirect (Transportation Research Procedia). Widely-cited general
overview paper on India's road accident problem — good foundational
citation for the "why this is a serious problem in India" framing.
https://www.sciencedirect.com/science/article/pii/S2352146517307913

**"Evaluation of risk factors for road accidents under mixed traffic: Case study on Indian highways"**
ScienceDirect. Directly matches our project's context — mixed traffic
(two-wheelers, cars, trucks, buses together) specifically on Indian
highways. Identifies risk factors: mid-block access points, pavement/
shoulder condition, vehicle type, time of day, road configuration
(two-lane vs multi-lane). Notes multi-lane highways have lower crash
*rates* but higher crash *severity* — relevant to how we set per-vehicle-type
TTC thresholds.
https://www.sciencedirect.com/science/article/pii/S0386111222000516

### Highway/expressway-specific, driver-behavior-focused

**"Identification of Factors Causing Risky Driving Behavior on High-speed Multi-lane Highways in India Through Principal Component Analysis"**
International Journal of Engineering (IJE). Directly about high-speed
multi-lane highways (exactly our scenario, not urban roads). Identifies
factor groups via Principal Component Analysis: overtaking/mirror use,
night driving behavior, helmet/seatbelt/insurance compliance, vehicle age
and lane preference. Good for grounding *why* our system checks lane and
closing-speed behavior specifically.
https://www.ije.ir/article_154252.html

**"Assessment of Fatal Rear-End Crash Risk Factors of an Expressway in India: A Random Parameter NB Modeling Approach"**
ASCE Journal of Transportation Engineering, Part A: Systems (2023). Focused
specifically on **rear-end crashes** on an Indian expressway — this is the
closest academic match to our system's core rear-approach TTC alert case.
Solid engineering-journal citation.
https://ascelibrary.org/doi/10.1061/JTEPBS.0000767

**"Investigating Risk Factors Affecting Crash Frequency on the Expressways in India: A Random Parameters Negative Binomial Modeling Approach"**
ASCE Journal of Transportation Engineering, Part A: Systems (2025).
Companion-style study, general crash-frequency risk factors on Indian
expressways — recent (2025).
https://ascelibrary.org/doi/10.1061/JTEPBS.TEENG-8491

### Latest official/statistical reports (2024-2025)

**India Status Report on Road Safety 2024**
IIT Delhi, Transportation Research and Injury Prevention Centre (TRIPC) —
freely downloadable full PDF. Near-primary-source quality (academic +
government data combined), the most authoritative "latest" citation
available. States over-speeding is the largest single risk factor
nationally, and that National Highways carry disproportionate fatality
share relative to their share of total road length.
https://tripc.iitd.ac.in/assets/publication/India_Status_Report_on_Road_Safety-20242.pdf

**"Statistical Analysis of Road Accidents in India"**
International Journal for Multidisciplinary Research (IJFMR), 2025. Recent,
open-access, general statistical treatment.
https://www.ijfmr.com/papers/2025/1/37160.pdf

### Recommended "best 4" for this general-causation part, if a short list is wanted

1. **Evaluation of risk factors under mixed traffic: Indian highways** (ScienceDirect) — closest match to our actual project context.
2. **India Status Report on Road Safety 2024** (IIT Delhi TRIPC) — most authoritative, freely downloadable, latest official data.
3. **Fatal rear-end crash risk factors, Indian expressway** (ASCE, 2023) — directly grounds the rear-approach TTC case.
4. **Risky driving behavior on high-speed multi-lane highways, India** (IJE, PCA study) — grounds the driver-behavior side of the design.

---

## A. Accident causes / black spots specific to this highway (kept for reference — guide clarified this is secondary to the general-causation papers above)

### 1. "Identification and Analysis of Black Spots on NH5 - Visakhapatnam (India)"
ResearchGate. Directly about our corridor — NH5 is the pre-2010 name for
this stretch of NH16 through Visakhapatnam. Identifies specific black spots
(Hanumanthwaka, Yendada junction, Cricket stadium junction, Carshed
junction, Madhurwada junction) using police accident data and spot-speed
studies. **Most directly relevant paper found — same road, same city.**
Full text is behind ResearchGate's login wall; abstract/citation accessible.
https://www.researchgate.net/publication/262488672_IDENTIFICATION_AND_ANALYSIS_OF_BLACK_SPOTS_ON_NH5_-_VISAKHAPATNAM_INDIA

### 2. Ramakrishna, M. & Ramesh, B. (2022) — Blackspots on NH-216A (a spur of NH16)
IJRASET (open access, fully readable). Studies a 49 km stretch (Diwancheruvu
to Siddantham, East Godavari district) using 3 years of accident data
(2018-2020) and the **Weighted Severity Index (WSI)** method — the standard
methodology Indian black-spot studies use. Recommends an Advanced Traffic
Management System (video surveillance, variable message signs, better
signage) — useful as a real citation for *why* a warning system approach is
a recognized mitigation strategy, and for the WSI methodology itself if your
guide wants a formal severity-ranking method behind the "5 real accident
causes" list.
https://www.ijraset.com/research-paper/identification-and-mitigation-of-blackspots-and-implementation-of-an-advanced-traffic-management-system

### 3. Visakhapatnam WSI study using AP Traffic Police data (2014-2021)
Referenced across search results studying black spots in Visakhapatnam using
official Andhra Pradesh Traffic Police crash data with the WSI method.
Worth tracking down the exact title/venue directly via Google Scholar if
your guide wants the primary citation — search results point to this
existing but full bibliographic details weren't confirmed via direct fetch.

---

## B. Wrong-way driving in India specifically (grounds our highest-severity alert case)

### 4. "Factors Affecting Wrong-way Driving Crashes and Fatalities: A Scenario with High Incidence of Wrong-way Movements"
*Transportation in Developing Economies* (Springer), 2024. **This is the
strongest methodological match** — a peer-reviewed journal article analyzing
wrong-way driving (WWD) crashes using real Tamil Nadu state crash data
(2009-2021) with statistical methods (logistic regression). Findings
directly relevant to our system: WWD is worse in India specifically because
of "deficiencies in road networks and access management" and the
prevalence of two-wheelers — matches what we found for NH16. Also finds WWD
crashes are more common on state highways, at intersections, and involve
non-car vehicles. Full text is behind Springer's login wall; abstract/
findings accessible via search.
https://link.springer.com/article/10.1007/s40890-024-00235-9

---

## C. VANET / V2V collision-warning system design (grounds the technical approach)

### 5. Talukder, S. et al. (2022) — "Vehicle Collision Detection & Prevention Using VANET Based IoT With V2V"
arXiv (fully open access — **best one to actually hand your guide a full
PDF of**). Combines IoT sensors with VANET/V2V communication for collision
detection, with driver alerts (buzzer/LED). Less about accident-cause
statistics, more about system architecture — useful to cite as precedent
for "a V2V-based warning system is an established research approach," which
supports the overall project design.
https://arxiv.org/abs/2205.07815

### 6. "A VANET-based real-time rear-end collision warning algorithm" (VERCWA)
Proposes an algorithm using space headway, velocity, and driver behavior to
assess real-time collision risk and time warnings appropriately — close to
our own Time-To-Collision approach for the rear-approach alert case. Full
text behind ResearchGate login; abstract accessible.
https://www.researchgate.net/publication/310615948_A_VANET-based_real-time_rear-end_collision_warning_algorithm

### 7. "Novel Time-Delay Side-Collision Warning Model at Non-Signalized Intersections Based on V2I"
Relevant specifically to our **merge-approach** case — models collision
warning timing at unsignalized junctions, which is exactly the scenario of
a vehicle merging onto NH16 from a side road. Open access (PMC/NCBI).
https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7915759/

---

## Recommended "best 3" if your guide only wants a short list

1. **Paper #1** (NH5 Visakhapatnam black spots) — same exact road/city, strongest local grounding.
2. **Paper #4** (Wrong-way driving in India, Springer) — peer-reviewed, statistical, directly explains our #1 alert case.
3. **Paper #5** (arXiv V2V collision system) — fully open access, gives a full readable PDF, establishes the V2V design approach has academic precedent.

## Access note

ResearchGate and Springer links above are paywalled beyond the abstract —
full text usually requires institutional/university library access. If your
university has IEEE Xplore / ScienceDirect / Springer access, search these
exact titles there for full PDFs. IJRASET (#2) and arXiv (#5) are freely
downloadable in full right now.
