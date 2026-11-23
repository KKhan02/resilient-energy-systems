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

The new `matched16_original_ac_input_preflight.py` is a fail-closed, **read-only** annual source checker with 17 synthetic tests. It authenticates all 16 target source energy CSVs, checks 2025 timestamps, and compares gross demand, inverter AC power, daylight/Q policy and source AC metadata for the two 106039 min-cost target-native equipment matches at the reference PF .98 and service multiplier x1.0. It does not certify corrected schedules or field networks, and never runs a solver. See `MATCHED16_ORIGINAL_AC_INPUT_RUN_LOCAL_2026-11-22.md` for precise Miniforge commands and output receipt constraints. The user executed this first read-only input preflight and pushed the signed v1 result package at commit `54b4f66d`; the files and their Windows CRLF/Git LF SHA correspondence were independently checked on 23 November. The assistant did not execute a new AC power-flow solve.

## Windows long-path source reader correction

A local full preflight reached a GitLab-existing A1 106039 original AC summary whose absolute Windows path measures exactly 260 characters. The signed read-only reader now uses extended Windows path syntax for JSON, CSV and binary checksum reads, preserving fail-closed missing-file and immutable source-SHA checks. Four new regression tests cover long drive paths, UNC paths, prefix idempotence, relative source rejection and genuinely missing files. No AC or LP results were changed.

## Extended 22-family source search, 22 November

After the user's reported 16/16 local first-stage preflight, an independent read-only GitLab scan of all 22 source equipment families identified **two additional 85398 exact original-hardware/energy-schedule matches**. Both corresponding 8,760-hour original PF .98 AC input streams match their source energy P/gross demand/daylight fields and their recorded original AC screens have zero infeasible hours. Thus 4/16 reciprocal fixed-hardware cases have identified *original-source candidate* records across the 22 families, rather than just 2/16 target-native same-tier matches. **0/16 are certified for SOC-corrected AC reuse**, and the user's new local v1 receipt has not yet been pushed. See `MATCHED16_ALL_ARCHIVE_FAMILY_DISCOVERY_2026-11-22.md` and its source-family CSV. No plot is warranted for this source-integrity audit.

## Four-family AC source and SOC-shift source gate, 23 November 2026

The uploaded original-source v1 receipt is now independently audited. The extended 22-family review found four exact original 2025 equipment/source input matches. For the original 106039 minimum-cost optimized sources, archived SOC shifts modify 39 A0 or four A1 active-power hours with 351 or 36 saved nine-factor changed-hour AC checks. The A0 compact AC report omits changed-hour P/Q inputs, a separate verification limitation. Both 85398 reference matches are original, uncorrected schedules. A new fail-closed `matched16_four_family_input_gate.py` and eight synthetic tests are ready for **user-local** source-only validation; see `MATCHED16_FOUR_FAMILY_SOCSHIFT_GATE_RUN_LOCAL_2026-11-23.md`, `MATCHED16_SOURCE_AND_SOCSHIFT_INDEPENDENT_REVIEW_2026-11-23.md` and its 4-case CSV. The new v2 gate has not yet run locally. Corrected-AC reuse remains uncertified and there are no new power-flow solves.
