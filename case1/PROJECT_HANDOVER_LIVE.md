# SEEDExchange El Arenal / San Rafael: rolling research handover

**Last audit: 7 November 2026. Scope-restatement awaiting explicit user verification; no new modelling.**
**Canonical project:** https://gitlab.com/KKhan02/resilient-energy-systems (private, GitLab.com), main.
**Verified pre-handover HEAD:** bfc95c1b60ee.
**Original public collaboration repository (separate):** https://gitlab.gwdg.de/open-energy-modelling/energy-community. Direct GWDG access failed during this audit. Do not assume it matches the private GitLab.com research repository.
**Purpose:** Enable exact continuation after context limits. This is a living technical record, not final design certification.

## 0. Instructions for every future assistant turn

Read this file first, then check the live GitLab HEAD and relevant output manifests. **After every substantive reply**, revise this SAME file with decisions, completed actions, results, failures, uncertainties, and next steps. Commit documentation changes with [ci skip] and retain an exportable Markdown copy. Do not recreate a new handover filename. Mark reported, source-verified, planned, running and unverified results distinctly. Preserve all historical numerical results and test evidence. Do not change new topology, equipment ratings, cost assumptions, models or tariffs without discussing substantive design choices with the user. Do not start a new historical optimization sweep simply to reproduce saved outputs.

## Standing research-decision and coding protocol (reconfirmed 6 November 2026)

**This takes precedence over an unqualified "proceed" when a modelling choice remains open.**

1. **Research/audit before coding.** Inspect existing results, source data, GIS geometry, repository history and tests. Use read-only comparisons for unresolved choices.
2. **Discuss substantive choices with the user before implementation.** Present alternatives, physical assumptions, evidence level, advantages/tradeoffs and a recommended choice. Explicitly settle equipment ratings, topology, nested membership, new transformer placement/rating, operating control, PF/voltage limits, costs, tariff, site or protection choices **before encoding them**. Do not infer approval from broad permission to continue.
3. **Once the engineering design is agreed**, implement and test without needless requests for approval of ordinary programming details. Clear bug fixes preserving agreed assumptions can follow a test-first process.
4. **LOCAL-FIRST IMPLEMENTATION, MAIN ONLY (user reaffirmed 7 Nov).** After engineering agreement, prepare downloadable code and test files for the user to run locally. User returns logs/results and iterations remain local. Once changes are substantial and validated, **only after explicit user authorization** synchronize them directly to the existing GitLab **main** branch. Do not create feature branches or merge requests as the default workflow. Never modify code, models, results, site data, or other GitLab files without the user's specific authorization. Documentation-only updates to this handover on main after every reply are the standing exception.
5. Distinguish **approved/implemented/passed/conditional/proposed/open** decisions in all reports. Never invent EPM poles, customer service topology, transformer nameplates, physical connection routes, phase systems, or software-supported reactive/backup capabilities. Park critical/deferrable demand fractions unless separately reapproved.
6. The 5–15-house **main design space**, the two EPM-vs-proposed-LV electrical studies, 50 first-stage economic anchors, and principal PF 0.95/0.98/1.00 were already discussed and agreed. **Still open**: exact proposed nested 15-site membership and supply-point geometry, topology and conductor choice, and matching source trajectories for remote AC results. No new physical network created in this turn.
7. **Earlier exception to MR discipline**: commit `3e9f526` directly changed `batch_archived_campaign.py` and added its regression assertions without the usual MR. It retained the agreed PF choices but has **not been shown to pass local tests**. Treat as pending independent review, not CI-verified. Do not silently overwrite or roll back.

**Explicit standing GitLab permission, 6 November 2026:** Update ONLY this canonical `case1/PROJECT_HANDOVER_LIVE.md` handover on GitLab after EVERY assistant response, with `[ci skip]`. **No other GitLab file, code, model, result, workflow, or dataset may be modified or committed unless the user specifically instructs it.** Local-first downloadable packages and user-run simulations remain the normal development process. Previous 27 October runner-minute guidance still applies to simulations and CI.

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

| **6 Nov 2026** | **Implemented agreed Stage A validation routing** | Reconciled 50 economic anchors with original 6,820 task-key index; all 50 exactly matched. 10 existing-GIS-runner eligible (4 seven, 3 nine, 3 twelve); 40 need an explicit new-LV network. One Stage A archive ID has saved AC evidence. Retained 337 B, 247 C, 621 D disjoint tiers and 296 overlapping transition designs. Wrote Stage A routing CSV, manifest, EPM dry-run manual and empty proposed-LV input contract. Extended existing AC batch tool with principal PF 0.98/0.95/1.0, preserving legacy 0.9 stress; new regression assertions added. No new AC or energy runs. Existing GitLab lacks campaign_manufacturer_01/ although campaign_AC_01/ has 4 candidate folders: before claiming reproducibility inspect local source trajectory hashes. NEXT: verify local simulation state, execute pending 9 eligible Stage A fixed-hardware energy/AC batches as resources allow; define nested 15-site geometry in parallel. |\n\n| **6 Nov 2026** | **Reconfirmed coding and decision protocol, read-only evidence audit** | Historical 26/27 Oct handovers verified: investigate first; settle substantive engineering assumptions with the user; then implement in a scoped tested MR; preserve original data. Direct-main runner edit 3e9f526 departed from MR process; test execution not claimed. Read-only comparison of 4 saved 12-home PF0.98 annual AC trajectories confirmed they are **not identical** despite equal worst-case headline values; 7-module EC-83dc vs 8-module EC-84f have 622/8760 inverter-P differences and maximum 3.7488 kW P difference. No new code, simulation or GitLab CI run. Next work: explicitly decide proposed nested-site geometry/topology, inspect local source manufacturer trajectories and existing active simulation state before new execution. |\n\n## Decision clarification, 6 November 2026: source of the 50 Stage A designs and third network comparison

