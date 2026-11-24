# Study A | 94022 A0 ten-house reciprocal SS90 combined March/November annual AC runbook

**Prepared:** 24 November 2026. **Status:** code and synthetic tests published, no new annual AC result yet. **Approved research scope:** A first, original provisional mapped 94022 LV, original different 2025 household stochastic traces and NASA PV, 5 kVA model hypothesis, original battery/hardware signed sources, 0.95–1.05 pu main research voltage range and 100% transformer/conductor thermal. PF .98 reference, .95 and 1.00 sensitivity (1.00 is not part of this immediate 2-PF source-archived validation). Field EPM nameplate/phase/conductor/service route approval remains unverified.

## Motivation and frozen corrected candidate

The uploaded combined two-event pilot **StudyA_94022_MarNov_SS90_DonorTarget_AC_Shift_v1/** passed 8/8 sampled AC cases by preserving November's prior 4/4 AC and correcting March's 4/4, after 2025 cyclic manufacturer SOC, inverter/battery P, grid imports and source power-energy validations:

- **2025-03-28 17:00 → 20:00:** defer **1.2312213377 kW DC** (50% of original March donor 2.4624426754 kW). This adds **1.169660270815 kW AC** to March evening.
- **2025-11-27 17:00 → 20:00:** defer **1.879328853626 kW DC** (98% of original November donor 1.9176825037 kW). This adds **1.7853624109447 kW AC** to November evening.
- Hardware **unchanged**, A1 original SS90 6 battery modules, approximately 10 kVA inverter, applied to original A0 10-house territory. 2025 original energy file \`StudyA_A0_A1_MatchedHardware_Full_v1/A1_94022_ss90_to_A0/energy_hourly_2025.csv\`, exact frozen SHA \`dc3ba1f9f6b3d9b0b750e2212f549ff8e1c351c44258233b8357577850374c93\`. No new grid-to-battery charging, unserved load or export. Annual original energy-only imports 4196.6064106846 kWh remain unchanged.
- User's uploaded November v1/v2 are identical repeats; v1 is pinned for archive evidence. Original historical archive and P1 remain immutable.

The user local code \`matched16_94022_ss90_mar_nov_annual_ac.py\` is a source-locked annual network validation, not new hardware investment optimization. **Why only four new corrected AC hours?** Original EPM/pandapower \`seed_study_a_v6.solve_ac_hour\` explicitly reassigns every individual house load, resets inverter Q to zero, solves each Q candidate with \`runpp(...init='flat')\` and recomputes current-hour voltage and loading, without stateful AC coupling across hours. Therefore, under *exactly the same model, GIS, equipment and source*, unchanged 2025 hours have identical AC P/Q input and are reusable. The runner requires the solver's source independence signature to match, computes **8,760 original AC case-hours** afresh, checks the original P1/March/Nov source baseline at four changed hours, computes **only four corrected AC case-hours**, verifies each against its previously accepted source sample, then creates two 8,760-hour hourly result CSVs:

1. \`ORIGINAL_2025_8760_AC.csv\`: entirely newly simulated original source P annual network.
2. \`CORRECTED_2025_8760_AC.csv\`: 8756 identical source original-hour AC values plus four freshly solved corrected-hour AC values from exact verified combined 8760-hour SOC source. This counts as a model-scope reconstructed annual AC only when every input, year timebase, AC solver stateless property and four source-archived regression signatures pass. Never claim 17,520 unique AC solves.
3. \`FOUR_CHANGED_AC_HOURS.csv\`: exact before/after AC P, min voltage, transformer loading, losses, source provenance and PF.

The runner independently validates annual voltage, line and transformer violations, convergence, extrema, optional strict 0.97–1.03 pu sensitivity, loss kWh, and corrected vs original AC loss delta equals the sum of those four hour changes. It does **not** reoptimize annual energy imports to include feeder losses, produce a Colombian tariff or certify real EPM cable/phase/nameplates. Separate diagnostic PNGs are created in \`figures_diagnostic\`.

## Commands to execute locally, Windows CMD / Miniforge Prompt

Start at the root of your existing cloned repository (with .git). Do not delete or \`git clean\` any untracked local output, ZIP archive, \`StudyA_Reciprocal12_P1_AC_Pilot_v2\` or local backup handover.

### 1. Pull latest code and audit notes

~~~bat
git branch --show-current
git status --short
git fetch origin
git pull --ff-only origin sync/seedexchange-local-2026-11-17
~~~

If the pull fails, share the exact output. Do not reset the working tree, force push, or move/overwrite untracked files.

### 2. Solver-free synthetic tests

~~~bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22" -p "test_matched16_94022_ss90_mar_nov_annual_ac.py" -v
~~~

Expected **12 tests, OK**. These tests do not solve new AC and cannot substitute for preflight.

### 3. Strict source/model preflight at PF .98 with zero annual AC calls

~~~bat
python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_94022_ss90_mar_nov_annual_ac.py" --repo-root . --pf 0.98 --preflight-only
~~~

Expected exact status:
\`SIGNED_94022_SS90_MAR50_NOV98_ANNUAL_AC_PREFLIGHT_ZERO_NEW_AC\`.

Expected: 8,760 original 2025 source records, exactly four corrected source inverter P hours, original/signed annual source SHA, March source v1 five candidates with .50 8/8 paired pass, original Nov v1 .98 4/4, original P1 failure reproduction, original GIS household trace, original manufacturer 20% SOC mapping, unchanged annual imports and grid-to-battery prohibition; 8,760 original AC evaluations PLANNED, 4 new corrected AC evaluations PLANNED, **0 done** in preflight.

### 4. Run the first annual PF .98 network AC comparison only after PASS

~~~bat
python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_94022_ss90_mar_nov_annual_ac.py" --repo-root . --pf 0.98 --run-local
~~~

A new output folder is selected, normally \`StudyA_94022_SS90_MarNov_AnnualAC_PF98_v1\`. No existing output is overwritten.

The runner prints updates at 500-hour intervals. It saves \`RUN_MANIFEST.json\` with INCOMPLETE status until finished. It also saves a clearly marked partial AC checkpoint every 500 hours. If the run fails, **do not archive partial results as complete or rerun immediately**. Share the failure and the saved manifest for targeted debugging.

A complete run records one of:
- \`ANNUAL_94022_SS90_MARCH50_NOV98_PF98_COMPLETE_MAIN_BAND_PASS\`
- \`ANNUAL_94022_SS90_MARCH50_NOV98_PF98_COMPLETE_VIOLATIONS_RECORDED\`
- \`ANNUAL_94022_SS90_MARCH50_NOV98_PF98_NONCONVERGED_DO_NOT_CLAIM\`

A violations-reported status is a valid diagnostic result, not a failed script. Only \`COMPLETE_MAIN_BAND_PASS\` means the corrected 2025 hourly modeled main-band AC screen was fully passing under the **PF .98 original service-length-1.0 provisional research network**. No outcome automatically implies PF .95, optional strict band or actual EPM feasibility.

### 5. Receipt verification and exact result-only push

For a completed run, from the root:

~~~bat
python -c "import pathlib,json,csv,hashlib; fs=sorted(pathlib.Path('.').glob('StudyA_94022_SS90_MarNov_AnnualAC_PF98_v*')); assert fs,'Missing annual PF98 output'; p=fs[-1]; j=json.loads((p/'RUN_MANIFEST.json').read_text()); assert j['status'].startswith('ANNUAL_94022_SS90_MARCH50_NOV98_PF98_') and 'INCOMPLETE' not in j['status']; assert j['new_original_AC_case_hours']==8760 and j['new_corrected_AC_case_hours']==4; names=['ORIGINAL_2025_8760_AC.csv','CORRECTED_2025_8760_AC.csv','FOUR_CHANGED_AC_HOURS.csv']; counts=[8760,8760,4]; assert all(sum(1 for _ in csv.DictReader((p/n).open(newline='')))==k for n,k in zip(names,counts)); assert all(hashlib.sha256((p/n).read_bytes()).hexdigest()==j['outputs_sha256'][n] for n in names); print('94022 ANNUAL PF98 RECEIPT PASS',p,'Original failures:',j['original_annual_summary']['main_band_infeasible_hours'],'Corrected failures:',j['corrected_annual_summary']['main_band_infeasible_hours'],'Nonconverged:',j['corrected_annual_summary']['nonconverged_hours'],'AC losses delta kWh:',j['annual_ac_loss_delta_kwh'])"
~~~

Then substitute actual printed output folder (v1 if unused) in:

~~~bat
git status --short
git add -- StudyA_94022_SS90_MarNov_AnnualAC_PF98_v1
git diff --cached --stat
git commit -m "Archive 94022 SS90 March-November full-year AC PF98 comparison [ci skip]"
git fetch origin
git rebase origin/sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
~~~

Stage **only** the actual completed result folder. The old P1 v2 and other untracked artifacts are unrelated and remain untouched. If push is rejected, fetch and rebase; if rebase reports conflict or untracked collision, stop and share. Do not force push.

## Subsequent research after independent remote audit

The next sensitivity is exact **PF .95** at original service x1.0. The same runner supports \`--pf 0.95\` and produces distinct \`StudyA_94022_SS90_MarNov_AnnualAC_PF95_vN\`, with no rerunning PF .98. Hold PF .95 until PF .98 annual violation and loss patterns are audited, because PF .95 can only worsen some thermal/voltage metrics and the 8/8 two-date pass does not prove annual. Later service multipliers x1.3/x1.6 and optional PF1 and strict band are separate controlled studies.

If the new PF .98 annual scan reveals other failed source hours, do **not** claim the four-hour correction fixes the entire year. Prioritize exact failed-hour diagnosis, chronology-constrained redispatch or actual nameplate/line-route evidence. Do not redo 6,840 investment cases or previous 36/40/20 sampled AC pilots.

User local 14 Nov synthetic + 8 Mar-Nov synthetic test receipts remain unreported; the new 12 annual synthetic test suite and preflight remain pending at the time of this package. Nothing touches \`main\`, signed original data or user-local ZIP files.
