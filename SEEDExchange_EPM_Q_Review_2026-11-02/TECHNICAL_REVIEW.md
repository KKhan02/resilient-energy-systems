# EPM GIS + HIL Volt–Var: AC validation review

## Source files and execution

- `epm_gis_q_results.zip` is the 24-scenario baseline (960 converged critical-hour solves), service multiplier 1.0, load PF 0.98, four controller modes (unity, fixed-PF inject, fixed-PF absorb, Volt–Var), three sites, two territories.
- Separately uploaded `ac_scenario_summary.csv` and `ac_hours.csv` represent the expanded sensitivity: 144 scenarios, 5,760 converged critical-hour solves, two controls, two Q ratios, load PF 0.90/0.98, three service-drop multipliers 1.0/1.3/1.6, three sites and two territories.
- Matching unity and Volt–Var 0.48 cases at PF 0.98, factor 1.0 are identical between uploads. Do **not** add the 960 to the 5,760 as 6,720 independent unique experiments: the latter includes equivalent cases.
- `strict_pass` is false for all 24 baseline and all 144 sensitivity scenarios. These use selected hours, not 8,760-hour annual checks.

## HIL control implementation

- Volt–Var breakpoints U1=0.96, U2=0.99, U3=1.01, U4=1.04 pu. Positive Q is sgen injection.
- Q capability = min(q_ratio × installed active-power rating, sqrt(S_rated² − P²)). Inverter ratings 10 kVA (94022), 12 kVA (106039), while modeled transformer ratings are 5 kVA each.
- Hourly cases use settled local-voltage Q(U) control, not the available 10 s first-order transient.
- Fixed-PF injection/absorption in the baseline uses inverter PF 0.98. Household load PF is 0.98 in baseline and either 0.98 or 0.90 in sensitivity.

## Baseline PF 0.98: voltage/reactive trade-off

| Transformer | Siting | Unity Vmin | Volt–Var Vmin | Unity Vmax | Volt–Var Vmax | Unity peak trafo | Volt–Var peak trafo |
|---|---|---:|---:|---:|---:|---:|---:|
| 94022 | head | 0.9500 | 0.9548 | 0.9978 | 0.9978 | 91.2% | 88.5% |
| 94022 | middle | 0.9500 | 0.9654 | 1.0107 | 1.0073 | 91.2% | 95.5% |
| 94022 | end | 0.9500 | 0.9573 | 1.0853 | 1.0446 | 91.2% | 125.8% |
| 106039 | head | 0.9580 | 0.9638 | 0.9981 | 0.9981 | 94.2% | 91.2% |
| 106039 | middle | 0.9595 | 0.9673 | 1.0316 | 1.0173 | 94.0% | 96.4% |
| 106039 | end | 0.9595 | 0.9463 | 1.0912 | 1.0468 | 94.0% | 150.6% |

### Interpretation

- Midpoint Volt–Var at Q ratio 0.48 improves minimum voltage for 94022 from 0.9500 to 0.9654 pu and for 106039 from 0.9595 to 0.9673 pu, but neither meets the 0.97 pu strict minimum. For 106039, midpoint Volt–Var also reduces Vmax from 1.0316 to 1.0173 pu.
- End Volt–Var at Q ratio 0.48 reduces Vmax for 106039 from 1.0912 to 1.0468 pu, but peak transformer loading jumps from 94.0% to 150.6%, with average selected-hour losses from 0.210 to 0.584 kW. For 94022 end, maximum voltage falls from 1.0853 to 1.0446 pu, but loading rises from 91.2% to 125.8%.
- Q ratio 0.25 is often less stressful, though no tested configuration passes all strict limits. More available Q is not automatically better because it increases reactive currents and transformer MVA.
- Peak minimum/maximum voltage and peak transformer loading may occur at different hours. These extrema must not be treated as one simultaneous operating point. Violations count *sampled scenario-hours*, not annual violations.
- There is no feeder-level optimum identified by this study. The controller and location should be judged by voltage, loading, losses and inverter Q headroom together.

## Model limitations

The supplied manifest describes a *balanced three-phase equivalent for a single-phase rural LV feeder*, ideal upstream MV source, approximate conductor R/X and ampacity, assumed service connections based on LV GIS proximity, fixed PyPSA hourly active dispatch and a single combined PV/BESS inverter. Actual consumer connections and cable electrical parameters remain unverified, and transformer 92395 has no linked LV backbone. No full-year voltage-control performance or project-wide resilience result is established.

## Recommended next stage

1. Prefer midpoint and transformer-head Volt–Var configurations for further investigation; retain end placement as a stress case, not a recommended final design.
2. Implement a joint reactive-power constraint that screens the **transformer apparent power** during every Q iteration, not merely the inverter kVA circle. Include voltage-dependent Q-limiting, anti-windup/saturation and explicit curtailment or unserved-demand flags where required.
3. Compare Q ratios 0, 0.25 and 0.48 with a constrained controller, then test dynamic stability separately from hourly steady-state checks. Examine 0.90 load-PF stress carefully.
4. If controls alone do not meet voltage and loading criteria, evaluate relocating/sectioning PV+BESS, network reinforcement, service topology sensitivity, and re-optimization of the energy dispatch under AC constraints.
5. Run 8,760-hour pandapower validation only on shortlisted *electrically eligible* designs. Keep resilience/adaptability after AC-constrained designs are established.

## Figures

All figures are unconnected scatter plots intended for a technical poster. Figures 01–04 show PF 0.98 and service factor 1.0; Fig. 05 shows the sensitivity of assumed service-drop lengths at midpoint placement.
