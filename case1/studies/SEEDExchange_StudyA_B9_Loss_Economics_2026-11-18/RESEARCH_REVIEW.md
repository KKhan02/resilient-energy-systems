# Study A1 106039: signed AC losses and battery economics

**Independent audit:** 18 November 2026. **Provenance:** 18 signed 2025 AC-corrected nine-battery annual scenarios from `StudyA_A1_106039_B9_FullAnnual_AC_Overlay_v1/`, 18 verified 2025 eight-battery reference AC annual cases plus their 108 changed-hour AC records from `StudyA_A1_106039_Redispatch_Trial_v1/`, and the existing eight-design fixed-hardware energy-cost frontier. Source 8-battery corrections and new B9 corrections both pass all nine PF × feeder-length cases under the proposed balanced A1 106039 feeder.

## Electrical and energy comparison

Both modelled hardware families have the **same 11 households** (20,878 kWh annual demand), same PV modules/power class within the pair, same modelling year and nine network sensitivity factors. Comparing each eight-battery reference with its nine-battery counterpart does not change the household cohort or PV count.

| Metric | Higher-SS, 8 batteries | Higher-SS, 9 batteries | Minimum-cost, 8 batteries | Minimum-cost, 9 batteries |
|---|---:|---:|---:|---:|
| PV panels, 435 W each | 49 | 49 | 41 | 41 |
| Battery modules, 5.12 kWh nameplate each | 8 | 9 | 8 | 9 |
| Annual grid imports, kWh | 2,034.60 | 1,478.23 | 3,107.49 | 2,792.93 |
| Annual DC PV curtailment, kWh | 5,492.23 | 4,875.76 | 2,443.60 | 2,095.07 |
| Self-sufficiency of demand, % | 90.255 | 92.920 | 85.116 | 86.623 |
| Modelled annual equipment-plus-import cost, USD/a | 5,056.59 | 5,041.70 | 4,416.47 | 4,471.70 |
| Annual AC loss at PF 0.95, length x1.6, kWh | 431.181 | 427.130 | 440.363 | 438.056 |
| **Illustrative annual cost including loss adder at USD 0.29/kWh** | **5,181.64** | **5,165.57** | **4,544.17** | **4,598.73** |

**Conditional ninth-module marginal change at worst stress case:**
- `SS_REF → SS_B9`: annual imports down 556.368 kWh, DC curtailment down 616.475 kWh, AC losses down 4.050 kWh, and illustrative loss-adjusted cost down **USD 16.07/year**. Without the loss-adder assumption, the original cost difference was USD −14.89/year.
- `MC_REF → MC_B9`: annual imports down 314.556 kWh, DC curtailment down 348.539 kWh, AC losses down 2.307 kWh, but illustrative loss-adjusted cost **increases USD 54.56/year**. Without the loss-adder assumption, cost increased USD 55.23/year.

Across all nine PF/length combinations, the illustrative loss-adjusted annual cost difference is about USD −16.07/year for SS_B9 versus SS_REF, and USD +54.56/year for MC_B9 versus MC_REF. The loss effect is small compared with equipment and tariff uncertainty.

## Calculation and accounting

The existing energy model counts `annual_equipment_usd + 0.29 × grid_import_kwh`. The **separately labelled hypothetical loss-adder** is `0.29 × annual_AC_feeder_loss_kwh`, *only if community members must pay for the entire modelled technical losses at that same assumed retail price*. Total shown here is `annual_total_usd + loss_adder`. The use of a common loss price is a **sensitivity** and not a verified utility charge or Colombia network tariff.

The eight-battery reference loss totals are reconstructed at each matching factor as:

`reference_corrected_loss = signed_original_8760h_AC_loss + Σ(changed_hour_candidate_loss − changed_hour_original_loss)`

The nine-battery loss totals come from the independently verified full-year B9 overlay at the **same factor**. The historical source hourly record and all hardware-selection results remain immutable.

## Interpretation and next work

The ninth battery modestly reduces PV curtailment and increases annual self-sufficiency in both families. In the higher-self-sufficiency family, the original model indicates a small annual equipment-plus-energy benefit; adding this loss sensitivity does not change its sign. **This is not a field-ready least-cost selection or a robust investment advantage.** Actual converter/BESS BOS, feeder cables, labor, grid tariff, nameplate transformer rating, phase allocation, dispatch causality and replacement assumptions can overwhelm a USD 16/year difference.

A1 transformer 106039 is still assumed **5 kVA**. The corrected worst-case loading is **99.4318%**, only ~28.4 VA of assumed margin. This is not a safe field reserve. Dynamic controls and forecast errors have not been validated.

**Next fixed-hardware energy-only candidate:** `SS_P45_B9` (45 panels, nine batteries, 20 kVA inverter), already in the approved frontier hardware plan. It isolates simultaneous moderate PV reduction and added battery storage. Execute a separate annual PyPSA trial, then independently audit, and only then run AC validation and re-evaluate field hardware costs. Other planned variants `SS_B9_POWER16`, `MC_B10`, `MC_P33` remain exploratory. Do not rerun the historical 6,840-case MILP and do not alter the original 432 AC denominators (376 passing originally; 408 only under the hypothetical A0 overlay).

**Reproducibility:** `audit_b9_loss_economics.py` regenerates a signed 18-row pair comparison and 36-row design-by-factor sensitivity from the original GitLab checkout. It validates canonical-LF hashes of five source documents and the 18 signed reference-AC summaries. No new physics simulator is involved.
