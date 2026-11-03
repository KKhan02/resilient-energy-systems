# San Rafael Case 1: Canonical dispatch and conditional AC coupling, Phase 2

**Status: implementation package for review. Python unit tests pass, but the full GitLab repository runtime and full-year numerical scenarios have NOT been executed by this package's authoring environment.** Do not describe the numerical output as validated until it has been run and checked in the pinned GitLab environment. These files intentionally do not replace or edit `case1/wp1_v3/model.py`, the historic notebooks, or saved 2026-10-27 studies.

## Scope and decisions

1. Preserve the existing seven candidate households on 94022/node 931076. Compare additions H01, H02 separately (8 houses), and jointly (9 houses) as **hypotheses only**. H01 and H02 could alternatively be on the northern 25 kVA transformer; the assignment must NOT be silently certified.
2. For node 923494/transformer 106039, retain the original twelve candidate properties. EPM has a portal **5 kW** record but no separately verified **5 kVA** nameplate. The fixed 5 kVA constraint in the canonical model is therefore a clearly labeled **hypothetical sensitivity**, not a claim about the actual transformer.
3. Do not subdivide connected households into several transformers, invent poles or transformer coordinates, or assume an LV reconnection has already occurred.
4. Reuse **the existing `case1.wp1_v3.model.dispatch` and `dispatch_cyclic`**; do not implement a new battery rule engine. Operational PV+BESS energy uses original annual v5 NASA-derived DC-PV and 20 fixed-seed synthetic demand signals. Synthetic profiles are ordinally assigned, not meter data.
5. Day (24h), week (168h), month (12 calendar totals) and year (8,760h plus daily/monthly aggregations) derive from the **same uninterrupted hourly SOC trajectory**.
6. Conditional nodal pandapower analysis comes after the annual dispatch. For 94022, reuse `case1/studies/conditional_94022_pv_bess/conditional_powerflow.py`'s provisional radial model and two user-approved distance conventions. For 106039, run explicit **75m/150m/325m equivalent radial-length** sensitivities, because its exact location/cable routes are unavailable. No EPM-certified physical network model is claimed.
7. Battery energy (kWh), battery charge/discharge power (kW), PV (kWp), and inverter (kVA) are **different independent sweep axes**. Preserve zero-ENS, self-sufficiency and economic objectives separately.

## Files

- `run_integrated_dispatch.py`: one scenario using the existing DC-coupled model, outputs `annual_dispatch_8760.csv`, JSON provenance/QA and figures
- `report_timeseries.py`: only aggregates and visualizes; no new dispatch physics
- `run_parameter_sweep.py`: canonical-model hardware parameter grid with rejection reasons and **energy-only** Pareto sensitivity and heatmaps
- `pandapower_handoff.py`: per-house nodal P/Q inputs; does not assert any LV voltage results
- `validate_ac_snapshots.py`: reuses conditional pandapower 94022 and explicitly parametric 106039 for AC power-flow validation; critical-hour or whole-year mode
- `plot_inputs.py`: source-only 2025 synthetic household demand and NASA irradiation monthly figure
- `run_all.py`: one-command five-case campaign plus sweep and conditional handoff
- `test_*.py`: invariant and interface unit tests, using a synthetic mock only for connection tests

## One consolidated local CLI campaign after review

From the **full repository root** where `case1/wp1_v3/model.py` and the original `Energy Community - San Rafael/` data directory exist:

```bash
python -m pytest -q case1/studies/integrated_dispatch_v1/test_*.py
python case1/studies/integrated_dispatch_v1/run_all.py --repo-root . --outdir case1/studies/integrated_dispatch_v1/outputs
```

The shell may not expand `test_*.py` on Windows PowerShell. Use `python -m pytest -q case1/studies/integrated_dispatch_v1/` instead.

For an individual tested configuration:

```bash
python case1/studies/integrated_dispatch_v1/run_integrated_dispatch.py --repo-root . --territory 931076 --panels 24 --battery-modules 4 --battery-power-kw 5 --inverter-kva 10 --soc-mode cyclic --outdir case1/studies/integrated_dispatch_v1/outputs/seven
```

Then perform **conditional** AC validation on its hourly output:

```bash
python case1/studies/integrated_dispatch_v1/validate_ac_snapshots.py --repo-root . --hourly case1/studies/integrated_dispatch_v1/outputs/seven/annual_dispatch_8760.csv --outdir case1/studies/integrated_dispatch_v1/outputs/seven/ac_critical --mode critical
```

Only after reviewing critical snapshot violations should you run `--mode full`. This uses locally installed pandapower and its pinned dependencies, without GitLab shared runners.

## Output interpretation

- `self_sufficiency_pct = 100*(1 - imported/requested demand)`. Always read it alongside ENS. If ENS is nonzero, report additionally served-load self-sufficiency and the fraction of original demand actually supplied locally.
- `fully_grid_independent_and_served` requires both zero import and zero unserved load in a calendar period. Export/import are summed **gross**, not netted monthly.
- `pv_dc_available_kw` is solar DC capability before inverter/curtailment. `pv_ac_kw` is final solar AC injected directly to demand or grid, not battery discharge. Battery DC charging consumes PV before inversion; charging PV is not included in `pv_ac_kw`. `curtailment_kw` is DC, not AC.
- Annual battery SOC starts from the cyclic boundary solution by default. Monthly/daily views do not reset storage at each calendar boundary.
- PCC kVA limits are enforced in the canonical energy model. Passing that internal limit is **not independent AC validation**. Actual pandapower voltage, line and transformer loading must be reported from `ac_validation.csv` with its topology assumptions and ENS.
- The cached October 2026 `annual_shared_pvbess` results use a different dispatch engine. **Do not overwrite them**. They are benchmarks for investigating model differences, not canonical hourly ground truth.
- Equipment costs are historical approximate reference values. Site-specific installation, LV cables, protection, meters, permits, reinforcement and settlement rules are unpriced. **No complete 25-year NPC optimum is claimed**.

## Known design blockers and required next iteration

1. Canonical dispatch presently has no dedicated **zero-export** control input. Do **not** post-process its grid exports to zero while leaving SOC unchanged. Add an explicit inverter/PCC export-cap control to the canonical core and its regression tests before comparing zero-export policies.
2. `wp1_v3.model.dispatch` uses the **5 kVA reference transformer** internally. Different true nameplate ratings, including the northern 25 kVA asset, require a separately validated parameterized canonical limit.
3. The twelve-house node 923494 has no known precise transformer location or certified LV service route. Only explicit parametric AC tests are possible now.
4. The proximity-based **cross-transformer transfer/hosting optimization**, confirmed phase/neutral currents, AC-constrained joint multiobjective PV+BESS sizing and final costs remain follow-on work. A parameter-sweep Pareto is not the joint optimum.
5. Some candidate H IDs may describe facilities rather than residential accounts. Assign actual load classes only when evidence supports them.
6. `case1` pinned old environment must be installed for pandapower; plotting scripts need pandas, matplotlib and NumPy. All studies must be executed once against the exact GitLab `main` revision before results can be released.

## GitLab upload without repeated CI runs

These paths are relative to repository root. Put the complete folder under `case1/studies/` in one batch using the GitLab Web IDE. Create a feature branch, leave the old files intact, and consolidate local tests and scenario results before the final verified CI run. Uploading a ZIP as a single blob is not the same as adding its extracted file tree. Do not use an undocumented pipeline skip for final numerical changes.
