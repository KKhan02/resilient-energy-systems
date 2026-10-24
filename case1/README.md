# SEEDExchange El Arenal, WP1 Case Study 1 v3, complete source package

**Scope:** Joint centralized PV/BESS/inverter and household expansion behind the 5 kVA EPM transformer 94022, with causal export and storage control and conditional islanded stress. **No forecasting or MPC in Case 1.** Do not treat this package as approval for installation or operation.

## 1. What you have

- `run_case1_v3.py`: full reproducible 2025 design sweep, economics, selected annual operation, 72-hour stress, CSVs and plots.
- `wp1_v3/model.py`: fast causal energy dispatch, transformer PCC kVA envelope, shared battery model, economics and user-defined control policies.
- `wp1_v3/plots.py`: all-design Pareto static PNG (full cloud and per-household), expansion, transformer duration, monthly supply, 72-hour stress, BESS-power comparisons.
- `results/`: **generated from the bundled inputs**, with model provenance recorded in `RUN_MANIFEST.json`.
- `data/`: the unchanged NASA hourly CSV, metadata and HOMER XML. Reference quotation PDF included.
- `legacy/independent_case1_original/`: **the COMPLETE original `SanRafael_Case1.zip` tree**, including all 15 modules (`rule_dispatch.py`, `grid_check.py`, `stress.py`, `economics.py`, `validation.py`, etc.), test code and saved results. Its results are not silently mixed with the new common-model v3 study.
- `legacy/case1_v2.py`: earlier version, unchanged. `legacy/SanRafael_*_v18/v5.ipynb`: original notebooks, unchanged.
- `tests/test_wp1_v3.py`: regression checks for kVA, dispatch energy balances, charge priority, causal reserve, exact reference-quote components and Pareto selection.

## 2. Run on Windows, from the package root

```powershell
python -m pip install -r requirements.txt
python -m pytest tests/test_wp1_v3.py -q
python run_case1_v3.py --require-pvlib
```

If pvlib is unavailable, `python run_case1_v3.py` uses the explicitly **unverified NOAA/Erbs PV approximation** rather than the original exact pvlib GHI/Erbs calculations. The bundled result files currently have that approximation because pvlib could not be installed in the build environment. **Rerun with `--require-pvlib` locally before presenting numerical results as source-aligned.** To try the fast small-grid smoke test use `--quick` (it overwrites result files, so copy the results directory first). You can change the study defaults with `--pf 0.95 --loading 0.8` and return to the provided reference with `--pf 0.98 --loading 0.9`.

The preserved `legacy/independent_case1_original/` also has `run_case1.py` and its own dependencies including pandapower, PyPSA and highspy. It must be run **separately**, against the same selected candidate/hourly PCC injections, to validate voltage, current and critical transformer hours. Full split-phase modelling and field-verified service connections do not yet exist.

## 3. Sweep and control

17 household counts **4 through 20**. PV **8 to 40 panels in steps of four, plus 48, 56, 64, 72, 80** (each 435 W). Battery energy **0, 2, 4, 6, 8, 10, 12, 16, 20, 24 modules**, scaled from HOMER's four-module nominal **19.2 kWh / usable 17.3 kWh**. Inverters **5, 6, 7.6, 8, 10, 12, 20, 24 kVA**. The final two options assume **two parallel 10 or 12 kVA Deye inverters** and require verification of controller compatibility, BMS, PV strings and grid interconnection.

The core dispatch prioritizes (1) household load from PV, (2) charge shared BESS with remaining PV, (3) export remaining generation subject to inverter rating and transformer apparent limit, (4) curtail surplus. When PV cannot meet demand, discharge the BESS then import from EPM, with involuntary shedding explicitly recorded rather than hidden. The model calculates residual Q from a constant lagging **household PF = 0.98**, and constrains **sqrt(P_PCC²+Q_PCC²) <= 4.5 kVA**, corresponding to an **assumed** 90% utilization of the nameplate 5 kVA. These are engineering sensitivities, **not official EPM settings**.

