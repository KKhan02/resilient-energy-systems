# Stage 20 | Study B: geometry, electrical paths and gross loading

Across 1,573 same-site pairs, median cable reduction is 36.4323%, median longest path increase 43.4388%, median peak branch demand increase 1.8234 kW. Maximum changes are 69.5058%, 274.0866% and 6.1907 kW, respectively. Figure 52 shows distributions by N. Geometry alone cannot determine voltage, losses, construction cost or resilience.

Figure 53 shows the gross annual transformer demand boundary using unique groups, not repeated sites. At PF .98, 0 groups at N=5–9 exceed the 5 kVA load proxy; 1/30 at N=10; every group at N=11–15. Median exceedance hours at N=11,12,13,14,15 are 4,33,124,305,550. At N=10 PF .95, 12/30 exceed. These are aggregate load-only demand proxies, not AC thermal results. No gross-only exclusions: PV/BESS and transformer sizing may change feasibility.

Figure 54 displays 2,202 within-group nondominated cases in cable length, maximum path and maximum branch peak. This is not a techno-economic Pareto frontier. Groups are not mutually interchangeable, and gross branch power is not actual AC current. No final geometry is selected. Next test conditional load-only AC cases with paired STAR/MST, existing EPM proxy scaling, explicit conductor and route sensitivity. Retain all candidates and failure records. Figures 52–54 rendered, byte-qualified and visually inspected.

[Signed source receipt](../../studies/SEEDExchange_StudyB_Integration_v1/B1_QUALIFICATION_3124248027_RECEIPT.json) | [Python generator](../generate_study_b_b1_figures.py) | [figure plan](../STUDY_B_FIGURE_PLAN_2026-11-27.json).

[Figure 52 PNG](python_figures/52_star_mst_geometry_tradeoffs.png) | [SVG](python_figures/52_star_mst_geometry_tradeoffs.svg)

[Figure 53 PNG](python_figures/53_gross_transformer_loading_boundary.png) | [SVG](python_figures/53_gross_transformer_loading_boundary.svg)

[Figure 54 PNG](python_figures/54_within_group_geometry_frontier.png) | [SVG](python_figures/54_within_group_geometry_frontier.svg)
