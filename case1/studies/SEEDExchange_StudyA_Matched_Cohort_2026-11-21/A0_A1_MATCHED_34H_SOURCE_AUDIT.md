# Study A | source-matched A0 versus A1 34-house cohort audit

**Date:** 21 November 2026. **Evidence type:** read-only recombination of existing archived 2025 energy and 432 original/conditional network AC records on GitLab. This does not execute a new PyPSA model or pandapower solve, price a new cable, certify geographic reassignments, or claim physical protection acceptability.

## Same population and controlled source selection

The 2025 source preparation records 35 different household traces in 6 original EPM transformer territories. The historically modelled 5-network AC comparison uses **34 households**. The remaining **H08** belongs to support-only 98380, has no source-supported modeled LV AC feeder here, and is consistently excluded from BOTH alternatives. At each studied stage, annual demand is **64,532 kWh**. Distinct households are not duplicated.

| Transformer | A0 original households | A1 closest-transformer assignment | Electrical status |
| --- | --- | --- | --- |
| 106039 | H11, H13, H16, H17, H18, H19, H20, H21, H22, H23, H24, H25 | H11, H16, H17, H18, H19, H20, H21, H22, H23, H24, H25 | GIS mapped with provisional service taps |
| 94022 | H01, H02, H03, H06, H26, H27, H28, H29, H34, H35 | H01, H02, H26, H27, H28, H29, H34, H35 | GIS mapped with provisional service taps |
| 113699 | H04, H05, H07, H10 | H03, H04, H05, H06, H07, H10 | GIS mapped with provisional service taps |
| 85398 | H09, H12, H14, H15 | H09, H12, H13, H14, H15 | GIS mapped with provisional service taps |
| 92395 | H30, H31, H32, H33 | H30, H31, H32, H33 | One shared proposed STAR model, not existing mapped EPM LV |

The moves are only **H03 and H06, 94022 to 113699**, and **H13, 106039 to 85398**. Under A0, transformer 106039 has 12 houses, 94022 10, 113699 4, 85398 4, 92395 4. Under A1 these counts are 11,8,6,5,4. This is transformer-coordinate nearest assignment, not evidence of an accepted EPM service move.

**Variant-selection rule:** The 432-case portfolio includes TWO hardware families at A0 113699 and 85398, each four houses. Select `four_house_new` for the main A0 4-house study and `archived_reference` for the A1 5/6-house study. For 92395 use its **single A0 four_house_new STAR** source as the exact *shared unchanged* block for both A0 and A1. Do not count that physical population twice, switch families in one comparator without disclosure or incorrectly treat proposed STAR as existing utility lines. An alternate A0 four-house `archived_reference` sensitivity is preserved in the 432 archive; its SS90 costs/energy differ materially from the selected `four_house_new` variant.

## Five-territory 34-house source energy totals

These source hardware families represent architecture-specific sizes as household membership changes. They are a **matched population comparison**, not a matched total hardware-capacity experiment, and do not isolate geography alone.

| Assignment | Energy hardware tier | Total PV panels | Total BESS modules | Grid imports, kWh/year | PV curtailment, kWh DC/year | Equipment + grid USD/year |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| A0 | min_cost | 126 | 23 | 11039.93 | 8756.69 | 13783.15 |
| A0 | ss90 | 146 | 29 | 5394.20 | 13097.95 | 14529.81 |
| A1 | min_cost | 122 | 23 | 11665.83 | 7330.81 | 13750.91 |
| A1 | ss90 | 146 | 28 | 5821.75 | 13571.72 | 14647.02 |

At **minimum-cost source hardware**, A1 has `$-32.24` difference (A1 minus A0) in the modelled annual equipment + import total, imports **625.90 kWh/year more**, and curtailment **-1425.89 kWh DC/year difference. This is not a cable installation saving or a field assessment.

At **higher self-sufficiency source hardware**, A1 has **$117.21 per year more** equipment + imports, **427.55 kWh/year more imports**, and **473.77 more curtailed PV DC kWh/year**. These source tiers cannot identify the sole causal effect of geographic assignment because PV/BESS numbers differ and optimal hardware can change with group size.

The archived economic total has no verified EPM reconnection/cable/civil-work or protection CAPEX, no additional line-upgrade cost and no field-certified source transformer service margin. Source tariffs, ageing and model assumptions remain conditional.

