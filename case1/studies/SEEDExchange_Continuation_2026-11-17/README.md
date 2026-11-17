# SEEDExchange reproducible continuation | 17 November 2026

This folder contains source-checked Stage 14 plotting and read-only archive triage. Use **Miniforge Prompt or Anaconda Prompt**, from the root of the synchronized GitLab checkout. No data deletion and no new PyPSA/pandapower optimization.

The scripts run directly against existing GitLab source files. The exact original 2025 annual CSV SHA-256 values are enforced before any plot is created.

## Step 1: Update

    git switch sync/seedexchange-local-2026-11-17
    git status --short
    git pull --ff-only origin sync/seedexchange-local-2026-11-17

Do not pull with uncommitted tracked changes. Save or commit them first.

## Step 2: Render Stage 14 figures

    python -m pip install matplotlib
    python "case1\professor_walkthrough\14_PVBESS_Sizing_and_Utilization\generate_stage14_figures.py"

Creates three figures and FIGURE_MANIFEST.json in a **new** Stage 14 figures folder. Existing folder is never overwritten. Figures represent eight fixed-hardware energy-only designs, not an AC-feasible sizing result. The B9 candidates still fail transformer loading at the recorded PF/length stress point.

## Step 3: Audit the repository

    python "case1\studies\SEEDExchange_Continuation_2026-11-17\audit_repository_archives.py" --repo-root . --out "case1\repository_audits\archive_audit_2026-11-17"

Creates ARCHIVE_AUDIT.json and ARCHIVE_AUDIT.md under a new directory. The audit reads all checked-out tracked ZIPs and identifies exact SHA-256 duplicates. It does **not** delete, rename or move any ZIP. Older snapshot: 57 ZIPs, seven identical groups; the local audit must establish its own results. Avoid committing full raw ZIPs to main as part of this step.

## Step 4: Review and push the small new results

    git status --short
    git add "case1/professor_walkthrough/14_PVBESS_Sizing_and_Utilization/figures" "case1/repository_audits/archive_audit_2026-11-17"
    git diff --cached --stat
    git commit -m "Add source-verified Stage 14 figures and local ZIP audit [ci skip]"
    git push origin sync/seedexchange-local-2026-11-17

The local audit is a disclosure of the current tracked checkout; the manual push publishes it for joint inspection, but does not constitute a merge to protected main.

## Next research gate

B9 (SS_B9 and MC_B9) has 1 / 2 transformer-overload hours under the PF=0.95 and length=1.6 stress case. Resolve by chronological SOC-neutral event-hour dispatch changes, independent changed-hour pandapower tests, and then all-nine PF/length checks. New hardware is not AC-certified.


## Verify before running plots

    python -m unittest discover -s "case1\studies\SEEDExchange_Continuation_2026-11-17" -p "test_*.py" -v

Two regression gates check the original eight-case SHA-verified sources and test read-only ZIP duplicate detection in an isolated temporary Git fixture.
