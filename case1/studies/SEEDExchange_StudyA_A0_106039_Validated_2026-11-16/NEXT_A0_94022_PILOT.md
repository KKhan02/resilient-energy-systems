# Next local pilot | A0 94022 mapped LV, sequenced redispatch

The already-distributed `SEEDExchange_StudyA_A0_Sequenced_Redispatch_Pilot_v1.zip` supports `--transformer 94022` using **the same** source-pinned, SOC-aware, nine-factor AC-validated algorithm. No updated model or new optimization package is needed yet.

The remaining mapped A0 94022 source is **112 distinct design-hour violations across four min-cost/SS90 and optimized/causal schedules**, in **76 schedule-specific days**, **32** with two or more events. The source portfolio still has **32 failing PF/route scenario runs** on 94022. These are *not* identical to 32 distinct clock-hours.

## Run in Miniforge/Anaconda Prompt, from your GitLab repository root

Ensure the previously supplied trial package is extracted to `case1\studies\SEEDExchange_StudyA_A0_Sequenced_Redispatch_Pilot_v1`. Keep all original annual results unchanged.

```bat
python "case1\studies\SEEDExchange_StudyA_A0_Sequenced_Redispatch_Pilot_v1\a0_sequenced_trial.py" --repo-root . --transformer 94022 --out "StudyA_A0_94022_Sequenced_Trial_v1" --zip-out "StudyA_A0_94022_Sequenced_Trial_v1.zip"
```

Upload `StudyA_A0_94022_Sequenced_Trial_v1.zip` even if it ends in `PARTIAL_OR_UNRESOLVED`. The runner checks every shifted donor and target hour in all nine PF/length combinations, preserves full-year SOC and signed sources, and re-evaluates every changed hour. If a candidate cannot pass, it reports the unresolved case rather than silently relaxing the limits.

## Scientific interpretation gates

1. Require every source hash, 2025 hourly chronology, no export/ENS and full SOC recurrence to pass before a numerical claim.
2. Check all 9 PF×length cases per schedule, changed hours, no newly induced violations and adequate **margin**, not merely pass/fail.
3. Preserve the original 432-case annual AC baseline and put the correction in a separate overlay.
4. If 94022 is only marginally feasible, compare buffer targets e.g. 0.955 pu voltage and <=95% transformer loading as *research stress margin tests*, not established utility rules.
5. Do not apply this battery-shift heuristic to the 92395 **proposed MST** as though its internal voltage drop were an energy deficit. Evaluate conductor sizing, inverter location and STAR versus MST architecture in Study B.
6. Start PV curtailment/marginal battery sizing as a separate analysis. The successful SOC shifts have not changed annual solar utilization or proven minimum LCOE.

No GitLab commits, source overwrites or 432-case reruns are needed for this pilot.
