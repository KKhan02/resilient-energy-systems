# SEEDExchange San Rafael Case 1
## Approved next-phase analysis and reporting specification
**Date:** 27 October 2026  
**Repository:** https://gitlab.com/KKhan02/resilient-energy-systems  
**Baseline HEAD at review:** `1fdf097aee955dfdca091f08a863b47888eca38e`  
**Status:** Requirements and source audit only. This file contains **no newly executed PV+BESS or AC power-flow simulations**. Intended for manual upload, review and local implementation; do not automatically trigger CI to add this document.

## 1. Decision: current electrical associations first, expansion second

All 35 H01–H35 labels remain visible in the geographic and electrical association diagram. An association is **candidate evidence**, not a utility-certified service.

| EPM electrical node | Transformer asset number | Candidate existing properties | Rating evidence |
|---|---|---:|---|
| 931076 | 94022 | 7: H03,H06,H26,H27,H28,H34,H35 | Earlier EPM record: 5 kVA |
| 923494 | 106039 | 12: H11,H13,H16–H25 | Portal: 5 **kW**, actual kVA unverified |
| 923848 | 92395 | 4: H30–H33 | Earlier EPM record: 5 kVA |
| 900607 | 85398 | 4: H09,H12,H14,H15 | Portal: 5 **kW**, actual kVA unverified |
| 823002 | 113699 | 3: H04,H05,H07 | Portal: 3 **kW**, actual kVA unverified |
| 241054 | 98380 | 1: H08 | Portal: 3 **kW**, actual kVA unverified |
| Northern transformer | asset/node identification unresolved | H01/H02 alternative | Earlier EPM information: 25 kVA, other existing customer loads unknown |

Alternative existing-house supply is unresolved for H01/H02 (94022 5 kVA **or** northern 25 kVA), H10 (923494/823002), and H29 (931076/923848). Explicitly examine, but never silently choose, alternatives. In particular test transformer **94022: seven, eight (H01 vs H02 separately), and nine (H01+H02)** candidates while keeping existing seven intact. Also compare H01/H02 on the northern 25 kVA transformer, **without presuming its unused capacity**, since its other loads are unknown. A 5 kVA assignment can be capacity-conservative but is not automatically the worst line-voltage arrangement, because line distance differs.

The northern transformer's separately documented position and transformer 94022's documented position must be retained independently. Never invent missing transformer GPS, actual energised LV routes, additional service wires or unpriced transformers.

## 2. Mandatory modelling order

1. **Electrical evidence diagram:** distinguish known transformer positions, unknown poles, candidate house-to-transformer associations, actual source-verified LV lines (if available), and schematic/assumed line paths. Diagram must not falsely imply real conductor routing.
2. **Current-load baseline:** for each existing candidate transformer territory, run no-DER load scenarios; report hourly/peak apparent transformer loading, min/max LV voltage, line loading, losses and loss-of-load/ENS. Use original v5 cable impedances for applicable reference studies. For 106039, test explicitly hypothetical 5/10/15 kVA sensitivities until actual rating verified.
3. **Current customers with PV+BESS:** retain current candidate houses and jointly size PV kWp, BESS usable kWh, BESS kW, inverter AC kVA and control. First parameter sweeps, then joint optimization with separate cost, self-sufficiency and hosted-household objectives. Constrain apparent-power kVA with Q, not merely active kW; record unserved load separately from self-sufficiency.
4. **Annual PyPSA / DC-coupled dispatch linked to pandapower:** one canonical hourly dispatch feeds geographically assigned nodal power-flow loads/injections. Compare matched PV/BESS architectures only as a secondary siting sensitivity. Run critical events first then annual time-series or validated representative subsets. Physical violations feed back into sizing. Do not equate the energy-only screen's `NOT_SIMULATED` AC status with verification.
5. **Incremental hosting and reassignment:** retain all existing customers first. Add houses one at a time or in explicitly chosen sensitivity sets without exceeding transformer/voltage/cable limits or reducing the agreed self-sufficiency floor. Then examine physical LV reconnection of a boundary house to a neighboring existing transformer, with reconnection cost, wire-route constraints and EPM permission. Never double count properties or treat geographically near as electrically connected.
6. **Community-scale portfolio and 25-year cost:** optimize investment among physically separate existing territories subject to total costs, service levels, transformer limits and self-sufficiency; distinguish energy-community billing/virtual allocation from literal electrical sharing. Include cable, protection, meters, interconnection, civil works, permits, PV/BESS/inverter, replacements and O&M; use uncertainty ranges for missing costs, not zero.

