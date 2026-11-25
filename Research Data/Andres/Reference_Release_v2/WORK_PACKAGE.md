# WP1 | Vulnerability and resilience
**SEEDExchange · San Rafael / El Arenal · Research brief · 25 November 2026**

## Central research question
How do plausible external and internal disruptions affect the performance of a shared PV and battery energy community, and which system characteristics provide the greatest resilience benefit for their cost?

## Starting point
Build on the existing `Vulnerability_Analisis.xlsx` (DB, Table, Summarized_Table and Resilience_def). The workbook already classifies internal and external stressors by potential impact and adaptive capacity, describes simulation scenarios and proposes performance, reliability and economic indicators. The next contribution is a quantitative framework, not a second inventory of stressors.

## Research directions
- Which of the existing stressors materially affect annual energy served, imports, curtailment, storage utilization and operating cost? Examples already identified include restricted grid imports, demand changes, solar shortfalls, battery degradation or unavailability, inverter failure and compound events.
- How sensitive is the outcome to disruption timing, duration, initial battery state and storage energy versus power capacity? Can one distinguish physical limits from dispatch-policy effects?
- What is the relationship between ordinary grid-connected economic sizing and resilience? Does the lowest-cost design also perform well under disruption, or is a different reserve strategy or capacity justified?
- How should the existing qualitative impact and adaptive-capacity classifications be supported by explicit quantitative criteria? Which proposed metrics are measurable with current inputs, and which require additional evidence?

## Expected research outcome
A documented, reproducible and parameterized assessment that compares a baseline against selected justified stress scenarios, reports performance loss, energy not served (ENS), normalized ENS, recovery where defined, and cost consequences. A concise ranked vulnerability register and interpretable figures should identify the most consequential stresses, sensitivities and remaining evidence gaps. Expected annual outage/reliability metrics such as EENS or SAIDI/SAIFI need documented probabilities or interruption data; otherwise report scenario-conditioned results, not utility reliability predictions. Express capacity reductions relative to each case; reconcile loss percentages versus percentage points and clearly define denominators, durations and recovery conditions.

## Optional stretch question
How does conditional outage energy adequacy vary with every possible start hour, outage duration, weather and initial battery state? A heatmap or resilience frontier could reveal whether a reserve policy or different storage size is worth its cost. Explore uncertainty in critical-load fractions only as an explicitly separate, hypothetical sensitivity: critical/deferrable load categories are parked in the approved primary scope. Without evidence of intentional islanding or an isolated backup arrangement, report energy adequacy conditional on that capability, not actual community outage survivability. Compare with a no-islanding baseline in which grid-dependent supply is unavailable.

## Inputs from the modelling lead
`data/household_demand_2025.csv`, `data/pv_availability_2025.csv`, `data/cohort_memberships.csv`, `data/model_assumptions.json`, `data/reference_cases/` and `data/reference_case_catalog.csv`. The reference cases include hourly demand, PV, grid imports, inverter output, battery charge/discharge, end-of-hour Store state, curtailment and hardware. The model uses a cyclic year; start-of-hour Store equals the preceding hour's end-of-hour Store (last hour for the first interval). The Store coordinate is not physical battery energy; see assumptions. The vulnerability workbook remains in the existing Andrés folder on main. No outage frequency, measured critical-load profile, verified backup hardware, repair duration distribution or value of lost load is supplied by the main model. Obtain or explicitly scenario-label these independently.

## Boundaries and integration
Use the supplied versioned cases as a development benchmark, not a final design. A1/A0 are model hypotheses, not actual verified service assignments. Keep the method independent of panel count, battery modules and inverter rating. Do not change signed schedules or claim physical outage capability. Return a short research report, assumptions/source register, machine-readable scenario definitions and results, reproducible code or workbook, and figures. Choice of analysis method and justified scenario selection is yours.
