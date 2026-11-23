# Study A | independent audit of reciprocal P1 six-case 36-hour AC upload

**Date:** 23 November 2026. **Branch:** `sync/seedexchange-local-2026-11-17`. **New source upload:** GitLab commit `12e0348d7b0b9df33460fcc63eb6e8250743e95b`, folder `StudyA_Reciprocal12_P1_AC_Pilot_v1/`.

## Audit status and source fidelity

**Verdict: 36/36 recorded AC case-hour results, 36/36 converged, 20/36 fail the modeled main-band screen; source P and target case-hour association independently cross-checked.** No new pandapower, PyPSA or other numerical solver was run by the reviewer.

The 36-row `TARGETED_36_AC_CASEHOURS.csv` was independently parsed and compared with the archived 18-row `RECIPROCAL12_P1_18H_SOURCE_PLAN_2026-11-23.csv` and the 16-case frozen `StudyA_A0_A1_MatchedHardware_Full_v1/RUN_MANIFEST.json`. Every case/time/PF pair is unique; all six source SHA strings match their frozen reciprocal case; 18/18 selected source event rows match the 2025 saved original demand, inverter active P, grid import, PV DC availability and target assignment to within 1e-7 kW; no source event mismatch. The run manifest reports a six-case signed GIS source preflight with exact 8760-hour energy source verification, assumed 3/5 kVA transformer sizes, balanced three-phase model, and no field EPM verification. We independently verified the selected **rows** and their frozen case SHA references, not a second byte-for-byte recomputation of all six 8760-hour source files.

Manifest lists `P1_TARGETED_36_AC_CASEHOURS_RECORDED_NOT_ANNUAL`, 6 case families, 18 time-stamped case events, PF [.98,.95], service factor 1.0, selected daytime Q ratio .25, zero AC annual/field verified claims. Independent source CSV check found 36 rows, all `CONVERGED`, no error text, all individual `ac_feasible` flags consistent with main voltage and line/transformer overload flags; 20 infeasible, 16 feasible. Of 36 rows, 24 are zero-PV night and 12 are day; all 20 failures are at night, and all 12 daylight case-hours are feasible. Exactly 12 flagged undervoltage below .95 pu, 12 flagged transformer loading above 100%, with **4 overlapping** the two, making 20 unique failed cases. Zero above 1.05 pu and zero line overload cases. PF=.98 and PF=.95 each have 10 failed out of 18; lower PF makes severity worse at several points without changing this sample's failure count. Maximum line loading across all cases is only 10.7498696671% under the assumed GIS/conductor model.

All night records have Q=0 and status `Q_OFF`; each daytime case has `AC_FEASIBLE_Q` but **Q selected and requested are also 0**. This is a source-specific diagnostic outcome, not a finding that reactive support is never needed. The actual number of internal pandapower solves remains unmeasured; the `ac_evaluations` field counts unique Q measurement points rather than every `runpp` call.

### Numerical results by frozen reciprocal case

| Frozen reciprocal case | Assignment | AC failed / evaluated | PF.98 / PF.95 failures | Main cause | Worst min house V [pu] | Max assumed transformer [%] |
|---|---|---:|---:|---|---:|---:|
| `A1_94022_min_cost_to_A0` | A0 10-house | 4/6 | 2/2 | Under-voltage, nights 28 Mar and 27 Nov | 0.943656335 | 94.221260 |
| `A1_94022_ss90_to_A0` | A0 10-house | 4/6 | 2/2 | Same demand/no-night-inverter-P, same night result | 0.943656335 | 94.221260 |
| `A0_113699_min_cost_to_A1` | A1 6-house | 4/8 | 2/2 | Trafo >100% on 14 Mar and 30 Nov; PF .95 also V under .95 | 0.948364476 | 104.834828 |
| `A0_113699_ss90_to_A1` | A1 6-house | 4/8 | 2/2 | Same night P and PF, same night results | 0.948364476 | 104.834828 |
| `A0_106039_ss90_to_A1` | A1 11-house | 2/4 | 1/1 | Trafo overload 27 Nov, both PF | 0.956512167 | 107.313666 |
| `A1_106039_ss90_to_A0` | A0 12-house | 2/4 | 1/1 | Trafo overload 27 Nov, both PF | 0.950850476 | 109.306022 |

**Independent scenario aggregation:** 94022 8/12 failed (voltage only); 113699 8/16 failed (transformer, with four PF .95 voltage cofailures); 106039 4/8 failed (transformer only). All 36 AC calculations converged, so the failed model screen must not be reported as a solver crash. Worst voltage = 0.9436563346 pu (94022 at 2025-11-27 20:00, PF .95). Highest transformer loading = 109.3060222% (A1 hardware SS90 on A0 106039, 2025-11-27 20:00, PF .95).

### New independent battery-source finding

Reopened **six full signed-source 8760-hour P dispatch CSV files** at their *actual frozen manifest paths* and inspected all hourly `battery_soc_usable_kwh` readings. Every failed-night source event has the battery **exactly at that case's minimum observed annual usable-store energy**, rather than above its saved annual observed floor. That is true even when the hour still has a small recorded inverter discharge, because the energy series records state at the snapshot. These are **observed source-year minima**, not independently certified battery physical SOC=20%, and the PyPSA generic `Store` energy definition alone does not prove these minima are immutable operational floors.

