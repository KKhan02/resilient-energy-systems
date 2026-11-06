# AC-aware annual active-power redispatch with chronological battery SOC

**Research question:** Can the previously optimized PV+BESS hardware recover a stricter feeder voltage margin by changing the battery's hourly active-power schedule, without purchasing more equipment?

## Seven-house demonstration, transformer 94022

The initial annual PyPSA/Linopy investment campaign optimized PV, BESS and inverter hardware with a complete perfect-foresight battery trajectory, but without individual feeder AC voltages. The subsequent fixed-hardware study applied the Deye SE-G5.1 **20% physical minimum SOC** and held the selected equipment fixed at **26 × 435 W panels, 5 battery modules, 8.499 kW DC battery power, 7.6 kVA inverter**.

Under the original **research** voltage band 0.97–1.03 pu, an independent 8,760-hour AC replay found **four** late-November evening undervoltage hours, with minimum voltage 0.968184 pu. The current battery schedule was already sufficient for the less restrictive 0.95–1.05 pu proposed engineering band.

The feedback stage sampled AC-feasible inverter P corridors at the failing hours and reran the **complete annual** fixed-hardware economic and SOC optimization. The resulting 8,760-hour schedule was then replayed independently in pandapower.

| Measure | Manufacturer-SOC baseline | Full-year AC-feedback schedule |
|---|---:|---:|
| AC hours meeting original 0.97–1.03 pu research band | 8,756/8,760 | **8,760/8,760** |
| Minimum household voltage (pu) | 0.968184 | **0.970099** |
| Peak transformer loading (%) | 62.29 | **58.58** |
| Annualized equipment + grid electricity cost (USD/year) | 2,810.01 | **2,810.01** |
| New hardware required | No | **No** |

The historical reference without the manufacturer SOC restriction cost USD 2,772.94/year. The difference of USD 37.07/year is attributable to **the 20% SOC restriction**, not the subsequent AC feedback.

## Four originally failing hours

| Hour index | Date/time in 2025 | Original minimum voltage (pu) |
|---:|---|---:|
| 7940 | 27 Nov 20:00 | 0.968184 |
| 7964 | 28 Nov 20:00 | 0.969163 |
| 7965 | 28 Nov 21:00 | 0.969196 |
| 7987 | 29 Nov 19:00 | 0.969935 |

These hours were re-evaluated after the annual dispatch changed. The complete annual replay found **zero new AC violations** under the selected strict research band. The result demonstrates **SOC-consistent network-feedback dispatch**, not merely adding inverter power to isolated pandapower snapshots.

## Interpretations and boundaries

- This is a **fixed-equipment** correction, not a new equipment capacity optimum.
- Original active-power hardware capacities and manufacturer SOC floor were preserved; reactive power was disabled at night. The feedback re-optimization was annual, while the final AC validator was a power-flow replay only.
- Incremental modelled annual cost is zero for the AC-feedback step; power-flow losses of approximately 367.15 kWh/year were **not added** to the energy objective, so loss-aware costs remain unresolved.
- The balanced GIS model uses **provisional household assignments and service/line parameters**. The voltage band was a research target, not a verified Colombian regulatory limit.

## Evidence and next work

- [Feedback provenance and cost summary](../../studies/ac_aware_redispatch_v1/outputs/seven_annual_feedback_01/feedback_manifest.json)
- [Annual feedback-redispatched hourly trajectory](../../studies/ac_aware_redispatch_v1/outputs/seven_annual_feedback_01/redispatched_hourly.csv)
- [Final 8,760-hour AC summary](../../studies/ac_aware_redispatch_v1/outputs/seven_annual_feedback_ac_check_01/annual_ac_summary.json)
- [Original manufacturer-SOC annual AC summary](../../studies/ac_aware_redispatch_v1/outputs/seven_manufacturer_annual_ac_01/annual_ac_summary.json)
- [Exact four-hour recheck](../../studies/ac_aware_redispatch_v1/outputs/seven_annual_feedback_01/formerly_failing_hours_rechecked.csv)

The larger-scale AC-aware corrective controller and network-constrained equipment frontier are **still in progress**. The numeric evidence here should not be extended to all saved designs. No replacement figure is fabricated for this section; the verified four-hour table and preserved source CSVs are its visual evidence.
