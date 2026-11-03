# SEEDExchange: resilient community energy, El Arenal (Colombia)

This repository preserves the SEEDExchange Case 1 research on shared PV and battery systems for rural electricity consumers. The central investigation connects **joint equipment sizing and hourly energy dispatch** with **geographically informed AC electrical feasibility**.

## Start here

**[Professor research walkthrough: numbered figures 01–09](case1/professor_walkthrough/README.md)** is the current progress presentation, with a brief explanation beside each figure. It is **not** the final poster.

**[Research status and independent review](case1/RESEARCH_STATUS_AND_AUDIT.md)** explains current evidence, perfect-foresight limitations, model versions, historical results and unresolved questions.

## Where the reproducible research lives

- [PyPSA joint PV/BESS and inverter MILP](case1/studies/pypsa_joint_optimization_v1/) and its `outputs/full_study/` campaign.
- [EPM GIS LV network and coordinated AC reactive control](case1/studies/epm_gis_pandapower_v1/), including critical-hour, Q-sweep, uncertainty and annual AC outputs.
- [Georeferenced 35 houses and EPM evidence](case1/studies/community_georef/).
- [NASA weather and source case inputs](case1/data/).
- [Earlier representative feeder and historical studies](case1/studies/).
- [Research archive](case1/research_archive/) for superseded previews, transfer ZIPs and old illustrative figures.

## Results and their limits

The local 6,840-task optimization co-optimizes equipment and 8,760 hourly PV/BESS operations under **perfect foresight**. Its energy-screen classifications are not proof of LV feeder feasibility. A separate EPM GIS pandapower study reports a conditional annual pass for transformer 106039, but with only 0.000005 pu above the 0.97 voltage threshold and remaining stress-case failures. Service associations, cable impedances, phase balance and inverter VAR capability require field/equipment verification.

The older Case 1 v3 figures and other independent dispatch engines are retained for provenance but must not be merged with the current MILP outputs without reconciling their assumptions.

**Current next research:** SOC-consistent AC-aware battery redispatch, followed by resilience and adaptability.

The recently pushed local modelling campaign was intentionally **not CI-validated** on GitLab because the commit used [ci skip]. Avoid describing it as GitLab-CI-verified. This repository curation also skips CI.
