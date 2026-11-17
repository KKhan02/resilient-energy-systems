# Sync-branch preservation and triage review (17 November 2026)

**Branch reviewed:** `sync/seedexchange-local-2026-11-17` compared against protected historical baseline `main` at `9aaca5473838b69de442cb238ba40a0e97405844`.

This branch was pushed from the user's local Windows repository. The GitLab comparison initially showed **one sync commit and 2,166 added paths**. Do not merge it wholesale without a file-size, provenance, duplication, source-integrity and privacy review.

Key observations from the synchronized tree:

- `case1/studies/` contains current reproducible codes, summaries, independent audits and original local numerical outputs. **Do not relocate or delete any signed/historical evidence in this branch.**
- There were **57 ZIP archives** across the sync tree, including duplicated packages alongside extracted folders and very large hourly-results material. Some archives may still be needed as provenance, so first identify byte-identical duplicates and authoritative manifests before any archive consolidation.
- The root contains **seven versions of PROJECT_HANDOVER_LIVE.md** and a path literally named `$zip`. These need manual provenance inspection before classification or cleanup, not an automatic deletion.
- Historical `case1/professor_walkthrough` held **24 PNG figures**. New curated plots are added under Stages 12–13 without replacing historical graphics. Stage 14 remains explicitly energy-only and under electrical validation.
- Avoid mixing counts: `376/432` is the corrected original-network AC portfolio; `408/432` requires the *hypothetical* A0 94022 five-edge network alternative.
- Preserve separate A0/A1, STAr/MST, site/architecture and outage-resilience boundaries. **No hydropower.**

**Recommended eventual main merge:** Source modules + tests + small audited summary CSVs/manifests + curated figure copies + navigable story documentation. Keep bulky redundant raw outputs and transfer ZIPs out of an eventual small reviewed merge, or in separately controlled archival storage when provenance permits. No force push, no history rewrite, no deleting old research.
