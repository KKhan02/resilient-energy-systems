# SEEDExchange Study A v6, local-first annual validation runner

**Updated:** 8 November 2026, v6.2 transformer-position assignment correction. **Status:** Source-reviewed; isolated synthetic regression tests are included and must pass before the user runs prepare. **Not validated against the user's actual v4 run_02 CSV schemas or local pandapower/PyPSA environment. No new 8,760-hour numerical results.** Read-only GitLab revision consulted: `9aaca5473838b69de442cb238ba40a0e97405844`. Do not commit this package or its output to GitLab without fresh approval.

## Purpose

Continue the approved existing-EPM Study A. Compare original provisional 35-house associations (A0) and the **six-territory nearest-transformer-position A1 cohort comparison**: H03 and H06 to 113699, H13 to 85398. A1 computes transformer ownership from household-to-transformer projected distance among the original six EPM territories. In this saved GIS evidence it yields only H03/H06/H13 moves. **Only after transformer selection**, moved houses attach provisionally to an LV section of that transformer for AC graph construction. Missing LV geometry is not evidence of missing electrical service. This is not the unrestricted `nearest_mapped` policy in the original EPM topology module. Preserve **35 different hourly household traces** as distinct P(t) and Q(t) injections at the GIS-attached house buses. Do not use the old annual EPM `equal` load allocation as a substitute. Reference the historical minimum-cost hardware and an **original 90%-self-sufficiency source candidate** separately. Treat the historic cost/SS as *source selection only*, not as a result for the new cohorts. Run a full-year manufacturer-SOC fixed-hardware PyPSA dispatch and then the independent AC replay. Include a separate causal PV-first dispatch sensitivity and battery utilization/curtailment metrics.

The **eight GIS-preflight-eligible cases** are 94022 (10 A0, 8 A1), 106039 (12 A0, 11 A1), 113699 (4 A0, 6 A1), 85398 (4 A0, 5 A1). Transformer 92395 is recorded but its LV sections are absent from the extracted dataset. Its actual service connections are unknown; load-only screening is possible, while this runner cannot construct a source-backed AC graph. 98380 is support-only. Additional 113306 is a separate proximity sensitivity, not silently inserted in A1. Northern 25 kVA transformer is excluded. Four-house candidates borrowed from the archived five-house data are **proxies**, not four-house economic optima. 113699 uses the research evidence 3-kVA rating, while 106039 uses the user-approved hypothetical 5-kVA value.

## v6.2 correction, 8 November 2026

The **user confirms** assignment must follow proximity to **transformer locations**. Source LV segments should be used exclusively for *provisional attachment geometry and AC feeder validation*, never as the transformer assignment criterion. Missing LV GIS does **not** establish absence of actual LV cables. v6.1 had hard-coded three known movements and used LV sections to place moved household taps. v6.2 now calculates all A1 transformer assignments directly from the six original EPM transformer coordinates and treats those three moves only as a **regression check**. This independently reproduces the original approved v4 A0/A1 group counts while preserving H30–H33 on 92395, which lacks extracted LV segments.

**Do not conflate transformer distance with complete electrical viability.** Nearest transformer is a geographic starting hypothesis. The resulting service branches, voltage, phase, transformer loading and EPM approval are unverified. Transformer 113306, near H32/H33, is another existing EPM asset to consider in a **separately approved option**, not in these first six-territory matched comparisons. Under seven-transformer nearest selection, H32/H33 would choose 113306, but no 113306 load-flow acceptance or existing-customer spare capacity is established.

**Install:** Extract `SEEDExchange_StudyA_v6_2_Patch.zip` into `case1\studies\` of the existing full checkout, replacing the previous v6/v6.1 files of the same name. Keep your `outputs` folder. Then run tests and prepare with the same commands below. Use new output paths if prior attempts succeeded. Prepared manifests are immutable because they include a hash of the current runner.

## Installation

Extract this folder inside the original **full** GitLab checkout as:

`case1\studies\SEEDExchange_StudyA_v6_LocalRunner\`

Use **Miniforge Prompt or Anaconda Prompt**, never PowerShell. Change directory to your local `resilient-energy-systems` checkout root, the directory containing `.git`. Use an environment with the existing PyPSA, Linopy, solver, pandapower, scipy, shapely, pandas and numpy dependencies that your historical models already use. The `prepare` and test stages require at least numpy and pandas.

From the repository root, first execute:

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\tests" -v
python "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\seed_study_a_v6.py" inspect --v4-run-dir "case1\studies\SEEDExchange_StudyA_LocalPreflight_v4\outputs\run_02"
```

`inspect` is **read-only** and displays the source CSV column names and two data rows. It allows us to catch a different CSV schema without modifying existing sources. No simulation is run.

Create one new output parent (only this new folder, not a historical results directory):

```bat
mkdir "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01"
```

The following creates an immutable input manifest only if all source profiles, GIS associations and hashes pass:

```bat
python "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\seed_study_a_v6.py" prepare --repo-root . --v4-run-dir "case1\studies\SEEDExchange_StudyA_LocalPreflight_v4\outputs\run_02" --out "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\input_manifest_v6_2.json"
```

If this fails because columns differ from the anticipated `house_id`/`profile_index` or `timestamp_lst`/`house_01_kw` naming, **return the inspection output**. Do not edit or overwrite the v4 files. The runner intentionally fails closed rather than guessing profile identities or changing input measurements.

## First numerical gate: gross AC smoke test, 24 hours

