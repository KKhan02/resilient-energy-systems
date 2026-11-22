# Study A | 113699 A1 nine-factor uncertainty screen

**Prepared 22 November 2026, not executed.** Read
AC113699_TWO_8760H_AC_REMOTE_AUDIT_2026-11-22.md.

## Source-supported motivation

The 2025 full-year original-source pandapower AC replays are now complete
for both fixed-hardware sets on the *provisional A1 six-house* 113699
network, under the reference PF .98 and assumed service length 1.0.

| Measured source property (model, not field) | 17PV / 3B / 5kVA | 20PV / 4B / 6kVA |
| --- | ---: | ---: |
| AC-converged/main-feasible annual hours | 8760 / 8760 | 8760 / 8760 |
| Maximum transformer loading (assumed 3kVA) | 95.75094% | 95.75094% |
| Lowest household voltage | .952963 pu | .952963 pu |
| Annual model AC losses | 286.964 kWh | 276.372 kWh |
| Hours below OPTIONAL .97pu strict limit | 245 | 120 |

The main .95..1.05pu / <=100% loading reference screen passes, but a
4.25 percentage-point peak transformer-loading margin is not extensive
uncertainty coverage. Individual EPM line/service attachments,
transformer nameplate, household phase/PF and inverter topology remain
unverified. Full-year strict .97 voltage fails for both cases.

The **next test is deliberately bounded**, not an automatic repeat of
18 full 8760-hour campaigns. The new source-pinned runner selects common
2025 timestamps from the prior 15-hour source AC pilot plus six
worst-ranked hours per metric and hardware origin for minimum voltage,
peak transformer, peak line, peak PCC kVA and peak AC losses.
At most **75 common source timestamps** are selected. It then checks:
- PF 0.95, 0.98 and 1.00 at each of
- service length 1.0, 1.3 and 1.6, for
- both frozen annual original-SOC-corrected PV/BESS schedules on A1.

This produces **18 factor-origin combinations**, and no more than 1350
new pandapower AC case-hours. Exactly the SAME selected timestamps
are evaluated for all 18 comparisons.

Baseline PF=.98 / length1.0 cases MUST reproduce the exact archived
full-year AC source values at all sampled hours. Original annual
PV/BESS equipment, 2025 SOC schedule, demand profiles and EPM GIS
household membership do not change. For length1.3/1.6, only the
original topology builder's service-length multiplier is changed.
PF variation changes the original household Q from its 0.98 model
value. No new transformer, battery or service route is invented.

This is **NOT ninefactor full-year AC validation**. A passing selected
factor is only eligible for follow-on 8760h AC replay. A failed factor
identifies the original timestamp and transformer/line/voltage cause.
The optional .97..1.03pu voltage flags remain separate from main
.95..1.05pu voltage flags. Sampled losses are NOT annual loss estimates.

**22 November preflight hotfix:** The first local execution reported 72 synthetic tests with two assertion-message failures and an `AttributeError` in preflight. The original source data was not implicated. The source checks now report `clocks disagree` for a duplicated/mismatched timestamp and `incomplete` for nonconvergent source rows. Both annual SOC CSV lookups use `annual.SOURCE_DIRS`, which is defined by `matched_hardware_113699_annual_ac.py`, rather than the SOC helper module. One source-directory ownership regression test was added. No equipment, AC/SOC equations, source hashes, annual results or GIS were changed. The revised 73-test suite and the full source preflight must still be rerun locally before launching the bounded screen.

## Windows Miniforge Prompt, original repository root

First pull the corrected floating-point source-only test and the new
study files. Your one previous synthetic failure was a comparison
precision bug, not a numerical model failure. Do NOT rerun the two
already completed full-year AC campaigns solely because of that test.

~~~bat
git status --short
git pull --ff-only origin sync/seedexchange-local-2026-11-17

python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21" -p "test_*.py" -v

