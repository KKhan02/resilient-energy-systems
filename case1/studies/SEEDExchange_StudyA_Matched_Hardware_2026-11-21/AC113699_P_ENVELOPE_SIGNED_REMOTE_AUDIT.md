# Study A | Independent signed A1 113699 nighttime P-envelope audit

**Reviewed 21 November 2026.** User result at GitLab commit 00a11b1c2a948360701744189bb2657c7a77f613. Signed data in StudyA_A0_A1_MatchedHardware_AC113699_P_Envelope_v1. This is a **bounded hypothetical static AC test**, not chronological SOC proof or complete annual AC certification.

## Source reproducibility

- Full previous A0/A1 energy and 150-hour pilot provenance was pinned by the producer and is still unchanged. The first 113699 pilot had 150/150 converged AC samples, ten failed scenario-hours from overloaded assumed 3 kVA transformer.
- Sweep manifest status: SAMPLED_AC_P_CANDIDATES_FOUND_SOC_AND_ANNUAL_PENDING; 123/123 power-flow samples converged; 0 unresolved source cases; annual_AC_feasible=false, SOC_schedule_changed=false, hardware_changed=false.
- GitLab LF CSV SHA-256 f2191b13105fcd888591c75617be29b267ae9f5cdb23ffbbb96e85a6a4c13c4e; source manifest records original local Windows CRLF SHA-256 8c400fdf5bc011a5ff838ae1b05f2426a70abd8fc84cd682c7a9d94fdcfadbb0. Producer's original-file verification and named-lineage checks passed, the GitLab LF hash is separate from Windows representation. CSV has 123 unique case-hour-sample keys, 3 case-hours x 41 P points; all saved JSON counts, statuses, first-feasible P and time provenance independently recalculated from CSV with no mismatches.
- Plot binary checksums exactly agree with signed manifest: sampled_transformer_vs_P.png 08fbcd5d63828b2adb14f4ad27c1896f927d5a06f163ca790968e04582128fb5; sampled_voltage_vs_P.png da1e5e292065b508476602bb9cfbaf8c9aefdfe43b9725e466600a184bf43738.
- Every sample uses A1 six-house source territory, assumed transformer 3 kVA, PF .98, service multiplier 1.0, Q=0 at night. Original P=0 AC failures reproduced at each exact timestamp. No apparent-power line overload and no nonconvergent sample. The experimental inverter P is hypothetical, and the original full-year battery SOC is *unchanged*.

## Verified samples

| Original frozen hardware on A1 | 2025 failed timestamp | Feasible AC samples | Smallest passing sampled P | P index3 kW | Transformer loading at index3 | Lowest voltage index3 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| A0 17PV/3B/5kVA | 14 Mar 19:00 | 40/41 | .0704995 kW | .2114984 | 93.933% | .953465 pu |
| A0 17PV/3B/5kVA | 30 Nov 20:00 | 40/41 | .0700763 kW | .2102288 | 93.403% | .952963 pu |
| A1 20PV/4B/6kVA | 30 Nov 20:00 | 40/41 | .0700763 kW | .2102288 | 93.403% | .952963 pu |

At P=0 the three hardware-hour cases fail transformer loading at 101.0974%, 100.5227%, 100.5227%; original inverter P zero and source battery SOC exactly physical 20% floor. First P>0 sampled points fix the **0.95..1.05 pu plus <=100% loading** model screen. P index3 offers a sampled transformer loading around 93.4..93.9%, reducing sensitivity to narrow near-limit AC point without requiring a large nightly P. This is a controlled next LP equality-target candidate, not an optimized reserve rule.

**Important strict .97 pu voltage caveat:** At 30 Nov 20:00 even the highest no-export P sample, 2.803051kW, leaves minimum household voltage .969546pu, below the optional strict 0.97pu screen. At 14 Mar the maximum allowed no-export P sample 2.819979kW reaches .970140pu. Thus the strict 0.97 criterion **cannot be satisfied in the saved November P-only sweep even at maximum P**. The main 0.95 screen passes many points, but claiming strict 0.97 feasibility or field compliance would be incorrect. This may require separate geometric/inverter-Q assumptions or an approved redesign, not a small P shift.

## Next stage

Prepare a source-verified full-2025 **fixed-hardware, cyclic-SOC PyPSA** constrained-dispatch experiment for the TWO origin hardware sets on A1. Enforce at each failed hour the exact 3rd sampled (index3) AC-feasible inverter P **as equality** with original frozen PV, BESS power, inverter kVA, transformer planning 3 kVA, PF .98, zero export/ENS, existing manufacturer 20% physical SOC floor, and existing battery + inverter losses. Verify before solver that each original P=0 source and selected positive P sample match the archived 123-row sweep.

Run a distinct 8,760-hour LP for A0-origin on A1 with 14 Mar and 30 Nov fixed P, and A1-origin on A1 with 30 Nov fixed P. This tests annual SOC feasibility without increasing equipment. After each solve, recheck battery SOC chronologically and independent AC at all 15 original pilot stress hours for that hardware. Any new failure is retained, not hidden; all untested annual hours remain AC pending. Compare original annual energy-only objective with corrected-dispatch economic cost on exactly the same equipment and 2025 demand. Do not infer annual feeder loss from 15 samples. Export per-case 8760-hour CSV, source hashes, summary, actual sampled AC, diagnostic figures and changed-hour count. Follow-up annual 8760h AC replay for BOTH corrected dispatches is needed before assignment-based AC conclusions; wider PF/length sensitivities are subsequent gates.

**Scope:** This paper model uses perfect foresight, assumed LV geometry and nameplate, and idealized head-connected inverter. Strict .97 voltage, utility-approved LV service, installed equipment topology and hardware current sharing are not field verified.
