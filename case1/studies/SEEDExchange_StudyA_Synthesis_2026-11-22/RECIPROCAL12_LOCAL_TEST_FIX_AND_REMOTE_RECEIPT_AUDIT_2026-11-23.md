# Study A | reciprocal-12 failing local test and archived source receipt audit

Date: 23 November 2026. Branch: `sync/seedexchange-local-2026-11-17`. Pre-fix uploaded output commit: `023f2b729ed7fb4448b49cb5364be2d798321fd7`.

## Finding: wrong hourly demand in synthetic test

The user's nine synthetic `test_matched16_reciprocal12_materiality.py` tests had one reported failure: `test_night_pf_095_proxy`. The original test passed `nighttime_proxy(4.887809301, 5.7703076217, .95)` but expected `5.1765998799` kVA. This produced `5.242881190284905` kVA, an error of `0.06628131038490448` kVA versus the asserted output.

The archived source target `A1_106039_ss90_to_A0` at **2025-11-27 20:00:00 LST** instead contains simultaneous `grid_import_kw=4.887809301`, `gross_demand_kw=5.186888959`, `inverter_ac_kw=0.2990796581`, `pv_dc_available_kw=0`. The accidental `5.7703076217` is the **annual maximum gross demand** shown in the materiality register, not gross demand during that hour. The nighttime proxy `hypot(grid_import, gross_demand*tan(acos(PF)))` at PF .95 equals `5.176599879895537` kVA with the correct time-matched inputs. The opposite `A0_106039_ss90_to_A1` case at the same timestamp uses `grid_import_kw=gross_demand_kw=4.8438874007` and produces `5.098828842842106` kVA.

**Change made:** only the erroneous synthetic fixture test uses the correct hourly demand, and the same test now also covers the opposite 106039 SS90 source peak in subtests. The `nighttime_proxy` production function, all source energy CSVs, all existing signed result folders, PF assumptions and grid/AC solvers are unchanged. The test file still has nine tests. The expected two PF .95 source-proxy exceedances remain valid model-only flags, not solved AC failures.

## Independent remote receipt review

The versioned `StudyA_Reciprocal12_Source_Materiality_v1` folder is already on GitLab at the above commit and includes `RUN_MANIFEST.json`, `UNMATCHED12_SOURCE_MATERIALITY.csv` and `TARGETED_25H_HOUR_SELECTION.csv`. Read-only independent CSV parsing verified:

- 12 unmatched case records; 8,760 source hours each are reported in the register, for 105,120 signed source-case hours in its manifest.
- 300 selected case-hours, **25 unique timestamps per case** across 12 cases.
- Priority register: P1=6, P2=4, P3=2.
- Recomputed PF .95 nighttime proxy for each nighttime row in the selected-case-hour CSV using recorded import and simultaneous gross load; maximum absolute difference versus source selection CSV approximately `8.9e-16` kVA.
- Exactly two selected PF .95 source apparent-power proxy values above the assumed nameplate, one per 106039 SS90 reciprocal case at 2025-11-27 20:00:00.
- Manifest declares `AC_solver_calls=0`, `SOC_corrected_AC_reuse_certified_hours=0`, `actual_EPM_feeder_verified=false`.

This remote audit checks present output structure and recomputed selected-hour arithmetic. It **does not substitute for** the user's local rerun of the fixed nine-test suite or re-verify all 12 original 8,760-hour source SHA signatures from a fresh local checkout. Do not claim a nine-test pass from the original failure.

## Immediate action and next research gate

1. Pull the existing sync branch without resetting/cleaning or touching `main`. Rerun only the nine synthetic source materiality tests. Also rerun the nine previously repaired A0 106039 P/Q regression tests if their PASS has not yet been confirmed. No AC solve is needed.
2. Check existing output `StudyA_Reciprocal12_Source_Materiality_v1/RUN_MANIFEST.json`. It has already been committed, so **do not rerun source screening or commit a duplicate v2 merely because the test was fixed**.
3. Next choose **bounded, decision-changing AC source-hour experiments**, first auditing whether the saved 94022/113699 proposed network connection, native P/Q source runner and 106039 SS90 case-hour signatures permit exact replay. The 300 source-selected rows are diagnostic targets, not annual physical passes/failures. Do not start a new 12x9x8760 AC sweep automatically. Before engineering conclusions, request EPM transformer nameplates, line/service routing, phases and permissions.

Standing Study A rulings: PF 0.98 base, .95 and 1.00 sensitivities; 106039 modelling assumption 5 kVA; main voltage 0.95–1.05 pu with strict 0.97–1.03 sensitivity; minimum battery SOC 20%; use full chronological annual AC and legitimate P/Q redispatch for final design decisions; exclude northern 25-kVA transformer 137468; keep original results immutable and do not modify main.