- **Origin of 50:** The number was **computed from the existing archive, not chosen as a hard simulation cap**, in the 6 Nov 2026 analysis commit `8184fb0bb8bd51271cb16d8987d232ec1080d195` (13:01:50 CET), documented at `case1/studies/household_frontier_reuse_v1/README.md`, later illustrated in commit `bfc95c1b`. Original study: 6,840 PyPSA tasks; 1,348 optimal 5-kVA task rows and 1,255 distinct hardware arrangements.
- Per one of the 12 **household-case variants** (N=5 to 15; 8-house H01 and H02 are separate synthetic load cases), take source-defined **minimum cost**, **highest self-sufficiency**, and the **least-cost designs exceeding 70%, 80%, 90% and 95% self-sufficiency**, deduplicate equipment within each case. Counts: 5 houses 5, 6 houses 5, 7 houses 4, 8-H01 4, 8-H02 4, 9 houses 4, 10 houses 5, 11 houses 4, 12 houses 4, 13 houses 4, 14 houses 4, 15 houses 3 = **50 across the entire 5–15-house design space**, not 50 designs for one house, and not 50 per household.
- The 50 Stage A anchors were the initial **energy-economic** candidate set, not 50 required annual AC runs, not 50 verified physical installations, and not an imposed maximum. The sampled nondominated and hardware transition archives provide adaptive expansion when actual AC outcomes warrant. Do not equate the two 8-house *synthetic demand variants* to as-built customer identity.
- **Three comparison scenarios now intended:** (A) existing EPM GIS-connected transformer/customer networks with provisional service mappings; (B) an explicitly designed hypothetical community LV network for comparable 5–15-home expansion; (C) a **Site A clearing-based shared PV+BESS** network, connecting selected nearby mapped properties where a credible LV cable path and EPM interconnection can be proposed. Scenario C is a distinct location-specific alternative to study, not proof that these houses are presently supplied by Site A and **does not imply a new transformer at Site A**. Compare with B as distinct layouts only where assumptions differ; avoid double-counting identical cases.
- The previous straight-line nearest-15-house exercise is **geographic screening only** and remains an optional input for C, not an approved existing EPM feeder map, no frozen nested membership. H25 may be nonresidential; H23 is a possible alternative. Existing mapped transformer locations and evidence already exist; **do not restart transformer georeferencing**. No new physical site/network parameters approved at this turn.
- **Coding and GitLab boundary reconfirmed:** After discussion and agreement, deliver local packages; user runs and supplies results; iterative debugging stays local; synchronize model/code only after sufficient locally verified progress and explicit user instruction. The standing exception is this rolling GitLab handover: update it after every response. **No other GitLab modifications without specific authorization.**

| **6 Nov 2026** | **Clarified 50-design provenance, Site A scenario, GitLab boundaries** | 50 was criteria-derived from archived 5–15-household cases in commit 8184fb0b, not a hard run cap nor a single-house design count. Accepted Site A clearing as third *proposed* location-specific PV+BESS/nearby-house comparison, no new transformer implied. Local-first code iterations; only this handover may be committed after every response. No project code or study files modified. |\n\n## Local-first execution checkpoint, 6 November 2026: no arbitrary 50-design AC cap

**User decision:** The 50 criterion-selected Stage A designs are **neither a minimum nor a maximum nor a fixed required count**. We may validate all 50 in annual AC, and then as many more of the remaining archived 1,255 5-kVA designs as are informative and computationally warranted. The user specifically objects to over-rigid statements implying we should not run all 50. Preserve every 5–15-household variant, both synthetic 8-house alternatives and all historical 6,840 PyPSA investment tasks. Reuse annual AC results where provenance matches; do not mistake simple annual output similarity for matching hardware trajectories. The constraint is correct network membership/topology, not an arbitrary run count.

**Prepared during this assistant turn, LOCAL PACKAGE ONLY:**
- `SEEDExchange_Local_Validation_Audit_v1.zip` with stand-alone Python source `review_validation_queue.py`, README and four local regression tests.
- Default `--scope anchors` audits **all 50** Stage A designs. `--scope all` audits **all 1,255** distinct archived 5-kVA hardware designs, including B/C/D. Neither mode runs energy optimization nor pandapower.
- Verifies exact historical task-key to candidate-ID matching, active GIS runner eligibility, SHA256/8,760-row manufacturer-SOC local trajectory, saved full-year PF0.98/service1.0 AC summary and hourly count with matching energy-source SHA. Missing local manufacturer trajectories remain explicitly unverified.
- Writes a candidate-by-network validation ledger, source status summary, and existing-GIS dry-run commands to a **new output directory outside the checkout**. No source code, remote data or existing simulation folder is modified. Future user-launched annual PyPSA fixed-hardware dispatch and AC is a separate explicit `--execute` action through the existing source runner.
- Offline fixture tests were executed: **4 passed**, then Python bytecode compilation verified. These are validation-*audit* tests, not proof the full GIS/PyPSA numerical runtime works. **No new annual AC calculations have been executed**.
- Three comparison configurations remain: A, existing EPM GIS; B, physically specified generic proposed LV for 5–15; C, Site A clearing-based PV+BESS and proposed nearby connections. No new B/C physical feeder, new EPM customer mapping, transformer installation, ratings or cable routing has been approved or implemented.

**NEXT LOCAL ACTION:** User runs `python review_validation_queue.py --repo-root <local checkout> --output-dir <fresh path> --scope anchors` after extracting the ZIP, then returns `validation_audit_summary.json` and `candidate_validation_ledger.csv`. With those, verify local historical `campaign_manufacturer_01/` chronologies, resume eligible existing-GIS jobs without overwriting, and develop the B/C network choices through discussion before their AC simulations. The full 1,255-design audit can be run whenever useful, without an artificial selection ceiling.

**GitLab permissions this turn:** the user authorizes committing **only** this rolling handover after each response. No repository code, model, simulation or other file may be edited on GitLab without a specific user instruction. This update is documentation only, `[ci skip]`. Local audit ZIP has **not** been pushed to GitLab.

## 7 November 2026: user local audit run and missing GitLab routing CSV

**User executed the delivered `SEEDExchange_Local_Validation_Audit_v1.zip` locally** under `D:\\0. UoL\\3rd Sem\\5.06.M308 Resilient Energy Systems\\resilient-energy-systems\\SEEDExchange_Local_Validation_Audit`. `python -m pytest -q tests` returned **4 passed in 0.47 s**. The follow-up `python review_validation_queue.py --repo-root ... --output-dir D:\\SEEDExchange_Validation_Review_01 --scope anchors` failed during source preflight, before producing any ledger or running any PyPSA/AC calculations:

```
review_validation_queue.py: error: Required source not found:
D:\\0. UoL\\3rd Sem\\5.06.M308 Resilient Energy Systems\\resilient-energy-systems\\case1\\studies\\household_frontier_reuse_v1\\outputs\\stage_a_50_network_routing.csv
```

**Diagnosis source-verified:** the missing source exists on GitLab main as of 7 Nov, exact path `case1/studies/household_frontier_reuse_v1/outputs/stage_a_50_network_routing.csv`, introduced in commit `3e9f526536c5d383ee7e0133b2022374f9e3e383`. Since the script reads `all_distinct_equipment_candidates.csv` *before* this routing file, it apparently found the equipment index locally. Local repository is likely missing recent direct-GitLab file commits. The four standalone unit tests did not exercise full repo data availability; no new solver or AC run was attempted.

