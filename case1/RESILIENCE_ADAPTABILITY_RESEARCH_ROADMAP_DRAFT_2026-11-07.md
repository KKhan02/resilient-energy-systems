# SEEDExchange: resilience, adaptability and grid-forming research extension

**Draft dated 7 November 2026. Proposed extensions, not approved replacements for the LOCKED WP1 research scope.**

## 0. Evidence and work-package boundary

The separately approved file `case1/RESEARCH_SCOPE_APPROVED_2026-11-07.md` controls WP1. This note does not alter A (existing EPM 7-/9-/12-house cohorts, sensitivities and annual validation), B (geographically grouped hypothetical 5–15-house star versus MST), or C (Site A via 94022 then conditional 5-kVA new transformer).

The supplied hackathon final presentation supports both clients' goals, specifically resilience for the community and stability for EPM, but cautions that savings and resilience need simulation and field validation. The project's `case1/studies/architecture_comparison/README.md` already proposes outage-season diversity, full-load energy not served and conditional islanding capability. The university's public SEEDexchange descriptions establish a renewable-powered resilience Living Lab in San Rafael but do **not** identify the technical contents of this team's WP2, WP3, or WP4. The retrieved GitLab repository also does not establish their formal deliverables. **Do not invent a WP2/WP3/WP4 mapping.** The strands below are suggested research tasks which may be assigned to those work packages only after seeing the actual course/project briefs.

The professor's idea as reported by the user is interpreted as **grid-forming (GFM) versus grid-following (GFL)** inverter control under a blackout, followed by a **change in the optimal PV/BESS/inverter cost configuration once resilience capability is valued**. That is a proposed, high-value technical study rather than a completed result.

## 1. Base model and no-duplication handoff

- Begin with a **representative network-feasible WP1 configuration** such as the archived 12-house 41-panel/8-module/12-kVA design on provisional EPM 106039, after checking the exact manufacturer-SOC-corrected hourly inputs and whether the network model applies. Include both a low-cost candidate and a high-self-sufficiency candidate once WP1 verifies them. Do not call historical 5-kVA economic optima electrically proven.
- Reuse 2025 NASA generation, distinct stochastic house-hour loads and the existing PyPSA LP/MILP dispatch. Use original pandapower bus/line/transformer models for steady-state voltage/thermal checks. Do not claim static hourly pandapower can compute frequency, RoCoF, PLL dynamics, seamless transfer or inrush transients.
- Reuse full-load baseline without invented priority/deferrable percentages. Keep one house = one source profile ID and maintain seeds. Save source hashes and baseline scenario identity.
- Separate ***network selection, physical architecture, power-electronic control*** and ***economic objective***. A single experiment changes one dimension while others are held constant. Match PV DC panels, battery energy, DC battery power and inverter AC capability across meaningful control comparators; add architecture-specific equipment cost later.

## 2. Professor's proposed experiment: GFM versus GFL during blackout

**Primary question:** For the same local PV+BESS hardware and customer demand, what loads can actually remain supplied during an EPM blackout under the installed inverter controls, and at what incremental cost can the microgrid acquire islanding/black-start capability?

- **S0 grid connected, GFL:** normal reference operation with EPM grid present. Establish cost, grid purchases, voltage/thermal and SOC trajectory.
- **S1 blackout, GFL only, with no independent voltage-frequency reference:** do **not** model it as an islanded source. Grid-following control ordinarily requires an energized reference and anti-islanding / protection disconnects. Report no intentional local service, *unless* a separately identified, capable grid-forming source already exists.
- **S2 blackout, GFM capable PV/BESS with verified islanding scheme:** controlled PCC opening, local voltage-frequency regulation, available battery SOC, inverter current limit and supported loads. Grid-forming capability is *necessary to establish the island voltage*, but is not sufficient to guarantee islanding protection, acceptable fault-clearing, inrush or long-term energy autonomy.
- **S3 black start (distinct event):** begin with local bus de-energized, check the inverter's and battery's ability to form a reference and pick up load blocks under energization, inrush and SOC limits. A successful seamless transfer does not establish black-start success.
- **S4, optional mixed fleet:** one GFM source plus GFL sources, relevant to multiple community clusters. Existing GFL PV can synchronize to the locally established GFM reference, subject to controls, protection and inverter compatibility.