Do this before launching any 8,760-hour solve. Here is the 12-home case, with both customer assignments. It reads distinct household kW traces, converts each to kvar using PF 0.98 and uses the original source GIS network builder. No PV or BESS runs at this gate.

```bat
python "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\seed_study_a_v6.py" ac --manifest "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\input_manifest_v6_2.json" --assignment A0 --transformer 106039 --mode gross --hours 24 --outdir "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\gross_A0_106039_smoke_24h"
python "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\seed_study_a_v6.py" ac --manifest "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\input_manifest_v6_2.json" --assignment A1 --transformer 106039 --mode gross --hours 24 --outdir "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\gross_A1_106039_smoke_24h"
```

Both outputs must say `PARTIAL_AC_SMOKE_TEST_NOT_AN_ANNUAL_RESULT`. Review voltage, transformer and line loading, convergence and source hashes in `ac_summary.json` and individual hourly results in `ac_hourly.csv`. These are test runs, not annual conclusions. Use new output names for later 8,760-hour jobs.

## Annual manufacturer-SOC energy dispatch, only after preflight review

Run exact A0 hardware minimum-cost **reference** for transformer 106039. Hardware: 41 panels, 8 Deye modules, 12 kW battery DC power, 12 kVA inverter, 5-kVA transformer (hypothetical). The fixed-hardware solver respects its source model's 2025 NASA PV chronology, continuous battery power/current, zero export, no unmet demand and manufacturer minimum physical SOC 20%. It **does not rerun the 6,840 historical investment MILPs**. This is one new 8,760-hour fixed-hardware dispatch for a different cohort, saved into a new folder:

```bat
python "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\seed_study_a_v6.py" energy --manifest "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\input_manifest_v6_2.json" --assignment A0 --transformer 106039 --anchor-tier min_cost --outdir "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\energy_A0_106039_min_cost"
```

For a **higher-self-sufficiency source reference**, use `--anchor-tier ss90` and a distinct output directory. That setting selects the archived Stage A candidate carrying `LOWEST_COST_SS_AT_LEAST_90_PCT` for the corresponding old synthetic household-count case. The old 90% figure is **not** the result for newly georeferenced houses.

## PV+BESS AC and causal PV-first sensitivity

Run the same-hardware, same-customer separate causal dispatch sensitivity against the full-year fixed-hardware output, with no look-ahead, PV to current demand first and then BESS charging from residual PV. It uses the PyPSA optimal model's cyclic end SOC as the shared initial SOC for comparability. A different final SOC is disclosed and **must not be treated as an equal annual cyclic energy comparison**. This sensitivity is standalone and is not automatically substituted for the perfect-foresight optimization.

```bat
python "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\seed_study_a_v6.py" causal --manifest "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\input_manifest_v6_2.json" --assignment A0 --transformer 106039 --anchor-tier min_cost --energy-dir "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\energy_A0_106039_min_cost" --outdir "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\causal_A0_106039_min_cost"
python "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\seed_study_a_v6.py" ac --manifest "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\input_manifest_v6_2.json" --assignment A0 --transformer 106039 --anchor-tier min_cost --mode pvbess --energy-dir "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\energy_A0_106039_min_cost" --hours 24 --outdir "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\pvbess_A0_106039_smoke_24h"
```

Once the smoke output is audited, change `--hours 24` to `--hours 8760` **and use a new unused `--outdir`**. Later, vary `--assignment A0/A1`, the four eligible transformer IDs, `--anchor-tier min_cost/ss90`, `--pf 0.95/0.98/1.00` and `--service-factor 1.0/1.3/1.6`. Do not execute the full Cartesian product by default. Choose sensitivity finalists after examining constraints.

## Status and limitations

- Source ingestion verifies 35 unique named profiles, 8,760 hours each, 1,898 kWh per house and 66,430 kWh total. A0 and A1 preserve the same 35 profile indices, with only three transformer reassignment changes. Hashes are checked on each stage, without altering source files.
- AC uses existing `epm_topology.py`/`run_epm_validation.py` balanced three-phase proxy at a provisional inverter **head** node and `coordinated_q_control.py` for daylight PV+BESS Q. Q is disabled at night. Voltages 0.95–1.05 pu and transformer/line ≤100% are engineering screens. Each house has its own hourly load injection. Default first AC result is a 24-hour partial test, **not** an annual study.
- AC is a separate replay of fixed P trajectories. The model **does not yet close the loop** to reoptimize battery active power and PV curtailment following AC failures. An AC result can expose a failure and trigger a later targeted AC-aware redispatch, not implicitly certify dispatch feasibility.
- The causal PV-first sensitivity uses source-equivalent simple battery/inverter efficiencies and source current bounds but **does not enforce cyclic terminal SOC**, network voltage or battery aging. It reports terminal SOC mismatch, so unadjusted annual import deltas are not a like-for-like energy comparison.
- Real 2025 customer meters, surveyed service cable routes, phase/neutral, upstream EPM load, protection, conductor verification and commercial connection consent remain missing. No field certification is claimed.
- **Four-house historical economic optimizers do not exist.** The two A0 four-house `min_cost` labels in the CLI mean only a borrowed minimum-cost **five-house** tuple, clearly identified as a proxy. The `ss90` tier is borrowed similarly. They are first-stage hardware stress references, not optimized four-house solutions. Targeted four-house economic selection is still required before making economic ranking claims.
- If your actual v4 CSV has a different schema, the parser deliberately fails before an output file is created. Share the `inspect` output, the new `input_manifest_v6_2.json` once prepared, and the two first `ac_summary.json` + hourly files. This allows fixing ingestion without touching source data.