**Minimal proposed local fix, not executed by assistant:** from the local repository root:
```bat
git fetch origin main
git show origin/main:case1/studies/household_frontier_reuse_v1/outputs/stage_a_50_network_routing.csv > "case1\\studies\\household_frontier_reuse_v1\\outputs\\stage_a_50_network_routing.csv"
```
This fetches current remote Git objects and writes only the missing local CSV without pulling/updating user code or switching branches. Then rerun `python review_validation_queue.py --repo-root "<repo root>" --output-dir "D:\\SEEDExchange_Validation_Review_01" --scope anchors`. If the output folder already exists, use a new one. **Next user evidence:** returned `validation_audit_summary.json` and `candidate_validation_ledger.csv`, or new error/output text. Need inspect hashes and existing manufacturer source trajectories before proposing expensive annual AC reruns.

**Standing remote-write policy:** update ONLY `case1/PROJECT_HANDOVER_LIVE.md` after each substantive assistant reply. All model/source changes and numerical work remain local-first and require user's explicit authorization before GitLab synchronization. No other GitLab file or CI action performed in this turn.

## 7 November 2026: clarify local main vs origin/main and missing destination folder

**User log:** Local audit tests passed 4/4 in prior turn. In local Windows CMD, running `git fetch origin main` succeeded and updated local remote-tracking reference `origin/main` from `1ac4d5d` to `ac17158` at that fetch. Then `git show origin/main:case1/studies/household_frontier_reuse_v1/outputs/stage_a_50_network_routing.csv > "case1\\studies\\household_frontier_reuse_v1\\outputs\\stage_a_50_network_routing.csv"` failed with **"The system cannot find the path specified."**

**Diagnosis:** `main` is the user's local checked-out branch; `origin/main` is a remote-tracking ref for the same GitLab main. Fetch alone does not update checked-out local files. Windows redirection cannot create a target file when parent directories are missing. This error indicates the destination parent path is missing or inaccessible locally, not evidence of two separately created development branches and not evidence the GitLab source file is absent. GitLab main still contains the exact routing CSV at the expected path.

**User command / standing policy (7 Nov):** **All authorized project pushes on the existing main branch only**, after enough local code and simulation work and explicit instruction from the user. No default feature branch or MR workflow. Continue committing only this rolling handover after each substantive reply with [ci skip]; never modify any other repository file on GitLab without user direction. Existing past commits and local branches (if any) are not to be altered or deleted merely because of this preference.

**Safe local check, not executed by assistant:**
```bat
cd /d "D:\\0. UoL\\3rd Sem\\5.06.M308 Resilient Energy Systems\\resilient-energy-systems"
git branch --show-current
git status --short
git log -1 --oneline
```
If checked out on `main`, no uncommitted or untracked conflicts, and no active simulations: `git pull --ff-only origin main` incorporates the missing CSV and other committed files without creating a feature branch. If there are local changes, do not pull blindly; inspect status. For isolated CSV recovery when avoiding a pull, create the parent directory `mkdir "case1\\studies\\household_frontier_reuse_v1\\outputs"` and then repeat the `git show origin/main:... > ...` operation; this only reconstructs a missing local CSV after parent directory exists. Verify CSV and rerun original audit from `SEEDExchange_Local_Validation_Audit`, with a fresh output directory if necessary.

No project code or numerical models were updated this turn; GitLab write scope: only this handover.

## 7 November 2026: first successful LOCAL Stage A validation audit

**User ran the local ZIP auditor (no change to GitLab code).** In the local Windows Conda base environment from `SEEDExchange_Local_Validation_Audit`:
- `python -m pytest -q tests` => **4 passed in 0.28s**.
- `python review_validation_queue.py --repo-root "D:\\0. UoL\\3rd Sem\\5.06.M308 Resilient Energy Systems\\resilient-energy-systems" --output-dir "D:\\SEEDExchange_Validation_Review_01" --scope anchors` => **successful**, wrote new read-only provenance audit results.

Exact user-reported summary:
```json
{
  "written_to": "D:\\SEEDExchange_Validation_Review_01",
  "status": "READ_ONLY_LOCAL_PROVENANCE_AUDIT_NO_NEW_OPTIMIZATION_OR_AC",
  "scope": "anchors",
  "candidate_count": 50,
  "tier_counts": {"A_DEFINED_TARGET_ANCHOR": 50},
  "GIS_eligible_count": 10,
  "manufacturer_SOC_status_counts": {
    "NOT_IN_LOCAL_CHECKOUT": 47,
    "LOCAL_TRAJECTORY_HASH_VERIFIED_8760": 3
  },
  "existing_EPM_reference_AC_status_counts": {
    "NOT_APPLICABLE_NO_GIS_MEMBERSHIP": 40,
    "NOT_IN_LOCAL_CHECKOUT": 9,
    "CONDITIONAL_ANNUAL_AC_PASS_PROVENANCE_MATCHED": 1
  },
  "source_plant_sizing_recomputed": 0,
  "AC_simulations_performed": 0
}
```
All 12 household-case variants (5..15, both 8-house variants) remain represented. GIS-eligible first-stage designs: **7-house 4, 9-house 3, 12-house 3**; remaining 40 lack membership for the current GIS runner. Principal PF 0.95, 0.98, 1.0; optional stress PF 0.90. Three network comparisons: A existing EPM; B hypothetical generic new LV; C Site A clearing-based proposed PV/BESS with nearby households.

**Interpretation:** 47 'NOT_IN_LOCAL_CHECKOUT' means no manufacturer-SOC trajectory at expected folder, NOT infeasible or solver failure. 9 'NOT_IN_LOCAL_CHECKOUT' AC likewise NOT failures. The 1 matching full-year AC pass is conditional on provisional GIS/screen assumptions; no new calculations are claimed. User provided only printed aggregate audit output, **not the candidate-by-candidate CSV**; do not guess the exact three SOC-verified IDs or nine missing cases. Need `D:\\SEEDExchange_Validation_Review_01\\candidate_validation_ledger.csv` to prioritize 8,760-hour AC and cost corrections, preserve exact checkpoint hashes, and avoid duplicating prior results. Also distinguish the 4 archived 12-house AC candidate folders on GitLab from 1 locally provenance-matched Stage A candidate.

**Next local-first action:** review user-generated candidate ledger (upload into chat, or print selected fields); confirm local checked-out runner version since `git fetch` does NOT update working files and the new principal PF mode may not be in the local checkout. Only after matching source trajectories and confirming network-specific model integrity should we issue targeted manufacturer-SOC/fixed-hardware and annual pandapower AC commands. Do not turn 50 into a rigid ceiling or a mandatory number; all 1,255 distinct 5-kVA equipment choices remain eligible for adaptive expansion. No extra GitLab files may be modified. Only this handover gets a documentation commit with [ci skip].

## 7 November 2026: project-contained outputs only, user correction

