@echo off
setlocal
REM All remaining 8 PF x length settings, annual 8760 hours per case.
python "case1\studies\SEEDExchange_StudyA_PVBESS_AnnualPortfolio_v1\run_annual_replays.py" --repo-root . --scope sensitivities --dispatch both --cases all --run
exit /b %errorlevel%
