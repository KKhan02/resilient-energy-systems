@echo off
setlocal EnableExtensions
rem Study A: three existing nine-house archived economic anchors on transformer 94022.
rem Reuse the existing batch_archived_campaign.py, not a new optimization model.
rem Example from repo root: call case1\studies\ac_aware_redispatch_v1\run_study_a_nine_reference.cmd preview energy
rem                          call case1\studies\ac_aware_redispatch_v1\run_study_a_nine_reference.cmd run energy
rem                          call case1\studies\ac_aware_redispatch_v1\run_study_a_nine_reference.cmd preview ac
rem                          call case1\studies\ac_aware_redispatch_v1\run_study_a_nine_reference.cmd run ac

if /I not "%~1"=="preview" if /I not "%~1"=="run" goto :usage
if /I not "%~2"=="energy" if /I not "%~2"=="ac" goto :usage
if not "%~3"=="" goto :usage
set "EXECUTE="
if /I "%~1"=="run" set "EXECUTE=--execute"
set "STAGE=%~2"

rem Anchor to the checked-out repository, regardless of caller's current folder.
pushd "%~dp0..\..\.." || exit /b 2
set "RUNNER=case1\studies\ac_aware_redispatch_v1\batch_archived_campaign.py"
set "PLAN=case1\studies\ac_aware_redispatch_v1\outputs\campaign_reuse_index_v18_01"
set "ENERGY=case1\studies\ac_aware_redispatch_v1\outputs\campaign_manufacturer_01"
set "AC=case1\studies\ac_aware_redispatch_v1\outputs\campaign_AC_01"
if not exist "%RUNNER%" (
    echo ERROR: Cannot find existing batch runner in local checkout.
    goto :error
)
if not exist "%PLAN%\all_distinct_equipment_candidates.csv" (
    echo ERROR: Missing archived campaign index. Do not rebuild the old campaign.
    goto :error
)
if /I "%~1"=="run" if /I "%STAGE%"=="ac" (
    echo INFO: Annual AC requires verified 8760-hour manufacturer-SOC trajectories.
    echo INFO: The existing runner skips a candidate when its energy source is missing.
)

echo.
echo Study A nine-house cohort on EPM 94022: %STAGE% / %~1 / PF0.98 / service factor 1.0
for %%E in (EC-3cc99d4429a15487a083 EC-b091c626114a2d74884f EC-9df8c68834f7c7f6faa3) do (
    echo.
    echo === %%E ===
    python "%RUNNER%" --repo-root . --plan-dir "%PLAN%" --energy-root "%ENERGY%" --ac-root "%AC%" --candidate-id %%E --stage %STAGE% --scenario-set reference %EXECUTE%
    if errorlevel 1 goto :error
)
echo.
echo DONE: Only selected archived nine-house reference candidates were addressed.
echo The 82-panel maximum-SS candidate remains excluded pending hardware/GIS eligibility review.
popd
exit /b 0

:error
echo ERROR: Candidate command returned a nonzero result. Inspect the original runner output.
popd
exit /b 1

:usage
echo Usage: %~nx0 preview^|run energy^|ac
exit /b 2
