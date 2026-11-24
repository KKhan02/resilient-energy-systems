# Study A | 94022 SS90 combined 28 March plus 27 November source-SOC AC test

**Date prepared:** 24 November 2026. **Status:** runbook and local runner committed, **not yet executed locally**. The preceding independent 40-casehour November pilot audit is \`RECIPROCAL_94022_NOV_40AC_TWO_RUNS_INDEPENDENT_AUDIT_2026-11-24.md\`.

## Goal and exact source

Keep the **original A0 10-house GIS territory at transformer 94022**, with **A1-origin SS90 original equipment** (6 battery modules and about 10 kVA inverter) and source 2025 demand/PV/annual battery dispatch. Main band is 0.95...1.05 pu, line/transformer <=100%, PF 0.98 and 0.95, original service-length factor 1.0 and original phase/network proxies. This is not a utility-certified grid map.

The **27 Nov 2025 17:00 to 20:00** battery shift is held constant at **1.879328853626 kW DC**, generating +**1.7853624109447 kW AC** at the evening target. Original archive \`StudyA_94022_Nov_DonorTarget_AC_Shift_v1\` already demonstrates 4/4 main-band AC passes at that donor/target pair with this precise frozen transfer (the uploaded v2 is an identical repeat).

The **other 94022 source failure** on **28 Mar 2025 at 20:00** has original minimum voltage **0.9499715541 pu at PF 0.98** and **0.9471409072 pu at PF 0.95**. Signed source-only best individual donor is **17:00 of 28 Mar**, with maximum **2.4624426754 kW DC** (up to 2.3393205416 kW AC at target). It originally has some PV at 17:00 and 2.46244 DC kW battery discharge; Q remains governed by the existing daytime PV-based controller. Shift fractions 0, 25, 50, 75 and 98% of this isolated limit are tested.

All five proposed March fractions are applied **after** the fixed November accepted transfer. The trial recalculates every 8760h storage state and DC/AC source-energy balance for each combined schedule. It reuses the four November AC points only after checking the exact individual household trace, saved GIS model and unchanged 17:00/20:00 November inverter P. Exactly **20 NEW AC case-hour evaluations** are planned (5 candidates x 2 PF x March donor/target). No additional new November AC run or full 2025 AC campaign.

A candidate's \`two_dates_eight_of_eight_local_ac_pass\` means 4 previous November plus 4 new March modeled AC screens pass, with combined annual SOC/energy constraints. It is **NOT** proof that every 2025 hour passes AC, that 0.97...1.03 pu strict sensitivity passes, or that hardware, EPM conductor/routes/transformer are field-approved.

## Commands, Miniforge Prompt from the real repository root

### Step 1: synchronize code safely

The user's earlier untracked \`StudyA_Reciprocal12_P1_AC_Pilot_v2\`, multiple old ZIPs, other PV results and \`PROJECT_HANDOVER_LIVE_v7.md\` must be preserved. Do not use \`git clean\`, \`reset --hard\`, force pushes or blanket \`git add .\`.

~~~bat
git branch --show-current
git status --short
git fetch origin
git switch sync/seedexchange-local-2026-11-17
git pull --ff-only origin sync/seedexchange-local-2026-11-17
~~~

If the pull fails because branch diverged, a tracked file conflicts, or untracked files collide, STOP and report status before changing anything.

### Step 2: test both source-transfer and combined two-event guard code

~~~bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22" -p "test_matched16_94022_nov_soc_shift_ac.py" -v

python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22" -p "test_matched16_94022_mar_nov_ss90_ac.py" -v
~~~

Expect **14** and **8** synthetic tests respectively, each reporting \`OK\`. These do not run pandapower. Stop if any test fails. The runner has been source-reviewed remotely, but no user-local test result is yet claimed.

### Step 3: signed no-AC preflight

~~~bat
python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_94022_mar_nov_ss90_ac.py" --repo-root . --preflight-only
~~~

The status must be:

\`SIGNED_94022_SS90_MARCH_PLUS_NOV_PREFLIGHT_NO_SOLVES\`

Receipt must report:
- exact signed A0 ten-house GIS and A1 SS90 original hardware source;
- prior November v1 completed, 40 old case-hours, unique 98% 4/4 passing record;
- March original PF .98 and .95 target baseline fail at old P=0;
- recomputed March donor upper bound about 2.4624426754 kW DC;
- November fixed 1.879328853626 DC kW and four identical archived AC-P source points;
- 20 planned new March AC hours, 0 actual in preflight;
- annual combined November source SOC and cyclic energy validated, 0 new AC.

### Step 4: perform bounded paired-hour AC only after both tests and preflight PASS

~~~bat
python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_94022_mar_nov_ss90_ac.py" --repo-root . --run-local
~~~

Expected new output version directory:

\`StudyA_94022_MarNov_SS90_DonorTarget_AC_Shift_v1\`

If that path already exists, the runner selects the next unused version. No prior output is overwritten.

Completed manifest status:

\`94022_SS90_MARCH_PLUS_NOV_TWO_EVENT_LOCAL_AC_20_COMPLETE_NOT_ANNUAL\`

Contains:
- \`MARCH_DONOR_TARGET_20_AC_CASEHOURS.csv\` with exact GIS AC voltage, transformer and line loading, inverter Q and losses at both March timestamps/PFs;
- \`MARCH_CANDIDATES_5.csv\`, including March 4/4 and combined March+Nov 8/8 local AC classification per candidate;
- \`RUN_MANIFEST.json\` including source SHA, method parameters, annual SOC validity, internal AC count distinction and explicitly annual_AC_verified=false;
- two exploratory figures in \`figures_diagnostic/\`, separate from eventual presentation-grade plots.

If the solver errors, it preserves an INCOMPLETE manifest and partial unverified rows. Do not claim the 20 cases passed just because a folder exists.

### Step 5: verify and archive only the finished version

~~~bat
python -c "import pathlib,json,csv,hashlib; fs=sorted(pathlib.Path('.').glob('StudyA_94022_MarNov_SS90_DonorTarget_AC_Shift_v*')); assert fs,'Missing March-Nov output folder'; p=fs[-1]; j=json.loads((p/'RUN_MANIFEST.json').read_text()); a=p/'MARCH_DONOR_TARGET_20_AC_CASEHOURS.csv'; c=p/'MARCH_CANDIDATES_5.csv'; rr=list(csv.DictReader(a.open(newline=''))); ss=list(csv.DictReader(c.open(newline=''))); assert j['status']=='94022_SS90_MARCH_PLUS_NOV_TWO_EVENT_LOCAL_AC_20_COMPLETE_NOT_ANNUAL'; assert len(rr)==20 and len(ss)==5; assert j['new_pandapower_AC_case_hour_evaluations']==20; assert hashlib.sha256(a.read_bytes()).hexdigest()==j['march_ac_csv_sha256']; assert hashlib.sha256(c.read_bytes()).hexdigest()==j['candidate_csv_sha256']; assert j['annual_AC_verified'] is False; print('MARCH NOV 94022 RECEIPT PASS:',p,'March pairs passing:',j['March_pair_pass_candidates'],'Both dates 8of8:',j['combined_two_event_eight_of_eight_pass_candidates'])"
~~~

When passed, substitute the **actual** version from that receipt into the following commands, for example for v1:

~~~bat
git status --short
git add -- StudyA_94022_MarNov_SS90_DonorTarget_AC_Shift_v1
git diff --cached --stat
git commit -m "Archive 94022 combined March-November SS90 AC pilot [ci skip]"
git fetch origin
git rebase origin/sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
~~~

Never add other untracked outputs by accident. If the rebase reports conflicts, STOP and share them. No force push or reset. The fresh remote March results will be independently audited, with the rolling handover updated afterwards.

## Decision at that point

- If one March candidate passes all four new AC hours, then that combined 2025 storage trajectory has two date-specific (November and March) source-consistent passing sampled AC pairs. The remaining **8760-hour AC** and uncertainty bands still need a source-pinned revalidation. Do not re-solve full-year energy or rerun hundreds of historical hardware variants without materiality.
- If March donors fail due to added evening import, the 2-event SS90 schedule is not locally feasible by this exact single-donor method; choose another donor/higher-chronology/PF controls or material hardware/verified route evidence. No EPM nameplate or surveyed path is inferred.
- The original A1 min-cost case already failed every prior November donor shift and is not silently included in the two-day SS90 candidate.

No historical signed archive, user-local untracked v2, \`main\`, or current November v1/v2 outputs have been changed.
