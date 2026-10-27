# Conditional annual shared PV+BESS size and cost screening

This is an 8760-hour simulation using the original NASA-derived 2025 hourly PV signal and 20 synthetic stochastic household profiles. It is a **new annual energy/SOC screen**, not PyPSA v18 optimization, not full nodal pandapower, and not utility-verified connections. It does not overwrite the original models.

The six candidate territories contain 31 uniquely assigned-by-user properties. H01 and H02 are unassigned, H10 and H29 have alternative transformers. Even the three user-described definite assignments are not certified EPM customer connections.

Compare C (one shared installation) and K (two multi-home shared installations), matching total DC PV, usable battery energy, battery kW and AC inverter rating. K has two independent 5 kW inverters for a total of 10 kW. Original 5.22 kWp NASA PV AC-unclipped series is scaled by panel count and clipped at inverter rating. Batteries use 5.12 kWh nominal, 4.325 kWh usable, sqrt(0.95) one-way efficiency, and a myopic self-consumption heuristic. Neither architecture is guaranteed inverter/battery BMS compatibility or protective islanding hardware. The K energy results assume community netting at the same provisional LV PCC, without assuming confirmed conductor connectivity.

Sweep PV 0/12/24/32 × 435Wp, modules 0/4/8, battery power 0/5/10kW, central vs two group-level sites (where group counts support two multi-home clusters), and no-export vs 4.5kW export-policy sensitivities. Annual peak import and hours above 4.5kW are reported for context, but a 4.5kW proxy threshold is NOT an EPM regulatory approval or a nodal voltage check.

Costs use original historical HOMER quote from case1/wp1_v3/model.py, horizon 25 years, 6% discount, battery replacements at 20 years or earlier throughput limit, inverter replacement after 15 years, source USD0.29/kWh import and optional USD0.275/kWh export. Additional site costs USD0..1500, BOS 0..30% and annual O&M 2% are explicit unsourced scenario parameters. LV cables, protection, meters, permits, land, taxes, engineering and utility approvals are unpriced. Do not present illustrative costs as a finalized lifecycle quotation.

For transformer nodes 931076 (94022) and 923848 (92395), 5 kVA is archived EPM evidence. Other portal records list 3 or 5 kW, NOT nameplate kVA, so the table does not assert a transformer rating or physical house limit. No critical/deferrable load splits, no new transformers, no individual household PV+BESS primary architecture.

Run: python case1/studies/annual_shared_pvbess/annual_screen.py --outdir /tmp/annual_screen
The GitLab CI job computes the full table; commit its outputs only after verifying the CI results.
