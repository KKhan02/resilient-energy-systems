# Study A | 113699 A1 same-hardware 2025 cyclic-SOC P-corridor experiment

**Created 21 November 2026. New full-year PyPSA solves NOT YET EXECUTED locally.**
Read AC113699_P_ENVELOPE_SIGNED_REMOTE_AUDIT.md first.

## Research question

At the six-house **provisionally proposed** A1 113699 feeder, the 15-hour
source pilot failed at three origin-hardware case-hours with the unchanged
2025 perfect-foresight battery schedule. The 123-point independent
night P-sample experiment finds AC-passing samples with the original
3 kVA *assumed* nameplate, but every failing source hour has the original
battery Store at the manufacturer's 20% physical SOC limit.

Can the original **A0-origin 17PV/3B/5kVA inverter** and
**A1-origin 20PV/4B/6kVA inverter** each supply their exact previously
tested inverter P points at the critical hours, by rescheduling 2025
battery energy across the year, without changing equipment?

The new script uses the preserved, signed PyPSA fixed_hardware.solve_fixed
and its original annual DC PV, inverter, charging and discharging links,
0.95 one-way inverter efficiency, sqrt(0.95) battery charging/discharging
efficiency, cyclic 8,760h Store, 20% physical-SOC manufacturer floor,
no unserved load, and no grid export. It does NOT change the transformer
assumption, source geometry, 35-house demand inputs, price, or inverter.

## Exact sampled-P equality corridors, not hypothetical interpolations

Rather than asserting an unproven AC-feasible continuous P interval,
the initial Linopy constraints are exact equalities at each saved
**sample index 3**. The source 41-point sample CSV and original 16-case
energy/GIS provenance are checked before any new solve.

| Origin hardware, applied to A1 | Timestamp 2025 | Fixed nighttime inverter AC P | Source transformer loading | Source minimum voltage |
| --- | --- | ---: | ---: | ---: |
| A0-origin | 14 Mar 19:00 | 0.2114984271 kW | 93.933% | .953465 pu |
| A0-origin | 30 Nov 20:00 | 0.2102288347 kW | 93.403% | .952963 pu |
| A1-origin | 30 Nov 20:00 | 0.2102288347 kW | 93.403% | .952963 pu |

The selected samples have around six percentage points below assumed
transformer nameplate compared with the original failing P=0 condition.
This margin is a modelling test choice, not a utility engineering
approval. An equality target is a **real 2025 LP constraint** and
does not give the battery free energy. No original source schedules
are edited. Source points are replayed again after the new 8760h solve.

The stricter 0.97pu lower voltage target **remains unresolved**.
On 30 November the highest no-export P sample (2.803kW) still produces
0.969546pu at the weakest modelled house. The new P constraints target
the main .95..1.05pu and 100% equipment-loading research screen, not
the optional strict .97..1.03pu study screen.

## Workflow and outputs

- Run source-only preflight: checks the original full 16 source cohort
  cases; original 150 AC samples; new 123 AC P-sweep samples, hashes,
  original 2025 NASA PV; the three exact failed-hour origins; original
  fixed hardware and original annual objective.
- Run ONE full 8760h original-equipment PyPSA LP for --origin A0.
  Run a separate LP for --origin A1. They are independent and
  must not overwrite prior result folders.
- After each annual energy optimum, check physical SOC bounds,
  full 8760h cyclic SOC recurrence, zero ENS/export, DC bank current,
  installed PV/BESS/inverter nameplates, annual equipment annuity,
  original source tariff, and exact P constraints.
- Re-evaluate AC at the **15 original common 2025 pilot hours**,
  using source individual A1 household loads and original EPM GIS
  pandapower, PF=.98, length multiplier 1.0, daylight Q=.25 and night
  Q OFF. Confirm the previously failed nights replay consistently at
  the signed P sample points.
- Save complete new annual 8760h energy CSV, all 15 AC results,
  original-versus-reoptimized SOC diagnostics PNGs, and a manifest
  with signed lineage, annual total cost delta, inverter/SOC changed
  hours and all sampled violations.

