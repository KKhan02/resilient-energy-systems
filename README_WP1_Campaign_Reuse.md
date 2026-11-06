# SEEDExchange WP1, v1.8: reuse the complete historical annual optimization

**Purpose:** Advance the whole existing 6,840-task campaign into **manufacturer-SOC and full-year AC validation**. This does **not** rerun `full_study.py`, replace the MILP, invent GIS connections, or redefine the PV/BESS/inverter sizing objectives.

## 1. What is already complete, from GitLab

Canonical file: `case1/studies/pypsa_joint_optimization_v1/outputs/full_study/complete_study_results.csv` in the **private** `KKhan02/resilient-energy-systems` repository, as inspected at commit `e377e21d26db4bffd7a164d1257d5860bb01f325`.

- **6,840** discrete PyPSA/MILP tasks, each with an 8,760-hour energy optimization; **6,820** reported optimal for the *energy-only* constraints, **20** infeasible. No AC feeder verification was included in this campaign.
- Household-study variants: 5, 6, 7, 8-H01, 8-H02, 9, 10, 11, 12, 13, 14 and 15 customers. The cases outside the explicitly mapped 7/9/12 provisional territories are **synthetic household-count studies**.
- Transformer rating scenarios: 5, 10, 15, 20 and 25 kVA. For transformer 106039 the **5 kVA is hypothetical**; larger ratings are also sensitivities, not known physical nameplates.
- Original tasks by type: **4,980** exact PV-panel economic, **1,020** fixed battery-module economic, **480** minimum self-sufficiency and **360** budget-constrained objectives. Preserve every objective and infeasible task.
- The saved original equipment choices number approximately **6,339 unique tuples** when case, transformer kVA, exact panel count, module count, battery power (six-decimal kW precision) and inverter kVA are distinguished. This is a *deduplicated study queue*, not 6,339 proven physical configurations.
- Of the 5 kVA territorial anchor studies for 7, 9 and 12 homes: **338** original optimal task rows and **312** distinct equipment tuples. The prior six-design shortlist is a **pilot only**. It does not replace the full archive.
- In the full original results, **1,480** optimal task records exceed the conservative `44.8 V × 50 A` DC continuous-current proxy per Deye SE-G5.1 module. These are **manufacturer/electrical-screen review flags**, not independently verified hardware failures. Preserve them; do not automatically discard them from the historical results.
- The old campaign optimized a full-year cyclic SOC but not the later 20% physical SOC floor. Only 3 archived reference designs have full hourly dispatch CSVs in GitLab. Fixed-hardware reoptimization creates needed *new* hourly trajectories without repeating historical capacity search.

Historical objective-specific dispatch is **not** preserved in the aggregate CSV for every task. Reoptimizing a unique hardware tuple economically must not be represented as reproducing an earlier epsilon/budget-optimal dispatch. The archive preserves the objective records separately.

## 2. Evidence gates, applied to the entire archive

1. **Read and index all 6,840 rows.** Check the run plan, study manifest, input SHA and exact unique solver task keys. Retain failed/energy-infeasible cases.
2. **Deduplicate fixed hardware only for subsequent work.** Keep each archived solver task, objective and cost in `archived_task_registry.csv`, including its link to an equipment ID. The `all_distinct_equipment_candidates.csv` is the full queue of distinct solutions, *not* a new optimization.
3. **Map physical evidence.** For presently supportable AC GIS proxies, use only the established 7-, 9- and 12-house territories. All other original household count cases stay in the catalogue, flagged `GIS_MAPPING_REQUIRED`. Larger hypothetical transformer ratings are permitted as explicitly labeled *sensitivity scenarios*, not installed-asset claims.
4. **Manufacturer checks.** Preserve candidates with unresolved continuous battery current and inverter compatibility, including zero-PV/no-inverter grid-only baselines requiring a different AC path. These need hardware verification or an explicit grid-only feeder test. No silent selection or erasure.
5. **Generate new full-year dispatch where absent.** Use the *existing* `fixed_hardware.solve_fixed` PyPSA method with exactly the **saved** panels/modules/DC kW/inverter kVA, same synthetic 2025 profiles, 20% physical SOC floor and original annual cyclic energy balances. **Do not call `full_study.py` and do not solve equipment sizing again.** A previously completed, identical manufacturer-SOC trajectory can be imported and cryptographically verified instead.
6. **Recheck annual AC.** Use existing `run_coordinated_q.run_hour`, EPM GIS, conservative no-night Q and voltage **0.95–1.05 pu**. Every result is an **8,760-hour** replay. For each already usable hardware tuple and applicable assumptions, run the full nine PF × service-factor matrix (.98/.95/.90 × 1/1.3/1.6). Critical-hour shortcuts are **not** part of this pipeline.
7. **Classify, never infer.** A candidate is new AC-feasible *only* if the complete signed annual AC CSV has 8,760 ordered rows, convergence and no voltage or transformer/line failures. Compare the national/EPM magnitude references and former 0.97 pu sensitivity separately. Failed conditions stay visible. Only after the complete annual phase, consider AC-feedback redispatch where needed, maintaining entire-year SOC.
8. **Rank after AC.** Output cost vs self-sufficiency among *evaluated and feasible* candidates. Do not describe the resulting nondominated sample as a complete global Pareto frontier until every eligible and physically mapped design has actually been assessed. No loss/cost corrections are claimed until implemented.

