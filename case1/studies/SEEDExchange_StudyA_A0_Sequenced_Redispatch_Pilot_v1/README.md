# Study A, A0 conservative sequenced AC-aware redispatch pilot

**Purpose:** determine whether A0 106039 archived hardware can be repaired by conservative same-day battery discharge shifts, without altering source models or equipment. This is a **pilot**, not a complete multi-hour AC-aware optimization. **A0 94022 and the 92395 MST/Study B network remain uncorrected.**

## Verified preflight

All 175 mapped events, 5,075 SOC-window records and 16 source schedules were audited. A0 accounts for 156 events in eight signed source schedules: A0 106039 44 events (33 schedule-specific day blocks, 11 with multiple failing hours); A0 94022 112 events (76 day blocks, 32 with multiple failures). The exact zipped window archive is bundled and SHA-256 pinned.

The main target is transformer 106039, 12 provisional households on the *existing modelled* LV connections, **5 kVA unverified transformer nameplate assumption**. Earlier reported A0 max transformer loading 119.379% under PF/route sensitivity is a modelled AC result, not a manufacturer nameplate observation.

## Installation and commands

Unzip this directory to `case1\studies\SEEDExchange_StudyA_A0_Sequenced_Redispatch_Pilot_v1` in your already prepared GitLab root. Keep `SEEDExchange_StudyA_PVBESS_v1/study_a_pvbess.py`, the signed v6.2 runner, demand profiles, and annual source output folders unchanged.

Execute in **Miniforge Prompt or Anaconda Prompt**, with working directory set to your GitLab repository root:

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_A0_Sequenced_Redispatch_Pilot_v1\tests" -v
python "case1\studies\SEEDExchange_StudyA_A0_Sequenced_Redispatch_Pilot_v1\a0_sequenced_trial.py" --preflight
python "case1\studies\SEEDExchange_StudyA_A0_Sequenced_Redispatch_Pilot_v1\a0_sequenced_trial.py" --repo-root . --transformer 106039 --out "StudyA_A0_106039_Sequenced_Trial_v1" --zip-out "StudyA_A0_106039_Sequenced_Trial_v1.zip"
```

Upload the resulting `StudyA_A0_106039_Sequenced_Trial_v1.zip`, **even if it reports partial success**. A failed or unresolved event is valid research evidence; do not modify limits to get a passing result.

Optional later expansion, **only after inspecting the 106039 pilot**:

```bat
python "case1\studies\SEEDExchange_StudyA_A0_Sequenced_Redispatch_Pilot_v1\a0_sequenced_trial.py" --repo-root . --transformer 94022 --out "StudyA_A0_94022_Sequenced_Trial_v1" --zip-out "StudyA_A0_94022_Sequenced_Trial_v1.zip"
```

## Rules of the experiment

- All local annual energy and AC source checks remain mandatory: exact cohort/2025 trace, hardware, SHA-256, hourly AC convergence, baseline source AC reproducibility and exact PF/length setting.
- Try small bounded transfers of DC discharge from earlier on the same local calendar day, subject to DC power, AC inverter, SOC, imported-energy, zero export, zero unmet load and unchanged annual curtailment.
- For each attempted transfer independently replay both donor and receiver at **PF 0.95/0.98/1.00 × feeder multiplier 1.0/1.3/1.6**. Reject a transfer if it causes any new AC violation.
- If a donor is itself an earlier repaired target hour, it **must** still pass all nine cases after the new change. Recheck all final changed hours, and reuse only unchanged signed original AC hours.
- The model is a **sequential greedy feasibility trial**. It does not jointly optimize the day's multiple events; it can leave failures because a later event has insufficient safe donor energy. Joint-day/annual PyPSA + AC corridors is the fallback when this trial cannot fix all events.
- Source files are never overwritten. The output directory and ZIP must not exist before a run. Do not remove or overwrite original source manifests or signed 432-case AC runs.
- A fully passing status means **only the requested pilot subset**, not all A0 configurations, and still conditional on the proposed balanced AC and provisional household network assumptions.
- PV curtailment is not reduced. Hardware sizing, marginal storage, real inverter controls, site protection, outage resilience and actual EPM nameplate/phase verification remain separate work.

## Evidence and tests

- `StudyA_Mapped_SOC_Windows_for_Redispatch.zip`: original exact SHA-256 pinned archival input, *not* a new simulation.
- `A0_109_DAY_GROUP_EVIDENCE.csv`: read-only 109-block summary. Earlier observed DC discharge is **not** assumed to be AC-safe donor capacity.
- `a0_sequenced_trial.py`: A0-specific adaptation of the previously regression-tested A1 runner, preserves all source verification and AC safeguards. The A0 solver path has **not been run in this environment** without the original local signed model and pandapower source files.
- `tests/test_a0_sequenced.py`: five standalone checks of source-window provenance, event grouping, 2025 energy balance and safe-shift invariants.
