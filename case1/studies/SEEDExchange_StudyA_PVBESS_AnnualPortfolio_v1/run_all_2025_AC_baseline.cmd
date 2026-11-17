@echo off
setlocal
REM Every A0/A1 cohort, both tiers, both optimized+causal, STAR+MST at 92395.
python "case1\studies\SEEDExchange_StudyA_PVBESS_AnnualPortfolio_v1\run_annual_replays.py" --repo-root . --scope baseline --dispatch both --cases all --run
exit /b %errorlevel%
