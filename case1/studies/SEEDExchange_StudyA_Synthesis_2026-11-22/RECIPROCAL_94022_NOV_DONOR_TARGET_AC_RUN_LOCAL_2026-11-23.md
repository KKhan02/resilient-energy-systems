# Study A | 94022 reciprocal 27 Nov donor-target AC pilot

**Prepared:** 23 November 2026. **Status:** local execution package, no numerical result claimed. **Authoritative audit source:** RECIPROCAL_P1_SOURCE_ONLY_SOC_AND_DONOR_SCREEN_2026-11-23.md, independently generated from the six frozen 8760-hour reciprocal source dispatches and the P1 36-case-hour AC pilot.

## Exact experimental question

Can the original A0 ten-house 94022 network and *unchanged equipment* from the two A1 hardware donor portfolios correct its **2025-11-27 20:00** night undervoltage by shifting battery discharge from an earlier hour, while satisfying original chronological 2025 SOC, 20% model physical floor, DC/AC balance, zero export/no ENS, and approved nominal PF .98 and stress PF .95 **at both the donor hour and the failing target hour**?

This is **NOT** an annual AC validation, PV/BESS resizer, tariff-approved cost result, manufacturer certification, or a claim about the actual EPM utility routing, phase and conductor status. The earlier 2025-03-28 20:00 94022 voltage failure remains even if this experiment succeeds.

## Frozen source cases and transfer bounds

| Frozen case | Donor | Target | Independent source-only max one-donor deferral | Inverter P upper |
|---|---|---|---:|---:|
| A1_94022_min_cost_to_A0 | 2025-11-27 13:00 | 2025-11-27 20:00 | 0.1153860326 kW DC | 0.1096167310 kW AC |
| A1_94022_ss90_to_A0 | 2025-11-27 17:00 | 2025-11-27 20:00 | 1.9176825037 kW DC | 1.8217983785 kW AC |

Each bound is rederived from the frozen 8760-hour target-energy CSV at PF .95 based on transformer **scalar import headroom**, intervening battery Store capacity, maximum original donor DC discharge, target battery power, inverter nameplate and target import headroom. Exact pandapower losses, voltage and feeder constraints **are not in the scalar bound**. Even a proposed transfer below the scalar bound may cause a *new* donor-hour voltage or transformer failure.

Use five fixed screening fractions of the upper bound: **0%, 25%, 50%, 75%, 98%**. At 0% the network target AC result is compared against the uploaded original P1 AC result across voltage, transformer, line, losses, PCC apparent power and selected inverter Q. This is an explicit regression gate.

10 candidate 8760h schedules (two equipment cases times five fractions) each independently check every storage transition, including the cyclic 31 December to 1 January boundary, electrical active-power balance, DC coupling, battery charge/discharge current-power, original hardware, 20% source-model storage floor and year-end conditions. No new PV charging, grid charging, export, unserved load or energy is invented. The corrected dispatch is **not** a fresh PyPSA optimum and no claim of economic optimality is made.

Each candidate then invokes the original frozen GIS/pandapower AC model at **two different timestamps** (donor and target) and **two different household PF** values .98 and .95, totaling **40 AC case-hour evaluations** (10 x 2 x 2). The internal solver may execute more than 40 power flows due to Q search. Control is original daylight Q ratio .25, zero Q for zero PV availability, inverter at existing 'head' siting, service factor x1.0. Both donor and target must satisfy 0.95 to 1.05 pu and <=100% source-model transformer/line limits at both PFs for a conditional *local pair* pass.

## Commands: existing Miniforge checkout root, Windows CMD

The previously uploaded root results (including untracked local P1 v2 and older ZIP archives) must remain untouched. Run only if git pull can fast-forward without modifying any untracked conflicts.

~~~bat
git status --short
git fetch origin
git switch sync/seedexchange-local-2026-11-17
git pull --ff-only origin sync/seedexchange-local-2026-11-17

python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22" -p "test_matched16_94022_nov_soc_shift_ac.py" -v

python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_94022_nov_soc_shift_ac.py" --repo-root . --preflight-only
~~~

