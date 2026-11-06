# SEEDExchange WP1, 12-house transformer 106039: critical-hour robustness audit

**Audit date:** 4 November 2026. **Scope:** uploaded `robustness_manifest(2).json`, `sensitivity_ac_hours(2).csv`, `sensitivity_scenarios(2).csv`, `selected_hours(1).csv`; equipment candidates from saved `equipment_shortlist_energy_only.csv`. Independent analysis of saved results, **not a new PyPSA or pandapower run**.

## Outcome

- 9 scenarios × 96 selected hours = **864 converged AC power flows**. The original 2025 annual, PF=0.98, length=1.0 reference had separately been screened for all 8,760 hours. These new sensitivity results are **critical-hour only**.
- Five of the nine sensitivity scenarios pass all 96 hours under 0.95–1.05 pu and the 100% modelled transformer/line limits. Four fail.
- The adverse PF=0.90 / length=1.6 scenario reaches **0.9441096 pu**, **106.8576% transformer loading**, and **32 distinct failed critical hours**. Its failure events overlap: 25 voltage and 31 transformer events, 24 involving both.
- PF=0.95 / length=1.6 has **two** undervoltage failures, zero modelled thermal overloads. The specific timestamps are 2025-10-08 19:00 (0.949279 pu) and 2025-11-27 20:00 (0.948500 pu).
- All selected 96 reference hours have **zero PV availability**. The conservative nighttime-Q-disabled policy therefore yields zero reactive injection at every sampled hour. **No conclusion about daytime reactive capability, voltage rise or coordinated Q performance follows from this sample.**

## Verified study matrix

| Household PF | Service factor | Min V (pu) | Max trafo (%) | Voltage failure hours | Trafo failure hours | Distinct failed hours |
|---|---:|---:|---:|---:|---:|---:|
| 0.98 | 1.0× | 0.95565 | 94.44 | 0 | 0 | 0 |
| 0.98 | 1.3× | 0.95382 | 94.50 | 0 | 0 | 0 |
| 0.98 | 1.6× | 0.95199 | 94.56 | 0 | 0 | 0 |
| 0.95 | 1.0× | 0.95220 | 98.96 | 0 | 0 | 0 |
| 0.95 | 1.3× | 0.95036 | 99.02 | 0 | 0 | 0 |
| 0.95 | 1.6× | 0.94850 | 99.09 | 2 | 0 | 2 |
| 0.90 | 1.0× | 0.94787 | 106.72 | 5 | 31 | 32 |
| 0.90 | 1.3× | 0.94599 | 106.79 | 12 | 31 | 32 |
| 0.90 | 1.6× | 0.94411 | 106.86 | 25 | 31 | 32 |

The union failure count is not the sum of the voltage and thermal failure counts because events overlap. All 864 sampled power flows converged; conductor loading stays below the study thermal limit in this dataset.

## Engineering interpretation and next gates

1. **Do not classify PF=0.90 cases as equipment-infeasible from this fixed-dispatch test alone.** The original 8,760-hour PyPSA schedule was optimized at household PF=0.98, then replayed unchanged at PF=0.90. This changes demand Q and the required apparent-power budget. Reoptimizing battery active power under the modified PF and AC constraints is required to distinguish scheduling limits from hardware limits.
2. **Keep the assumed transformer nameplate at 5 kVA only as a stress assumption.** Actual 106039 field nameplate, service types, phase allocation and effective conductor parameters remain unverified. Transformer percentage loading here comes from a balanced three-phase proxy.
3. **Expand critical-hour coverage** to midday high-PV, high-inverter-output, reverse-power/overvoltage and high-Q intervals. The current all-night critical sample is unsuitable for daylight-reactive conclusions.
4. For PF=0.95/length 1.6, attempt chronological AC-aware active-power redispatch at fixed hardware. For PF=0.90/length 1.6, require the updated PF in PyPSA and then examine whether transformer kVA and voltage can both be satisfied without ENS; do not silently alter assumed transformer ratings or disregard losses.
5. **Proceed to manufacturer-SOC-corrected equipment selection** under the 0.95–1.05 pu engineering target, zero-ENS and thermal constraints. Compare different panel counts, battery module counts, battery DC power ratings and inverter nameplates. Use independent conditional AC validation after each optimization, then resilience evaluation after network-constrained shortlisting.
6. AC energy losses and device nighttime VAR/loss support remain outside the present optimization. Report economic improvements as provisional until consistent losses and physical equipment costs are included.

## Six representative hardware candidates for the next pilot

| Panels | Battery modules | Inverter (kVA) | Earlier annual $ (energy-only) | Earlier self-sufficiency |
|---:|---:|---:|---:|---:|
| 41 | 7 | 12 | 4,777.86 | 78.67% |
| 41 | 8 | 12 | 4,767.83 | 81.04% |
| 41 | 9 | 12 | 4,828.53 | 82.33% |
| 34 | 6 | 10 | 4,900.57 | 68.60% |
| 54 | 9 | 20 | 5,259.45 | 92.61% |
| 56 | 10 | 20 | 5,297.08 | 95.21% |

These six rows are **historic energy-screen candidates**, not a complete Pareto frontier, not yet 20%-physical-SOC-corrected in their saved costs, and not AC-validated for the modified equipment. Other candidates in the full 60-row shortlist remain eligible for later stages. All six pass the *existing battery-current proxy*, which is not manufacturer/BMS interoperability certification.

## Data provenance

- Reference code revision: `e377e21d26db4bffd7a164d1257d5860bb01f325`.
- Critical-hour mode: `critical`; hours per scenario `96`.
- Original P and battery SOC schedules were unchanged under sensitivity; `reoptimized_for_PF_or_service_length` is false.
- Voltage criterion used here: 0.95–1.05 pu **research engineering target**, not official EPM service approval.
- Synthetic demand, assumed service cables, balanced EPM GIS LV equivalent and assumed 5 kVA transformer rating remain uncertainty sources.
- For data integrity and reproducibility, retain the original CSVs/manifest alongside this audit; this audit does not replace the source files.
