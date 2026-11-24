# Study A | independent March plus November SS90 two-event AC audit

**Audited:** 24 November 2026. **Original upload:** GitLab commit `b5f2ae3c104b90edb41f4ff22af68f5fea32bec6`. **Source result:** `StudyA_94022_MarNov_SS90_DonorTarget_AC_Shift_v1/`. **Verdict:** complete bounded 20 AC case-hour March pilot, 3/5 March transfer fractions pass all March donor/target/PF samples and preserve November's four archived accepted samples. **Annual AC unverified.**

## 1. Result and digital provenance

- One folder `StudyA_94022_MarNov_SS90_DonorTarget_AC_Shift_v1` uploaded, with `RUN_MANIFEST.json`, `MARCH_DONOR_TARGET_20_AC_CASEHOURS.csv`, `MARCH_CANDIDATES_5.csv`, two diagnostic plots. Actual source hours March 28 2025 17:00 donor and 20:00 target, original A0 10-house transformer 94022 GIS, A1-origin SS90 six battery-module fixed hardware, provisional 5 kVA transformer, original service length x1.0, PF .98/.95. November 27 2025 accepted source 17:00 donor to 20:00 target (98% of its donor limit) remains fixed.
- Independently parsed all **20 unique** March fraction/PF/point records, all `CONVERGED`; their `ac_feasible` flags agree with the voltage and thermal flags. Precisely **3/20 infeasible**, all from target undervoltage below .95 pu: March fraction 0, PF .98 and .95; fraction .25, PF .95. **Zero donor-hour failures**, zero overvoltage, zero transformer and zero line overloads. Ten source points from both PFs and both March hours are not annual AC scans.
- CSV SHA provenance: GitLab normalized LF AC CSV SHA-256 `6c8b6328d074c9490afc338dd4da6d62d7627b5f8803a7d75bbeb41238292858`; normalization only to Windows CRLF produces **exact saved manifest hash** `c0b46b80cb08ef54a8e19ec67341de51fb04b91ed9719949553596fa9f08575e`. GitLab LF candidate CSV SHA-256 `ad092785374da522bcdad2039383c79805d3635e8f9a0b82f0148bfc816316e3`; CRLF restoration exactly matches manifest `34eda749d33a5473fab41dbd286107552d0e1c87ea7a98eff735a9e28c2617ed`. Plot PNG GitLab SHA-256 matches the manifest: `march_min_voltage_vs_shift.png` `02235a28c00281b5a8e3f1d2d9e912dcfe63c9275d4f69ddbb91a1b048071d1f`, `march_trafo_loading_vs_shift.png` `be2479ce2ecb2040cd82059046b05a1c240d7b94e79060a9aa9462304c4ab04c`. No data corruption indicated by line-endings.

## 2. Original March failure and tested corrected AC

March 28 20:00 signed P=0 and the source original minimum house V at PF .98 = **0.9499715541 pu**, PF .95 = **0.9471409072 pu**. The source March 17:00 donor has original DC battery discharge **2.4624426754 kW**, so fractions of 0, .25, .50, .75 and .98 correspond to added 20:00 AC output of 0, .584830, **1.169660**, 1.754490 and 2.292534 kW (inverter efficiency .95), respectively.

| March fraction | Extra target inverter P [kW AC] | March target V PF .98 [pu] | March target V PF .95 [pu] | March donor V PF .95 [pu] | March 4/4 + old November 4/4 |
|---|---:|---:|---:|---:|---|
| 0 | 0 | .94997155 | .94714091 | .97687791 | FAIL |
| .25 | .58483014 | .95227186 | .94944892 | .97471257 | FAIL |
| **.50** | **1.16966027** | **.95455253** | **.95173714** | **.97252942** | **PASS** |
| .75 | 1.75449041 | .95681391 | .95400588 | .97070680 | PASS |
| .98 | 2.29253413 | .95887762 | .95607623 | .96925958 | PASS |

The 50% March transfer is the smallest **sampled** passing amount (not an optimized minimum passing magnitude). At PF .95 its March 20:00 margin to 0.95 is +.001737 pu. March 50% 17:00 donor PF .95 minV .972529 pu, and March transformer loading PF .95 peaks at 63.23249% at target. All four March rows converged. The archived November four accepted results use precisely the unchanged previous 98% correction: at PF .95 minV November 20:00 **.9506981274 pu** and donor 17:00 **.9671966321 pu**; worst main-band margin across March+November is therefore November 20:00 **+.0006981274 pu**. Note that the November donor and all evening targets fail the optional stricter .97 minimum screen. Do not claim 0.97-band robustness.