**User correction:** The prior assistant instructed `--output-dir "D:\\SEEDExchange_Validation_Review_01"`, which scattered research outputs outside the repository. This was an assistant path choice, not a requirement of the auditor. **All future SEEDExchange source, working files, input datasets, reports, logs, numerical results, figures, and local audit outputs must remain beneath the existing repository root** `D:\\0. UoL\\3rd Sem\\5.06.M308 Resilient Energy Systems\\resilient-energy-systems`, under the relevant `case1/studies/<study>/...` directory. No absolute `D:\\SEEDExchange_...` sibling output folders in future instructions. Scripts may create a **new** internal study output directory; do not overwrite the historical archives.

**One-time user-local move instruction (not executed by assistant):** run from repository root:
```bat
move "D:\\SEEDExchange_Validation_Review_01" "case1\\studies\\household_frontier_reuse_v1\\outputs\\validation_review_01"
```
The parent `.../outputs` is an existing directory in the checkout; check whether destination exists before moving and avoid overwrite. Future full-archive read-only audit can be run from repo root:
```bat
python SEEDExchange_Local_Validation_Audit\\review_validation_queue.py --repo-root . --output-dir "case1\\studies\\household_frontier_reuse_v1\\outputs\\validation_review_02" --scope all
```
The output target should be a fresh study-local folder for each run, with relative path appropriate to the script invocation.

**User uploaded 3 actual local outputs** from the successful `--scope anchors` audit: `candidate_validation_ledger.csv` (50 candidate rows), `existing_GIS_dry_run_commands.txt`, and `validation_audit_summary.json`. Their contents were inspected in this turn. The three `LOCAL_TRAJECTORY_HASH_VERIFIED_8760` Stage A candidates are **ALL 12-house 106039 cases**:
- `EC-84f6a468f79bf545e863`: 41 PV panels, 8 batteries, 12 kVA inverter, historical $4767.8333/y and 81.0366% self sufficiency, source trajectory SHA256 `ce38d26890b11fa8342fc5a663b479ebebaece219b5388cade1dc26c74ed78b3`; **only candidate** with locally provenance-matched 8760-hour conditional annual EPM AC pass, zero failed hours for reference PF0.98, service factor1.0.
- `EC-ae0eed011a95698df0af`: 54 panels, 9 batteries, 20 kVA inverter, historical $5259.4462/y and 92.6061% self sufficiency, source trajectory hash `d178239b3f4d29a09c7ef4da833e8b472ccc0d7cd262ff7a61ef6a2c45a4309c`; annual EPM reference AC **not present in local expected folder**, not a failure.
- `EC-70d86432647ba0b77603`: 56 panels, 10 batteries, 20 kVA inverter, historical $5297.0754/y and 95.2109% self sufficiency, source trajectory hash `be0998cce99b094c19ab3925ff04d10aa4d024ff3eb368203dfa65490e0d648e`; annual EPM reference AC **not present locally**, not a failure.
The remaining seven 7-/9-house GIS-eligible anchors have **no locally verified SOC trajectory in their expected folders**, so they need local review or fixed-hardware SOC dispatch before AC; all 40 other anchors lack existing GIS membership, awaiting hypothetical B/C site/network definition.

**No source/code pushed, no numerical runs started, only this rolling handover updated on GitLab with [ci skip].** User's main-only GitLab synchronization requirement is unchanged.

## 7 November 2026: incorrect relative destination while inside audit subfolder

**User reported failure** running from `D:\\0. UoL\\3rd Sem\\5.06.M308 Resilient Energy Systems\\resilient-energy-systems\\SEEDExchange_Local_Validation_Audit`:
```bat
move "D:\\SEEDExchange_Validation_Review_01" "case1\\studies\\household_frontier_reuse_v1\\outputs\\validation_review_01"
```
returned `The system cannot find the path specified. 0 dir(s) moved.`

**Cause and correction:** Destination was **relative to the active working directory** (the audit-tool subfolder), not to repository root. This was a mistaken instruction from assistant; prior audit output was reported as written to `D:\\SEEDExchange_Validation_Review_01`. Correct from current prompt:
```bat
cd ..
move "D:\\SEEDExchange_Validation_Review_01" "case1\\studies\\household_frontier_reuse_v1\\outputs\\validation_review_01"
dir "case1\\studies\\household_frontier_reuse_v1\\outputs\\validation_review_01"
```
If still absent, verify source with `dir "D:\\SEEDExchange_Validation_Review_01"` before any other attempt. This is a **user-local file move only**, not yet confirmed successful; do not claim it was executed.

**Read-only next AC work plan grounded in user-provided 50-design ledger:** 12-house EPM 106039 Stage A candidate `EC-84f6a468f79bf545e863` already has provenance-matched 8760h PF.98 reference AC. Two other 12-house Stage A candidates have verified manufacturer-SOC dispatch and no matching local PF.98 annual AC: `EC-ae0eed011a95698df0af` (54 panels/9 BESS/20 kVA) and `EC-70d86432647ba0b77603` (56/10/20). First perform **dry-run** of the existing `batch_archived_campaign.py --stage ac --scenario-set reference --candidate-id ...` from repo root using original study-local plan, energy, AC directories; confirm each job's outputs/manifest. Then the user may run with `--execute` on their machine. No investment PyPSA campaign rerun. Do not overwrite prior manufacturer or AC folders. PF 0.95 and 1.0 optional next principal sweep once reference validated, and retain 7- and 9-house remaining queued work. Annual AC output folders remain inside `case1/studies/ac_aware_redispatch_v1/outputs/campaign_AC_01/`.

**Read-only source verification this turn:** Live GitLab main `batch_archived_campaign.py` supports `reference` and `principal` PF sets; user-local checkout may lag remote because previous `git fetch` does not update working tree. Runner requires signed source trajectory and checks checkpoint hashes; do not blindly pull with uncommitted local data or re-run existing completed jobs. No numerical runs, fixes, or non-handover GitLab code/data changes performed this turn.

## 7 November 2026: Correct scope drift, distinguish annual AC reference runs from research design

**User concern and corrected priority:** The assistant was issuing many ad hoc simulation/audit commands, treating specific 12-home AC runs and output folders as if they defined the research program. This drifted from the joint study goal. **Return to the engineering comparison first**, with the pre-existing 5–15-house PyPSA sweep as economics, and the three agreed network configurations:
1. **A existing EPM GIS transformer/LV connections**, with provisional customer associations and correctly qualified nameplates;
2. **B new hypothetical shared-community LV system**, an explicitly designed network across household counts;
3. **C Site A clearing shared PV+BESS and credible proposed nearby-house electrical connections**, avoiding any assumption that a new transformer must be at the clearing.

