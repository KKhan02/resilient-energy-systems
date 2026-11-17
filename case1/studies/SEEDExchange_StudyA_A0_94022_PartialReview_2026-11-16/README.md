# A0 94022 independent review and network probe

The review is sourced from `StudyA_A0_94022_Sequenced_Trial_v1.zip`, not fresh numerical assumptions. See `RESEARCH_REVIEW.md` and `INDEPENDENT_QA.json` first.

Files:

- `A0_94022_ALL_36_FACTOR_RESULTS.csv`: nine factor sensitivities times four designs, original versus shifted violations.
- `A0_94022_FOUR_CANDIDATE_ENERGY_AUDIT.csv`: independently computed checksum, annual battery and energy metrics.
- `A0_94022_32_UNRESOLVED_CASE_EVENTS.csv`, `A0_94022_9_DISTINCT_RESIDUAL_HOURS.csv`: residual problem and corresponding inverter/grid import information.
- `STUDYA_432_POST_A0_94022_PARTIAL_OVERLAY.csv`: source-preserving portfolio correction overlay.
- `build_independent_review.py`: reproducibility of the research summary (on an evidence-review computer).
- `probe_94022_network_options.py`: separate optional local pandapower sensitivity (requires original repository).

## Run the optional network diagnostic locally

Extract this package folder under `case1\studies\` in your existing **Windows GitLab checkout**. Keep the original A0 94022 trial output folder at the repository root, where it was generated.

From **Miniforge Prompt**, repository root:

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_A0_94022_PartialReview_2026-11-16\tests" -v

python "case1\studies\SEEDExchange_StudyA_A0_94022_PartialReview_2026-11-16\probe_94022_network_options.py" --trial-dir "StudyA_A0_94022_Sequenced_Trial_v1" --preflight

python "case1\studies\SEEDExchange_StudyA_A0_94022_PartialReview_2026-11-16\probe_94022_network_options.py" --repo-root . --trial-dir "StudyA_A0_94022_Sequenced_Trial_v1" --out-zip "StudyA_A0_94022_Network_Probe_v1.zip"
```

Upload `StudyA_A0_94022_Network_Probe_v1.zip` for comparison. The default is 360 selected-hour AC probes, **not** a full-year dispatch or a physical network redesign. It aborts if the shared-inverter head reference cannot reproduce previously verified model results. It does not overwrite any signed input or earlier results.

If the default network comparisons look promising, the later command adds `--all-nine` and uses a **different new output filename**. Do not rerun until the first set is audited.

`run_epm_validation.build_net` supports head/middle/end injection locations on the conditional LV model. The resistance multipliers apply to **all modelled LV lines** and are not actual utility or manufacturer conductor specifications. Neither option is a costed construction proposal.
