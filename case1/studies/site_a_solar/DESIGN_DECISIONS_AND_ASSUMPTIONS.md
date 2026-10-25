# Site A design decisions versus scenario assumptions

## Agreed for future study (do NOT assume chosen equipment or architecture)

1. Compare **centralized PV+BESS**, **distributed household PV+BESS**, and **distributed PV with shared BESS**, using equivalent total capacities/demand when judging architecture.
2. Size battery **usable energy (kWh)** and allowable **charge/discharge power (kW)** independently. Keep existing fixed-5-kW reference and the hardware-permitted BESS-power sensitivity distinct.
3. Multi-objective comparison: annualized cost, energy self-sufficiency and resilience, with physical constraints and installation footprint.
4. Study different outage start times and weather conditions.
5. The LV network voltages at **all households**, including farthest/worst node, belong to the pandapower workstream, not a hand-formula Site A solar calculation.
6. **Remove critical-load and deferrable-load categorization from ACTIVE comparisons** until discussion with the professor. Do not apply a 30%/15% split, even as a default baseline.
7. The approximately **50 m² reference total installation** and 1,759 m² **digitized gross clearing** are inputs to feasibility screening, not construction approvals.

## Unapproved screening assumptions — no design selection has followed

- Candidate Site A is assumed **level** only to parameterize solar-access obstruction angles. Slope, drainage, shading and ownership remain unverified.
- Tree heights 8/12/18 m; distances 5/10/20 m; arbitrary east/west and 360° obstruction sectors; panel mid-height 1.5 m. **None measured.**
- Tested panel tilts 0/10/20° and north/south facing are alternatives, **not selected**.
- Source weather is NASA POWER gridded 2025, NOT local measured Site A irradiation. Photovoltaic generation and string losses are NOT inferred from simple POA obstruction.
- A grid-connected installation in the clearing is NOT yet proven physically connected to the actual EPM feeder.
- No PV simulation outputs will be applied to the validated Case 1 dispatch/optimization until appropriate assumptions are agreed and provenance recorded.

## Decision gate before implementation

Agree the architecture-specific footprint and shadowing method, confirm or explicitly scenario-label network geometry, and keep a clean separation of unshaded reference versus shade-stressed runs. No changes to existing 11,515-row historic results should be made as part of this site-study branch.
