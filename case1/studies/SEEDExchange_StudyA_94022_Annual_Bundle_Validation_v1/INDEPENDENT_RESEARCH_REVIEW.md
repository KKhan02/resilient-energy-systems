# SEEDExchange Study A: A0 94022 nine-factor branch-bundle audit

**Audit date:** 2026-11-16. **Source:** `StudyA_A0_94022_AllNine_Bundle_v1_Results.zip`, SHA-256 `d94c960eb657ac866f8ea70849adc1633a52ccd5c16d656653733ef24126cc2d`.

## Verified evidence

- ZIP CRC pass. Exactly 1,620 unique rows, 5 network options × 4 original A0 94022 equipment/dispatch schedules × 9 previously identified residual timestamps × 9 PF/length combinations. The factor grid is PF 0.95/0.98/1.00 and service length ×1.0/1.3/1.6.
- All 1,620 cases converged, their voltage/loading metrics are finite, and all saved feasibility flags agree with recomputed 0.95–1.05 pu household voltage and ≤100% transformer/line loading criteria.
- **360 matched rows** were independently cross-checked against the previous 2-factor dual-service trial contained in the published research package. Maximum absolute discrepancy for the voltage, transformer and line metrics was `3.552714e-15` (percent for loadings). All 360 feasibility labels reproduce.
- The original head-inverter network passes 198/324 targeted snapshots, min voltage 0.937278 pu, max transformer loading 98.205%.
- Four changed model edges `[7,4,14,11]` with only resistance halved pass **324/324** targeted snapshots, min voltage 0.951268 pu, max transformer loading 97.513%, voltage headroom 0.001268 pu. Their sum of original *model-edge lengths* is 791.992 m.
- Five edges `[7,4,14,11,16]`: **324/324**, min voltage 0.953224 pu, max transformer loading 97.396%, original model-edge length 826.648 m.
- Six edges `[7,4,14,11,16,18]`: **324/324**, min voltage 0.954500 pu, max transformer loading 97.339%, original model-edge length 854.357 m.
- All 26 modelled LV edges with R×0.5: **324/324**, min voltage 0.956955 pu, max transformer loading 97.068%, 2028.967 m.

## What this means

The four-edge model is the smallest **among options actually tested**, not necessarily globally minimal or cost-optimal. Its 0.001268 pu margin is extremely small relative to unverified conductor sizes, household phases and point-of-connection assumptions. The five-edge option is the most reasonable next *research sensitivity* candidate because of somewhat greater margin with only one additional model edge. This is not a conductor recommendation or a field installation design.

The additional conductor resistance reductions act on model edges only. The H01/H06 household service connections are hypothetical paths and exceptionally long (~326.6 m/~315.3 m). Modelled line indices 014/011 correspond to EPM LV GIS sections 47053086/47053070, but tap splits and lengths may not match physical replacement segments. Reactance, ampacity, protection, transformer ratings, phase model, demand, equipment and SOC are unchanged. No cable catalogue/cost, as-built service routes or utility approval has been established. The 5 kVA transformer rating at 94022 has EPM source evidence but the service assignments and impedances remain conditional.

Importantly, H06 is assigned to transformer 113699 under proposed geographic nearest A1, rather than 94022 under A0. Improving a long *assumed* A0 service to H06 may be pointless if the actual network/utility connection differs. Compare A0 retrofit only as a conditional counterfactual to A1.

## Critical remaining research gate

The 1,620 calculations are **selected-hour tests**, not 8,760-hour network validation. Reduced resistance can affect daytime voltage rise, loss and reactive behavior in untested hours. Do not revise the signed 432-case portfolio pass/fail counts yet: **376 passing / 56 failing**, comprising 32 A0 94022 and 24 A0 92395 proposed MST.

Next run one *new annual AC network sensitivity* for the five-edge R×0.5 hypothesis, starting with all four A0 94022 optimized/causal dispatch schedules at PF 0.95, length ×1.6 (4 × 8,760 = 35,040 hours). Independently compare 9 selected-hour controls against this upload. If all annual cases pass with acceptable margin, expand the same fixed bundle to nine PF/length combinations without rerunning completed jobs. The runner computes annual line/transformer losses, but does not update economic costs or PV curtailment. If the five-edge hypothesis has newly detected annual failures, diagnose them before trying six edges.

Following the annual electrical gate: verify actual utility service connections/phase and cable ratings; compare hypothetical A0 upgrade cost against A1 alternative; proceed with the independent PV/BESS utilization and cost frontier and Study B 92395 STAR/MST analysis. The trial is still not robust engineering certification.

## Provenance and status

All original user Windows numerical runs and source code remain unmodified. No new pandapower numerical AC runs were executed in the assistant environment. This package includes reproducible code for user-local annual validation and complete original targeted evidence in the `inputs` directory. No GitLab changes were made.
