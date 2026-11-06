# SEEDExchange Case 1: research progress narrative

**El Arenal, Antioquia, Colombia | Updated for professor review, 6 November 2026**

This is a staged research discussion, not a finished design or EPM compliance study. Open the [11 ordered sections](README.md) and their 24 curated original figures in parallel. Every numerical result below is conditional on documented demand and feeder assumptions.

## 01. Community, energy resource and provisional network evidence

Thirty-five candidate properties were mapped near El Arenal. NASA POWER/pvlib-derived 2025 PV availability and independently seeded synthetic household profiles provide the annual reference. The profiles were normalized from prior work; **there are no verified individual household meters**. EPM GIS records support transformer and conductor-node topology, but physical house-service assignments, cable specifications, phases and some transformer nameplates remain unconfirmed. We distinguish provisional geographical layouts from EPM-mapped LV backbone geometry. [01](01_Community_and_Inputs/) and [05](05_Geographic_EPM_Feeder_Evidence/) show these evidence levels.

## 02. Already completed joint capacity-and-energy optimization

The initial investment research jointly optimized integer PV panel counts, battery module counts, battery power and inverter ratings with **all 8,760 consecutive hourly operation decisions**. PyPSA/Linopy used a DC-coupled PV/BESS system with cyclic storage SOC, inverter and battery efficiencies, import costs and an aggregate PCC kVA proxy. The preserved **6,840-task MILP** produced 6,820 energy-screen optimal and 20 infeasible results across 12 household configurations and five assumed transformer ratings. Original results remain read-only.

Annualized costs are based on historical equipment quotes, assumed grid import prices and a 25-year accounting model. Connection, site works and real-network losses are not fully costed. The original model's horizon has **perfect foresight**, so its SOC schedule is a planning benchmark, not an online implemented controller. [02](02_Joint_PV_BESS_Sizing/) shows investment trade-offs and [03](03_Chronological_Battery_Dispatch/) shows operation.

## 03. Independent AC tests reveal missing network constraints

An aggregate energy/PCC screening constraint cannot establish household voltage, transformer loading, line current or distribution losses. We therefore replayed the existing active-power trajectories through pandapower: first on representative radial feeders, then on geographically assumed routes, and finally on the GIS-backed LV backbone with provisional service drops. The results depend on conductor resistance, phase proxy and actual household connection data, so 'AC feasible' always means **conditional under this model**. See [04](04_Representative_Feeder_AC_Screen/) and [05](05_Geographic_EPM_Feeder_Evidence/).

## 04. Local voltage control and inverter location

Inverter connection at the transformer head, midpoint or remote feeder end changes voltage and thermal margins. The original local HIL Volt-Var and transformer Q-guard tests found that reactive support can relieve low voltage or reduce overvoltage while also increasing transformer currents and feeder losses. A thermal guard can remove an overload yet allow unwanted voltage rise. Additional **copies of the original maximum-voltage and sampled-loss plots** now appear in [06](06_Inverter_Siting_and_VoltVar/); original numerical studies remain untouched.

## 05. Coordinated Q selection and Q-ratio trade-offs

The coordinated controller searches feasible Q at each selected AC operating point and checks voltage and transformer/line loading simultaneously. In the historical **40-critical-hour** reference, 106039 required at least the *tested* Q ratio 0.25 at the head or 0.20 at the midpoint to pass all 40, under the then-current 0.97–1.03 pu screen. The 94022 midpoint reached at most 38/40. The new supplementary trade-off plot shows that raising Q beyond a useful level can increase apparent-power loading and losses without improving feasibility. [07](07_Coordinated_AC_Q_Optimization/) separates this sampled Q-search evidence from annual AC tests.

Historical Q-sweep settings are not identical to the subsequent manufacturer-SOC scenarios. Nighttime inverter reactive operation in older studies is **not manufacturer-verified**. The new annual cases disable nighttime Q. A 40-hour controller comparison cannot certify 8,760-hour feasibility.

## 06. Manufacturer battery-SOC correction

The original investment sweep used historical modelled usable battery energy. A subsequent fixed-hardware study instead enforces the Deye SE-G5.1 **20% physical minimum SOC**, retaining full-year state-of-charge chronology and the same equipment. For the selected seven-house 94022 design (26 panels, five modules, 7.6 kVA inverter), annualized energy-model cost changed from about **USD 2,772.94 to USD 2,810.01**. The approximately USD 37.07/year increment is due to the SOC operating restriction, not the later AC correction.

