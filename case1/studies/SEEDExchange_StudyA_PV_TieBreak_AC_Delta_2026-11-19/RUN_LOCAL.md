# A1 106039 | Stage 2 versus Stage 1 targeted AC differential

The signed v2 energy experiment succeeded for both MC_REF and MC_P33, showing identical annual grid-import energy but different hourly dispatch. An AC replay is required because the import differences reach several kW.

**Method:** Reuse the original `seed_study_a_v6.py` methods `data_for_case`, `new_territory`, `solve_ac_hour`, the original GIS `run_epm_validation.build_net`, the approved A1 11-house 2025 individual load chronology, the 106039 hypothetical 5 kVA source transformer and the same head-connected PV/BESS inverter. The script checks v2 Stage1/Stage2 CSV SHA256, annual source manifest, hourly energy closure, equipment, load and source chronology, and produces **paired AC solutions for every hour whose inverter AC injection changed**. It uses the existing controller and daytime Q ratio 0.25 with nighttime Q off. No new network model, hardware change or energy optimization.

By design this is **not a full 8760-hour AC validation**: unchanged hours are not rerun, existing annual results cannot be silently transplanted across unmatched source hashes, and output status never says AC-certified. Baseline PF 0.98/route 1.0 first; the full scope then covers PF {0.95,0.98,1.00} and length {1.0,1.3,1.6}. Each matched changed hour has two AC solves. The separate sign, voltage, line/transformer, reactive and incremental-loss statistics are in the per-factor CSV and manifest. Existing AC failures and original annual evidence are unchanged.

## Complete Windows Miniforge pull, test, execute, check, push

From repository root:

```bat
cd /d "D:\0. UoL\3rd Sem\5.06.M308 Resilient Energy Systems\resilient-energy-systems"
git status --short
git switch sync/seedexchange-local-2026-11-17
git pull --ff-only origin sync/seedexchange-local-2026-11-17

python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_PV_TieBreak_AC_Delta_2026-11-19" -p "test_*.py" -v

python "case1\studies\SEEDExchange_StudyA_PV_TieBreak_AC_Delta_2026-11-19\ac_delta_replay.py" --repo-root . --preflight-only

python "case1\studies\SEEDExchange_StudyA_PV_TieBreak_AC_Delta_2026-11-19\ac_delta_replay.py" --repo-root . --scope baseline --out "StudyA_A1_106039_PV_TieBreak_AC_Delta_Baseline_v1"
```

The baseline output is useful ONLY if both cases have results and `errors` is empty. It does not establish any complete year AC status, even if every changed hour passes.

Review `StudyA_A1_106039_PV_TieBreak_AC_Delta_Baseline_v1/RUN_MANIFEST.json`. If baseline completes, run full 9-factor robustness comparison in a separate path:

```bat
python "case1\studies\SEEDExchange_StudyA_PV_TieBreak_AC_Delta_2026-11-19\ac_delta_replay.py" --repo-root . --scope full --out "StudyA_A1_106039_PV_TieBreak_AC_Delta_Full_v1"
```

Only after reviewing a successful manifest with two cases for baseline or eighteen scenarios (2 cases × 9 factor combinations) for full, commit and push **results only**. Preserve any failed receipts without claiming success. Do not overwrite result folders:

```bat
git status --short
git add "StudyA_A1_106039_PV_TieBreak_AC_Delta_Baseline_v1" "StudyA_A1_106039_PV_TieBreak_AC_Delta_Full_v1"
git diff --cached --stat
git diff --cached --name-only
git commit -m "Validate paired AC change hours for A1 PV tie-break [ci skip]"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
```

If only the baseline has been run, stage **only** that folder and adjust the commit message. All source code is already in the active GitLab branch, so there are no ZIPs to extract or new source files for the user to stage.
