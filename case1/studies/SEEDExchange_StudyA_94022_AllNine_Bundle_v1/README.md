# SEEDExchange | A0 94022 all-nine targeted resistance-bundle verification

Local **read-only** validation of the recently successful sparse H01/H06 network sensitivity, before a full-year network screen. This is **not** an annual AC test and does not change equipment, batteries, signed annual results, or any GitLab file.

## Installation

Extract this complete directory into:

`case1\studies\SEEDExchange_StudyA_94022_AllNine_Bundle_v1\`

Keep the original `StudyA_A0_94022_Sequenced_Trial_v1` folder at the GitLab repository root. Also retain the earlier installed original modules under `case1\studies\`: `SEEDExchange_StudyA_A0_Sequenced_Redispatch_Pilot_v1`, `SEEDExchange_StudyA_A0_94022_PartialReview_2026-11-16`, and the existing Study A annual portfolio/geographic grid modules. This package includes the SHA-256-verified uploaded dual-service ZIP under `inputs`.

Run from your GitLab repository root in **Miniforge/Anaconda Prompt**:

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_94022_AllNine_Bundle_v1\tests" -v
python "case1\studies\SEEDExchange_StudyA_94022_AllNine_Bundle_v1\studya_94022_allnine_targeted.py" --repo-root . --trial-dir "StudyA_A0_94022_Sequenced_Trial_v1" --preflight
python "case1\studies\SEEDExchange_StudyA_94022_AllNine_Bundle_v1\studya_94022_allnine_targeted.py" --repo-root . --trial-dir "StudyA_A0_94022_Sequenced_Trial_v1" --out "StudyA_A0_94022_AllNine_Bundle_v1_Results.zip"
```

Upload `StudyA_A0_94022_AllNine_Bundle_v1_Results.zip`, even if any configurations fail. The script will report the measured voltage, transformer loading, line loading, H01/H06 limiting identity and exact failed timestamps in the CSV. A hard error (e.g. corrupted signed file) must be diagnosed rather than ignored.

## Scope

5 options × 9 selected timestamps × 4 equipment/dispatch groups × 9 PF/length pairs = **1,620 new targeted AC solves**. All nine PF/length pairs are PF 0.95, 0.98 and 1.00 crossed with length factors 1.0, 1.3 and 1.6. Five options: unmodified head baseline; 4, 5 and 6 modelled-branch R×0.5; all-26-LV R×0.5 as numerical control.

All 360 overlapping prior local trial snapshots must reproduce within 2e-4 on electrical metrics. Each of the original candidate schedules, energy checks and unmodified original AC reference is verified before use. Output is a new ZIP, never overwriting previous evidence.

## Interpretation

A passing selected-hour result is **not** annual electrical feasibility or physical cable engineering. The service runs, conductor type, phase allocation, customer attachments, material cost, protections and field transformer ratings remain open. A genuinely installed design needs network verification and cost evaluation against the A1 alternative.
