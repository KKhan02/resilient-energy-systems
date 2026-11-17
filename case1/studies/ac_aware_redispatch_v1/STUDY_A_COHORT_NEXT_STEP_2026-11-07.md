# Study A: next verified work, zero-export base case

**Status:** A study execution aid, not completed simulations. Reuse original data, PyPSA, pandapower, saved annual checks and the existing `batch_archived_campaign.py`. **Only the cohort comparison remains the present priority**. Do not switch to Site A, new transformer layouts, or repeat inverter placement yet.

## Zero export is confirmed

In `case1/studies/pypsa_joint_optimization_v1/model.py`, `Settings.export_policy='zero'` is the default and the `GRID_EXPORT` model component exists only under the separate `reference_credit` policy. The archived candidate runner `run_archived_energy.py` expressly rejects a source whose export policy is not `zero`; the fixed-hardware solver asserts zero exports, rather than relying on a report caption.

The two uploaded **12-house, 106039, head-connected, PF0.98, 5kVA reference** trajectories each contain 8,760 timestamps with strictly zero `grid_export_kw`:

| Candidate | 54 PV / 9 battery / 20kVA | 56 PV / 10 battery / 20kVA |
|:--|--:|--:|
| Annual PV available, DC kWh | 28,524.173 | 29,580.624 |
| Annual PV generated, DC kWh | 22,530.855 | 23,288.609 |
| PV curtailed, DC kWh | 5,993.318 | 6,292.015 |
| PV curtailed as % of available | 21.01% | 21.27% |
| Battery charged, DC kWh | 12,367.257 | 13,081.446 |
| Grid import, AC kWh | 1,959.132 | 1,273.190 |
| Grid export, AC kWh | **0** | **0** |

PV is available to meet local demand and to charge battery, subject to DC, inverter and battery constraints. Residual energy is curtailed. **Do not sum DC and AC flows as though they were at the same bus.** More battery and PV improve annual self-sufficiency, but do not necessarily remove worst evening demand at minimum battery SOC.

Note that source PyPSA dispatch optimizes economic operation, with additional constraints and sometimes self-sufficiency targets. Zero export is a constraint, **not a guarantee** that the entire available solar production can be stored or that 100% self-sufficiency will be achieved.

## Existing Study A evidence: do not rerun

| GIS-backed source cohort | Physical transformer | Archived useful annual evidence | Action |
|:--|:--|:--|:--|
| 7-house | 94022, 5kVA | 26-panel/5-battery/7.6kVA 2025 manufacturer-SOC baseline had **4 of 8760** failures under the historical **0.97–1.03pu** strict band; source `outputs/seven_manufacturer_annual_ac_01/annual_ac_summary.json`. Saved revised full-year AC `outputs/seven_annual_feedback_ac_check_01/annual_ac_summary.json` has **8760/8760** conditional pass under the same strict band. | Reuse both as distinct trajectories; analyze P redispatch and line-length/PF robustness, no baseline recompute. |
| 9-house | **same 94022**, not a separate transformer | H01 and H02 added to the 7-house group as *provisional* modelled connections; no verified annual AC for the three source-selected tier-A eligible hardware candidates in uploaded audit | **Current priority:** manufacturer SOC, annual baseline AC, then sensitivities. |
| 10-house | **same 94022** | Historical head/middle 40-hour GIS critical-hour study is based on ten provisional houses and cannot be compared as a 9-house annual trajectory. | Evidence only; do not relabel as the 9-house group. |
| 12-house | 106039, **5kVA selected model rating** | Annual AC 41/8/12 head reference; two uploaded 54/9/20 and 56/10/20 both 8760/8760 pass on 0.95–1.05 pu main screen; strict 0.97–1.03 has 31 and 23 undervoltage hours for uploaded two | Reuse; pursue key sensitivity once the 9-house base is clear. |

The 9-house historical `H01/H02` **demand-variant** labels used by some energy studies must never be confused with mapped georeferenced `H01/H02` houses, whose EPM link is still a modelling assumption.