python "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21\matched_hardware_113699_ninefactor_stress.py" --repo-root . --preflight-only
~~~

Preflight must finish with:
SIGNED_TWO_8760H_AC_SOURCES_NINEFACTOR_STRESS_PREFLIGHT_NO_SOLVES.
Inspect selected_hour_count and planned_AC_solves. Expected:
factor_cases=18 and planned_AC_solves=18*selected_hour_count.
The source-only preflight writes nothing, does not create a new
drive letter, and performs NO new pandapower solves.

Then launch the bounded numerical stress run:

~~~bat
python "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21\matched_hardware_113699_ninefactor_stress.py" --repo-root .
~~~

Each factor group prints progress. The runner writes a new versioned
root output directory:
StudyA_A0_A1_MatchedHardware_113699_NineFactorStress_vN.

Expected content:
- RUN_MANIFEST.json with original signatures and every sampled factor outcome
- factor_ac_hourly.csv including nonconvergence, main/strict flags and Q
- factor_summary.csv, with exactly 18 scenario-factor groups
- figures_diagnostic/max_transformer.png
- figures_diagnostic/min_voltage.png

Completed diagnostic statuses:
- SAMPLED_NINEFACTOR_MAIN_BAND_PASS_ANNUAL_SENSITIVITY_UNTESTED
- SAMPLED_NINEFACTOR_MAIN_BAND_VIOLATIONS_RECORDED
- SAMPLED_NINEFACTOR_NONCONVERGENCE_RECORDED

INCOMPLETE_NINEFACTOR_STRESS_NOT_VALIDATED means no completed
comparison. Preserve the traceback and output for debugging;
do not report it as a successful sample.

## Mandatory GitLab push, after completed local result

Find the created result version:

~~~bat
dir /b /ad "StudyA_A0_A1_MatchedHardware_113699_NineFactorStress_v*"
~~~

Replace v1 if the runner created another version.

~~~bat
set "OUT=StudyA_A0_A1_MatchedHardware_113699_NineFactorStress_v1"

python -c "import os,json; from pathlib import Path; p=Path(os.environ['OUT']); j=json.loads((p/'RUN_MANIFEST.json').read_text()); good=('SAMPLED_NINEFACTOR_MAIN_BAND_PASS_ANNUAL_SENSITIVITY_UNTESTED','SAMPLED_NINEFACTOR_MAIN_BAND_VIOLATIONS_RECORDED','SAMPLED_NINEFACTOR_NONCONVERGENCE_RECORDED'); assert j['status'] in good; assert j['factor_groups']==18; assert j['new_AC_solves']==j['planned_AC_solves']; assert j['annual_AC_verified_for_nine_factors'] is False; print('COMPLETE NINE-FACTOR BOUNDED AC DIAGNOSTIC, NOT NINE ANNUAL CHECKS')"

git add -- "%OUT%"
git diff --cached --name-only
git diff --cached --stat

git commit -m "Screen 113699 A1 nine-factor PF and LV length uncertainty at common 2025 hours [ci skip]"

git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17

git status --short
~~~

Stage ONLY the actual complete new versioned directory. No changes
to main, original 8760h AC results, historic LP sources, provisional
EPM GIS, hypothetical A0 94022 five-edge feeder or proposed 92395 STAR
are authorized. If a source-preflight or simulation check fails,
share its traceback for a narrow code repair. Do not suppress checks.

## Next after the push

Assistant independently audits all signed sampled factor-origin rows,
figure digests, PF/length changes, the repeated original PF98 length1
reference, convergence, main voltage/load limits, separate strict .97
outcomes, and which assumptions threaten 113699 feasibility. Full 2025
AC sensitivity should then be chosen based on the failed and marginal
factors, alongside an evidence request for actual EPM transformer,
service routes, phases and installed hardware.

No assignment A0/A1 utility decision, transformer sizing recommendation
or distribution-grid regulatory compliance can be inferred from the
bounded nine-factor stress screen alone.