Expected **14** synthetic regression tests with OK, then a JSON receipt:

- status **SIGNED_94022_TWO_HARDWARE_DONOR_TARGET_PREFLIGHT_NO_SOLVES**
- case_count **2**
- candidate_count **10**
- planned_case_hour_AC_evaluations **40**
- actual_new_case_hour_AC_evaluations **0**
- donor source-bound reproductions near **0.1153860326** and **1.9176825037** DC kW
- main 2025 signed hardware and full individual-house load checks preserved.

Any failed test, changed SHA, source mismatch, year chronology, SOC or Q/regression gate means STOP and share the exact traceback. Do not edit original signed source, do not suppress the error or run new annual LP as a workaround.

## Bounded AC execution only after all checks pass

~~~bat
python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_94022_nov_soc_shift_ac.py" --repo-root . --run-local
~~~

The runner writes to the next nonexisting *new* root folder, normally **StudyA_94022_Nov_DonorTarget_AC_Shift_v1**:

- RUN_MANIFEST.json: complete/incomplete status, 40 case-hour records, 10 candidate source-energy validation receipts and local pair acceptance count.
- DONOR_TARGET_AC_40_CASEHOURS.csv: 10 candidates x PF .95/.98 x donor/target, source hashes, AC voltage, loading, PCC apparent power, inverter Q and loss values.
- PAIR_CANDIDATES_10.csv: each candidate's energy-valid and four-AC-points pass/fail classification.
- figures_diagnostic/minimum_voltage_vs_shift.png and transformer_loading_vs_shift.png: separate exploratory plots, not supervisor/validated final figures.

Completed status is **94022_NOV_TWO_PAIR_AC_SWEEP_COMPLETE_NOT_ANNUAL**. This status only says all 40 model case-hours were recorded. It is not a pass by itself. Inspect **local_pair_screen_pass_candidates** and the row-level failing causes. A candidate passes only when **all four** AC points pass. An error writes an INCOMPLETE manifest and, if present, PARTIAL_UNVERIFIED_AC_ROWS.csv; preserve it rather than silently restarting or overwriting.

## Receipt and archiving, only after a completed run

~~~bat
python -c "import json,csv,pathlib,hashlib; folders=sorted(pathlib.Path('.').glob('StudyA_94022_Nov_DonorTarget_AC_Shift_v*')); assert folders,'No experimental output'; p=folders[-1]; j=json.loads((p/'RUN_MANIFEST.json').read_text()); x=p/'DONOR_TARGET_AC_40_CASEHOURS.csv'; y=p/'PAIR_CANDIDATES_10.csv'; rows=list(csv.DictReader(x.open(newline=''))); cases=list(csv.DictReader(y.open(newline=''))); assert j['status']=='94022_NOV_TWO_PAIR_AC_SWEEP_COMPLETE_NOT_ANNUAL'; assert len(rows)==40 and len(cases)==10; assert j['actual_new_case_hour_AC_evaluations']==40 and j['tested_2025_annual_soc_schedules']==10; assert hashlib.sha256(x.read_bytes()).hexdigest()==j['ac_csv_sha256']; assert hashlib.sha256(y.read_bytes()).hexdigest()==j['candidate_summary_sha256']; assert j['annual_AC_verified'] is False; print('94022 NOV PAIR RECEIPT PASS',p,'Local 4/4-pass candidates:',j['local_pair_screen_pass_candidates'])"
~~~

Review git status first, then stage **only the new StudyA_94022_Nov_DonorTarget_AC_Shift_vN folder**, commit to the sync branch and push after fetching / integrating any intervening handover-only GitLab commits. Do not stage other untracked directories or overwrite their files. If rebase or untracked collisions appear, stop rather than force push/reset.

The published branch will be independently audited for signature, original-hour regression, pair AC pass/failure taxonomy and annual dispatch algebra. Only after a source-consistent AC-corrected choice should we consider a full-year 94022 AC campaign. The other five case families, the other 94022 night, actual conductor ratings/phases/routing and Study B/C remain open under the agreed scope; northern 25-kVA transformer 137468 remains excluded.
