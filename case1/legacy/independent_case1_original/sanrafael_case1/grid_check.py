"""
Electrical feasibility screening with pandapower.

Ported from pandapower v5, including the single-phase equivalent, the EPM
conductor data and the screening bands. `validation.py` checks that this port
reproduces the v5 published results.

SINGLE-PHASE EQUIVALENT (unchanged from v5)
-------------------------------------------
Transformer 94022 is a single-phase 7.621 kV / 240-120 V unit, and
pandapower's standard solver is balanced three-phase, so the physical network
is represented as an equivalent:

    equivalent voltage        = sqrt(3) x physical single-phase voltage
    equivalent power          = 3 x physical single-phase power
    equivalent transformer VA = 3 x physical rating

Per-unit voltage, conductor current and transformer loading percentage then
match the physical single-phase system, and reported active power is
converted back. The 240 V secondary uses twice the single-conductor series
impedance to represent the two-conductor current path.

This is an EQUIVALENT, not a split-phase model: it cannot represent
120 V leg imbalance. That remains a documented limitation.

CASE 1 EXTENSIONS
-----------------
1. Load power factor and transformer permissible loading are parameters, so
   the 5 kVA apparent-power constraint is screened on the same basis as the
   energy model rather than against a fixed 100% line.
2. The inverter sgen can be driven by a Case 1 dispatch time series, so the
   network sees the ACTUAL net AC injection of a controlled PV-BESS system.
   v5 ran PV-only with the battery idle, which is a conservative envelope but
   cannot show what a control strategy does to the network.
3. A feasibility screen crosses PV size, inverter rating, export allowance
   and household count and returns a pass/fail frontier.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import Case1Config


def require_pandapower():
    try:
        import pandapower as pp
        return pp
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Install with: pip install pandapower") from exc


# ---------------------------------------------------------------------------
# Equivalent-circuit helpers
# ---------------------------------------------------------------------------


@dataclass
class EquivalentScaling:
    cfg: Case1Config

    @property
    def power_scale(self) -> float:
        return self.cfg.network.pp_power_scale

    @property
    def mv_eq_kv(self) -> float:
        return math.sqrt(3) * self.cfg.site.mv_voltage_kv

    @property
    def lv_eq_kv(self) -> float:
        return math.sqrt(3) * self.cfg.site.lv_voltage_kv

    @property
    def trafo_eq_mva(self) -> float:
        return self.power_scale * self.cfg.site.transformer_kva / 1000.0

    def kw_to_pp_mw(self, p_kw: float) -> float:
        return self.power_scale * float(p_kw) / 1000.0

    def pp_mw_to_kw(self, p_mw: float) -> float:
        return float(p_mw) * 1000.0 / self.power_scale

    def kvar_to_pp_mvar(self, q_kvar: float) -> float:
        return self.power_scale * float(q_kvar) / 1000.0


def q_from_p_pf(p_kw: float, pf: float) -> float:
    p_kw = float(p_kw)
    if p_kw == 0 or pf >= 1.0:
        return 0.0
    return abs(p_kw) * math.tan(math.acos(pf))


def tap_house_counts(houses: int, houses_per_tap: int) -> list[int]:
    remaining = int(houses)
    counts = []
    while remaining > 0:
        count = min(houses_per_tap, remaining)
        counts.append(count)
        remaining -= count
    return counts


# ---------------------------------------------------------------------------
# Network construction
# ---------------------------------------------------------------------------


def total_lv_route_m(cfg: Case1Config, houses: int, route_mode: str = "fixed",
                     expansion_segment_m: float | None = None) -> float:
    if route_mode == "fixed":
        return float(cfg.site.secondary_length_m)
    if route_mode != "expansion":
        raise ValueError("route_mode must be 'fixed' or 'expansion'")

    segment = (expansion_segment_m if expansion_segment_m is not None
               else cfg.network.expansion_segment_m)
    if segment is None:
        raise ValueError(
            "Expansion sensitivity requires an explicit added-tap spacing. "
            "No spacing is assumed silently.")

    per_tap = cfg.network.houses_per_tap
    reference_taps = math.ceil(cfg.demand.reference_houses / per_tap)
    required_taps = math.ceil(houses / per_tap)
    added = max(0, required_taps - reference_taps)
    return float(cfg.site.secondary_length_m + added * segment)


def build_group_network(cfg: Case1Config, houses: int,
                        route_mode: str = "fixed",
                        expansion_segment_m: float | None = None):
    """Build the representative radial LV group behind transformer 94022."""
    pp = require_pandapower()
    scale = EquivalentScaling(cfg)
    net_cfg = cfg.network
    site = cfg.site

    houses = int(houses)
    if houses < 1:
        raise ValueError("houses must be >= 1")

    lv_route_m = total_lv_route_m(cfg, houses, route_mode, expansion_segment_m)

    net = pp.create_empty_network(
        name=f"San Rafael {houses}-house group ({route_mode} route)",
        f_hz=60.0, sn_mva=1.0)

    b_upstream = pp.create_bus(net, vn_kv=scale.mv_eq_kv,
                               name="UPSTREAM_MV_EQ", type="b")
    b_hv = pp.create_bus(net, vn_kv=scale.mv_eq_kv,
                         name="TRF_94022_HV_EQ", type="b")
    b_lv = pp.create_bus(net, vn_kv=scale.lv_eq_kv,
                         name="TRF_94022_LV_EQ", type="b")

    pp.create_ext_grid(net, bus=b_upstream, vm_pu=1.0, name="EPM_UPSTREAM")

    pp.create_line_from_parameters(
        net, from_bus=b_upstream, to_bus=b_hv,
        length_km=site.primary_length_m / 1000.0,
        r_ohm_per_km=net_cfg.mv_r_ohm_per_km,
        x_ohm_per_km=net_cfg.mv_x_ohm_per_km,
        c_nf_per_km=0.0, max_i_ka=net_cfg.mv_max_i_ka,
        name="MV_LOCAL_#2_ACSR")

    pp.create_transformer_from_parameters(
        net, hv_bus=b_hv, lv_bus=b_lv,
        sn_mva=scale.trafo_eq_mva,
        vn_hv_kv=scale.mv_eq_kv, vn_lv_kv=scale.lv_eq_kv,
        vk_percent=net_cfg.trf_vk_percent,
        vkr_percent=net_cfg.trf_vkr_percent,
        pfe_kw=scale.power_scale * net_cfg.trf_pfe_physical_kw,
        i0_percent=net_cfg.trf_i0_percent,
        shift_degree=0.0, name="TRF_94022_EQ")

    # The shared community inverter sits at the transformer LV bus.
    inverter_idx = pp.create_sgen(net, bus=b_lv, p_mw=0.0, q_mvar=0.0,
                                  name="SHARED_COMMUNITY_INVERTER")

    counts = tap_house_counts(houses, net_cfg.houses_per_tap)
    segment_km = lv_route_m / len(counts) / 1000.0

    previous = b_lv
    load_indices: list[int] = []
    lv_bus_indices = [b_lv]
    lv_line_indices: list[int] = []
    house_number = 1

    for tap_no, count in enumerate(counts, start=1):
        tap_bus = pp.create_bus(net, vn_kv=scale.lv_eq_kv,
                                name=f"LV_TAP_{tap_no}", type="b")
        lv_bus_indices.append(tap_bus)

        line_idx = pp.create_line_from_parameters(
            net, from_bus=previous, to_bus=tap_bus, length_km=segment_km,
            r_ohm_per_km=net_cfg.lv_r_loop_ohm_per_km,
            x_ohm_per_km=net_cfg.lv_x_loop_ohm_per_km,
            c_nf_per_km=0.0, max_i_ka=net_cfg.lv_max_i_ka,
            name=f"LV_TRUNK_{tap_no}_1/0_AAC_LOOP")
        lv_line_indices.append(line_idx)

        for _ in range(count):
            load_indices.append(pp.create_load(
                net, bus=tap_bus, p_mw=0.0, q_mvar=0.0,
                name=f"HOUSE_{house_number}"))
            house_number += 1

        previous = tap_bus

    net._san_rafael = {
        "houses": houses,
        "route_mode": route_mode,
        "lv_total_route_m": lv_route_m,
        "lv_segment_length_m": lv_route_m / len(counts),
        "upstream_bus": b_upstream,
        "trafo_hv_bus": b_hv,
        "trafo_lv_bus": b_lv,
        "lv_bus_indices": lv_bus_indices,
        "load_indices": load_indices,
        "inverter_idx": inverter_idx,
        "lv_line_indices": lv_line_indices,
    }
    return net


def set_operating_point(net, cfg: Case1Config,
                        house_loads_kw=None,
                        total_load_kw: float | None = None,
                        inverter_ac_kw: float = 0.0,
                        inverter_q_kvar: float = 0.0,
                        load_pf: float | None = None) -> None:
    scale = EquivalentScaling(cfg)
    meta = net._san_rafael
    houses = meta["houses"]
    load_pf = cfg.network.load_power_factor if load_pf is None else float(load_pf)

    if house_loads_kw is None:
        if total_load_kw is None:
            raise ValueError("Provide total_load_kw or house_loads_kw")
        house_loads = np.full(houses, float(total_load_kw) / houses, dtype=float)
    else:
        house_loads = np.asarray(house_loads_kw, dtype=float)
        if len(house_loads) != houses:
            raise ValueError(
                f"Expected {houses} household loads, received {len(house_loads)}")
        if (house_loads < 0).any():
            raise ValueError("Household demand cannot be negative")

    for idx, p_kw in zip(meta["load_indices"], house_loads):
        net.load.at[idx, "p_mw"] = scale.kw_to_pp_mw(p_kw)
        net.load.at[idx, "q_mvar"] = scale.kvar_to_pp_mvar(
            q_from_p_pf(p_kw, load_pf))

    net.sgen.at[meta["inverter_idx"], "p_mw"] = scale.kw_to_pp_mw(inverter_ac_kw)
    net.sgen.at[meta["inverter_idx"], "q_mvar"] = scale.kvar_to_pp_mvar(
        inverter_q_kvar)


def solve(net):
    pp = require_pandapower()
    pp.runpp(net, algorithm="bfsw", init="flat",
             calculate_voltage_angles=False, max_iteration=100,
             tolerance_mva=1e-9)
    return net


# ---------------------------------------------------------------------------
# Result extraction
# ---------------------------------------------------------------------------


def extract_snapshot(net, cfg: Case1Config, scenario: str,
                     total_load_kw: float, inverter_ac_kw: float,
                     inverter_q_kvar: float = 0.0) -> dict:
    scale = EquivalentScaling(cfg)
    meta = net._san_rafael
    lv_buses = meta["lv_bus_indices"]
    lv_lines = meta["lv_line_indices"]
    net_cfg = cfg.network

    ext_import_kw = scale.pp_mw_to_kw(net.res_ext_grid["p_mw"].sum())
    ext_import_kvar = (
        float(net.res_ext_grid["q_mvar"].sum()) * 1000.0 / scale.power_scale)

    trafo_loading = float(net.res_trafo["loading_percent"].iloc[0])
    trafo_lv_current_a = float(net.res_trafo["i_lv_ka"].iloc[0] * 1000.0)

    mv_idx = net.line.index[net.line["name"] == "MV_LOCAL_#2_ACSR"][0]
    mv_loading = float(net.res_line.at[mv_idx, "loading_percent"])
    lv_loading = (float(net.res_line.loc[lv_lines, "loading_percent"].max())
                  if lv_lines else np.nan)

    min_vm = float(net.res_bus.loc[lv_buses, "vm_pu"].min())
    max_vm = float(net.res_bus.loc[lv_buses, "vm_pu"].max())

    limit_pct = 100.0 * cfg.transformer.loading_limit_pu

    # Apparent power at the transformer LV terminal, physical single-phase.
    trafo_p_kw = scale.pp_mw_to_kw(float(net.res_trafo["p_lv_mw"].iloc[0]))
    trafo_q_kvar = (
        float(net.res_trafo["q_lv_mvar"].iloc[0]) * 1000.0 / scale.power_scale)

    return {
        "scenario": scenario,
        "houses": meta["houses"],
        "route_mode": meta["route_mode"],
        "lv_total_route_m": meta["lv_total_route_m"],
        "load_kw": float(total_load_kw),
        "inverter_ac_kw": float(inverter_ac_kw),
        "inverter_q_kvar": float(inverter_q_kvar),
        "load_power_factor": net_cfg.load_power_factor,
        "net_demand_before_losses_kw": float(total_load_kw) - float(inverter_ac_kw),
        "pcc_import_physical_kw": ext_import_kw,
        "pcc_import_physical_kvar": ext_import_kvar,
        "transformer_p_lv_kw": trafo_p_kw,
        "transformer_q_lv_kvar": trafo_q_kvar,
        "transformer_apparent_kva": math.hypot(trafo_p_kw, trafo_q_kvar),
        "transformer_loading_pct": trafo_loading,
        "transformer_lv_current_a": trafo_lv_current_a,
        "transformer_loading_limit_pct": limit_pct,
        "max_mv_line_loading_pct": mv_loading,
        "max_lv_line_loading_pct": lv_loading,
        "min_lv_vm_pu": min_vm,
        "max_lv_vm_pu": max_vm,
        "lv_drop_screen_ok": min_vm >= net_cfg.lv_screen_min_pu,
        "lv_rise_screen_ok": max_vm <= net_cfg.lv_screen_max_pu,
        "transformer_nominal_ok": trafo_loading <= 100.0,
        "transformer_permissible_ok": trafo_loading <= limit_pct,
        "line_loading_ok": (mv_loading <= net_cfg.line_limit_percent
                            and lv_loading <= net_cfg.line_limit_percent),
    }


def run_snapshot(cfg: Case1Config, houses: int, scenario: str,
                 house_loads_kw=None, total_load_kw: float | None = None,
                 inverter_ac_kw: float = 0.0, inverter_q_kvar: float = 0.0,
                 route_mode: str = "fixed",
                 expansion_segment_m: float | None = None,
                 load_pf: float | None = None,
                 net=None):
    """Solve one operating point. Pass `net` to reuse a built network."""
    own_net = net is None
    if own_net:
        net = build_group_network(cfg, houses, route_mode, expansion_segment_m)

    set_operating_point(net, cfg, house_loads_kw=house_loads_kw,
                        total_load_kw=total_load_kw,
                        inverter_ac_kw=inverter_ac_kw,
                        inverter_q_kvar=inverter_q_kvar, load_pf=load_pf)
    solve(net)

    if house_loads_kw is not None:
        total_load_kw = float(np.asarray(house_loads_kw, dtype=float).sum())

    result = extract_snapshot(net, cfg, scenario, total_load_kw,
                              inverter_ac_kw, inverter_q_kvar)
    return net, result


# ---------------------------------------------------------------------------
# Equivalent-circuit validation (from v5)
# ---------------------------------------------------------------------------


def validate_single_phase_equivalent(cfg: Case1Config,
                                     test_load_kw: float = 0.5,
                                     load_pf: float = 0.90) -> pd.DataFrame:
    """
    Check the sqrt(3) / 3x / loop-impedance construction once against a direct
    single-phase I*(R cos phi + X sin phi) voltage-drop calculation.

    A diagnostic of the representation, not an operating scenario.
    """
    net = build_group_network(cfg, 1, route_mode="fixed")
    set_operating_point(net, cfg, house_loads_kw=np.array([float(test_load_kw)]),
                        inverter_ac_kw=0.0, load_pf=load_pf)
    solve(net)

    meta = net._san_rafael
    source_vm = float(net.res_bus.at[meta["trafo_lv_bus"], "vm_pu"])
    end_vm = float(net.res_bus.at[meta["lv_bus_indices"][-1], "vm_pu"])

    phi = math.acos(load_pf)
    lv_kv = cfg.site.lv_voltage_kv
    current_a = float(test_load_kw) * 1000.0 / (lv_kv * 1000.0 * load_pf)

    route_km = float(meta["lv_total_route_m"]) / 1000.0
    r_loop = cfg.network.lv_r_loop_ohm_per_km * route_km
    x_loop = cfg.network.lv_x_loop_ohm_per_km * route_km
    delta_v = current_a * (r_loop * math.cos(phi) + x_loop * math.sin(phi))

    physical_source_v = source_vm * lv_kv * 1000.0
    manual_end_vm = (physical_source_v - delta_v) / (lv_kv * 1000.0)

    return pd.DataFrame([{
        "test_load_kw": float(test_load_kw),
        "load_power_factor": float(load_pf),
        "physical_current_a": current_a,
        "source_lv_vm_pu": source_vm,
        "manual_end_vm_pu": manual_end_vm,
        "pandapower_end_vm_pu": end_vm,
        "difference_pct": 100.0 * (end_vm - manual_end_vm) / manual_end_vm,
        "validation_note": (
            "First-order single-phase I*Z comparison; a small residual "
            "difference is expected because pandapower solves the nonlinear "
            "AC power flow."),
    }])


# ---------------------------------------------------------------------------
# Annual and critical-hour runs driven by a Case 1 dispatch
# ---------------------------------------------------------------------------

CRITICAL_SELECTORS: dict[str, tuple[str, str]] = {
    "max_import": ("pcc_import_kw", "max"),
    "max_export": ("pcc_import_kw", "min"),
    "max_inverter_output": ("inverter_ac_output_kw", "max"),
    "max_load": ("load_kw", "max"),
    "max_net_injection": ("net_injection_kw", "max"),
}


def critical_hours(dispatch: pd.DataFrame) -> dict[str, pd.Timestamp]:
    """Timestamps of the network-critical hours of a dispatch time series."""
    work = dispatch.copy()
    work["net_injection_kw"] = (
        work["inverter_ac_output_kw"] - work["served_load_kw"])

    out = {}
    for label, (column, mode) in CRITICAL_SELECTORS.items():
        series = pd.to_numeric(work[column], errors="coerce")
        out[label] = series.idxmax() if mode == "max" else series.idxmin()
    return out


def run_dispatch_hours(cfg: Case1Config, dispatch: pd.DataFrame,
                       household_loads: pd.DataFrame, houses: int,
                       timestamps, scenario: str = "CASE1_DISPATCH",
                       inverter_pf: float = 1.0,
                       route_mode: str = "fixed") -> pd.DataFrame:
    """
    Power-flow the selected hours of a Case 1 dispatch.

    The inverter sgen is driven by `inverter_ac_output_kw`, which already
    contains PV and battery discharge. Battery CHARGING does not appear as an
    AC load because the battery is DC-coupled, so it is correctly absent.
    """
    net = build_group_network(cfg, houses, route_mode)
    rows = []

    for ts in pd.DatetimeIndex(timestamps):
        row = dispatch.loc[ts]
        loads = np.array(
            [float(household_loads.at[ts, f"house_{h}_kw"])
             for h in range(1, houses + 1)], dtype=float)

        # Scale household loads so their sum matches the served load of the
        # dispatch (shedding and load management change the served total).
        raw_total = loads.sum()
        served = float(row["served_load_kw"])
        if raw_total > 0 and abs(served - raw_total) > 1e-9:
            loads = loads * (served / raw_total)

        p_inv = float(row["inverter_ac_output_kw"])
        q_inv = (0.0 if inverter_pf >= 1.0
                 else -q_from_p_pf(p_inv, inverter_pf))

        _, result = run_snapshot(cfg, houses, scenario,
                                 house_loads_kw=loads,
                                 inverter_ac_kw=p_inv,
                                 inverter_q_kvar=q_inv,
                                 route_mode=route_mode, net=net)
        result["timestamp"] = ts
        result["inverter_power_factor"] = inverter_pf
        result["dispatch_pcc_import_kw"] = float(row["pcc_import_kw"])
        result["battery_dc_kw"] = float(row.get("battery_dc_kw", np.nan))
        result["pv_curtailed_kw"] = float(row.get("pv_curtailed_kw", np.nan))
        rows.append(result)

    return pd.DataFrame(rows)


def run_annual_from_dispatch(cfg: Case1Config, dispatch: pd.DataFrame,
                             household_loads: pd.DataFrame, houses: int,
                             scenario: str = "CASE1_ANNUAL",
                             inverter_pf: float = 1.0,
                             step_hours: int = 1) -> pd.DataFrame:
    """
    Power-flow a whole dispatch year.

    `step_hours` > 1 subsamples for speed; the critical hours should always be
    screened separately at full resolution with `run_dispatch_hours`.
    """
    timestamps = dispatch.index[::int(step_hours)]
    return run_dispatch_hours(cfg, dispatch, household_loads, houses,
                              timestamps, scenario=scenario,
                              inverter_pf=inverter_pf)


def summarise_network_results(results: pd.DataFrame, cfg: Case1Config) -> dict:
    net_cfg = cfg.network
    limit_pct = 100.0 * cfg.transformer.loading_limit_pu
    return {
        "hours_screened": int(len(results)),
        "min_lv_vm_pu": float(results["min_lv_vm_pu"].min()),
        "max_lv_vm_pu": float(results["max_lv_vm_pu"].max()),
        "max_transformer_loading_pct": float(results["transformer_loading_pct"].max()),
        "max_transformer_apparent_kva": float(results["transformer_apparent_kva"].max()),
        "max_lv_line_loading_pct": float(results["max_lv_line_loading_pct"].max()),
        "max_mv_line_loading_pct": float(results["max_mv_line_loading_pct"].max()),
        "max_import_kw": float(results["pcc_import_physical_kw"].max()),
        "max_export_kw": float(-results["pcc_import_physical_kw"].min()),
        "hours_below_voltage_screen": int(
            (results["min_lv_vm_pu"] < net_cfg.lv_screen_min_pu).sum()),
        "hours_above_voltage_screen": int(
            (results["max_lv_vm_pu"] > net_cfg.lv_screen_max_pu).sum()),
        "hours_above_permissible_loading": int(
            (results["transformer_loading_pct"] > limit_pct).sum()),
        "hours_above_nominal_loading": int(
            (results["transformer_loading_pct"] > 100.0).sum()),
        "voltage_screen_ok": bool(
            (results["min_lv_vm_pu"] >= net_cfg.lv_screen_min_pu).all()
            and (results["max_lv_vm_pu"] <= net_cfg.lv_screen_max_pu).all()),
        "transformer_permissible_ok": bool(
            (results["transformer_loading_pct"] <= limit_pct).all()),
        "line_loading_ok": bool(results["line_loading_ok"].all()),
    }


# ---------------------------------------------------------------------------
# Feasibility frontier
# ---------------------------------------------------------------------------


def feasibility_screen(cfg: Case1Config, study, specs_and_dispatches,
                       inverter_pf: float = 1.0) -> pd.DataFrame:
    """
    Screen the network-critical hours of each candidate configuration.

    `specs_and_dispatches` is an iterable of
        (label, houses, resolved_system, dispatch_table)

    Returns one row per configuration with the binding electrical result and
    an overall electrically_feasible flag, which is the answer the research
    question needs: how far PV and BESS can grow behind the 5 kVA transformer
    before the NETWORK, not the energy balance, stops it.
    """
    rows = []
    for label, houses, system, dispatch in specs_and_dispatches:
        hours = critical_hours(dispatch)
        results = run_dispatch_hours(
            cfg, dispatch, study.ts, houses, list(hours.values()),
            scenario=label, inverter_pf=inverter_pf)
        results["critical_condition"] = list(hours.keys())

        summary = summarise_network_results(results, cfg)
        rows.append({
            "case": label,
            "houses": houses,
            "panel_count": system.spec.panel_count,
            "pv_kwp": system.pv_kwp,
            "bess_modules": system.spec.bess_modules,
            "inverter_ac_kw": system.inverter_ac_kw,
            "export_limit_kw": system.export_limit_kw,
            "import_limit_kw": system.import_limit_kw,
            "inverter_power_factor": inverter_pf,
            **summary,
            "electrically_feasible": bool(
                summary["voltage_screen_ok"]
                and summary["transformer_permissible_ok"]
                and summary["line_loading_ok"]),
            "binding_constraint": _binding_constraint(summary, cfg),
        })
    return pd.DataFrame(rows)


def _binding_constraint(summary: dict, cfg: Case1Config) -> str:
    net_cfg = cfg.network
    limit_pct = 100.0 * cfg.transformer.loading_limit_pu
    reasons = []
    if summary["max_transformer_loading_pct"] > limit_pct:
        reasons.append("transformer loading")
    if summary["max_lv_vm_pu"] > net_cfg.lv_screen_max_pu:
        reasons.append("LV voltage rise")
    if summary["min_lv_vm_pu"] < net_cfg.lv_screen_min_pu:
        reasons.append("LV voltage drop")
    if not summary["line_loading_ok"]:
        reasons.append("conductor loading")
    return ", ".join(reasons) if reasons else "none"
