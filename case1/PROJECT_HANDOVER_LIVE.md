# SEEDExchange El Arenal / San Rafael: rolling research handover

**Last audit: 6 November 2026. Selection and executable validation routing prepared.**
**Canonical project:** https://gitlab.com/KKhan02/resilient-energy-systems (private, GitLab.com), main.
**Verified pre-handover HEAD:** bfc95c1b60ee.
**Original public collaboration repository (separate):** https://gitlab.gwdg.de/open-energy-modelling/energy-community. Direct GWDG access failed during this audit. Do not assume it matches the private GitLab.com research repository.
**Purpose:** Enable exact continuation after context limits. This is a living technical record, not final design certification.

## 0. Instructions for every future assistant turn

Read this file first, then check the live GitLab HEAD and relevant output manifests. **After every substantive reply**, revise this SAME file with decisions, completed actions, results, failures, uncertainties, and next steps. Commit documentation changes with [ci skip] and retain an exportable Markdown copy. Do not recreate a new handover filename. Mark reported, source-verified, planned, running and unverified results distinctly. Preserve all historical numerical results and test evidence. Do not change new topology, equipment ratings, cost assumptions, models or tariffs without discussing substantive design choices with the user. Do not start a new historical optimization sweep simply to reproduce saved outputs.

## 1. Project purpose and boundary

**Overriding study-design decision:** The entire 5-to-15-household sweep, including both 8-house synthetic cases, is the **primary design space regardless of where households ultimately connect**. The existing EPM GIS network and proposed new LV feeder are **two parallel electrical comparison scenarios** using archived equipment designs. The proposed-feeder topology is a gate only for AC validation of that specific new feeder; it must not block archived frontier analysis, fixed-hardware dispatch preparation, or continued existing-EPM AC checks. The main study is not restricted to current EPM transformer territories.


Research a shared, grid-connected community PV+BESS energy system for El Arenal, San Rafael, Antioquia, Colombia. Compare investment cost, 8,760-hour energy self-sufficiency and physical grid capability, accounting for transformer kVA, LV voltage, conductor ampacity, losses and battery SOC. Keep two distinct network questions:

1. **Existing EPM GIS network:** Mapped transformer/node/conductor data with inferred customer service attachments and phase assumptions. These are provisional but physically informed.
2. **Proposed new community LV network:** A new defined 5–15-household group and supply point. It does NOT automatically share existing EPM transformer territories. Transformer 5 kVA is a provisional hypothesis only.

The original September hackathon supplied community framing, HOMER comparison, initial PyPSA/PV+BESS and outage analysis, spatial groupings, governance and household billing. These remain historical background. 35 mapped candidate properties are available, but they are NOT 35 verified service-to-transformer assignments.

The primary investment engine is PyPSA/Linopy, with a perfect-foresight annual energy chronology. Independent pandapower AC checks test network physics. Energy-only optimality or PCC kVA screening does not imply AC feeder feasibility. Perfect foresight is a planning benchmark, NOT MPC or realistic online forecasts.

## 2. Live GitLab findings, verified 6 November 2026

