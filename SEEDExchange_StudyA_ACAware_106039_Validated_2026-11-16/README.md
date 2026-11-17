# Study A 106039 AC-aware correction and next portfolio diagnostics

This package is a **read-only analysis update** for the completed 16 November 2026 local AC-aware shift trial. No historical source file, input manifest, GitLab repository, or local annual calculation is changed.

## Contents

- `RESEARCH_REVIEW.md`: independent study findings and next steps.
- `INDEPENDENT_QA.json`: 34 verified hourly/energy/AC data checks.
- `TRIAL_18_AC_RESULTS.csv`: corrected and baseline annual sensitivity summaries.
- `PORTFOLIO_432_STATUS_WITH_TRIAL_OVERLAY.csv`: original 432 rows with 18 corrected case metrics in separate effective fields; original metrics retained.
- `REMAINING_20_DESIGN_DISPATCH_GROUPS.csv`: remaining failing groups and prioritization.
- `independent_trial_audit.py`: reproduce uploaded-data QA if placed alongside all six trial files.
- `extract_remaining_events_and_pv.py`: next local read-only evidence extractor for all 126 remaining failing annual AC scenarios, and coincident PV curtailment flags.

## How to collect the next evidence

Extract the ZIP's inner folder to your repository root or an external working folder. In Miniforge/Anaconda Prompt, from the repository root:

```bat
python "SEEDExchange_StudyA_ACAware_106039_Validated_2026-11-16\extract_remaining_events_and_pv.py" --repo-root . --out StudyA_Remaining_AC_And_PV_Diagnostics.zip
```

If extracted to `case1\studies`, change the relative script path accordingly. The script reads the complete signed annual AC and dispatch output folders, validates source checksums, and writes a new ZIP. It **does not** perform numerical simulations or edit source outputs. Upload `StudyA_Remaining_AC_And_PV_Diagnostics.zip` next.

Expected: 126 signed failing AC scenarios after overlay and up to 44 distinct PV/BESS dispatch family summaries. The 126 case list represents stress-case failures, not 126 distinct hardware installations. Check `EXTRACTION_QA.json` for any missing or inconsistent files. PV clipping/coincidence flags overlap and are not a proof of a single curtailment cause.

Do not put the new corrected trial CSVs into original PyPSA/AC source result folders. Reuse these as separately signed candidate designs, retaining their original source provenance.
