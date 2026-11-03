# SEEDExchange: professor research walkthrough

**Current purpose:** A chronological progress review with figures, not the final poster.

Open numbered folders 01 to 09 in order. Each folder contains an image sequence and a short explanation of the question, method, results and next step. Original numerical outputs and code remain in their source study folders. This directory is a curated copy, not a new numerical analysis.

## Research storyline

We first identified the 35 candidate households, mapped EPM transformer assets and reconstructed the evidence available from NASA weather, synthetic electricity demand and utility GIS. PyPSA/Linopy then co-optimized discrete PV, BESS and inverter choices with 8,760 hourly battery charge, discharge and state-of-charge values. These runs use *perfect foresight*, meaning they know the entire modelled year in advance; interpret them as planning benchmarks, not proven causal controls. We independently replayed active power in pandapower. A representative feeder revealed voltage constraints, EPM GIS improved the backbone topology, and reactive power was optimized with transformer and voltage safeguards. One 106039 reference case passed an entire year's hourly AC screen but has negligible voltage margin. Other uncertainty cases and 94022 still fail. Next is SOC-consistent active-power redispatch, then resilience and adaptability.

## Folder sequence

| Order | Story | Why it follows |
|---|---|---|
| 01 | [01_Community_and_Inputs](01_Community_and_Inputs/) | Why El Arenal, and what data can the models rely on? |
| 02 | [02_Joint_PV_BESS_Sizing](02_Joint_PV_BESS_Sizing/) | Joint equipment sizing: PV, BESS, inverter and cost |
| 03 | [03_Chronological_Battery_Dispatch](03_Chronological_Battery_Dispatch/) | How the optimized battery is used across time |
| 04 | [04_Representative_Feeder_AC_Screen](04_Representative_Feeder_AC_Screen/) | First electrical falsification: aggregate feasibility is not AC feasibility |
| 05 | [05_Geographic_EPM_Feeder_Evidence](05_Geographic_EPM_Feeder_Evidence/) | Moving from hypothetical feeders to EPM-mapped conductor sections |
| 06 | [06_Inverter_Siting_and_VoltVar](06_Inverter_Siting_and_VoltVar/) | Why inverter siting and reactive control help, and where they fail |
| 07 | [07_Coordinated_AC_Q_Optimization](07_Coordinated_AC_Q_Optimization/) | Coordinated Q control with thermal and voltage constraints |
| 08 | [08_Annual_AC_and_Uncertainty](08_Annual_AC_and_Uncertainty/) | Annual AC validation and fragility to uncertain inputs |
| 09 | [09_Next_Research_Decisions](09_Next_Research_Decisions/) | Research decisions, not completed results |

## Core scientific distinctions

**Planning optimality is not real-time control.** The MILP solves investment and the whole year's energy dispatch simultaneously. Its schedules are based on full-year information. Economic numbers are conditional on the stochastic reference demand, prices and source data.

**Battery SOC was optimized already.** The later pandapower runs fix the previously optimized active-power trajectory and adjust Q. They have not re-optimized battery charge/discharge with network feedback or a changed SOC trajectory.

**AC passing does not verify as-built EPM compliance.** Feeder sections come from EPM GIS, while household service assignment, conductor impedance/ampacity and balanced equivalent phase treatment are assumptions. The 106039 annual result is 8,760/8,760 conditional passes at 0.970005 pu minimum voltage.

**Costs are annualized economic equivalents.** Upfront CAPEX differs from equipment annuity/O&M/replacement plus annual net grid energy; cost per house is the annual total divided by participants. Historical quotes omit substantial site-specific network costs.

## Source and review pointers

- [Current research status and audit](../RESEARCH_STATUS_AND_AUDIT.md)
- [Main mixed-integer optimization](../studies/pypsa_joint_optimization_v1/)
- [EPM GIS and coordinated AC control](../studies/epm_gis_pandapower_v1/)
- [Archived figures and upload bundles](../research_archive/)
- [Numerical provenance index](FIGURE_INDEX.csv)

The older source READMEs may still reflect package-authoring status before locally completed runs. Read the latest manifests and this progress index for current state.
