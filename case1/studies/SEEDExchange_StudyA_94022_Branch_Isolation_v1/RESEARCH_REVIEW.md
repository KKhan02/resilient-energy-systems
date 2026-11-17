# A0 94022: independent network-option audit and branch-isolation decision

**Date:** 2026-11-16. **Status:** 360-file-record independent audit passed; no annual network upgrade proven.

## Provenance

User-provided `StudyA_A0_94022_Network_Probe_v1.zip` SHA-256 `b9e5764d425c0dd1472234eaf4b545e6784fc8cb413eed6af1d84d464f94fb4b` contains exactly 360 converged pandapower snapshot records, one probe manifest, and nine timestamps. Four A0 94022 (min-cost/SS90, optimized/causal) schedules, nine timestamps, two factor pairs (PF 0.98 × length 1.0; PF 0.95 × length 1.6), five options. All 360 case keys unique and flags independently checked against 0.95–1.05 pu bus voltage and 100% maximum transformer and line loading. Input manifest reports original transformer-head model reproduced earlier source AC. This is a file-level audit and does not represent a fresh assistant-run pandapower power flow.

The ZIP includes eight extra case-hour-factor combinations per option: all four schedules at selected timestamps even if they were not originally unresolved for that particular case. There are 32 distinct unresolved **schedule-hour** keys, each represented under both factors; 64 corresponding records per option. Use 72 as the *targeted tested snapshots* denominator, not 72 distinct originally failed conditions.

## Audit summary

| Model option | Feasible /72 | Undervoltage records | Overvoltage records | Worst low voltage (pu) | Worst high voltage (pu) | Peak transformer loading (%) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Existing head connection | 28 | 44 | 0 | 0.937278 | 0.994930 | 98.205 |
| Midpoint proxy | 50 | 22 | 0 | 0.937278 | 1.019572 | 98.205 |
| Feeder-end proxy | 6 | 20 | 46 | 0.937278 | **1.112727** | 98.205 |
| Head, all LV R ×0.75 | 60 | 12 | 0 | 0.947272 | 0.995201 | 97.627 |
| Head, all LV R ×0.50 | **72** | **0** | **0** | **0.956955** | 0.995471 | 97.068 |

All tested line loadings remain <18%. All 360 events have available PV DC power 0 kW and occur in the evening. Source `grid_import_kw` denotes the fixed dispatch's energy-model import, not a new loss-aware electrical meter total.

### Factor-specific result

| Option | PF 0.98, length ×1.0 | PF 0.95, length ×1.6 |
| --- | ---: | ---: |
| Head | 24/36 | 4/36 |
| Midpoint | 26/36 | 24/36 |
| End | 4/36 | 2/36 |
| R ×0.75 | 36/36 | 24/36 |
| R ×0.50 | 36/36 | 36/36 |

H01 is the limiting household in **all** transformer-head and resistance-scaled cases. Midpoint connection changes the limiting household in several cases; feeder end raises voltage severely in the injection hours and therefore creates overvoltage. When the inverter active output is zero (28 March 20:00, 27 November 20:00, and some 29 November 20:00 cases), simply moving the inverter yields no benefit under the nighttime-Q-disabled assumption.

### What this proves and what it does not

- **Proves conditionally in the selected network model:** voltage-drop sensitivity is substantial; uniformly lower line resistance at the *unchanged* head inverter would eliminate all tested residual-hour violations. The strongest sampled option retained a 0.006955 pu margin against the 0.95 pu threshold at the tested hours.
- **Does not prove:** an actual available cable choice, conductor Ampacity or reactance, installation budget, 8760-hour AC feasibility, equipment controls or dynamic islanding. `R ×0.50` was applied to all modelled LV lines, including assumed house service lines; transformer impedance and actual customer connection identities remain fixed. No costs were optimized.
- **Does not alter:** annual PV curtailment, battery modules, unchanged annual power schedules, or earlier 432 annual AC results. The current portfolio remains **376 pass / 56 fail**, 32 failing scenario runs on A0 94022 and 24 on proposed A0 92395 MST, pending a validated annual network alternative.

## Research next action

The next discriminating experiment tests which **individual line or line category** contributes most. Separate GIS LV segments from assumed household service drops. Test one-branch-only R ×0.50, GIS-only R ×0.50 and services-only R ×0.50. Retain the original head inverter placement and the same nine residual timestamps/two factors. Output line IDs, lengths, kind, worst limiting house, voltage/thermal margins. Resistances are only *proxies*, not conductor types. Then check all nine factor pairs and the full year only for defensible physical candidates, with actual cable specs and costs.

The purpose of Study A is to compare the original versus geographic-nearest assignments. A0 94022's need for network reinforcement is itself a meaningful finding, rather than a mandate to engineer A0 to equal the A1 result at any cost. If physical upgrade economics are pursued, integrate them in Study B with the proposed 92395 network design.

## Evidence

See the CSVs `NETWORK_OPTIONS_SUMMARY.csv`, `NETWORK_OPTIONS_BY_FACTOR.csv`, `NETWORK_OPTIONS_BY_EVENT.csv`, `MINIMUM_VOLTAGE_CHANGES_VS_HEAD.csv`, and `INDEPENDENT_AUDIT.json`. The original user probe ZIP is retained as read-only evidence under `inputs/`.
