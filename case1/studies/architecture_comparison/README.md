# San Rafael Case 1 — Architecture comparison protocol (DRAFT, NO IMPLEMENTATION)

**Status:** Study structure proposed for review. This documentation DOES NOT select an architecture, equipment catalogue, metering contract, feeder geometry, outage system, PV orientation or dispatch control. NO simulation code or published results are changed by this branch.

## 1. Research objective and agreed design directions

Compare these three physical architectures:
- **C — Centralized PV + centralized BESS:** common ground/roof installation with AC injection at a shared LV node; Site A is a candidate, not approved or surveyed.
- **D — Distributed PV + distributed household BESS:** arrays and storage at individual premises. Each house needs an actual available roof/site and a compatible electrical installation.
- **H — Distributed rooftop PV + shared BESS:** generation at household nodes; a shared bank at a separately identified common node (possibly Site A).

The team already agreed to multi-objective **annualized supply cost**, **energy self-sufficiency**, **resilience during diverse outages**, installation **footprint**, and a 2-D sensitivity on BESS **usable energy** versus **power**. Voltage drop and voltage rise at **all houses** are an explicit **separate pandapower workstream**. **Critical-load percentages and deferrable-load management are PARKED completely**, including in the active baseline and comparative studies. The old 30% / 15% modelled shares must not enter active results.

## 2. Apples-to-apples reference: 4 households only

The proposal quoted **12 × 435 W PV panels = 5.22 kWp** and **4 × 5.12 kWh battery modules = 20.48 kWh nominal**; the main model describes **17.3 kWh usable** for that bank. The **~50 m² complete-system footprint** is a planning estimate, not a measured module layout or buildable area. The inverter quotation describes one 5-kW unit; whether it is compatible with the real service and other architectures is UNRESOLVED.

For a **conceptual 4-household matched-capacity comparison**:
- C: all 12 PV panels and 4 battery modules at one shared site;
- D: a *hypothetical even split* of 3 PV panels and one battery module per house (only where the exact inverter/BMS and roof are capable of operating a single module);
- H: 3 PV panels per house; 4 battery modules at one shared site.

All three share **the same total demand timeseries, annual resource basis, number of panels, nominal storage, and initially the same total permitted battery charging/discharging-power target**. The presently used 5 kW total BESS-power limit is a **reference study target**, not proof of safe or purchasable inverter/BMS configurations. Physical inverter conversion capacities, module granularity, wiring and inverter efficiency must be checked, and apparent equal-capacity combinations can be ruled out if the hardware cannot support them.

The no-BESS PV-only control should be retained for each feasible architecture as a baseline. A second series will vary battery module count and hardware-permitted discharge/charge power **independently**, without silently upgrading inverter capabilities.

For **8–20 households**, the neat one-module-per-house allocation with just four total battery modules is impossible. Do **not** pretend that fractional modules can be installed. The capacity- and service-matched architecture grid must be rebuilt using physically discrete allocations and identifiable houses. Avoid asserting that each house has a battery if only a subset does.

The CSV `architecture_reference_matrix_DRAFT.csv` is a **planning matrix, NOT a device procurement list**.

## 3. Evaluation stages

### Stage 0 — Confirm constraints and business boundaries (decision gate)
Determine whether the community has one legally permissible common connection/meter, individual meters, virtual self-consumption or another permitted arrangement. EPM interconnection/export rules, ownership, supplier warranties and islanding hardware cannot be inferred from energy modelling. Confirm actual installation rights for Site A and household roofs.

### Stage 1 — Neutral capacity comparison (model-design proposal, not yet executed)
Keep the SAME annual household demand realization, resource year, panel count, battery energy, target battery-power allowance, and assumed tariff/discount assumptions. Evaluate C, D and H **without inventing site-to-site yield benefits**. Differences should only arise from topology-dependent inverter efficiency, electrical losses and genuine additional equipment where explicitly represented and evidenced. If physical topology is absent, report **"equivalent aggregate-energy model cannot discriminate location"**, not a spurious ranking.

