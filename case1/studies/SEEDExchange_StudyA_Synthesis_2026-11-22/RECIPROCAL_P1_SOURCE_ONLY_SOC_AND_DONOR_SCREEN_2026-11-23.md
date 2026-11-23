# Study A | P1 reciprocal six-case physical SOC floor and same-day donor window screen

**Independent source-only assessment:** 23 November 2026. **Status:** completed audit of six frozen 8,760-hour energy files and 10 distinct failed source events from the previously signed 36-case-hour P1 AC pilot. **No new AC, LP or battery redispatch calculation executed.**

## Source and battery contract

- The signed 16-case `StudyA_A0_A1_MatchedHardware_Full_v1/RUN_MANIFEST.json` chooses six exact case source CSV paths and SHA references. We re-read all **52,560 annual case-hours**, not 52,560 unique household timestamps.
- Original PyPSA PV/BESS model constants: inverter efficiency **0.95**, battery link charge and discharge efficiency **sqrt(0.95) = 0.97467943448** each way, DC-coupled PV, no grid-to-battery charging path, cyclic `Store`. The battery model uses **4.325 kWh energy per module**, while the archived `studya_106039_soc_shift_trial.py` explicitly maps a **5.12 kWh manufacturer-model nameplate and 20% physical minimum SOC** to residual modeled `Store` energy: `4.325 - (0.8 * 5.12) = 0.229 kWh per module`. This mapping is a **modelled manufacturer rule**, not new field certification. It refines the earlier provisional description of an unexplained empirical floor.
- We independently recomputed every hour of demand/inverter/import/export/ENS AC balance, PV/battery/inverter DC balance and cyclic storage transitions, including the Dec 31 to Jan 1 boundary. All six 8,760-hour originals satisfy those checks. Maximum absolute errors are about **1.01e-10 kW AC**, **1.43e-10 kW DC**, **1.44e-10 kWh** on storage transition. Zero export and zero ENS. Every source annual `Store` minimum equals precisely **0.229 kWh times module count** (within float rounding), and the maximum does not exceed **4.325 kWh times modules**. Original discharge and charge power stay within the signed per-case DC bank rating. This is a reference model algebraic audit, not a new battery hardware safety certificate.
- All **10 distinct failed-hour events** (20 PF .98/.95 case-hours) occur at that modeled 20%-SOC-corresponding store floor. Thus additional target-hour discharge requires rescheduling, a different source-energy profile, changed hardware or a changed AC network. No unsupported isolated inverter P injection is accepted.

## Single-source-donor preflight: previous 12 hours, night PF .95 proxy

For each of the ten failed hours, inspect original discharge at `t_donor` within the preceding 12 hours. Calculate a **maximum isolated single-hour DC discharge deferral**, subject to donor available original battery discharge, donor transformer **scalar PF .95 apparent-power proxy** after import substitution, maximum existing `Store` storage headroom throughout `[t_donor,t_target)`, target DC discharge power rating, inverter apparent-P nameplate and target import/no-export headroom. We do **not** sum donor maxima, which can share the same SOC storage headroom and cannot be treated as independently additive. Every bound is only an upper bound for a `DC source hour -> DC target hour` swap. A positive bound **does not prove** donor AC voltage or thermal feasibility, dispatch chronology under multiple shifts, model AC passing at target, realistic manufacturer charge current, or annual economics.

For a donor at hour `d` and target `t`, let `D_d` be original solar-bus DC discharge, `I_d` and `I_t` grid imports, `S_n` assumed transformer kVA, `Q_d=P_load,d*tan(acos(.95))`, `Emax=4.325*modules`, `E_k` original end-of-hour storage, and `eta_B=sqrt(.95)`. Then the isolated shift `x_dc` is bounded above by

```text
x_dc <= min(
  D_d,
  max(0, (sqrt(max(0, S_n^2 - Q_d^2)) - I_d) / 0.95),
  max(0, min_k(Emax - E_k) * eta_B), for donor <= k < target,
  max(0, DC_power_rating - D_t),
  max(0, (inverter_kVA - inverter_P_t) / 0.95),
  max(0, I_t / 0.95)
)
extra target AC inverter P <= 0.95 * x_dc
```

The donor scalar grid import bound **ignores AC feeder and transformer losses and their exact P/Q**, so it is a mathematical filter only. The AC PF .98 reference and PF .95 stress **must both be revalidated** if a schedule changes.

