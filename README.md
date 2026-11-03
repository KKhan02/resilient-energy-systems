# pandapower validation plot fix, v1.1

This replaces **only** `case1/studies/pandapower_dispatch_validation_v1/run_validation.py` and adds a regression test. All input dispatch and optimization outputs remain unchanged.

Fixes the post-processing `KeyError: '2025-11-29 20:00:00'`. The `groupby(...).idxmin()` return value is the **timestamp**, not a DataFrame row index.

Adds `--plots-only` to regenerate the four summary/voltage-profile figure groups from existing completed calculations, without running any new power flows, without reading the 8,760-hour inputs, and without requiring pandapower in the active environment.

From the repository root, merge/overwrite these files into their stated paths, then run in PowerShell:

```powershell
cd case1/studies/pandapower_dispatch_validation_v1
python -m unittest discover -s tests -v
python run_validation.py --plots-only --output outputs/critical
```

Existing `outputs/critical/scenario_summary.csv`, `tap_voltage_profiles.csv`, and `powerflow_hourly_or_critical.csv` remain intact. The original AC solve results were written before plotting, but the run crashed before writing the final `validation_manifest.json`. To produce the full manifest, rerun the short critical mode only if needed, after checking the existing outputs. A full-year pandapower run is a separate operation.

The network is still the **synthetic representative feeder**, not geographic EPM topology. This patch does not alter model physics or imply a validated actual feeder.