For the main Pareto, annual grid-connected ENS > 0 marks a case as **excluded in the PCC screen**, not feasible. This is not full feeder voltage, current, service or protection validation. Battery DC power is held at a 5 kW cap in the main uniform energy-size sweep; **`higher_households_battery_power_extended_screen.csv` adds 5, 7.5, 10, 15 kW for 12–20 homes and larger PV/BESS configurations**, and `battery_power_sensitivity.csv` tests 2.5, 5, 7.5, 10 kW for selected configurations. `ALL_designs_including_extended_battery_power.csv` joins and deduplicates these runs. Pareto figures use this combined design cloud. Battery replacement, battery current sharing and ageing remain provisional.

## 4. Which figures to use for WP1

1. `01_pareto_all_designs_self_consumption.png` and `01_pareto_all_designs_homer_sellback.png`: six static subplots (4, 8, 12, 15, 17, 20 households) displaying the **complete cloud of sampled scenarios** using continuous BESS usable-energy color scales, PV-size marker classes, colored crosses for PCC-ENS failures, and connected nondominated PCC frontiers. `pareto_per_household/` includes 34 detailed static figures covering all household counts 4–20 across both remuneration regimes. Rebuild these from the saved CSV with `python render_pareto_static.py`.
2. `01_pareto_all_designs_*.png`: professor-ready 4/8/12/15-household static Pareto comparisons under both compensation regimes.
3. `02_household_expansion_feasible_designs.png`: least annual per-house cost for 80/90/95% self-sufficiency targets; achievable annual self-sufficiency at different solar capacities and household counts.
4. `03_transformer_loading_duration.png`: year-long PCC apparent-power duration curves for screened configurations representing community sizes **4/8/12/15/17**.
5. `04_monthly_supply_multiple_community_sizes.png`: annual monthly energy balance, PV direct use, BESS discharge, EPM import and demand, for selected representative 4/8/12/15/17-home options, not only baseline four homes.
6. `05_72h_combined_stress_causal_controllers.png`: PV, load, actual and reserve SOC, battery discharge and cumulative strict energy shortfall during a 24-hour low-solar/high-demand prelude plus a **48-hour hypothetical EPM outage**. Compare four controllers on the same selected **8-home** system.
7. `06_bess_power_sensitivity.png`: independently varying battery power limits, with fixed hardware combinations.

**Economic Pareto interpretation:** A frontend's full cloud is larger than the line of nondominated cases. Use one frontier per fixed household population. `annual_total_no_credit_usd` and `annual_total_homer_credit_usd` include annualized capital/replacement charges **plus net purchased/sold electricity**, *not just capital cost*. The same physical local-first, transformer-envelope export dispatch generates both tariff regimes. The sellback credit is HOMER's hypothetical $0.275/kWh, *not confirmed EPM remuneration*.

## 5. Quotation-derived cost screening

The 12-panel / four-module / 5 kW reference quotation states **USD 11,974.79 excluding VAT and USD 14,250 including tax**, while HOMER splits USD 11,956 into PV USD 3,856, four-battery bank USD 4,770 and 5 kW converter USD 3,330. The code scales the HOMER component split to the quoted subtotal, then extrapolates **proportionally** by panels, battery modules and inverter nameplate capacity. This deliberately reproduces the reference $11,974.79 for 12P/4B/5kW. It is **not** a reliable procurement quote for the much larger arrangements or for parallel inverters. The proposal PDF includes Mexican CFE/MXN wording even though it is labeled for San Rafael, so Colombian tariffs and applicable fiscal treatment must be validated independently.

The updated code uses a 25-year horizon and 6% discount rate (study assumptions). The inverter lifetime is 15 years, while battery replacements follow the lesser of HOMER's 20-year float life and a throughput-derived lifetime (23,660 kWh per battery module divided by annual 0.5 × (DC charging + DC discharging) throughput). Replacements are discounted and scheduled strictly before year 25. **The existing saved results predate this correction and must be regenerated before citing new annualized costs.** It omits changing installation/site civil costs, insurance, land or roof area, permitting, commercial BMS/control systems, complex protection, and battery calendar-cycle ageing. It avoids simultaneously charging both a battery throughput wear penalty and replacement capex. Use +/- cost sensitivity before making a financial recommendation.

## 6. What the reserve formula means and what it does NOT establish

`adaptive` follows an **author-designed heuristic**, using previous completed days only:

`I_t = [mean PV energy over previous 3 completed days] / [mean PV energy over all earlier completed days]`;
`reserve_SOC = clip(0.30 + 0.60*(1-I_t), 0.30, 0.75)` during grid connection.

