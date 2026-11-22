# Independent full-2025 SOC equality-corridor audit | 113699 A1

**Audit date:** 22 November 2026. **Result commit:** c3653a557bf0584c74e29ea895e9905a1248f523, on sync/seedexchange-local-2026-11-17. **Model:** Proposed six-house transformer 113699 A1, 3 kVA assumed nameplate, EPM GIS inferred LV service connections, balanced three-phase proxy, PF 0.98 and service length factor 1.0. Saved results are user-executed on Windows; assistant independently checked CSVs, receipts and calculations, not a new PyPSA/pandapower calculation.

## Scope, controls and provenance

Both versioned directories were present and complete:
- StudyA_A0_A1_MatchedHardware_113699_SOC_Corridor_A0_v1
- StudyA_A0_A1_MatchedHardware_113699_SOC_Corridor_A1_v1

Each contains a signed run manifest, **8,760 chronological 2025 dispatch rows**, 15 selected pandapower AC checks, and source-versus-new SOC figure PNGs. Full-year LP output is source-provenance-checked against the exact same A0/A1 hardware-on-A1 annual energy original and the earlier AC P-sweep. Saved P constraints are actual index-3 AC-tested points, not interpolated P bands. All three original failed case-hours require an updated battery schedule because original stored energy was at the 20% physical minimum.

Source grid/non-export model **does not** automatically include feeder losses or true physical AC constraints. Preserve original 15 stress-hour profiles and exact source geometry; do not modify original solar or 35-house demand assumptions.

## Independent annual CSV audit

| Audit dimension | Fixed A0 hardware on A1 | Fixed A1 hardware on A1 |
| --- | ---: | ---: |
| PV / BESS / inverter | 17 panels / 3 modules / 5 kVA | 20 panels / 4 modules / 6 kVA |
| Installed bank DC power | 4.700939451 kW | 6.439699033 kW |
| Annual 2025 LP result | Optimal, fixed hardware, new SOC scheduling | Optimal, fixed hardware, new SOC scheduling |
| Annual demand | 11,388 kWh | 11,388 kWh |
| Original and new annual imports | 3682.545919 kWh | 2393.727936 kWh |
| Annual import difference (saved precision) | +1.2e-9 kWh | -1.6e-9 kWh |
| Annual modelled total USD (before AND after) | 2481.192672 | 2436.021870 |
| Inverter P hours changed vs signed original, >1e-5kW | 188 | 131 |
| Battery SOC hours changed vs signed original, >1e-5kWh | 135 | 106 |
| Minimum model usable battery SOC | .687 kWh | .916 kWh |
| Maximum model usable battery SOC | 12.975 kWh | 17.300 kWh |
| Max absolute hourly cyclic SOC-balance residual | <1.41e-10 kWh | <1.41e-10 kWh |
| Physical 20% SOC floor violations | 0 | 0 |
| Charge/discharge bank power violations | 0 | 0 |
| Inverter nameplate violations | 0 | 0 |
| Simultaneous charge/discharge events >1e-6kW | 0 | 0 |
| Export or unserved-load events >1e-6kW | 0 | 0 |
| Selected AC stress hours converged / feasible | 15/15 | 15/15 |
| Max transformer loading in 15 AC hours | 93.932805% | 93.402930% |
| Minimum household V in 15 AC hours | .952963pu | .952963pu |
| Optional strict lower .97pu violation hours in 15 | 5 | 4 |
| **Annual 8,760-hour AC verified** | **NO** | **NO** |

Independent recomputation: both old/new CSVs contain exactly 8,760 timestamp-matched source records with identical 2025 annual demand, PV availability, no unmet/export, virtually unchanged annual PV generation/curtailment, battery charge/discharge energy and grid imports. The new dispatch changes timing within source-equivalent cost/energy totals. The altered 188 and 131 P hours and 135 and 106 SOC hours were independently recomputed from saved old/new tables, not copied from manifest. Cyclic SOC equation checked with eta= sqrt(.95) and first-hour wrap to last saved hour.

Source-portable GitLab CRLF SHA checks:
- A0 annual CSV: Git LF SHA 6f3eae932cc8f1ed23d3a64ff9cebfd59db3232a6eb863b3f0fe1515a3ce3eae; restoring Windows CRLF yields 52f88c39afe089e2206e666c706fd8c41ccab0543377f1c9e3086cb5c43ba04d, identical to signed manifest.
- A0 15-hour AC CSV: Git LF SHA 7162a70997110c83bca6f2402d5369dc821c0342625706b3d8ce4b21acbd50fe; CRLF yields ebdf4f137ce4a8edd5f5add005f32439a2009bab04e08233d472e1e62ad65491, exact signed manifest.
- A1 annual CSV: Git LF SHA 83dcda85a621a4d28dec7ff86f9913d9ee95c952e16477f66d63880f29ff4a43; CRLF yields 4f3b9687e54ae04aa3d77c8a30a1803c6d1988fb1a82227a729b781124d8402b, exact signed manifest.
- A1 15-hour AC CSV: Git LF SHA 0ab00e659c1cb9d87888c5a19d2948ec794bdcd470e2b7d3fdef5f310a272cfd; CRLF yields a344d97679637214ac78f88a3c1bf0c1ed0096b60a2251089f8cbb473bd87725, exact signed manifest.
- All three diagnostic PNGs are binary checksum-matched to their saved manifests: A0 March 4ed4e402..., A0 November 12e4ee7e..., A1 November 38a27788....

## Important limitations and next gate

**Passing 15 selected AC stress hours does not establish 8,760-hour physical power-flow feasibility.** The optimization's annual import and total USD cost remain exactly the same because it selects another equally optimal perfect-foresight dispatch. This **is not** a proof that full-year feeder losses, upgrade costs, installed protection or hardware operating behavior cost zero. AC losses have not yet been summed for the full year, nor incorporated into dispatch optimization.

Neither the 0.97..1.03 pu optional stricter voltage screen (5 or 4 sampled-hour violations) nor actual EPM transformer rating, LV service cables and single-/three-phase arrangement are verified. The original 0.95..1.05pu and 100% screens are research assumptions.

**Next:** two separate 8,760-hour original-source EPM GIS pandapower AC replays with exactly these signed *new* full-year inverter P trajectories. Check 100% transformer and line loading, voltages .95..1.05pu, strict .97..1.03pu sensitivity, convergence, no nighttime inverter reactive support, original A1 six-house named profiles and original fixed hardware. Compare annual losses against identical original annual AC only if both source sets are AC-replayed or an equally auditable matched subset exists. Never extrapolate 15 sampled losses to 8760 hours. Recheck original source hardware and energy manifest hashes before computing. If failed hours appear, preserve them and consider further AC-constrained P adjustments and another full-year SOC solve, not new equipment without evidence.

**Windows R: drive provenance:** prior user-local `subst R:` mapping from 19 November was explicitly suggested for historic long-path annual_ac_replays_v1 archive, NOT created by these 113699 annual SOC scripts. Subst maps an existing folder to a temporary drive letter, not a new device; `subst` lists mapping, `subst R: /D` removes alias without deleting data, but old historical-root R:/ workflows then need full path.
