"""
Case 1 pipeline: run every study and write the result tables.

Order follows the objectives:

  0  provenance and baseline validation
  1  reference case: v18 constraint vs the Case 1 5 kVA constraint
  2  transformer constraint sensitivity              (objective 3)
  3  PV / BESS / inverter oversizing grid            (objective 2)
  4  BESS energy vs BESS power                       (objective 2)
  5  economically useful size                        (objective 4)
  6  control strategy comparison                     (objective 6)
  7  vulnerability and adaptive resilience           (objectives 5, 7, 8)
  8  demand-realization uncertainty
  9  pandapower electrical feasibility               (objective 3)
 10  run manifest

Every table is written to `results_case1/` as CSV. Nothing is printed that
is not also saved.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, replace

import numpy as np
import pandas as pd

from . import economics as E
from . import grid_check as G
from . import kpi as K
from . import rule_dispatch as RD
from . import stress as S
from . import sweeps as SW
from .config import Case1Config, provenance_table
from .demand import build_reference_load_8760, group_load_kw
from .lp_model import SystemSpec
from .study import Case1Study

DECISION_CONTROL = "ADAPTIVE_PLUS_LM"
REFERENCE_CONTROL = "CONVENTIONAL"


def _log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


# ---------------------------------------------------------------------------
# Candidate systems
# ---------------------------------------------------------------------------


def candidate_specs(cfg: Case1Config, houses: int = 4) -> list[SystemSpec]:
    """
    Representative systems used for the control and resilience comparisons.

    Inverter choice follows the Deye datasheet: 12 and 16 panels fit the
    quoted SUN-5K (7.5 kWp DC input); 20 and 24 panels require a larger unit
    from the same split-phase family.
    """
    return [
        SystemSpec(label="REF_12P_4B_5K", houses=houses, panel_count=12,
                   bess_modules=4, inverter_key="SUN-5K"),
        SystemSpec(label="OS_16P_4B_5K", houses=houses, panel_count=16,
                   bess_modules=4, inverter_key="SUN-5K"),
        SystemSpec(label="OS_16P_8B_5K", houses=houses, panel_count=16,
                   bess_modules=8, inverter_key="SUN-5K"),
        SystemSpec(label="OS_20P_8B_8K", houses=houses, panel_count=20,
                   bess_modules=8, inverter_key="SUN-8K"),
        SystemSpec(label="OS_24P_8B_12K", houses=houses, panel_count=24,
                   bess_modules=8, inverter_key="SUN-12K"),
    ]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


@dataclass
class Case1Results:
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    notes: dict[str, object] = field(default_factory=dict)

    def add(self, name: str, table: pd.DataFrame) -> pd.DataFrame:
        self.tables[name] = table
        return table

    def save(self, cfg: Case1Config) -> list[str]:
        paths = []
        for name, table in self.tables.items():
            path = cfg.paths.results_dir / f"{name}.csv"
            table.to_csv(path, index=False)
            paths.append(str(path))
        return paths


def run_case1(cfg: Case1Config | None = None,
              study: Case1Study | None = None,
              run_validation: bool = True,
              run_annual_power_flow: bool = False,
              full_outage_grid: bool = False,
              houses: int = 4) -> Case1Results:
    cfg = cfg or Case1Config()
    cfg.paths.ensure()
    st = study or Case1Study(cfg)
    results = Case1Results()
    homer = st.homer
    profile = st.decision_profile

    # ---- 0. provenance and validation ----------------------------------
    _log("0. provenance and baseline validation")
    results.add("parameter_provenance", provenance_table())
    results.add("homer_reference_context", st.homer_context().reset_index(
        names="metric"))
    results.add("resource_diagnostics", st.resource_diagnostics())
    results.add("demand_summary", st.demand_summary())
    results.add("inverter_family", _inverter_family_table(cfg, homer))

    if run_validation:
        from .validation import run_validation as _run_validation
        results.add("baseline_validation",
                    _run_validation(cfg, st, include_sweeps=True, verbose=True))

    # ---- 1. reference case under both constraint models ----------------
    _log("1. reference case: v18 constraint vs Case 1 5 kVA constraint")
    results.add("reference_constraint_comparison",
                _reference_constraint_comparison(st, houses))

    # ---- 2. transformer sensitivity ------------------------------------
    _log("2. transformer constraint sensitivity")
    results.add("transformer_sensitivity",
                SW.transformer_sensitivity(
                    st, control=REFERENCE_CONTROL,
                    houses_list=tuple(cfg.demand.house_group_size_sweep)))

    # ---- 3. oversizing grid --------------------------------------------
    _log("3. oversizing grid: PV x BESS x inverter")
    grid = SW.oversizing_grid(
        st, houses=houses, control=REFERENCE_CONTROL,
        bess_modules=cfg.hardware.bess_module_sweep)
    results.add("oversizing_grid", grid)

    _log("3b. oversizing grid under export restriction")
    export_grid = SW.oversizing_grid(
        st, houses=houses, control=REFERENCE_CONTROL,
        panel_counts=cfg.hardware.panel_count_sweep,
        bess_modules=(4, 8), inverter_keys=("SUN-8K",),
        export_limits_kw=(0.0, 1.5, 3.0, None))
    results.add("oversizing_export_restricted", export_grid)

    _log("3c. curtailment attribution")
    curtail_rows = []
    for spec in candidate_specs(cfg, houses):
        system = st.resolve(spec)
        if not system.hardware_feasible:
            continue
        for export_limit in (None, 0.0):
            table = SW.curtailment_breakdown(
                st, spec, control=REFERENCE_CONTROL,
                export_limit_kw=export_limit)
            table["export_control_kw"] = (
                export_limit if export_limit is not None
                else system.export_limit_kw)
            curtail_rows.append(table)
    results.add("curtailment_attribution", pd.concat(curtail_rows,
                                                     ignore_index=True))

    # ---- 4. BESS energy vs BESS power ----------------------------------
    _log("4. BESS energy vs BESS charge/discharge power")
    results.add("battery_energy_vs_power",
                SW.battery_power_study(st, houses=houses,
                                       control=REFERENCE_CONTROL))

    # ---- 5. economically useful size -----------------------------------
    _log("5. economically useful size under both compensation regimes")
    pv_tables, bess_tables = [], []

    for regime in E.COMPENSATION_REGIMES:
        pv_marginal, pv_useful = SW.pv_marginal_study(
            st, houses=houses, control=REFERENCE_CONTROL,
            compensation_regime=regime)
        pv_tables.append(pv_marginal)
        results.notes[f"pv_useful_size_{regime}"] = pv_useful

        bess_marginal, bess_useful = SW.bess_marginal_study(
            st, houses=houses, control=REFERENCE_CONTROL,
            compensation_regime=regime)
        bess_tables.append(bess_marginal)
        results.notes[f"bess_useful_size_{regime}"] = bess_useful

    results.add("pv_marginal_value", pd.concat(pv_tables, ignore_index=True))
    results.add("bess_marginal_value", pd.concat(bess_tables, ignore_index=True))

    if cfg.economics.run_tariff_sensitivity:
        _log("5b. tariff sensitivity")
        results.add("tariff_sensitivity",
                    _tariff_sensitivity(st, houses, REFERENCE_CONTROL))

    # ---- 6. control comparison -----------------------------------------
    _log("6. control strategy comparison")
    specs = candidate_specs(cfg, houses)
    comparison = SW.control_comparison(st, specs)
    results.add("control_comparison", comparison)

    # ---- 7. vulnerability ----------------------------------------------
    _log("7. vulnerability and adaptive resilience")
    scenario_rows = []
    for spec in specs:
        system = st.resolve(spec)
        if not system.hardware_feasible:
            continue
        scenarios = (
            S.build_scenario_set(st, profile, houses,
                                 outage_months=tuple(range(1, 13)),
                                 outage_hours=cfg.stress.outage_sample_hours)
            if full_outage_grid
            else S.build_scenario_set(st, profile, houses)
        )
        for control in RD.CONTROLLERS:
            params = RD.ControlParams.from_config(
                control, cfg,
                export_limit_kw=1.5 if control == "EXPORT_LIMITED" else None)
            runner = S.ResilienceRunner(st, system, params, profile, houses)
            for scenario in scenarios:
                metrics, _ = runner.run(scenario)
                metrics["system"] = spec.label
                scenario_rows.append(metrics)
        _log(f"   {spec.label}: {len(scenarios)} scenarios x "
             f"{len(RD.CONTROLLERS)} controllers")

    scenario_results = pd.DataFrame(scenario_rows)
    results.add("vulnerability_scenarios", scenario_results)

    family_rows = []
    for system_label, group in scenario_results.groupby("system", sort=False):
        summary = S.summarise_by_family(group)
        summary.insert(0, "system", system_label)
        family_rows.append(summary)
    family_summary = pd.concat(family_rows, ignore_index=True)
    results.add("vulnerability_by_family", family_summary)

    index_rows = []
    for system_label, group in family_summary.groupby("system", sort=False):
        ranked = S.vulnerability_index_both(group)
        ranked.insert(0, "system", system_label)
        index_rows.append(ranked)
    results.add("vulnerability_index", pd.concat(index_rows, ignore_index=True))

    # ---- 8. demand-realization uncertainty -----------------------------
    _log("8. demand-realization uncertainty on the causal controller")
    results.add("demand_uncertainty",
                _demand_uncertainty(st, houses, DECISION_CONTROL,
                                    specs[0], specs[-1]))

    # ---- 9. pandapower electrical feasibility --------------------------
    _log("9. pandapower electrical feasibility screen")
    bundles = []
    dispatches = {}
    for spec in specs:
        system = st.resolve(spec)
        if not system.hardware_feasible:
            continue
        for control in (REFERENCE_CONTROL, DECISION_CONTROL):
            _, dispatch = SW.run_system(
                st, spec, control=control, houses=houses,
                with_economics=False, return_dispatch=True)
            label = f"{spec.label}|{control}"
            dispatches[label] = dispatch
            bundles.append((label, houses, system, dispatch))

    feasibility = G.feasibility_screen(cfg, st, bundles)
    results.add("network_feasibility", feasibility)

    _log("9a. export-control counterfactual: controlled vs uncontrolled export")
    results.add("network_export_control_counterfactual",
                _export_control_counterfactual(cfg, st, houses))

    _log("9b. inverter power-factor sensitivity at the worst export hour")
    results.add("inverter_pf_sensitivity",
                _inverter_pf_sensitivity(cfg, st, bundles))

    _log("9c. network critical hours")
    critical_rows = []
    for label, houses_i, system, dispatch in bundles:
        hours = G.critical_hours(dispatch)
        table = G.run_dispatch_hours(cfg, dispatch, st.ts, houses_i,
                                     list(hours.values()), scenario=label)
        table["critical_condition"] = list(hours.keys())
        table["case"] = label
        critical_rows.append(table)
    results.add("network_critical_hours", pd.concat(critical_rows,
                                                    ignore_index=True))

    if run_annual_power_flow:
        _log("9d. annual power flow for the reference and recommended systems")
        annual_rows = []
        for label in (f"{specs[0].label}|{REFERENCE_CONTROL}",
                      f"{specs[-1].label}|{DECISION_CONTROL}"):
            if label not in dispatches:
                continue
            table = G.run_annual_from_dispatch(
                cfg, dispatches[label], st.ts, houses, scenario=label)
            table["case"] = label
            annual_rows.append(table)
        if annual_rows:
            annual = pd.concat(annual_rows, ignore_index=True)
            results.add("network_annual", annual)
            results.add("network_annual_summary", pd.DataFrame([
                {"case": case, **G.summarise_network_results(group, cfg)}
                for case, group in annual.groupby("case", sort=False)
            ]))

    # ---- 10. manifest ---------------------------------------------------
    _log("10. run manifest")
    results.add("run_manifest", _manifest(cfg, st, results))

    paths = results.save(cfg)
    _log(f"wrote {len(paths)} tables to {cfg.paths.results_dir}")
    return results


# ---------------------------------------------------------------------------
# Study helpers
# ---------------------------------------------------------------------------


def _inverter_family_table(cfg: Case1Config, homer: dict) -> pd.DataFrame:
    """Datasheet limits of the Deye split-phase family, as modelled."""
    from .config import INVERTER_FAMILY

    rows = []
    for key, model in INVERTER_FAMILY.items():
        max_panels = int(np.floor(
            model.max_pv_dc_kw / (cfg.hardware.module.rated_w / 1000.0)))
        rows.append({
            "key": key,
            "model": model.name,
            "rated_ac_kw": model.rated_ac_kw,
            "max_apparent_kva": model.max_apparent_kva,
            "max_pv_dc_kw": model.max_pv_dc_kw,
            "max_panels_435w": max_panels,
            "max_battery_current_a": model.max_battery_current_a,
            "battery_port_kw_at_48v": model.battery_power_kw(
                homer["battery_nominal_v"]),
            "max_ac_current_a": model.max_ac_current_a,
            "pf_adjust_min": model.pf_adjust_min,
            "quoted_unit": key == cfg.hardware.inverter_key,
        })
    return pd.DataFrame(rows)


def _reference_constraint_comparison(st: Case1Study, houses: int) -> pd.DataFrame:
    """
    The reference 12-panel / 4-battery system under:
      * the v18 constraint (5 kVA read as 5 kW active, DC-side inverter limit)
      * the Case 1 constraint (derated apparent-power envelope, AC-side limit)
    each with the LP bound and the causal controller.

    This isolates the effect of correcting the transformer constraint from
    every other Case 1 change.
    """
    from .validation import v18_spec

    rows = []

    # The reference size, where the constraint is not expected to bind, and
    # an oversized case where it is, so the comparison shows both.
    sizes = [
        ("reference 12 panels / 4 modules", 12, 4, "SUN-5K"),
        ("oversized 20 panels / 8 modules", 20, 8, "SUN-8K"),
    ]

    for size_label, panels, modules, key in sizes:
        v18 = v18_spec(f"V18_{panels}P", houses=houses, panels=panels,
                       bess=modules)
        case1 = SystemSpec(label=f"CASE1_{panels}P", houses=houses,
                           panel_count=panels, bess_modules=modules,
                           inverter_key=key)
        # The v18 constraint model also used a 5 kW converter, so hold the
        # inverter at the Case 1 rating to isolate the transformer change.
        v18 = replace(v18, inverter_ac_kw=case1.inverter_ac_kw
                      or st.cfg.hardware.inverter(key).rated_ac_kw)

        for label, spec in (
            ("v18 constraint (5 kW active, DC-side inverter limit)", v18),
            ("Case 1 constraint (5 kVA derated, AC-side inverter limit)", case1),
        ):
            system = st.resolve(spec)
            if not system.hardware_feasible:
                continue
            lp = SW.run_system_lp(st, spec)
            lp.update({"constraint_model": label, "size": size_label})
            rows.append(lp)

            causal = SW.run_system(st, spec, control=REFERENCE_CONTROL,
                                   houses=houses)
            causal.update({"constraint_model": label, "size": size_label})
            rows.append(causal)

    table = pd.DataFrame(rows)
    columns = [
        "size", "constraint_model", "control", "engine", "perfect_foresight",
        "import_limit_kw", "export_limit_kw", "inverter_ac_kw",
        "self_sufficiency_pct", "net_grid_independence_pct",
        "grid_import_kwh", "grid_export_kwh", "pv_used_kwh",
        "pv_curtailed_kwh", "battery_throughput_kwh",
        "peak_import_kw", "peak_export_kw",
        "transformer_peak_loading_pct_estimate",
        "hours_at_import_limit", "hours_at_export_limit",
        "unserved_energy_kwh", "annualized_total_cost_usd", "lcoe_usd_per_kwh",
    ]
    return table[[c for c in columns if c in table.columns]]


def _tariff_sensitivity(st: Case1Study, houses: int,
                        control: str) -> pd.DataFrame:
    """Optional: how the useful PV size moves with the purchase tariff."""
    cfg = st.cfg
    rows = []
    for tariff in cfg.economics.tariff_sensitivity_usd_per_kwh:
        for panels in cfg.hardware.panel_count_sweep:
            spec = SystemSpec(label=f"TARIFF_{tariff:.3f}_PV{panels}",
                              houses=houses, panel_count=panels,
                              bess_modules=4, inverter_key="SUN-12K")
            system = st.resolve(spec)
            if not system.hardware_feasible:
                continue
            kpi = SW.run_system(st, spec, control=control, houses=houses,
                                tariff_usd_per_kwh=tariff)
            kpi["tariff_case_usd_per_kwh"] = tariff
            rows.append(kpi)

    table = pd.DataFrame(rows)
    out = []
    for tariff, group in table.groupby("tariff_case_usd_per_kwh", sort=True):
        marginal = E.marginal_value_table(group, "panel_count", cfg)
        marginal["tariff_case_usd_per_kwh"] = tariff
        out.append(marginal)
    return pd.concat(out, ignore_index=True)


def _demand_uncertainty(st: Case1Study, houses: int, control: str,
                        reference_spec: SystemSpec,
                        oversized_spec: SystemSpec,
                        realizations: int | None = None) -> pd.DataFrame:
    """
    Re-draw the stochastic demand model and re-run the causal controller.

    The PV resource and the hardware are held fixed, so the spread is purely
    demand-realization uncertainty within the HOMER stochastic-load
    formulation. It does not make independent hourly noise a measured
    household-load model.
    """
    cfg = st.cfg
    realizations = realizations or cfg.stress.mc_solved_realizations
    seeds = [int(child.generate_state(1, dtype=np.uint32)[0])
             for child in np.random.SeedSequence(
                 cfg.stress.mc_base_seed).spawn(realizations)]

    rows = []
    for spec in (reference_spec, oversized_spec):
        system = st.resolve(spec)
        if not system.hardware_feasible:
            continue
        params = RD.ControlParams.from_config(control, cfg)
        pv = st.decision_profile.dc_kw(system.pv_kwp)

        for realization, seed in enumerate(seeds, start=1):
            ts = build_reference_load_8760(
                st.homer, cfg.demand, cfg.site.model_year,
                seed=seed, profile_house_count=max(houses, 4))
            load = group_load_kw(ts, houses)
            dispatch = RD.simulate(load, pv, system, cfg, st.homer, params)
            kpi = K.compute_kpis(dispatch, cfg, st.homer, system.as_row(),
                                 spec.label, control)
            kpi["realization"] = realization
            kpi["stochastic_seed"] = seed
            rows.append(kpi)

    raw = pd.DataFrame(rows)
    metrics = ["self_sufficiency_pct", "grid_import_kwh", "grid_export_kwh",
               "pv_curtailment_pct", "battery_throughput_kwh",
               "peak_import_kw", "peak_export_kw",
               "transformer_peak_loading_pct_estimate"]

    out = []
    for case, group in raw.groupby("case", sort=False):
        for metric in metrics:
            series = group[metric].astype(float)
            out.append({
                "case": case,
                "control": control,
                "metric": metric,
                "realizations": int(len(series)),
                "mean": float(series.mean()),
                "std": float(series.std(ddof=1)),
                "p05": float(series.quantile(0.05)),
                "p50": float(series.quantile(0.50)),
                "p95": float(series.quantile(0.95)),
                "min": float(series.min()),
                "max": float(series.max()),
            })
    return pd.DataFrame(out)


def _export_control_counterfactual(cfg: Case1Config, st: Case1Study,
                                   houses: int) -> pd.DataFrame:
    """
    The central test for objective 3.

    Each PV size is run twice:

      CONTROLLED    export is held inside the derated transformer envelope,
                    so surplus beyond it is curtailed.
      UNCONTROLLED  export is limited only by the inverter's AC rating, which
                    is what an installation configured for maximum export
                    would do.

    The critical hours of both dispatches are then solved in pandapower. The
    difference is the electrical headroom that export control buys, and it is
    what decides how far PV can be oversized behind a 5 kVA transformer.
    """
    rows = []

    for panels in cfg.hardware.panel_count_sweep:
        pv_kwp = cfg.hardware.pv_kwp(panels)
        key = SW.cheapest_feasible_inverter(cfg, pv_kwp)
        inverter_kw = cfg.hardware.inverter(key).rated_ac_kw

        for mode, export_limit in (
            ("CONTROLLED_TO_TRANSFORMER_ENVELOPE", None),
            ("UNCONTROLLED_INVERTER_LIMITED", inverter_kw),
        ):
            spec = SystemSpec(
                label=f"PV{panels}_{mode}", houses=houses,
                panel_count=panels, bess_modules=4, inverter_key=key,
                export_limit_kw=export_limit,
            )
            system = st.resolve(spec)
            if not system.hardware_feasible:
                continue

            _, dispatch = SW.run_system(
                st, spec, control=REFERENCE_CONTROL, houses=houses,
                with_economics=False, return_dispatch=True)

            hours = G.critical_hours(dispatch)
            network = G.run_dispatch_hours(
                cfg, dispatch, st.ts, houses, list(hours.values()),
                scenario=spec.label)
            summary = G.summarise_network_results(network, cfg)

            rows.append({
                "panel_count": panels,
                "pv_kwp": pv_kwp,
                "inverter_key": key,
                "inverter_ac_kw": inverter_kw,
                "export_control": mode,
                "export_limit_kw": system.export_limit_kw,
                "energy_self_sufficiency_pct": float(
                    100.0 * (1 - dispatch["grid_import_kw"].sum()
                             / dispatch["load_kw"].sum())),
                "pv_curtailed_kwh": float(dispatch["pv_curtailed_kw"].sum()),
                "pv_curtailment_pct": float(
                    100.0 * dispatch["pv_curtailed_kw"].sum()
                    / max(dispatch["pv_available_kw"].sum(), 1e-9)),
                "grid_export_kwh": float(dispatch["grid_export_kw"].sum()),
                "dispatch_peak_export_kw": float(
                    max(0.0, -dispatch["pcc_import_kw"].min())),
                **summary,
                "electrically_feasible": bool(
                    summary["voltage_screen_ok"]
                    and summary["transformer_permissible_ok"]
                    and summary["line_loading_ok"]),
                "binding_constraint": G._binding_constraint(summary, cfg),
            })

    return pd.DataFrame(rows)


def _inverter_pf_sensitivity(cfg: Case1Config, st: Case1Study,
                             bundles) -> pd.DataFrame:
    """
    Reactive-power absorption at each configuration's worst export hour.

    The Deye datasheet gives an adjustable power factor from 0.8 leading to
    0.8 lagging, so absorbing reactive power to limit voltage rise is a real
    capability of the quoted unit. These remain screening cases, not
    commissioned inverter settings.
    """
    rows = []
    for label, houses, system, dispatch in bundles:
        export_hour = pd.to_numeric(dispatch["pcc_import_kw"]).idxmin()
        for pf in cfg.network.inverter_pf_sensitivity:
            table = G.run_dispatch_hours(
                cfg, dispatch, st.ts, houses, [export_hour],
                scenario=f"{label}_PF{pf:.2f}", inverter_pf=pf)
            row = table.iloc[0].to_dict()
            row["case"] = label
            row["inverter_power_factor"] = pf
            row["panel_count"] = system.spec.panel_count
            row["pv_kwp"] = system.pv_kwp
            rows.append(row)
    return pd.DataFrame(rows)


def _manifest(cfg: Case1Config, st: Case1Study,
              results: Case1Results) -> pd.DataFrame:
    import sys

    import pandas as _pd

    try:
        import pandapower
        pandapower_version = pandapower.__version__
    except Exception:
        pandapower_version = "not installed"
    try:
        import pypsa
        pypsa_version = pypsa.__version__
    except Exception:
        pypsa_version = "not installed"
    try:
        import pvlib
        pvlib_version = pvlib.__version__
    except Exception:
        pvlib_version = "not installed"

    return _pd.DataFrame([{
        "model": "SEEDExchange San Rafael Case 1",
        "package_version": __import__("sanrafael_case1").__version__,
        "case_label": cfg.case_label,
        "model_year": cfg.site.model_year,
        "transformer": f"{cfg.site.trafo_number} / node {cfg.site.trafo_node}",
        "transformer_kva": cfg.site.transformer_kva,
        "transformer_loading_limit_pu": cfg.transformer.loading_limit_pu,
        "pf_import": cfg.transformer.pf_import,
        "pf_export": cfg.transformer.pf_export,
        "import_limit_kw": cfg.import_limit_kw,
        "export_limit_kw": cfg.export_limit_kw,
        "reference_stochastic_seed": cfg.demand.stochastic_load_seed,
        "decision_pv_profile": st.decision_profile.label,
        "benchmark_pv_profile": st.benchmark_profile.label,
        "monthly_radiation_source": st.monthly_radiation_source,
        "reference_control": REFERENCE_CONTROL,
        "decision_control": DECISION_CONTROL,
        "forecasting_used": "none - Case 1 controllers are causal",
        "lp_role": "perfect-foresight upper bound only",
        "islanding_confirmed": False,
        "hardware_confirmed_installed": False,
        "demand_basis": "synthetic HOMER stochastic-load model; not measured",
        "pv_useful_panels_net_metering": results.notes.get(
            "pv_useful_size_NET_METERING_HOMER", {}).get("recommended_size"),
        "pv_useful_panels_self_consumption": results.notes.get(
            "pv_useful_size_SELF_CONSUMPTION_ONLY", {}).get("recommended_size"),
        "bess_useful_modules_net_metering": results.notes.get(
            "bess_useful_size_NET_METERING_HOMER", {}).get("recommended_size"),
        "bess_useful_modules_self_consumption": results.notes.get(
            "bess_useful_size_SELF_CONSUMPTION_ONLY", {}).get("recommended_size"),
        "python": sys.version.split()[0],
        "pypsa": pypsa_version,
        "pandapower": pandapower_version,
        "pvlib": pvlib_version,
        "pandas": _pd.__version__,
        "numpy": np.__version__,
    }])
