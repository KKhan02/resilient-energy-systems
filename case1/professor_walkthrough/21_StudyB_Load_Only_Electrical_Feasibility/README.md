# Stage 21 | Study B: load-only electrical feasibility

**Checkpoint: paired preflight passed. Full sampled campaign wrote CSVs; JSON report serialization failed.** The same five-household group B_G0009 at site B_G0009_S3 was tested at its annual coincident gross peak on 11 September 2025, 20:00. Both power flows converged; both fail the 0.95 pu voltage limit despite transformer loading below 64%. The 5 kVA transformer and AAC 4 conductor are modelling hypotheses, not installation specifications.

| Metric | STAR | MST |
|---|---:|---:|
| Gross demand (kW) | 2.903427 | 2.903427 |
| Minimum household voltage (pu) | 0.917796 | 0.899280 |
| Transformer loading (%) | 62.516321 | 63.192749 |
| Maximum line loading (%) | 3.764478 | 9.087812 |
| Network loss (kW) | 0.128999 | 0.163199 |

This matched operating point motivates joint conductor, transformer and topology evaluation, not automatic rejection of the 5-house group. It provides no annual feasibility evidence. Source: [preflight receipt](../../studies/SEEDExchange_StudyB_Integration_v1/B3_PREFLIGHT_3124290063_RECEIPT.json).

## Figure plan after actual B3 evidence qualification

Provisional numbering after figures 50–54:
- 55: sampled electrical margins and failures by household count, topology, conductor and factor.
- 56: matched STAR/MST point-by-point differences in voltage, loading and losses; nonconverged pairs kept separate.
- 57: paired conductor sensitivity; rescued passes and retained violations.
- 58: site-level sampled coverage and limiting constraint; distinguish pooled point counts from sites with all sampled points passing.

The [post-processing script](../../studies/SEEDExchange_StudyB_Integration_v1/qualify_b3_paired_results.py) checks the completed manifest against independent trace receipt, output hashes, all eight factor combinations per site/hour, matched gross demand, power balance and exact limit classification. It reports overlapping failure flags and site-level denominators separately. No solve or invented figure. Actual figure generation and index publication require signed completed B3 results.

## B3 report recovery

Job 18436937794 reached final manifest serialization and failed on NumPy int64; four original CSVs were written and the failure archive retained. [Recovery method](../../studies/SEEDExchange_StudyB_Integration_v1/B3_REPORT_RECOVERY.md). [Pipeline 3124340971](https://gitlab.com/KKhan02/resilient-energy-systems/-/pipelines/3124340971) attempts original archive verification first, or identical bounded replay if archive download denied. No full sampled results accepted until the report and table checks pass.
