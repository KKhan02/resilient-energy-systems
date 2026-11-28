# B3.1: matched transformer and conductor sensitivity

The qualified B3 campaign establishes electrical limits for the load-only reference and severe conditions. It does not choose installed equipment. B3.1 retains the 43 diagnostic sites, 741 selected site-hours, exact frozen house profiles, STAR/MST geometry, 60 Hz EPM balanced equivalent, idealized MV source and voltage/thermal thresholds. It reuses 5,928 authenticated B3 operating points rather than solving them again. Baseline 5 kVA and diagnostic 10 kVA are separate rating hypotheses, with unchanged percentage impedance, proportional core-loss assumption and unchanged no-load current percentage inherited from the EPM builder. A real transformer requires manufacturer-specific data. No 15 kVA case until 10 kVA outcomes justify it.

| Conductor layout | Rule |
|---|---|
| UNIFORM_AAC4 | All branches AAC4 |
| UNIFORM_AAC2 | All branches AAC2, intermediate registry proxy |
| UNIFORM_AAC10 | All branches AAC1/0 |
| SHARED_AAC10_LEAF_AAC4 | Branches serving two or more downstream houses AAC1/0; single-house branches AAC4 |

The shared/leaf layout is an explicit engineering sensitivity, not actual installed trunk/service allocation. In STAR, all branches serve one house, so this layout is electrically identical to uniform AAC4. Use exact aliases, not duplicate solves. The two existing PF/route combinations are jointly varied conditions, not separately identified PF or route effects. Test all 43 sites, 2 topologies, 2 conditions, 2 ratings and 4 layouts at the same sampled hours: 23,712 logical operating points, 5,928 archived, 2,964 exact STAR aliases, 14,820 new AC solves. Separate preflight of 12 points, including two archived baseline regression checks. Compare rating at fixed conductor and conductor at fixed rating. Retain all nonconvergence and joint voltage/thermal violations. Record conductor lengths separately, no fabricated costs. Use site-level all-sampled-pass counts, matched changes and convergence-conditioned numerical differences. No full-year feasibility or probability interpretation.

Source: B3_SIGNED_NUMERICAL_TABLES.zip, verified SHA256 96f2df6e1c73215f8701fd9822e0f4e65761de98026c4dd1a89cd80ae3bffa2c. Recreate only B1 geometry from frozen sources and require all seven original table hashes; no repeat B3 run. Output signed new AC records, summaries, conductor lengths, logical matrix and compact source archive. Use the resulting alternatives to prepare matched PV/BESS hardware scenarios, not to exclude candidates purely on load-only failure.
