# Native portfolio loss and extrema closure gate | 27 November 2026

Execution commit c3ab450c782f7268d7f061193325cc3e81d2ffcb, automatic pipeline3124070133. Four existing signed optimized source and corrected schedules; no new LP, no annual AC rerun.

| Case | Source | Corrected schedule | Changed hours | New AC points across two factors |
|---|---|---|---:|---:|
| A0_106039_min_cost_ref | 53012c200ee5... | e7012b9b4b1d... |39|0 (156 signed old/new replay rows reused)|
| A0_106039_ss90_ref | a3453b283d28... |241887b0cde5...|2|8|
| A1_106039_ss90_ref |449b8bbc098a...|942d7ff67ddd...|2|8|
| A1_113699_min_cost_ref |ce9493033a7c...|417a1221c460...|4|16|

Use existing frozen v6.2 stateless AC, native household mappings, fixed hardware and transformer ratings, PF .98 length1 and PF .95 length1.6. Source and candidate annual SHA checks, all 8760 hourly load/PV/P identities and annual energy/SOC closure, old AC archive exact hash, metadata, chronology, Q policy, finite results, annual original loss and extrema reconciliation. Use old archived P/Q changed-hour audit for MC0, replay original and corrected points only for other three. Regress old P/Q/AC quantities and compact corrected minima/transformer peaks, plus SS1 composed full-year reference loss398.29336041168557. Stitch each annual original unchanged-hour dataset with exact corrected AC rows; compute full-year loss, main/optional voltage and thermal violations, minima, peaks and changed-hour deltas. 70080 annual case-hours accounted, not newly solved; 94 changed factor-hours, 156 reused point records,32 new original/corrected point solves. Preserve all resulting annual failures if any. New wrapper preflight and tests pending; no field or causal control certification. Output summaries/CSV/hashes, no unreviewed output push. Main untouched. No new 113699 severe correction or isolated sizing. After completed receipt, integrate both-factor loss and headroom for all53 candidates, re-enumerate within geometry classes, then select decision-relevant portfolios and proceed to Study B.
