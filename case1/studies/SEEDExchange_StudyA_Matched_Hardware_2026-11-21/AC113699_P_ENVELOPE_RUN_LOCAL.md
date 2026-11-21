# Study A | A1 113699 nighttime failed-hour inverter-P AC envelope

**21 November 2026. Prepared next experiment, not executed.** First read
AC113699_SIGNED_PILOT_REMOTE_AUDIT.md and the original 15-hour pilot.
The signed result e211d601 contains 150 converged cases, 10 failed
case-hours due to overload, and no verified annual AC pass.

## Mechanism

Under the *assumed* 3 kVA nameplate and provisional A1 six-house service
territory, original load-only demand exceeded model transformer rating on
14 Mar 19:00, 11 Sep 20:00, 06 Oct 19:00 and 30 Nov 20:00 (2025).
Neither installed hardware was infeasible at all four hours:
- A0 original hardware on A1: only 14 Mar 19:00 and 30 Nov 20:00 fail.
- A1 original hardware on A1: only 30 Nov 20:00 fails.
- Both original schedules have zero inverter P at 30 Nov 20:00.
- The original battery Store is at its existing physical-SOC lower bound
  then, so simply injecting extra power into the saved dispatch is invalid.
  An intertemporal full-year fixed-hardware battery schedule must be solved
  *after* an electrically feasible candidate P point is found.

The source energy PCC proxy can understate real AC transformer loading.
At 30 Nov 20:00, energy proxy 2.860256 kVA becomes actual balanced-model
AC PCC 3.015682 kVA, so source energy-only no-export and cap checks
do NOT prove the network model's apparent-power compliance.

## First experiment, narrowly bounded

The new runner reads and hashes the prior signed 150-row AC CSV and
manifest, then reruns all previous source checks for 35-house profiles,
16 matched energy cases, four original/cross 113699 schedules and
the A0/A1 radial EPM GIS circuits. It requires **exactly three
original A1/Q-off/fixed-hardware failed case-hours**, no silent changes.

For each failed case-hour it holds six individual customer load profiles,
the original A1 feeder and 3 kVA planning nameplate, PF=.98, service
factor=1.0, and nighttime Q OFF. It probes 41 inverter P values from 0 to
the lower of gross load, installed inverter kVA and 0.95 times the
installed Deye battery DC power limit. This bounds instantaneous battery
power and prohibits gross-export injection. The 0-kW original AC solution
must reproduce exactly before any sweep is accepted.

**Total 123 additional, selected-hour pandapower solves.** No PyPSA solve
or SOC schedule change. Per-case sample AC feasibility uses 0.95..1.05
pu and <=100% transformer/line screen; 0.97..1.03 pu may be inspected
separately. The tool records all samples and groups only *adjacent tested
feasible points*. Feasibility BETWEEN such points is not mathematically
proven. This is NOT a grid-approved inverter P corridor and no battery
chronology has been changed.

Results live in an unused repo-root directory
StudyA_A0_A1_MatchedHardware_AC113699_P_Envelope_vN, with:
- RUN_MANIFEST.json, original-source hashes and 3 case-hour sample bands
- AC_P_SWEEP_SAMPLES.csv, every AC result including nonconvergence
- figures_diagnostic/sampled_voltage_vs_P.png
- figures_diagnostic/sampled_transformer_vs_P.png

If a case has zero feasible P samples, the tool records it unresolved
instead of inventing redispatch. If all 3 have feasible sampled points,
a later **separate** fixed-hardware PyPSA 8,760-hour SOC reoptimization
must test whether energy can be shifted to these P requirements, with
the physical 20% SOC floor, cyclic boundary, no ENS, no export, fixed
PV/BESS/inverter nameplates, and verified discharge/charge losses.
Subsequent pandapower AC rechecks are still required.

## Local workflow, Windows Miniforge Prompt, Git repository root

Check local status before updating to avoid overwriting work:

~~~bat
git status --short
git pull --ff-only origin sync/seedexchange-local-2026-11-17

python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21" -p "test_*.py" -v

python "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21\matched_hardware_ac113699_p_envelope.py" --repo-root . --preflight-only
~~~

The preflight is source-only, writes no output and must report:
SOURCE_PINNED_113699_FAILED_HOUR_P_ENVELOPE_NO_SOLVES.
There must be three failed hardware case-hours and
planned_AC_powerflow_calls=123. If any source hash, the 15-hour failure
roster or source geometry differs, stop and inspect instead of bypassing
the gate.

Then run locally:

~~~bat
python "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21\matched_hardware_ac113699_p_envelope.py" --repo-root .
~~~

After completion, verify the output folder shown by the program:

~~~bat
dir /b /ad "StudyA_A0_A1_MatchedHardware_AC113699_P_Envelope_v*"
~~~

## Always include push, do not stage unrelated work

Replace v1 with the actual version printed by the runner. A completed
SAMPLED_AC_P_HAS_UNRESOLVED_HOURS_SOC_AND_ANNUAL_PENDING is a legitimate
diagnostic and should be preserved; it is not a simulation success
claim. The other completed status is
SAMPLED_AC_P_CANDIDATES_FOUND_SOC_AND_ANNUAL_PENDING. If the manifest
says INCOMPLETE_P_ENVELOPE_DO_NOT_CLAIM, share the console traceback
before promoting any result.

~~~bat
set "OUT=StudyA_A0_A1_MatchedHardware_AC113699_P_Envelope_v1"

python -c "import os,json; from pathlib import Path; p=Path(os.environ['OUT']); j=json.loads((p/'RUN_MANIFEST.json').read_text()); assert j['status'] in ('SAMPLED_AC_P_HAS_UNRESOLVED_HOURS_SOC_AND_ANNUAL_PENDING','SAMPLED_AC_P_CANDIDATES_FOUND_SOC_AND_ANNUAL_PENDING'); assert j['new_ac_solver_calls']==123; assert len(j['sampled_hour_results'])==3; assert j['annual_AC_feasible'] is False; print('COMPLETED BOUNDED DIAGNOSTIC, NOT ANNUAL AC')"

git add -- "%OUT%"
git diff --cached --name-only
git diff --cached --stat
git commit -m "Screen 113699 matched-hardware nighttime inverter P AC sample envelope [ci skip]"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
~~~

Only the new versioned output folder is staged. Do not alter source
mappings, the shared 92395 proposed STAR, the five-edge hypothetical
94022 network, original history or main. The local runner/test changes
still require execution, and these result commits skip GitLab CI.
An independent audit of the pushed P-sample CSV is required before
claiming an AC-constrained SOC-control option or commissioning a
new annual numerical run.
