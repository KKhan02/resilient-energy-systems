# Stage 13. Annual AC corrections and conditional network retrofit

**Research question:** Which originally infeasible operating schedules can be corrected without changing PV/BESS hardware, and which violations require an explicit network alternative?

1. **[Reference comparison after A1 redispatch](01_A1_acaware_reference_comparison.png).** Retain the gross-load and original operating benchmarks to show *why* a chronological discharge shift was investigated. The plot compares selected original and corrected territory-violation-hour counts at the reference PF/length. It is not a complete 432-case portfolio chart.
2. **[A1 higher-SS nine-factor robustness](02_A1_nine_factor_acaware_sensitivity.png).** Explicitly show the progression from A0 original, A1 original, to A1 corrected, under PF 0.95/0.98/1.00 and service length x1.0/x1.3/x1.6. Corrections preserve annual battery SOC and energy balance; a narrow voltage margin remains.
3. **[A0 transformer 94022, hypothetical five-edge network](03_A0_94022_hypothetical_five_edge_recovery.png).** The A0 redispatch alone still left thermal and voltage constraints. After branch-isolation sensitivity and selected-hour trials, a *five-edge resistance-halving hypothesis* passed 36/36 annual AC cases (315,360 hourly snapshots). This is not an actual conductor-replacement specification. Two long service connections are assumed rather than field confirmed.

**Portfolio evidence boundaries:** Original archived AC campaign 432 scenarios, with later validated SOC-aware redispatch: **376 passing / 56 failing on the original network assumptions**. A *separate hypothetical five-edge A0 94022 alternative* converts 32 previously failing scenarios, giving **408 passing / 24 failing** only in that conditional comparison. The remaining 24 belong to proposed A0 92395 MST. Never present the conditional 408 as a modification to signed original-network results.

**Why Stage 14 follows:** Electrical feasibility is necessary, but it does not reveal which PV array, inverter, or battery size minimizes total cost or curtailment. The next research step compares annual energy utilization and then AC-screens altered hardware.

**Sources:** Copied PNGs remain byte-identical to validated source figures in `case1/studies/SEEDExchange_StudyA_A1_Validated_2026-11-16/figures/` and `case1/studies/SEEDExchange_StudyA_94022_AllNine_IndependentReview_2026-11-17/`. Check each source folder's independent audit and manifests. PF/length tests are research screens, not grid-code certification.
