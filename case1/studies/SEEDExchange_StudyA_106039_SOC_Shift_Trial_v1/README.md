# SEEDExchange | Study A A1 / transformer 106039 | battery-discharge timing trial

Status: **candidate validated for energy/SOC algebra against the uploaded signed 14-day excerpts, NOT yet AC-validated**.

## Why this trial is needed

- **27 November 2025, 20:00 LST:** both existing A1 106039 equipment tiers have 0 kW inverter output because the usable battery state is already at its 1.832 kWh operational lower bound. Full-year prior AC result: 103.491672% loading (PF 0.98, length 1.0), rising to 107.431169% at PF 0.95, length 1.6. No voltage violation on those hours under 0.95–1.05 pu.
- **13 October 2025, 20:00 LST:** minimum-cost equipment gives just 0.256078 kW inverter output and 103.195603% transformer loading in PF 0.95, length 1.6. The higher-SS equipment already covers that hour.
- Battery bank **power is not the limiting factor at these events**. The schedule has consumed its permitted energy earlier in the evening.

## Source-grounded trial modification

| Tier | Save discharge at | Add same discharge at | Discharge shifted (solar-bus DC kW) | Added at target (AC kW) | Temporary extra usable SOC (kWh) |
|---|---|---|---:|---:|---:|
| Minimum cost | 13 Oct 17:00 | 13 Oct 20:00 | 0.60 | 0.57 | 0.616 |
| Minimum cost | 27 Nov 18:00 | 27 Nov 20:00 | 0.80 | 0.76 | 0.821 |
| Higher SS | 27 Nov 18:00 | 27 Nov 20:00 | 0.80 | 0.76 | 0.821 |

The source hour imports more from the grid, while the target hour imports less. Battery usable SOC is temporarily higher between the two hours, then exactly returns to the original annual schedule. The original battery modules and power ratings, 20% physical SOC floor, zero grid export, zero grid charging, and cyclic annual SOC are preserved. Total annual energy-only grid imports are unchanged. AC losses and resulting economics are not assumed unchanged.

These shifts are **test values, not solved-optimal setpoints**. They are chosen to provide headroom beyond the observed overloads. They will only be accepted if independently re-solved with the original AC feeder model.

## Local commands, from Windows Miniforge/Anaconda Prompt

Extract this directory into `case1\studies\` without replacing or changing any existing script. Run from the repository root:

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_106039_SOC_Shift_Trial_v1\tests" -v

python "case1\studies\SEEDExchange_StudyA_106039_SOC_Shift_Trial_v1\studya_106039_soc_shift_trial.py" --repo-root . --dry-run

python "case1\studies\SEEDExchange_StudyA_106039_SOC_Shift_Trial_v1\studya_106039_soc_shift_trial.py" --repo-root . --out StudyA_A1_106039_Redispatch_Trial_v1
```

The last command **does not rerun PyPSA**. It reads and verifies signed 8,760-hour optimized energy trajectories and AC outputs for both equipment tiers and all 9 PF × length factors, checks battery/AC/DC energy and the SOC trajectory, and independently recomputes **only the changed AC hours**. It verifies the original AC solver reproduces the original signed hour results. It then combines revalidated changed-hour records with verified unchanged original annual AC records to calculate 8,760-hour annual violation counts. This is valid for the existing **stateless hourly AC solver**, which starts from flat voltage on every hour and evaluates Q from the current hour's inputs.

No historical annual result, source model, source signed manifest, or GitLab file is changed. The new output folder must not already exist. If a rerun is needed, pass a different `--out` name.

## What to upload

Zip the new `StudyA_A1_106039_Redispatch_Trial_v1` folder and upload it. It includes:

- `trial_manifest.json`, with original source SHA references and explicit status.
- `nine_factor_annual_reuse_comparisons.csv`, with original and corrected AC violation counts across both tiers and nine conditions each.
- `changed_hour_ac_checks.csv`, baseline versus candidate power-flow tests.
- `A1_106039_{min_cost_ref,ss90_ref}_candidate_8760.csv`, both full-year fixed-hardware candidate schedules.
- `candidate_shifts.csv`, a reproducible change register.

Do not present the candidate as an optimized economic dispatch. If any AC case fails, the output explicitly says `CANDIDATE_NOT_FULLY_FEASIBLE`; we can adjust shifts and rerun under a new output name.

## Notes

- The model's transformer 106039 reference capacity is a **hypothetical/assumed 5 kVA**, not a certified EPM nameplate.
- Results are for the **provisional balanced AC feeder**, not field protection/islanding certification.
- Annual operations are energy-only after this manual timing change. The procedure does not claim to re-optimize original PyPSA/Linopy objectives.
- Hardware device-level communications, scheduling/forecast uncertainty, reactive-power manufacturer permission and service phases remain open.
- This experiment is limited to A1 106039; it does not establish full-system robust feasibility at other transformer territories.