### Important scope limits

The campaign's 5–15-house studies are **not** twelve validated geographical networks. Existing AC code has credible provisional transformer-house groups for **7, 9 and 12** only. Expanding GIS to the other household counts requires explicit attachments, phase assignment and service routing, not automatic expansion from synthetic profile indices. All existing historical results remain part of the total analytical sweep.

## 3. Installation

Unzip v1.8 into the local root of the existing private repository. These are **additive files** under `case1/studies/ac_aware_redispatch_v1/`. They require the previously installed v1.1–v1.7 Python modules, PyPSA/HiGHS and pandapower available in the same conda environment used for the successful 12-house run. No historical output files are replaced. No GitLab changes or CI jobs occur through this package.

All commands below run from the repository root in PowerShell or Windows Command Prompt. Use a **new** output directory for each analysis snapshot.

### A. Audit the WHOLE original campaign, without a solver

```powershell
python case1/studies/ac_aware_redispatch_v1/audit_archived_campaign.py --repo-root . --outdir case1/studies/ac_aware_redispatch_v1/outputs/campaign_reuse_index_v18_01
```

Outputs:

- `archived_task_registry.csv` (6,840 records, **including 20 infeasible**)
- `all_distinct_equipment_candidates.csv` (all unique hardware combinations with hardware/GIS review flags)
- `original_campaign_by_case_and_rating.csv` (60 household-count/rating groups)
- `campaign_reuse_manifest.json` with SHA256 links to the **existing** source files

**This command should be run first.** It does zero PyPSA or pandapower calculations.

### B. Dry-run the complete work queue

The work queue does **not** default to six candidates. Without `--case`, it includes every compatible archived design with an available provisional GIS household group. Without `--kva`, it includes all archived transformer-rating sensitivities, clearly labelled hypothetical. The command below previews the 12-house, hypothetical 5 kVA anchor first:

```powershell
python case1/studies/ac_aware_redispatch_v1/batch_archived_campaign.py --stage energy --repo-root . --plan-dir case1/studies/ac_aware_redispatch_v1/outputs/campaign_reuse_index_v18_01 --energy-root case1/studies/ac_aware_redispatch_v1/outputs/campaign_manufacturer_01 --ac-root case1/studies/ac_aware_redispatch_v1/outputs/campaign_AC_01 --case twelve --kva 5
```

No calculations run without `--execute`. A command with `--max-candidates 1 --execute` runs only one **new 8,760-hour** full-year *fixed-hardware* SOC solve, useful for verifying the batch interface. Omitting `--max-candidates` includes all eligible candidates in the chosen scope. Add `--continue-on-error` to log failed candidates and continue without suppressing them.

### C. REUSE the ALREADY COMPLETE 12-house baseline, without solving again

The accepted reference equipment is **41 panels, 8 modules, 12 kW battery, 12 kVA inverter**. Find its `equipment_id` in the newly generated index:

```powershell
python -c "import pandas as pd; x=pd.read_csv('case1/studies/ac_aware_redispatch_v1/outputs/campaign_reuse_index_v18_01/all_distinct_equipment_candidates.csv'); print(x.loc[(x.case=='12_homes') & (x.assumed_transformer_kva==5) & (x.pv_panels==41) & (x.battery_modules==8) & (abs(x.battery_power_dc_kw-12)<1e-5) & (x.inverter_kva==12), ['equipment_id','historical_min_annual_total_usd']].to_string(index=False))"
```

Replace `<EQUIPMENT_ID>` below with the exact ID printed:

```powershell
python case1/studies/ac_aware_redispatch_v1/run_archived_energy.py --repo-root . --plan-dir case1/studies/ac_aware_redispatch_v1/outputs/campaign_reuse_index_v18_01 --candidate-id <EQUIPMENT_ID> --out-root case1/studies/ac_aware_redispatch_v1/outputs/campaign_manufacturer_01 --reuse-existing-baseline case1/studies/ac_aware_redispatch_v1/outputs/twelve_manufacturer_01
```

It verifies full-year profile, fixed hardware, 20% floor, cyclic SOC, no ENS and source SHA. It copies the already calculated CSV into the new, indexed evidence folder. It does **not** call the optimizer.

Reuse the corresponding completed **0.95–1.05 pu full-year AC** output:

```powershell
python case1/studies/ac_aware_redispatch_v1/validate_archived_candidate_ac.py --repo-root . --pilot-dir case1/studies/ac_aware_redispatch_v1/outputs/campaign_manufacturer_01/<EQUIPMENT_ID> --outdir case1/studies/ac_aware_redispatch_v1/outputs/campaign_AC_01/<EQUIPMENT_ID>/pf_0.98_service_1.00 --load-pf 0.98 --service-factor 1.0 --reuse-existing-ac case1/studies/ac_aware_redispatch_v1/outputs/twelve_ac_full_02
```

