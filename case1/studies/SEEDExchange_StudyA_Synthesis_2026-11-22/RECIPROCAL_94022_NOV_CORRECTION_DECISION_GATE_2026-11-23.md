# 94022 reciprocal P1 | targeted AC correction decision gate

Dated 23 November 2026. This package is a constrained experiment, **not evidence of a successful corrective dispatch yet**. Derived from the completed P1 36-case-hour AC audit and the 52,560-hour original source battery and donor screening, not from newly run simulations.

## Why this is next

The archived A0 household cohort of ten houses under 94022 fails minimum house voltage at the 27 November 2025 20:00 saved original reciprocal P/Q schedules. Both A1 min-cost and SS90 hardware transferred to A0 have the same original zero-inverter-power night result, minimum house voltage **0.9436563346 pu** at PF .95. At PF .98 source result is **0.946770... pu**. Both have source battery after-hour energy equal to their 20%-SOC-model floor. Therefore simply increasing the target inverter output without a source hour and year SOC balance would be invalid.

The original annual source has a mathematically possible same-day discharge donor: min-cost 13:00 0.1153860326 DC kW (0.109616731 AC kW), SS90 17:00 1.9176825037 DC kW (1.8217983785 AC kW). These values are *isolated upper bounds* using the previous 12-hour PF .95 scalar screen, not already validated AC modifications. The new runner explicitly rechecks every year hour of battery and energy and runs the original physical-proxy AC model at **both** altered times and at PF .98/.95.

## Nonnegotiable gates

1. Signed source identities: frozen 16-case reciprocal hardware manifest, original v6.2 model and 35 household-specific GIS/profiles, source target annual energy CSV exact SHA, independently saved donor-envelope register, original 36-hour P1 AC target row baseline. No reusing A1 94022 topology as A0 load, no inferred new transformer or LV edge.
2. Mathematical conservation: no nonphysical battery discharge beyond existing source donor or hardware, capacity headroom throughout donor-target window, exact DC and AC closure, cyclic year-end energy, physically mapped minimum 20% SOC, zero grid export/unserved. Existing battery/PV hardware and annual equipment cost unchanged.
3. AC: 0.95...1.05 pu, <=100% assumed transformer and conductor; both PFs and both hours, with source daylight/zero-irradiance Q policy. Original target baseline results must reproduce saved P1 prior AC for the same model.
4. Interpretation: four sampled local AC points are only a *local pair* screen, not proof of 8,760-hour AC safety or a utility-certified connection. Prior 28 March 2025 low-voltage failure and remaining P2/P3 reciprocal sources are not automatically resolved.

## Expected follow-on

- If min-cost has no pair passing within its <0.11 kW AC single-donor upper, do **not** conclude that any min-cost configuration is impossible; only that the *particular source-signed one-donor, <=12h, fixed hardware, fixed-network method* did not pass. Next options are controlled expanded chronology, other equipment or verified network route/phase evidence.
- If SS90 has a local passing amount, this remains a candidate needing the 28 March correction and full-year check, with energy and AC losses in economics. Do not automatically declare a new annual solution or accept a single PF-only pass.
- If donor AC fails, this matters. Moving power may relieve the target while worsening the donor-hour voltage or thermal result. Keep both signed records and distinguish source baseline donor infeasibility from the extra constraint caused by the transfer.

## Methodical record

Run guide: RECIPROCAL_94022_NOV_DONOR_TARGET_AC_RUN_LOCAL_2026-11-23.md.
Runner: matched16_94022_nov_soc_shift_ac.py.
Synthetic tests: test_matched16_94022_nov_soc_shift_ac.py.
Original P1 AC: StudyA_Reciprocal12_P1_AC_Pilot_v1/TARGETED_36_AC_CASEHOURS.csv.
Source-only cap: RECIPROCAL_P1_TEN_FAILED_EVENT_DONOR_CAP_2026-11-23.csv.
No historical data/AC copies, main, untracked local P1 v2, or older ZIP files altered.
