# Study A | reciprocal 12 unarchived-original AC families: numerical materiality and next gates

**Date:** 23 November 2026. **Method:** independent read-only GitLab source review of 12 signed 8,760-hour optimized energy cases. **Status:** prior to the new user's local 12-case SHA revalidation. No new AC, PyPSA, line/conductor or hardware optimizer runs.

## Source population and scope

The fully signed 16-case reciprocal annual energy portfolio exchanges fixed equipment between the original **A0** and geographic-nearest **A1** household groups. Its four original AC source-family matches are already separately archived and audited. The remaining **12** have exact validated energy schedules but no same-hardware/same-household/same-P original archived 8,760-hour AC source. These cases cover four territories, with **four at 94022, four at 113699, two at 106039 and two at 85398**. Twelve signed original energy series contain **105,120** source-case-hour records; do not read this as 105,120 unique annual community hours.

The attached `RECIPROCAL12_REMOTE_NIGHT_PROXY_AUDIT_2026-11-23.csv` contains the 12 case signatures, equipment origins, source annual grid imports, maximum nighttime PF .95 source apparent-power estimates and evidence-based preliminary priority bands. This table was independently derived from the saved GitLab 2025 input CSVs. The newly authored `matched16_reciprocal12_materiality.py` verifies all 12 local source hashes again and generates a reproducible report, 25 source-selected hour targets per reciprocal case, and a new signed receipt. That Python implementation has **not yet** been run locally.

## Important limits of the night-PCC proxy

For each 2025 hour with PV availability zero (4,353 hours in each annual source), assume the archived inverter's own Q control is off. Ignoring feeder losses and transformer excitation, compute `S_proxy = hypot(grid_import_kW, demand_kW * tan(acos(PF)))`. This adds load reactive demand at either PF .98 or stress PF .95. At solar-daylight hours the unknown inverter Q changes the PCC S, so this night-only metric must not be transferred to daylight or treated as a solved AC network result. The original source transformer ratings of 5 kVA (94022,106039,85398) or 3 kVA (113699) are **model assumptions**, not evidenced EPM nameplates. The same original hourly loads are synthetic 2025 traces, not measured meter histories.

**Two nighttime PF .95 proxy exceedances were found across the 12 target source cases**, both on transformer 106039 at **27 November 2025, 20:00 local standard time**:

- `A0_106039_ss90_to_A1`: `5.0988288428 kVA` versus assumed 5 kVA, approx **1.98%** above the source screening capacity.
- `A1_106039_ss90_to_A0`: `5.1765998799 kVA` versus assumed 5 kVA, approx **3.53%** above the source screening capacity.

PF .98 night proxy has zero >100% hours across these 12 schedules, though the second 106039 case reaches approx **5.00000000004 kVA** at its peak. This is a model-input warning and **not proof** that pandapower will converge or that a real transformer will overload. Conversely no night proxy exceedance does not prove there are no voltage, phase, conductor or actual AC loading problems.

## Priorities for the 12 unmatched original source families

| Priority | Case families | Reason and decision |
|---|---|---|
| **P1: 94022 original A0 target** | `A1_94022_{min_cost,ss90}_to_A0` (two) | Ten-house A0 proposed feeder has known under-voltage. Original A0 min-cost/SS90 PF .98 length1 archived source AC has five/two failing hours respectively on DIFFERENT hardware. The prior A0 94022 sequenced SOC trials reduced but did not eliminate the original-network issues. The alternative five-branch resistance halving is entirely conditional and unbuilt. H01/H06 service wiring and material are unresolved. |
| **P1: 113699 nearest A1 target** | `A0_113699_{min_cost,ss90}_to_A1` (two) | Six-house assumed 3-kVA GIS feeder. Separate previous PF .98, length1 annual AC passes on A0/A1-origin equipment after annual SOC corrections; its PF .95 **25-hour sampled** sensitivity reported 12 factor-case under-voltage events at three dates. Those earlier results do not establish new reciprocal dispatch AC feasibility. |
| **P1: 106039 SS90** | `A0_106039_ss90_to_A1`, `A1_106039_ss90_to_A0` (two) | Each has one source nighttime PF .95 PCC proxy > assumed 5 kVA on 27 November at 20:00. That is a targeted PF stress condition. Existing 106039 corrected main-band result at PF/route extremes has only 0.0000077895 pu minimum voltage reserve, making network source uncertainty important. |
| **P2: 94022 nearest A1 target** | `A0_94022_{min_cost,ss90}_to_A1` (two) | Eight-house A1 mapped source AC has stronger original voltages than A0 for its own DIFFERENT native equipment; exact transferred hardware is not yet AC validated. |
| **P2: 85398 nearest A1 target** | `A0_85398_{min_cost,ss90}_to_A1` (two) | Five-house A1 H13 connection lacks EPM phase/service confirmation. The two already matched `A0_85398_*_ref` annual source pairs apply instead to A0 four-house targets, NOT to these A1 five-house cases. |
| **P3: 113699 original A0 target** | `A1_113699_{min_cost,ss90}_to_A0` (two) | Four-house source night proxy well below assumed 3 kVA; no exact four-house AC source exists. This does NOT establish feeder voltage or site wiring feasibility. |

