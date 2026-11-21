# Independent audit | full 27-case new hardware annual AC | 21 November 2026

**Verdict:** Pass for full 27-case source-stitched annual AC under Study A1 106039 provisional balanced model, assumed 5 kVA transformer. GitLab user result `b2fdfe6b13c5077b3ac6d2131042b8697e1c5ace`, source `StudyA_A1_106039_NewHardware_Reserve_AnnualAC_Full_v1/`.

## Checks performed on actual uploaded GitLab content

1. Parsed complete `RUN_MANIFEST.json` and `ANNUAL_AC_PAIRED_SUMMARY.csv`. Confirmed scope=`full`, status=`SOURCE_STITCHED_ANNUAL_AC_ALL_CASES_PASS`, modelled/complete 27/27 factor cases, nine factors per each of MC_B10, SS_B10, SS_P45_B9, 8,760 converged hours and 0 main-screen failures per factor. Expected/actual original new hour counts equal at 9,256; expected/actual corrected replays equal at 72. Original B9 signed nine-factor source count recorded 18; 27 source combinations preflighted.
2. Fetched **all 27 case receipts**, each matching its full manifest case object exactly.
3. Fetched and parsed **all 27 per-factor AC delta CSVs**. Reconciled 1,272 original + 36 corrected rows for MC_B10; 2,136 original + 18 corrected for SS_B10; 5,848 original + 18 corrected for SS_P45_B9. **9,328 total saved newly solved AC delta rows**. Every file has correct recorded original/candidate phase counts and no duplicated timestamp/phase keys. All saved rows report `CONVERGED`.
4. Independently cross-matched all **72 corrected rows** with the original user-pushed `StudyA_A1_106039_NewHardware_Reserve_NineFactor_v1/ALL_NINE_CHANGED_HOUR_AC.csv` using case, factor, date, phase. Compared `inverter_ac_kw`, min/max voltage, transformer percent, line percent, losses and PCC kVA; all differences within **2e-7** at the CSV saved precision. Zero corrected-hour feasibility flags disagreed.
5. The full manifest's corrected 27/27 annual summaries yield **236,520** converged annual case-hours, 0 main-screen failures; worst transformer 99.4318148586%; worst min voltage 0.9572396590 pu. The strict 0.97/1.03 pu failure counts sum to **638 factor-case-hours across the 27 combinations**, not 638 unique timestamps or customers. The original PF .95 x1.6 AC annual file for each new case is reused from its **own** historical 8760h stress archive, not another hardware reference.
6. Matched source hour accounting: `MC_B10` 8×159=1272 original mismatch replays; `SS_B10` 8×267=2136; `SS_P45_B9` 8×731=5848. Total 9256 newly solved original hours, 227264 reused original hours. Reuse depends on exact recorded original inverter AC power, inverter kVA, PV Q-enable state, matching household trace and PF/length geometry. The solver's 72 independent matching-input control replays add further numerical evidence.
7. This audit did not rerun pandapower or independently recalculate all 236,520 annual electrical states. SHA-256 values and signed sources remain recorded in the machine-readable manifests; the review primarily independently verifies the remote file identities, per-file numerical records, replay agreement and resulting summary cross-consistency.

## What the results do not demonstrate

- These are balanced, provisional modelled AC results, not verified unbalanced service phases, protection, neutral capacity or a utility-approved line layout.
- The rated 5 kVA 106039 transformer and feeder/service paths are still model assumptions. Worst 0.568185 percentage points loading headroom cannot support a robust installation claim without field evidence and additional uncertainty controls.
- The stricter 0.97 to 1.03 pu sensitivity does not pass and must be reported, even when the main 0.95 to 1.05 pu research band passes.
- An energy-only design not included in this six-case validated comparison has not received this complete AC certification.
- The annualized equipment costs and $0.29/kWh grid purchases are archived research assumptions, not all-in local capital quotation or a present retail tariff determination.

## Decision

Study A1 106039 additional-hardware corrected annual AC exploration is complete for the six compared portfolios. Next task: common-population A0/A1 energy and network economics, with source evidence gates before new numerical work. Keep historical source files and `main` unchanged.
