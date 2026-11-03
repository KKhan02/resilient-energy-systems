# SEEDExchange PyPSA study: checkpoint-safe plotting fix

## Failure fixed
`KeyError: 'panel_count_fixed'` in `pareto_panel_sweep.py` after successful HiGHS MILP solve.

Cause: `full_study.py` stores the exact fixed-PV count in the `panels` task field, whereas the shared plotting routine expected `panel_count_fixed` (from the older standalone panel-sweep runner).

## Files supplied
- `case1/studies/pypsa_joint_optimization_v1/pareto_panel_sweep.py` (one-file replacement)
- `case1/studies/pypsa_joint_optimization_v1/tests/test_plot_checkpoint_fix.py` (three local regression tests)

## Installation
Extract this archive at your repository root, allowing the replacement of ONLY `pareto_panel_sweep.py`. Do not delete or rename `case1/studies/pypsa_joint_optimization_v1/outputs/full_study/checkpoint.jsonl`.

To regenerate summaries/figures **without any solver runs**:

```powershell
python case1/studies/pypsa_joint_optimization_v1/full_study.py --repo-root . --max-tasks 0 --no-shortlist
```

To resume the **next batch of 50 uncompleted tasks**:

```powershell
python case1/studies/pypsa_joint_optimization_v1/full_study.py --repo-root . --max-tasks 50
```

Keep the output folder and other flags identical to your earlier run. The checkpoint is append-only. Valid `OPTIMAL` records are skipped upon resumption, and old runtime-error records may be retried.

## Tested
- End-to-end plotting of a synthetic partial checkpoint using `panels`
- Backward compatibility for `panel_count_fixed`
- Graceful no-op plotting when a subset contains only infeasible designs

Tests executed with pandas 2.2.3, matplotlib 3.10.8, pytest 9.0.2. No PyPSA solver was run locally; the user's HiGHS log confirms their numerical solve completed before reporting failed.

## Scope
This patch fixes the **reporting crash only**. The previously noted PyPSA model warnings (custom variable mapping, undefined carriers, missing shadow prices, objective-constant deprecation) are not addressed. This patch makes no claim of AC network validation.
