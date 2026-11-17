@echo off
setlocal
REM Run from repository root using Miniforge Prompt or Anaconda Prompt.
REM Combined PF x service-length corners for ALL eight GIS A0/A1 cases.
python "case1\studies\SEEDExchange_StudyA_GrossAC_Sensitivity_v1\run_gross_sensitivity.py" --repo-root . --phase interactions --run
if errorlevel 1 exit /b %errorlevel%
REM 92395 proposed STAR and MST PF x length corners.
python "case1\studies\SEEDExchange_StudyA_92395_STAR_MST_v1\run_92395_star_mst.py" --repo-root . --phase interactions --run
if errorlevel 1 exit /b %errorlevel%
echo INTERACTION PHASE COMPLETE. Review AC results and proceed to PV+BESS.
endlocal
