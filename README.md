# SEEDExchange WP1, 12-house 106039 manufacturer-SOC and voltage-band pilot

**Patch v1.6, 4 November 2026. Status: implementation and unit tests only.**

This is an additive patch for the existing `case1/studies/ac_aware_redispatch_v1/` in the full local GitLab repository. It has no new numerical simulation results. It preserves the frozen 94022 seven-house calculations and the original PyPSA and EPM GIS models.

## Why this study is separate

The existing 7-house 94022 PV/BESS reference passed 8,760/8,760 hourly AC power-flow checks after chronological feedback under the **original** 0.97–1.03 pu research band. Subsequent 94022 full-year PF 0.90 / service-length x1.6 study reported 111 strict-band violations, but no 0.95–1.05 pu engineering-target violations, **for that exact fixed dispatch and assumed network**. The 12-house 106039 scenario is not an extrapolation of those findings.

## Fixed research reference for 106039

The script checks that the saved `twelve_best_fixedPV_41panels` reference has 12 synthetic household profiles, assigned candidate node 923494, zero export and **assumed** 5 kVA transformer. From the GitLab reference manifest, the fixed equipment is:

- 41 x 435 W PV panels = **17.835 kWp**.
- 8 Deye SE-G5.1 battery modules, nominal **40.96 kWh** and historic PyPSA Store upper bound **34.60 kWh**.
- A manufacturer-based physical SOC minimum of 20%, equivalent to **1.832 kWh lower bound in the historical Store coordinates**. The physical 20%–100% operating window is **32.768 kWh** in this model. This mapping assumes nominal 5.12 kWh per module corresponds to 100% physical SOC and does not constitute an independently verified BMS operating range.
- An originally optimized battery-side power limit of **12 kW** and inverter rating **12 kVA**, fixed for this pilot, not commercially certified hardware choices.
- Original saved energy-only annualized cost is a historical proxy, not the outcome of the updated manufacturer-SOC or AC model.

The provisional GIS territory contains H11, H13, H16–H25. House connections and phases remain unverified. The **5 kVA** nameplate is a conservative research scenario, not EPM-certified transformer data. The balanced GIS model uses assumed service drops, cable impedance and transformer parameters.

## Installation

Extract the ZIP into the **root of the existing repository**. New files are placed under `case1/studies/ac_aware_redispatch_v1/`. The included v1.5 plotting patch scripts are additive; no original source or prior results need replacement. Ensure earlier v1.1, v1.2 and v1.3 files are already present.

From the repository root, run:

```powershell
python -m pytest -q case1/studies/ac_aware_redispatch_v1/tests
```

## Stage A: manufacturer-SOC baseline with fixed hardware

```powershell
python case1/studies/ac_aware_redispatch_v1/run_12house_manufacturer_baseline.py --repo-root . --outdir case1/studies/ac_aware_redispatch_v1/outputs/twelve_manufacturer_01
```

The script calls the **existing** PyPSA/Linopy model with the fixed saved equipment and reoptimizes its full 8,760-hour battery charging, discharging, inverter dispatch and SOC. It imposes the physical 20% minimum SOC. No fabricated reserve heuristic, no nighttime Q or loss adjustment. It verifies the exact reference demand and GIS scenario membership and writes `fixed_hardware_manufacturer_soc_baseline.csv`, `pilot_manifest.json`, `manufacturer_baseline_summary.json`. It rejects output folder overwrite.

It does **not** assert that the AC network is feasible. No investment-capacity sweep occurs in Stage A.

## Stage B: independent AC validation at the engineering target

Smoke test a *partial* run first, recording it as diagnostic only:

```powershell
python case1/studies/ac_aware_redispatch_v1/validate_annual_ac_target.py --repo-root . --pilot-dir case1/studies/ac_aware_redispatch_v1/outputs/twelve_manufacturer_01 --outdir case1/studies/ac_aware_redispatch_v1/outputs/twelve_ac_smoke_01 --max-hours 24 --vmin 0.95 --vmax 1.05
```

Then run the complete year to a **different** folder:

```powershell
python case1/studies/ac_aware_redispatch_v1/validate_annual_ac_target.py --repo-root . --pilot-dir case1/studies/ac_aware_redispatch_v1/outputs/twelve_manufacturer_01 --outdir case1/studies/ac_aware_redispatch_v1/outputs/twelve_ac_full_01 --vmin 0.95 --vmax 1.05
```

The script validates the **saved 8,760-hour** trajectory, exact household demand, manufacturer SOC floor, fixed hardware, energy balance and cyclic battery SOC. It uses the existing EPM GIS network, transformer-head inverter, equal household load allocation, **no nighttime Q**, daytime coordinated Q capability ratio 0.25, and the existing pandapower model. Device-specific reactive capability and inverter losses remain unverified.

The validator writes `annual_ac_hours.csv`, `annual_ac_summary.json`, `annual_ac_violating_hours.csv`, `annual_ac_worst_voltage_hours.csv`, and `voltage_band_comparison.csv`.

The latter **reclassifies the same P/Q operating points** against four voltage magnitude bands (0.90–1.10, 0.90–1.05, 0.95–1.05, 0.97–1.03). It does not rerun coordinated Q separately for the other bands, and is not a formal assessment of one-minute or ten-minute regulatory compliance. The primary AC solve enforces 0.95–1.05 pu and transformer/conductor loading <=100% as research screening thresholds. The 0.90–1.10 reference is based on national voltage guidance but we do not interpret hourly, balanced-node results as legal compliance.

## Stage C: evidence-based action after annual results

- If 0.95–1.05 passes all 8,760 hours, retain this as a **conditional AC-screened** fixed-hardware reference. Then compare the 7-, 9- and 12-house configurations under matched assumptions and begin manufacturer-constrained **PV/BESS/battery-power/inverter capacity sweeps**. The 8-module system is **not** the final battery selection.
- If the AC engineering target fails, inspect all failing hours, network operating points, SOC and inverter P/Q capabilities. Only then construct AC-feasible P corridors and reoptimize full-year SOC. **Do not run the old `run_annual_feedback.py` unchanged**, because it hardcodes the older 0.97–1.03 pu band. A band-aware feedback extension must be implemented using the actual annual outputs and separately tested.
- If the fixed 12-house hardware cannot meet all constraints, preserve infeasibility as a valid outcome, then explore other hardware and explicit assumed transformer-nameplate sensitivities.

## Verification and limits

- Pure helper tests: 9 new tests; 41 combined tests in an assembled copy of the existing pilot scripts passed in this environment.
- Syntax and ZIP integrity checked.
- **Not run here:** PyPSA, Linopy, HiGHS, pandapower, no full-year AC outcomes, no field validation. The current execution environment does not have these solvers.
- Do not confuse the original 106039 8,760-hour, nighttime-Q-enabled 0.97–1.03 reference with this proposed night-Q-off 0.95–1.05 study. Those are different operating assumptions.

## Source / version discipline

Input basis: `KKhan02/resilient-energy-systems` reference files from 3 November 2026, latest inspected main commit `e377e21d26db4bffd7a164d1257d5860bb01f325`. The runtime records the actual local Git revision and file SHA256 hashes. This patch has **not** been pushed to GitLab or run in GitLab CI.
