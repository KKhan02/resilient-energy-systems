# SEEDExchange | Study A annual PV+BESS portfolio, 8,760-hour runs

**Version:** AnnualPortfolio v1, 2026-11-09. Local workstation only. GitLab and original historical files remain unchanged.

## Why this package exists

The earlier instructions ran two annual energy solutions for **only 106039 A0**, two annual causal replays, and **24-hour AC smoke tests**. Those 24-hour AC runs did **not** establish annual PV+BESS AC feasibility. This package runs the approved **complete multi-house Study A portfolio**.

## What is covered

- **16 archived-hardware fixed-reference annual PyPSA re-dispatch jobs**: four GIS-modelled transformers (94022, 106039, 113699, 85398), A0 and A1, min-cost and higher self-sufficiency references. Archived hardware is not a new economic optimum for geographic cohorts.
- **Six new four-house MILPs**: A0 113699, A0 85398 and 92395, each with min-cost and >=90%-self-sufficiency targets. A1 four-house cohorts elsewhere are not invented. These cases are additional to, not replacements for, 16 references. Four-house cases use a battery hardware and 20% physical-SOC screen.
- **22 annual causal PV-first dispatch runs** corresponding to the annual energy outputs. Causal and PyPSA optimized schedules can differ hourly even if their annual totals are identical. Check terminal SOC before interpreting comparative economics.
- **24 distinct AC network/hardware combinations**: 16 mapped geographic archived reference cases; four new A0 four-house designs at 113699/85398; and four 92395 designs (2 equipment tiers × 2 STAR/MST networks). 92395 A0=A1, so duplicate numerical AC runs are deliberately avoided.
- **2 dispatch types** on each AC network/hardware combination: optimized and causal.
- **9 PF × feeder-length combinations**: PF = 0.95/0.98/1.00 and service-length multiplier = 1.0/1.3/1.6. The dispatch and hardware remain fixed when PF and length are varied. These are **AC sensitivity replays**, not re-optimizations at every uncertain condition.

| Stage | Annual 8,760-hour jobs | Meaning |
|---|---:|---|
| Energy, including new 4-house hardware MILPs | 22 | 2 are already signed from the 106039 A0 pilot |
| Causal PV-first energy replays | 22 | 2 already signed from 106039 A0 pilot |
| AC at reference PF .98, length 1.0 | 48 | 24 AC configurations × 2 dispatch types |
| AC remaining 8 PF/length combinations | 384 | All 24 AC configurations × 2 dispatch types × 8 combinations |
| **AC total** | **432** | Every run executes 8,760 hours |

Total is **476 stage jobs**, including the already completed four annual energy/causal jobs, or **432 distinct annual AC replays**. The historical gross-demand 90-case study is preserved separately. 92395's A0 and A1 are equal and therefore are not double-counted.

## Installation

Unzip the folder `SEEDExchange_StudyA_PVBESS_AnnualPortfolio_v1` directly into your repository's `case1\studies\` folder. Keep the existing `SEEDExchange_StudyA_PVBESS_v1` with its **v1.1 launcher fix**, the unchanged signed v6.2 runner, unchanged input manifest, 92395 STAR/MST code, and original source model files.

Use **Miniforge Prompt or Anaconda Prompt**, with the current directory set to the repository root. Do not run this in PowerShell.

## Test and check the plan without running

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_PVBESS_AnnualPortfolio_v1\tests" -v
python "case1\studies\SEEDExchange_StudyA_PVBESS_AnnualPortfolio_v1\run_annual_replays.py" --repo-root . --scope baseline
```

Expected baseline: 48 AC jobs, **all 8,760 hours**. The dry run writes no files and launches no solver.

## Run the entire agreed annual project

Single command, staged in the correct order:

```bat
call "case1\studies\SEEDExchange_StudyA_PVBESS_AnnualPortfolio_v1\run_all_StudyA_2025.cmd"
```

This calls (1) 22 energy jobs, (2) 22 causal replays, (3) 48 baseline AC jobs, (4) 384 AC sensitivity jobs. Existing results are cryptographically verified and reused. The new `run_all_energy_causal.py` executes all 44 energy/causal jobs independently, recording failures without blocking unrelated cohorts. If any energy/causal task fails, the all-in-one CMD stops before AC so the failure can be reviewed. AC replay itself continues over independent cases and records each failure without claiming feasibility.

## Alternatively, run each complete stage yourself

**All household configurations, annual energy:**

The source v1.1 portfolio runner is also available for individual stages. It stops at the first failure, unlike the new `run_all_energy_causal.py` batch which continues over independent jobs.

```bat
python "case1\studies\SEEDExchange_StudyA_PVBESS_v1\run_portfolio.py" --repo-root . --stage all-energy --run
```

**All causal PV-first dispatches:**

```bat
python "case1\studies\SEEDExchange_StudyA_PVBESS_v1\run_portfolio.py" --repo-root . --stage all-causal --run
```

**Annual AC for all cohorts, hardware candidates and both dispatch types, PF .98 and length 1.0:**

```bat
python "case1\studies\SEEDExchange_StudyA_PVBESS_AnnualPortfolio_v1\run_annual_replays.py" --repo-root . --scope baseline --dispatch both --run
```

**Annual AC for all remaining PF/length sensitivity combinations:**

```bat
python "case1\studies\SEEDExchange_StudyA_PVBESS_AnnualPortfolio_v1\run_annual_replays.py" --repo-root . --scope sensitivities --dispatch both --run
```

The program also supports filtering by transformer, assignment, tier, source reference vs new four-house design and dispatch. Without filters, it does **not** restrict execution to 106039 or to 24-hour windows. `--scope full` requests all nine PF/length combinations including the baseline; verified outputs are reused.

## Output and verification

Original signed energy and causal folders are saved under:

`case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\pvbess_phase_01\`

Each annual AC case goes to a **new, unique directory** under:

`...\pvbess_phase_01\annual_ac_replays_v1\`

An AC output is reused **only if** `ac_summary.json` and `ac_hourly.csv` exist, match the signature, use the expected cohort/hardware/topology/dispatch/PF/length, contain exactly 8,760 rows, and reference the signed input and energy manifests. Partial folders trigger explicit errors, never silent overwrites. New execution receipts `annual_AC_replay_receipt_*.json` list completed, reused and failed cases.

When complete, share the receipts and the annual AC folders (ZIP/7z, split into parts if needed). To review an interrupted batch, first upload the receipt and the affected case summary files.

## Engineering limitations that remain

- Annual balanced three-phase AC proxy, **not** a field certification or phase-unbalanced utility-verified model.
- 92395 STAR/MST are **proposed** radial geometries, not proof of existing conductor routes.
- Equipment refs are archived energy-screen selections. New geographic optimization is only done for the explicit four-house jobs in this package.
- Optimized and causal schedules are compared using the same hardware. Check initial/terminal SOC. PV-first cannot charge the battery from grid; zero export.
- AC replay is **post hoc**. An AC violation is reported honestly, not silently eliminated by the PyPSA model. This phase does not automatically re-optimize dispatch to satisfy AC.
- PF and feeder-length sensitivities rerun AC using the same stored optimized/causal dispatch; do not claim each PF is a separately reoptimized energy system.
- The historical gross-demand 90-case study remains the comparison baseline for subsequent net AC analyses.

No source code in the frozen v6.2 runner, original PyPSA / pandapower modules or GitLab repository is modified by this package.
