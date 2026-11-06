# Protocol for a proposed new shared-transformer LV community scenario

**Status:** input and evidence specification, not a simulated or as-built proposed network. No invented household lines, locations or cable lengths. This is separate from the existing EPM GIS-connected case study.

## Purpose

Compare the original saved **5-to-15-house** equipment-optimization cases on a **consistent proposed LV network**, allowing a hypothetical new transformer and new household grouping, rather than requiring that all candidate groups correspond to presently mapped EPM connections. The 8-house H01/H02 archived variants differ in synthetic load profiles and do not themselves specify new physical customer locations.

## Required inputs before constructing pandapower

1. **Supply point and transformer:** proposed placement/site; service nominal voltage and phase arrangement; **5 kVA initially as a hypothesis**; source impedance, tap and line-to-neutral/line-to-line ratings; material/nameplate uncertainties.
2. **Households:** a consistent 15-site *candidate geometry* or another explicit site arrangement; unique household IDs and positions; which first 5,6,...,15 sites participate. This should preserve geographical identity as participation increases, not reshuffle houses to improve a modelled result.
3. **Feeder topology:** routed cable sections and nodes, service drops, total route lengths, and allowable connection topology. Specify a physically credible compact/branched candidate and a radial candidate only where supported by location/layout; label both as hypothetical until engineering verification. Do not fabricate EPM-owned connections.
4. **Electrical cable data:** documented conductor type, R/X in ohm/km, ampacity, phase/neutral representation and thermal protection. The current balanced EPM GIS model and approximate conductor characteristics are research proxies, not final engineering specifications.
5. **Shared PV/BESS point:** proposed inverter location, AC/PCC nominal voltage, allowable P/Q operation, grounding/protection and zero-export policy. Verify manufacturer string, DC ratio and integrated inverter/battery-port limits; assume nighttime Q disabled until documented.
6. **Load model:** retain the exact archived stochastic 2025 8,760-hour profiles as planning input; do not pretend they are metered households. Allocate customer-level load profiles to explicit attachment nodes and retain their profiles consistently across household-count variants.

## Agreed operating assumptions

- **Household PF reference:** 0.98. Principal PF sensitivity: **0.95 / 0.98 / 1.00**. PF 0.90 stays an optional inductive stress check, **not a universal viability requirement**, since large inductive appliances have not been identified. Actual measurements are needed to verify PF.
- **Voltage:** principal proposed engineering screen **0.95 to 1.05 pu**, with the prior 0.97 to 1.03 pu band reported only as strict research sensitivity; distinguish national/historical EPM references and duration-based legal compliance.
- **Thermal:** transformer and conductor loading must be evaluated from hourly apparent power and current, not annual average kWh. The reference 5 kVA rating is conditional and can be reconsidered only if actual thermal or voltage calculations show a need. No new capacity expansion MILP is warranted simply because several nameplates were used in the historical campaign.
- **Annual chronology:** every selected equipment configuration receives manufacturer-SOC-constrained 8,760-hour active dispatch and independent pandapower AC replay. AC losses and unbalanced LV phases require later model refinements; do not label these field verified.
- **Comparability:** the same physical network parameters and 2025 weather/demand realization must be used for equipment comparison within each household count. The new-network and EPM-GIS cases must be compared as **separate network configurations**.

## Decision gate

**Do not run new AC for the proposed transformer yet.** First settle the new-connection geometry and cable assumptions. The energy-only portfolio and stage-A anchors can be reviewed without a modelled feeder. Once the topology is grounded and tested for load-only plausibility, execute annual AC for defined anchors, expand to nondominated/transition candidates based on observed feasibility gaps, and then perform full-year PF/route robustness for finalists.

## Never conflate

A 5 kVA transformer rating **does not bound inverter size**: a larger zero-export DC-coupled inverter may serve local loads but must still satisfy bus-voltage, protection, export and cable ratings. Conversely, a small annual average household energy does not by itself ensure peak load/current below 5 kVA.

The existing source EPM GIS territory assignments remain available for physically grounded studies; this proposed new-community case does **not** claim those customers are currently connected to a new asset.