The corresponding twelve-house 106039 design has 41 panels, eight modules and a 12 kVA inverter. Its historical energy-only annual estimate of about **USD 4,767.83** becomes **USD 4,820.76** with the manufacturer SOC floor. The 5 kVA transformer is a **hypothetical sensitivity** for this territory, not a confirmed utility nameplate. See [08](08_Annual_AC_and_Uncertainty/) and [09](09_AC_Aware_Redispatch/).

## 07. Re-evaluating voltage criteria and completing annual AC replay

The original **0.97–1.03 pu** limit was a **strict research choice**, not an established EPM regulatory voltage band. The corrected workflow reports the **proposed 0.95–1.05 pu engineering magnitude target** separately from the national and historical EPM reference bands. Hourly balanced-proxy simulations cannot demonstrate legal compliance with measurement durations or actual phases.

At the seven-house 94022 reference, the manufacturer-SOC annual AC replay passed **8,756/8,760** hours against 0.97 pu, with minimum voltage **0.968184 pu**. However, it already passed all hours at the proposed 0.95 pu minimum. After annual feedback redispatch, the same fixed hardware passed **8,760/8,760** under the original strict band, minimum **0.970099 pu**.

The 12-house, 106039 manufacturer-SOC configuration passed **8,760/8,760** hours under the proposed **0.95–1.05 pu** band, minimum **0.955651 pu** and peak transformer loading **94.44%**. That small thermal margin requires separate robustness investigation.

In a full-year seven-house stress replay with unchanged dispatch, PF **0.90** and service multiplier **1.6**, all 8,760 hours still passed 0.95–1.05 pu. **111** hours failed the original stricter 0.97 pu floor, a consequence of the stricter research screen. The new annual voltage-duration and threshold-comparison figures are in [08](08_Annual_AC_and_Uncertainty/).

The 12-house, nine-scenario PF/service sensitivity so far covers only **96 critical hours per scenario**. The worst sampled case, PF 0.90 and factor 1.6, reached **0.94411 pu** minimum voltage and **106.86%** transformer loading. The selected hours are nighttime, so this is not complete annual uncertainty evidence.

## 08. SOC-consistent AC-aware active-power feedback

The seven-house 94022 manufacturer's schedule had four late-November hours below the strict 0.97 pu line. AC power sampling identified provisional feasible inverter P corridors at these operating points. The existing annual PyPSA model then **reoptimized all 8,760 battery charging, discharging and SOC hours with the same hardware**, not just the failing snapshots. Independent pandapower replay confirmed **8,760/8,760** strict-screen passes; the recorded modelled annual cost remained **USD 2,810.01**, with no AC-feedback incremental cost.

This demonstrates an actionable difference between static reactive compensation and **chronological active-power coordination**, but the real-grid connection and annual loss-aware economic effects still need verification. [09](09_AC_Aware_Redispatch/) links the precise manifest and original hourly trajectories.

## 09. Reusing all existing equipment investment results

The preserved 6,840-task annual investment campaign is **not being rerun**. The reuse index maps all original tasks to **6,339 distinct hardware configurations**, retaining the original objectives and failed cases. It places **1,214** into the current mapped/hardware-screen-ready annual SOC and AC queue. For hardware lacking a saved hourly trace, the fixed-hardware energy model reconstructs an 8,760-hour manufacturer-compatible operation trajectory, after which pandapower performs annual AC replay at specified PF and service-length combinations. That fixed-hardware operational solve is **new evidence**, not a new capacity-investment sweep.

The network-feasible cost/self-sufficiency frontier is **not yet complete**. Partial campaign output folders must not be counted as fully validated. The evidence-led approach and open questions are recorded in [10](10_Campaign_Equipment_Feasibility/) and [11](11_Next_Research_Decisions/).

## Remaining work

Complete the annual campaign and corrective SOC-aware feedback for failed hardware, verify battery current ratings and inverter nighttime Q support, include AC/inverter losses in economics, obtain utility transformer and service connection records, and then test outage resilience, forecast-based operation and new-household hosting. Until those are complete, all results are conditional research design evidence.
