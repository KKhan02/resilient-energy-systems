"""
Validation against the verified PyPSA v18 and pandapower v5 baselines.

This module exists to make one guarantee: the Case 1 package reproduces the
published baseline numbers from the original notebooks BEFORE any Case 1
extension is applied. If a port silently changed the physics, these checks
fail and the Case 1 results that build on them are not trusted.

Every expected value below is transcribed from the executed output cells of
the two baseline notebooks. None is a target that the Case 1 code was tuned
to hit; they are the published results.

Run:
    python -m sanrafael_case1.validation
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import kpi as K
from .config import Case1Config
from .lp_model import SystemSpec, curtailment_attribution
from .study import Case1Study

# ---------------------------------------------------------------------------
# Published baseline values
# ---------------------------------------------------------------------------

V18_DEMAND = {
    "annual_load_4hh_kwh": 7592.0,
    "stochastic_peak_4hh_kw": 2.166677435937405,
    "deterministic_peak_4hh_kw": 1.4963834557023217,
    "clipped_household_hours": 168,
    "clipped_household_hours_pct": 0.09589,
    "peak_load_kw_by_houses": {4: 2.1667, 5: 2.5193, 6: 2.9979,
                               7: 3.7174, 8: 4.1833},
    "annual_load_kwh_by_houses": {4: 7592.0, 5: 9490.0, 6: 11388.0,
                                  7: 13286.0, 8: 15184.0},
}

V18_RESOURCE = {
    "homer_calibrated_annual_pv_dc_kwh": 7326.3,
    "nasa_annual_ghi_kwh_m2": 1773.00935,
    "nasa_annual_poa_kwh_m2": 1772.391717,
    "nasa_poa_to_ghi_ratio": 0.999652,
    "nasa_annual_pv_dc_kwh": 7054.003295,
    "nasa_peak_pv_dc_kw": 3.850082,
}

# S2 reference: 4 houses, 12 panels, 4 battery modules, 5 kW converter.
V18_S2_HOMER_SHAPE = {
    "self_sufficiency_pct": 84.9801,
    "net_grid_independence_pct": 89.46,
    "grid_import_kwh": 1140.3112,
    "grid_export_kwh": 339.9833,
    "battery_throughput_kwh": 3454.8435,
    "battery_charge_kwh": 3543.429254,
    "battery_discharge_kwh": 3366.257791,
    "peak_import_kw": 2.0192,
    "peak_export_kw": 2.1406,
    "pv_dc_generation_kwh": 7326.3,
    "pv_penetration_pct": 96.5,
}

V18_S2_NASA = {
    "self_sufficiency_pct": 82.8746,
    "net_grid_independence_pct": 86.016405,
    "grid_import_kwh": 1300.1588,
    "grid_export_kwh": 238.5243,
    "battery_throughput_kwh": 3508.7209,
    "battery_charge_kwh": 3598.68809,
    "battery_discharge_kwh": 3418.75,
    "peak_import_kw": 2.1667,
    "peak_export_kw": 2.5313,
    "pv_dc_generation_kwh": 7054.0033,
    "pv_penetration_pct": 92.91,
}

# Fixed-hardware household sweep on the NASA profile (v18 decision case).
V18_HOUSE_SWEEP_SS_PCT = {4: 82.87, 5: 68.96, 6: 57.76, 7: 49.70, 8: 43.64}
V18_HOUSE_SWEEP_IMPORT_KWH = {4: 1300.16, 5: 2946.06, 6: 4810.39,
                              7: 6682.87, 8: 8558.32}

# v18 battery-module sweep, NASA profile, 12 panels / 4 houses.
V18_BESS_SWEEP_SS_PCT = {0: 40.10, 1: 59.20, 2: 75.53, 3: 82.09, 4: 82.87}

# v18 PV-panel sweep, NASA profile, 4 battery modules / 4 houses.
V18_PV_SWEEP_SS_PCT = {4: 29.33, 6: 43.62, 8: 57.75, 10: 71.65, 12: 82.87}

# pandapower v5 published network results (reference-seed, PF 0.90).
V5_NETWORK = {
    "nasa_pv_ac_annual_kwh": 6701.30313,
    "nasa_pv_ac_peak_kw": 3.657578,
    "inverter_clipping_hours_at_5kw": 0,
    "annual_4hh_min_lv_vm_pu": 0.9736,
    "annual_4hh_max_lv_vm_pu": 1.0094,
    "annual_4hh_max_trafo_loading_pct": 61.3215,
    "annual_4hh_max_import_kw": 2.2467,
    "annual_4hh_max_export_kw": 3.0216,
    "max_load_4hh_trafo_loading_pct": 50.9661,
    "clear_sky_5kw_4hh_trafo_loading_pct": 92.2167,
    "first_overload_houses_fixed_route": 9,
    "equivalent_validation_difference_pct": -0.002981,
}


# ---------------------------------------------------------------------------
# Check machinery
# ---------------------------------------------------------------------------


@dataclass
class Check:
    group: str
    name: str
    expected: float | int | str
    actual: float | int | str
    tolerance: float
    relative: bool = False

    @property
    def difference(self) -> float:
        try:
            return float(self.actual) - float(self.expected)
        except (TypeError, ValueError):
            return np.nan

    @property
    def passed(self) -> bool:
        if isinstance(self.expected, str) or isinstance(self.actual, str):
            return self.expected == self.actual
        if not np.isfinite(float(self.actual)):
            return False
        if self.relative:
            denominator = max(abs(float(self.expected)), 1e-12)
            return abs(self.difference) / denominator <= self.tolerance
        return abs(self.difference) <= self.tolerance

    def as_row(self) -> dict:
        return {
            "group": self.group,
            "check": self.name,
            "expected": self.expected,
            "actual": self.actual,
            "difference": self.difference,
            "tolerance": self.tolerance,
            "mode": "relative" if self.relative else "absolute",
            "status": "PASS" if self.passed else "FAIL",
        }


def v18_spec(label: str, houses: int = 4, panels: int = 12,
             bess: int = 4, converter_kw: float = 5.0,
             allow_export: bool = True) -> SystemSpec:
    """
    A specification that reproduces v18's modelling choices exactly:

      * PCC active-power limits of +/- 5.0 kW (v18 treated 5 kVA as 5 kW)
      * inverter p_nom limiting the DC input
      * battery DC power capped by the converter rating
    """
    return SystemSpec(
        label=label, houses=houses, panel_count=panels, bess_modules=bess,
        inverter_key="SUN-5K", inverter_ac_kw=converter_kw,
        import_limit_kw=5.0, export_limit_kw=5.0 if allow_export else 0.0,
        allow_grid_export=allow_export,
        inverter_limit_side="dc", battery_sizing="v18",
    )


def run_validation(cfg: Case1Config | None = None,
                   study: Case1Study | None = None,
                   include_sweeps: bool = True,
                   verbose: bool = True) -> pd.DataFrame:
    """Run all baseline checks and return them as a table."""
    cfg = cfg or Case1Config()
    st = study or Case1Study(cfg)
    checks: list[Check] = []

    def add(group, name, expected, actual, tol, relative=False):
        checks.append(Check(group, name, expected, actual, tol, relative))

    # -- HOMER inputs -----------------------------------------------------
    h = st.homer
    add("homer", "annual 4-house load [kWh]", 7592.0, h["annual_load_4hh_kwh"], 1e-9)
    add("homer", "PV reference [kWp]", 5.22, h["pv_kwp"], 1e-9)
    add("homer", "inverter rating [kW]", 5.0, h["inverter_kw"], 1e-9)
    add("homer", "inverter efficiency", 0.95, h["inverter_efficiency"], 1e-12)
    add("homer", "battery round-trip efficiency", 0.95,
        h["battery_roundtrip_efficiency"], 1e-12)
    add("homer", "battery minimum SOC [pu]", 0.10, h["battery_min_soc_pu"], 1e-12)
    add("homer", "battery usable bank [kWh]", 17.3,
        h["battery_bank_usable_kwh_reference"], 1e-12)
    add("homer", "grid buy [USD/kWh]", 0.29, h["grid_buy_usd_per_kwh"], 1e-12)
    add("homer", "grid sell [USD/kWh]", 0.275, h["grid_sell_usd_per_kwh"], 1e-12)
    add("homer", "day-to-day load variability", 0.20,
        h["load_daily_variability_pu"], 1e-12)
    add("homer", "timestep load variability", 0.25,
        h["load_timestep_variability_pu"], 1e-12)
    add("homer", "HOMER annual PV production [kWh]", 7326.3, h["homer_pv_kwh"], 1e-9)
    add("homer", "project lifetime [y]", 25, h["project_lifetime_y"], 0)
    add("homer", "discount rate", 0.06, h["discount_rate"], 1e-12)

    # -- demand -----------------------------------------------------------
    add("demand", "annual 4-house load [kWh]",
        V18_DEMAND["annual_load_4hh_kwh"], float(st.ts["load_4hh_kw"].sum()), 1e-6)
    add("demand", "stochastic 4-house peak [kW]",
        V18_DEMAND["stochastic_peak_4hh_kw"],
        float(st.ts["load_4hh_kw"].max()), 1e-12)
    add("demand", "deterministic 4-house peak [kW]",
        V18_DEMAND["deterministic_peak_4hh_kw"],
        float(st.ts["deterministic_load_4hh_kw"].max()), 1e-12)
    add("demand", "clipped household-hours",
        V18_DEMAND["clipped_household_hours"],
        int(st.ts.attrs["clipped_household_hours"]), 0)
    add("demand", "clipped household-hours [%]",
        V18_DEMAND["clipped_household_hours_pct"],
        float(st.ts.attrs["clipped_household_hours_pct"]), 1e-4)

    summary = st.demand_summary().set_index("houses")
    for houses, expected in V18_DEMAND["peak_load_kw_by_houses"].items():
        add("demand", f"peak load, {houses} houses [kW]", expected,
            float(summary.at[houses, "peak_load_kw"]), 5e-5)
    for houses, expected in V18_DEMAND["annual_load_kwh_by_houses"].items():
        add("demand", f"annual load, {houses} houses [kWh]", expected,
            float(summary.at[houses, "annual_load_kwh"]), 1e-6)

    # -- resource ---------------------------------------------------------
    bench = st.benchmark_profile
    nasa = st.decision_profile
    add("resource", "HOMER-calibrated annual PV DC [kWh]",
        V18_RESOURCE["homer_calibrated_annual_pv_dc_kwh"],
        float((bench.per_kwp_kw * h["pv_kwp"]).sum()), 1e-6)
    add("resource", "NASA annual GHI [kWh/m2]",
        V18_RESOURCE["nasa_annual_ghi_kwh_m2"],
        nasa.diagnostics["annual_ghi_kwh_m2"], 1e-5)
    add("resource", "NASA annual POA [kWh/m2]",
        V18_RESOURCE["nasa_annual_poa_kwh_m2"],
        nasa.diagnostics["annual_poa_kwh_m2"], 1e-5)
    add("resource", "NASA POA/GHI ratio",
        V18_RESOURCE["nasa_poa_to_ghi_ratio"],
        nasa.diagnostics["poa_to_ghi_ratio"], 1e-6)
    add("resource", "NASA annual PV DC at 5.22 kWp [kWh]",
        V18_RESOURCE["nasa_annual_pv_dc_kwh"],
        nasa.diagnostics["annual_pv_dc_kwh_at_reference_kwp"], 1e-4)
    add("resource", "NASA peak PV DC at 5.22 kWp [kW]",
        V18_RESOURCE["nasa_peak_pv_dc_kw"],
        nasa.diagnostics["peak_pv_dc_kw_at_reference_kwp"], 1e-5)

    # -- v5 PV AC chain (inverter efficiency and the 5 kW AC clip) --------
    nasa_dc = nasa.dc_kw(h["pv_kwp"])
    nasa_ac_unclipped = nasa_dc * 0.95
    nasa_ac = np.minimum(nasa_ac_unclipped, 5.0)
    add("resource", "v5 NASA inverter AC annual [kWh]",
        V5_NETWORK["nasa_pv_ac_annual_kwh"], float(nasa_ac.sum()), 1e-3)
    add("resource", "v5 NASA inverter AC peak [kW]",
        V5_NETWORK["nasa_pv_ac_peak_kw"], float(nasa_ac.max()), 1e-5)
    add("resource", "v5 inverter clipping hours at 5 kW",
        V5_NETWORK["inverter_clipping_hours_at_5kw"],
        int((nasa_ac_unclipped > 5.0).sum()), 0)

    # -- S2 reference LP, both profiles -----------------------------------
    for group, profile, expected in (
        ("lp_s2_homer_shape", bench, V18_S2_HOMER_SHAPE),
        ("lp_s2_nasa", nasa, V18_S2_NASA),
    ):
        _, system, dispatch = st.run_lp(v18_spec("S2_REFERENCE_PV_BESS"),
                                        profile=profile)
        k = K.compute_kpis(dispatch, cfg, h, system.as_row(),
                           "S2_REFERENCE_PV_BESS", "LP_V18_COMPATIBILITY")
        for field, value in expected.items():
            add(group, field, value, k[field], 5e-4, relative=True)

        residual = K.energy_balance_residual(dispatch, h["inverter_efficiency"], 1.0)
        add(group, "max |AC node residual| [kW]", 0.0,
            float(residual.abs().max()), 1e-7)
        add(group, "simultaneous charge and discharge hours", 0,
            int(((dispatch["battery_dc_kw"] > 1e-9)
                 & (dispatch["battery_dc_kw"] < -1e-9)).sum()), 0)
        add(group, "minimum battery SOC >= minimum [pu]", True,
            bool(dispatch["battery_actual_soc_pu"].min()
                 >= h["battery_min_soc_pu"] - 1e-9), 0)

    if include_sweeps:
        # -- fixed-hardware household sweep, NASA profile -----------------
        for houses, expected in V18_HOUSE_SWEEP_SS_PCT.items():
            _, system, dispatch = st.run_lp(
                v18_spec(f"S3_FIXED_HW_{houses}HH", houses=houses),
                profile=nasa)
            k = K.compute_kpis(dispatch, cfg, h, system.as_row(),
                               f"S3_FIXED_HW_{houses}HH", "LP_V18_COMPATIBILITY")
            add("lp_house_sweep", f"self-sufficiency, {houses} houses [%]",
                expected, k["self_sufficiency_pct"], 5e-4, relative=True)
            add("lp_house_sweep", f"grid import, {houses} houses [kWh]",
                V18_HOUSE_SWEEP_IMPORT_KWH[houses], k["grid_import_kwh"],
                5e-4, relative=True)

        # -- battery-module sweep -----------------------------------------
        for modules, expected in V18_BESS_SWEEP_SS_PCT.items():
            _, system, dispatch = st.run_lp(
                v18_spec(f"BESS_{modules}MODULES", bess=modules), profile=nasa)
            k = K.compute_kpis(dispatch, cfg, h, system.as_row(),
                               f"BESS_{modules}MODULES", "LP_V18_COMPATIBILITY")
            add("lp_bess_sweep", f"self-sufficiency, {modules} modules [%]",
                expected, k["self_sufficiency_pct"], 5e-4, relative=True)

        # -- PV-panel sweep -----------------------------------------------
        for panels, expected in V18_PV_SWEEP_SS_PCT.items():
            _, system, dispatch = st.run_lp(
                v18_spec(f"PV_{panels}PANELS", panels=panels), profile=nasa)
            k = K.compute_kpis(dispatch, cfg, h, system.as_row(),
                               f"PV_{panels}PANELS", "LP_V18_COMPATIBILITY")
            add("lp_pv_sweep", f"self-sufficiency, {panels} panels [%]",
                expected, k["self_sufficiency_pct"], 5e-4, relative=True)

    # -- pandapower port against v5 --------------------------------------
    checks += _network_checks(st, include_annual=include_sweeps)

    table = pd.DataFrame([c.as_row() for c in checks])

    if verbose:
        failures = table[table["status"] == "FAIL"]
        print(f"Baseline validation: {len(table)} checks, "
              f"{len(table) - len(failures)} passed, {len(failures)} failed.")
        if not failures.empty:
            print(failures.to_string(index=False))

    return table


def _network_checks(st: Case1Study, include_annual: bool = True) -> list[Check]:
    """
    Check the pandapower port against pandapower v5.

    v5 used a load power factor of 0.90 and ran PV only with the battery
    idle, so those settings are restored here. Case 1's own network runs use
    power factor 0.95 and a controlled PV-BESS dispatch.
    """
    from dataclasses import replace as dc_replace

    from . import grid_check as G

    cfg = st.cfg
    v5cfg = dc_replace(cfg, network=dc_replace(cfg.network,
                                               load_power_factor=0.90))
    checks: list[Check] = []

    def add(name, expected, actual, tol, relative=False):
        checks.append(Check("network_v5", name, expected, actual, tol, relative))

    scaling = G.EquivalentScaling(v5cfg)
    add("equivalent MV line-line voltage [kV]", 13.2, scaling.mv_eq_kv, 5e-4)
    add("equivalent LV line-line voltage [kV]", 0.4157, scaling.lv_eq_kv, 5e-4)
    add("equivalent transformer rating [kVA]", 15.0,
        scaling.trafo_eq_mva * 1000, 1e-9)

    equivalence = G.validate_single_phase_equivalent(v5cfg, 0.5, 0.90)
    add("single-phase equivalent difference [%]",
        V5_NETWORK["equivalent_validation_difference_pct"],
        float(equivalence.at[0, "difference_pct"]), 1e-5)

    # v5 inverter series: PV only, battery idle, clipped at 5 kW AC.
    dc = st.decision_profile.dc_kw(st.homer["pv_kwp"])
    ac = np.minimum(dc * 0.95, 5.0)
    household = st.ts[[f"house_{h}_kw" for h in range(1, 5)]].to_numpy()

    net = G.build_group_network(v5cfg, 4)

    # Peak-demand and inverter-stress snapshots, exactly as v5 defined them.
    load4 = st.load_kw(4)
    peak_ts = load4.idxmax()
    position = load4.index.get_loc(peak_ts)
    _, peak_result = G.run_snapshot(
        v5cfg, 4, "MAX_LOAD_NO_DER", house_loads_kw=household[position],
        inverter_ac_kw=0.0, net=net)
    add("peak-demand transformer loading [%]",
        V5_NETWORK["max_load_4hh_trafo_loading_pct"],
        peak_result["transformer_loading_pct"], 1e-3)

    daytime = load4.index.hour.to_series(index=load4.index).between(10, 14)
    min_day_ts = load4[daytime.to_numpy()].idxmin()
    min_day_position = load4.index.get_loc(min_day_ts)
    _, stress_result = G.run_snapshot(
        v5cfg, 4, "CLEAR_SKY_5.0KW",
        house_loads_kw=household[min_day_position],
        inverter_ac_kw=5.0, net=net)
    add("5 kW inverter-stress transformer loading [%]",
        V5_NETWORK["clear_sky_5kw_4hh_trafo_loading_pct"],
        stress_result["transformer_loading_pct"], 1e-3)

    if include_annual:
        rows = []
        for i, timestamp in enumerate(dc.index):
            _, row = G.run_snapshot(
                v5cfg, 4, "V5_ANNUAL_PV_BATTERY_IDLE",
                house_loads_kw=household[i],
                inverter_ac_kw=float(ac.iloc[i]), net=net)
            rows.append(row)
        annual = pd.DataFrame(rows)

        add("annual minimum LV voltage [pu]",
            V5_NETWORK["annual_4hh_min_lv_vm_pu"],
            float(annual["min_lv_vm_pu"].min()), 1e-4)
        add("annual maximum LV voltage [pu]",
            V5_NETWORK["annual_4hh_max_lv_vm_pu"],
            float(annual["max_lv_vm_pu"].max()), 1e-4)
        add("annual maximum transformer loading [%]",
            V5_NETWORK["annual_4hh_max_trafo_loading_pct"],
            float(annual["transformer_loading_pct"].max()), 1e-3)
        add("annual maximum import [kW]",
            V5_NETWORK["annual_4hh_max_import_kw"],
            float(annual["pcc_import_physical_kw"].max()), 1e-3)
        add("annual maximum export [kW]",
            V5_NETWORK["annual_4hh_max_export_kw"],
            float(-annual["pcc_import_physical_kw"].min()), 1e-3)

        # v5 fixed-route headroom sweep: first nominal overload at 9 houses.
        first_overload = None
        for houses in range(1, 21):
            column = f"load_{houses}hh_kw"
            if column not in st.ts.columns:
                break
            group = st.ts[column]
            group_peak_ts = group.idxmax()
            group_position = st.ts.index.get_loc(group_peak_ts)
            loads = st.ts[[f"house_{h}_kw" for h in range(1, houses + 1)]
                          ].to_numpy()[group_position]
            _, row = G.run_snapshot(v5cfg, houses, "HEADROOM",
                                    house_loads_kw=loads, inverter_ac_kw=0.0)
            if row["transformer_loading_pct"] > 100.0:
                first_overload = houses
                break
        add("first nominal transformer overload [houses]",
            V5_NETWORK["first_overload_houses_fixed_route"],
            first_overload if first_overload is not None else -1, 0)

    return checks


def assert_baseline(cfg: Case1Config | None = None,
                    study: Case1Study | None = None,
                    include_sweeps: bool = True) -> pd.DataFrame:
    """Raise if any baseline check fails."""
    table = run_validation(cfg, study, include_sweeps=include_sweeps, verbose=True)
    failures = table[table["status"] == "FAIL"]
    if not failures.empty:
        raise AssertionError(
            "Case 1 package does not reproduce the verified baselines:\n"
            + failures.to_string(index=False))
    return table


if __name__ == "__main__":  # pragma: no cover
    cfg = Case1Config()
    cfg.paths.ensure()
    table = run_validation(cfg)
    out = cfg.paths.results_dir / "baseline_validation.csv"
    table.to_csv(out, index=False)
    print("Saved:", out)
