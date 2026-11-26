# 94022 middle-placement SOC reserve annual comparison | 26 November 2026

Remote job 18394344888, execution eb83c31e2e32cfa32251ba8f7182d3c175b6cf05, pipeline 3118474887: both stages succeeded automatically. Source byte audit 12/12 exact, 402 frozen sample controls, 241 corridor constraints, three optimal annual LPs, 52,560 new converged AC case-hours, six strict model passes. Previous screen artifact access was unavailable; deterministic screen replay reproduced exact signed CSV SHA. Runner reports 142/143/142 inverter-P hours changed, all 3 reference annual costs/import/curtailment/cycles unchanged within 1e-6 versus the prior signed full-night reserve. Retained 20% physical SOC, cyclic storage, zero export/ENS, no night Q. No independent binary artifact audit. All 12 old/new source and corrected energy identities matched using receipts; this is trace/receipt review, not an independent AC rerun.

| PF / length | battery modules | frozen middle failures | reserve middle failures | reserve middle Vmin | R050 Vmin | reserve middle cost incl. losses USD/a | R050 cost incl. losses before physical cost USD/a |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0.98 / 1 | 5 | 0 | 0 | 0.955353454 | 0.961266801 | 4305.75 | 4292.01 |
| 0.95 / 1.6 | 5 | 76 | 0 | 0.950000104 | 0.955486045 | 4363.69 | 4305.79 |
| 0.98 / 1 | 6 | 0 | 0 | 0.955353454 | 0.961266801 | 4343.92 | 4330.14 |
| 0.95 / 1.6 | 6 | 78 | 0 | 0.950000104 | 0.955486045 | 4402.61 | 4343.92 |
| 0.98 / 1 | 7 | 0 | 0 | 0.955353454 | 0.961266801 | 4429.72 | 4415.84 |
| 0.95 / 1.6 | 7 | 76 | 0 | 0.950000104 | 0.955486045 | 4488.95 | 4429.61 |

Under PF .95 length1.6, all three reserve schedules achieve Vmin .950000103521 (margin 1.0352e-7 pu); peak transformer falls from 98.1494% to 90.4721%, peak line 18.1728%. R050 retains larger minimum voltage margin .005486 pu, and lower losses but unpriced physical costs. The conditional loss-only present values vs corrected middle are 175.72/176.12/177.33 USD at reference and 740.18/750.30/758.56 USD at stress for 5/6/7 modules. Existing historical tariff .29 USD/kWh, 25y, 6%, all losses purchased, no escalation/differential O&M/replacement; no stress probability or causal loss attribution. B5 lowest modeled cost among tested options, B6/B7 separate energy autonomy trade-off. No installation selection or field verification. A near-zero voltage margin demands explicit sensitivity and eventual implementable reserve policy; perfect foresight is not operational control.

Next: check the exact new schedules on the nine approved PF/length factors using a common sample that covers the previous 67 hours, all 241 support hours and all changed inverter-P hours plus energy extrema. Already completed reference/stress annual results remain separate. Use exact artifact hashes, or deterministic reconstruction with matching energy hashes only. New seven-factor annual validation only when sample/decision evidence warrants it. No arbitrary run cap, no new voltage threshold or equipment assumption; any proposed safety margin or causal forecast/control policy requires explicit design discussion. Finish A-wide consolidation before B/C.