### Stage 2 — Spatial and solar-resource sensitivities
For Site A use `../site_a_solar/` and the digitized ~1,759 m² gross clearing, with **level ground assumed** and tree-height/setback sensitivities. The solar study calculates **plane-of-array irradiation**, not proven PV yield. Rooftop geometry/shading is unknown and may only be handled by clearly labelled hypothetical scenarios until roof data are available. Avoid claiming centrally or distributively superior shading by default.

### Stage 3 — LV electrical workstream in pandapower
Build/reference an LV feeder with actual or labelled hypothetical nodes, cable lengths, conductor properties, transformer connections, household legs/phases and injection locations. Compare lowest-house voltage, voltage-rise hours, thermal currents, losses and active/reactive PCC. The 5-kVA reference transformer and assumed 90% (4.5-kVA) operating envelope are **screening assumptions**, not utility approval; the algebraic PCC cap cannot certify household voltages. No results from this workstream are implied by the present protocol.

### Stage 4 — Resilience and design economics
Calculate grid-connected reliability using **all household demand**, without critical/deferrable splits. For outages, compare **total demand served, total ENS, hours of full-load supply, depletion/recovery** at diverse start times and solar conditions. Islanded service is a **conditional technical scenario** until true grid-forming operation, switchgear, anti-islanding/protection and transfer arrangements are verified. Compare real inverter/BESS counts and costs and give no export-credit baseline with explicitly hypothetical remuneration sensitivities until tariff evidence is obtained.

## 4. Common proposed reporting (no rankings yet)

Each architecture/population should report:
- PV kWp, nominal and usable BESS kWh, maximum battery charging/discharging kW, inverter ratings and number of inverter devices;
- annual demand, ENS, PV supply, grid imports/exports, self-sufficiency of total demand, curtailment and signed annual SOC drift;
- annualized equipment/replacements, grid purchases, total USD/year and USD/household/year, plus unpriced site/electrical/civil-work omissions;
- total unserved energy and full-demand availability in outages; no assertion of protected minimum household service;
- required PV/ground/rooftop area, equipment enclosure and access area, site/feeder geometry provenance, shaded PV assumption;
- pandapower minimum and maximum bus/service voltage and worst-house node, feeder losses and ampacity where topology validation exists;
- feasibility status in separate columns: `energy_screen`, `site_space`, `hardware`, `network`, `islanding`, `EPM_approval`. Never collapse into a blanket "feasible" flag.

## 5. Decisions STILL requiring discussion BEFORE implementation

1. **Metering/ownership/community sharing**: physically shared LV connection versus separately metered houses; what constitutes a "community" tariff/settlement?
2. **Distributed storage definition**: every house must have BESS, or is a mixed subset acceptable? This controls comparison fairness and storage granularity for 8–20 homes.
3. **Equipment matching**: reference 5-kW inverter is not trivially replaceable by four small hybrid inverters; establish feasible catalogue options, costs, and AC/DC topology.
4. **Roof feasibility**: identify which houses have roof area, solar access and permission; Site A ground rights remain unverified.
5. **Grid and islanding architecture**: interconnection location(s), utility service type, neutral/phase arrangements, export policy, and conditional island-capable topology.
6. **Scope and priorities**: confirm the exact normalization of cost and whether resilience is part of the Pareto objective or a separate stress-screen.

The scenario matrix is deliberately a **4-household illustration** only. There are **no new results, design selections, or engineering claims** in this work.

## 6. Provenance and connections

- Site A source geometry, hypothetical pvlib shade outputs and CI provenance: [Site A solar study](../site_a_solar/README.md).
- Historical Case 1 results are stale and must not be republished as if this architectural study reran them.
- Development process: agree choices, then test-first implementation on a separate MR, then reference validation and electrical network verification.
