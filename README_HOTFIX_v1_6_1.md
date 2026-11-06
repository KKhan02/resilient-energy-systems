# SEEDExchange WP1 annual AC validator hotfix v1.6.1

This patch fixes a Python keyword mismatch in the 12-house AC validator. The repository's `corridors.q_ratio_at_hour` signature uses `night_q_allowed`, while the previous validator called it with `allow_night`. The update changes only that call and adds two regression tests. No electrical equations, reactive-power operating decisions, scenario settings, or model limits are changed.

## Installation

Extract this ZIP into the root of your existing `resilient-energy-systems` checkout. Overwrite the *two supplied source/test files only*. Do not overwrite any `outputs` directories. The original v1.6 and earlier pilot files are prerequisites.

## Validation

```powershell
python -m pytest -q case1/studies/ac_aware_redispatch_v1/tests
```

## Rerun 12-house AC screen

The original failed run may already have created `twelve_ac_full_01`. Use a new output folder:

```powershell
python case1/studies/ac_aware_redispatch_v1/validate_annual_ac_target.py --repo-root . --pilot-dir case1/studies/ac_aware_redispatch_v1/outputs/twelve_manufacturer_01 --outdir case1/studies/ac_aware_redispatch_v1/outputs/twelve_ac_full_02 --vmin 0.95 --vmax 1.05
```

Optionally do a smoke test to a distinct folder, using `--max-hours 24`, before the full-year run.

## Validation status

43 pure Python tests passed in a composite package assembled from the previously supplied v1.1 through v1.6 source files; syntax and command-line help were checked. PyPSA/pandapower numerical run was not executed here.