| Research result | Verified numerical status | Source |
|---|---|---|
| Historical investment campaign | 6,840 annual PyPSA/Linopy tasks, 6,820 energy-optimal, 20 infeasible; 12 household configurations spanning 5–15 households including 8-house H01 and H02 synthetic variants, with five assumed transformer ratings | studies/pypsa_joint_optimization_v1/outputs/full_study/complete_study_results.csv and study_manifest.json |
| Full-campaign reuse index | 6,339 distinct fixed-hardware combinations; 1,584 GIS-mapped energy-only; 1,214 assigned to new SOC+AC work; 5,125 unmapped or equipment-review cases. This is a queue, NOT 1,214 AC passes | studies/ac_aware_redispatch_v1/outputs/campaign_reuse_index_v18_01/campaign_reuse_manifest.json |
| 7-house EPM 94022 | 26 × 435 W panels, 5 battery modules, 7.6 kVA inverter; with 20% physical min SOC and full-year active-P feedback: 8,760/8,760 independently checked 0.97–1.03 pu strict research passes; min 0.9700987 pu, max trafo 58.5846%, modeled losses 367.15 kWh. Earlier manufacturer SOC baseline had four strict-band failures but passed 0.95–1.05 pu | studies/ac_aware_redispatch_v1/outputs/seven_annual_feedback_ac_check_01/annual_ac_summary.json |
| 12-house EPM 106039 | 41 panels, 8 modules, 12 kVA inverter; 20% SOC manufacturer baseline, night Q off, 8,760/8,760 AC passes at 0.95–1.05 pu; min 0.955651 pu, max trafo 94.4387%, modeled AC losses 456.31 kWh. **5 kVA is a hypothetical nameplate for 106039, not verified by EPM** | studies/ac_aware_redispatch_v1/outputs/twelve_ac_full_02/annual_ac_summary.json |
| Manufacturer SOC economic adjustment | Seven-house energy-only $2,772.94/y -> $2,810.01/y with SOC floor; twelve-house $4,767.83/y -> $4,820.76/y. Seven-house AC feedback adds $0/y against its manufacturer baseline. These are modeled costs excluding certified EPM tariff and full feeder/site expense | professor_walkthrough/RESEARCH_NARRATIVE.md |
| Existing robustness | Seven-house PF 0.90, service factor 1.6 fixed-operation 8,760-hour stress still passes 0.95–1.05 pu, but 111 hours fail the old 0.97 pu floor. Twelve-house PF/service stress covered 96 critical hours per scenario, NOT 8,760 per scenario. Worst 0.94411 pu and 106.86% trafo loading | studies/ac_aware_redispatch_v1/outputs/seven_robustness_worst_full_01/ and twelve_robustness_critical_01/ |
| Campaign partial annual AC | Four EC-* candidate output folders under studies/ac_aware_redispatch_v1/outputs/campaign_AC_01; some AC scenarios saved, some reuse prior checks. Do not treat the partial set as a completed AC-feasible frontier or 1,214 validated cases | studies/ac_aware_redispatch_v1/outputs/campaign_AC_01/ |
| 5-kVA archived 5–15 household frontier | 1,348 optimal 5-kVA task rows, 1,255 distinct hardware combinations; 452 sampled nondominated task rows, 387 nondominated equipment combinations, 50 deduplicated initial economic/SS anchors, 296 exact fixed-PV hardware-switch boundary configurations. **Energy-only, no new AC for these 50** | studies/household_frontier_reuse_v1/README.md and outputs/frontier_source_manifest.json |
| Minimum-cost transitions | Five houses: 17 panels / 3 batteries / 5 kVA inverter, $1,991.78/y. Fifteen houses: 67/11/20 kVA, $6,133.19/y. Nine to ten houses stay 34/6/10; eleven to fourteen stay 41/8/12. Annual cost increases despite identical hardware across some neighboring populations | studies/household_frontier_reuse_v1/README.md |
| Professor review | 24 figures curated in 11 numbered stages and a source-linked research narrative, including full-year AC feedback and remaining conditionality | professor_walkthrough/README.md, RESEARCH_NARRATIVE.md, FIGURE_INDEX.csv |
| ZIP relocation | 12 historical WP1 versioned/patch ZIPs relocated from root to research_archive/versioned_wp1_packages/; exact former paths indexed. Python, tests and outputs left active | research_archive/RELOCATION_INDEX.csv, commits 92239bd8 / 8184fb0b / bfc95c1b |

**All paths in this handover are relative to the case1/ folder unless specified otherwise.** Source results are from GitLab read-only audits, not freshly executed solvers. The old case1/wp1_v3 heuristic, legacy independent Case 1 and source PyPSA v18 / pandapower v5 notebooks are separate historical studies. Avoid silently mixing figures or stale stage-specific README status with newer output manifests.

## 3. Latest engineering decisions