**User has already started annual AC** following previously supplied local commands. The supplied commands were for **two individual 12-house EPM 106039 candidate IDs**, not for full study B or C: `EC-ae0eed011a95698df0af` (54 panels/9 battery modules/20 kVA inverter) and `EC-70d86432647ba0b77603` (56/10/20). The script checks the stored 8,760-hour manufacturer-SOC fixed-equipment dispatch at PF 0.98 and service factor 1.0 against a provisional balanced pandapower network, using a **hypothetical 5 kVA nameplate for 106039**. Exact chosen candidate(s), runtime and outcomes remain unknown until the user reports them. It does **not** re-run the full investment MILP, choose hardware, build a new topology or validate network B/C. If already running, preserve the results and avoid unnecessary interruption. Do not automatically queue further such annual runs just because input trajectories already exist.

**Scientific distinction:** In fixed-hardware redispatch/AC, hardware is held constant **for one candidate evaluation**; other equipment configurations, household counts, network geometries, control variants, reinforcement alternatives and optimisation models are explicitly part of the research. Archived 50 Stage A economic anchors are **not** a fixed or limiting number of annual AC jobs. Results across evolving models should differ where assumptions differ; always label what changed and compare only controlled scenarios.

**Output policy clarified:** Each study/model stage and version has its own **project-contained** output folder, with source inputs, scenario manifest, hardware, PF, household case, network definition, time-series, annual summaries, validation status, and source version/provenance. Existing fixed campaign folders are historical reference artefacts, **not** the one compulsory destination for future studies. Never overwrite older saved outputs to fit a new run. Never scatter folders outside repository root.

**Next activity is study design, not more blind annual batch execution:** Define controlled comparison matrix for A/B/C, distinguish known EPM asset/service links from hypothetical network extensions, decide which topology and PV/BESS siting alternatives actually answer research questions, then implement new/evolving models locally after discussing assumptions with user. Build staged checks (network baseline, representative hours, full-year energy-SOC+AC) where meaningful. The original aim also includes economic/lifecycle, resilience and multiple shared PV+BESS clusters when source-grounded; do not narrow all work to a single central plant. Maintain the local-first user-run loop and direct-main GitLab synchronisation only when explicitly authorised. **Only this rolling handover may be committed to GitLab after each response**, with [ci skip].

## 7 November 2026: integrated A/B/C research matrix, source reuse (no model changes)

**User direction:** Proceed with the agreed SEEDExchange objective, explicitly **do not deviate or reinvent the wheel**. Stop treating ad hoc audits, isolated candidate IDs or fixed output paths as the research objective. Do not undertake new unrelated simulations, tooling, georeferencing or equipment sweeps when source work already exists. The user has an annual 12-house PF0.98 AC reference run in progress or recently started, with outcome not yet provided; preserve its results and do not issue automatic extra jobs.

**Read-only source confirmation performed:** GitLab `main` at `bb21c13edf03456ac6186183cecc04a8c858a5ef` at inspection. Existing components to REUSE rather than rewrite:
- Investment and annual energy: `case1/studies/pypsa_joint_optimization_v1/{model.py,run.py,full_study.py,outputs/full_study/}` with 6,840 archived 5–15-house tasks and 12 synthetic case variants. Separate `case1/studies/household_frontier_reuse_v1/` frontiers contain 1,255 5-kVA economic hardware combinations, 50 initial anchors, and adaptive extra hardware pool.
- Existing GIS: `case1/studies/epm_gis_pandapower_v1/{epm_topology.py,run_coordinated_q.py,coordinated_q_control.py,data/}` with six modeled EPM transformer assets and mapped LV network, unverified service associations, balanced equivalent. `case1/studies/ac_aware_redispatch_v1/scenario_membership.py` explicitly selects 7-house and 9-house 94022 cohorts and 12-house 106039 cohort. No implication all 5–15 synthetic cases map directly to one existing EPM feeder.
- Manufacturer SOC and annual physics: `case1/studies/ac_aware_redispatch_v1/{fixed_hardware.py,run_archived_energy.py,validate_archived_candidate_ac.py,corridors.py,run_annual_feedback.py,outputs/}`. Saved 7-house annual redistribution and 12-house annual manufacturer AC results are conditional on original proxy networks; keep historical AC outputs and running work.
- Existing central/shared-cluster energy-model research: `case1/studies/annual_shared_pvbess/{annual_screen.py,outputs/}` and `case1/studies/architecture_comparison/{README.md,architecture_reference_matrix_DRAFT.csv,decision_register.csv}`. Initial C vs K comparison already modeled in annual aggregate energy terms, but its shared PCC netting is not nodal-feeder placement evidence. C=one centralized shared PV/BESS; K=multiple **multi-home** shared clusters; H=central plus satellites (later), I=per-house benchmark only if worthwhile. Matched aggregate PV, battery energy/power and inverter AC ratings precede separately optimized discrete equipment comparisons.
- Site A: `case1/studies/site_a_solar/` with user-proposed clearing, digitized ~1,759m² gross area, pvlib NASA 2025 analysis, shading scenario assumptions. This is a preliminary resource/space study, **not** evidence that the clearing has utility service or that all new hardware fits.
- Prior design method `case1/NEXT_PHASE_SCOPE.md` and existing architecture draft: preserve load-only baseline, existing-customer territory, 25yr cost, potential hosting/reassignment after base-case evidence, no new free transformers, no critical/deferrable load fractions.

**Comparison protocol to implement by EXTENDING existing code after decisions:**
1. Three **network** setups are distinct dimensions: **A** existing provisional EPM LV cases at supported populations, **B** explicit hypothetical but electrically specified representative community LV for full 5..15-house expansion, **C** a Site A-centered shared PV/BESS with proposed credible nearby-house feeder/interconnection. C need not install a new transformer; test connection options, not fabricated as-built cables.
2. Architecture dimension C(central) / K(shared multi-home clusters) initially; optionally H hybrid, I secondary benchmark. Do not confusingly use letter C for both network setup Site A and architecture central in code labels: use `network=EPM/NEW_LV/SITE_A`, `architecture=CENTRAL/CLUSTERED/HYBRID/INDIVIDUAL`.
3. Hold weather, load realization, household count, original archived hardware, manufacturer SOC, PF and voltage/thermal screens identical for *matched-hardware* architecture/network comparisons. Separately allow the distinct hardware sizes and per-architecture reoptimization. Compare no DER, PV-only where available, shared PV+BESS.
4. For each network run load-only plausibility, controlled representative-hour pandapower, then full 8760h selected AC/P-Q-constrained dispatch. Reuse source trajectories and pre-existing checks where provenance matches; only reoptimize failed/incomparable cases. Report Vmin/Vmax, feeder/transformer current/loading, losses, unserved energy, grid import, self-sufficiency, costs and site/connection constraints. The existing AC results do not include AC losses in original PyPSA optimization.
5. Control comparison and external validity: 0.95/0.98/1.00 principal PF, 0.90 optional stress, 0.95–1.05 pu engineering screen, 0.97–1.03 prior strict research band, 20% manufacturer battery SOC floor, night Q default off. Distinguish actual EPM evidence from modeled service routes and unverified phase/nameplate; no certified 106039 5-kVA assertion. Outage/islanding resilience is later separate conditional analysis.
6. Keep each evolving *study* under a separate **project-contained** versioned directory with its own inputs/results/figures/manifest, rather than forcing all future configurations into the old `campaign_AC_01` reference folder. Existing saved studies must remain intact.