This import refuses changed voltage-band or Q assumptions, missing complete 8,760h data, changed hardware/trajectory or mismatched previous pilot hash. After successful import, the batch AC runner recognizes this completed job and does not repeat the original AC calculation.

### D. Execute new annual fixes where results are genuinely missing

For **all compatible 12-house 5 kVA designs** (not six):

```powershell
python case1/studies/ac_aware_redispatch_v1/batch_archived_campaign.py --stage energy --repo-root . --plan-dir case1/studies/ac_aware_redispatch_v1/outputs/campaign_reuse_index_v18_01 --energy-root case1/studies/ac_aware_redispatch_v1/outputs/campaign_manufacturer_01 --ac-root case1/studies/ac_aware_redispatch_v1/outputs/campaign_AC_01 --case twelve --kva 5 --execute --continue-on-error
```

Then all **nine full-year AC scenarios per completed candidate**:

```powershell
python case1/studies/ac_aware_redispatch_v1/batch_archived_campaign.py --stage ac --repo-root . --plan-dir case1/studies/ac_aware_redispatch_v1/outputs/campaign_reuse_index_v18_01 --energy-root case1/studies/ac_aware_redispatch_v1/outputs/campaign_manufacturer_01 --ac-root case1/studies/ac_aware_redispatch_v1/outputs/campaign_AC_01 --case twelve --kva 5 --scenario-set nine --execute --continue-on-error
```

Both commands check completed output first. Annual AC saves every hour to CSV, plus a `ac_checkpoint.json` signature every 250 hours. Rerun the same AC command with the same inputs to resume incomplete runs or verify completed runs. Failed cases are logged and remain visible.

To cover **all GIS-supported cases**, omit `--case` and `--kva`; these additional transformer ratings are *research nameplate scenarios* and **must not be reported as actual EPM hardware**. The full archive of 12 household-count studies remains indexed, but cases without valid GIS assignments cannot receive an AC verdict yet.

### E. Collate all evaluated candidates, without inventing passes

```powershell
python case1/studies/ac_aware_redispatch_v1/collate_archived_campaign.py --plan-dir case1/studies/ac_aware_redispatch_v1/outputs/campaign_reuse_index_v18_01 --energy-root case1/studies/ac_aware_redispatch_v1/outputs/campaign_manufacturer_01 --ac-root case1/studies/ac_aware_redispatch_v1/outputs/campaign_AC_01 --outdir case1/studies/ac_aware_redispatch_v1/outputs/campaign_collated_v18_01 --scenario-set nine
```

- `all_equipment_with_new_validation_status.csv`: **every** archived distinct hardware tuple, whether tested, failed, blocked or awaiting GIS input.
- `annual_AC_scenario_ledger.csv`: source-aware full-year AC record for each candidate and each of nine sensitivity conditions.
- `validated_conditional_cost_self_sufficiency_comparison.csv`: new manufacturer-SOC economics for **actually** verified combinations, not a full Pareto frontier until coverage is complete.

## 4. Scientific limitations and next development

1. Full-year energy optimization uses perfect foresight, the archived synthetic profiles, and a conditional transformer P/Q approximation. **Do not redo the original joint MILP** merely to produce graphs or a six-design comparison.
2. The v1.8 wrapper reuses the historical fixed-hardware *economic* objective. New SOC and AC constraints can change economics and make archived equipment infeasible; those differences must be reported as **new corrections**, not erased from the original study.
3. Manufacturer continuous current proxy must be checked against actual SE-G5.1 bank wiring, operating voltage, BMS, inverter battery port and configuration. Rows that fail the proxy stay in the archive and get a review flag, not an unsupported claim of physical impossibility.
4. The inverter's ability to generate reactive power at night remains unverified and conservatively disabled. Q controller operation and its energy/loss consequences are imperfect; AC network losses are presently **not charged to the PyPSA energy balance or objective**.
5. All full-year runs use the proposed engineering target 0.95–1.05 pu, not an alleged Colombian regulatory limit. National/EPM voltage magnitude comparisons are additional interpretations, not legal duration-compliance claims.
6. The existing GIS representation is balanced, household-to-transformer and phase attachments are provisional, and all 106039 kVA ratings in this campaign are not verified EPM nameplates. AC outcomes must be labelled conditional.
7. Where reference AC fails, use **the existing** manufacturer-SOC constrained annual P-feedback process after updating it to accept arbitrary indexed hardware and 0.95–1.05 pu limits. This remains **future work**, not implemented by this package. Do not label a failed configuration as optimized-away.
8. For the complete physical hosting study, ground each additional household and service connection first. Archived 5–15-house cases are a useful synthetic hosting envelope, not certified mapped feeders.

## 5. Tests

```powershell
python -m pytest -q case1/studies/ac_aware_redispatch_v1/tests/test_archived_campaign_reuse_v18.py
```

No production GitLab files, historical source files or simulation outputs are modified by the scripts. The package includes **no new physics model**.
