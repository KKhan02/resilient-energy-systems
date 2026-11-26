# A1 94022 head reserve corrected frontier | 26 November 2026

Pipeline 3120839679 job 18412258573, execution d9500a1895599ae539383473443007d2b25f8c40. Reassembled complete report and exactly matched six individual RESERVE_ENERGY and 54 RESERVE_SAMPLE records. 12 signed inputs; nine original schedule hashes; 45 event checks; 4353 night hours, 8706 endpoints, 1088 extra stored probes; 34 zero-injection failures, 34 terminal corridors, zero ceiling/unresolved failures. Tested lower sum 28.5932419147 kWh and peak 3.62103536674 kW. Six optimal chronological reserve LPs, 91 common hours, 4914 converged, 54/54 sampled groups pass. Annual energy totals/cost and cycles unchanged to 1e-6; corrected schedules distinct. No independent binary verification or causal controller proof.

| design | cost USD/a | import kWh | spill DC kWh | changed P hours | sample Vmin pu |
|---|---:|---:|---:|---:|---:|
| A0_94022_min_cost_to_A1 | 3267.25 | 1519.80 | 3173.42 | 3 | 0.950039667 |
| A1_94022_min_cost_ref | 3233.97 | 3275.15 | 1409.04 | 12 | 0.950039162 |
| A1_94022_ss90_ref | 3267.25 | 1519.80 | 3173.42 | 6 | 0.950039667 |
| A1_94022_P34_B8 | 3574.25 | 966.37 | 2560.20 | 3 | 0.950039667 |
| A1_94022_P30_B8 | 3679.89 | 1766.68 | 1328.07 | 2 | 0.950039667 |
| A1_94022_P34_B7 | 3471.04 | 1115.49 | 2725.43 | 4 | 0.950039254 |

Native minimum cost preserves lowest cost, P30_B8 minimum absolute spill, P34_B7 balanced lower-cost/lower-spill candidate, P34_B8 greater autonomy at higher cost, and two 34/6 designs energy-equivalent but distinct battery power and dispatch. All six are decision-relevant; validate both reference and severe stress (105120 annual case-hours total, no arbitrary cap), preserving three already validated designs. Deterministic reconstruction only as prior artifacts not independently available; require nine original and six corrected hashes, exact night screen/probe and 91-hour selection hashes, 12 group sample summary checks covering 1092 case-hours. No new design, margin or operating assumptions. Do not repeat 52560 already completed annual AC or 4914 reserve AC sample. Include annual losses, optional narrower voltage-band counts, all-loss purchase sensitivity, and complete matched nine-design table after results. Next shift to 85398 and A-wide synthesis.
