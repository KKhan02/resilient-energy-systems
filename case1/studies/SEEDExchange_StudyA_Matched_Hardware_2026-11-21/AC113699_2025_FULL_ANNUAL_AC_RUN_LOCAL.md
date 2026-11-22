# Study A | 113699 full 2025 AC validation of both SOC-corrected hardware sets

**Created 22 November 2026. The annual AC replay code has not been executed locally.**
Source audit: AC113699_ANNUAL_SOC_REMOTE_AUDIT_2026-11-22.md.

## Goal and evidence hierarchy

The two 8,760-hour exact-P Linopy annual SOC reoptimizations are already
completed and user-pushed, commit c3653a55. They preserve original 113699
A0-origin 17PV/3B/5kVA inverter and A1-origin 20PV/4B/6kVA inverter
hardware, physical 20% SOC minimum, original no-export/no-ENS policy,
battery power limits, cyclic SOC, NASA 2025 PV and six A1 household demand
profiles. Both reoptimized schedules now pass the **15 original**
pandapower AC selected hours at PF .98 and service factor 1.0, but
**full 8,760-hour AC feasibility has NOT yet been checked**.

The next gate is the unabridged 8,760-hour original EPM GIS balanced
pandapower AC replay for EACH reoptimized 2025 dispatch, exactly as saved.
The assumed transformer nameplate is 3 kVA; EPM service paths, real
nameplate, phase arrangement and inverter nighttime auxiliary behavior
are not field verified. No reconstructed wiring or fictitious network
modification is introduced. Do not invoke or rely on Windows SUBST R:
for this run. The prior R: alias is a historical annual_ac_replays_v1
path-length workaround, not another disk or a required project root.

The runner checks BOTH signed annual SOC source manifests and all saved
full-year 2025 dispatch data and original 15-hour sampled AC results
BEFORE creating any new output or running new power flows.
Previously signed annual CSV/AC CSV Windows-CRLF SHA can be
reconstructed only from an exact GitLab LF representation, not
arbitrarily suppressed. All three earlier SOC diagnostic PNGs
are hash-checked too. Original full matched A0/A1 household and
123-hour P sample lineage is checked through the source runners.

## AC model and result checks

One annual replay evaluates all 8,760 original 2025 timestamps:
- exact original A1 H03,H04,H05,H06,H07,H10 individual customer demands
- exact original six EPM LV sections plus *inferred* service taps
- 3kVA assumed transformer, 0.98 household PF, original length factor 1.0
- measured saved inverter AC P per hour from signed reoptimized SOC CSV
- existing daylight Q=.25 coordinated control, night Q=0
- main research voltage range 0.95..1.05 pu, <=100% transformer/line loading
- separate strict research voltage flag 0.97..1.03 pu
- all pandapower convergence outcomes (including failed hours, not dropped)
- exact reproduction of the 15 previously signed AC points within tolerances

Each origin produces a new versioned folder named
StudyA_A0_A1_MatchedHardware_113699_AnnualAC_A0_vN or
StudyA_A0_A1_MatchedHardware_113699_AnnualAC_A1_vN.

Results: RUN_MANIFEST.json, annual_ac_hourly_2025.csv,
figures_diagnostic/annual_min_voltage.png and
figures_diagnostic/annual_transformer_loading.png.

A full 8760h convergence/AC-pass can establish only a **modelled**
2025 research-screen feasibility for this provisional network,
not a grid-operator approval. The optional .97..1.03pu strict band
has its own independently counted violations and is NOT silently
combined with the main .95..1.05pu research screen.

If any convergence or AC failure occurs, a completed diagnostic retains
it and counts it. Annual loss kWh totals are reported only if ALL 8760
hours converge; otherwise no complete annual losses are claimed.
No AC-loss-adjusted tariff/economic comparison is made without an
identically sourced original-year AC baseline. Neither this runner
nor its preflight creates/mounts virtual drives or changes the source.

## Windows Miniforge Prompt: pull, tests, preflight

Use your original D: checkout, preserving unrelated local files:

