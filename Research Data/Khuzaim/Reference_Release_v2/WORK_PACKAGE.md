# WP5 | Techno-economic modelling and research integration
**SEEDExchange · San Rafael / El Arenal · Research brief · 25 November 2026**

## Central research question
Which shared PV/BESS architectures, equipment sizes and dispatch strategies are economically defensible and electrically feasible for the proposed El Arenal community, and how do these outcomes change with network geometry, regulation and resilience requirements?

## Starting point
Study A compares provisional A0/A1 associations on existing EPM GIS. The 35 synthetic household profiles, signed 2025 PV availability and source hardware archives provide reproducible reference inputs. The active comparison has 34 households across five territories; H08/98380 is support only. The Study A sizing follow-up at 113699 and 94022 is running locally; no final conclusion is implied by this brief. Study B and C are approved scope but not yet final configurations.

## Research directions
- What are the economically promising and electrically feasible sizes, dispatch and reserve strategies for existing Study A territories? Preserve the battery charging-priority, curtailment, energy/power sizing, cyclic SOC, AC-loss and nine-factor uncertainty distinctions. Retain both passing and failing evidence and avoid a fixed arbitrary candidate cap.
- How do proposed geographically compact 5–15-house Study B groups and controlled STAR/MST networks compare using common membership and hardware, then architecture-specific sizing? Use WP3 candidate geometry; 5 kVA is a planning hypothesis.
- For Study C, is Site A connected to existing 94022 LV technically and economically preferable to a new transformer fallback? Preserve route and field evidence gaps; exclude the northern transformer. Compare shared central and multiple independent multi-home clusters without assuming electrical ties between secondaries.
- How can the independent resilience, commercial, spatial and inverter findings be integrated without allowing unverified assumptions to alter the primary model? Which additional analyses change the main conclusions, and which remain extensions?

## Expected research outcome
An integrated, reproducible architecture comparison showing annualized cost and import, self-sufficiency, PV curtailment, battery utilization, voltage/thermal feasibility and network losses. Distinguish source energy-only optimization, sampled AC, annual AC and field verification. Quantify relevant uncertainty and explicitly price or identify missing physical, commercial and implementation costs. Preserve original signed data and versioned results; update the rolling handover after substantive modelling work.

## Optional stretch question
How does the feasible cost/self-sufficiency frontier change when a quantified resilience or affordability objective and feasible backup capability are added? Only after the necessary WP1/WP2/WP4 evidence and agreement on changed scope. No assumed critical-load category or outage capability in the primary comparison.

## Inputs and interfaces
`data/` includes fixed synthetic demand/PV, provisional GIS, cohort membership, model assumptions, hardware evidence, three signed representative energy snapshots, monthly summaries and source manifests. The core model remains in the repository. WP1 should return scenario definitions and conditional performance, WP2 cost and billing assumptions, WP3 group/edge/site candidates, and WP4 hardware/protection feasibility conditions. Review each contribution before merging assumptions or changing signed model inputs. The exporter generates a new immutable input release whenever the design snapshots or evidence are updated.

## Boundaries and integration
Main modelling stays on the active sync branch. No remote change while an ongoing local simulation is using that branch. Colleagues can work in their individual research directories or separate branches; integrate reviewed data rather than changing signed archives. The 25-year/6%, .29 USD/kWh historical economics, PF .95/.98/1, length factors 1/1.3/1.6, .95–1.05 pu main voltage band, .97–1.03 optional band, 20% physical battery SOC and zero export remain source reference conditions, not field-certified requirements. Return curated evidence, walkthrough figures and integrated findings. No final sizing choice is required before the team begins independent method development.
