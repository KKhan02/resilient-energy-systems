# WP1 AC-aware redispatch: full-year diagnostic patch

This patch adds a **new file only**, `validate_annual_ac.py`, to the existing v1.1 pilot. It does not overwrite or modify the previous saved MILP, EPM GIS, pilot scripts, or outputs.

## Purpose

The initial 12-hour pilot found 2 AC violations in the **saved original** dispatch, but the recomputed manufacturer-SOC baseline already passed those same 12 hours. Re-solving with provisional P corridors produced exactly the same 8,760-hour trajectory and annual cost. A year-long, unselected AC screen is required to establish whether and where active-power redispatch is actually necessary.

## Usage from repository root

Create a fresh output directory automatically by selecting a unique name. This command reads the **existing v1.1 pilot outputs** and reruns all 8,760 hours using exactly the same selected GIS household scenario and conservative night Q=0:

```cmd
python case1/studies/ac_aware_redispatch_v1/validate_annual_ac.py --repo-root . --pilot-dir case1/studies/ac_aware_redispatch_v1/outputs/seven_pilot_02 --outdir case1/studies/ac_aware_redispatch_v1/outputs/seven_manufacturer_annual_ac_01
```

If your v1.1 result folder has a different name, replace only `--pilot-dir` with its actual location.

Outputs:
- `annual_ac_hours.csv`: separate AC power-flow result for each evaluated hour.
- `annual_ac_violating_hours.csv`: hours that fail any AC condition or fail to converge.
- `annual_ac_worst_voltage_hours.csv`: 30 lowest-voltage hours.
- `annual_ac_summary.json`: pass counts, margins, evidence labels and input hashes.

Assumptions: provisional GIS-backed balanced feeder, EPM-backed conductor geometry with assumed service routes and electrical parameters, 5 kVA nameplate scenario, 0.97 to 1.03 pu research voltage thresholds, 100% thermal research limits, head inverter, equal household load allocation, zero inverter reactive power when PV DC availability is zero. These are **not** verified field conditions.

The program is intentionally read-only with respect to the source repository models and existing pilot output. It refuses to use an existing output folder. A full-year pass establishes only model-conditional feasibility; it does not validate phase imbalance, physical equipment, inverter nighttime capability, metering, EPM interconnection requirements, or field nameplate values. The AC model's losses are not fed back into the PyPSA economic objective.
