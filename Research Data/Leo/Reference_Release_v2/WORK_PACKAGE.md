# WP4 | Inverter compatibility, backup and protection
**SEEDExchange · San Rafael / El Arenal · Research brief · 25 November 2026**

## Central research question
Which commercially available inverter and protection arrangements could support the proposed community's grid-connected operation, and under what technical and regulatory conditions could isolated backup operation be feasible?

## Starting point
The prior GFM investigation concluded that grid-forming participation was unsuitable for this small and unpredictable system and identified a regulatory rating restriction. Preserve that conclusion and its source, distinguishing the scope of grid-forming services or generation requirements from intentional islanding, anti-islanding and isolated backup capability. Do not repeat a general GFM literature review or assume a regulation permits community islanding.

The existing model uses representative Deye hybrid inverter ratings and SE-G5.1 battery constraints. Exact quoted inverter model/revision is not identified. The existing documentation flags a possible mismatch between representative 220/380 or 230/400 V three-phase inverter family and the 240/120 V single-phase EPM proxy. The balanced pandapower equivalent is not physical phase-compatibility evidence. Nighttime reactive power remains off unless documented device capability supports otherwise.

## Research directions
- Which real hardware models and ratings match the local secondary voltage, phase arrangement, battery DC voltage/current, continuous/overload capability, BMS compatibility and expected operating modes? What can be verified from manufacturer manuals and what requires utility/vendor confirmation?
- What is the distinction between a grid-connected hybrid inverter, an isolated backup output, an intentionally islanded community network and providing grid-forming services to the public grid? Which architectures are technically compatible and legally supportable at the proposed scale? A negative finding is a valid outcome.
- What limitations arise from anti-islanding, transfer/isolation, earthing/neutral configuration, short-circuit current, protection coordination, load inrush, black start, reconnection, and nighttime P/Q operation? Identify information needed before a safe design can be approved.
- How would the supported backup architecture constrain the vulnerability research? For example, distinguish grid-dependent households, isolated selected circuits, and a hypothetical electrically isolated community. No existing household is assumed to have an approved critical-load circuit.

## Expected research outcome
A manufacturer-source-based capability/compatibility matrix for relevant inverter ratings and batteries, conceptual single-line options (including a conventional grid-connected baseline), a technical/regulatory feasibility matrix and a clear decision on what can realistically be modelled or claimed. Identify exact model codes, regional variants, manual revisions and source links; do not infer capabilities from generic hybrid marketing or another model. Flag unmet information, costs and permissions. Coordinate licensing interpretation with WP2 and conditional outage assumptions with WP1. This is a conceptual research study, not a protection design approved for installation.

## Optional stretch question
If a clearly isolated hypothetical backup system is useful, what is its dynamic response to grid loss, load change, rapid PV reduction or inverter current limitation? A small simulation could compare control concepts and assess voltage/frequency recovery, without asserting that a real community is allowed to island. If dynamic models or parameters are unavailable, a documented conceptual comparison or literature-based limitation assessment is sufficient. No utility-grid GFM service demonstration is required.

## Inputs from the modelling lead
`data/model_assumptions.json`, `data/hardware_evidence.md`, `data/reference_case_catalog.csv`, `data/reference_cases/`, and `data/cohort_memberships.csv`. Hourly P and DC PV availability, load, charge/discharge and equipment ratings are adequate for operating-envelope screening, not transient/inrush/fault-current calculations. No measured phase topology, exact device firmware, protection settings, impedance at the actual PCC, switching data or validated inverter dynamic model is provided. Obtain or mark these as unknown; do not manufacture parameters. Use manufacturer and EPM evidence for hardware compatibility.

## Boundaries and integration
Do not change current energy model or enable unsupported nighttime Q, islanding, or physical interconnection. Treat candidate inverter kVA and battery DC power as model inputs, not chosen products. Return a concise report, referenced hardware comparison, conceptual diagrams, capability assumptions and feasibility limits. Method, alternative models and optional simulation are yours.