~~~bat
git status --short
git pull --ff-only origin sync/seedexchange-local-2026-11-17

python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21" -p "test_*.py" -v

python "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21\matched_hardware_113699_annual_ac.py" --repo-root . --preflight-only
~~~

Preflight must report:
SIGNED_TWO_113699_SOC_RESULTS_ANNUAL_AC_SOURCE_PREFLIGHT_NO_NEW_SOLVES.
Both source directories must show 8760 hours and the prior 15 AC
checks, with TWO source-origin hardware cases. This source preflight
does not solve a new AC hour.

## Execute separately, one original hardware set at a time

~~~bat
python "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21\matched_hardware_113699_annual_ac.py" --repo-root . --origin A0

python "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21\matched_hardware_113699_annual_ac.py" --repo-root . --origin A1
~~~

Both simulations can be lengthy because each contains 8760 real
pandapower calls plus Q-control evaluations. Run them locally and
retain partial diagnostic manifests on interruption. Do not overwrite
or blend results with historical root annual_ac_replays_v1, 92395
STAR/MST topology, A0 94022 five-edge hypothetical changes, or any
separately modified 106039 network.

Complete outcome status variants:
- ANNUAL_113699_MODEL_AC_MAIN_BAND_PASS_STRICT_SEPARATE
- ANNUAL_113699_MODEL_AC_MAIN_BAND_VIOLATIONS
- ANNUAL_113699_MODEL_AC_NONCONVERGENCE_RECORDED

Each complete outcome is a valid full-year AC *diagnostic*,
including a failed study outcome. INCOMPLETE_113699_ANNUAL_AC_DO_NOT_CLAIM
is NOT a successful completed run. Preserve and report its failure
traceback before attempting a repair.

## GitLab push, mandatory after local execution

First identify the output directories and use the actual new versions:

~~~bat
dir /b /ad "StudyA_A0_A1_MatchedHardware_113699_AnnualAC_*_v*"

set "A0OUT=StudyA_A0_A1_MatchedHardware_113699_AnnualAC_A0_v1"
set "A1OUT=StudyA_A0_A1_MatchedHardware_113699_AnnualAC_A1_v1"

python -c "import os,json; from pathlib import Path; keys=('A0OUT','A1OUT'); good=('ANNUAL_113699_MODEL_AC_MAIN_BAND_PASS_STRICT_SEPARATE','ANNUAL_113699_MODEL_AC_MAIN_BAND_VIOLATIONS','ANNUAL_113699_MODEL_AC_NONCONVERGENCE_RECORDED'); docs=[json.loads((Path(os.environ[k])/'RUN_MANIFEST.json').read_text()) for k in keys]; assert all(j['status'] in good and j['new_AC_solves']==8760 and j['annual_summary']['hourly_records']==8760 and j['source_validation_replayed_15h'] is True for j in docs); assert set(j['origin'] for j in docs)=={'A0','A1'}; print('TWO SOURCE-GATED 8760-HOUR AC REPLAYS COMPLETE')"

git add -- "%A0OUT%" "%A1OUT%"
git diff --cached --name-only
git diff --cached --stat
git commit -m "Validate matched-hardware 113699 A1 full-year AC for both SOC-corrected dispatches [ci skip]"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
~~~

If only ONE of the two full-year replays is completed, do not pretend
that both have finished. Inspect that origin's RUN_MANIFEST, stage and
push ONLY its completed versioned directory, and tell the assistant
which counterpart remains pending. For a failed/incomplete directory,
do not stage it as a complete result. Every pushed full-year result
requires a separate independent GitLab audit of 8760 timestamps,
AC fields, source SHA, annual losses and network constraints before
any technology or economics recommendation.

**Post-run decision:** If all 8760 modelled hours pass main limits
for BOTH hardware sets, document conditional support for the A1
proposed six-house connection and investigate PF .95/.98/1.00 and
length x1.0/1.3/1.6, strict .97 voltage, and field documentation.
If any hour fails, examine the exact new failure time and whether
additional AC-constrained P adjustment can preserve 2025 cyclic SOC.
Do not silently upgrade the assumed transformer.