**Causal study method:** First reproduce annual *normal* operating SOC and dispatch, then draw blackout start times across seasons, weather and high/low load. Do not let year-ahead PyPSA foreknowledge pre-charge the battery before a surprise outage. For a separate **preparedness policy** test, predefine a causal reserve SOC and measure its real annual grid-cost penalty. Example outage durations as research scenarios: 2, 8, 24, 48 and 72 hours, without pretending any distribution is an observed EPM outage frequency. Include no-PV night onset, multi-day poor solar, peak evening load and high/low initial SOC. Re-run grid-connected prelude, blackout window, and post-restoration recharge, with a consistent energy balance and no future data leakage.

**Metrics:** annual and event energy not served (kWh), fraction of full household load served, hours all loads are covered, restoration time, time to BESS SOC floor, inverter power/current violations, PV curtailment, bus voltage bounds, transformer/line loading, recovery grid purchases and extra $/year under reserve strategy. For frequency transient studies add frequency nadir/zenith (Hz), RoCoF (Hz/s), voltage settling, critical bus load steps, current-limit excursions and transition/black-start pass/fail.

**Simulation separation:** 8760-hour PyPSA for investment/operational SOC, 8760-hour / outage-window pandapower for quasi-static nodal V/thermal feasibility, and a **separately validated dynamic inverter model** (e.g. existing team Simulink/PowerFactory/validated reduced-order simulator if available) for GFM droop, GFL PLL, frequency dynamics, transfer and black start. Do not simulate inverter frequency controls by changing only power factors in static pandapower. A credible dynamic GFM model needs grid-forming control law (droop/VSM/VOC as chosen), inner control, saturation/current limiting, filter/network impedance and protection logic. A GFL model needs current control/PLL and anti-islanding/synchronization. Avoid claiming manufacturer Deye unit has grid-forming mode without a supporting product manual.

## 3. Make resilience change the economic optimum rather than add an afterthought

Re-evaluate the existing WP1 candidate pool under explicit *new* requirements, not a complete replay of 6840 prior planning tasks:

1. **Economics only:** original investment cost/annual import objective, with prior physical limits, existing candidate equipment and same community demand.
2. **Resilience constraint:** e.g. require at least a selected percentage of *total* household demand served during an unannounced 24- or 48-hour blackout at specified start hours. This need not be achievable for all 5–15-house cases on an existing 5-kVA network; report infeasibility rather than inventing load flexibility.
3. **Cost to buy islanding:** include candidate price difference between GFM-capable hardware and GFL hardware, islanding switch/transfer, controls, protection, commissioning, and any battery/inverter oversizing. Unknown prices are sensitivity **ranges**, not assumed zero.
4. **SOC preparedness:** examine reserve floor policies (e.g. 20%, 40%, 60% usable operating reserve above manufacturer physical floor where consistent with definition) versus extra grid imports, self-sufficiency and outage success; define reserve coordinate clearly.
5. **Robustness:** vary outage timing, solar profile reductions, load uncertainty and equipment outage; compare the Pareto trade-off between annualized cost and full-demand energy unserved / survival probability over an explicitly stated event ensemble.

Report a new **cost versus resilience** frontier: how many extra USD/year per additional kWh of blackout demand served (and per hour of full service), plus differences in PV, BESS, inverter and service-connection sizes. Compare **minimum cost grid-connected**, **minimum cost for resilience target**, and **highest achievable resilience within a fixed budget**. Show whether the preferred WP1 economic optimum changes when GFM and blackout capacity are required. This is a testable thesis, not an assumed outcome.

Keep the economic treatment of utility exports, grid-only baseline, physical energy losses, inverter lifetime and battery replacements consistent with the approved WP1 model. Do not conflate self-sufficiency (%) with a metric of islanding survival.

## 4. Additional high-value study opportunities (prioritized, not assigned to formal WP2–WP4)

| Priority | Study | Controlled variables | Useful outputs and why |
|---|---|---|---|
| 1 | **Outage timing and battery preparedness** | 2/8/24/48/72h outage; 12 calendar months; initial SOC; normal versus reserved dispatch | Distinguishes annual self-sufficiency from actual blackout survivability and costs of reserve |
| 1 | **Grid-following vs grid-forming and black start** | Same hardware, capable controls and protection; GFL with/without an external forming reference; GFM; optional mixed fleet | Establishes which services are physically possible and quantify switching/frequency/voltage response |
| 1 | **Resilience-constrained re-sizing** | Original least-cost, constrained EENS and budget; GFM hardware premium, battery/power size | Shows when resilience changes the economic optimum, the professor's core point |
| 2 | **Topology resilience for B/C** | star/MST; line/service length x1/1.3/1.6; feeder outage locations; isolating sectionalizers where proposed | Quantifies single-line common-mode vulnerability, houses left energized, restoration costs |
| 2 | **Cluster coordination resilience** | independent islanded clusters, physically interconnected microgrids only with designed protection, coordinated energy sharing absent a physical tie | Benefits and feasibility of 7/9/12 household clusters, without parallel transformer secondaries by assumption |
| 2 | **Technology/controller uncertainty** | inverter GFM modes, DC battery power/current limits, nighttime Q disabled, low irradiance, temperature, reserve, controller delays | Exposes designs feasible in hourly balance but unstable or current-limited at transitions |
| 3 | **Adaptability to growth and resource changes** | physically coherent N=5..15 populations, growth rates, PV degradation, 20% solar variation, battery failure and replacement | Cost of adaptive modular expansion, hosting headroom and retrofit decisions |
| 3 | **Community-versus-EPM trade-off** | transformer export cap, PF/Q, energy sharing/meters, tariff uncertainty, network investment and compensation scenarios | Presents $/house/year versus EPM voltage and hosting limits without inventing tariff or legal permissions |

