# Study A A0 transformer 94022: sequenced redispatch trial and next network diagnostic

**Status:** Independently audited 16 November 2026. **Partial correction, not a feasibility pass.**

## 1. Exact source and scope

- Upload: `StudyA_A0_94022_Sequenced_Trial_v1.zip`, SHA-256 `88fa44a46fd67234b39d281b2dde341116bdab0af6ae6d5dbad2ee67a6b551d0`.
- Four independently dispatched 2025 annual schedules: archived A0 94022 min-cost and higher-SS equipment, each with optimized and causal modes; 8,760 hours each.
- One mapped LV topology with provisional service assignments. Nine sensitivity conditions are three PF values (0.95, 0.98, 1.00) times three service factors (1.0, 1.3, 1.6).
- Uploaded trial manifest: `PARTIAL_OR_UNRESOLVED`. Original signed annual source files remain unchanged. The user-run pandapower solver recalculated changed hours; the independent review verifies the numerical records and balances but **did not rerun pandapower**.

## 2. Verified result

| Design / dispatch | Applied shifts | Unresolved event keys | Violating case-hours before | After | Annual stress cases still failing |
|---|---:|---:|---:|---:|---:|
| Min-cost, causal | 33 | 9 | 120 | 39 | 8 |
| Min-cost, optimized | 32 | 9 | 119 | 39 | 8 |
| Higher-SS, causal | 7 | 7 | 34 | 24 | 8 |
| Higher-SS, optimized | 8 | 7 | 37 | 24 | 8 |
| **Total** | **80** | **32** | **310** | **126** | **32** |

- The trial reduces 94022 violating sensitivity-case hours by **184/310 = 59.35%**, while **all 32 original failing sensitivity cases still fail** at least one hour.
- All 1,368 recorded changed-hour AC calculations are converged/feasible. The lowest newly computed changed-hour voltage is **0.9500273055 pu**, leaving a narrow margin of **0.0000273 pu**. Peak transformer loading in those changed-hour records is **79.599%**; these are *changed-hour* extrema, not unconditional full-year network extrema.
- The four candidate annual CSVs have 8,760 contiguous timestamps, valid SHA-256 hashes, DC and AC hourly energy balance, SOC recurrence, zero grid export and unserved load, and unchanged original annual grid imports, solar curtailment and end-of-year SOC. These shifts do **not** increase annual PV utilization.
- The 32 unresolved schedule-event keys involve only **nine distinct local clock timestamps**. These nine are not nine separately sampled years, and a timestamp can belong to multiple hardware/dispatch cases.

## 3. What the nine persistent hours reveal

The independent source extract `A0_94022_9_DISTINCT_RESIDUAL_HOURS.csv` maps all nine timestamps. On **24 September 19:00 and 20:00, 29 September 20:00, and 26 October 20:00**, all four configurations have **zero active grid import** at the failing hour while the minimum household voltage is 0.94906, 0.94444, 0.94477 and 0.94835 pu, respectively. Their transformer loading is only about 29–34%.

This is critical: under the current **one shared inverter at the transformer head** and **no-export** policy, further head-end battery discharge cannot reduce grid import below zero. A large battery at that same point will not by itself address those individual end-of-feeder undervoltages. Network location and assumptions must be examined, rather than assuming that additional storage is sufficient.

On 28 March 20:00, 27 November 20:00, and 29 November 19:00/20:00, substantial active grid imports remain and minimum voltage is about 0.937–0.940 pu. Some same-day donor moves were AC-rejected or had insufficient usable earlier discharge. A joint, multiple-hour SOC/AC optimization **might** help, but cannot be inferred as feasible from this sequential heuristic's failures.

A *zero net import* at the transformer does not mean household branch currents are zero. Local demand and a centralized inverter can create voltage drops along the intervening LV sections. Further evidence is needed for the limiting houses, individual line voltages, conductor assumptions and site interconnection points.

## 4. Correct portfolio accounting

The prior independently reconciled portfolio had **376 passing and 56 failing annual sensitivity cases (432 total)**, with **1,248** summed scenario-violation-hours across the 56 failing cases. Applying this validated *partial* 94022 trial as a separate overlay changes that latter count to **1,064** without changing the 56 failing-case count.

- A0 94022 mapped LV: 32 failing annual AC scenarios, **126** remaining violation case-hours.
- A0 92395 proposed MST: 24 failing annual AC scenarios, **938** remaining violation case-hours.
- A1, A0 106039 and all remaining designs: zero failing cases in the tested grid after their previous corrections.

An exact 432-case overlay is in `STUDYA_432_POST_A0_94022_PARTIAL_OVERLAY.csv`. It **does not overwrite** original electrical results or incorrectly promote partial candidates to feasible.

## 5. Next controlled research experiment

Use `probe_94022_network_options.py` only as a **targeted diagnostic**, not a final investment option. It keeps the same proven equipment, battery SOC schedules and individual household loads, and retests the nine residual timestamps under two first-pass PF/length conditions:

- **Head reference** to reproduce the signed AC model or final corrected changed-hour evidence.
- **Middle / farthest-house bus siting proxies** to test the sensitivity to changing the common inverter's electrical connection point.
- **Head resistance multipliers 0.75 and 0.50** applied to the modelled LV lines as *artificial resistance sensitivities*, not selected real cable types, measured field data, or fully costed upgrades.

For each trial the script records the limiting household, bus voltage, transformer loading, line loading and AC feasibility. The head case must reproduce saved numerical evidence within a tight tolerance. Default is 4 annual schedules × 9 timestamps × 2 PF/length pairs × 5 model variants = **360 targeted AC calculations**. A `--all-nine` switch increases coverage after reviewing the initial outcomes. No 8,760-hour numerical replays are repeated.

A promising targeted result needs follow-up full-year AC screening, equipment location feasibility, conductor and installation cost assessment, field-confirmed transformer capacities and real phase allocation. The network screen must not silently replace the original A0 scenario.

## 6. Broader research priorities

1. Correct the narrative figures for the **partial** A0 94022 result only after choosing how to distinguish original, successful A1 and partial A0 evidence. Do not show A0 as fully feasible.
2. Retain A0 92395 MST for Study B topology/conductor optimization, rather than forcing head-end redispatch to resolve geographically driven voltage drops.
3. Keep PV utilization, optimal battery sizing, charge/discharge kW, inverter nameplate and loss-aware economic frontier as an independent optimization. Current accepted shifts preserve annual curtailment.
4. Check robustness beyond near-threshold AC model passes, especially because household connections, phase imbalance, conductor values and inverter operating policies are assumptions.
5. Full outage resilience and critical-load backup still require separate definitions and design evidence.

No GitLab commits or changes to original signed simulation outputs.
