# SEEDExchange: professor research walkthrough

**Status: progress discussion updated 6 November 2026.** This folder curates **24 PNG figures** across the source studies, with 11 numbered stages. It is not a field-certification report or final poster. All figure copies retain links to original data and code; no original simulation outputs are moved or rewritten.

## Research storyline

The study begins with 35 provisional candidate properties, 2025 NASA POWER resource and synthetic household demand, and an EPM GIS-backed low-voltage skeleton with assumed service connections. A full 6,840-task PyPSA/Linopy campaign then optimizes integer PV/BESS/inverter choices and chronological 8,760-hour dispatch under **perfect foresight**.

Independent pandapower tests show why aggregate energy/PCC feasibility does not establish household voltage or thermal feasibility. We examine inverter siting, local Volt-Var, transformer safeguards, coordinated reactive power and their effects on voltage and losses.

**New since the original 3 November walkthrough:** a manufacturer's 20% minimum battery-SOC restriction, successful **SOC-consistent 7-house active-power feedback** under the stricter original voltage research band, and a **12-house reference full-year 0.95–1.05 pu AC pass** with nighttime Q disabled. Full-year stress screening also demonstrates how the original 0.97 pu threshold can classify hours differently from a 0.95 pu engineering target. A reuse-first AC-validation campaign is assessing previously optimized equipment choices; no complete network-feasible economic frontier is claimed yet.

For the connected narrative see [RESEARCH_NARRATIVE.md](RESEARCH_NARRATIVE.md). For original source paths see [FIGURE_INDEX.csv](FIGURE_INDEX.csv).

## Presentation order

| Stage | Topic | Key purpose |
|---|---|---|
| 01 | [Community and inputs](01_Community_and_Inputs/) | Geography, 35 provisional houses, EPM GIS and resource evidence |
| 02 | [Joint PV/BESS sizing](02_Joint_PV_BESS_Sizing/) | Reuse the 6,840-task investment campaign and price/self-sufficiency trade-offs |
| 03 | [Annual battery operation](03_Chronological_Battery_Dispatch/) | Optimized chronological battery charge/discharge and SOC |
| 04 | [Representative feeder AC](04_Representative_Feeder_AC_Screen/) | Why economic screening is not household AC feasibility |
| 05 | [EPM GIS network evidence](05_Geographic_EPM_Feeder_Evidence/) | Infrastructure-backed conductor graph and uncertain service attachments |
| 06 | [Inverter siting and local Volt-Var](06_Inverter_Siting_and_VoltVar/) | Lower/upper voltage, thermal loading, guard behavior and feeder loss |
| 07 | [Coordinated Q and capability](07_Coordinated_AC_Q_Optimization/) | Q-ratio feasibility versus voltage and transformer-loading trade-offs |
| 08 | [Full-year AC and uncertainty](08_Annual_AC_and_Uncertainty/) | Revised voltage bands, 7- and 12-house annual AC and sensitivity limits |
| 09 | [SOC-consistent AC-aware redispatch](09_AC_Aware_Redispatch/) | Four strict-screen 94022 failures resolved by changing annual active-power timing |
| 10 | [Full-campaign equipment feasibility](10_Campaign_Equipment_Feasibility/) | Historical investment reuse, manufacturer SOC and annual AC queue, still in progress |
| 11 | [Next research decisions](11_Next_Research_Decisions/) | Field evidence, loss-aware sizing, resilience and forecasting gaps |

## Interpretation requirements

- **Voltage bands are separate:** 0.97–1.03 pu is the old strict model sensitivity; 0.95–1.05 pu is the proposed engineering magnitude target. Reference to Colombia's national 0.90–1.10 pu or historical EPM 0.90–1.05 pu does **not** make hourly balanced-proxy simulations regulatory certification.
- **AC and energy models are distinct:** PyPSA optimizes fixed-hardware operation with SOC; pandapower independently replays AC voltage and currents. Active-power feedback for **one seven-house reference** was completed, not yet generalized to the archived campaign.
- **Old Q-control plots differ:** earlier sampled coordinated-Q studies used different nighttime Q and SOC assumptions. Preserve them as historic controller comparisons, not direct manufacturer-supported annual dispatch.
- **Costs and grid data are conditional:** demand is synthetic, conductor/service data and some transformer nameplates are provisional or hypothetical, and pandapower losses are not integrated into equipment-cost optimization. Do not claim commercially verified designs.
- **No duplication or invalid completion claims:** the campaign uses the archived 6,840 optimized energy tasks; unvalidated or partial annual-AC output folders remain pending.

## Original studies

- [Current numerical AC and campaign work](../studies/ac_aware_redispatch_v1/)
- [Original PyPSA full study](../studies/pypsa_joint_optimization_v1/)
- [EPM GIS and coordinated Q](../studies/epm_gis_pandapower_v1/)
- [Research status audit](../RESEARCH_STATUS_AND_AUDIT.md) (older document; later progress appears here)
- [Figure provenance index](FIGURE_INDEX.csv)