**Implementation gap, rather than new engines:** A/B/C scenario topology and physical PV/BESS placement-to-node input mapping, followed by existing PyPSA-to-pandapower dispatch/AC interface and architecture cost crosswalk. Need approve physically relevant B and C source/feeder assumptions before building new network branches. Not justified to rerun 6840 tasks or create another general-purpose audit interface. Begin with read-only source integration plan, then a *single* focused local model extension when design inputs are decided, tested by the user on their machine, GitLab main sync only on explicit request.

**This assistant turn:** Audited docs and source files read-only, no new model files, optimizer execution, or AC runs, no modifications to GitLab beyond this handover. User's existing local 12-house annual job is separate and may continue.

## 7 November 2026: Site A GIS source-crosswalk: northern 25 kVA found

**Purpose:** Make concrete progress on the agreed A/B/C model comparisons without recreating existing tools, running another historical optimization, or coding new physical network assumptions without user design agreement. This was a **read-only inspection of the GitLab existing GIS and model source files**.

**New cross-reference, source-grounded (NOT new site survey):**
- Existing source `case1/studies/epm_gis_pandapower_v1/data/epm_network_relevant_sanitized.geojson` has 183 features: 14 EPM transformer points, 54 EPM LV segments, 32 EPM MV features and 83 EPM poles.
- The formerly partly unidentified **northern 25 kVA** transformer point `(latitude 6.249940251, longitude -75.011914005)` is matched to an explicit feature with **number 137468**, **EPM node 842059**, **25 KVA** `UNIDAD_MED_CAPACIDAD`, `OPERACION` status, `R50-02` circuit, `S` phase and `240/120` secondary. GIS recorded position `(6.24994025200004, -75.011914006)` matches the user-reported coordinates to ~0.000001 degree (submetre). The older candidate aliases 010729/010729c/224804 are not yet independently reconciled; asset details are an archival GIS record, not field-certified or proof of spare capacity.
- **No EPM LV features associated with node 842059 are in the sanitized extract.** This is a data-extract limitation, **not evidence no real LV network exists**. Existing `epm_topology.py` main modeled IDs exclude 137468; treating it as a modeled usable existing LV feeder requires obtaining source LV geometry and explicit implementation, not a rename.
- Site A clearing `(6.248376671296207,-75.00932156861505)` sits **~335.2 m straight-line** from 137468 and **~378.9 m** from 94022. The closest EPM LV line segment in the existing GIS source lies **~191.6 m** from Site A: EPM LV `G3E_FID 47053144`, node `931076`, transformer `94022`, circuit `221-12`, `AAC calibre 2`, source GIS `OPERACION`, segment catalog length 27 m. Next nearest 94022 LV segments are ~215.6 and 218.4 m away. These are **planar nearest-point distances**, not routed cable lengths or permission to interconnect.
- 94022 in GIS is explicitly `5 KVA` `OPERACION`, circuit `221-12`, phase T, 240/120 transformer secondary, with 6 LV GIS features on node 931076. The source GIS also carries `106039` as `5 KVA` `OPERACION` on node 923494 with 15 LV features, **distinct from the earlier portal table's nominal 5 kW label**. Preserve the source-unit and timestamp distinction, field nameplate unverified.
- The 15 closest mapped properties to Site A are a **proximity screen only**, not verified customer membership. Some of those properties belong to different EPM candidate transformer territories; a physically connected Site A network would require valid routes, customer reassignment or separate PCC/metering, not simple accounting.

**Concrete research recommendation before coding:**
1. **A existing EPM**: retain and reuse exact GIS backbone, known 7/9/12 case membership, known annual AC results and user's current annual run; A is the evidence-based reference. No new A optimisation by default.
2. **B representative community LV**: use documented existing conductor assumptions and original reference feeder methodology as inputs, then discuss one explicit physical 15-site nested tap geometry, transformer/PCC parameters and 5–15-house participation before AC. Keep B as **synthetic engineering benchmark**, not claimed surveyed site connection. Avoid implicit reshuffling and no free capacity.
3. **C Site A clearing**: first conditional candidate is **PV+BESS installed at Site A, new explicitly hypothetical service route to existing 94022 LV segment FID 47053144**, with variable proposed cable route/length and connection/protection cost, not an assumed existing wire. Alternative candidate is a connection associated with source-matched northern 25 kVA transformer 137468; requires missing mapped LV and possible separate circuit/site permissions first. The `R50-02` vs `221-12` distinction must never be erased. The 5 kVA 94022 nameplate could bind well below 15 households; transformer 25 kVA does not imply free headroom. These are **recommendations for discussion, not yet approved code/model connections**.
4. For all three, compare **same equipment and demand first** in CENTRAL vs multi-home CLUSTERED shared PV/BESS configurations, using existing `annual_shared_pvbess` to benchmark grouped energy and existing `epm_topology.py` + `ac_aware_redispatch` for pandapower physical AC, without rewriting solver engines. Separate fixed-hardware validation from later genuine equipment-per-architecture optimisation. Output each evolving study stage to unique **inside-project** directories with source manifests; do not force future studies into historical `campaign_AC_01`.
5. First execution gate after physical connection decisions: load-only / selected worst-hour network checks, followed by 8,760-hour dispatch+AC for valuable designs and robust conditions. Avoid long annual tasks before confirming topology and comparative value; but **do not impose a 50-design annual run ceiling**.

**User-facing status:** The previous annual reference run is user-started and its outcome has NOT yet been provided. No new numerical simulator, code patch, new geometry, GitLab data edit, or external utility approval. Only this handover commit `[ci skip]` under user's standing permission.

## 7 November 2026: revised N1/N2/N3 conditional network design, placement reused