- Include every 5–15 house count and preserve the two 8-house synthetic variants, not an arbitrary six-design subset.
- Principal load PF scenarios: **0.95, 0.98 and 1.00**. PF 0.90 is an *optional* inductive stress assumption, not required of all final equipment.
- Distinguish existing EPM GIS connections from a **proposed new** community network. Do not relocate or duplicate mapped houses by accounting alone.
- Proposed new transformer **5 kVA** is an initial planning sensitivity. Only revisit based on demonstrated hourly voltage/thermal need and documented location/nameplate choices; do not presume it serves all 15 homes.
- Principal proposed engineering voltage band **0.95–1.05 pu**. Preserve **0.97–1.03 pu** as old strict research sensitivity, not official regulation. All AC results remain conditional balanced-feeder proxies.
- Enforce Deye manufacturer **20% physical min SOC** for new studies, hour-to-hour chronology, feasible BESS charge/discharge and inverter AC kVA. Treat nighttime Q support as **off** until manufacturer proof.
- Use original 70/80/90/95% self-sufficiency targets, minimum cost and maximum self-sufficiency for Stage A (50 equipment anchors); remaining nondominated points Stage B, exact transition-boundary designs Stage C (296) and complete archive Stage D. AC candidate expansion should be guided by actual pass/fail and hardware transitions.
- Keep full original 6,840-task investment results, the 35-property spatial evidence, existing source paths, historical figures and tests intact. New network topologies must be labelled hypothetical until real design inputs exist.
- Use manufacturer battery/current, inverter-string and PV constraints before procurement recommendation. Original economic model omits full site cost, physical feeder losses, actual EPM tariff, verified service reconnection cost and some hardware cost increments.

## 4. Unfinished work, organized by dependency (parallel tracks)

**Execution order clarified 6 Nov:** Advance (A) proposed feeder topology specification, (B) 5-to-15-house equipment candidate preparation and manufacturer-SOC annual dispatch, and (C) reuse/reconciliation of existing EPM GIS annual AC evidence **in parallel**. New-feeder AC must wait for A, but neither B nor existing-EPM work must wait for A. The selection does not impose an arbitrary cap: 50 first economic anchors, then sampled nondominated and hardware-transition candidates when AC results justify. Do not claim all 50 require immediate runs. No new historical investment sweep.


### Parallel track A: Define a defensible proposed LV topology, NOT YET SIMULATED

Study protocol exists: studies/household_frontier_reuse_v1/PROPOSED_LV_NETWORK_PROTOCOL.md.

- Choose a consistent proposed transformer/PCC position and **15 nested participating household positions**, keeping a fixed first 5, first 6, … first 15 arrangement.
- Use mapped geographic evidence, clearly distinguishing hypothetical supply routes from actual EPM GIS-owned conductors. Derive conductor type, R/X, ampacity, LV nominal phase/neutral assumptions, service lengths and a defensible radial or branched scheme.
- Define whether one supplied solar inverter at the shared PCC or a separately documented arrangement applies. Make zero-export logic, source voltage, protection and 5 kVA sensitivity explicit.
- First run **load-only baseline** and representative worst-hour voltage, transformer and branch-current checks; document basic plausibility before launching selected PV+BESS AC.

### Parallel track B: Reuse archived investment choices without rerunning MILP

- Read stage A 50 anchors and Stage B/C from studies/household_frontier_reuse_v1/outputs/archived_hardware_pool_5kva.csv; retain **all** household counts.
- Reconstruct full 8,760-hour fixed-hardware operation with manufacturer SOC and realistic power constraints; preserve original source hash and initial objective.
- Verify Deye SE-G5.1 current, 20% SOC, battery DC power sizing, inverter/PV string constraints and zero/incomplete cost proxies.

### Network-specific AC: resume existing GIS checks now; proposed network after track A

- Reuse prior annual 94022/106039 AC and partial campaign results. Run **independent** full-year AC for the proposed new LV network and each relevant selected PF, voltage and route assumption.
- Store convergence, Vmin/Vmax, line and transformer loading, losses, ENS, self-sufficiency and lifecycle-cost impacts; distinguish fixed-energy schedules from true AC-constrained redispatch.
- When AC fails, resample feasible P/Q regions for the same network/PF/topology, reoptimize **all 8,760 chronological SOC hours**, then independently AC-revalidate. Never transfer existing seven-house P constraints to another network.
- Only after validated AC runs form an AC-feasible cost/self-sufficiency Pareto. Targeted finalist PF/route stress must run all 8,760 hours before an annual claim. Do not turn a 77/96 critical-hour sample into annual certification.

### Later gate: Field validity and extensions

- Verify customer meter and actual transformer associations, nameplates (especially 106039), conductor impedances/current ratings, service routes, actual LV phase/split-phase and neutral, household PF, inverter night Q support, manufacturer battery power, actual tariffs, battery replacement and local civil/permit costs.
- Include AC losses and site/interconnection expenses in economics, and test uncertainty. Then move toward resilience/outage, practical forecasting/causal control, and household hosting/reassignment as independent, costed options.

