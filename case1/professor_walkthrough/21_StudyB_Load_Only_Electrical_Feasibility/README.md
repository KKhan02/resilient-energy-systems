# Stage 21 | Study B: load-only electrical feasibility

**Historical preflight checkpoint:** The same five-household group B_G0009 at site B_G0009_S3 was tested at its annual coincident gross peak on 11 September 2025, 20:00. Both power flows converged; both fail the 0.95 pu voltage limit despite transformer loading below 64%. The 5 kVA transformer and AAC 4 conductor are modelling hypotheses, not installation specifications.

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

## Historical B3 report recovery

Job 18436937794 reached final manifest serialization and failed on NumPy int64; four original CSVs were written and the failure archive retained. [Recovery method](../../studies/SEEDExchange_StudyB_Integration_v1/B3_REPORT_RECOVERY.md). [Pipeline 3124340971](https://gitlab.com/KKhan02/resilient-energy-systems/-/pipelines/3124340971) attempted original archive retrieval; scoped job token denied access, so the identical bounded replay completed successfully. The original failure archive remains intact.

## Stage 21: completed diagnostic load-only AC campaign

The initial report failed only at final JSON serialization; scoped retrieval of that failed-job archive was denied. The identical bounded replay completed successfully in [pipeline 3124340971](https://gitlab.com/KKhan02/resilient-energy-systems/-/pipelines/3124340971), producing a report and four signed tables. The [completed receipt](../../studies/SEEDExchange_StudyB_Integration_v1/B3_COMPLETE_3124340971_RECEIPT.json) records 43 matched sites, 741 selected site-hours and 5,928 AC points across two topologies, two conductor proxies and reference/severe factors. 5,767 converge; 2,645 pass; 3,283 fail including 161 nonconvergent points, all in MST AAC4. These counts describe the selected critical hours only.

| Topology | Conductor | Condition | Pass / 741 | Minimum converged voltage (pu) | Peak transformer (%) |
|---|---|---|---:|---:|---:|
| STAR | AAC 1/0 | Reference | 427 | .95546 | 148.10 |
| STAR | AAC 4 | Reference | 416 | .91780 | 148.83 |
| STAR | AAC 1/0 | Severe | 394 | .93980 | 154.01 |
| STAR | AAC 4 | Severe | 366 | .86751 | 155.24 |
| MST | AAC 1/0 | Reference | 337 | .81533 | 155.84 |
| MST | AAC 4 | Reference | 258 | .46579 | 198.89 |
| MST | AAC 1/0 | Severe | 295 | .66209 | 182.00 |
| MST | AAC 4 | Severe | 152 | .55566 | 171.27 |

Minimum voltages and peak transformer loadings are extrema among converged points, not necessarily coincident. The seemingly higher severe MST AAC4 minimum is not evidence of improvement: only 608 of 741 points converge compared with 713 at reference, so the sets differ.

The complete point-level paired qualification, source archive export and Python figures 55–58 are submitted in [pipeline 3124486343](https://gitlab.com/KKhan02/resilient-energy-systems/-/pipelines/3124486343). Figure index remains 54 until actual output verification. [B3-to-B4 decision gate](../../studies/SEEDExchange_StudyB_Integration_v1/B3_TO_B4_DECISION_GATE.md) explain the implications. No annual pass, installed-cost or field feasibility assertion.
