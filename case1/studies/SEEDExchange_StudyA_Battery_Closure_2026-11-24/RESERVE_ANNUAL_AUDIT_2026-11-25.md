# 25 November 2026 | Sizing annual AC and reserve receipt audit
Source user upload cb9b3dfcb0ee37fd649e5315e80034f41c8f2b8b. Read-only independent audit of stored values, not a solver rerun.

- 113699: five annual CSVs, 43,800 rows; exact hourly chronology, no nonfinite checked fields, case/PF/source ID mismatch, main/strict band failure, feasibility mismatch or nighttime-Q violation. Annual min/max voltage, loading, losses and imports reproduce receipt within 6.3e-13 in respective units. All five at PF .98, length x1 only. Manifest records 225 regressions, not independently rerun.
- 94022: three annual reserve schedules, 26,280 rows, matched released source demand and PV availability exactly; max balance residual 1.43e-10 across AC/DC/PV/cyclic SOC (CSV precision). All 15 corridor points satisfy bounds; sampled schedule P matches within 5e-11 kW. All 102 sampled AC records converge, feasibility flags match strict thresholds; reference 51/51 pass, stress 28/51 pass. 394 probes converge. 13 near-boundary probe flags differ from exact .95 cutoff by less than 1e-6 pu; chosen reserve points have positive margin, no sampled reference failure. Do not infer field validity or exact continuous feasibility from finite probes.
- Sep 24 19:00 and 20:00 stress: no tested feasible power up to zero-export ceiling; best sampled min voltage .949061727 and .944435685 pu respectively. Keep stress unresolved, not proof of impossibility for all network/control designs.
- No independent SHA-256 byte audit in assistant environment; local preflight validates signed inputs. No new LP/AC executed. Annual replay source added with 5 synthetic tests, user execution pending. Preserve all original outputs.
- Next: annual reference replay for all three 94022 reserve cases, 26,280 AC hours and 51 sample regressions. No new LP. Follow with nine-factor checks as warranted and engineering discussion of stress cases; do not silently change topology, Q policy, physical assumptions or tariff. Retain five 113699 alternatives and full Study A scope.

## Miniforge
From repo root on sync branch after clean-status check and fast-forward pull:
```bat
set "RUN=case1\studies\SEEDExchange_StudyA_Battery_Closure_2026-11-24"
python -m unittest discover -s "%RUN%" -p "test_reserve_reference_annual.py" -v
python "%RUN%\reserve_reference_annual.py" --repo-root . --preflight-only
python "%RUN%\reserve_reference_annual.py" --repo-root . --out StudyA_94022_Sizing_Reserve_AnnualAC_v1
```
Stop on failure. Output manifest must show complete reference annual replay; inspect pass/failure independently before claiming feasible. Stage only new output directory and push to sync. 
