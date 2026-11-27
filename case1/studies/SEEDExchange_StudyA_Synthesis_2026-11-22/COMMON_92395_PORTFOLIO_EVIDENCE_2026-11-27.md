# 92395 common four-house portfolio reference | 27 November 2026

Same H30/H31/H32/H33 cohort and 7592 kWh/year in A0 and A1. No exported EPM LV backbone, hence common hypothetical STAR, not installed network. Do not duplicate its energy, loss, or modeled case-hours when comparing the assignments. Retain H30 original association. Existing proposed MST is a Study B option rather than evidence of original EPM wiring.

## Energy sources

- A0_92395_min_cost_four: 17 panels, 3 modules, 4.583375379661477 kW DC battery, 5 kVA inverter, 5 kVA planning transformer. 777.185879296 kWh imports, 1605.659564513 kWh DC spill, 1638.638260075 USD/a modeled cost, 89.76309432% self-sufficiency. Signed energy CSV 393f048c3c66648facceb92e67a0ba95390d47e403611bd076f55b1e09fba3b9.
- A0_92395_ss90_four: 17 panels, 4 modules, 5.76 kW DC battery, 5 kVA inverter, 5 kVA planning transformer. 524.095292550 kWh imports, 1325.226781415 kWh DC spill, 1711.693970210 USD/a cost, 93.09674272% self-sufficiency. Signed energy CSV 420abca72ed90c76aea21fcbac4ab08b61580ee8e0e31f9911c47931055b2b6b.

Reopened both energy manifests, battery coverage rows and eight original annual AC summary receipts. Same energy-manifest SHA within each tier, both proposed topologies, reference PF.98x1 and severe .95x1.6. Metadata chronology, house IDs, PF/length, topology, dispatch and Q-policy checks, not new binary/hourly rehash or power flow.

| Tier | Topology | PF | Length | Failures | Minimum V pu | Loss kWh |
|---|---|---:|---:|---:|---:|---:|
| MC | star | 0.98 | 1 | 0 | 0.971565951 | 300.428 |
| MC | star | 0.95 | 1.6 | 0 | 0.954963954 | 326.790 |
| MC | mst | 0.98 | 1 | 0 | 0.957742761 | 349.659 |
| MC | mst | 0.95 | 1.6 | 110 | 0.931606317 | 413.095 |
| SS90 | star | 0.98 | 1 | 0 | 0.973726600 | 299.697 |
| SS90 | star | 0.95 | 1.6 | 0 | 0.957165669 | 326.047 |
| SS90 | mst | 0.98 | 1 | 0 | 0.959487955 | 348.906 |
| SS90 | mst | 0.95 | 1.6 | 105 | 0.933546955 | 412.313 |

All four STAR receipts pass; both MST reference receipts pass, severe MST records 110/105 infeasible hours, minimum .931606/.933547 pu. Annual loss penalties MST minus STAR: MC 49.2314662 kWh reference, 86.3051254 stress; SS90 49.2091448 reference, 86.2661868 stress. Loss sensitivity at .29 USD/kWh is not actual network construction cost. Neither modeled topology is field-certified; do not conclude STAR minimizes full installed cost. The previous AC72 audit covers all nine STAR factors for both optimized/causal dispatch families within the composed architecture-specific A0/A1 results. Do not rerun or expand 92395 within Study A merely to resolve missing actual GIS. Reuse common STAR reference in portfolio and preserve MST failure evidence for Study B route/sizing tradeoffs. Need actual EPM conductor/route, phase, costs and permissions.

## Concurrent A1 85398 live checkpoint

Pipeline3123392461 preflight18430116579 SUCCESS, 12 signed inputs,18/18 native archived annual groups pass (157680 case-hours), worst archived V .9561485353, peak trafo53.2034863017%, 100 old reciprocal source sample rows authenticated. Research18430116580 RUNNING, 4 energy records and 8/8 complete sample groups passed, common44h, first reciprocal severe annual last trace 4000/8760 at 13:53 CET. No complete new annual record at inspection. No duplicate job. Await next explicit status check; no new solver or topology launched in this turn. Main unchanged. Binary artifact access limited.
