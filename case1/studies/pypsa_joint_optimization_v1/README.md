# San Rafael, Case 1: PyPSA joint capacity expansion, first implementation

**Status: implementation code and previous-sweep figures prepared; FULL PyPSA optimization NOT EXECUTED or numerically verified in this sandbox.** The runtime does not provide PyPSA/Linopy/HiGHS, and network installation is blocked. The tests for pure helper functions pass, but the PyPSA integration test is skipped. No GitLab commits, pipelines or runner minutes used.

This is a **new study folder only** under `case1/studies/pypsa_joint_optimization_v1/`, designed to be copied into the existing `resilient-energy-systems` repository. Do not overwrite PyPSA v18, pandapower v5, the October annual screen, or any previously frozen result files.

## Source provenance

- **Stochastic households:** original 2025 v18/v5 household demand curves (`nasa_hourly_pv_and_load_inputs.csv`). Original v18 code uses `np.random.SeedSequence(20250913)` and separate independent child RNGs per house, with Gaussian daily and hourly perturbations using HOMER standard deviations; each individual profile is renormalized to **1,898 kWh/year**. These are **not real metered demand**, and the seed is only one reference realization. The saved reference has 20 individual synthetic profiles; do not call a test above 20 households a distinct stochastic-customer analysis without regenerating more profiles.
- **H01 vs H02:** earlier energy studies assigned both alternatives the same next synthetic profile and thus obtained identical results. This study uses house_8 for H01 and house_9 for H02 as *explicitly arbitrary distinct synthetic reference draws*. Differences in annual energy outcomes do not identify the actual supplied house or LV cable.
- **PV:** use `nasa_pv_dc_kw` 2025 NASA/pvlib-derived source, normalized by original 5.22 kWp; separate original NASA hourly GHI from the same source. No synthetic PV production is inserted.
- **EPM nodes:** for original 7, 8, 9 houses, node 931076/transformer 94022 has an archived 5 kVA nameplate; for 12 houses node 923494/transformer 106039, the portal reported nominal 5 **kW** and no nameplate kVA has been verified. Thus 5, 10 and 15 kVA in this code are hypothetical ratings, NOT installed infrastructure claims.

## Mathematical model

PyPSA DC-coupled topology: PV DC generator -> DC link -> shared inverter -> AC load. Battery has an independently expandable DC **Store** and separately expandable but linked charger/discharger **Links**, both efficiency `sqrt(0.95)`. The shared inverter has efficiency 0.95. The battery kW hardware has no separately sourced incremental cost beyond the selected integrated inverter. Its independently sized power rating is therefore economically degenerate where extra power can be provided at no extra quoted cost; report actual optimized peak charge/discharge as well and perform battery-power cost sensitivities before selecting commercial hardware. PV charges the battery directly via the DC bus; there is no AC-to-DC charging from the grid. Its cyclic-year storage balance prevents energy borrowed from an artificial initial SOC. Renewable curtailment is allowed.

The Linopy model explicitly chooses these variables jointly:

- Integer panel counts, 0.435 kWp per panel; study roof-panel cap is a **scenario variable** (32/48/64 panels), NOT a measured rooftop surface maximum.
- Integer battery module counts, 4.325 kWh usable per module (HOMER reference usable energy, distinguished from battery advertised nominal energy).
- Continuous battery DC power rating (kW), limited by bank/module current and the selected inverter family.
- One discrete inverter AC rating from the preserved Deye family (kVA treated as unity-PF active rating for this energy-only optimization).
- Every hour: solar dispatch/curtailment, DC battery charging and discharging, SOC, grid import and optional grid export.

The **PCC apparent-power approximation** is `sqrt(P_grid^2 + Q_load^2) <= nameplate_kVA * 0.90`, using fixed load PF=0.98 and no inverter VAR support. This algebraic profile constraint is stricter than a plain 4.5 kW bound for positive reactive demand. It is NOT an actual unbalanced 240/120 V AC power-flow, neutral check, feeder loss model or pandapower-hosting validation.

- `economic`: minimize annualized 25-year hardware cost + purchased grid electricity - conditional export credit, requiring 100% demanded energy served.
- `energy`: minimize annual imports with an investment CAPEX budget. This is operational self-sufficiency, NOT net-zero import minus exports.
- `frontier`: independently solve an economic optimum for each minimum self-sufficiency target and an energy optimum for each investment budget. Do not replace these with a weighted score.
- `hosting`: for **existing** 7-house or 12-house anchor, add one independent *anonymous synthetic profile* at a time up to 20, and test 32/48/64-panel ceiling, 70/80/90% self-sufficiency, and chosen kVA sensitivities. The largest passing N is **conditional energy hosting capacity**, not AC-proven physical hosting capacity.

## 25-year cost accounting