A 15-hour AC pass is **not** an 8760-hour AC feasibility proof. If
new dispatch changes other hours, previously unseen AC failures may
occur. The 8760h AC replay is a following distinct validation gate.
Any 15-hour AC failures are recorded instead of treating the constrained
LP as an AC OPF. Results remain planning benchmarks, with 3 kVA
transformer, LV service paths and phase wiring not surveyed/approved.

## Run in Windows Miniforge Prompt, repository root

First check and pull the synchronized branch. Preserve any unrelated
working tree changes and check Git status before pulling.

~~~bat
git status --short
git pull --ff-only origin sync/seedexchange-local-2026-11-17

python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21" -p "test_*.py" -v

python "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21\matched_hardware_113699_soc_corridor.py" --repo-root . --preflight-only
~~~

Expected preflight status:
SIGNED_113699_SAMPLED_P_TO_ANNUAL_SOC_PREFLIGHT_NO_NEW_LP_OR_AC.
Require **three** source-sampled P target points, across **two**
original fixed hardware sets. The separate synthetic tests are not
GitLab-CI run because the study commits use [ci skip].

Only after preflight succeeds, run each of these separately:

~~~bat
python "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21\matched_hardware_113699_soc_corridor.py" --repo-root . --origin A0

python "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21\matched_hardware_113699_soc_corridor.py" --repo-root . --origin A1
~~~

One output folder per origin, chosen as the next unused version:
StudyA_A0_A1_MatchedHardware_113699_SOC_Corridor_A0_vN and
StudyA_A0_A1_MatchedHardware_113699_SOC_Corridor_A1_vN.

Completed (still annual AC pending) statuses:

- ANNUAL_SOC_FEASIBLE_15_SAMPLE_AC_PASS_ANNUAL_AC_PENDING
- ANNUAL_SOC_FEASIBLE_15_SAMPLE_AC_VIOLATIONS_ANNUAL_AC_PENDING

INCOMPLETE_SOC_CORRIDOR_DO_NOT_CLAIM is *not* a completed result. Preserve
its manifest, report traceback, and do not stage as successful.

## Required push instructions after the local run

Find output folders, and replace v1 below with the actual versions:

~~~bat
dir /b /ad "StudyA_A0_A1_MatchedHardware_113699_SOC_Corridor_*_v*"

set "A0OUT=StudyA_A0_A1_MatchedHardware_113699_SOC_Corridor_A0_v1"
set "A1OUT=StudyA_A0_A1_MatchedHardware_113699_SOC_Corridor_A1_v1"

python -c "import os,json; from pathlib import Path; keys=('A0OUT','A1OUT'); valid=('ANNUAL_SOC_FEASIBLE_15_SAMPLE_AC_PASS_ANNUAL_AC_PENDING','ANNUAL_SOC_FEASIBLE_15_SAMPLE_AC_VIOLATIONS_ANNUAL_AC_PENDING'); docs=[json.loads((Path(os.environ[k])/'RUN_MANIFEST.json').read_text()) for k in keys]; assert all(j['status'] in valid and j['new_LP_solves']==1 and j['new_AC_solves']==15 and j['annual_AC_feasible'] is False for j in docs); assert set(j['origin'] for j in docs)=={'A0','A1'}; print('TWO COMPLETE SOC LP CASES, ANNUAL AC STILL PENDING')"

git add -- "%A0OUT%" "%A1OUT%"
git diff --cached --name-only
git diff --cached --stat

git commit -m "Reoptimize 113699 A1 source-matched 2025 battery SOC with AC-sampled P constraints [ci skip]"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
~~~

Stage only the actual two complete output folders. If either solve
is infeasible, has a source mismatch, or has nonconvergent AC, share its
console traceback and preserve its incomplete output without claiming
annual SOC or AC feasibility. Assistant independently audits both
signed full-year trajectories and 15 AC replays after the push, then
prepares broader annual AC validation only if the results support it.

No changes to historical outputs, physical EPM source, proposed 94022
five-edge intervention, shared 92395 STAR/MST, 16-case energy study,
or the main branch are authorized by this experiment.