**Direct user decisions, overriding earlier brainstorming:**
- **Explicitly EXCLUDE northern transformer** from all modelling, recommendations and future comparisons. This includes northern asset previously tentatively identified as 137468, EPM node 842059, 25 kVA on circuit R50-02. Retain its prior identification only as provenance/history; **do not include it as a candidate PCC or suggest work involving it**.
- Use **5 kVA transformer rating for 106039** as the operating modelling assumption. Source's earlier portal 5 kW label can be acknowledged historically, but do not repeatedly reopen the rating choice. User reported that local authorities may effectively use PF=1 for ratings. Treat this as user-supplied rationale rather than a verified universal Colombian rule; preserve electrical PF reference 0.98, principal sensitivity 0.95/0.98/1.00. Do not infer real household load PF=1 from rating nomenclature.
- **Conditional site design accepted for further comparison:** If connection to existing 94022 LV fails technical/economic checks, consider a **NEW hypothetical 5 kVA transformer at Site A clearing** supplying selected nearby houses. Compare proposed **STAR** vs **MST (minimum spanning tree)** house connections. Both are *new proposed layouts*, not as-built EPM links. MST minimizes geometric edge lengths only for specified nodes and permissible routes, and is not intrinsically thermally/voltage/protection-feasible; compare impedance, conductor ampacity, actual route, fault protection, PCC/transformer loading and installation cost. Do not assume 5 kVA will be sufficient to serve all 15.
- **Reframe network comparison labels for clarity:** `N1 = existing EPM transformer/LV GIS`; `N2 = shared PV/BESS at Site A with proposed tie to existing 94022 LV`; `N3 = fallback new 5 kVA transformer at Site A, proposed STAR versus MST feeder topology`. The earlier vague `generic hypothetical LV` becomes the physically specified N3 geometry rather than a disconnected fourth network scenario. The 5–15-household synthetic energy design space remains primary. Select actual house groups/attachment routes explicitly before representing a new network as valid.
- **DO NOT confuse N1/N2/N3 NETWORK cases with historical frontiers A/B/C selection tiers**: hardware Tier A = initial 50 cost/self-sufficiency anchors; Tier B = further sampled nondominated hardware; Tier C = transition-boundary hardware. The optimal hardware configurations identified by the archived 6,840 PyPSA tasks are the **inputs to subsequent network-specific pandapower + manufacturer-SOC-constrained PyPSA electrical/economic validation**, not separate full optimization campaigns for each network by default. Broaden hardware selection as warranted; no 50-candidate cap or required count.

