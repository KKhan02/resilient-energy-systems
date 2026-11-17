@echo off
setlocal
REM Full agreed local-only PV+BESS work: 22 energy, 22 causal, 48 baseline and 384 sensitivity AC replays.
call "case1\studies\SEEDExchange_StudyA_PVBESS_AnnualPortfolio_v1\run_all_2025_energy_and_causal.cmd"
if errorlevel 1 exit /b %errorlevel%
call "case1\studies\SEEDExchange_StudyA_PVBESS_AnnualPortfolio_v1\run_all_2025_AC_baseline.cmd"
if errorlevel 1 exit /b %errorlevel%
call "case1\studies\SEEDExchange_StudyA_PVBESS_AnnualPortfolio_v1\run_all_2025_AC_sensitivities.cmd"
exit /b %errorlevel%
