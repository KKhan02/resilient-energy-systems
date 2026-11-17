# SEEDExchange Study A, remaining 126 case diagnostic review

Reproducible independent, read-only research triage of the uploaded `StudyA_Remaining_AC_And_PV_Diagnostics.zip` (16 Nov 2026). No new simulation jobs and no GitLab edits.

Files:
- `ENGINEERING_RESEARCH_REVIEW.md`: analysis and interpretation, with methodological limits.
- `NEXT_EXPERIMENT_DESIGN.md`: bounded order of engineering follow-ups.
- `REMAINING_FAILURE_TERRITORY_TRIAGE.csv`: territory-level classification of 586 grouped events.
- `PV_BESS_CURTAILMENT_SCREENING_44.csv`: all 44 existing hardware/dispatch annual PV statistics.
- `INDEPENDENT_QA.json`: input source checksum, original source QA and consistency checks.
- Four original CSV/JSON input diagnostic files, byte-for-byte, for full provenance.

All figures and original code in GitLab remain unchanged. Prepare AC-aware modifications only in separate trial outputs with source hashes. Store this package as supporting research evidence, not as a substitute for the signed 432 AC ledger.

## Optional next read-only local extraction

To inspect the SOC and dispatch *before and after* the 175 **mapped-feeder** failing design-hour events without rerunning AC or PyPSA, copy this entire folder under `case1\studies\`, keep your existing `StudyA_Remaining_AC_And_PV_Diagnostics.zip` in the repository root and execute in **Miniforge/Anaconda Prompt** from the repository root:

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Remaining126_Triage_2026-11-16" -p "test_window_extractor.py" -v
python "case1\studies\SEEDExchange_StudyA_Remaining126_Triage_2026-11-16\extract_mapped_dispatch_windows.py" --repo-root . --events-zip "StudyA_Remaining_AC_And_PV_Diagnostics.zip" --out "StudyA_Mapped_SOC_Windows_for_Redispatch.zip"
```

This source-hash-verifies the 16 selected optimized/causal annual dispatch files and gathers 24 preceding plus four following hours per event (expected 5,075 event-relative hourly rows). It **does not** perform any corrective power-flow calculation, new hardware optimization or SOC-aware dispatch and may not be needed if you first prioritize the Study B topology branch. Upload the resulting ZIP for a detailed feasible-energy-corridor assessment.
