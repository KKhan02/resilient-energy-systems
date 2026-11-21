# Reciprocal Study A signed-source audit | 21 November 2026

**Read-only GitLab validation, not new energy simulations.**

- Original `MATCHED_HARDWARE_16_SOURCE_PLAN.csv` has exactly 16 A0/A1 source portfolios: four named transformers, two equipment tiers, two directions. Excludes unchanged 92395 proposed STAR from newly simulated cases and excludes H08 on unmapped support-only 98380 from both sides.
- Opened all 16 original `energy_manifest.json` files. Every donor A0/A1 house list, original signed hardware, battery DC rating, inverter kVA and assumed transformer rating matches the experiment roster.
- Read all 16 original 8,760-hour CSVs, **140,160 hourly records**. All 16 pass 20% physical SOC floor, maximum battery/inverter power, no simultaneous charging/discharging, and cyclic SOC consistency. Example maximum hourly SOC residuals around `1.4e-10 kWh`. The complete preflight is still required on the user's checkout with source SHA gates.
- Original source input-manifest SHA `2ff7eb9c1f28f12efc11aca9b366e5277da72a62f6d7709f47dc3841b6e71d69`; NASA solar source SHA `b03e9274d40fcc486eddc54a2cada013c1493bd5562216f27e984f4d5d5d1e08`.
- A0 and A1 106039 **minimum-cost** sources both have exactly 41 PV panels, eight batteries, 12 kW DC power and 12 kVA inverter. Their 8,760-hour original energy schedules are valid same-hardware reciprocal outputs. The two remain distinct A0/A1 **load and network** scenarios and must not be mistaken for the same household time series.
- User-pushed initial A1-to-A0 113699 pilot `StudyA_A0_A1_MatchedHardware_113699_Pilot_v1` has 8,760 unique timestamps and zero export/ENS, no simultaneous battery events, min/max SOC inside bank bounds, maximum inverter 2.0443 kW, and maximum absolute cyclic SOC residual `1.409e-10 kWh`. Annual A0 imports 208.529525 kWh; PV DC curtailment 2563.116348 kWh; equipment + grid USD1802.314331. The grid purchase rate in the model remains USD0.29/kWh.
- After reusing the initial pilot plus two reciprocal same-device 106039 source schedules, the full study needs **13 additional annual LP solves** under the current code. The next A0-to-A1 113699 reverse pilot remains unrun and would permit further reuse if validated.

**Conclusions:** Original and pilot source data pass recorded energy checks. No source supports a new EPM connection approval, 94022 conductor CAPEX estimate, actual 92395 feeder, corrected aggregate network-loss total or all-16 AC pass. User-local reverse pilot and independent remote audit come first.
