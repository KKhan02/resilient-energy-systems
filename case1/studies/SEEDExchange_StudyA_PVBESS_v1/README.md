# Study A PV+BESS phase 1: local execution package

**Launcher maintenance release v1.1 (2026-11-08):** The portfolio launcher now creates the missing `pvbess_phase_01` parent directory **after** validating the source manifest and checking for existing completed/partial output, **before** launching the first simulator. This fixes the user-reported `ValueError: Create output parent before running` on the first 106039 A0 pilot. Neither the signed v6.2 runner nor its manifest changes. The `--run` flag is still required to execute a numerical task; dry runs still write nothing.

**Scope:** source-grounded 35-home A0/A1 transformer cohorts, eight mapped cohort scenarios and the four-home 92395 proposal under STAR/MST. Original PyPSA and v6.2 EPM source files are **not altered**. No historical 6,840-case investment sweep is rerun. All numerical work happens on your local Windows checkout using Miniforge Prompt or Anaconda Prompt.

## Implementation / model boundaries

- The existing signed `SEEDExchange_StudyA_v6_LocalRunner/seed_study_a_v6.py` is reused **unchanged**. The A0/A1 manifest remains signed by SHA256. Do not replace it with any code from this package.
- The `run_portfolio.py` wrapper plans up to **16 archived-hardware reference re-dispatch jobs**, one for each of the eight A0/A1 mapped cohorts at min-cost and archived ≥90%-SS source anchor. This does **not** claim that archived hardware or historic costs have been re-optimized for new geographic households.
- `study_a_pvbess.py four-opt` creates **six new dedicated 4-house hardware MILPs**: A0 113699, A0 85398 and 92395 A0=A1, each at (a) lowest annual cost with PV and ≥1 battery module and (b) >=90% annual self-sufficiency constrained cost minimum (if feasible). Uses original `model.py` cost/PCC model with new geographic profiles, original PyPSA default expansion bounds (64 panels, 16 modules, 24 kW DC battery, 24 kVA inverter), discrete source Deye-family inverter sizes, 20% physical SOC minimum, no export, no ENS and conservative manufacturer continuous-power screen 2.24 kW per module. Cost is the source annualized equipment + import estimate; service routes, protection, balance-of-system and utility works are **not priced**. Inverter choices 20/24 kVA require separate actual manufacturer/parallel-operation approval; they remain source-model screening options, not a recommended four-house device.
- Separate `four-causal` runs compare no-lookahead PV-first scheduling with optimal cyclic PyPSA for same new 4-house design. **Final SOC is not forced equal**. Do not interpret raw annual import differences as like-for-like economics without normalizing terminal SOC.
- Existing v6.2 `causal` handles the 16 reference cases. New `replay` handles both mapped and **92395 proposed STAR/MST** AC networks; it reuses the signed v6.2 node-specific P/Q and steady-state daylight Q-control. This is post-optimization AC replay, **not a closed-loop AC-constrained re-optimization**.
- The original 92395 proposed feeder code is required: `case1/studies/SEEDExchange_StudyA_92395_STAR_MST_v1/run_92395_star_mst.py`. It must be present and unchanged from its previously tested package; no claim that GIS lacks real service, only that proposed electrical geometry is hypothetical.

## Install

Extract `SEEDExchange_StudyA_PVBESS_v1` directly to `case1\studies\` alongside existing v6.2 and 92395 packages. Do not modify any historical results or files. Use a Python environment with the existing `pypsa`, `linopy`, `highs`, `pandapower`, `numpy`, `pandas`, `networkx`, `scipy`, `shapely` and `pyproj`.

From the repository root, test and inspect the planned portfolio:

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_PVBESS_v1\tests" -v
python "case1\studies\SEEDExchange_StudyA_PVBESS_v1\run_portfolio.py" --repo-root . --stage all-energy
```

These **do not launch numerical solvers**. Expect 22 planned energy jobs (16 source hardware references + 6 dedicated four-house MILPs).

