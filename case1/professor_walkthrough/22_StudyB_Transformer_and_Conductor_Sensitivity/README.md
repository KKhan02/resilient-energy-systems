# Stage 22 | Study B: transformer and conductor sensitivity

**Status, 28 November 2026:** submitted; no new AC result yet. [Pipeline 3127147250](https://gitlab.com/KKhan02/resilient-energy-systems/-/pipelines/3127147250).

Stage 21 establishes the need to investigate both voltage and thermal constraints, with 1,418 combined failures, 1,263 thermal-only and 441 voltage-only failures. This chapter separates transformer rating and conductor effects at fixed geometry and demand. Its reference is the exact authenticated B3 numerical archive, not a new baseline simulation.

The four layouts are uniform AAC4, AAC2, AAC1/0, and a shared-branch AAC1/0/single-house AAC4 proxy. Both 5 kVA and diagnostic 10 kVA use the existing EPM transformer parameter scaling convention, not a new manufacturer model. Reference PF .98 route x1 and severe PF .95 route x1.6 are combined conditions. The 43 matched sites and 741 selected site-hours remain fixed. There are 23,712 logical points, 14,820 new AC solves, 5,928 archived points and 2,964 exact STAR aliases (shared/leaf equals AAC4 for STAR); 12 separate preflight solves. Conductor lengths recorded by layout and route factor; no fabricated installed prices.

Expected research outputs after execution and qualification: (1) transformer rating effect at each fixed conductor layout, (2) intermediate and shared-branch conductor trade-offs at fixed transformer rating, (3) per-site all-sampled-hour feasibility and retained violations/nonconvergence, (4) actual length of each conductor size and comparison with paired STAR/MST cable totals. Figures 59 onward remain provisional until numerical results exist; generate only from authenticated tables. This chapter does not reject a DER-enabled alternative on a load-only failure or claim annual feasibility. Next: matched PV/BESS hardware and exact-cohort chronological dispatch, with targeted annual AC validation after comparison.

[Detailed methodology](../../studies/SEEDExchange_StudyB_Integration_v1/B31_TRANSFORMER_CONDUCTOR_METHOD.md) | [Python engine](../../studies/SEEDExchange_StudyB_Integration_v1/run_b31_transformer_conductor_sensitivity.py) | [B3 paired receipt](../../studies/SEEDExchange_StudyB_Integration_v1/B3_PAIRED_3124486343_RECEIPT.json).


## Live update, 28 November 2026

Preflight 18454771717 passed (12 diagnostic solves including two exact archived regressions); layout job 18454771718 succeeded. Figures 55–58 are published at 64159721, revised 55/58 and originals retained at 6a9d5c35. Main sensitivity job 18454771719 status at latest check: running. No completed result inferred from the preflight. See [B3.1 qualification and B4 entry gate](../../studies/SEEDExchange_StudyB_Integration_v1/B31_QUALIFICATION_AND_B4_ENTRY_GATE.md).

## Qualified results, 28 November 2026

23,712 logical points reconstructed; 23,336 converged, 14,554 passed, 9,158 failed including 376 nonconvergent. Maximum absolute balance residual 0.0000342583914 kW. Matched topology outcomes: both pass 5,552; STAR only 3,450; MST only zero; neither 2,854. Counts include exact STAR aliases and are not annual probabilities. At 10 kVA AAC2/AAC1/0 STAR passes all reference samples; AAC1/0 severe passes 740/741. At 10 kVA uniform AAC1/0 MST passes 563/457 reference/severe; mixed passes 544/417. Only two combined thermal/voltage failures remain at 10 kVA (MST AAC2 severe); other failures are voltage/nonconvergence. No broad 15 kVA sensitivity justified now. Preserve 5 kVA and compare DER before physical rejection. Qualification checked every archived CSV supplied, independently reconstructed logical rows and verified summaries and paired contrasts; original logical_screen.csv omitted from compact archive, so its original byte hash not independently recovered. No additional AC or LP.

- Figure 59: [PNG](python_figures/59_transformer_rating_sensitivity.png) · [SVG](python_figures/59_transformer_rating_sensitivity.svg). Matched 5 and 10 kVA rating effect at each conductor and topology; selected points only.
- Figure 60: [PNG](python_figures/60_conductor_and_failure_modes.png) · [SVG](python_figures/60_conductor_and_failure_modes.svg). Exclusive failure categories at 10 kVA; voltage remains limiting.
- Figure 61: [PNG](python_figures/61_mixed_conductor_lengths.png) · [SVG](python_figures/61_mixed_conductor_lengths.svg). Actual hypothetical route lengths by conductor calibre and matched site; no installed costs.
- Figure 62: [PNG](python_figures/62_site_coverage_by_house_count.png) · [SVG](python_figures/62_site_coverage_by_house_count.svg). Site coverage by household count at 10 kVA; diagnostic sites not annual probabilities.
- Figure 63: [PNG](python_figures/63_route_feasibility_tradeoffs.png) · [SVG](python_figures/63_route_feasibility_tradeoffs.svg). Total route length versus sampled pass fraction at 10 kVA; overlapping groups not independent populations.

[Active figure manifest](../STUDY_B_B31_FIGURES_59_63_VERIFIED_MANIFEST.json). [Numerical archive](../../studies/SEEDExchange_StudyB_Integration_v1/outputs/b31_2026-11-28/B31_NUMERICAL_TABLES.zip).
