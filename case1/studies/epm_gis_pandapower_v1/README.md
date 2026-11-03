# EPM GIS LV validation and coordinated reactive-power control

**Latest local status: 3 November 2026.** This active study reconstructs LV sections from EPM GIS conductor/node records, connects 35 candidate properties with explicitly assumed service drops, and replays previously optimized PyPSA active-power trajectories through pandapower. The model uses a balanced three-phase equivalent and proxy conductor impedance and current ratings. Its house-to-line associations are a working assumption, not a verified utility customer register.

## Study progression

The baseline `run_epm_validation.py` compares unity PF, HIL Volt–Var and inverter siting. `transformer_q_guard.py` limits reactive commands when transformer loading would exceed nominal ratings. `run_coordinated_q.py` and `coordinated_q_control.py` then search Q in both directions to satisfy simultaneous LV Vmin/Vmax, transformer and conductor limits. The Q capability ratio is swept, not restricted to 0.25 or 0.48. Energy dispatch and chronological SOC are **not changed** by this Q-only AC controller.

## Current evidence

- `outputs/coordinated_q_sweep_pf098/`: critical-hour Q-capability sweep, 106039 and 94022, control and placement comparisons.
- `outputs/coordinated_q_robustness/`: PF 0.90 and 1.3/1.6 service length uncertainty.
- `outputs/annual_106039_head_q025/`: 8,760 hourly AC results, 106039 12-house candidate territory, head placement, Q ratio 0.25, PF 0.98 and service factor 1.0. All hours passed the modelled 0.97–1.03 pu and thermal limits; minimum voltage was 0.970005 pu, meaning essentially zero robustness margin.
- `outputs/trafo_guard_end_stress/`: Q-induced thermal stress and response to transformer safeguard. A thermal pass does not imply a voltage pass.
- `data/`: source GIS, proposed household associations and transformer evidence.
- `tests/`: unit tests for topology and controller logic.

Historical transfer ZIP bundles were relocated to [the research archive](../../research_archive/transfer_zips/epm_gis/). Their expanded numerical outputs above remain authoritative.

## What remains

SOC-consistent active power redispatch is **not** yet implemented. The 8,760-hour PyPSA schedule is optimized with perfect foresight and replayed at fixed P. Any AC-motivated battery adjustment must respect SOC, discharge/charge power, inverter apparent power, annual ENS and revised costs. More work is needed on phase imbalance, measured cable properties, inverter nighttime Q capability and verified service drops. Do not treat the annual conditional pass as field certification.

[Professor walkthrough](../../professor_walkthrough/README.md) | [research status and audit](../../RESEARCH_STATUS_AND_AUDIT.md)
