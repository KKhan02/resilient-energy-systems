@echo off
setlocal
REM Independent 2025 annual energy and PV-first causal cases; continues after a failed candidate.
python "case1\studies\SEEDExchange_StudyA_PVBESS_AnnualPortfolio_v1\run_all_energy_causal.py" --repo-root . --stage both --run
exit /b %errorlevel%
