# Study A: P1 reciprocal six-case targeted AC diagnostic

Prepared 23 November 2026. Local execution only. The proposed pilot is not completed AC evidence. The original 16 reciprocal annual energy files and the already uploaded 12-case, 300-hour source materiality folder are unchanged.

## Design and source hierarchy

The six P1 cases are the original A0 10-house 94022 cohort with A1 frozen hardware (min cost and SS90), the geographic-nearest A1 six-house 113699 cohort with A0 frozen hardware (min cost and SS90), and both 106039 SS90 hardware transfers. Source cohort and hardware identities are taken from StudyA_A0_A1_MatchedHardware_Full_v1/RUN_MANIFEST.json. The 18 event rows are a **subset of the signed 300 source selections**, with exact source data recorded in RECIPROCAL12_P1_18H_SOURCE_PLAN_2026-11-23.csv.

The archive stress nights are 2025-03-28 20:00 and 2025-11-27 20:00 for 94022; 2025-03-14 19:00, 2025-03-30 19:00, and 2025-11-30 20:00 for 113699; and 2025-11-27 20:00 for 106039. Each of the six cases also includes the selected high-solar 2025-09-04 12:00 daylight hour. This totals 18 case-hours and 36 PF-specific case-hour AC evaluations for PF 0.98/0.95, line factor 1.0, inverter at head, daylight Q capability 0.25, night Q off. The source inverter P and household gross load remain unchanged. AC-constrained P redispatch is NOT done in this pilot.

The runner verifies existing SHA source signatures, the original signed v6.2 script/model, 2025 individual stochastic profiles, exact target household IDs, transformer rating assumptions, existing provisional GIS territory and the exact 18 source P/PV/import/daylight rows. A missing/changed source stops rather than silently substitutes a different dispatch. No existing results are overwritten.

## Run from your actual Windows Miniforge repository root

First synchronize. Do not reset, clean, or force checkout if git reports local modifications.

~~~bat
git status --short
git branch --show-current
git fetch origin
git switch sync/seedexchange-local-2026-11-17
git pull --ff-only origin sync/seedexchange-local-2026-11-17
~~~

The user's separate A0 106039 P/Q regression suite already reported nine out of nine passing on 23 November. The corrected reciprocal12 source-materiality fixture and the newly authored P1 tests still require local confirmation.

~~~bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22" -p "test_matched16_reciprocal12_materiality.py" -v

python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22" -p "test_matched16_reciprocal12_p1_ac_pilot.py" -v

python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_reciprocal12_p1_ac_pilot.py" --repo-root . --preflight-only
~~~

Expected: nine and ten synthetic tests with OK, then status P1_RECIPROCAL12_SIGNED_GIS_PQ_PREFLIGHT_NO_AC with six cases, 18 selected source case-hours, 36 planned PF case-hour evaluations and zero new AC evaluations. There are NO pandapower calculations in preflight mode.

## Conditional 36-case-hour AC execution

Only after the above three checks pass:

~~~bat
python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_reciprocal12_p1_ac_pilot.py" --repo-root . --run-pilot
~~~

The output is newly versioned at the repository root as StudyA_Reciprocal12_P1_AC_Pilot_v1 (or next unused version). It contains TARGETED_36_AC_CASEHOURS.csv, RUN_MANIFEST.json, and figures_diagnostic/min_voltage.png plus trafo_loading.png. The manifested 36 case-hour evaluations are distinct from underlying pandapower solver calls because a single daytime Q selection can require multiple AC solves. Model nonconvergence or voltage/thermal failures count as recorded diagnostic outcomes, not reason to hide results.

A successful receipt has status P1_TARGETED_36_AC_CASEHOURS_RECORDED_NOT_ANNUAL and new_AC_case_hour_evaluations=36, with converged+nonconverged=36. It explicitly retains annual_AC_verified=False, field_EPM_verified=False. If the pilot errors, preserve the incomplete output folder and report the exception without treating results as a pass.

Once checked, stage only the newly created P1 pilot output, commit and push the sync branch. Do not alter main, any signed annual AC outputs or the manufacturer SOC hardware policy.

## Scientific decision rule

A selected violated hour proves that the **fixed P/Q dispatch** fails that model's screen at that hour. It does NOT establish that the hardware is unsuitable after legitimate AC-constrained P/Q redispatch, different siting or approved network changes. Passing all 36 cases is NOT a chronological 8,760-hour AC pass. Prioritize EPM feeder routing, H03/H06/H13 affiliations, individual service phases, transformer nameplates and protection evidence before treating a model screen as a real utility conclusion. In final studies, use full chronological annual dispatch plus AC and, when needed, a physically valid redispach and revalidation. Exclude the northern 25 kVA transformer completely.
