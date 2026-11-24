# Study A | independent forensic audit of 94022 November donor/target AC sweep v1 and v2

**Audit dated:** 24 November 2026. **Archive commit:** d08b8f6d8118b48dca862988ba43739084a8312d. **Branch:** sync/seedexchange-local-2026-11-17. **Status:** INDEPENDENT UPLOADED-RESULT AUDIT COMPLETE; ONE LOCAL PAIR FEASIBLE, ANNUAL AC AND FIELD FEASIBILITY UNDETERMINED.

## Archive and hash verification

- Both folders, \`StudyA_94022_Nov_DonorTarget_AC_Shift_v1\` and \`v2\`, are present on GitLab. Their Git tree IDs are identical. All five tracked file blobs are identical byte-for-byte between folders: RUN_MANIFEST.json, DONOR_TARGET_AC_40_CASEHOURS.csv, PAIR_CANDIDATES_10.csv, and two separate exploratory PNGs. These are **repeat runs with identical outputs**, not 80 distinct scenarios or independent uncertainty realizations.
- Each manifest has the exact status \`94022_NOV_TWO_PAIR_AC_SWEEP_COMPLETE_NOT_ANNUAL\`, 40 case-hour entries, 40 converged, 16 failing the main AC screen, 10 candidate fixed-hardware schedules tested against original 8760-hour battery/source checks, **one candidate passes all four local AC points**. There were no nonconverged AC case-hours, over-voltage, line overload or transformer overload in these 40 records. The 16 violations were all \`min_v_pu <0.95\` **at target 20:00**. The donor hour always passed the main band.
- Independently recomputed the CSV content SHA-256 against GitLab blob metadata. Git uses LF line endings (\`DONOR_TARGET_AC_40_CASEHOURS.csv\` Git SHA a14fcc574819fecba22b8647edd8a31a82dd613311bce88482261fe52c6fe3b8 and \`PAIR_CANDIDATES_10.csv\` Git SHA d37709d40861329b8614df6ca7513246f4e625bd389fc48ff19be180d2109c52). Replacing only LF with CRLF and hashing reproduces **exactly** the saved manifest hashes ce0f69511cc26e858ea53e72c6ff342dc692e86c5bd9ea6247d3ef14858905b8 and 2f5c5712a04d4032e35421bc0ebf98618113d18424244bceb0e142922abc28b9, respectively. This is Git normalization, not corrupt data.
- GitLab file metadata independently agrees with both manifest diagnostic PNG SHA hashes: minimum_voltage_vs_shift.png = deaf37431223e35c3e36b9c90ba0155463c8d1e70fae009934a88a818b5c80f2; transformer_loading_vs_shift.png = 001692d81110cea7260b3477ee0b56f2397131ec45f40ce00e19a075fe371561.
- The baseline 0% transfer replicates the P1 archived 27 November PF .98 and .95 network AC result. The source SHA references remain the original frozen A1-origin hardware to A0 ten-house target, not a genuine physical reassignment attested by EPM.

## Main numerical result at 2025-11-27 20:00

Five sampled shift fractions = 0%, 25%, 50%, 75% and 98% of each case's isolated 12-hour single-donor DC limit; two PF values .98/.95; two stages donor/target. That gives 10 candidate schedules times four local AC case-hour screens.

| A1-origin hardware on A0 ten-house 94022 | Share of individual DC source donor limit | Added 20:00 inverter AC power [kW] | Target minimum V at PF .98 [pu] | Target minimum V at PF .95 [pu] | Pair AC pass (4/4) |
|---|---:|---:|---:|---:|---|
| Min cost | 0% | 0 | 0.946770273 | 0.943656335 | NO |
| Min cost | 25% | 0.027404183 | 0.946879360 | 0.943765837 | NO |
| Min cost | 50% | 0.054808365 | 0.946988404 | 0.943875295 | NO |
| Min cost | 75% | 0.082212548 | 0.947097402 | 0.943984708 | NO |
| Min cost | 98% | 0.107424396 | 0.947197642 | 0.944085329 | NO |
| SS90 | 0% | 0 | 0.946770273 | 0.943656335 | NO |
| SS90 | 25% | 0.455449595 | 0.948577524 | 0.945470687 | NO |
| SS90 | 50% | 0.910899189 | 0.950372636 | 0.947272469 | NO, PF .95 target |
| SS90 | 75% | 1.366348784 | 0.952155773 | 0.949062157 | NO, PF .95 target |
| **SS90** | **98%** | **1.785362411** | **0.953785819** | **0.950698127** | **YES, both PF and hours** |

Only **SS90 with 98% of its isolated donor limit** passes all four modeled main-band AC screens. PF .95 target voltage margin = +0.000698127 pu above the 0.950000 threshold, a narrow research margin (0.0698% of nominal voltage). This is **not** a safe field design margin or robustness certification. PF .98 at 50%/75% passes target but PF .95 remains below limit.

For the passing SS90 98% shift, 2025-11-27 **17:00 donor** and **20:00 target**, including original conditional AC Q controller:

| Timestamp | PF | Min V [pu] | Max transformer [%] | Selected inverter Q [kVAr] | AC feasibility |
|---|---:|---:|---:|---:|---|
| 17:00 donor | 0.98 | 0.968693355 | 56.194145 | +0.181077573 | PASS |
| 17:00 donor | 0.95 | 0.967196632 | 57.512291 | +0.286247700 | PASS |
| 20:00 target | 0.98 | 0.953785819 | 55.483886 | 0 (night Q disabled) | PASS |
| 20:00 target | 0.95 | 0.950698127 | 60.458823 | 0 (night Q disabled) | PASS |

**Important strict-band sensitivity:** At the optional **0.97..1.03 pu** voltage screen, both corrected SS90 donor-hour PF results fail 0.97 minimum (0.968693 and 0.967197), despite the four MAIN-band checks passing. At the original November 20:00 target, main and optional strict both differ; only the former is the stated A feasibility test. A 1.3/1.6 service-length perturbation or new phase/line routing could erase the narrow PF .95 target margin; no such 94022 uncertainty run is yet archived for the newly corrected schedule.

## Independently reconstructed 8760-hour annual schedule consistency

Reopened the two **original, frozen 8760-hour** source energy CSVs from the matched 16-case manifest and reconstructed the full 2025 battery transfer at the **98%** fraction for BOTH equipment tiers without any new PyPSA or pandapower run. The winning SS90 case uses:
- Original 17:00 DC battery discharge: 1.9176825037 kW; defer 1.879328853626 kW, leaving 0.038353650074 DC kW. This raises 17:00 original grid import from 0.8739641385 to **2.6593265494447 kW**.
- At 20:00, extra DC battery discharge 1.879328853626 kW yields inverter AC = **1.7853624109447 kW**; original 20:00 grid import **4.2221422722** becomes **2.4367798612553 kW**. No new PV energy is assumed.
- Incremental intervening stored-energy retention = 1.879328853626 / sqrt(.95) kWh. After the 20:00 sink, the source original storage trajectory is restored exactly. Annual grid imports, annual battery discharged DC energy and year-end state are unchanged (within floating-point precision).
- Full source-year 8760 h checks, including Dec 31/Jan 1 cyclic boundary, independently returned maximum AC closure error ~1.00e-10 kW, DC closure ~1.42e-10 kW, storage transition error ~1.41e-10 kWh; minimum stored energy **1.374 kWh**, maximum **25.95 kWh**, both same as the original 6-battery module bounds. No unserved load or export. The min-cost 98% proposal likewise preserves its algebraic SOC trajectory (min 1.145 and max 21.625 kWh) but **still violates target AC voltage**.
- Annual **energy-only** import kWh is unchanged, but AC conductor losses differ at donor/target and have not been assessed across the full 8760h. No unchanged annual loss-adjusted economics, tariff or energy-trading compliance follows.

## Decision, scope and next gate

**Decision:** Prefer the archived **SS90 original hardware** over the min-cost original hardware **for a bounded same-day November voltage-correction candidate on this specific A0 94022 assumed ten-house network**, because the former has one 4/4 sample pass with chronological SOC. This does NOT establish that the min-cost hardware is inherently nonviable: the only tested way to shift energy was a **single previous-12-hour donor** at 13:00, with at most 0.115386 DC kW. Alternative annual SOC schedules, changed PV/inverter hardware and verified LV routing remain open.

**Next decision-changing test: 2025-03-28 20:00.** Both SS90 and min-cost original reciprocal P1 portfolios fail the 94022 target at this second night. The source donor preflight suggests isolated best earlier donor 17:00 for SS90, max 2.4624426754 DC kW (2.3393205416 AC kW). A new **combined two-day, fixed-SS90-hardware annual SOC source** should preserve the already passing 27-Nov 17:00-to-20:00 transfer and apply a separately bounded 28-Mar donor-to-target pair. The two day-event windows do not overlap, but the **entire combined annual schedule must still be revalidated**. Use the approved PF .98/.95 original AC model at both March donor and target; retain the existing November four AC results only when exact source P, Q capability and GIS unchanged. If March corrects, it is eight **sampled** AC case-hours across two days, not annual AC. Then choose a targeted annual AC replay with changed hour rechecks and previous annual-source input parity (where available) or a fresh annual scan if the old annual original source is not identical.
 
**Research caveats:** Existing 94022 GIS is provisional. Transformer is 5 kVA study assumption, house phases, service routes and conductor installation are not independently certified; original source year is NASA synthetic irradiance plus seeded synthetic household demand, not observed meter. No original archived 36 case-hour or annual run was overwritten. Both run folders are preserved, and local untracked P1 v2 and other user files have not been touched. The user's latest 14 synthetic test console output was not directly supplied, so do not claim we independently observed that test suite passing, even though run manifests report completed experiments.
