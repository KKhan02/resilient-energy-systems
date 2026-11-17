# Study A, A0 94022: branch-isolation interpretation and next engineering gate

**Date:** 16 November 2026. **Evidence status:** Independent audit of user-supplied 2,160-row targeted pandapower output. **Study A whole-portfolio status:** 376/432 annual AC scenario runs pass under the prior validated schedule overlays; the remaining 56 runs are A0 94022 (32) and the proposed A0 92395 MST (24). No feeder-augmentation proposal has been applied to the annual portfolio.

## 1. What was tested and validated

The uploaded archive contains nine distinct previously unresolved timestamps, four A0 94022 equipment/dispatch combinations, two PF/service-length factor pairs [(0.98,1.0),(0.95,1.6)] and 30 branch sensitivity options (2160 AC solves). All runs are `CONVERGED`, no rows or numeric values missing, no duplicate case-factor-hour-option keys, all flags reproduce the 0.95–1.05 pu and 100% transformer/line thresholds. Original reference passes 28/72 snapshots. The hypothesized half-resistance retrofit on **all** LV branches passes 72/72, but it is an artificial electrical sensitivity, **not** a selected cable grade, priced build, or annual network design.

| Resistance assumption | Passing / 72 | Worst low voltage (pu) | Peak transformer loading (%) |
| --- | ---: | ---: | ---: |
| Original reference | 28 | 0.937278 | 98.205 |
| All EPM GIS LV segments at R ×0.50 | 66 | 0.948797 | 97.474 |
| All assumed household service drops at R ×0.50 | 60 | 0.945587 | 97.785 |
| All LV segments at R ×0.50 | 72 | 0.956955 | 97.068 |

The 72 rows include 36 design/timestamp combinations per factor. Neither 72/72 nor 66/72 represent annual 8,760-hour validation or all nine PF/length combinations.

## 2. Which branches matter in the single-branch screen

**Ranking is marginal, not additive.** These values show the pass count when exactly one model branch is set to 50% of its previous resistance. Other branches are unchanged. The number of newly passing snapshots is relative to the same 28/72 original reference.

| Model branch | Source classification | Modelled length (m) | Passing / 72 | Additional passing |
| --- | --- | ---: | ---: | ---: |
| `line_007`, source FID 47053144 | **Assumed service drop** | 326.55 | 60 | 32 |
| `line_014`, source FID 47053086 | Mapped GIS LV section | 83.17 | 48 | 20 |
| `line_011`, source FID 47053070 | Mapped GIS LV section | 67.00 | 46 | 18 |
| `line_016`, source FID 47053100 | Mapped GIS LV section | 34.66 | 46 | 18 |
| `line_018`, source FID 47053118 | Mapped GIS LV section | 27.71 | 42 | 14 |
| `line_021`, source FID 47053143 | Mapped GIS LV section | 29.00 | 42 | 14 |
| `line_022`, source FID 47053144 | Mapped GIS LV section | 27.00 | 38 | 10 |
| `line_017`, source FID 47053100 | Mapped GIS LV section | 15.34 | 38 | 10 |

In the original network, H01 is the lowest-voltage household in every one of the 72 evaluated snapshots. `line_007` is the dominant modelled service connection by sensitivity, but the uploaded register does **not** record which household is connected at the far end of that line; verify this from the original pandapower bus-to-line mapping before asserting `line_007 = H01`. The new trial exports `MODEL_BRANCH_ENDPOINTS.csv` precisely for this check.

Some source GIS branches were split into near-zero 0.001 m pieces to accommodate assumed household taps. These are **model graph edges**, not independently field-verified cable assets. Modelled 244–327 m assumed service drops deserve particular review before specifying any upgrade. Their lengths reflect GIS-based nearest-tap assumptions rather than confirmed customer services.

## 3. Important residual events

- GIS-only half-resistance still fails **six** of 72 snapshot evaluations, all at PF 0.95 and ×1.6. At these cases, the voltage remains as low as 0.948797 pu, often with zero inverter output.
- Service-only half-resistance still fails **12** of 72. Its minimum is 0.945587 pu.
- One branch at a time fails to eliminate all 44 original failing snapshots. `line_007` alone achieves the largest reduction but leaves 12 failures.
- Thermal loading is not the limiting constraint in these tests; modelled peak transformer loading is less than 100% for every tested option, and line loading remains less than 12%.

## 4. Sparse bundle experiment

Prepare combinations of the highest-ranked single branches, and independently rerun both AC factors for every one of the nine hours in each of four annual schedules. The new test **must** preserve the original source manifests, reuse the original immutable 8760-hour schedules, and check reference/controls against the uploaded data. Affected modelled branch length is recorded to help prioritize engineering review, but is **not** a cable price or new route length. 

Evaluate 15 configurations (including the original, GIS-only, service-only, all-LV controls), giving 1,080 targeted AC results. Do not infer the result of combined branches by adding their individual improvements. The new solver must calculate each combined option.

If one or more sparse combinations pass 72/72, next determine exact model branch-to-house connection and actual EPM line material, caliber, service routes, installation permissions and cable costs. Re-run all nine PF/length combinations and the complete year only for a defensible cable/routing choice. Consider alternative feeder routing and location of shared injection in Study B. If no sparse solution passes, the correct next work is topology and verified connectivity evidence, not forcing an unrealistic resistance reduction.

## 5. Research safeguards

- All household EPM attachments and large service drops are provisional.
- `R×0.50` affects resistance only. Reactance, ampacity, transformer model, routing and cost remain untouched. Do not call it a genuine replacement conductor, or claim it meets Colombian grid code.
- No new PV generation is available during these late-evening events. PV curtailment and battery-sizing optimization remain separate studies, including annual cost, actual solar capture and later resilience reserves.
- Preserve A0 as the original-assignment counterfactual. It may be economically preferable to select A1 rather than retrofit A0. Compare the options only after credible price and topology evidence.
- Do not update the 432 annual results based on a nine-hour network what-if, and do not modify GitLab without explicit authorization.
