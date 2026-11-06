# WP1 seven-house 94022, reference checkpoint before sensitivity runs

Source: user-uploaded `annual_ac_hours(1).csv` and `redispatched_hourly(1).csv`, 2025, 8,760 rows each. **This document is a descriptive audit of the existing single operating case, not a new PF/length robustness result.**

- Fully converged and AC-feasible at baseline assumptions: 8760/8760.
- Minimum modelled voltage: 0.970098728 pu. Study threshold: 0.970000 pu; margin 0.000098728 pu.
- Hours with Vmin below 0.975: 41.
- Hours below 0.980: 191.
- Maximum transformer loading: 58.5846%.
- Maximum line loading: 8.9533%.
- Critical-hour selection for robustness pilot (weak voltage + peak P/demand + thermal extremes + monthly weakness + endpoints): 77 distinct hours. These indices are retained in the adjacent CSV.
- The critical sample is **not** sufficient to declare any varied PF or service factor annually feasible.
- Existing AC simulation evaluates line and transformer losses but does not integrate these back into PyPSA hourly SOC or grid-import cost.

## Voltage quantiles

| Quantile | Vmin, pu |
|---|---:|
| 0.1% | 0.971320 |
| 1% | 0.978020 |
| 5% | 0.981817 |
| 50% | 0.988793 |
| 95% | 0.993111 |


## Next computational gate

1. Replay this identical dispatch with PF 0.98, 0.95, 0.90 and service-factor 1.0, 1.3, 1.6, using the `run_robustness.py` patch.
2. Inspect all failed critical scenarios. Critical pass requires full-year checking before an annual pass claim.
3. For scenarios that fail, evaluate P/Q feasibility and rerun 8,760-hour PyPSA dispatch without violating the battery SOC or manufacturer limits.
4. Screen alternatives with `shortlist_equipment.py`; every archived selected design is energy-only until newly optimized and AC-validated.

## Source data SHA256 (uploaded bytes)

- `annual_ac_hours(1).csv`: `3414f4cc60fcd9809e34bad2d7502e3bbed4261cddd787d7cf69661639bcd95e`
- `redispatched_hourly(1).csv`: `6bdf93cba08e80db0614aff54263de7b6ec7d21373c187303a5e785bcf570b09`
- `annual_ac_summary(1).json`: `76958885bd4819ac7e7a6d1b7885d7bbb9244dae92c1e3af4e2076f64d7405e7`
