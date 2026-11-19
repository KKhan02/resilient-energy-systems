# Demand provenance and power interpretation | 19 November 2026

## What the files establish

The actual load *shape* for the new Study A is from `Demand_curve.xlsx` `Tabelle1!F5:I28`, extracted as `data/demand_excel_seasonal_24h.csv` in the source-audited v4 preflight. Four 24-hour curves correspond to September–November, December–February, March–May, and June–August. Compare the separate original HOMER XML `SimulacionTampico1k(1).xml`; its values have coarser roundoff.

The baseline *annual energy target* comes from the HOMER primary-load `scaled_annual_average=20.8`, a four-house daily energy figure; code `daily_4hh*365/4` yields 1898 kWh/year **per synthetic household** (5.2 kWh/day). The full-precision Excel curves are normalized over the exact 2025 chronology to 1898 kWh per home/year; they are NOT interpreted as total load of all 35 homes. HOMER-mode profiles remain historical-reproduction controls.

The `prepare_study_a.py` generator creates 35 **independent hourly synthetic profiles**, seed 20250913, daily relative Gaussian SD .20 and hourly SD .25, nonnegative clipping, and an independent yearly energy renormalization for each home. Every named mapped home H01–H35 has one fixed 2025 profile across A0/A1 transformer assignments, in `fixed_house_to_profile_map.csv`. This is **not** 35 metered household histories; yearly equality across homes is a methodological assumption.

## Modelled values read directly from signed 2025 Excel-mode CSV

| Scope | Annual kWh | Daily mean kWh | Average kW | Peak coincident 1-hour kW |
|---|---:|---:|---:|---:|
| 1 synthetic home | 1898 | 5.2 | 0.2166667 | Different by house, 0.619837–0.775578 |
| A1 106039, 11 homes H11 and H16–H25 | 20878 | 57.2 | 2.383333 | 5.326677 (Oct 13 19:00) |
| A0 106039, 12 homes | 22776 | 62.4 | 2.6 | Not recomputed for this audit |
| Complete 35-home mapped population | 66430 | 182.0 | 7.583333 | 15.096765 (Nov 1 19:00) |

Calculation: `5.2 kWh/day / 24 hours = 0.2166667 kW` average; `1898 kWh/year / 8760 hours` same. Those are **annual-average powers**, not fixed continuous appliance powers, inverter ratings or peak loads. One profile's hourly maximum is a maximum one-hour *average*, not subhourly inrush/current spike. Sum houses' simultaneous hourly powers before computing transformer peak. The 35 mapped consumers occupy different provisional transformers, and A1 106039 has 11 specific homes. Never apply all 35 to a single 5 kVA source transformer.

## Important limitations
- Provisional source 5 kVA transformer at 106039 is **a modelling assumption**, not confirmed original nameplate or measured spare capacity.
- The 5.2 kWh/day/home norm is derived from the provided HOMER case, not a field survey or measured demand from these exact El Arenal properties. A proper load-input sensitivity should test additional calibrated daily-energy levels when site data arrive.
- PF sensitivity .95/.98/1.00 changes Q load and AC constraints; it does not change the initial energy target.
- The current Stage 2 PV priority experiment serves A1 106039 **11 homes, 20878 kWh/year**. Annual `grid_import_kw` integrates the grid *residual* after PV+BESS, not system gross household demand.
- Previous source-signed 20 HOMER-mode household series match archived historic data, but do not treat a newly created Excel-mode trajectory as identical to that archived original.

Source pointers: `case1/studies/SEEDExchange_StudyA_LocalPreflight_v4/scripts/prepare_study_a.py`; `data/demand_excel_seasonal_24h.csv`; `outputs/run_02/household_profiles_2025_excel_35.csv`; `outputs/run_02/fixed_house_to_profile_map.csv`; `outputs/run_02/historical_profile_audit_v1.json`; `case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/input_manifest_v6_2.json`.
