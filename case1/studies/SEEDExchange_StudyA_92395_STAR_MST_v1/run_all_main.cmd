@echo off
setlocal
REM Run from repository root, using Miniforge Prompt or Anaconda Prompt.
REM Main PF/length for ALL 8 mapped GIS A0/A1 cohorts. No transformer filter.
python "case1\studies\SEEDExchange_StudyA_GrossAC_Sensitivity_v1\run_gross_sensitivity.py" --repo-root . --phase main --run
if errorlevel 1 exit /b %errorlevel%
REM Also cover 92395 baseline (STAR + MST), both A0 and A1 identical.
python "case1\studies\SEEDExchange_StudyA_92395_STAR_MST_v1\run_92395_star_mst.py" --repo-root . --phase baseline --run
if errorlevel 1 exit /b %errorlevel%
REM All principal non-baseline parameter choices for both proposed topologies.
python "case1\studies\SEEDExchange_StudyA_92395_STAR_MST_v1\run_92395_star_mst.py" --repo-root . --phase main --run
if errorlevel 1 exit /b %errorlevel%
echo MAIN PHASE COMPLETE. Review all annual results before interactions.
endlocal