**Risk-first priority:** do not invest in costly sub-second dynamics for dozens of unverified hardware selections. First select two or three electrically justified WP1 physical designs and meaningful outage cases; then validate the controls, expand if the response surfaces or viability boundaries remain uncertain.

## 5. Evidence gaps and modelling questions that really matter

1. **Formal WP2, WP3 and WP4 briefs:** not supplied in current accessible project records; do not name or assign official deliverables without them. The suggested resilience and adaptability experiments can later be mapped to actual work packages.
2. **Inverter capability:** Does the actual proposed inverter support autonomous grid-forming, off-grid transition, black start, GFL companion parallel operation and specified short-circuit current? A GFM label alone does not prove it can safely supply selected households.
3. **Islanding boundary:** Where is the isolating breaker/PCC; do all loads and PV/BESS share a physically continuous LV island? Existing distinct EPM transformers cannot be assumed interconnected by copper.
4. **Cost evidence:** supplier-specific GFM/GFL premium, transfer/protection, metering, feeder reinforcements, O&M and compatible battery/BMS; keep scenarios separate until priced.
5. **Dynamic validation:** actual controller parameters, inertia/droop power/current limits, black-start sequencing, fault protection and three-phase/split-phase network behavior.
6. **Field validation:** household profiles are synthetic, feeder routes provisional; no EPM official outage schedule, utility protection approval or customer loads yet. Give results correct conditional labels.

## 6. Source notes

**Existing project sources (do not treat as WP2–WP4 charters):**
- `case1/RESEARCH_SCOPE_APPROVED_2026-11-07.md` (locked scope)
- `case1/studies/architecture_comparison/README.md` (already identifies full-demand blackout hours, SOC preconditioning, conditional islanding)
- `case1/studies/annual_shared_pvbess/README.md` (previous central vs shared cluster study)
- `Community_Energy_Final.pdf`, slide "Project Context & Client Requirements" (community resilience/EPM stability); slide "Value Proposition" notes resilience requires model and field validation
- Original `SEEDexchange_Medellin_Project.md` recognizes islanding as a distinct heavier study needing grid-forming/balancing/black-start

**Independent technical background, not work-package definitions:**
- National Renewable Energy Laboratory, *Introduction to Grid-Forming Inverters* (2024): https://www.nrel.gov/docs/fy24osti/90256.pdf
- National Laboratory of the Rockies, *Black Start*: https://www.nlr.gov/grid/black-start
- PNNL, *Modeling of Grid-Forming and Grid-Following Inverters for Dynamic Simulation of Large-Scale Distribution Systems* (2020), DOI 10.1109/TPWRD.2020.3018647: https://www.osti.gov/biblio/1909842
- PNNL, *Optimal Control for Fast Frequency Response and Black-Start using Embedded Storages with Grid-Forming Control* (2025): https://www.pnnl.gov/publications/optimal-control-fast-frequency-response-and-black-start-using-embedded-storages-grid

## 7. Current next actions

1. Complete/aggregate the user's two running 12-house annual AC candidate runs with the **existing read-only exporter**. No new PyPSA campaign. This informs WP1 Study A only.
2. Systematically continue WP1 A existing-EPM cohort and equipment validation (7/9/12) with PF, length, Q/control and AC-aware redispatch, matched saved results. B/C follow once A evidence is organized.
3. Meanwhile record, but do not yet simulate, the **GFM/GFL outage comparator**, definitions of full-load resilience and a scenario-specific *resilience-constrained* cost reoptimization objective.
4. Obtain formal internal WP2–WP4 definitions, then assign the agreed research extensions rather than guessing their package numbers.
