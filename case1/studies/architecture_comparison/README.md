# San Rafael Case 1 — PV/BESS expansion, grouping and network-impact study protocol

**Status: DRAFT FOR ENGINEERING DISCUSSION, not an approved design or simulation.** This document sets the correct research priorities without changing the main Case 1 code or saved results.

## 1. Main research question

> How many households can be served, at what electricity cost, self-sufficiency and grid/network impact, as we increase PV capacity (kWp), battery energy (usable kWh) and battery charge/discharge power (kW); and when is one shared PV+BESS installation preferable to several *shared group-level* PV+BESS clusters?

The dominant variables are **household grouping, installed PV, BESS energy/power, inverter topology, grid constraints and lifecycle costs**, not a generic "one PV + one battery at every house" comparison.

### Primary architectures (different physical decisions)

- **C — Centralized shared PV+BESS**: one larger installation at candidate Site A or another defensible shared location, serving the selected household group(s). One equipment location; actual LV feeder/PCC(s) unverified.
- **K — Distributed GROUP-LEVEL clusters**: two or more *shared* installations, each serving several nearby homes. Each cluster gets its own physically valid connection topology, inverter and BESS bank. Examples: 12 homes as 2 groups of 6 or 3 groups of 4, and 20 homes as 2 of 10 or 5 of 4 (exploratory partitions, NOT mapped EPM groups).
- **H — Hybrid cluster topology**: a principal central PV+BESS installation plus satellite shared PV and/or BESS for subsets of homes. Quantities and locations are open; it does not mean distributed PV necessarily at every household.
- **I — Individual PV+BESS at EVERY home**: accepted as an ADDITIONAL benchmark, not the primary distributed or hybrid research. This extends the individual/shared sensitivity already explored in PyPSA v18. Discrete 5.12 kWh battery-module, inverter and roof feasibility constraints apply; cannot assume one whole-module bank can use the shared inverter quoted for four modules.
- **PV-only controls** without storage are needed to isolate storage value; no extra hybrid-without-a-hybrid component should be counted as a distinct architecture.

**Do not assume that connecting several physically independent clusters behind the SAME 5 kVA PCC multiplies its rating.** A "cluster" may refer to grouping behind a single transformer/PCC, independent grid-connected nodes, or a network with an approved shared bus. Those are different electrical and commercial architectures, and should NOT be conflated. Use conditional results only until confirmed by EPM/physical mapping.

## 2. Evidence already available, and what it does NOT prove

- **PyPSA v18** already compares shared versus individual systems using matched total hardware and household profiles, and studies 4–8-household consumption and limited PV/BESS sweeps. It is energy-system modelling, **not a detailed feeder model**. The earlier PV sweep deliberately capped at 12 panels and four battery modules.
- **pandapower v5** already explored stochastic 4–8-household groupings, transformer/feeder headroom, and voltage/load stress. It uses representative rather than surveyed LV geometry. The existing 324.5 m route and 4–8-house scenarios should be the starting reference, **not proof** that future expanded clusters share one circuit.
- **Case 1 v3** already screens households 4–20, PV 8–80 × 435 W, batteries 0–24 modules and additional 5–15 kW battery-power cases. Historic ~11,515 design rows are **stale** after dispatch/economics/provenance revisions and NOT independently pandapower validated. It provides a scenario foundation, not an approved optimum or a physical limit of 17 homes.
- Candidate Site A has a user-digitized ~1,759 m² *gross* clearing, not a verified usable construction site. Reference proposal: **12 × 435 W = 5.22 kWp**, **4 × 5.12 kWh = 20.48 kWh nominal**, ~17.3 kWh usable modelled, **~50 m²** tentative total installation footprint (not a survey).

## 3. Expansion/grouper design matrix — three types of comparisons

**A. Capacity growth at fixed household count and fixed physical topology.** Hold the same demand realization, PV resource basis, tariff scenario and inverter/transformer assumptions. Increase PV panel count, battery module count and battery kW *independently*, then in combinations. Record incremental change in grid import/export, unmet demand, curtailment, annual cost, battery throughput/life, thermal loading, household voltage and footprint. Explicit PV-only and grid-only references. Use equipment-feasible ratings; do not extrapolate an actual inverter beyond port/input limits.

**B. Population growth at given installed system.** At fixed hardware and physical topology, add households incrementally. This identifies where the existing design becomes insufficient, but **it is NOT the same as optimizing system size for each number of households**.

**C. Joint group size + equipment sizing + clustering.** For total households N (initial study N=4–20), compare *one shared group* against multiple partitions (e.g. N=8: 1×8 versus 2×4; N=12: 1×12, 2×6, 3×4; N=16: 1×16, 2×8, 4×4; N=20: 1×20, 2×10, 4×5, 5×4). For each partition, search physically valid PV, BESS and inverter sizes. These are **research partitions**, not geospatial clusters until household coordinates are linked to the topology. Larger populations may be studied later only after constraints and network model assumptions are agreed.

The two distinct comparisons that must both be reported:

1. **Matched TOTAL hardware** across C/K/H: same total PV panels, nominal/usable battery energy and **same aggregate permitted battery kW**, as far as physically feasible, plus the same demand and irradiation reference. This isolates topology / power-sharing / diversity. A 5 kW **per-cluster** choice with two clusters becomes 10 kW aggregate and is *not* equal hardware to a single 5 kW installation; do not silently call it matched.
2. **Optimized REAL-WORLD equipment per architecture**: each cluster has discrete devices, and can carry extra inverters, BMS, protection, metering and BOS costs. Compare optimized lifecycle cost, resilience, connection constraints and spatial footprint even if capacities differ.

