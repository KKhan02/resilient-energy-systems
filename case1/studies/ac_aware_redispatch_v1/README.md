> **UPDATE v1.1 (4 November 2026):** Fixes the seven-house GIS membership error. The provisional 94022 GIS territory has 10 candidate houses (including alternative H01/H02/H29), while the saved `seven` case contains only H03, H06, H26, H27, H28, H34, H35. A new `scenario_membership.py` explicitly selects 7/9/12 reference cohorts without modifying source GIS or assigning actual household meters. The SE-G5.1 model was recovered from the original HOMER XML, and a 20% physical SOC floor (80% manufacturer-recommended DoD) now applies to the new battery-constrained comparator. Read `HARDWARE_EVIDENCE_2026-11-04.md`. The device model's historical **10% SOC** input is not manufacturer guidance. The new pilot still requires full local PyPSA+pandapower execution.

# SEEDExchange WP1: AC-aware fixed-hardware redispatch pilot

**Status: prototype, not executed against full PyPSA/pandapower environment.** The pure-Python contract tests pass. No AC redispatch results, EPM installation verification, or new hosting limits are claimed.

## Existing research preserved

This versioned study imports and reuses:

- `case1/studies/pypsa_joint_optimization_v1/model.py`: original DC PV, shared inverter, battery charge/discharge links, cyclic `Store`, efficiency and cost function.
- `case1/studies/pypsa_joint_optimization_v1/run.py`: 2025 NASA PV and original fixed-seed stochastic household profiles.
- `case1/studies/epm_gis_pandapower_v1/`: GIS network, assumed service attachments, `run_hour` coordinated-Q search, and pandapower network.
- Saved *discrete* `outputs/full_study/shortlisted_hourly/{seven,nine,twelve}_*/model_manifest.json` and hourly dispatch, without editing them.

The full-year MILP optimizer's SOC is **dynamic and perfectly forecast**, not an adaptive SOC reserve rule. It uses `e_cyclic=True`, and eta_ch=eta_dis=sqrt(0.95), with battery charging only from the solar DC bus. The older `wp1_v3` adaptive reserve remains independent.

## Exact saved hardware (not hypothetical newly optimized hardware)

| Case | Candidate trafo | Houses | Panels, 435 W | Battery usable | DC battery power | Inverter |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `seven` | 94022 | 7 | 26 | 21.625 kWh | 8.49905 kW | 7.6 kVA |
| `nine` | 94022 | 9 | 34 | 25.95 kWh | 9.55864 kW | 10 kVA |
| `twelve` | 106039 | 12 | 41 | 34.6 kWh | 12 kW | 12 kVA |

These are from source saved **model manifests**. The `nine` case cannot run against the current 7-house base GIS territory until H01/H02 assignments are explicitly added as **new hypothetical** physical service attachments, so the pilot stops instead of silently changing the EPM map. Start with seven and twelve. V1.1 also permits the explicit nine-house scenario, retaining the H01/H02 provisional service attachments and excluding H29.

The 106039 five-*kVA* transformer assumption is deliberately conservative versus the ambiguous 5-*kW* portal field, but it is **not a confirmed installed nameplate**. The GIS pandapower study represents archived phase geometry as a balanced three-phase proxy with an internal factor of three. This pilot preserves that exact proxy and does not certify actual split-phase service, neutral currents, impedance, or service paths.

## Method

1. Select a small reproducible stress/critical-hour set from the original 8,760-hour reference schedule.
2. Evaluate the saved inverter P with the existing pandapower coordinated-Q controller at each selected hour.
3. For a failed hour, sample inverter P between 0 and the smaller of aggregate house demand and fixed inverter kVA, preserving the original zero-export policy. Search Q in both signs under `|Q|<=min(q_ratio*P_inst,sqrt(S^2-P^2))`.
4. Group adjacent sampled feasible P values into candidate continuous P bands. Choose the band nearest the saved P. **The interval between sample points is not mathematically proven AC-feasible.** Never extrapolate beyond sampled P. If no sample passes, stop rather than fabricate a redispatch.
5. Re-solve the full original 8,760-hour PyPSA scheduling model with **exact same fixed hardware, no new AC constraints**. Compare the yearly objective to the saved reference. Stop if mismatch exceeds the **1 USD reproducibility diagnostic threshold**. This threshold is merely a regression tolerance, not an engineering margin.
6. Derive the manufacturer physical minimum SOC from **SE-G5.1 (20% = 80% DoD)** while keeping the historical PyPSA Store energy coordinate and fixed installed equipment. Run two same-hardware reference solves, first under the historical SOC range for reproducibility, then with the manufacturer floor. Add the selected hourly inverter P bands to Linopy, solve all 8,760 hours again with the **same manufacturer SOC floor**. Preserve `Store.e_cyclic`, battery power limits, round-trip charging losses, and zero-ENS and zero-export constraints. Re-check the reconstructed SOC equations hour by hour.
7. Re-evaluate the redispatched P values in pandapower and record successes and failures. No annual AC pass is claimed until every hour is independently checked; failed hours must be re-sampled or the structural limits revisited.
8. Compare incremental AC-redispatch cost against the recomputed **manufacturer-SOC-constrained fixed-hardware baseline**, not the old uncorrected SOC range or a different equipment configuration.

