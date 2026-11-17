# SEEDExchange: local-first AC validation preparation

**Research status: 6 November 2026.** This package is a read-only audit and run planner for the archived San Rafael WP1 study. It does **not** optimize investment, run PyPSA, run pandapower, change topology, or modify any existing GitLab file. This is a local test package, not a GitLab commit.

## What it checks

The original archived 6,840-task PyPSA campaign has 12 household-case variants, 5–15 homes inclusive and two distinct 8-home synthetic load variants. The existing derived 5 kVA equipment archive has 1,255 distinct hardware choices. Its **50 Stage A anchors are an initial group, not a fixed limit**. The local audit can use either the 50 initial anchors or **all 1,255** saved hardware choices. You can perform all 50 annual AC tests, or more than 50, once the network models are defined.

For each equipment choice, the audit records its exact archived task and stable equipment ID, the existing EPM GIS runner eligibility, battery manufacturer-SOC trajectory and source hash status, and any matching saved full-year EPM AC reference status. The remaining generic LV and Site A scenarios stay explicitly **unmodeled**. Results without matching manufacturer-SOC source data are flagged, never counted as proven AC passes.

### How to use

Do not unzip on top of your existing project files. Extract this package to its own location, for example `D:\SEEDExchange_Local_Validation_Audit`.

From PowerShell, in the Python environment you use for the project, execute:

```powershell
python -m pytest -q .\tests
python .\review_validation_queue.py --repo-root "D:\path\to\resilient-energy-systems" --output-dir "D:\SEEDExchange_Validation_Review_01" --scope anchors
```

Replace the repository path with the absolute path of your actual GitLab checkout. **Choose an output directory that does not exist.** The program never writes into the checkout by itself. No PyPSA or pandapower dependency is required for this audit.

To review the **complete** 1,255-design historical pool:

```powershell
python .\review_validation_queue.py --repo-root "D:\path\to\resilient-energy-systems" --output-dir "D:\SEEDExchange_Validation_All_01" --scope all
```

This produces:

- `candidate_validation_ledger.csv`: per-equipment and network-specific evidence status
- `validation_audit_summary.json`: counts by case, selection tier, local energy status and EPM annual AC status, plus input hashes
- `existing_GIS_dry_run_commands.txt`: existing, verified GitLab runner entry points for each eligible GIS candidate, **without `--execute`**

The dry-run commands reuse `case1/studies/ac_aware_redispatch_v1/batch_archived_campaign.py` and only cover GIS-supported candidate cases. They should be run from the **repository root**, after verifying that no previous long-running simulation is active and checking the local output folders. To execute computational jobs later, the existing runner requires its explicit `--execute` option. It must not blindly overwrite earlier output directories.

## Three network comparison tracks

| Track | Physical model | Present validation scope |
|---|---|---|
| A, existing EPM GIS | Saved EPM GIS LV backbone, known transformer locations and provisional household-service links | Existing runner currently supports 7, 9, 12-house reference memberships. Other population sizes need explicit, evidence-backed or hypothetical assignment scenarios. |
| B, proposed community LV | New, physically specified LV community arrangement; transformer 5 kVA is an initial **hypothesis**, not assumed sufficient for 15 homes | No new nodal AC model until supply point, nested home locations, cable paths, phase and impedance are agreed. |
| C, Site A clearing-based PV+BESS | Existing identified clearing, shared PV+BESS, nearby mapped properties and a feasible EPM connection proposal | **A third location-specific sensitivity**, not automatically a new transformer. Feeder routes and legal/electrical interconnection remain unverified. |

The initial geographic nearest-property set is only an optional C screening input. It is **not** an existing EPM circuit map. Original historical optimization results remain unchanged for all three comparisons.

## Interpreting the audit

This is a source integrity/queue audit, not a new power-system result. A 12-house candidate with saved `annual_ac_summary.json` but without the matching `campaign_manufacturer_01/<equipment_id>/` annual chronology gets `AC_RECORDED_BUT_LOCAL_SOURCE_TRAJECTORY_MISSING` in the audit. This status is deliberately conservative. If your local checkout already has that annual chronology, the audit checks it before reporting the saved AC result.

The principal future PF values are 0.95, 0.98 and 1.00. The current local audit inspects the **reference PF 0.98, service factor 1.0** full-year AC evidence. Other PF sensitivities remain in the source result directories and are not classified by this script.

The code uses only Python standard library. The tests additionally require `pytest`. No network requests, installs, GitLab writes or CI pipelines are performed.

**After running**, send the generated `validation_audit_summary.json` and `candidate_validation_ledger.csv` in this chat. They identify which local manufacturer-SOC simulations and annual AC checks can be reused versus those truly missing. We can then prepare a locally runnable, network-specific simulation batch without duplicating completed work.