**Already completed inverter siting work (READ-ONLY RECONFIRMED, DON'T REPEAT):**
- `case1/studies/epm_gis_pandapower_v1/run_epm_validation.py` studied feeder `head` and `end` and control alternatives. `run_coordinated_q.py` explicitly supports `head`, `middle`, `end`; saved `outputs/coordinated_q_sweep_pf098/ac_scenario_summary.csv` has **116 distinct scenarios × 40 selected critical hours = 4640 solved rows**, PF 0.98, head/middle for 94022 and 106039, Q-ratio/control variations. In saved 106039 12-house Q-ratio=0.25 coordinated comparison, head **40/40** feasible selected hours with mean loss **0.0897372 kW**, middle **40/40** with mean loss **0.1580490 kW**. These values are critical-hour *means* not annual AC losses. Past 12-house head manufacturer-SOC annual AC saved 8760/8760 feasible on the provisional GIS with 5 kVA model reference.
- Reuse siting results and previous models. New Site A placement is an *additional physical connection* case, not reason to rerun head/mid/end benchmark. Only repeat an operating sensitivity when a new physical network or hardware assumption actually changes the question.

**Next local-first modelling step after user design confirmation:** Reuse saved 5–15-house Tier A/B/C economic selection, existing `epm_topology.py` and `ac_aware_redispatch` engines and historical siting evidence. N1 continue preserved existing EPM studies. N2 require realistic proposed Site A-to-94022 feeder connection, candidate houses and electrical routing; evaluate 94022 headroom and 5 kVA thermal/voltage constraints with no fictitious customer transfer. If infeasible or uneconomic, N3 proposed 5 kVA transformer + star/MST routing for same comparable site/house set, reassess 5 kVA against actual modelled coincident loads and PV/BESS. Distinguish energy economics vs electrically feasible network costs and retain separate versioned **project-contained** study outputs. Any additional central-versus-shared-cluster architecture analysis builds on archived study, not a new optimizer.

**No code, data or simulator modifications performed in this turn.** Continue local-first user-run iterations. **GitLab remote write permission extends solely to this single `case1/PROJECT_HANDOVER_LIVE.md` file each substantive assistant reply with `[ci skip]`; no other files to be committed without explicit user instruction.**

## 7 November 2026: selected full-year siting comparison, two candidate jobs

**User research decision/question:** Original inverter placement study on EPM GIS used only **40 critical hours**. Is a selective annual (8,760 h) placement comparison justified? The user reports **one of the two pending 12-house fixed-hardware annual AC jobs has finished** and plans to run the other too, "just in case". Which job finished, outcome, hourly output hashes and metrics have NOT yet been provided; do not invent or mark either completed/failed. Existing planned jobs are candidate `EC-ae0eed011a95698df0af` (54 panels, 9 battery modules, 20 kVA inverter) and `EC-70d86432647ba0b77603` (56 panels, 10 battery modules, 20 kVA inverter), 12-house EPM transformer 106039, PF0.98, service factor1, current annual validator uses **head siting only**.

**Source check, read-only GitLab:** `case1/studies/epm_gis_pandapower_v1/outputs/coordinated_q_sweep_pf098/ac_scenario_summary.csv` and `validation_manifest.json` confirm 116 scenarios ×40 critical hours on 94022 and 106039, PF0.98, head and middle Q-capability sweep. At `106039, 12 houses, coordinated Q ratio 0.25`, head had **40/40 feasible**, `mean_loss_kw=0.08973719999213202`; middle had **40/40 feasible**, `mean_loss_kw=0.1580490245018943`. Relative difference of mean loss **~76% higher at middle** for these specifically selected hours; **NOT** an annual energy-loss estimate, and does not itself prove 8,760 h feasibility. For 94022 historical sweep uses **10-house** group, not the seven-house annual cohort; avoid cross-membership conclusions.
- Separate saved annual `case1/studies/ac_aware_redispatch_v1/outputs/twelve_ac_full_02/annual_ac_summary.json`: **12-house, 41 panels/8 modules/12 kVA**, head-connected, manufacturer SOC 20%, 5 kVA model transformer, PF0.98, 8,760/8,760 AC pass on **0.95–1.05 pu** screen, `sum_modelled_ac_losses_kwh=456.3059875`, min voltage 0.95565107 pu, maximum transformer loading 94.43866%; remember proxy balanced GIS and source-trajectory assumptions. This is a head-only annual comparator, NOT an annual head/middle matched study.
- Seven-house full-year AC feedback/head reference `outputs/seven_annual_feedback_ac_check_01/annual_ac_summary.json` 8760/8760 pass on earlier 0.97–1.03 research band, annual losses 367.15 kWh, but its redispatched P differs from some other fixed-hardware baselines.
- `case1/studies/ac_aware_redispatch_v1/validate_archived_candidate_ac.py` currently **hardcodes** `build_net(territory,'head')` and calls `run_hour(...,'head',...)`; it does not expose a `--siting` parameter. `run_coordinated_q.py` and `epm_topology.py` already support head/middle/end. Do NOT suggest a non-head annual run using a nonexistent argument.

**Agreed practical recommendation, not yet implemented:** selectively run one matched **12-house annual head-versus-middle** check for the existing 41/8/12 reference if source dispatch, controls, Q-ratio, 5kVA/PF.98, SOC, household membership, voltage bands and seasonal profiles are truly aligned. Reuse existing 8760-hour head result only after verifying exact provenance and assumptions; perform full-year *middle* AC in a new project-contained versioned directory after adding an optional `siting` parameter to the **existing** annual validator locally, with signature/resume protection and tests. No new optimization engine or broad 50-design x siting sweep. Only consider additional annual placement tests for the seven/nine-house 94022 cohorts after matching same household membership, hardware and control conditions; existing 40-hour 10-house placement effect is only a screening clue. New N2 Site A physical PV/BESS position and N3 star/MST require own electrical checks; they are not duplicates of old inverter siting study.

**No code, simulator, or scenario output changed this assistant turn.** User's current annual jobs run locally and their outcomes are pending. Standing authorization is to update ONLY the rolling handover on GitLab after each assistant response, with [ci skip], with all code changes delivered locally first and other GitLab project files not changed.

## 7 November 2026: user scope verification REQUESTED, NOT YET APPROVED

**Critical user correction:** The assistant had repeatedly conflated the 5–15-house PyPSA economic sweep, the smaller number of 7/9/12-house GIS-eligible EPM electrical cases, selection tiers A/B/C, physical network scenarios, and a 40-critical-hour inverter siting study. User explicitly directed: **IMMEDIATELY state entire objective, modelling workflow and current assumptions for user verification, THEN after verification preserve the approved understanding completely and avoid scope drift.** The assistant's response in this turn is a proposed technical restatement **PENDING USER VERIFICATION**. Do not silently declare it approved or start implementation. The requested local aggregation/ZIP script from the preceding user request is paused until they verify scope; still owed afterward.

**Scope summary presented FOR VERIFICATION:** Main goal is 5–15 households San Rafael community PV+BESS supply: equipment PV/BESS/inverter sizes; energy cost and self-sufficiency; pandapower AC voltage, line/transformer loading, losses; hosting capacity and comparison of central shared versus multi-home shared clusters; grid-only/PV-only controls if meaningful. Original saved 6,840 PyPSA optimization tasks with 6,820 optimal and 20 infeasible, 1,255 distinct 5kVA historical equipment and 50 initial anchors across 12 case variants (including two synthetic 8-house variants), not 50 compulsory simulations. Source-demand profiles synthetic 2025 data. Selected annual manufacturer SOC and EPM AC pass checks exist for 7-/12-house cases; 9-house model eligible but not annual checked in archive. The **full 5–15-house physical AC sweep is not done** and existing GIS only maps actual/plausible selected 7/9/12 cohorts, not each N=5..15 as-built.

**Three study tracks offered to user for confirmation:**
- **A Existing EPM:** reuse mapped existing transformer/LV data and provisional service attachments, initially 7/9 houses on 94022 and 12 houses on 106039 (not a 5..15 as-built expansion). Do not arbitrarily assign missing houses to existing EPM.
- **B Proposed 5–15-house community LV:** consistent geographically identified 15-home candidate set with nested participating N=5..15, explicit hypothetical supply point and realistic star/MST or other credible route/conductor variants; model via existing pandapower and PyPSA. Keep physical geometry and ratings open until agreed.
- **C Site A shared PV+BESS clearing:** proposed 94022 LV connection; if unsuitable, fallback hypothetical new 5 kVA transformer at Site A plus star/MST electrical connections to selected houses. **Northern 25 kVA transformer 137468 excluded completely** under user's explicit ruling. Study B and C share network builder; avoid duplicating models, but keep distinct hypotheses and costs.
This **reinstates the originally agreed distinct new-LV 5–15-house workstream**, which an earlier 'N1/N2/N3' shorthand accidentally collapsed into Site A options. Require user confirmation before finalizing nomenclature; preserve historical N1/N2/N3 as superseded draft only if user agrees.

**Methods and sequencing proposed, pending confirmation:** reuse 6,840 PyPSA economic task archive, select cost/self-sufficiency anchors and expand toward Pareto/transition when AC boundary uncertain; establish valid network and household memberships; run baseline load-only and representative stress-hour AC on each physically supported network; run 8760h manufacturer-SOC-compliant dispatch+AC for promising equipment; revise constrained dispatch/size only where warranted, compare network losses and lifecycle costs plus central-vs-shared clusters. Existing ~40-hour head/middle/end study remains evidence; optional annual matching placement study later, **NOT the priority**. User reports one of two 12-house AC equipment jobs done and second planned, outcomes/files not yet provided.

**Provisional assumptions presented:** PF 0.98 baseline, PF0.95/PF1.0 principal sensitivities, PF0.9 optional stress; user-selected 106039 model 5kVA and known archived 94022 5kVA; new 5kVA transformer at Site A conditional, not proven adequate for 15 homes; voltage primary 0.95..1.05 pu, prior 0.97..1.03 stricter sensitivity; 20% minimum physical battery SOC; nighttime inverter Q off unless substantiated; 2025 gridded NASA and synthetic household profiles, 25-year provisional lifecycle cost framework, uncertain EPM actual tariff/site/installation costs, EPM phase/service associations not certified. Critical/deferrable fractions remain parked.

**Important unresolved choices needing user confirmation before code:** actual 15-house nested geospatial cohort, supply point for synthetic new-LV study, permissible star/MST cable routes and conductor/phase parameters, Site A service connection and criteria to compare fallback, common demand-profile assignments. No 'PF=1 Colombian law' independently asserted merely from user's report about power-factor conventions. One correction if user disagrees with A/B/C taxonomy is welcome and must override this provisional write-up.

**CONTROL: DO NOT TREAT THIS SECTION AS AN APPROVED DESIGN.** When user verifies, create an explicit pinned LOCKED scope/assumptions/decision register within this same canonical handover and export local copy; keep future answers consistent unless user explicitly revises a decision. Only this handover was updated remotely [ci skip]; no code, data or simulation output changes made.


## 7. Working routine to avoid another context loss

Each substantive chat response should append a log entry and revise this file, committing with [ci skip] and without changing simulation outputs. Before modifying models, check live repository changes, read relevant source manifests and discuss any material new scenario/engineering assumption. If GitLab is unavailable, update a downloadable Markdown copy and explicitly mark remote sync as pending. Continue from verified results, not from old chat fragments.

**Local Windows repo:** Check git status and git log -1 --oneline before a new git pull. When safe, use git pull --ff-only origin main. Never pull blindly during an active local simulation or with uncommitted changes.