## 5. Repo map and current source-of-truth links

- [Start here](READ_ME_FIRST.md)
- [Older overall audit](RESEARCH_STATUS_AND_AUDIT.md), superseded where newer manifests disagree.
- [Research walkthrough](professor_walkthrough/README.md) and [narrative](professor_walkthrough/RESEARCH_NARRATIVE.md).
- [Full saved PyPSA study](studies/pypsa_joint_optimization_v1/outputs/full_study/).
- [5–15-house archived economic frontier and equipment selection](studies/household_frontier_reuse_v1/README.md).
- [Proposed LV network assumptions and required missing inputs](studies/household_frontier_reuse_v1/PROPOSED_LV_NETWORK_PROTOCOL.md).
- [Manufacturer SOC and annual AC work](studies/ac_aware_redispatch_v1/).
- [Historical ZIP relocation](research_archive/RELOCATION_INDEX.csv).
- [EPM GIS topology and Q work](studies/epm_gis_pandapower_v1/README.md).

## 6. Session and change log

| Date | Action | Outcome |
|---|---|---|
| 3–6 Nov 2026 | Earlier archive and professor walkthrough organization | 24 figures / 11 stages; older images, raw notebooks, transfer ZIPs archived and indexed |
| 4–6 Nov 2026 | Manufacturer SOC + EPM-grid tests | 94022 seven-house 8,760 AC pass with P feedback at old strict screen; 106039 twelve-house 8,760 AC pass at proposed engineering screen; uncertainties stated |
| 5 Nov 2026 | Original campaign reuse index | 6,840 original tasks retained, 1,214 index-ready for further SOC+AC; no presumption of passing |
| 6 Nov 2026 | ZIP cleanup and 5–15-house frontier | 12 versioned ZIPs moved; 1,255 distinct 5-kVA hardware options, 387 sampled frontier hardware, 50 initial anchors, 296 hardware transitions; no new AC |
| **6 Nov 2026** | **Recovered project after chat context limit** | Located live private GitLab.com repo, verified latest commit and exact sources/manifest values, established this rolling handover. NEXT: define proposed feeder geometry, then baseline AC |

| **6 Nov 2026** | **User reconfirmed original methodology** | Primary research space remains 5–15 households (12 synthetic scenarios). Existing EPM connections and proposed LV network are two separate validations, not sequential alternative scopes. Proceed with economic/SOC selection and existing EPM AC work while defining proposed LV topology. Earlier summary incorrectly implied the topology was an overall research gate. No new numerical calculations executed. NEXT: dependency-aware parallel execution, then adaptive full-year AC. |

| **6 Nov 2026** | **Implemented agreed Stage A validation routing** | Reconciled 50 economic anchors with original 6,820 task-key index; all 50 exactly matched. 10 existing-GIS-runner eligible (4 seven, 3 nine, 3 twelve); 40 need an explicit new-LV network. One Stage A archive ID has saved AC evidence. Retained 337 B, 247 C, 621 D disjoint tiers and 296 overlapping transition designs. Wrote Stage A routing CSV, manifest, EPM dry-run manual and empty proposed-LV input contract. Extended existing AC batch tool with principal PF 0.98/0.95/1.0, preserving legacy 0.9 stress; new regression assertions added. No new AC or energy runs. Existing GitLab lacks campaign_manufacturer_01/ although campaign_AC_01/ has 4 candidate folders: before claiming reproducibility inspect local source trajectory hashes. NEXT: verify local simulation state, execute pending 9 eligible Stage A fixed-hardware energy/AC batches as resources allow; define nested 15-site geometry in parallel. |\n\n## 7. Working routine to avoid another context loss

Each substantive chat response should append a log entry and revise this file, committing with [ci skip] and without changing simulation outputs. Before modifying models, check live repository changes, read relevant source manifests and discuss any material new scenario/engineering assumption. If GitLab is unavailable, update a downloadable Markdown copy and explicitly mark remote sync as pending. Continue from verified results, not from old chat fragments.

**Local Windows repo:** Check git status and git log -1 --oneline before a new git pull. When safe, use git pull --ff-only origin main. Never pull blindly during an active local simulation or with uncommitted changes.
