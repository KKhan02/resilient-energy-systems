# Study A A1 post-redispatch audit, 16 November 2026

- `INDEPENDENT_RESEARCH_REVIEW.md`: findings, safeguards and open issues.
- `INDEPENDENT_QA.json`: exact numerical/metadata QA, caveats and SHA-256 of the user's uploaded trial ZIP.
- `PORTFOLIO_432_POST_A1_CORRECTIONS.csv`: original 432 cases plus two *overlay* fields, leaving original `infeasible_hours` intact.
- `REMAINING_12_A0_FAILURE_GROUPS.csv`: ranked remaining A0 combinations.
- `A1_72_SENSITIVITY_AC_AUDITED.csv`, `A1_342_CHANGED_AC_AUDITED.csv`, `A1_19_DISCHARGE_TRANSFERS.csv`: direct source trial records, preserved after checks.
- `A1_8_SCHEDULE_ENERGY_AUDIT.csv`: independently reconstructed annual energy/SOC consistency and checksums.
- `A0_A1_36_AGGREGATES_WITH_ACAWARE.csv`: adjusted figure data for main five-territory comparisons.
- `plot_a1_acaware_progression.py`: regenerates two progress figures from the bundled aggregate CSV, without simulating anything.
- `figures/`: two curated new progress figures as PNG and SVG. Keep earlier original plots separately for provenance.

**No new PyPSA or pandapower execution in this environment.** User's Windows trial executed 342 changed-hour AC calculations, with unchanged hours reused from signed original annual files.
