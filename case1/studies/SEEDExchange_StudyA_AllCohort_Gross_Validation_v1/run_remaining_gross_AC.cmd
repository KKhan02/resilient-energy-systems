@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM Study A v6.2: six remaining GIS-source-backed annual gross AC cohort cases.
REM Run only from repository root, within Miniforge Prompt or Anaconda Prompt.
REM Does not edit GitLab, existing sources, or prior result folders.
if not exist ".git" (
  echo ERROR: Run from the resilient-energy-systems repository root.
  exit /b 1
)
set "RUNNER=case1\studies\SEEDExchange_StudyA_v6_LocalRunner\seed_study_a_v6.py"
set "MANIFEST=case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\input_manifest_v6_2.json"
set "BASE=case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\batch_remaining_gross_v1"
if not exist "%RUNNER%" (
  echo ERROR: v6.2 runner not found: %RUNNER%
  exit /b 1
)
if not exist "%MANIFEST%" (
  echo ERROR: signed manifest not found: %MANIFEST%
  exit /b 1
)
if exist "%BASE%" (
  echo ERROR: Output parent already exists. No overwrites permitted: %BASE%
  echo Review old outputs and rename BASE in this CMD file before a fresh rerun.
  exit /b 1
)
python -c "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); assert d['population_houses']==35 and d['2025_hours']==8760; assert all({k:len(d['groups'][a][k]) for k in ('94022','113699','85398','92395')}==({'94022':10,'113699':4,'85398':4,'92395':4} if a=='A0' else {'94022':8,'113699':6,'85398':5,'92395':4}) for a in ('A0','A1'))" "%MANIFEST%"
if errorlevel 1 (
  echo ERROR: Manifest A0/A1 cohort counts failed preflight.
  exit /b 1
)
mkdir "%BASE%" || exit /b 1
for %%T in (94022 113699 85398) do (
  for %%A in (A0 A1) do (
    echo.
    echo === Study A gross AC 24h smoke: %%A, trafo %%T ===
    python "%RUNNER%" ac --manifest "%MANIFEST%" --assignment %%A --transformer %%T --mode gross --hours 24 --outdir "%BASE%\gross_%%A_%%T_smoke_24h"
    if errorlevel 1 (
      echo ERROR: 24h run did not finish. Existing output preserved. Annual batch not started.
      exit /b 1
    )
    python -c "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); assert d['simulation_hours']==24 and d['converged_hours']==24 and d['nonconverged_hours']==0, 'AC convergence smoke gate failed'; print('24h convergence gate passed; AC feasibility may still be violated and is NOT assumed.')" "%BASE%\gross_%%A_%%T_smoke_24h\ac_summary.json"
    if errorlevel 1 (
      echo ERROR: 24h convergence gate failed. Inspect hourly outputs before running annual.
      exit /b 1
    )
  )
)
for %%T in (94022 113699 85398) do (
  for %%A in (A0 A1) do (
    echo.
    echo === Study A gross AC 8760h: %%A, trafo %%T ===
    python "%RUNNER%" ac --manifest "%MANIFEST%" --assignment %%A --transformer %%T --mode gross --hours 8760 --outdir "%BASE%\gross_%%A_%%T_annual_8760h"
    if errorlevel 1 (
      echo ERROR: Annual run stopped. Previous output folders preserved.
      exit /b 1
    )
    python -c "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); assert d['simulation_hours']==8760 and d['converged_hours']==8760 and d['nonconverged_hours']==0, 'Annual convergence incomplete'; print('Annual AC convergence gate passed. AC-infeasible hours:',d['AC_infeasible_hours'])" "%BASE%\gross_%%A_%%T_annual_8760h\ac_summary.json"
    if errorlevel 1 (
      echo ERROR: Annual AC convergence incomplete. Inspect and share results.
      exit /b 1
    )
  )
)
echo.
echo All SIX additional GIS-graph AC cases completed. The already completed A0/A1 106039 cases are NOT rerun.
echo Transformer 92395 needs a separately approved provisional LV topology for AC; use the transformer-only screen in this ZIP meanwhile.
echo Results parent: %BASE%
exit /b 0
