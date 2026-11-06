# SEEDExchange: original Deye battery and inverter evidence register

Date: 2026-11-04. This is a hardware-documentation review, not a vendor installation certification.

## Exact source identifiers

1. `SimulacionTampico1k.xml` in project source (HOMER export) identifies the battery as **Deye SE-G5.1**, modelled as 4 modules. It uses a 10% minimum SOC, 95% round-trip efficiency and 100 A maximum charge current. Those are **HOMER study inputs**, not automatically manufacturer's recommended limits.
2. `Proposal - Hackaton Medellin(1).pdf`, quotation table, lists **Deye Hybrid Inverter 5K 3P** and **Deye 5.12 kWh battery**, without the inverter manufacturer's complete model code or hardware revision.
3. Deye manufacturer's official SE-G5.1 page: https://deyeess.com/product/se-g5-1/ specifies **5.12 kWh nominal per module, 80% recommended DoD, 50 A continuous charge/discharge current and 44.8–57.6 V operating range**. That is consistent with a nominal **20% physical SOC floor**, assuming full upper-SOC usage. At 5.12kWh, the recommended usable range is **4.096 kWh/module**. The manufacturer rather than HOMER wins for a product-constraint screen.
4. Deye manufacturer's SUN-5/6/8/10/12K-SG04LP3-EU family page, https://deye.com/product/sun-5-6-8-10-12k-sg04lp3-eu/ : representative **three-phase hybrid** family includes 5, 8, 10, and 12 kW rated models, 40–60 V battery input, BMS adaptation, PF adjustment **0.8 leading to 0.8 lagging**, and AC connection **3L+N+PE, 220/380 V or 230/400 V**. The exact hackathon quotation **does not identify SG04LP3-EU**, so these features cannot be asserted as those of the quoted hardware.

## Battery implementation and the existing PyPSA Store

The historical PyPSA model uses 17.3/4 = 4.325 kWh *usable model energy* per battery module. Compared to manufacturer nominal 5.12 kWh, `Store.e=0` is interpreted as an implicit physical SOC of 1 - 4.325/5.12 = 15.53% if full energy at physical 100% SOC is assumed. This relationship is an **explicit modelling coordinate assumption**, not a measured battery SOC calibration. Merely capping the original Store to 80% would reduce max SOC while still allowing physical SOC below 20%, so that approach is not used.

This pilot adds `Store-e >= modules * max(0, 4.325 - 5.12*(1 - min_physical_soc))`. At the manufacturer-recommended 20% floor, this gives minimum usable Store energy: 5 modules = 1.145 kWh, 6 = 1.374 kWh, 8 = 1.832 kWh. The span available for cycling becomes 4.096 kWh/module, or 80% of nominal; the top remains 100% of the manufacturer's nominal range. The original historical model and its output files are not edited.

The SE-G5.1 50 A maximum continuous charging/discharging current at its lower published 44.8 V gives an intentionally conservative **2.24 kW/module** bank-side screening bound. Current sharing and device limits remain contingent on BMS and wiring. The saved 7/9/12-house battery DC power ratings are below this independent screening bound. This is NOT a proof of installation feasibility.

To keep effects identifiable, the v1.1 pilot first checks the original fixed-hardware energy-only benchmark with the original Store range. It then solves the manufacturer-SOC-constrained baseline. Finally, it solves the AC-redispatched case **with exactly the same manufacturer SOC constraint**, so `redispatch - manufacturer_soc_baseline` isolates the incremental cost of the AC corridors. If there is no AC violation in the selected hours, the pilot does not solve those baselines and does not claim validation of the new manufacturer constraint.

## Nighttime Q, grid voltage, and inverter qualification

The documented **adjustable power factor** is evidence of an inverter's reactive-control capability in its specified operating range. It is **not** evidence that reactive power is permitted while PV is dark and inverter active power is zero. Whether an inverter can run nighttime/static VAR compensation, supply DC-link auxiliary losses from the battery or grid, and operate with zero PV remains **UNVERIFIED** for the exact quoted 5K 3P model. The default pilot runs `--night-q off`. Its `--night-q idealized_on` is an unsupported idealized what-if sensitivity until the exact manufacturer part number and manual/firmware details are obtained. Any real energy to cover converter losses must be included in the SOC and lifetime analyses before declaring the scenario implementable.

**Critical connection mismatch:** the Deye SG04LP3-EU example is a **220/380 V or 230/400 V three-phase** inverter. The EPM GIS pandapower proxy was constructed from **240/120 V single-phase** equipment approximated as a balanced three-phase system. That proxy does not establish that a European-style three-phase inverter can be connected at the physical El Arenal PCC. Confirm the actual EPM secondary phase configuration and quote's exact inverter model before making a hardware recommendation or inferring Q limits.

The saved PyPSA equipment choices of 7.6, 10 and 12 kVA come from a broader representative Deye family and historical scaled costs. The quoted 5K 3P is not itself the confirmed physical identity for all three larger selections. Physical compatibility, parallel inverter configurations, BMS limits and EPM approval remain open.

## Decision record

- Manufacturer reserve based on **SE-G5.1 80% DoD** is required in new operating studies; keep original historical results unchanged for provenance.
- No unsupported adaptive reserve heuristic enters the current PyPSA design.
- Q=0 during solar-unavailable hours is a conservative pilot. Use `idealized_on` only as an explicitly tagged sensitivity, not equipment-approved behaviour.
- Compare identical physical equipment and manufacturer SOC limits before claiming any incremental redispatch benefit/cost.
- Treat the balanced equivalent transformer apparent rating and cable loading as conditional, not certified 240/120 V as-built compliance.