## Same-source electrical feasibility comparison, original versus corrections

The existing 432-case portfolio has 12 source-case families, not 12 distinct populations. For an aligned **34-house / five-territory** cohort, choose one source case per transformer, tier, dispatch, PF and length. The derived `A0_A1_34H_AC_72_FACTOR_DISPATCH.csv` contains **72** consistent scenario-tiers-dispatch-factor rows, each referencing exactly five original source cases.

Each count is a **sum of violated territory-hours** across the five separate annual AC models. These are not the number of unique household hours, nor independent outage events.

| Assignment | Tier | PF / length | Original network violation territory-hours | After saved SOC redispatch on original model | Including *hypothetical* A0 94022 five-edge changes |
| --- | --- | --- | ---: | ---: | ---: |
| A0 | min_cost | 0.98 × 1.0 | 15 | 4 | 0 |
| A1 | min_cost | 0.98 × 1.0 | 2 | 0 | 0 |
| A0 | ss90 | 0.98 × 1.0 | 3 | 2 | 0 |
| A1 | ss90 | 0.98 × 1.0 | 1 | 0 | 0 |
| A0 | min_cost | 0.95 × 1.6 | 62 | 9 | 0 |
| A1 | min_cost | 0.95 × 1.6 | 9 | 0 | 0 |
| A0 | ss90 | 0.95 × 1.6 | 16 | 7 | 0 |
| A1 | ss90 | 0.95 × 1.6 | 2 | 0 | 0 |

The conditional A0 five-edge column is **not** a verified existing EPM network. The 94022 five-edge experiment assumes reduced resistance on five model branches, including **two provisional service edges for H01/H06**, with unknown actual conductor reactance, ampacity, route, protection and construction cost. Its 36 annual cases passed in the saved balanced-model audit but cannot be declared an available physical correction. Without that hypothetical work, A0 94022 retains AC violations after the saved SOC corrections; A1's saved source schedule corrections clear main model violations but retain very narrow network margins.

The unchanged common 92395 STAR candidate is also only a proposed layout with no confirmed mapped LV backbone. The separate 92395 MST option in the 432-case source is an additional *Study B* geometry stress case, not an extra A0 family that can be silently summed into the 34-house comparison.

**Loss accounting warning:** The original `annual_network_losses_kwh` field in the 432 source belongs to the pre-redispatch original circuit. The overlay fields do not reprice or reconstruct changed-hour loss sums for every corrected case, and the conditional five-edge network has its own source-specific loss outputs. Do not sum these unlike loss fields into a final A0-versus-A1 economic decision. First define a matched corrected-AC loss and the utility payment/ownership basis.

## Next scientific gate

1. Establish a **matched-total-hardware** A0 versus A1 controlled experiment, in addition to this source architecture-specific sizing comparison, to isolate the electrical effect of relocating household supply associations from an effect of changing the PV/BESS investment itself.
2. Validate the **H01/H06 and moved-house physical connection and phase assumptions**, conductor material/size and local quotations before upgrading the A0 94022 candidate. Retain the separate *original model* and *hypothetical five-edge* results side by side.
3. Compute corrected network losses on the same basis if economically material, without double counting grid purchases or rewriting previously signed originals.
4. Review the approved 7/9/12-house reference cohort evidence and associated 10/8-house GIS territories against this same-population table. Keep the 92395 STAR/MST comparison for Study B and Site A alternatives for Study C.
5. Reuse the 6,840 historical PyPSA jobs and existing GIS solver rather than adding an unsupported new community or physical line type.

Data sources:
- `case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/input_manifest_v6_2.json` (35 households and A0/A1 mapped membership).
- `case1/studies/SEEDExchange_StudyA_94022_AllNine_IndependentReview_2026-11-17/PV_BESS_22_DESIGN_UTILIZATION_PRIORITIES.csv` (22 candidate source energy groups).
- `case1/studies/SEEDExchange_StudyA_94022_AllNine_IndependentReview_2026-11-17/PORTFOLIO_432_ORIGINAL_PLUS_CONDITIONAL_FIVE_EDGE_OVERLAY.csv` (signed and conditional AC source cases).
- `case1/RESEARCH_SCOPE_APPROVED_2026-11-07.md` (approved methodology and experiment ordering).

**No new numerical solver runs occurred in this audit.** Hardware dimensions, real physical connections and costs have not been verified by a utility or survey.