**YES, purchased grid electricity is included**, like the HOMER/hackathon accounting. Published prior sweep values use annualized equipment, **USD 0.29/kWh grid import**, and an illustrative **USD 0.275/kWh export credit**. Since that is not confirmed to be a valid Colombian community tariff, the new model uses **zero export by default** and keeps the reference-credit case separate.

Annualized cost comprises equipment acquisition (HOMER/quote proportional component prices), 2%/year proxy hardware O&M, battery replacement year 20, inverter replacement year 15, and grid purchases less eligible reference export credit. The discount is 6% and horizon 25 years. The objective is expressed in USD/year; NPC = annualized total / 25-year CRF. Battery early-throughput replacement is NOT endogenously modeled; calculate/review it after optimization before quoting final lifecycle results. Costs of LV cables, site-specific construction, protection, metering, EPM connection, taxes, new physical equipment, land and permitting are **excluded** until source figures exist. The historical quote was prepared for a different billing context and is NOT an EPM site-specific installation estimate.

## Outputs from each successful full-year solve

For every solution, `hourly_dispatch.csv` has 8,760 entries: requested demand, PV DC availability/generation, charge/discharge powers, usable SOC, grid import/export, curtailed PV, and PCC proxy P/Q/S. `monthly_energy_balance.csv` records solar GHI, demand, grid energy, PV, battery and self-sufficiency for every calendar month. The `figures` folder contains day (24h), week (168h), monthly (12) and yearly (8760h) PNG/SVG charts. `model_manifest.json` includes the relevant assumed transformer, cost, source hash, controls and unverified LV AC status.

**These new solution outputs do not yet exist**. The PNG/SVG files already in this distribution visualize the *previously supplied 290-row sweep only*. Labels distinguish panels, modules, DC battery kW and inverter kVA. Energy-screened results are NOT AC validated.

## Running in your local GitLab checkout

Copy only this directory into your local repository:

`case1/studies/pypsa_joint_optimization_v1/`

Use your existing pinned PyPSA environment (original repository noted PyPSA 1.2.4; must also have a compatible Linopy, pandas and a HiGHS solver). For a quick functional smoke test, the sample first-week run is not annual:

```powershell
python case1/studies/pypsa_joint_optimization_v1/run.py --repo-root . --outdir case1/studies/pypsa_joint_optimization_v1/outputs --mode economic --cases seven --hours 168 --continuous
```

Then run complete-year **continuous LP** first to check size/reasonableness, and **discrete MILP** for final equipment decisions:

```powershell
python case1/studies/pypsa_joint_optimization_v1/run.py --repo-root . --outdir case1/studies/pypsa_joint_optimization_v1/outputs --mode economic --cases seven,eight_H01,eight_H02,nine,twelve --hours 8760 --continuous
python case1/studies/pypsa_joint_optimization_v1/run.py --repo-root . --outdir case1/studies/pypsa_joint_optimization_v1/outputs --mode economic --cases seven,eight_H01,eight_H02,nine,twelve --hours 8760
```

For the separate Pareto analyses, initially limit to one case, test 5/10/15 **hypothetical** transformer ratings:

```powershell
python case1/studies/pypsa_joint_optimization_v1/run.py --repo-root . --outdir case1/studies/pypsa_joint_optimization_v1/outputs --mode frontier --cases twelve --transformer-kva-12 5,10,15 --hours 8760 --continuous
```

Then run the maximum household-energy-screen sensitivity, initially with manageable bounds, increasing only after a verified solve:

```powershell
python case1/studies/pypsa_joint_optimization_v1/run.py --repo-root . --outdir case1/studies/pypsa_joint_optimization_v1/outputs --mode hosting --hosting-case seven --hosting-start 7 --hosting-end 12 --hosting-panel-caps 32,48,64 --hosting-ss-targets 0.70,0.80,0.90 --hours 8760 --continuous
```

To see the effect of the old assumed export credit, use `--export reference_credit` on an otherwise identical experiment. Do **not** combine it with zero-export runs in a single unlabelled ranking.

PowerShell optional tests:

```powershell
python -m pytest -q case1/studies/pypsa_joint_optimization_v1/tests
```

GitLab Web IDE is sufficient for uploading/editing and final committing the package. The web editor does not execute numerical Python. No GitLab pipeline has been initiated as part of creating this package. The actual full-year PyPSA MILP and pandapower validation must be run later in a PyPSA/pandapower-enabled environment and independently verified before the results can be presented as optimized/AC-feasible.

## Clear distinction from previous 'modelling checkpoint'

The earlier checkpoint ZIP was **an analysis specification and repackaging of the previously saved sweep**, not a new PyPSA solve. This ZIP adds a runnable PyPSA/Linopy expansion implementation, CLI entry point, validation tests, clearer source-based figures and designated output structure, but it still **requires solver execution** before numerical optimum results exist.