## 9-house initial equipment checks

These three candidates are selected from the archived 5kVA historical Pareto anchors, not newly invented equipment. Their historical costs/SS are **energy-only prior to manufacturer-SOC and AC validation**.

| ID | Panels | Battery modules | Inverter kVA | Original annual cost USD | Original self-sufficiency | Reason selected |
|:--|--:|--:|--:|--:|--:|:--|
| `EC-3cc99d4429a15487a083` | 34 | 6 | 10 | 3,570.99 | 84.97% | Historical minimum-cost, ≥70 and ≥80% |
| `EC-b091c626114a2d74884f` | 40 | 7 | 12 | 3,684.54 | 92.99% | Lowest cost reaching ≥90% |
| `EC-9df8c68834f7c7f6faa3` | 41 | 8 | 12 | 3,749.12 | 95.28% | Lowest cost reaching ≥95% |

The fourth 9-house maximum-SS anchor (`EC-ff3278f35c4ce1466cdd`, 82 panels, 7 batteries, 24kVA) was marked **not eligible for the existing fixed-hardware GIS runner** in the source audit. Retain the candidate in the source pool; do not silently run or delete it.

## How to execute the first missing annual cohort check

Extract `run_study_a_nine_reference.cmd` beside this file, under `case1/studies/ac_aware_redispatch_v1/` in the existing checkout.

From the **repository root** in Windows CMD / Anaconda Prompt:

```bat
call case1\studies\ac_aware_redispatch_v1\run_study_a_nine_reference.cmd preview energy
call case1\studies\ac_aware_redispatch_v1\run_study_a_nine_reference.cmd run energy
call case1\studies\ac_aware_redispatch_v1\run_study_a_nine_reference.cmd preview ac
call case1\studies\ac_aware_redispatch_v1\run_study_a_nine_reference.cmd run ac
```

The **preview** commands do not simulate anything. `run energy` starts the existing 8760-hour fixed-hardware manufacturer-SOC solves for only these three nine-house candidates, checking existing completed output hashes before skipping work. `run ac` starts the existing annual AC solver on already-available energy trajectories. It uses the **same original source output directories** as the previous annual candidate campaign. If any job errors, the wrapper stops; it does not declare missing cases feasible. The historical 6840 investment tasks never run again.

Annual AC reference conditions: `PF 0.98`, line/service factor `1.0`, selected EPM 94022 LV cohort, main `0.95–1.05 pu` voltage screen, 100% thermal screen, zero grid export, 20% minimum physical SOC and nighttime Q disabled. These do not establish actual field wiring or EPM connection approval.

### After these three runs

1. Compare 7, 9 and 12 household reference equipment, **without treating 7/9/12 as one physical network**. Compare annual cost per house, import and self-sufficiency, voltage minimum and voltage violation hours, worst transformer/line loading, losses, manufacturer-SOC and resulting AC redispatch if needed.
2. Select meaningful frontier designs or boundary cases and run the previously agreed **PF1.00, 0.98, 0.95** and **service length 1.0, 1.3, 1.6** full-year AC scenarios, without presuming voltage robustness because PF0.98 x1.0 passed. The existing runner supports `--scenario-set principal_nine`, but only run the computationally larger scenario set for relevant candidate(s) after reviewing baseline outcomes.
3. Preserve the original geographic EPM GIS conductor data and scale only the **explicit provisional service/route-length hypotheses**, as coded; document what is actually lengthened. Do not silently multiply measured GIS conductor lengths or change entire topology.
4. If voltage, thermal or SOC-constrained dispatch prevents feasibility, reuse existing `run_annual_feedback.py` P redispatch and Q controller, then assess marginal hardware/cost adjustments. Avoid repeating full-year 40-hour placement screens unless a specific remaining uncertainty warrants it.
5. No changes to Study B/C order, no northern transformer and no new project folders outside the checked-out repository.