## 3. Baseline numeric reconciliation required before reporting

The 27 October `annual_shared_pvbess/outputs/annual_scenarios.csv` contains **386** annual energy-only heuristic runs. These are **not full PyPSA optimization nor annual pandapower**.

For **24 × 435 W = 10.44 kWp**, **4 batteries = 17.3 kWh usable**, **battery power 5 kW**, **10 kW inverter total**, zero export and architecture C:

| Territory | Homes | Demand kWh/year | Grid import kWh/year | `1 − grid import/demand` |
|---|---:|---:|---:|---:|
| 931076 / 94022 | 7 | 13,286 | 2,728.696 | 79.462% |
| 923494 / 106039 | 12 | 22,776 | 11,125.524 | 51.152% |

These are **different** territories with different demands but matched equipment; 2,728.696 kWh should never be paired with the twelve-house 51.152% claim.

**Crucial comparability issue from the attached independent review:** `case1/studies/annual_shared_pvbess/annual_screen.py` is a separate (fourth) energy-dispatch implementation. It treats battery AC/DC losses differently from the DC-coupled `case1/wp1_v3/model.py` core, and checks a **4.5 kW active-power proxy**, not `sqrt(P²+Q²)` ≤ an established kVA rating. The hardcoded battery and PV conversion, cost routines and energy conservation must be reconciled before treating these as validated engineering numbers. Never silently overwrite the source table: preserve existing runs as labeled prior-study provenance and publish revised results with new version/manifest.

The attached review also flags a saved older `case1/results/` frozen sweep as stale after changing to pvlib solar. It must not be used as the final monthly or Pareto baseline without a reproducible rerun. The review confirms that GitLab CI *does* exist and had succeeded on HEAD, but passing unit tests has not established that the four dispatch implementations are equivalent or that the grid model is independently AC-validated.

## 4. Required annual (8760 h) model output, same source per scenario

Use timestamp **2025 local solar time (LST)** for NASA inputs, document local-time handling and weather/model conversion. Preserve one **chronological battery SOC trajectory** for the entire year. No resetting SOC at the start of a plotted day, week or month. Record initial/terminal SOC, and enforce/test cyclic closure on representative annual design comparison so that initially stored energy is not treated as free energy.

**Full hourly exports (CSV):**

`timestamp_lst, scenario_id, transformer_node, house_ids, demand_requested_kw, demand_served_kw, ens_kw, ghi_wh_m2, poa_wh_m2_if_computed, pv_dc_kw, pv_ac_kw, battery_charge_dc_kw, battery_discharge_dc_kw, soc_usable_kwh, soc_pct, grid_import_kw, grid_export_kw, curtailment_kw, pcc_p_kw, pcc_q_kvar, pcc_s_kva, lv_min_pu, lv_max_pu, worst_line_loading_pct, transformer_loading_pct, lv_losses_kw`

Do not fabricate values for missing AC-network metrics. Write null plus `NOT_SIMULATED` status until pandapower actually runs.

**All resolutions derive from that same annual trajectory:**

- **Day:** hourly demand, observed radiation (GHI), PV DC/AC generation, charging and discharging, battery SOC, grid import/export, curtailment and, when available, worst bus voltage and transformer kVA. Provide at least a representative day, highest-demand day and lowest-solar/high-demand day selected *from the simulated series*.
- **Week:** seven-day 168-hour trajectories. Include representative and stressed periods, with continuous SOC carried over from preceding hours.
- **Month:** 12 calendar months, each with demand kWh, PV available/used/curtailed kWh, charged/discharged kWh, imports/exports kWh, ENS kWh, self-sufficiency %, production-to-demand ratio %, transformer/voltage violations and SOC start/end. Show monthly stacked energy charts, monthly self-sufficiency, grid-import/export plot, and radiation/PV seasonal plot.
- **Year:** 8760-point power and SOC data, daily aggregation for a year overview, monthly totals, energy conservation table, annual self-sufficiency, supply adequacy and violations. Report detailed event windows rather than making an unreadable 8760-hour line plot the only figure.