## Pilot first

First try 106039 A0 minimum-cost **source hardware** for 2025 annual dispatch (new geography, existing hardware) and use its signed output for causal replay.

```bat
python "case1\studies\SEEDExchange_StudyA_PVBESS_v1\run_portfolio.py" --repo-root . --stage mapped-energy --transformer 106039 --assignment A0 --run
```

This command runs both `min_cost` and `ss90` source references for that cohort. If one fails, the runner stops and preserves successful output. Report the error; do not claim feasibility.

Then a separate new *four-house hardware investment* trial for 92395:

```bat
python "case1\studies\SEEDExchange_StudyA_PVBESS_v1\run_portfolio.py" --repo-root . --stage four-opt --transformer 92395 --run
```

The 92395 trial uses the source equipment and transformer/PCC energy-screen assumptions. STAR/MST is a separate later AC validation, not part of the energy-only MILP. If the 90% target is infeasible, report it, do not substitute an invented hardware design.

After inspecting the pilot manifests and metrics, run the full energy phase (skips already verified complete outputs without overwriting):

```bat
python "case1\studies\SEEDExchange_StudyA_PVBESS_v1\run_portfolio.py" --repo-root . --stage all-energy --run
```

Then run causal sensitivity on *all completed energy cases*:

```bat
python "case1\studies\SEEDExchange_StudyA_PVBESS_v1\run_portfolio.py" --repo-root . --stage all-causal --run
```

This writes under the new and separate `...\outputs\run_01\pvbess_phase_01\` directory. Existing prior folders remain untouched. Outputs contain `energy_hourly_2025.csv`, `energy_manifest.json`, and optionally `causal_pv_first_2025.csv` plus `causal_summary.json`.

## AC replay sample after first energy review

A0 106039 min-cost 24-hour smoke on the **existing mapped GIS feeder**:

```bat
python "case1\studies\SEEDExchange_StudyA_PVBESS_v1\study_a_pvbess.py" --repo-root . replay --assignment A0 --transformer 106039 --topology mapped --energy-dir "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\pvbess_phase_01\energy_A0_106039_min_cost_ref" --hours 24 --outdir "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\pvbess_phase_01\ac_A0_106039_min_cost_24h"
```

For 92395 with new 4-house min-cost hardware, use both explicitly proposed topologies in separate outputs:

```bat
python "case1\studies\SEEDExchange_StudyA_PVBESS_v1\study_a_pvbess.py" --repo-root . replay --assignment A0 --transformer 92395 --topology star --energy-dir "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\pvbess_phase_01\energy_A0_92395_min_cost_four" --hours 24 --outdir "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\pvbess_phase_01\ac_92395_star_min_cost_24h"
python "case1\studies\SEEDExchange_StudyA_PVBESS_v1\study_a_pvbess.py" --repo-root . replay --assignment A0 --transformer 92395 --topology mst --energy-dir "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\pvbess_phase_01\energy_A0_92395_min_cost_four" --hours 24 --outdir "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\pvbess_phase_01\ac_92395_mst_min_cost_24h"
```

After review, re-run with `--hours 8760` and **new output directory**. Later vary `--pf .95`, `--pf 1`, `--length 1.3`, `--length 1.6` for shortlisted and adverse cases. Battery/inverter head-only siting and daylight reactive support are first references; do not claim final siting/control optimization.

## Results to upload

For pilots: share each `energy_manifest.json` and `energy_hourly_2025.csv`, and `ac_summary.json` / `ac_hourly.csv` from each 24h AC test. For the full phase, compress the *new* `pvbess_phase_01` folder into a ZIP/7z archive. Keep all manifests/CSV identities and timestamps.

## Current status

The wrapper and figure assets were authored and syntactically/unit tested in the assistant's environment. **No new PV+BESS numerical solve has been run here.** Source PyPSA/pandapower solver environments and full local source profiles must execute on your workstation. A numerical failure or target infeasibility must remain explicit.
