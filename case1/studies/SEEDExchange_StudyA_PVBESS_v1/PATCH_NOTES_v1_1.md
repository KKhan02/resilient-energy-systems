# Study A PV+BESS launcher v1.1: parent-directory correction

## User-reported error

First `run_portfolio.py --stage mapped-energy --transformer 106039 --assignment A0 --run` stopped before solving with:

`ValueError: Create output parent before running: ...\outputs\run_01\pvbess_phase_01`

## Root cause

The signed v6.2 runner's `new_output` requires its target's parent directory to exist. The separate v1 portfolio wrapper did not create `pvbess_phase_01`. The 22-job dry run intentionally never created it, making the first actual run fail.

## Correction

After `secure_context` has verified the signed manifest and frozen source hashes, and after the existing-output / dependency check has succeeded, the wrapper now:

1. Requires the job output directory to be an immediate child of its configured output base.
2. Creates only that output base (`outbase.mkdir(parents=True, exist_ok=True)`).
3. Passes the same case-specific output path to the unchanged numerical runner.

The wrapper does **not** create the case folder, overwrite prior results, modify signed files, or create output directories during `--dry-run`.

## How to install

Extract this ZIP into the local repository's `case1\studies` folder and allow replacement of `SEEDExchange_StudyA_PVBESS_v1\run_portfolio.py` and its README. Keep all existing output directories.

From repository root, in **Miniforge Prompt / Anaconda Prompt**:

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_PVBESS_v1\tests" -v
python "case1\studies\SEEDExchange_StudyA_PVBESS_v1\run_portfolio.py" --repo-root . --stage mapped-energy --transformer 106039 --assignment A0 --run
```

Expected tests: `Ran 16 tests`, then `OK`. Numerical optimization remains exclusively for the user's local execution; no new result is claimed in this patch.

## Immediate alternative without replacing the script

```bat
mkdir "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\pvbess_phase_01"
```

Then rerun the exact original pilot command.
