# SEEDExchange WP1, robustness and equipment-shortlist gate v1.3

**Study date:** 4 November 2026. **Authoritative code base:** `KKhan02/resilient-energy-systems`, branch `main`, reported original revision `e377e21d26db4bffd7a164d1257d5860bb01f325`.

## Purpose and scope

Continue the **seven-house transformer 94022** study from its newly AC-feasible full-year redispatch. The previous reoptimized trajectory has 8,760 converged and AC-feasible hours **only for the assumed reference feeder** (PF 0.98, service factor 1.0, head inverter, equal household synthetic load allocation, 0.97–1.03 pu voltage and 100% thermal limits). Minimum voltage is 0.970098728 pu. The research baseline is **not field-certified**.

Two separate next gates are implemented in this additive package:

1. **Robustness screen:** Replay the exact validated 8,760-hour P and SOC trajectory in pandapower, varying PF and assumed service lengths. The script does **not** reoptimize battery charge/discharge or SOC for each varied case. It evaluates Q under the pre-existing coordinated-Q algorithm with **nighttime Q off**. Any updated economic results require a new solve.
2. **Hardware shortlist:** Rank a diverse subset from the existing **6,840-task PyPSA energy-only campaign**, including PV panels, battery module energy, battery power and inverter capacities. These are candidates for future manufacturer-SOC, AC-aware *new* optimization, not final designs or AC-passing cases. New equipment candidates require their own AC operating regions; copying P corridors from the seven-house configuration is invalid.

### What has been prepared from uploaded results

The original annual AC and dispatch CSVs in this conversation identify **41 hours** with minimum household voltage below 0.975 pu. The deterministic critical sampler adds electrical and demand peaks and each month's minimum-voltage hour, giving **77 unique hours** for the first robustness screen. See `reference_checkpoint/REFERENCE_CHECKPOINT.md`, the 77-hour CSV and the reference voltage histogram. These are pre-existing reference results, not sensitivity outputs.

## Installation

This ZIP is **additive**. Extract at the root of the complete local GitLab repository, e.g. `D:\0. UoL\3rd Sem\5.06.M308 Resilient Energy Systems\resilient-energy-systems`. It adds:

- `case1/studies/ac_aware_redispatch_v1/run_robustness.py`
- `case1/studies/ac_aware_redispatch_v1/shortlist_equipment.py`
- `case1/studies/ac_aware_redispatch_v1/plot_robustness.py`
- `case1/studies/ac_aware_redispatch_v1/tests/test_robustness_shortlist.py`
- `case1/studies/ac_aware_redispatch_v1/reference_checkpoint/` (source-derived checkpoint evidence)
- this README

It does not overwrite the earlier PyPSA solver, pandapower model, pilot, original output directories or prior manuscripts. No GitLab commit or pipeline has been run to produce this package.

The existing v1.1 pilot and v1.2 annual feedback modules must already be present, as in your local working copy. **Do not extract v1.3 into a new empty repository.**

## 1. Initial tests

From the GitLab repository root:

```powershell
python -m pytest -q case1/studies/ac_aware_redispatch_v1/tests
```

Tests are self-contained, but integrated AC calculations require your existing PyPSA/pandapower/HiGHS environment.

## 2. Robustness, first critical-hour screen

Use the **feedback trajectory** (`seven_annual_feedback_01`) and its **independently validated full-year AC replay** (`seven_annual_feedback_ac_check_01`). If you used different output names, substitute those directories.

```powershell
python case1/studies/ac_aware_redispatch_v1/run_robustness.py --repo-root . --feedback-dir case1/studies/ac_aware_redispatch_v1/outputs/seven_annual_feedback_01 --annual-dir case1/studies/ac_aware_redispatch_v1/outputs/seven_annual_feedback_ac_check_01 --outdir case1/studies/ac_aware_redispatch_v1/outputs/seven_robustness_critical_01 --mode critical --power-factors 0.98 0.95 0.90 --service-factors 1.0 1.3 1.6 --q-grid-points 9 --q-refine 0
```

The script checks source trajectory hash, source pilot hash, membership, fixed hardware, 8,760 aligned timestamps, SOC consistency, successful source AC replay, and reference-case voltage reproduction (default 0.00005 pu tolerance). It refuses mismatched files and existing output directories.

Outputs:

- `evaluated_hour_indices.csv`: the 77 baseline critical hours selected using the uploaded 2025 reference data (your exact number may change if source inputs change).
- `sensitivity_ac_hours.csv`: a row per tested hour and sensitivity pair, including convergence, Q, voltage and thermal loading.
- `sensitivity_scenarios.csv`: conditional pass/fail summaries. A passing **critical** sample remains `CRITICAL_SAMPLE_PASS_ONLY`, never an annual feasibility claim.
- `robustness_manifest.json`: source hashes, Git revision, cases, assumptions, performance metadata.

Plot the completed sensitivity results using:

```powershell
python case1/studies/ac_aware_redispatch_v1/plot_robustness.py --results-dir case1/studies/ac_aware_redispatch_v1/outputs/seven_robustness_critical_01
```

This writes PNG and SVG plots in `figures/` with the sampled minimum voltage and failed-hour count for each PF/length combination.

## 3. Full-year test at selected sensitivities

Critical-hour results identify candidate stress scenarios. **A critical failure already disproves that fixed trajectory's feasibility for that case**, but a critical pass requires a complete annual replay before claiming an annual pass.

For example, to check a selected less favorable case:

