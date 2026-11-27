# Stage 19 | Study B: household grouping and transformer siting

Study A evaluated the existing EPM network proxy. Study B asks how proposed community LV configurations can improve the design. Frozen individual 2025 demand profiles and fixed geographic identities are retained. The candidate generation covers N=5 to 15, using full35 and matched34 populations. Overlapping group experiments and 36 disjoint partitions are separate.

The B1 run produced 454 groups, 1,573 deduplicated supply sites and 3,146 STAR/MST networks. A second run reproduced all seven table hashes and checked every partition's membership. Four geometric site methods are candidates, not land or construction approvals. Figure 50 shows the candidate coverage; Figure 51 shows actual hypothetical paired chord networks selected by median cable saving at N=10 and N=15. Both use identical group and site in each comparison. No upstream supply route is demonstrated.

Figures 50–51 are rendered, byte-verified and visually inspected. Source: [B1 qualification receipt](../../studies/SEEDExchange_StudyB_Integration_v1/B1_QUALIFICATION_3124248027_RECEIPT.json), [generator](../generate_study_b_b1_figures.py), [figure plan](../STUDY_B_FIGURE_PLAN_2026-11-27.json).

[Figure 50 PNG](python_figures/50_group_size_and_supply_candidates.png) | [SVG](python_figures/50_group_size_and_supply_candidates.svg)

[Figure 51 PNG](python_figures/51_matched_star_mst_geometry.png) | [SVG](python_figures/51_matched_star_mst_geometry.svg)

Matched 10-house site B_G0268_S1: STAR 2,298 m, MST 1,470 m; matched 15-house B_G0433_S2: STAR 5,162 m, MST 2,714 m (rounded plot labels). These are hypothetical geometric chords. Minor header-spacing refinement remains for presentation; verified original plots preserved.
