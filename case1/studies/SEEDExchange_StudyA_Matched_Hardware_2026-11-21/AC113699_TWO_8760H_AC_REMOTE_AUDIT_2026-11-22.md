# Study A | 113699 A1, independent 2025 full-year AC replay audit

**Audit date:** 22 November 2026. **User source-result commit:** f580c39349478f0bccafddbf697a93bb0b8bb4b4. **Current research status:** Two 8760-hour source-verified, cyclic-SOC fixed-hardware schedules pass the ORIGINAL EPM GIS balanced-model main AC research screen for A1 six-house assignment at **PF 0.98, length multiplier 1.0, assumed transformer 3 kVA**. This is not EPM service approval, utility-certified transformer nameplate, phase/neutral proof or compliance with optional strict voltage bands.

## Required corrections and source integrity

The synthetic test test_matched_hardware_113699_soc_corridor.py originally failed one of 61 tests due only to Python binary floating-point rounding: computed .21149999999999997 versus literal .2115 in assertEqual. The model's equality corridor remains genuinely equal lower and upper P. Assistant changed only that contract test to assertEqual(lo,hi) plus assertAlmostEqual(lo,.2115,places=10), GitLab commit 0f0fdb5e, after user source-result commit. No source simulation equations, archived inputs, LP, pandapower outputs or physical constraints changed. 60/61 tests passed before correction; updated tests not yet rerun on user's Miniforge. The source run itself was completed/pushed irrespective of this non-material test defect.

Archived original signed SOC annual source manifests remain pinned:
- A0 fixed hardware 17 PV panels / three modules / 4.700939451 kW DC / 5 kVA inverter, original source ANNUAL_SOC_FEASIBLE_15_SAMPLE_AC_PASS_ANNUAL_AC_PENDING.
- A1 fixed hardware 20 PV panels / four modules / 6.439699033 kW DC / 6 kVA inverter, same source status.
- Prior 8760-hour annual energy records passed zero-export, zero-ENS, 20% physical SOC floor, cyclic SOCEnergy with sqrt(.95) charge/discharge efficiency, installer power limits, and exact sample-3 night P equality corridor.
- The full AC outputs are saved, not solver-recomputed by assistant, in StudyA_A0_A1_MatchedHardware_113699_AnnualAC_A0_v1 and _A1_v1.

Checked two 8760h full-year AC CSVs directly, exact chronological alignment with each signed 8760h SOC dispatch, each original household gross demand and its source inverter output for all 8760 hours. Every row is unique and CONVERGED. Recomputed per-hour main 0.95..1.05pu /100% transformer/line flags; all 15 originally validated stress hours agree with full-year independently saved AC values to the replay tolerance. Manifest counts, min/max voltage, peak transformer loading and annual losses match the uploaded raw AC CSVs, not merely receipt status.

| 2025 A1 territory model metric | A0-origin fixed hardware | A1-origin fixed hardware |
| --- | ---: | ---: |
| AC solves complete | 8760 / 8760 | 8760 / 8760 |
| Source annual P/housing profile exact match | 8760 / 8760 | 8760 / 8760 |
| AC convergence | 8760 / 8760 | 8760 / 8760 |
| Main AC research screen feasible | 8760 / 8760 | 8760 / 8760 |
| Transformer loading >100% | 0 hours | 0 hours |
| Line loading >100% | 0 hours | 0 hours |
| Household voltage below .95pu or above 1.05pu | 0 hours | 0 hours |
| Optional voltage below .97pu | **245 hours** | **120 hours** |
| Optional voltage above 1.03pu | 0 hours | 0 hours |
| Lowest modelled household voltage | .9529631731pu | .9529631731pu |
| Highest modelled household voltage | .9985376650pu | .9986068133pu |
| Peak modelled transformer loading | 95.75093728% | 95.75093728% |
| Peak modelled line loading | 10.66995542% | 10.66995542% |
| Annual original balanced-model line + transformer losses | **286.963521 kWh** | **276.372000 kWh** |
| Controller selects nonzero daylight Q | 108 hours | 86 hours |
| Nonzero Q when original NASA PV availability says night | 0 | 0 |
| Fifteen originally signed AC points reproduced | 15 / 15 | 15 / 15 |

Both peak transformer loading events occur at 2025-10-23 20:00; both minimum voltages occur at 2025-11-30 20:00. Maximum saved model AC PCC is 2.872528 kVA. No power-flow errors, no missing records, no output discrepancies from signed source schedule.

**When/where strict voltage fails:** Of A0 245 hours <.97pu, 59 are in November and 53 October; A1 120 hours, 39 November and 24 October. Strict violations remain even after the original overload repairs. This is evidence requiring targeted **model** voltage management and uncertain physical topology investigation. Do NOT relabel a main-screen pass as strict pass. The strict criterion is separate research screening, not an established EPM statutory grid code requirement for this circuit.

Binary diagnostic PNG checks from saved manifest against GitLab file content:
- A0 annual_min_voltage.png 60831b8600f949b685cdfb124e1d2cd861498e8f72f5f491fc8a8069bc46da8b; annual_transformer_loading.png 4f749d96d1fc6cf5d501df93b2dff3549e3b1cda3985e9eef76872f232e69766.
- A1 annual_min_voltage.png c312c5cb27340c0de0e8131c9d186c3dc3d73c6598b1596c6757f97da4f58c8e; annual_transformer_loading.png 239b8d3f164e0bf3ae0a1de24281680db3cbc53814d9b2381065dfd79433baa5.
All four actual GitLab binary hashes equal manifest. GitLab-normalized text CSV SHA for A0 is 0dcc9b8849e3b2c4a47b1beb6bb0b1fbd58582ab775de40d720f87485e203523, A1 299057d26e79645e15e1ec54efe8997ea2f212a0ee7924fafcbff825275f77bd, original user Windows CRLF digests retained in source manifest 3a05d64b... and d56aed64... respectively. Do not mistake normalization for altered physics.

## Scientific interpretation and next bounded gate

The original paired fixed-hardware 2025 energy-only LP objective stayed the same after cyclic-SOC redispatch: A0 origin model annual total USD 2481.192672, A1 origin model annual total USD 2436.021870, with annually unchanged imports 3682.545919 and 2393.727936 kWh. Those are **different hardware capacities**, so the approx 10.591521 kWh/yr gap in AC losses is not an isolated hardware effect or an already monetized benefit. AC losses are post-processing; they are not fed back into the original PyPSA billing/dispatch objective. No annual original-uncorrected AC baseline was run on the same hardware for loss delta, and no feeder reinforcement cost has been added.

The reference model now passes the main research AC screen for two different capacities, but the reserve is only ~4.249 percentage points of the assumed transformer rating at worst loading. Future feasibility is sensitive to household PF, assumed service length, EPM installed transformer nameplate, service-wire phasing/neutral and load stochasticity. Recommended **bounded next gate**: source-pin both new complete annual AC results, select a common 2025 high-stress hour set from actual 8760 AC minima, peak load/transformer/line metrics, strictly low voltage events and calendar markers, then independently sweep original GIS/solver PF .95/.98/1.00 by service multiplier 1.0/1.3/1.6 for both frozen annual SOC dispatches. Compare all 9 combinations at exactly the same stress timestamps. This is a 9-factor *sampled* robustness screening, **not** 9 separate annual AC certifications. Prioritize full annual replays only for physically plausible/decision-changing factors, and obtain EPM equipment and phase source evidence before concluding physical hosting capacity.

No original annual input altered; main unchanged; sync branch only. Original 94022 five-edge hypothetical and 92395 STAR/MST proposal remain separate physical network cases.
