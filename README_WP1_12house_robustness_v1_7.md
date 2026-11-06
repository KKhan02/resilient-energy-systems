# SEEDExchange WP1: 12-house 106039 AC robustness, v1.7

**Scope:** New additive script to test the **already manufacturer-SOC-constrained** twelve-house dispatch against provisional feeder uncertainties. The code changes **no equipment** and **does not modify SOC or reoptimize P**. It is not a sizing or resilience study. It uses existing `case1/studies/ac_aware_redispatch_v1` modules and the full local GitLab checkout.

## Verified source result (uploaded 4 November 2026)

The 12-house / 106039 manufacturer baseline passed 8760/8760 simulated AC hours at household PF=0.98, service factor=1.0, 0.95–1.05 pu target and ≤100% modelled thermal loading. Minimum household voltage 0.955651 pu, maximum transformer loading 94.438659%, maximum line loading 8.821249%, modelled AC losses 456.306 kWh. Reclassification of the **same** AC results against 0.97–1.03 pu gives 145 failing hours. The 12-house feeder is a balanced GIS-backed equivalent with unverified household service attachments, conductor impedances and nameplate ratings. Hourly AC checks are not duration-based regulatory compliance evidence.

Of the 145 strict-voltage failures, 143 occur from 18:00 through 22:00; all have selected Q=0. The final 0.95 target is only 0.005651 pu below the minimum voltage, and transformer loading reaches 94.44%. This baseline pass does not imply that lower-PF or longer-service sensitivity cases also pass.

## Prerequisites

The local repository must contain the earlier successfully run outputs:

- `case1/studies/ac_aware_redispatch_v1/outputs/twelve_manufacturer_01/` with `pilot_manifest.json` and `fixed_hardware_manufacturer_soc_baseline.csv`.
- `case1/studies/ac_aware_redispatch_v1/outputs/twelve_ac_full_02/` with `annual_ac_summary.json` and `annual_ac_hours.csv`.
- The existing PyPSA, GIS pandapower, and v1.6.1 validator source modules. Nothing is copied over these files.

The new script validates source hashes, timestamp alignment, saved hardware, case/transformer membership, manufacturer SOC provenance and reproducibility of the original PF=0.98, factor=1.0 AC points. It refuses to report results if these checks fail.

## Install and run

Extract the archive into the **root** of `resilient-energy-systems`. One new script and one new test file will be added to `case1/studies/ac_aware_redispatch_v1/`, plus this README. Other files stay intact.

Run the pure-Python tests:

```powershell
python -m pytest -q case1/studies/ac_aware_redispatch_v1/tests/test_12house_robustness_v17.py
```

Run **critical-hour screening of all nine combinations**:

```powershell
python case1/studies/ac_aware_redispatch_v1/run_12house_robustness.py --repo-root . --pilot-dir case1/studies/ac_aware_redispatch_v1/outputs/twelve_manufacturer_01 --annual-dir case1/studies/ac_aware_redispatch_v1/outputs/twelve_ac_full_02 --outdir case1/studies/ac_aware_redispatch_v1/outputs/twelve_robustness_critical_01 --mode critical --vmin 0.95 --vmax 1.05
```

The scenario matrix uses load PF values 0.98, 0.95, 0.90 and assumed service-length multipliers 1.0, 1.3, 1.6. Critical hours combine reference voltage below 0.965 pu, top-15 voltage/loading/demand cases, and monthly minima. These settings are study hypotheses, not measured bounds.

If any case fails this critical test, it is already **conditionally infeasible at fixed dispatch** under the chosen model. A critical-sample pass is **not** evidence of a full-year pass. For a chosen combination, use the full-year mode, e.g. the stressed PF=0.90, factor=1.6 case:

```powershell
python case1/studies/ac_aware_redispatch_v1/run_12house_robustness.py --repo-root . --pilot-dir case1/studies/ac_aware_redispatch_v1/outputs/twelve_manufacturer_01 --annual-dir case1/studies/ac_aware_redispatch_v1/outputs/twelve_ac_full_02 --outdir case1/studies/ac_aware_redispatch_v1/outputs/twelve_robustness_pf090_f160_full_01 --mode full --power-factors 0.90 --service-factors 1.6 --vmin 0.95 --vmax 1.05
```

**Do not run every full-year case by default.** First review critical-hour outcomes and the assumed physical ranges.

## Output semantics

- `selected_hours.csv`: actual sampled time indices and timestamps.
- `sensitivity_ac_hours.csv`: AC results at *fixed* inverter active power and SOC trajectory, with coordinated daytime Q on and night-Q off.
- `sensitivity_scenarios.csv`: per-scenario convergence, feasibility, threshold count and thermal metrics.
- `robustness_manifest.json`: source SHA-256 fingerprints, assumptions, run mode, no-dispatch-change flag and revision.

## Next gate: PV/BESS/inverter sizing

Use `equipment_shortlist_energy_only.csv` only as a pool of initial candidates. First reoptimize fixed 12-house candidate hardware combinations with the 20% physical SOC floor and the existing 8760-hour PyPSA model. Then AC-screen each **candidate-specific** trajectory, with candidate-specific inverter P/Q limits and its physical connection. If a candidate fails, sample feasible P corridors and reoptimize SOC again before declaring it infeasible or changing hardware. Report zero ENS, cost, self-sufficiency, voltage and loading margins together. Avoid referring to any of the historical 60 candidates as AC-feasible before this step.

**Known limitation:** modelled AC losses are not included in PyPSA operation/cost, and vendor inverter Q capability, cable electrical parameters, phase allocation, EPM transformer rating and actual household attachments remain unverified. Full-year AC pass is conditional screening only.