## Prevent mistaken reuse of the 113699 annual AC evidence

The previously completed `StudyA_A0_A1_MatchedHardware_113699_AnnualAC_A0_v1` and `..._A1_v1` are two **annual A1 six-house** PF .98 length1 corrected-SOC AC runs, with 8,760 model research-band passes each and optional strict under-.97 pu hours 245 and 120 respectively. They use two frozen hardware families and a separately corrected schedule. Although the A0-origin 17-panel/3-battery/4.700939kW source hardware exactly matches `A0_113699_min_cost_to_A1`, an independent hourly comparison of that reciprocal target energy CSV to the subsequently corrected 113699 A0-origin SOC schedule found **188 changed inverter-P hours**, zero demand differences and approximately zero annual net P shift. Therefore the earlier passing AC cannot be directly reused as though it were the **uncorrected** reciprocal target's hourly AC replay. An intentionally approved corrected operating-schedule alternative is an independent result, not an identity replacement.

The earlier 25-hour 113699 sensitivity is a nonannual sample. Its PF .95 failures occur at `2025-03-14 19:00:00`, `2025-03-30 19:00:00` and `2025-11-30 20:00:00` across different origins and length settings. Treat these dates as **stress anchors for future targeted tests**, not necessarily failures of the 12 reciprocal original-energy schedules.

For 94022 the original archived A0 min-cost reference PF .98 length1 file has its worst household voltage **0.9467702727 pu** at `2025-11-27 20:00:00`, before using different same-hardware dispatch and without the hypothetical network improvement. The fixed five original-archive stress timestamps embedded in the 12-case script belong to THAT SOURCE, not to new reciprocal AC replay results.

## Next bounded gate, without new AC solves

Run `matched16_reciprocal12_materiality.py` from the actual GitLab sync checkout. It uses the already tested MAX_PATH-safe signed source parser, rejects missing or altered 2025 rows, preserves exact 12 original case IDs, checks source zero export/ENS and verified annual import sums, computes the nighttime PF .95/.98 proxy and returns **25 nonduplicated 2025 stress-hour timestamps per case**. The 300-hour selection prioritizes previous model stress anchors, target nighttime apparent-PCC peaks, gross load peaks, PV-availability peaks and grid-import peaks, with deterministic ties.

This is **source-hour selection only**: no unbalanced power flow, no 25-hour AC or annual AC run. It is not proof of worst-case AC behavior. The 300 target case-hours are not 300 unique geographical/historical times. Use the results to decide whether a **small first 106039/113699/94022 targeted AC experiment** can change the Study A A0/A1 decision, after reviewing EPM nameplate, service and phase uncertainty. New full-year matched-hardware AC studies remain conditional on an explicit decision need.

The corresponding full Miniforge command sequence, including initial `git fetch/pull` and final `git add/commit/push`, is in `RECIPROCAL12_SOURCE_MATERIALITY_RUN_LOCAL_2026-11-23.md`. No previous signed annual outputs or `main` changed. The separately repaired nine-test A0 P/Q synthetic suite has not yet been reported as passing user-locally, but its archived 36/702 AC replays were already independently audited; **do not rerun AC to fix a synthetic test**.
