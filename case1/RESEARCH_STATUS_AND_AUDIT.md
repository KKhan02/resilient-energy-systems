# SEEDExchange research status and independent review
**Revision:** 2026-11-03. **Scope:** Current work after local runs uploaded on commit 5d6df2d2. This is a progress note, not an equipment certification.

## Current sequence and verified evidence

1. **Data and geography:** NASA POWER 2025 solar resource, modelled synthetic hourly demand, 35 user-mapped properties and EPM GIS transformer/LV segment records.
2. **Joint capacity/energy optimization:** 6,840 reported PyPSA/Linopy tasks (6,820 optimal model solutions; 20 infeasible). The complete-study driver uses discrete panel/battery/inverter choices and optimizes hourly storage charging, discharging and SOC. **Perfect foresight = yes:** all 8,760 hours are visible to the solver at once. These schedules are idealized planning benchmarks, not an operational forecasting algorithm or causal control.
3. **Separate continuous runs:** Earlier `outputs/twelve_economic_5kva_zero/model_manifest.json` explicitly has `discrete:false`, yielding fractional equipment equivalents. Do not mix those continuous-relaxation choices with buildable MILP panel/module counts.
4. **Independent AC evaluation:** Representative 5–15-house feeder, then synthetic geographic networks, then EPM GIS conductor/node topology. Aggregate PCC kVA is not equivalent to full AC voltage and thermal feasibility.
5. **Reactive-power control:** HIL Volt–Var, transformer Q-guard, and coordinated AC Q search. These stages hold PyPSA *active dispatch fixed*; they do not independently redispatch battery energy.
6. **Annual result:** 106039 at head, household PF 0.98, service factor 1.0, Q ratio 0.25 reports 8,760 converged and feasible hours. Worst LV voltage 0.970005 pu is virtually at the 0.97 limit. Stress cases and 94022 have remaining violations; the representative EPM feeder is a balanced equivalent with assumed service drops, ratings and nighttime inverter VAR ability.

## Independent consolidated review: interpretation and remaining gates

The 24 October review's red-test-first B01/B11 correction and B02/B04 time/backlog fixes refer to the historical `case1/wp1_v3` causal dispatch engine. Those are separate from the later PyPSA MILP and EPM GIS models. The reviewed G2/G3 fixes include deterministic pvlib handling, SOC boundary diagnostics, cost replacement logic, plot eligibility and pinned core/legacy dependencies. Preserve that history.

**Legacy frozen result warning.** `case1/results/RUN_MANIFEST.json` still declares `independent_NOAA_Erbs_approximation_UNVERIFIED` and `pandapower_validation: NOT_RUN`. These refer to the historic v3 saved result set. The reported 3,909 versus 3,599 filtered count mismatch deserves separate regeneration/reconciliation; none of these old numbers should override the 6,840-task MILP outputs. Keep historical files for audit, but classify the older headline plots as superseded, not current evidence.

**Battery throughput and power scope.** The original v3 headline sweep still may impose an explicit 5 kW battery power scenario, even where component datasheets allow more. The later PyPSA MILP includes a separate battery power variable with a zero incremental power-cost proxy, which may make marginal power economically degenerate; verify equipment power/cost assumptions before treating them as purchase specifications.

**Finite-horizon foresight.** The MILP hourly schedule uses perfect knowledge of future PV and demand and typically cyclic SOC. Do not present its self-sufficiency or peak-reduction as achieved by a forecasting-free controller; use it as a planning benchmark. For practical operation compare causal control and forecast uncertainty. A labelled `perfect_foresight: true` field belongs in future-generated manifests.

**Old screened kVA ceiling.** When the v3 `_core` already enforces 4.5 kVA, an additional 4.5 kVA post-filter is not an independent electrical validation. The EPM pandapower studies supply genuinely separate, conditional AC evidence, but retain their own feeder uncertainties.

**Model engines are not interchangeable.** The historical `annual_shared_pvbess/annual_screen.py` uses different charge/discharge coupling and power checks from `wp1_v3._core` and the new DC-coupled MILP. Do not combine quantitative outputs without reconciling energy balances, conversion efficiencies and costs on the same inputs.

**CI status:** The recent large 5d6df2d push explicitly used [ci skip]. The earlier green pipeline on the older 1fdf097 commit does not cover the later 6,840-run source drop. This update also intentionally skips CI at the user's request. Local simulation convergence and unit tests support reported outputs, but CI verification of the new sources is still outstanding. No GitHub Actions workflow is required for a GitLab-hosted repository.

**Numerical reproducibility:** Keep original `outputs/full_study/` CSVs, checkpoint and manifests. Treat archived ZIPs as file transfers, not authoritative source. Git moves keep historical blobs and do not reduce repository storage. New online changes here are documentation and curation only, with no rerun or altered simulation outputs.

## Next research, incomplete

- Chronological **AC-constrained active-power battery redispatch** with SOC, power, energy, inverter kVA and no load omission, then re-evaluate costs and ENS.
- Verify conductor impedances/current ratings, actual phase connections and nighttime reactive-power support.
- Test the successful design against uncertain solar and demand realizations, lower PF, route lengths and outages.
- Assess resilience and adaptability only after the network-constrained baseline is established.

[Professor walkthrough](professor_walkthrough/README.md) provides the numbered figure narrative.
