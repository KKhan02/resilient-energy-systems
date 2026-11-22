# Study A synthesis | 22 November 2026

Source-linked decision preparation for the original versus nearest A0/A1 existing-network Study A. This folder does not replace signed original case results or propose a new transformer assignment.

- [Synthesis and next decision gates](STUDY_A_EVIDENCE_AND_NEXT_DECISIONS.md)
- [Machine-readable five-territory evidence matrix](FIVE_TERRITORY_EVIDENCE_GATES.csv)
- [Professor walkthrough Stage 15](../../professor_walkthrough/15_Matched_Hardware_and_AC_Robustness/)

Next step: use the matrix to produce a single comparison of validated versus conditional 2025 model results, and collect actual EPM transformer/line/service evidence before deciding which additional full-year AC scenarios can alter A0/A1 recommendations. Preserve studies B and C as separately approved workstreams.

## Verified 34-house source reconciliation (22 November)

The new `STUDY_A_34HOUSE_NUMERICAL_RECONCILIATION_2026-11-22.md` independently cross-matches 72 aligned A0/A1 architecture-specific source selections to all their 360 individual source case IDs in the 432-case annual AC overlay. A0 original-network residual AC violations after saved SOC correction occur only in 94022; every A1 source selection has zero main-band residual violations under its own equipment and provisional topology. The 72/72 zero-residual conditional A0 five-edge overlay is not a real network approval. The 16 reciprocal same-hardware annual energy controls are **not** 72 verified matched-hardware AC runs.

A compact `STUDY_A_34HOUSE_DECISION_SCORECARD_2026-11-22.csv` retains source-specific sizes, imports, PV curtailment, model cost and evidence labels. New poster-candidate Stage 14 figure is source-specific and energy-only.

## Exact original-AC input preflight, 22 November 2026

The new `matched16_original_ac_input_preflight.py` is a fail-closed, **read-only** annual source checker with eleven synthetic tests. It authenticates all 16 target source energy CSVs, checks 2025 timestamps, and compares gross demand, inverter AC power, daylight/Q policy and source AC metadata for the two 106039 min-cost target-native equipment matches at the reference PF .98 and service multiplier x1.0. It does not certify corrected schedules or field networks, and never runs a solver. See `MATCHED16_ORIGINAL_AC_INPUT_RUN_LOCAL_2026-11-22.md` for precise Miniforge commands and output receipt constraints. This preflight has been prepared in GitLab, **not executed by the assistant on the local repository**.

## Windows long-path source reader correction

A local full preflight reached a GitLab-existing A1 106039 original AC summary whose absolute Windows path measures exactly 260 characters. The signed read-only reader now uses extended Windows path syntax for JSON, CSV and binary checksum reads, preserving fail-closed missing-file and immutable source-SHA checks. Four new regression tests cover long drive paths, UNC paths, prefix idempotence, relative source rejection and genuinely missing files. No AC or LP results were changed.