## Nighttime reactive power

`--night-q off` (default): `Q=0` where the reference installed-PV **availability** is essentially zero, regardless of battery discharge. It is an intentional conservative proxy, not a validated sunrise/sunset schedule.

`--night-q idealized_on`: allow the full nominal Q capability during such hours (as the earlier coordinated Q study did). This assumes the grid-connected inverter can hold a DC link and provide nighttime VARs. Real reactive-current losses, auxiliary power, battery SOC drain, equipment thermal response, and manufacturer mode support are **not** in the original PyPSA energy model. Do not claim this sensitivity is an implementable control unless these are added and verified.

At P=0, an inverter producing 3 kVAr for an hour does **not** inherently consume 3 kWh. It exchanges reactive energy with the AC system; real power is consumed by losses and DC-link auxiliaries, potentially sourced from a BESS or the grid.

## Local run instructions (no GitLab writes)

Copy this **entire folder** into the checkout as:

`case1/studies/ac_aware_redispatch_v1/`

From the repository root (Windows CMD/PowerShell), install/reuse the existing PyPSA, Linopy, HiGHS, pandapower, pandas, numpy and pytest environment from the current project. Run the tests first:

```powershell
python -m pytest -q case1/studies/ac_aware_redispatch_v1/tests
```

Then a first **12-critical-hour**, intentionally coarse and speed-oriented, 7-house pilot:

```powershell
python case1/studies/ac_aware_redispatch_v1/run_pilot.py --repo-root . --case seven --outdir case1/studies/ac_aware_redispatch_v1/outputs/seven_pilot_02 --night-q off --p-grid-points 7 --q-grid-points 9 --q-refine 0 --max-hours 12
```

For the distinct 12-house reference, select `--case twelve`, use an entirely new output path such as `outputs/twelve_pilot_01`, and **retain the same parameters** for the first matched comparison. The selected reference is head-connected, 5 kVA *assumed* transformer and Q ratio 0.25, with assumed household load allocation.

The `--p-grid-points 7` and `--q-grid-points 9` are pilot speed settings only, **not accuracy standards**. After timing and reviewing output, study refinement (for example more P/Q points) and determine whether the selected redispatched P remains AC-feasible. Do not increase scenario counts blindly until this comparison is reliable.

## Outputs (in a new, nonexisting `--outdir` only)

- `selected_hours.csv`: reproducible critical-hour selection
- `ac_reference_hours.csv`: original AC checks, no editing of source
- `ac_p_samples.csv`, `sampled_corridors.csv`, `unresolved_hours.csv`: sampling and unproven corridor hypotheses
- `fixed_hardware_reference_soc_hourly.csv`: recomputed historic SOC reference; `fixed_hardware_manufacturer_soc_baseline.csv`: same hardware with recommended physical SOC floor, only if the sampling stage has some viable corridors
- `redispatched_hourly.csv`: chronological revised dispatch, only if reoptimization is successful
- `redispatch_ac_validation_selected_hours.csv`: independent AC rechecks on the selected hours, **not annual validation**
- `pilot_manifest.json`: exact assumptions, case hardware, speed, unresolved cases, outcome, and cost comparison

**Known limitations:** this pilot does not yet loop all 8,760 AC hours with incremental corridor updates, enforce a full nighttime-Q loss model, solve an AC OPF, verify hardware from manufacturer sheets, or implement the 7-to-20 household hosting sweep. Those are distinct follow-on gates, not claimed results. It also does not import actual separate household hourly meters or actual per-house phase connections.

## Decisions already accepted

- Main method: sampled P/Q operating regions and full-year chronological fixed-hardware redispatch, AC recheck in pandapower.
- Alternative for later: sensitivity-derived cuts or multiperiod AC OPF.
- Maintain the study screening limits of 0.97 to 1.03 pu and <=100% transformer/line loading, not official EPM limits.
- Keep equipment and export policy unchanged when calculating incremental redispatch costs.
- Preserve every old study, reference schedule, manifest, and figure; do not overwrite GitLab main.
- Widen to household hosting and other transformer configurations once at least one constrained operating mode works and validation tests are checked.

## Known upfront issue fixed in v1.1

Previously a `--case seven` run would halt with `Saved synthetic profiles count differs from GIS provisional associations`, because the full provisional GIS file has **10** candidate houses on 94022. The saved seven-house PyPSA case assumes seven profiles and cannot include the additional alternatives H01/H02/H29. Rather than rescale demand, silently change assignments or accept a 10-house feeder with seven-house demand, v1.1 selects the seven explicit reference house IDs. All unverified source assignments remain unmodified.

**Do not reuse the old output directory.** The earlier failed script created `outputs/seven_pilot_01` before checking memberships. Use a distinct `outputs/seven_pilot_02` to preserve provenance. Copy v1.1 files over the existing **pilot folder only**.

The manufacturer's Deye SE-G5.1 80% DoD and 50 A continuous current limits, exact-nameplate uncertainty and the 3-phase/240/120V mismatch are documented in `HARDWARE_EVIDENCE_2026-11-04.md`.
