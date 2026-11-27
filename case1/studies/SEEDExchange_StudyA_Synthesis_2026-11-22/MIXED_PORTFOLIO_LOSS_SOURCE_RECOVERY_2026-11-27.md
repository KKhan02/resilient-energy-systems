# Mixed-portfolio loss evidence recovery | 27 November 2026

Recovered reference and stress loss quantities from original annual summaries and audited source-stitched evidence. No new solves. Values below are kWh/year. Do not mix physical geometry classes or interpret omitted construction costs as zero.

| Case | Reference | Severe stress | Source |
|---|---:|---:|---|
| A1 106039 MC_REF | 407.372626 | 440.347062 | StudyA_A1_106039_PV_TieBreak_GridReserve_Full_v3/RUN_MANIFEST.json, reserve_candidate |
| A1 106039 MC_B9 | 405.082682 | 438.056046 | StudyA_A1_106039_B9_FullAnnual_AC_Overlay_v1/ANNUAL_NINE_FACTOR_B9_RESULTS.csv |
| A1 106039 MC_B10 | 403.971781 | 436.947194 | StudyA_A1_106039_NewHardware_Reserve_AnnualAC_Full_v1/ANNUAL_AC_PAIRED_SUMMARY.csv |
| A1 106039 SS_B9 | 394.236470 | 427.130467 | StudyA_A1_106039_B9_FullAnnual_AC_Overlay_v1/ANNUAL_NINE_FACTOR_B9_RESULTS.csv |
| A1 106039 SS_B10 | 392.173541 | 425.082845 | StudyA_A1_106039_NewHardware_Reserve_AnnualAC_Full_v1/ANNUAL_AC_PAIRED_SUMMARY.csv |
| A1 106039 SS_P45_B9 | 398.591496 | 431.500706 | same new-hardware paired summary |
| A1 106039 native SS90 | 398.293360 | pending | MATCHED_A1_SS90_TERRITORY_LOSSES_2026-11-24.csv |
| A0 94022 older five-edge MC | 421.631018 | 468.868327 | StudyA_A0_94022_Annual_Bundle_Results_v1/five_A0_94022_min_cost_ref_optimized_pf{098_l10,095_l16}/annual_network_ac_summary.json |
| A0 94022 older five-edge SS90 | 405.028274 | 452.100729 | same directory, ss90_ref instead of min_cost_ref |
| A0 113699 native MC | 196.367694 | 206.930137 | StudyA_v6 annual_ac_replays_v1/A0_113699_min_cost_four_mapped_optimized_pf{098_length10,095_length16}_annual8760/ac_summary.json |
| A0 113699 native SS90 | 195.190787 | 205.744992 | corresponding ss90_four |
| A1 113699 native SS90 | 264.588077 | 286.981423 | corresponding A1_113699_ss90_ref |
| A1 113699 native MC | pending | pending | StudyA_A1_Mapped_Redispatch_Trial_v1/TRIAL_MANIFEST.json and NINE_FACTOR_ANNUAL_REUSE.csv show corrected annual passes, compact AC records lack losses |

A0 106039 MC: existing original AC summary hashes match StudyA_A0_106039_Sequenced_Trial_v1/NINE_FACTOR_ANNUAL_REUSE.csv. Original losses461.4156912054 and504.260480195397; use StudyA_A0_106039_ChangedHour_PQ_Audit_v2/REPLAY_PQ_AUDIT.csv to add all39 changed-hour corrected minus original loss quantities separately by factor. Do not substitute original losses for corrected. A0 106039 SS90 requires exact loss reconciliation; do not infer missing values. Annual extrema must use unchanged-hour extrema plus corrected points, not corrected points alone. Native A1 113699 MC corrected schedule SHA417a1221c460d2749cef33f2bcea9c04287946fe0f41dd48f28416c5f193dc0c; original SHA ce9493033a7c58775e5528a6e2809143746e3469019a1085891aa4348668c28a. No full annual rerun needed merely to recover changed-hour losses. Source-based bulk candidate update attempted but tool-call limit prevented completion. No new Pareto results claimed. 

First live 113699 reference result: 8760 converged, no violations, Vmin .9532119561, peak transformer95.7509373%, losses284.6277427604 kWh. Final campaign receipt pending. Existing pilot unchanged.
