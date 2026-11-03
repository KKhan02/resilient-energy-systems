# EPM transformer-aware Volt–Var, critical-hour results review

## Dataset
- 32 scenario records, each with 40 critical-hour results. 1,280 AC calculations, all converged.
- Two EPM LV territories: 94022 (10 properties, 5 kVA) and 106039 (12 properties, 5 kVA).
- Head and midpoint inverter, unity PF / HIL Volt–Var, q_ratio 0.25/0.48, load PF 0.98, service multiplier 1.0; safeguard ON/OFF.
- EPM mapped LV backbone plus assumed house service connections. Inverter active-power dispatch unchanged, settled reactive control.

## Major results
- Transformer safeguard had **zero interventions**: guard_limited_hours=0, guard_unresolved_hours=0 and Q reduction=0 in every case. The ON and OFF results were identical. Its ability to correct overload was **not exercised** by this test set.
- Peak transformer loading across scenarios was **96.39%**, with no transformer thermal overloads in 1,280 observations.
- All 32 scenarios fail the 0.97–1.03 pu voltage-screen pass due to undervoltage; the optimized inverter does not guarantee LV service voltage.
- At midpoint, the 94022 minimum LV voltage changes from 0.9500 (unity) to 0.9605 (Volt–Var 0.25) and 0.9654 pu (Volt–Var 0.48). 94022 peak transformer loading is 91.22%, 90.03%, 95.46%, respectively.
- At midpoint, 106039 minimum LV voltage changes from 0.9595 (unity) to 0.9686 (Volt–Var 0.25) and 0.9673 pu (Volt–Var 0.48). Peak loading is 93.99%, 92.36%, 96.39%, respectively.
- 106039 middle unity voltage maximum 1.0316 exceeds 1.03, while Volt–Var 0.25/0.48 maxima are 1.0218/1.0173, respectively.
- Tested hours below 0.97 for midpoint 106039: 10 at unity, 10 with 0.25, 6 with 0.48. Minimum-voltage level and number of violation hours do not necessarily move together because different hours govern.

## Crucial interpretation
This is a controlled experiment under one demand PF and service-length assumption; it does not demonstrate transformer-guard correction. Test stress conditions where the **unguarded** inverter is known to overload the transformer (notably feeder-end injection), and compare OFF vs enforce for the same critical-hour records. The guard limits Q in the controller's current direction without changing P or demand. If unity-Q itself overloads, report unresolved overload instead of claiming correction.

## Run targeted stress test (Miniforge Prompt, from case1/studies/epm_gis_pandapower_v1)

```bat
python run_epm_validation.py --mode critical --trafos 94022 106039 --design optimized --assignment base --siting end --q-controls unity volt_var --service-factors 1.0 --power-factors 0.98 0.90 --q-ratios 0.25 0.48 --trafo-guards off enforce --trafo-max-loading-pct 100 --output outputs/trafo_guard_end_stress
python make_guard_figures.py --input outputs/trafo_guard_end_stress/ac_scenario_summary.csv --output outputs/trafo_guard_end_stress/figures
python -c "import shutil; shutil.make_archive('trafo_guard_end_stress','zip','outputs/trafo_guard_end_stress')"
```

This comprises 32 case definitions and approximately 1,280 selected-hour records before any additional safeguard inner solves. Check run results, guard_status, guard_limited_hours, guard_unresolved_hours, and the AC voltage/transformer tradeoff. The EPM network geometry and conductor electrical parameters retain documented assumptions; critical-hour passes do not establish year-round feasibility.
