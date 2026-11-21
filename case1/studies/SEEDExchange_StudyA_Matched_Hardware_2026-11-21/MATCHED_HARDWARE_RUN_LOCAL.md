# Matched-hardware A0/A1 Study A pilot | 21 November 2026

**Status:** Controlled experiment prepared. This pilot is **not executed yet** and
it does not validate feeder AC or complete the 34-house comparison.

## Why this control matters

The existing 34-house A0/A1 research results pair equal total population and
2025 demand, but select different equipment by territory. They cannot isolate
whether technical and cost differences result from geography or different
PV/BESS/inverter selections.

A properly matched-hardware experiment freezes all **four** equipment fields
at a named transformer: PV panel count, battery modules, battery DC power,
and inverter kVA. It then changes **only which already signed households**
the transformer serves and re-solves the entire annual chronological 2025
PyPSA fixed-hardware model. At a given transformer, modelled source rating,
physical SOC minimum (20%), zero grid export and zero unserved demand are
also held fixed. The resulting same-device AC trajectories must eventually
be tested on each assignment's own *provisional feeder geometry*, not
transferred from a different cohort.

## First source-pinned pilot

| Attribute | Original signed donor | New controlled recipient |
| --- | --- | --- |
| Assignment | A1 | A0 |
| EPM transformer | 113699 | 113699 |
| House count | 6 | 4 |
| Houses | H03,H04,H05,H06,H07,H10 | H04,H05,H07,H10 |
| PV | 20 panels (8.700 kWp) | same |
| Deye battery | 4 modules | same |
| Battery DC power limit | 6.439699 kW | same |
| Inverter | 6 kVA | same |
| Transformer | 3 kVA planning assumption | same |

The donor full-year signed energy file already exists:
`case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/pvbess_phase_01/energy_A1_113699_min_cost_ref`.
Its recorded modelled 2025 annual imports are **2,393.727936 kWh** for
11,388 kWh of six-house demand. Those figures are source inputs, **not
predictions for the new A0 four-house pilot**. The new four-house energy
and cost numbers will be calculated only by the user-local fixed-hardware LP.

## Reproduction from Miniforge Prompt

From the original repository checkout on
`sync/seedexchange-local-2026-11-17`:

~~~bat
git status --short
git pull --ff-only origin sync/seedexchange-local-2026-11-17
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21" -p "test_*.py" -v
python "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21\matched_hardware_pilot.py" --repo-root . --preflight-only
~~~

Preflight required status:
`SIGNED_MATCHED_HARDWARE_PILOT_PREFLIGHT_PASS_NO_SOLVE`.
It reads and checks original source signatures and both membership/solar
time series and writes nothing.

Only if preflight passes, run the limited 8,760-hour energy model:

~~~bat
python "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21\matched_hardware_pilot.py" --repo-root .
~~~

Output chooses an unused
`StudyA_A0_A1_MatchedHardware_113699_Pilot_vN` at repo root.
Required final state:
`ENERGY_ONLY_MATCHED_HARDWARE_PILOT_PASS_AC_PENDING`.
Read `RUN_MANIFEST.json` and `energy_hourly_2025.csv` and **never
call this an AC-feasible annual design**.

After inspecting a completed source-signed result, stage **only** that
successful output folder, replacing vN with the actual printed version:

~~~bat
git add "StudyA_A0_A1_MatchedHardware_113699_Pilot_vN"
git diff --cached --name-only
git diff --cached --stat
git commit -m "Test matched A1 hardware on A0 113699 cohort energy [ci skip]"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
~~~

If the solver is infeasible, preserve diagnostics and do **not** push as
a successful case. Source hardware may not support the receiving load.
That outcome is scientifically relevant and calls for a physically
constrained hardware alternative, not an assumed feasible dispatch.

## Remaining reciprocal controlled design

Once the pilot passes and is independently audited on GitLab,
compare both directions: freeze original A0 equipment across A0/A1,
and separately freeze original A1 equipment across A0/A1, for 94022,
106039, 113699 and 85398 in both minimum-cost and SS90 source tiers.
That is at most 16 new annual fixed-equipment dispatch jobs (some
cases may be provably source-identical and reused), not another 6,840
MILP investment search. The common 92395 four-house STAR installation
and energy schedule remain exactly the same in both and are not run
again. Report **two controlled 34-house comparisons per tier**, plus
the existing architecture-specific matched-population comparison.

After full energy/source QA, screen changed electrical injection hours,
run controlled stress AC and then the required source-stitched annual
PF and service-length comparisons; use the original unchanged pandapower
solver. Do not transfer earlier SOC-aware redispatch schedules from a
different hardware/load case without solving and signing them again.

## Corrected AC losses and physical evidence

The previous aggregate original-network loss screen exists at
`case1/studies/SEEDExchange_StudyA_Utilization_Frontier_v1/A0_A1_EQUAL_POPULATION_ENERGY_COST_SCREEN.csv`.
It contains **original dispatch** losses, not equal-hardware post-redispatch
losses, and must not be mislabelled. The source A1 342 corrected-hour
audit CSV has min voltage and transformer loading, **not loss_kw**.
The stored A0 and 94022 summary-only shift records also cannot justify
a new annual loss sum without same-hour old/new AC loss evidence.
Next work should first inventory existing signed changed-hour solver CSV
archives for loss_kw and overlay those only when exact original and
changed provenance matches. Otherwise generate a bounded same-hour
pandapower loss replay. Keep ownership/payment of electrical losses
separate from the original $0.29/kWh import bill.

No field measurements, conductor quotations, protection approval,
actual H01/H06 service attachments or 92395 existing LV backbone have
been independently obtained. The proposed 92395 STAR and MST belong
to Study B; northern 25 kVA transformer is outside scope.
