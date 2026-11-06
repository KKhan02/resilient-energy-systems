# WP1: evidence-aware Stage A AC routing, 5–15 homes

**6 November 2026.** This is an executable-workflow routing aid based on original saved energy investment results. **No new PyPSA optimization or pandapower power flow was performed in this step.** All original 6,840 tasks and existing AC results remain unchanged.

## Audited selection

- 12 synthetic household-case variants (5 to 15 homes, both 8-house H01/H02 variants).
- 1,255 distinct archived hardware designs at the 5 kVA planning reference.
- 50 criteria-derived Stage A anchors, with exactly one original archived task key and matching stable equipment ID each. [Machine-readable routing file](outputs/stage_a_50_network_routing.csv).
- All **10** presently executable on the provisional EPM GIS runner are in 7-house (4), 9-house (3), and 12-house (3) cases. The remaining **40** are retained for a proposed LV layout; they must not be imputed onto unsupported existing EPM territories.
- The rest of the saved pool remains available: **337 Tier B** (additional sampled frontier equipment), **247 Tier C** (hardware transitions not already Tier A/B), and **621 Tier D**. The separate 296 distinct transition-boundary count overlaps A/B/C, so 296 is not a further disjoint queue.
- One of the ten is EC-84f6a468f79bf545e863, the historical 12-house minimum cost design, with 8,760-hour saved EPM GIS AC evidence at PF 0.98 and additional sensitivity results. The other nine anchors are **not** labelled annual AC-passed.

## Separate network tracks

**Existing EPM GIS:** use existing explicit 7, 9, 12-house provisional membership only. Reference transformer 94022 for 7/9; 106039 for 12, where 5 kVA is **hypothetical**. Use the existing `batch_archived_campaign.py`, `run_archived_energy.py`, and `validate_archived_candidate_ac.py`; no duplicate model or fabricated household connections.

**Proposed new LV community:** preserve all 50 anchor selections across the 12 case variants, but do not call a pandapower network valid until a fixed 15-site nested participation order, transformer/PCC location, realistic feeder routes and cable parameters, phases and component connection points exist. See [proposed-network protocol](PROPOSED_LV_NETWORK_PROTOCOL.md) and [machine-readable unpopulated input contract](PROPOSED_LV_INPUT_CONTRACT.json). Transformer 5 kVA is only a preliminary hypothesis. Compare physically plausible compact versus radial designs only where the site geometry supports them.

## Existing-GIS run order and commands

**Do not pull over a running local simulation.** Inspect `git status`, saved local `campaign_manufacturer_01/` trajectories and any active processes first. The checked-in GitLab `campaign_AC_01/` contains results for four 12-house equipment IDs, but `campaign_manufacturer_01/` (source manufacturer-SOC trajectories) is **not present** in the repository output tree at this audit. Its absence does not prove the local run is missing. Retain the local trajectory CSV/manifest and verify their source hashes before relinking or re-running AC.

From repository root, in the existing power-systems Python environment:

```powershell
python -m pytest -q case1/studies/ac_aware_redispatch_v1/tests/test_archived_campaign_reuse_v18.py

# Dry-run the fixed-hardware manufacturer-SOC job for ONE selected existing-GIS anchor:
python case1/studies/ac_aware_redispatch_v1/batch_archived_campaign.py --stage energy --repo-root . --plan-dir case1/studies/ac_aware_redispatch_v1/outputs/campaign_reuse_index_v18_01 --energy-root case1/studies/ac_aware_redispatch_v1/outputs/campaign_manufacturer_01 --ac-root case1/studies/ac_aware_redispatch_v1/outputs/campaign_AC_01 --candidate-id EC-e47a168bfdbf7ea91f20

# When its energy trajectory exists locally, preview 0.98/0.95/1.00 annual AC jobs:
python case1/studies/ac_aware_redispatch_v1/batch_archived_campaign.py --stage ac --repo-root . --plan-dir case1/studies/ac_aware_redispatch_v1/outputs/campaign_reuse_index_v18_01 --energy-root case1/studies/ac_aware_redispatch_v1/outputs/campaign_manufacturer_01 --ac-root case1/studies/ac_aware_redispatch_v1/outputs/campaign_AC_01 --candidate-id EC-e47a168bfdbf7ea91f20 --scenario-set principal
```

These are safe **dry runs** by default. To launch a job, run the same command with `--execute` once the local dependencies, prior output folders, and hardware provenance have been checked. Existing completed checkpoints are resumable. Do **not** blindly rerun/overwrite the saved 12-house annual AC. Source code now accepts `--scenario-set principal` (PF 0.98/0.95/1.00 at base service factor) and `principal_nine` (three PF values by 1.0/1.3/1.6 *provisional* service factors) while preserving old `reference` and `nine` (PF 0.90 stress) behavior. Nine-combination annual checks are for **selected finalists**, not mandatory for every archived design.

After Stage A annual AC evidence, expand Stage B and C *adaptively* where feasible/infeasible, hardware-power or cost/frontier boundaries are unresolved. Reconstruct 8,760-hour manufacturer-SOC dispatch and verify separate annual AC per scenario. If AC fails, repeat P/Q corridor identification and chronological reoptimization **for that same hardware and network**, then independently AC revalidate all hours. A saved historical energy frontier is not a proven network-feasible economic frontier.

## Current evidence limitations

- No EPM certified customer connection, phase, exact conductor rating or transformer rating for every studied site.
- Manufacturer battery 20% physical minimum SOC, battery current, AC converter rating, zero nighttime VAR, chronological dispatch and zero load shedding must be checked with source records.
- Existing EPM AC source dispatch paths are not fully present on remote. The current 4×12-house AC candidate folders must not be counted as four independent cases of fully reproducible, separately verified equipment-annual economics without matching their energy trajectories.
- No fresh AC runs or economic cost corrections were made here. The older 0.97–1.03 pu screen remains a strict research sensitivity; 0.95–1.05 pu is a proposed engineering screen and not EPM certification.

[Routing manifest](outputs/stage_a_routing_manifest.json) | [Source frontier study](README.md) | [Existing campaign runner](../ac_aware_redispatch_v1/batch_archived_campaign.py)
