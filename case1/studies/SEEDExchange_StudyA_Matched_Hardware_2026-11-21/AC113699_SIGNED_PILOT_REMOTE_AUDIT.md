# Study A | Signed 113699 bounded A0/A1 AC audit, 21 November 2026

**Input commit:** e211d601314b2b34dbfceba5a224622e618b005f on private sync/seedexchange-local-2026-11-17
**Input output:** StudyA_A0_A1_MatchedHardware_AC113699_Pilot_v1
**Provenance:** Saved user-run 2025 bounded AC result; independently examined source manifest, 150 CSV rows, per-group summary, original four 8,760-hour energy CSVs and source GIS. This is NOT 8,760-hour AC validation or an independently performed pandapower solve.

## Remote-result checks

- Status BOUNDED_AC_VIOLATIONS_RECORDED_ANNUAL_PENDING. 15 distinct hours x 10 operation/assignment/frozen-hardware cases = 150 records; every unique configuration/time is present, all 150 converge, zero failures due to numerical nonconvergence.
- AC CSV SHA-256 is 05e52f3d66631b434e392d172d3373e38f18d10318aa8e03b389e8f32f7c74bb in GitLab-normalized LF; restoring original Windows CRLF gives exactly 908ce6a602e1e317288ce8d4028084b207790753fa8ed943ffd0af180a, identical to pilot RUN_MANIFEST.json. **Do not confuse GitLab LF SHA with a source-change error.**
- Reconstructed ten group summaries from CSV. All selected-hour counts, convergence, main-band feasibility counts, voltage/transformer/line extrema, strict-band violations and sampled loss sums match saved JSON to 1e-6. There are 10 AC-infeasible case-hours, all transformer overloaded; 1 of these also violates the .95 pu minimum.
- All documented A0/A1 GIS house identifiers and moved-house provisional source FIDs match previously audited signed v6.2 source manifest. A0 113699 is four houses, A1 six houses; both have six EPM GIS LV sections, and modeled radial/connected graph, with 3kVA *assumed* transformer. In A1 the two new assumed service taps are H03 57.762m / FID39974487 and H06 131.376m / FID13360817. Neither is an EPM-authorized physical reconnection. One original house H10 has 213.472m assumed service length.
- Original A0 min-cost hardware: 17PV/3B/4.700939kW DC/5kVA inverter, A1: 20PV/4B/6.439699kW DC/6kVA, both frozen across source/target assignment. Annual chronology is 2025 perfect foresight; AC model is static balanced proxy. Nighttime inverter Q remains off.

## 15 common sampled hours: exact results

| A0/A1 feeder | Equipment | Main band feasible (Q-off) | Main band feasible (daylight Q=.25) | Min voltage pu (daylight Q) | Max transformer % | Max line % |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| A0 | load-only | 15/15 | not applicable | .969406 | 72.396 | 5.299 |
| A0 | A0 frozen hardware | 15/15 | 15/15 | .969406 | 67.675 | 5.299 |
| A0 | A1 frozen hardware | 15/15 | 15/15 | .974829 | 56.505 | 5.234 |
| A1 | load-only | 11/15 | not applicable | .946960 | 109.142 | 10.888 |
| A1 | A0 frozen hardware | 13/15 | 13/15 | .951572 | 101.097 | 10.670 |
| A1 | A1 frozen hardware | 14/15 | 14/15 | .951572 | 100.523 | 10.670 |

**Exact failed A1 assignment rows under Q-off:**

| Timestamp 2025 | A1 load only, transformer % | A0 hardware-on-A1 | A1 hardware-on-A1 | Main cause |
| --- | ---: | --- | --- | --- |
| 14 Mar 19:00 | 101.097 | 101.097% FAILED, zero inverter P | 84.130% PASS, 0.5034kW inverter P | Limited evening discharge in original A0-hardware schedule |
| 11 Sep 20:00 | 108.406 | 23.194% PASS, 3.0103kW inverter P | 23.194% PASS, same 3.0103kW | Battery discharge already relieves gross-only overload |
| 06 Oct 19:00 | 109.142 | 24.213% PASS, 2.9133kW inverter P | 23.351% PASS, 3.0443kW | Battery discharge already relieves gross-only overload |
| 30 Nov 20:00 | 100.523 | 100.523% FAILED, zero inverter P | 100.523% FAILED, zero inverter P | Both existing schedules have no discharge at this hour |

**Low SOC evidence:** 14 March 19:00 A0 hardware on A1 Store e=0.687kWh (20% physical floor); 30 November 20:00 A0 on A1 Store e=0.687kWh and A1 on A1 Store e=0.916kWh, respective floors. Need *chronological energy rescheduling* for additional discharge, not an instantaneous uncontrolled SOC change. These are original schedules, not an impossibility proof for the equipment.

**Daylight Q effect:** Only two q025 rows select nonzero Q, both 2 January 06:00 on A1 feeder (+.022634kVAr for A0 hardware and +.020261kVAr for A1 hardware), improving minimum voltage by only .000186/.000167 pu and reducing transformer loading by .203/.185 percentage points respectively. All three equipment-related infeasible Q-off cases remain infeasible with Q=.25. At the three unique failure timestamps the PV availability is zero and the model disables night Q. Thus no demonstrated reactive-control remedy for those evenings.

**Critical PCC proxy discrepancy:** Source 30 November 20:00 both A1 donor schedules report modelled energy-only pcc_kva_proxy=2.860256kVA, below assumed 3kVA. Independent AC replay at that exact timestamp gives **3.015682kVA** including reactive flows and AC losses, exceeding the 3kVA screen by .5227%. This directly demonstrates why energy-only P/PF proxy does not establish AC feasibility. Also 14 March A0 hardware-on-A1 energy pcc proxy=2.877530kVA, AC pcc=3.032922kVA and transformer 101.097%. Recheck the active/reactive sign and loss basis; do not set a transformer nameplate from LP PCC proxy alone.

**Interpretation:** The tested A1 feeder with 3kVA planning nameplate is not sampled-AC feasible with the original full-year battery schedules. This does NOT prove all possible dispatches, hardware sizes, 3kVA actual EPM nameplate or actual LV attachments fail. The AC analysis does not yet include utility protection, field phase configuration or installed costs. Sampled losses are **not** annual losses.

## Next narrow scientific test: P-only AC envelope of the actual failures

At each of the **three failed frozen-hardware A1 case-hours** (A0 on A1: Mar14 19:00, Nov30 20:00; A1 on A1: Nov30 20:00), hold exact individual load and original EPM GIS network fixed, keep nighttime Q disabled, and sweep a bounded inverter active-power range from 0 to min(gross demand, inverter kVA, 0.95 × fixed battery DC power). Reproduce the saved Q-off P=0 AC result before varying P. Save ALL sampled P values, AC violations and samples with no AC solution. The first sampled AC-feasible point is a **hypothesis** for a future Linopy/PyPSA annual P corridor, not a proof that interpolation between points is feasible. Do not change SOC or manipulate saved annual dispatch. No new capacity or 94022 five-edge assumptions.

If at least one AC-feasible sampled P exists for all affected cases, test chronological full 8,760-hour fixed-hardware SOC-aware reoptimization with exactly the original PV/BESS capacities and manufacturer 20% physical floor, then AC-replay changed hours and ultimately all 8,760 hours; otherwise stop and investigate original assumed nameplate/network/feeder or hardware constraint. Do not quietly increase inverter capability, permit grid export or count nighttime unsupported Q.

**Verification status:** Independently verified saved pilot arithmetic, lineage and results. No new solver execution by assistant. No annual AC pass.
