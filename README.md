# SEEDExchange: approved research scope and annual AC evidence export

**Date:** 7 November 2026.

This package contains the approved WP1 scope, one proposed resilience/adaptability roadmap, one export script and its regression tests. Extract the package **into the root of your existing `resilient-energy-systems` checkout**, preserving the internal `case1/...` paths. No Git push is performed by this package.

## Contents

- `case1/RESILIENCE_ADAPTABILITY_RESEARCH_ROADMAP_DRAFT_2026-11-07.md`: New proposed grid-forming/grid-following blackout, resilience-constrained cost and adaptability studies. **Not approved WP2/WP3/WP4 definitions.**

- `case1/RESEARCH_SCOPE_APPROVED_2026-11-07.md`: Approved research objective, Stage A/B/C boundaries, physical assumptions, methodological sequence, open decisions and no-drift rules. No simulator inputs are changed.
- `case1/studies/ac_aware_redispatch_v1/export_selected_annual_results.py`: Read-only source/provenance check and zipped export of the two user-run 12-house, PF0.98 annual AC candidates. Uses the Python standard library only. No new calculations or Git changes.
- `case1/studies/ac_aware_redispatch_v1/tests/test_export_selected_annual_results.py`: Four unit regression tests.

## Run from repository root in Windows CMD or Anaconda Prompt

Test the export utility:

```bat
python -m unittest discover -s case1\studies\ac_aware_redispatch_v1\tests -p test_export_selected_annual_results.py -v
```

After your two annual runs have finished, create a **new project-local** export folder:

```bat
python case1\studies\ac_aware_redispatch_v1\export_selected_annual_results.py --repo-root . --output-dir "case1\studies\ac_aware_redispatch_v1\outputs\annual_exports\two_candidates_01"
```

This produces, inside that fresh folder:
- `comparison.csv`: one line per requested candidate, including source-verification status, annual feasibility, voltage, loading, losses, and selected manufacturer SOC/economics fields.
- `export_manifest.json`: source SHA-256 hashes, references, missing/incomplete-file flags.
- `SEEDExchange_two_12house_annual_AC.zip`: the shareable ZIP containing the comparison, manifest and *all found selected source hourly CSVs and associated provenance*, with their original project-relative paths.

Upload the generated `SEEDExchange_two_12house_annual_AC.zip` into the conversation. If either job did not finish, it is included as `AC_NOT_FOUND` or `INCOMPLETE_OR_PROVENANCE_UNVERIFIED`; the tool will never invent a pass. **The folder must not already exist**, to avoid overwriting old results.

Candidate IDs are fixed to `EC-ae0eed011a95698df0af` (54 PV, 9 batteries, 20 kVA) and `EC-70d86432647ba0b77603` (56 PV, 10 batteries, 20 kVA). These are equipment validations in existing network A, **not a 5–15-household physical sweep and not an inverter-location comparison**.

## Scope and GitLab

The matching `case1/PROJECT_HANDOVER_LIVE.md` on GitLab main is the only remotely updated file under the standing agreement. Place the approved scope file into your local `case1/` root. Do not commit or push this local source package until you explicitly decide to synchronize validated local changes to `main`.
