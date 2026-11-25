# WP2 | Commercial model, financing and affordability
**SEEDExchange · San Rafael / El Arenal · Research brief · 25 November 2026**

## Central research question
Under what ownership, financing and energy-benefit allocation arrangements could a technically feasible shared PV and battery energy community deliver an affordable and financially sustainable service to participating households in Colombia?

## Starting point
The previous regulatory study already addressed articles, licensing, connection requirements and regulatory pathways. Use that work as the legal foundation. The new contribution is to connect those findings to a viable operating and commercial model, not to repeat the legal review. Where a commercial arrangement creates a new legal question, identify the exact applicable rule and whether eligibility is confirmed, conditional or unresolved.

## Research directions
- Which plausible ownership and operating arrangements fit the regulatory findings and the local community? Consider shared ownership, cooperative management, third-party financing or utility participation where relevant. Distinguish physical electrical sharing from virtual or commercial allocation.
- How would household bills, contributions, savings, shared capital costs, maintenance and battery replacement be allocated? How do unequal demand, initial contributions, affordability and participation affect the outcome?
- Under what tariff, financing, subsidy, cost and lifetime assumptions does a project become financially attractive? What are the most influential uncertainties and break-even conditions?
- What additional costs are absent from the current energy-only model? Consider cable and civil works, metering, protection, land, permitting, installation, operation, finance, taxes and utility charges; do not silently price unknown costs at zero.

## Expected research outcome
A transparent commercial/financial comparison, with documented Colombian tariff and policy sources, lifecycle costs, household-level payment or savings examples, uncertainty and conditions under which each arrangement makes sense. A reusable billing and financing workbook or model should accept household demand, project capex, equipment replacement and monthly grid-energy totals as parameters. Separate modelled economic savings from actual regulated bills; distinguish USD reference values from COP, exchange date, and tariff/subsidy assumptions. Show who pays, who benefits and what is required for long-term operation. A result that a proposed arrangement is not currently implementable is valuable.

## Optional stretch question
Can an allocation rule provide fair household benefits without making any participant worse off relative to a suitable individual baseline? Compare equal sharing, usage- or investment-proportional allocation, or a justified cooperative game-theory approach. A Shapley-value or other cooperative allocation is optional and conditional on the definition of coalition costs; no actual legal tariff mechanism is implied. Explore sensitivities to participation, financing and demand differences.

## Inputs from the modelling lead
`data/household_demand_2025.csv`, `data/cohort_memberships.csv`, `data/reference_case_catalog.csv`, `data/reference_cases/` (hourly schedules, hardware and original energy-economic summary), `data/monthly_reference_energy.csv`, `data/model_assumptions.json`, and `data/hardware_evidence.md`. The historical tariff is 0.29 USD/kWh, 25-year horizon and 6% discount rate; these are modelling references, not confirmed current local tariffs. No household income, actual bill, legal eligibility, installation quotation, subsidy award or agreed financing structure is provided. Gather or scenario-label these independently and avoid assuming participation or affordability.

## Boundaries and integration
Study A hardware and dispatch can change. Build a calculator that takes case-specific inputs rather than fixing the output to one PV/BESS size. Distinguish cost of imported energy from losses (not included in original optimization), actual billing and commercial allocation. Keep unpriced items visible. Return a concise report, regulatory-to-commercial decision matrix, referenced cost/tariff assumptions, reusable calculator and figures. Choice of commercial cases, evaluation criteria and method is yours.