```powershell
python case1/studies/ac_aware_redispatch_v1/run_robustness.py --repo-root . --feedback-dir case1/studies/ac_aware_redispatch_v1/outputs/seven_annual_feedback_01 --annual-dir case1/studies/ac_aware_redispatch_v1/outputs/seven_annual_feedback_ac_check_01 --outdir case1/studies/ac_aware_redispatch_v1/outputs/seven_robustness_pf095_len13_full_01 --mode full --power-factors 0.95 --service-factors 1.3 --q-grid-points 9 --q-refine 0
```

Do **not** claim that a changed PF/length is annual feasible because the old 94022 baseline passed 8,760 hours. All sensitivity cases are counterfactual assumptions. No EPM-backed probability distributions or tolerances have been established for these PF and service-length factors.

If a case fails and is selected for further study, a later version must calculate feasible P/Q regions at the **modified PF and feeder geometry**, then reoptimize 8,760-hour storage SOC using those constraints, and independently revalidate all hours. Existing fixed-P corridors cannot be reused across these changed assumptions. If full-year AC feedback remains infeasible, it becomes an input to equipment re-sizing or service reinforcement scenarios.

## 4. Equipment sizing shortlist from the original 6,840-task campaign

This can run without waiting for the AC robustness simulation. It does not reoptimize anything:

```powershell
python case1/studies/ac_aware_redispatch_v1/shortlist_equipment.py --repo-root . --outdir case1/studies/ac_aware_redispatch_v1/outputs/equipment_energy_shortlist_01 --cases 7_homes 9_homes 12_homes --assumed-trafo-kva 5 --max-per-case 20
```

Outputs:

- `equipment_shortlist_energy_only.csv` selects cost, self-sufficiency target and equipment-diversity representatives.
- `saved_sampled_energy_cost_frontiers.csv` contains **nondominated rows among sampled saved designs**, not a proved complete Pareto frontier.
- `equipment_shortlist_manifest.json` gives source CSV hash, selection counts and all outstanding manufacturer/AC gates.

These old results had **perfect foresight** and did **not** enforce the updated SE-G5.1 20% physical minimum SOC in the accepted new way, nor did they include AC line losses in optimized battery dispatch. Their PV/BESS costs exclude site-specific LV installation, protection and permitting. The model also assigns zero separately sourced incremental battery power-electronics cost, so battery-power selections can be economically degenerate. They must be treated as a shortlist to be verified, not new recommended installations. Further combined PV/battery-power/inverter size combinations should be explored after this screen.

**The household sweep is not omitted:** 7, 9 and 12 anchor configurations are evaluated first; the full source has 5–15-house scenario results, but using them as GIS-verified electrical territories without actual customer mapping would be unjustified. Further household cases need explicit GIS memberships/transformer territories and a new selection protocol.

## 5. Twelve-house / transformer 106039 next pilot

The existing v1.1 pilot also supports `--case twelve`, with the saved **41 panels, 8 battery modules, 12 kW battery power and 12 kVA inverter**. EPM transformer **106039** is studied under a **hypothetical 5 kVA** assumption. This is a different problem, with 12 assumed houses and different network geography. Do not copy the seven-house corridors.

After checking the seven-house robustness screen, begin the twelve-house diagnostic pilot with a fresh output path:

```powershell
python case1/studies/ac_aware_redispatch_v1/run_pilot.py --repo-root . --case twelve --outdir case1/studies/ac_aware_redispatch_v1/outputs/twelve_pilot_01 --night-q off --p-grid-points 7 --q-grid-points 9 --q-refine 0 --max-hours 12
```

Only after reviewing that pilot should an 8,760-hour manufacturer-SOC baseline AC replay and AC-feedback study proceed. The earlier 106039 8,760-hour Q-enabled reference had minimum 0.970005 pu and allowed nighttime reactive capability that is not established for the quoted inverter. It is **not** interchangeable with the night-Q-off, manufacturer-SOC test proposed here.

## 6. Research decision record

- No adaptive SOC reserve heuristic: the earlier heuristic lacks an established research basis. Retain manufacturer 20% physical SOC floor and existing cyclic year energy equations for the planning benchmark.
- Nighttime Q **off** for the primary scenario. The on-case is deferred pending identification and literature/manufacturer review of the exact inverter model, including DC-link supply and loss effects.
- PF 0.98/0.95/0.90 and length factor 1.0/1.3/1.6 are **explicit stress assumptions**, not field-measured statistical distributions.
- No real EPM customer-to-transformer service assignment, conductor impedance, phase mapping or precise rating verified beyond the archived evidence; the balanced equivalent remains a conditional screen.
- Current 0.97–1.03 pu and 100% loading are **study criteria**, not utility operating settings.
- Maintain the original 6,840-task campaign and all saved historical results. Do not downgrade or overwrite simulations.
- After this stage, refine AC P sampling around weak hours based on runtime/convergence tests, then extend joint equipment sizing, hosting limits and resilience scenarios.

## Completion status in this package

**Implemented and tested locally:** file consistency checks, critical-hour selection, robustness-sweep orchestration, equipment shortlist logic and visualization. The uploaded 94022 annual source data were audited to create the 77-hour checkpoint.

**Not run here:** pandapower 9-scenario robustness calculations, sensitivity-specific redispatch, PyPSA resizing, 106039 pilot, equipment electrical validation or inverter literature verification. The local environment lacks PyPSA/Linopy/pandapower. Do not label any of these unperformed studies complete.
