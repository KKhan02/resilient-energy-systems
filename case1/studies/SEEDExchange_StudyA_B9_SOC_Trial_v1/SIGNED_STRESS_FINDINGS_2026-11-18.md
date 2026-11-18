# SEEDExchange Study A | Independent B9 stress-result review
**Evidence date:** 18 November 2026. **Pushed by user:** commit `c06d4469` on `sync/seedexchange-local-2026-11-17`.
**Sources:** `StudyA_A1_106039_B9_SOC_Trial_v2/TRIAL_MANIFEST.json`, `STRESS_CASE_COMPARISON.csv`, `CHANGED_HOUR_AC_CHECKS.csv`, `CANDIDATE_SHIFT_REGISTER.csv` and candidate full-year energy schedules.

## Full annual PF=0.95, line-length factor=1.6 stress comparison

| Metric | SS_B9 | MC_B9 |
|---|---:|---:|
| Homes | 11 | 11 |
| PV panels / batteries / inverter kVA | 49 / 9 / 20 | 41 / 9 / 12 |
| Original AC-infeasible hours | 1 | 2 |
| Corrected AC-infeasible hours | **0** | **0** |
| Original worst transformer loading | 107.431169% | 107.431169% |
| Corrected worst transformer loading | **99.431815%** | **99.431815%** |
| Corrected minimum voltage | 0.957239659 pu | 0.957239659 pu |
| Corrected maximum line loading | 7.909677% | 7.909677% |
| Corrected annual imported energy | 1,478.227846 kWh | 2,792.928666 kWh |
| Changed case-hours | 2 | 4 |

All original and candidate changed-hour solves converged. Six unique case-hour changes were solved both as originals and candidates, **12 new AC evaluations**. The other **17,514 case-hour snapshots** were preserved from the verified, separately simulated original 8,760-hour stress AC replays. Annual battery discharge, grid imports, 20%-physical-floor-equivalent SOC, terminal SOC, no-export and no-unserved-load constraints remained unchanged.

## Event-by-event transformer loading

| Case | Event (2025) | Original | Candidate | DC power shift |
|---|---|---:|---:|---|
| MC_B9 | Oct 13 17:00 donor | 23.742905% | 26.874933% | Save 0.60 kW |
| MC_B9 | Oct 13 20:00 constrained | 103.195603% | 92.082522% | Release 0.60 kW |
| MC_B9 | Nov 27 18:00 donor | 54.590830% | 68.357505% | Save 0.80 kW |
| MC_B9 | Nov 27 20:00 constrained | 107.431169% | 92.533365% | Release 0.80 kW |
| SS_B9 | Nov 27 18:00 donor | 28.837693% | 33.384907% | Save 0.80 kW |
| SS_B9 | Nov 27 20:00 constrained | 107.431169% | 92.533365% | Release 0.80 kW |

The transformer **106039 nameplate is assumed 5 kVA**, not EPM certified. The passing model retains only **0.568185 percentage points**, approximately **28.4 VA**, of headroom at its peak. It is not a robust operating margin, actual conductor/equipment certification or proof under uncertainty.

## Byte-level provenance finding

GitLab normalized both committed candidate CSV files from Windows CRLF to LF. Independent hashing of the entire GitLab CSV content, with LF converted back to CRLF, produced exactly the manifest SHA-256 values:

- SS_B9: manifest CRLF `55fd31443a3ecd4315e61f6de55c60d39b544a2d4f3d82b68c26d52081594dc2`; GitLab LF `63ef1fce216686473ab67862d4b1686b006bec1e45c010ccf115302bfb350006`.
- MC_B9: manifest CRLF `a93fe0d2ab8095ff933d8fc7e8dd49a1307952d45376fe624197537d44881717`; GitLab LF `4055656762836fa0f24050744a32f6923d9d5b42595999fdd1f85ce33b68c75d`.

This is confirmed line-ending normalization, **not altered numerical data**. Original Windows working-copy SHA checks remain a valid gate.

## Next research actions

1. Run the existing gated nine-factor **changed-hour** screen: `case1/studies/SEEDExchange_StudyA_B9_SOC_Trial_v1/b9_nine_factor_changed_hours.py`, using the user-generated `StudyA_A1_106039_B9_SOC_Trial_v2` root. It checks six case-hours × two original/candidate states × nine factors, **108 AC solves**. Source checks and the prior stress **PASS** are mandatory.
2. If this passes, separately validate **all 8,760 hours** for the remaining eight factor scenarios per hardware design, without inferring annual compliance from changed hours alone.
3. Include actual AC-network losses, equipment/BOS costs and transformer/nameplate verification before claiming robust economic superiority or recommending equipment sizing.

**Historical baselines unaffected:** 376/432 passing original-network AC cases, versus 408/432 conditional on an explicitly hypothetical A0 five-edge model. These B9 fixed-equipment candidate designs are separate and do not change the 432-case denominator.