There is **no located paper validating this exact expression** or its 3-day, 0.60, 0.30/0.75 settings. Literature supports causal microgrid energy management and battery reserve management in general, not these parameters. Thus the generated resilience outputs are demonstrations of a **proposed** controller, not an empirically optimal controller.

The strategies are `conventional`, `fixed_reserve` (50% SOC), `adaptive`, and `adaptive_lm` (adaptive reserve plus an assumed 15% deferrable demand, 8-hour limit). During outages all reserves release to the battery's minimum SOC (10%). The assumed **30% critical share, 15% deferrable share**, and the validity of shifting load during outage need field data. Energy shifted into a backlog is **not counted as served** until later consumption; unpaid backlog appears in strict shortfall. The old independent case's 30% strict all-demand outage success for load management refers to **the sampled outage distribution and that specific synthetic flexibility model**, not a general failure rate.

References on the *general idea* only:
- Dey, Khatana, Mani, Salapaka (2021). [Transactive Framework for Dynamic Energy Storage Allocation for Critical Load Management](https://arxiv.org/abs/2101.05890).
- Sharma, Mathur, Mishra, Bansal (2022). [A critical and comparative review of energy management strategies for microgrids](https://doi.org/10.1016/j.apenergy.2022.120028).
- Abu Bakar et al. (2017). [Microgrid and load shedding scheme during islanded mode: A review](https://doi.org/10.1016/j.rser.2016.12.049).

## 7. Validation gates prior to engineering recommendations

1. Run the original pvlib GHI + Erbs solar conversion; compare 5.22 kWp annual DC energy against the saved v5 **7054.003295 kWh** target (and check hourly alignment, not just yearly total).
2. Reproduce base 4-house synthetic demand **7592 kWh/year** and original stochastic peak **2.166677435937405 kW**. The 4-home reference is **an audit point, not the design-space limit**.
3. Use the preserved pandapower v5 equivalent with actual controlled injections from v3 for critical hours, before declaring network voltage/current feasible. For expanded households update the secondary topology/service drops: the old 4–8 branch representation is insufficient. A balanced equivalent is **not** a full split-phase model.
4. Obtain EPM permitted continuous transformer loading, import/export permissions, islanding/anti-islanding/protection/transformer ownership and meter arrangement. Confirm whether multiple inverters may be paralleled on this connection.
5. Validate real demand/critical and deferrable appliance fractions; these are synthetic household traces, not meter measurements. Confirm PV field area/string DC voltage and batteries' BMS compatibility.
6. Reprice PV, BESS, inverters, installation, repairs and EPM tariffs with Colombian supplier quotes; invoice services from a different transformer are only an external sensitivity.

**Current screening interpretation:** Across the main fixed-5 kW battery-power sweep some zero-ENS cases reached 15 households; the targeted higher-household battery-power extension finds limited zero-ENS combinations through **17 households** (including 80 panels, 20 battery modules, 15 kW battery DC power and a hypothetical 24 kVA parallel-inverter set), but none at 18–20 households within the tested envelope. This is a bound on the **tested scenario grid**, not a claim that the transformer or community has a field-proven 17-household limit.

The current results report **PCC-only feasibility** and simulated energy availability if an island is correctly engineered. They are not commissioning or islanding proof.


### Annual SOC boundary-condition diagnostics (B05)

The default annual screen retains the declared **55% initial nominal battery SOC**, without artificially balancing the beginning and end of the model year. Each new design row reports `initial_stored_kwh`, `end_stored_kwh`, `soc_boundary_drift_kwh` and `soc_boundary_closed` (numerical tolerance 0.001 kWh). Positive drift means net energy carried into the end of the window; negative drift means net energy drawn down. Compare designs only with that difference visible; these diagnostics do **not** constitute a periodic-energy closure or a correction to grid imports.

For a **separate sensitivity analysis only**, `wp1_v3.model.dispatch_cyclic(load, pv, modules, inverter_kva, ...)` searches for an initial SOC whose ending usable energy matches its beginning over a complete, grid-connected local-day window. It reruns the same load, PV, battery and controller conditions and raises an error if closure cannot be demonstrated within the specified tolerance; it never adds energy to a simulated result. This method **must not** replace the physically preconditioned initial SOC of an outage/stress window, and does not establish a cyclic state for the adaptive controller's past-solar history. The already saved results predate these reporting changes and remain historical-only pending the controlled source-aligned rerun.