If absent feeder data mean an aggregate energy model cannot distinguish where PV is located, explicitly say so instead of reporting a fabricated topology advantage. **Network loading, bus voltage, feeder current/losses, reverse-flow distribution and the electrically weakest/farthest house** go to the separately maintained pandapower model.

## 4. Staged study method: PyPSA / dispatch, pandapower, pvlib, economics

### Stage 1 — Shared reference and robust capacity sweep
Use the same year/hours/loads for all scenarios and a versioned pvlib-derived solar input. Maintain a grid-only and PV-only reference. For each N, run incremental PV, battery-energy and charge/discharge-power sweeps, respecting battery/inverter ratings. Report **zero-ENS normal-operation screening** and self-sufficiency/cost trade-offs; never call a scenario network-feasible based on PCC kVA screening alone. Compare fixed-5-kW bank power versus manufacturer-permitted power *as separate scenario axes*, already agreed.

### Stage 2 — Group/cluster configurations
Use spatially meaningful household membership when actual coordinates are available; otherwise clearly document synthetic partitions. For C, K, H and secondary I, allocate PV, batteries, inverters, electricity demand and available roof/ground area. Define whether clusters exchange power, have separate PCCs/meters or share a capped transformer; the effect on power flows and costs depends on this definition.

### Stage 3 — pandapower validation (separate electrical workstream)
Transfer chronological and stress-case injections for each distinct point in the **actual or explicitly synthetic** LV topology. Compute minimum/maximum individual house voltage, farthest/worst node, current, cable and transformer loading, losses, import/export and reverse power flow over appropriate samples. Model voltage-drop with pandapower, **not** illustrative resistance-only "answer" tables. Treat 5 kVA nameplate / 4.5 kVA operational cap as the existing single-PCC reference assumption, NOT extra capacity created by PV storage or by re-labelling the same connection. Study upgrades or multiple separate PCCs only as separately costed/permitted alternatives, not an assumed EPM approval.

### Stage 4 — Land, roof and solar yield
Use Site A's traced polygon and **assumed level ground** as a preliminary candidate, not surveyed land. Apply the documented pvlib tree-height and setback **sensitivity** only as explicit hypothetical shade cases, not measured loss. For K/H/I verify (or label unknown) each candidate cluster plot or roof, array/setback sizing, shared BESS enclosure, inverter/switchgear/access and cable routing. **50 m²** is for the original 12-panel/four-module proposal only; do not linearly scale it without a physical layout.

### Stage 5 — Consistent lifecycle economics and robustness
Compare annualized equipment, inverter and battery replacement per validated HOMER-based rules, grid imports and optional export credits, but **also installation and BOS**, additional inverters/switchgear/protection, any extra transformers/cables/service drops, maintenance, land/civil works and metering/settlement where evidenced. Unknown costs remain explicit ranges/unpriced, not zeros masquerading as verified. Report total cost and cost/house/year, marginal $/additional-household, incremental $/kWh grid import avoided, and cost per increased reliability outcome. Avoid claiming official EPM tariffs/approval from HOMER illustration.

For resilience compare diverse outage start hours, months and low-solar conditions using full normal household demand **without any 30%-critical or 15%-deferrable decomposition**. Report total ENS, time all load is served, annual SOC drift/preconditioned SOC, recovery. Islanding service remains **conditional** on proper inverter/control/protection topology; multiple islanded clusters may perform differently.

## 5. Pareto and decision reporting

Within each N/grouping and topology, compare annualized cost vs grid dependence vs full-load resilience, and retain all electrical/site constraints as distinct feasibility gates. Do not mix total project costs across very different household numbers without normalization. Show PV/BESS footprint, grid voltage envelopes, curtailment and connection assumptions as independent constraints. Hold user approval before weights, reference capacities or actual cluster split are selected.

## 6. Proposed research gates requiring discussion BEFORE implementation

- **Electrical ownership/connection:** actual transformer 94022 locations, split-phase details, whether one PCC, multiple individually rated PCCs or an upgrade is permitted; cluster sharing/meters.
- **Group topology and households:** actual household geocoordinates/branch membership, right to build Site A/other cluster plots, roof availability and real feeder routes.
- **Hardware and BOS:** whether commercially operable single-module household storage exists, parallel inverter compatibility, per-cluster equipment counts and costs.
- **Expansion range:** beyond the existing 4–20 households? desired self-sufficiency targets? boundary conditions for "served" (zero grid-connected ENS vs acceptable probabilistic threshold).
- **Objectives and ranking:** resilience on the Pareto or as a separate stress-screen, export-credit economics only as sensitivity or allowed real tariff, cost of new connection/reinforcement.
- **Critical/deferrable loads REMAIN PARKED** until professor decision. No active scenario should use those fractions.

### Implementation hold
This branch is **documentation and comparison design only**. Do not run or alter the optimization, PV/BESS sizing or saved CSV/Pareto figures until the team agrees which group/PCC assumptions and matched-vs-optimized comparisons to implement. Version all supporting data in GitLab, with tests, provenance and CI.
