# Study A: A1 transformer 106039 SOC-aware dispatch trial, independent review

**Date:** 16 November 2026. **Scope:** 11 houses in A1, transformer 106039, assumed 5 kVA, two archived equipment reference tiers, optimized annual dispatch only. All input source files and numerical runs preserved. No GitLab writes.

## Headline result

The user-supplied local trial `trial_manifest.json`, both candidate annual 8,760-hour CSVs, `candidate_shifts.csv`, 108 changed-hour AC records and all 18 sensitivity summaries agree. Independent read-only audit: **34 checks passed**. Each of the 18 annual sensitivity conditions (2 equipment tiers × 3 PF × 3 service-length factors) reports **zero violations** after the modified hours were independently solved in pandapower and the remaining signed historical hours were reused. All 108 AC evaluations converged, including 54 candidate changed-hour evaluations. This is **not** a fresh full-year PyPSA optimization, not a new inverter control implementation, and not a full re-solve of 18 × 8,760 AC points.

The manual shifts are:

| Tier | Original hour | New target hour | DC battery discharge shifted | Extra target AC output |
|---|---|---|---:|---:|
| Minimum cost | 13 Oct 2025 17:00 | 13 Oct 20:00 | 0.60 kW | 0.57 kW |
| Minimum cost | 27 Nov 2025 18:00 | 27 Nov 20:00 | 0.80 kW | 0.76 kW |
| Higher SS | 27 Nov 2025 18:00 | 27 Nov 20:00 | 0.80 kW | 0.76 kW |

Both 8,760-hour files pass chronological, SOC 20% physical-floor, hourly and cyclic SOC closure, DC/AC coupling, PV curtailment arithmetic, device power rating, zero-export, zero-ENS and original annual-grid-import consistency checks. Initial and final yearly SOC unchanged. Annual modelled grid imports and PV curtailment unchanged. No extra equipment purchased. Grid AC losses change by roughly 0.024–0.030 kWh across the repaired hours for each annual case, so any loss-aware annual economics must be separately calculated rather than asserted identical.

### AC results

| PF | Service factor | Baseline minimum-cost violations | Baseline higher-SS violations | Corrected violations, each tier | Highest corrected yearly transformer loading |
|---:|---:|---:|---:|---:|---:|
| 0.95 | ×1.0 | 2 | 1 | 0 | 99.35% |
| 0.95 | ×1.3 | 2 | 1 | 0 | 99.39% |
| 0.95 | ×1.6 | 2 | 1 | 0 | 99.43% |
| 0.98 | ×1.0 | 1 | 1 | 0 | 95.82% |
| 0.98 | ×1.3 | 1 | 1 | 0 | 95.86% |
| 0.98 | ×1.6 | 1 | 1 | 0 | 95.90% |
| 1.00 | ×1.0 | 1 | 1 | 0 | 93.04% |
| 1.00 | ×1.3 | 1 | 1 | 0 | 93.07% |
| 1.00 | ×1.6 | 1 | 1 | 0 | 93.11% |

The lowest yearly corrected voltage is 0.95724 pu. The remaining PF0.95 ×1.6 thermal margin is only **0.57 percentage points**; this is a model-sensitivity pass, not field-certification. Inverter nighttime reactive power remains disabled. The assumed 106039 transformer capacity is unconfirmed as a physical nameplate.

## Portfolio correction, do not overwrite source

Merge the new trial as a **separate analysis overlay** onto the previously audited 432 annual AC results, matching A1 / 106039 / archived-reference / mapped / optimized / equipment tier / PF / length. Preserve original signed CSV and manifest files. Exactly 18 rows acquire corrected AC metrics; original 432 are unchanged.

- Before trial: 144 of 432 annual AC sensitivity configurations had one or more violations.
- After overlay: 126 of 432 remain violating, covering 20 distinct network/hardware/dispatch groups, not 126 independent equipment designs.
- At baseline PF0.98 ×1.0, for A1 and the selected five-territory STAR architecture: higher-SS **optimized** portfolio drops from 1 to **0** summed territory violation-hours; minimum-cost optimized from 2 to **1**, remaining at 113699. These are modeled distinct territory-hours, not site-certified systems.
- At PF0.95 ×1.6, A1 higher-SS optimized STAR retains 1 violation-hour at 94022; A1 min-cost optimized STAR retains 7 at 113699 and 94022. These tallies use four mapped territories plus the already nonviolating 92395 STAR model, no actual 92395 line GIS.
- The A1 106039 **causal** modes were *not corrected*. Other major bottlenecks are A0 92395 proposed MST undervoltage, A0 94022 low voltage, and A0 106039 overload. Neither extra PV panels nor a blind AC shift is guaranteed to fix those network problems.

## Curtailment still present

At A1/106039, both candidate schedules retain the original PV energy and curtailment. Minimum-cost PV DC available 21,657.24 kWh, curtailed 2,443.60 kWh (11.28%); higher-SS available 25,883.05 kWh, curtailed 5,492.23 kWh (21.22%). The trial **moves battery discharge** and does not optimize charging, PV sizing, battery storage or curtailment.

## Next evidence-led action

Before building any general correction, use the separately included read-only `extract_remaining_events_and_pv.py` locally. It examines the 126 remaining signed failing AC scenario files, extracts exact violation timestamps joined to matching annual optimized/causal SOC, and produces one PV-curtailment diagnostic table for each distinct source dispatch. It does **not** execute AC models, overwrite results or claim causality from coincident SOC and curtailment flags.

After reviewing that evidence, separate repair strategies into (a) active-power redispatch when stored energy and network slack exist, (b) voltage/route/conductor/transformer remediation where shifting demand cannot help, and (c) PV+BESS hardware and control optimization for cost/SS/curtailment frontiers. Generalize corrections to A0, A1 and causal dispatch as supported, with the nine sensitivity cases and later resilience reserve requirements kept explicit.

## Evidence limits

The independent auditor confirms uploaded candidate CSV arithmetic and the internal agreement of local changed-hour AC outputs. It does not have the complete original signed 432 hourly source files to independently reproduce all unchanged 8,760-hour AC points, nor physical EPM commissioning measurements. The source trial runner reports checked SHA-256 historical references and baseline re-solves for modified hours. Recompute AC on the Windows workstation if those original source signatures change.