| Frozen source case | Failed 2025 hour | Largest single donor in prior 12h | Isolated DC shift upper [kW] | Extra target AC P upper [kW] | Positive donor count |
|---|---|---|---:|---:|---:|
| `A0_106039_ss90_to_A1` | 11-27 20:00 | 11-27 18:00 | 4.1888 | 3.9794 | 4 |
| `A0_113699_min_cost_to_A1` | 03-14 19:00 | 03-14 17:00 | 1.5864 | 1.5070 | 4 |
| `A0_113699_min_cost_to_A1` | 11-30 20:00 | 11-30 17:00 | 2.0310 | 1.9294 | 4 |
| `A0_113699_ss90_to_A1` | 03-14 19:00 | 03-14 17:00 | 1.5864 | 1.5070 | 4 |
| `A0_113699_ss90_to_A1` | 11-30 20:00 | 11-30 17:00 | 2.0310 | 1.9294 | 4 |
| `A1_106039_ss90_to_A0` | 11-27 20:00 | 11-27 18:00 | 4.4167 | 4.1959 | 4 |
| `A1_94022_min_cost_to_A0` | 03-28 20:00 | 03-28 15:00 | 1.1183 | 1.0624 | 4 |
| `A1_94022_min_cost_to_A0` | 11-27 20:00 | 11-27 13:00 | 0.1154 | 0.1096 | 1 |
| `A1_94022_ss90_to_A0` | 03-28 20:00 | 03-28 17:00 | 2.4624 | 2.3393 | 5 |
| `A1_94022_ss90_to_A0` | 11-27 20:00 | 11-27 17:00 | 1.9177 | 1.8218 | 3 |

All ten failures had **zero original PV DC curtailment during the preceding 12 source hours**. No net new PV energy is assumed in this donor-shift preflight. An actual design could need earlier-than-12h charging or PV/hardware redesign, but those require a distinct chronological optimization with full-year physical constraints.

## Main decision-changing observation

- **A0 target 94022, A1 min-cost hardware, 27 Nov 20:00:** only **0.115386 DC kW** original battery discharge is available to defer from the previous 12h, at 13:00. That supports at most **0.109617 kW** of isolated extra AC P by this mechanism. It is not yet known whether that small amount can restore the original-network voltage **0.943656 pu at PF .95** to the 0.95 pu research limit; **do not assume it can**. There is no original curtailed PV energy in that 12h. Prioritize physically valid network-route evidence, selective better hardware, or extended chronological optimization.
- **A0 target 94022, A1 SS90 hardware, 27 Nov 20:00:** best donor 17:00 with 1.917683 DC kW (up to 1.821798 AC kW), much more room for a conservative local candidate, but still no AC proof.
- **A1 target 113699:** source donor 17:00 on 14 Mar and 17:00 on 30 Nov, with isolated AC upper limits around 1.507049 and 1.929443 kW. The 3 kVA assumed transformer can limit permissible import during the donor hour; exact AC donor validation required.
- **106039 SS90 transfers:** 27 Nov 18:00 is a promising original positive-discharge donor, with isolated AC limits around 3.979375 (A0->A1) and 4.195897 kW (A1->A0), respectively, BEFORE exact donor/target AC and full-year SOC verification.

## Reproducibility, provenance and decision gate

Two additive source-only CSVs are attached to this audit: `RECIPROCAL_P1_SIX_ANNUAL_BATTERY_CLOSURE_2026-11-23.csv` (6 rows, one per frozen source), and `RECIPROCAL_P1_TEN_FAILED_EVENT_DONOR_CAP_2026-11-23.csv` (10 rows, one per distinct failed event). Both retain signed source file names and source SHA references, all keys and units. They are research registers, not pilot AC outputs. The prior `StudyA_Reciprocal12_P1_AC_Pilot_v1/` data and the user's untracked local v2 remain unchanged.

**Next experiment**: A bounded exact P-injection envelope on the two 94022 27 Nov cases and then 113699/106039, using original signed GIS, both PF factors, and the donor-hour AC as well as the failing target-hour AC. Test only modeled `x_dc` values within a proven source-only physical bound and preserve the real 8760-hour energy schedule by a same-hour-pair DC swap; then verify cyclic SOC, hardware limits and model AC at both changed hours. The accepted feasible schedule is NOT an original optimal LP result. If no passing schedule exists within donor constraints, identify equipment/connection upgrades rather than fabricated negative import, extra battery energy or a hypothetical conductor as installed.

**Unresolved:** actual EPM nameplates and phase/neutral/service routes, availability of same-day AC-valid donor P, possible failures in other annual hours and 85398/94022/113699 remaining unmatched P2/P3 reciprocal AC cases. This source-only screen cannot establish annual AC or physical/utility compliance. No original model or data, 36 AC CSVs, historic 702 AC source, main branch, or user-local untracked v2 changed.
