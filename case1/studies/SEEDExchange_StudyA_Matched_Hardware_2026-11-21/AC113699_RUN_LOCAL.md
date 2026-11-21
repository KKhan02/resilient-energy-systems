# Study A | 113699 matched-hardware bounded AC pilot

**21 November 2026. Code prepared, no local AC run or annual AC result.**

## Purpose and evidence

This is the next diagnostic gate after the independently audited full 16-case
A0/A1 fixed-hardware 2025 energy comparison. It reuses the preserved
seed_study_a_v6.py, EPM GIS territory builder, pandapower build_net and
solve_ac_hour. There is no new PV/BESS optimization.

The same original equipment is frozen across each A0 versus A1 load pair:

| Hardware origin | PV panels | Deye battery modules | Battery DC kW | Inverter kVA |
| --- | ---: | ---: | ---: | ---: |
| A0 113699 minimum cost | 17 | 3 | 4.700939451 | 5 |
| A1 113699 minimum cost | 20 | 4 | 6.439699033 | 6 |

A0 has H04,H05,H07,H10. A1 adds H03 and H06. The independent source
verification also checks H13 moves from 106039 to 85398. The saved proposed
straight-line service distances to LV taps are H03 57.76m, H06 131.38m and
H13 218.52m. Actual service circuits, EPM permission and phase wiring
are NOT verified. The 113699 nameplate of 3 kVA is an explicit planning
assumption. Existing EPM GIS conductors and provisional service taps remain
separate from the hypothetical A0 94022 five-edge retrofit and 92395 STAR/MST.

Preflight pins the original full 16-case run manifest SHA, audits all 16
per-case receipts and signed dispatches, and independently reconstructs
two GIS territories from source. Both must be connected and radial with
exact named household nodes. No new AC power-flow is solved during preflight.

Pilot stress timestamps are selected deterministically from both load
assignments and all four annual fixed-hardware dispatches. The union contains
at most 36 non-contiguous 2025 hours. Every scenario is tested at the
same timestamps. Per timestamp the runner evaluates:

- Two source-specific load-only AC cases.
- Four fixed-hardware active-power dispatch cases with Q disabled.
- The same four cases with existing daylight reactive control, Q ratio .25,
  nighttime Q disabled.

This is 10 AC result rows per selected hour, with PF 0.98, service length
factor 1.0, head-mounted shared inverter and balanced network proxy. Record
convergence, bus-voltage extrema, transformer/line loading, sampled losses,
and main 0.95..1.05pu and strict 0.97..1.03pu sensitivity screens.
This selected-hour experiment does NOT prove any complete 8760-hour AC pass.

## Commands in original Miniforge Prompt

From the original resilient-energy-systems checkout root:

~~~bat
git status --short
git pull --ff-only origin sync/seedexchange-local-2026-11-17

python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21" -p "test_*.py" -v

python "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21\matched_hardware_ac113699.py" --repo-root . --preflight-only
~~~

Expected preflight status:
SIGNED_113699_AC_SOURCE_GEOMETRY_PREFLIGHT_NO_SOLVES.

Preflight must report four energy cases, two mapped-geometry records,
selected_unique_2025_hours <= 36, and expected_powerflow_cases equal to
selected_unique_2025_hours times 10. The study folder now has 30 synthetic
tests, including eight new AC gate tests. They have NOT yet run on your
Miniforge environment.

After tests and source-only preflight pass, run:

~~~bat
python "case1\studies\SEEDExchange_StudyA_Matched_Hardware_2026-11-21\matched_hardware_ac113699.py" --repo-root .
~~~

The program automatically chooses an unused repo-root output named
StudyA_A0_A1_MatchedHardware_AC113699_Pilot_vN. It writes
RUN_MANIFEST.json, BOUNDED_AC_HOURLY.csv and two PNGs under
figures_diagnostic/. It always preserves annual_AC_feasible=false.
Numerical failures are recorded as bounded diagnostic findings, not
silently counted as passes. If a new exception stops the run, the
output is INCOMPLETE_AC_DIAGNOSTIC_DO_NOT_CLAIM. Preserve it for debugging.

If complete, inspect the actual version and stage ONLY the new folder.
Replace v1 below with the version printed at completion.

~~~bat
set "OUT=StudyA_A0_A1_MatchedHardware_AC113699_Pilot_v1"
git add -- "%OUT%"
git diff --cached --name-only
git diff --cached --stat
git commit -m "Screen 113699 matched A0 A1 bounded AC scenarios [ci skip]"
git pull --rebase origin sync/seedexchange-local-2026-11-17
git push origin sync/seedexchange-local-2026-11-17
git status --short
~~~

Do not stage partially failed output as a successful diagnostic. The assistant
will independently audit the saved results in GitLab before proposing
full-year, PF/length-factor AC runs or AC-aware SOC redispatch. Actual physical
connections, protection, battery/inverter compatibility, network losses
allocation and costs remain separate open evidence gates. Keep main unchanged.