For 1-h intervals, hourly kW × 1 h becomes kWh. NASA `ALLSKY_SFC_SW_DWN` is hourly Wh/m². Sum to daily/monthly kWh/m² using /1000. Do not label irradiance/irradiation and PV AC generation interchangeably; convert NASA GHI to actual plane-of-array and module/inverter output using the pinned canonical pvlib method.

**Monthly self-sufficiency:** for each calendar month `100 × (1 − import_kWh / requested_load_kWh)` when ENS=0; also report `1 − imports/served` explicitly as a distinct metric when ENS>0. **Fully grid-independent month** means `grid_import_kWh ≈ 0` **and** `ENS = 0`, not merely >80% self-sufficiency. Use a declared numerical tolerance, and distinguish autonomous grid-outage operation from ordinary grid-connected net-zero annual energy.

## 5. Reproducibility and accuracy gates

- Reuse a **single DC-coupled dispatch core**; reconcile hourly annual_screen with `wp1_v3/model.py`/PyPSA and the inverter and battery component assumptions. No fifth independent dispatch engine for plotting.
- Battery one-way and inverter efficiency must agree with the selected DC-coupled physical path. No simultaneous charge and discharge, SOC bound excursions, double-counted losses or surplus creation.
- Every hour: AC/DC conservation residuals below declared tolerance, actual PCC apparent `sqrt(P²+Q²)` obeys nameplate/load-limit assumptions, no free initial/terminal stored energy, correctly accounted curtailed solar and unserved load.
- Verify input hashes and full 8760 timestamps; data gaps/timezone issues are errors, not silently interpolated.
- Test PV-only, zero-PV, BESS-only (no free annual energy), no-DER, zero-export, unrestricted-export, seven-house and twelve-house reference scenarios; reconcile original October annual kWh, identify and explain any model differences.
- AC network acceptance requires actual pandapower voltage, thermal loading and losses across supported source assumptions; a `PCC_screened` label that repeats a limit already enforced inside dispatch is **not independent validation**.
- Make cost and Pareto eligibility checks consistent across CSVs, charts and reports; treat stale frozen outputs separately.

## 6. Mandatory publication artifacts

Per territory and scenario class, publish `figures/` **PNG and SVG** paired with underlying hourly CSV, monthly CSV, annual summary, a provenance/assumptions manifest and exact regenerating script. Include map/electrical association diagram, baseline voltage/loading curves, daily/weekly power/SOC profiles, twelve-month energy balance and self-sufficiency, annual daily heatmaps, PV-kWp × BESS-kWh × battery-kW parameter sweep, cost/SS/hosting Pareto fronts, and rated-transformer sensitivity/transfer scenarios. Explain every plot as *measured, sourced, conditional model, or electrical-validated*.

## 7. GitLab workflow without a local CLI until final verification

- GitLab **Web IDE** can edit multiple code/Markdown files, create branches and merge requests. It **cannot execute Python** or run pandapower/PyPSA itself.
- Preserve changes locally where practical and arrange one coherent batch for manual upload. Alternatively use a single Web IDE feature branch, with carefully reviewed commits and CI skipped for **documentation-only commits** if policy allows. A normal Web IDE commit can otherwise trigger CI. Never skip substantive model verification at final review.
- Execute a local terminal run once near finalization, **or** run one intentionally consolidated GitLab CI pipeline that executes the full pinned environment, regression suite, canonical full-year simulations and figure generation, and saves downloadable pipeline artifacts. This is code execution, even though no local CLI is required.
- Keep figures and numerical artifacts reproducible. Use one final verification pipeline after combined changes, not one for each minor edit. Keep raw/derived data under versioned filenames and never overwrite historical outputs without provenance.

**Do not claim this document implements or validates any simulation.** It is a controlled handoff requirements artifact, based on the existing GitLab records and 27 October reviewer observations.
