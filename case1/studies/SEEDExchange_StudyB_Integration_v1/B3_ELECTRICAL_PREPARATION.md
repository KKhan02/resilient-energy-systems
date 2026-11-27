# Study B B3 electrical preparation (27 November 2026)

Proposed modelling basis, not authorization of real equipment or final design. Reuse Study A and legacy EPM GIS model conventions from `../epm_gis_pandapower_v1/run_epm_validation.py` and `epm_topology.py`. These are conditional proxies, not surveyed Study B infrastructure.

| Input | Existing reference / proposed sensitivity |
|---|---|
| Supply | Idealized MV source at 1 pu, 60 Hz for first controlled screen; new MV route/connection not demonstrated |
| Physical nominal voltages | 7.621 kV L-N primary and 240/120 V secondary, per archived EPM records |
| Equivalent network | ROOT_FACTOR=3, sqrt(3) times 7.621/0.240 kV nominal model voltage, physical powers and ratings scaled by 3, physical losses divided by 3; no split-phase neutral or imbalance claim |
| Transformer | Initial 5 kVA, vk 3%, vkr 1.8%, i0 2.5%, iron loss 0.03 kW at physical 5 kVA (scales with rating) |
| Route/PF | 1/1.3/1.6 times geometric length once; 0.95/0.98/1 PF |
| Voltage | 0.95–1.05 pu principal, 0.97–1.03 optional; line/trafo loading <=100% |

Conductor proxy values copied from the original registry after the code doubles one-way R for the physical loop. X and current limit follow the original convention.

| Proxy | R loop ohm/km | X ohm/km | A |
|---|---:|---:|---:|
| AAC 1/0 | 1.312 | 0.160 | 180 |
| AAC 2 | 2.10 | 0.160 | 125 |
| AAC 4 | 3.30 | 0.160 | 95 |
| ACSR 2 | 2.24 | 0.160 | 110 |

Do not silently assign a conductor or price to hypothetical B routes. Use matched uniform conductor hypotheses first (including AAC 4 as the existing service proxy) and explicitly identify alternative trunk/service conductor allocation when justified. Preserve equal electrical assumptions across STAR and MST; investigate the impact of conductor changes before claiming a shorter route is cheaper. Upstream MV extension, terrain, route accessibility, right of way, grounding, protection, phase assignment and site suitability remain open. No northern transformer, no Site A or direct transformer-secondary ties. Existing recorded assets on 221-12 and 221-13 are contextual evidence, not proof of available new supply.

Next: qualify signed B1 replay and compare same-group/site tradeoffs; use no gross-only exclusion, retain matched and full populations. Build load-only critical-hour cases with frozen individual house profiles mapped to buses (including co-located supply/house). Test topology count, energy conservation, equivalent scaling, independently computed simple radial voltage drop, branch thermal/transformer loading, no zero-length branch, and solver failure accounting. Preserve matched STAR/MST comparison and use Study A controls when adding fixed equipment. No new AC or LP submitted in this checkpoint.
