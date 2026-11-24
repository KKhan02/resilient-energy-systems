# Study A | 94022 SS90 three remaining November undervoltages: joint local AC runbook

**Prepared:** 24 November 2026. **GitLab branch:** \`sync/seedexchange-local-2026-11-17\`. **Status:** new source-only candidate builder + 60 AC case-hour bounded runner prepared; no new solver result claimed. Original PF0.98 annual AC source \`StudyA_94022_SS90_MarNov_AnnualAC_PF98_v1\` already independently audited in \`RECIPROCAL_94022_SS90_ANNUAL_PF98_INDEPENDENT_AUDIT_2026-11-24.md\`.

## Aim and immutable source model

The original annual PF0.98 model has 8760/8760 converged but **five** original annual undervoltage hours. Two were corrected by held March28 50% + November27 98% battery discharge transfers (2 fixed target hours). Three original remaining hours require another bounded source-respecting strategy:

| New failed target | Original PF.98 min house V | Candidate same-day donor |
|---|---:|---|
| 2025-11-16 20:00 | .9493666354 pu | 2025-11-16 19:00 |
| 2025-11-29 19:00 | .9498047086 pu | 2025-11-29 17:00 |
| 2025-11-29 20:00 | .9470063251 pu | 2025-11-29 18:00 |

All three original failures have no transformer or conductor overload, and they are **not** cured by the March/27-Nov accepted schedule. The 29-Nov donor intervals 17->19 and 18->20 **overlap**: donors are physically distinct, but their shifted modeled storage energy shares an intervening snapshot. Their individual caps are **not additive AC or storage guarantees**.

Frozen source: \`StudyA_A0_A1_MatchedHardware_Full_v1/A1_94022_ss90_to_A0/energy_hourly_2025.csv\` SHA256 \`dc3ba1f9f6b3d9b0b750e2212f549ff8e1c351c44258233b8357577850374c93\`. A0 ten-house EPM-proxy GIS territory (not surveyed), A1 SS90 original six battery module hardware, nominal 5kVA *assumed* transformer, inverter 10kVA and bank DC maximum 8.55095461847511kW. Manufacturer-model 20% battery physical SOC maps to .229kWh per module / 1.374kWh six-module usable Store floor. No new PV energy, PV export, load shedding, grid charging or installed hardware is inferred.

The runner keeps **exactly the already sampled 8/8 PF.98/.95 March+Nov27 acceptable operating points**, applies the three new same-day battery discharge transfers to the **same annual 8760h state trajectory**, checks annual complete DC/P/AC balance, battery power, battery \`Store\` 20% floor/nameplate, cyclic year-end closure, zero ENS/export, hardware inverter power and unchanged annual energy. It then tests **five common fractions** of each independent single donor DC bound (0, 25, 50, 75, 98%), but **validates the three simultaneously** before solving any AC. The frozen annual original PF0.98 8760-hour AC archive is verified by signed hash and all six new 0% PF.98 baselines are regenerated and compared exactly.

The new AC workload is **5 joint candidates × 6 distinct changed hours × 2 PF values (.98 and .95) = 60** case-hour evaluations. Night/remaining daylight Q is the existing PV availability/controller rule; no nighttime reactive capability invented. Passing all 60 is not the criterion: a specific candidate must pass **all 12 local new AC points** while preserving the earlier 8/8 = 20 selected sampled model AC points. Even 20/20 would not be corrected full-year AC, utility signoff or an optimal economic schedule.

## Windows Miniforge Prompt commands, from repository root

### A. Synchronize GitLab, preserve untracked results

~~~bat
git branch --show-current
git status --short
git fetch origin
git pull --ff-only origin sync/seedexchange-local-2026-11-17
~~~

Do not use \`git clean\`, \`git reset --hard\`, global \`git add .\`, or force push. Leave P1 v2, ZIP archives and older backup handover untracked unless independently approved.

### B. Ten new solver-free tests

~~~bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22" -p "test_matched16_94022_ss90_remaining3_ac.py" -v
~~~

Expected \`Ran 10 tests\`, \`OK\`. The tests cover two overlapping Nov29 storage transfer effects, distinct chronological donor/target stamps, no additional overlap with March/Nov27, stop-on-hardware/chronology mismatch, expected sixty AC samples and unchanged source battery math. They do not prove the full frozen file is present; preflight handles that.

### C. Signed preflight without new AC solves

~~~bat
python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_94022_ss90_remaining3_ac.py" --repo-root . --preflight-only
~~~

Required status:

\`SIGNED_94022_SS90_REMAINING3_MULTI_DONOR_PREFLIGHT_NO_NEW_AC\`

The printed receipt must show 8760 signed original source hours, a prior PF98 original AC 8760-row source hash, validated 8 already accepted March/Nov27 AC points at both PF values, source donor PF .95 scalar envelope values, and five common-fraction candidate annual SOC/AC/DC passes. There should be **60 planned and zero new AC**. The original three target hours must remain exactly from the original signed source before redistribution.

The expected isolated DC caps, subject to exact source recomputation in the code, are approximately: Nov16 19→20 **4.094481 kW**, Nov29 17→19 **2.939809 kW**, Nov29 18→20 **4.057018 kW**. Treat them as bounds only. A valid joint battery source frame is not proof of donor AC feasibility.

### D. Execute the bounded local AC campaign only after tests + preflight pass

~~~bat
python "case1\studies\SEEDExchange_StudyA_Synthesis_2026-11-22\matched16_94022_ss90_remaining3_ac.py" --repo-root . --run-local
~~~

Expected new version directory, if unused:

\`StudyA_94022_SS90_Remaining3_Pair_AC_v1\`

Expected complete status:

\`REMAINING3_94022_SS90_JOINT_AC_SAMPLED_60_COMPLETE_NOT_ANNUAL\`

Contains \`RUN_MANIFEST.json\`, \`REMAINING3_DONOR_TARGET_60_AC_CASEHOURS.csv\`, \`JOINT_CANDIDATES_5.csv\`, separate \`figures_diagnostic/\` donor/target voltage plots. For numerical failures a partial file is explicitly unverified and the manifest remains INCOMPLETE. Preserve incomplete evidence and share the traceback instead of rerunning immediately.

### E. Verify the result and push ONLY that folder

On completed output, using the actual new folder name if not v1:

~~~bat
python -c "import pathlib,json,csv,hashlib; p=pathlib.Path('StudyA_94022_SS90_Remaining3_Pair_AC_v1'); j=json.loads((p/'RUN_MANIFEST.json').read_text()); a=p/'REMAINING3_DONOR_TARGET_60_AC_CASEHOURS.csv'; c=p/'JOINT_CANDIDATES_5.csv'; assert j['status']=='REMAINING3_94022_SS90_JOINT_AC_SAMPLED_60_COMPLETE_NOT_ANNUAL'; assert sum(1 for _ in csv.DictReader(a.open(newline='')))==60; assert sum(1 for _ in csv.DictReader(c.open(newline='')))==5; assert j['new_AC_hours_executed']==60; assert hashlib.sha256(a.read_bytes()).hexdigest()==j['ac_csv_sha256']; assert hashlib.sha256(c.read_bytes()).hexdigest()==j['candidate_csv_sha256']; assert j['annual_2025_corrected_AC_verified'] is False; print('60AC 94022 RECEIPT PASS | AC converged:',j['AC_converged_casehours'],'| New 12/12 local pass:',j['new_12of12_AC_pass_candidates'],'| Combined 20/20 local pass:',j['all_selected_20of20_pass_candidates'])"
~~~

If the receipt passes:

~~~bat
git status --short
git add -- StudyA_94022_SS90_Remaining3_Pair_AC_v1
git diff --cached --stat
git commit -m "Archive 94022 SS90 three-residual-hour joint 60AC pilot [ci skip]"
git fetch origin
git rebase origin/sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
~~~

Never stage other untracked research outputs. If the pull/rebase has a conflict, stop and share the error. No force push. Do not re-run a previous 8,760 annual AC baseline during this pilot. The next remote independent audit should use the source-parity and violation registers to determine whether a jointly AC-valid candidate is sufficiently robust before reconstructing the **PF.98 corrected annual AC from previous 8760 original rows plus six re-evaluated changed hours**. PF.95 full-year AC remains a separate later sensitivity.

## Research boundaries

The optional stricter V .97..1.03 band was already violated in the original annual model and may worsen with donor shifts. Passing the original main .95..1.05 test under provisional EPM GIS does not validate EPM nameplate, true conductor/neutral/phase arrangements, physical installation or field code compliance. This new local candidate is a controlled chronological redispatch, not an economically optimal PyPSA dispatch.