For March fraction .50, all **eight sampled AC point records** are main-band passing across two days, both PF .98/.95 and both donor/target hours. Four November points are independently cross-checked previously archived values, **not four fresh new March-run power flows**. The manifest's 8/8 is correct but must retain the reused-source distinction.

## 3. Fully independent annual DC/AC power and cyclic battery replay

Independently read the original `StudyA_A0_A1_MatchedHardware_Full_v1/A1_94022_ss90_to_A0/energy_hourly_2025.csv`, applied **both** signed transfers to an in-memory copy, and reevaluated **all 8760 hourly records** including the December-to-January cyclic boundary:

- March donor 2025-03-28 17:00 defers `0.50 × 2.4624426754 = 1.2312213377` kW DC. March target 20:00 obtains +1.169660270815 kW AC. Original source March donor P=2.7731939001 kW AC, target P=0. Same battery/inverter/transformer assumed hardware.
- November donor 2025-11-27 17:00 defers `0.98 × 1.9176825037 = 1.879328853626` kW DC. November target 20:00 obtains +1.785362410945 kW AC. The two transfer windows do not overlap.
- Changed inverter-P hours **exactly four**: March 28 17:00 and 20:00, November 27 17:00 and 20:00. At each of these four times and both PFs the in-memory P exactly matches the archived March or November accepted AC inverter P. No change to per-household stochastic demand or GIS.
- Annual **energy-only grid imports** unchanged at **4196.6064106846 kWh**. Annual battery DC discharged energy unchanged at **7413.9927006602 kWh**, original annual battery DC charging 7804.2028428008 kWh, and curtailed PV DC 2007.9876854120 kWh. No grid export or ENS introduced. Year-end modeled Store unchanged.
- Maximum absolute per-hour reconstructed AC balance residual ≈1.00e-10 kW; PV/DC/inverter balance ≈1.42e-10 kW; cyclic storage transition ≈1.41e-10 kWh. Minimum modeled Store = **1.374 kWh** (6 battery modules × .229 kWh per module source 20% physical SOC mapping), maximum = **25.95 kWh**, original original bank inverter P envelope respected; peak inverter P 4.760835 kW AC, peak battery discharge 5.011405 kW DC, peak charge 8.5509546185 kW DC (rounding consistent with source hardware rating 8.55095461847511).
- All source ledger checks use the **same 8,760-hour 2025 signed original** and preserve exact source mapping. The corrected annual schedule is a fixed-hardware **candidate redispatch**, not a fresh PyPSA cost-minimum, annual AC or physical network field certification. Annual source-energy-only imports stay the same, but losses and any loss-adjusted economic valuation are not yet checked across all annual hours.

## 4. Recommended next research gate

Choose the **combined SS90 March .50 plus November .98** as the *minimum tested-correction reference*, conditional on original signed A0 94022 ten-house GIS. It is not evidence that a min-cost hardware option or a separate route could never work.

**The next genuinely decision-changing validation is original source-matched annual AC**, not a new 6,840-task energy optimization. A defensible low-duplication path is to run a signed **8760-hour original reciprocal SS90 annual baseline AC** for PF .98 on the frozen same-year A0 ten-house GIS. Then recompute the AC only for the **four changed P hours** at PF .98 and combine with 8756 exactly unchanged hours, but only after validating the original source P, per-house phase/GIS mapping and stateless hourly solver independence. Repeat PF .95 for robustness and scope 1.3/1.6 length factors after results require it. Do not reuse an annual AC file from A1 loads or native A0 hardware unless its every relevant input and equipment are identical. Save both original and corrected annual violation counts, max line/transformer loading, voltage extrema, annual AC network loss kWh and source SHA. Candidate from same hardware and same source remains to be compared with actual EPM nameplate, service circuits, phase/neutral and conductor evidence before implementability claims.

Historical signed AC and energy runs, main, previous November v1/v2, and unrelated untracked local outputs remain untouched. No live annual AC was run in this audit.