| Frozen case | Battery modules | Minimum observed 2025 stored energy [kWh] | Source stored energy on failing evening hour(s) | Observed 2025-11-27 20:00 inverter P [kW] |
|---|---:|---:|---:|---:|
| `A1_94022_min_cost_to_A0` | 5 | 1.145 | 1.145 (28 Mar, 27 Nov) | 0 |
| `A1_94022_ss90_to_A0` | 6 | 1.374 | 1.374 (28 Mar, 27 Nov) | 0 |
| `A0_113699_min_cost_to_A1` | 3 | 0.687 | 0.687 (14 Mar, 30 Nov) | 0 |
| `A0_113699_ss90_to_A1` | 4 | 0.916 | 0.916 (14 Mar, 30 Nov) | 0 |
| `A0_106039_ss90_to_A1` | 9 | 2.061 | 2.061 (27 Nov) | 0 |
| `A1_106039_ss90_to_A0` | 8 | 1.832 | 1.832 (27 Nov) | +0.2990796581 |

The source PyPSA energy model uses a cyclic battery Store and DC-coupled inverter/charger/discharger, with `battery_soc_usable_kwh` extracted from `stores_t.e`. Consequently an isolated extra nighttime battery injection without checking existing store energy, charging opportunity, device P limits, the required manufacturer 20% SOC rule and *annual SOC closure* cannot be called a valid corrected dispatch. Earlier 113699 SOC-corrected model passes cannot be substituted for these original P schedules: original 113699 A0-origin minimum-cost reciprocal differs in 188 inverter-P hours from its previously archived corrected counterpart. A pilot constrained to the failed nights is a diagnostic but is not sufficient to establish annual curtailment/economics impact.

### Digital provenance / line-endings

The saved manifest claims `TARGETED_36_AC_CASEHOURS.csv` SHA-256 **b7ac735ec3dce405044292a6a8e56c2e0ccd952be71f949284b532f51da7a6cc** (the local Windows CRLF CSV). GitLab's uploaded repository blob is normalized to **LF** and GitLab separately reports SHA-256 **c18dc2cab74a83f7d054e50cdc250ecb5e73f8294da2b88d4a0a00be7d988bf8**, size 15107 bytes. Independently SHA-256 hashing the GitLab LF text reproduces c18dc..., then converting only line endings back to CRLF reproduces b7ac..., **exactly matching the manifest**. This is an expected Git end-of-line normalization, not a data mismatch. Figure hashes independently confirmed against GitLab file metadata: `figures_diagnostic/min_voltage.png` = `1a54e20e2b3ef004020cc3ebfdf5a2335a37c983bccd40af3edcb4ea4c168e06`; `figures_diagnostic/trafo_loading.png` = `1cac8c56bac352ccb9383984b90efad8acff349548d6e482e8fd3bb093eba840`.

## Decision-ready next steps, not yet performed

1. **Do not rerun** the 36-case v1 pilot, 12-case 105120h materiality source producer, the previously audited A0 106039 36/702 replay or broad matched annual simulations. Local untracked `StudyA_Reciprocal12_P1_AC_Pilot_v2/` exists per user's earlier git status but has **NOT been uploaded or inspected**; preserve it unmodified until needed.
2. First build a **source-only SOC/dispatch correction feasibility gate** on the exact failed timestamps with prior and following battery energy, discharge/charge power, inverter efficiency and PV surplus/curtailment. Distinguish available mathematical `Store` energy from manufacturer's genuine physical minimum SOC. If additional energy must be shifted to these evenings, identify the earlier hours and the cyclic-year balance, then only run a controlled same-hardware chronological correction if it changes Study A's decision.
3. **94022 A0**: prioritize physically valid night undervoltage mitigation and verified H01/H06 routes; existing five-edge resistance-halving is a hypothetical alternative, not a real installed fix. **113699 A1**: investigate the assumed 3 kVA nameplate and PF .95 event pairs; earlier corrected 8760-hour PF .98 pass does not certify these original reciprocal schedules. **106039**: check actual 5 kVA nameplate and precisely correct 27 Nov thermal exceedances with signed SOC constraints.
4. Retain 0.95–1.05 pu/100% assumed limits as research main screen, 0.97–1.03 pu optional strict band, PF .98 reference and .95/1.00 robustness, and balanced GIS provisional network. No whole-year EPM field or loss-adjusted economic claim follows from 36 selected hour screens. 85398 A1 two unmatched P2 cases, 94022 A1 two P2, and 113699 A0 two P3 remain to be addressed for overall Study A completeness. Keep northern 137468 excluded and 92395 STAR/MST explicitly hypothetical.

**Audit result:** signed source-hour and model-output consistency PASS, 20/36 model-limit violations REAL in this specific fixed-P/Q sampled research model; annual/field feasibility UNDETERMINED. Test console output for nine reciprocal source and ten new P1 synthetic tests was not provided to reviewer, so no user-local test PASS is claimed here.
