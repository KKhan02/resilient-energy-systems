"""
Causal, no-forecast rule-based dispatch.

WHY THIS MODULE EXISTS
----------------------
The PyPSA model in `lp_model` solves the whole year in one linear program, so
its dispatch has PERFECT FORESIGHT of PV and demand. That is a legitimate
upper bound on achievable performance, but it is NOT a realistic reactive
controller and must never be presented as one.

Case 1 explicitly forbids solar forecasting (that is Case 2's rolling-horizon
MPC). Every controller here is therefore CAUSAL: at hour t it uses only
quantities observable at or before t - the current PV output, the current
demand, the current state of charge, and trailing history. No future value is
read.

PHYSICAL MODEL
--------------
DC-coupled hybrid inverter, matching the Deye SUN-*-SG02LP2-US topology:

                 PV (DC)
                    |
      +-------------+-------------+
      |                           |
  battery (DC)              inverter  --AC-->  community load
                                 |                   |
                                 +---- PCC ----------+---- EPM grid

Consequences the model respects:

  * PV DC above the inverter AC rating can still charge the battery, because
    the battery is on the DC bus. Clipping only destroys energy once the
    battery cannot absorb it.
  * The inverter AC port is SHARED by PV and battery discharge, so a
    saturated AC port can force grid import even while the battery is full.
  * The battery is never charged from the grid (community rule).

Per hour, with dt = 1 h and all powers in kW:

    pv_to_inverter_dc + pv_to_battery_dc + curtailed_dc = pv_available_dc
    ac_out = (pv_to_inverter_dc + battery_to_inverter_dc) * eta_inverter
    ac_out <= inverter_ac_kw
    served_load = ac_out + grid_import - grid_export
    e_{t+1} = e_t + pv_to_battery_dc * eta - battery_to_inverter_dc / eta

where e is usable stored energy above the minimum state of charge and eta is
the one-way efficiency sqrt(round-trip).

CONTROLLERS
-----------
CONVENTIONAL       PV -> load -> battery -> export; grid last. No reserve.
EXPORT_LIMITED     As above with a lower PCC export cap.
FIXED_RESERVE      Will not discharge below a fixed emergency state of charge
                   while the grid is available.
ADAPTIVE_RESERVE   Reserve rises when TRAILING solar availability falls. Uses
                   an expanding mean of past days only, so it is causal.
ADAPTIVE_PLUS_LM   Adaptive reserve plus same-day deferrable load management.
                   Deferrable demand is pushed out of high-import hours and
                   flushed by the end of each day, so annual served energy is
                   unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import Case1Config
from .lp_model import ResolvedSystem, add_pcc_apparent_power

CONTROLLERS = (
    "CONVENTIONAL",
    "EXPORT_LIMITED",
    "FIXED_RESERVE",
    "ADAPTIVE_RESERVE",
    "ADAPTIVE_PLUS_LM",
)


@dataclass
class ControlParams:
    """Controller settings. All thresholds are causal."""

    name: str = "CONVENTIONAL"

    # Operating reserve while the grid is available, as actual state of charge.
    reserve_soc_pu: float = 0.0           # 0 means "use down to minimum SOC"
    adaptive: bool = False
    adaptive_reserve_min_pu: float = 0.30
    adaptive_reserve_max_pu: float = 0.75
    adaptive_solar_index_days: int = 3
    adaptive_reserve_gain: float = 0.60

    # Deferrable load management
    load_management: bool = False
    deferrable_fraction: float = 0.0
    deferrable_max_defer_hours: int = 8
    import_trigger_pu: float = 0.80

    # Export cap override for the export-limited strategy, kW at the PCC.
    export_limit_kw: float | None = None

    # Outage / islanding behaviour
    critical_fraction: float = 0.30

    @classmethod
    def from_config(cls, name: str, cfg: Case1Config,
                    export_limit_kw: float | None = None) -> "ControlParams":
        d = cfg.dispatch
        dem = cfg.demand
        base = dict(
            name=name,
            adaptive_reserve_min_pu=d.adaptive_reserve_min_pu,
            adaptive_reserve_max_pu=d.adaptive_reserve_max_pu,
            adaptive_solar_index_days=d.adaptive_solar_index_days,
            adaptive_reserve_gain=d.adaptive_reserve_gain,
            deferrable_max_defer_hours=dem.deferrable_max_defer_hours,
            import_trigger_pu=d.load_management_import_trigger_pu,
            critical_fraction=dem.critical_load_fraction,
            export_limit_kw=export_limit_kw,
        )
        if name == "CONVENTIONAL":
            return cls(**base)
        if name == "EXPORT_LIMITED":
            return cls(**base)
        if name == "FIXED_RESERVE":
            return cls(reserve_soc_pu=d.fixed_reserve_soc_pu, **base)
        if name == "ADAPTIVE_RESERVE":
            return cls(adaptive=True, **base)
        if name == "ADAPTIVE_PLUS_LM":
            return cls(adaptive=True, load_management=True,
                       deferrable_fraction=dem.deferrable_load_fraction, **base)
        raise ValueError(f"Unknown controller: {name}. Choose from {CONTROLLERS}")


# ---------------------------------------------------------------------------
# Causal trailing solar-availability index
# ---------------------------------------------------------------------------


def trailing_solar_index(pv_available_kw: pd.Series, window_days: int) -> pd.Series:
    """
    Causal solar-availability index in [0, inf):

        index_t = (mean daily PV energy over the last `window_days` COMPLETED
                   days) / (mean daily PV energy over ALL earlier completed days)

    Only completed past days enter either term, so no future information is
    used. During the warm-up, before enough history exists, the index is 1.0,
    which makes the adaptive controller behave like the fixed-reserve one.
    """
    daily = pv_available_kw.resample("D").sum()

    trailing = daily.shift(1).rolling(window_days, min_periods=window_days).mean()
    baseline = daily.shift(1).expanding(min_periods=window_days).mean()

    index = (trailing / baseline).replace([np.inf, -np.inf], np.nan).fillna(1.0)
    index = index.clip(lower=0.0, upper=3.0)

    # Broadcast the daily value to every hour of that day.
    return index.reindex(pv_available_kw.index.normalize()).to_numpy()


# ---------------------------------------------------------------------------
# Core simulator
# ---------------------------------------------------------------------------


def simulate(load_kw: pd.Series,
             pv_available_kw: pd.Series,
             system: ResolvedSystem,
             cfg: Case1Config,
             homer: dict,
             params: ControlParams,
             initial_soc_pu: float | None = None,
             grid_available: pd.Series | None = None,
             allow_unserved: bool | None = None,
             cycles: int = 2) -> pd.DataFrame:
    """
    Run a causal hourly simulation.

    Parameters
    ----------
    grid_available
        Boolean per hour. False means the EPM grid is unavailable (outage), so
        import and export are both zero and the battery may be used down to
        its minimum state of charge regardless of the operating reserve.
    initial_soc_pu
        Actual state of charge at the start. When None, the simulation is run
        `cycles` times and the final state of charge of one pass seeds the
        next, so the annual result is near-periodic and comparable with the
        LP's cyclic state-of-charge constraint. Only the last pass is returned.
    allow_unserved
        When None, unserved energy is permitted only while the grid is
        unavailable. Any unserved energy in a grid-connected hour is a model
        warning, not a design result, and is reported in the table.

    Returns
    -------
    The standard dispatch table (see kpi.REQUIRED_COLUMNS) plus the causal
    diagnostics: operating reserve, curtailment reason, deferred backlog.
    """
    index = load_kw.index
    if not index.equals(pv_available_kw.index):
        raise ValueError("load and PV series must share an index")

    eta_inv = float(homer["inverter_efficiency"])
    bank = system.battery
    eta_bat = bank.one_way_efficiency if bank.module_count > 0 else 1.0
    e_max = float(bank.usable_kwh)
    p_bat = float(bank.dc_power_kw)
    min_soc = float(bank.min_soc_pu)
    inv_ac = float(system.inverter_ac_kw)

    export_cap = (
        float(params.export_limit_kw) if params.export_limit_kw is not None
        else float(system.export_limit_kw)
    )
    import_cap = float(system.import_limit_kw)

    if grid_available is None:
        grid_on = np.ones(len(index), dtype=bool)
    else:
        grid_on = np.asarray(grid_available.reindex(index).fillna(True), dtype=bool)

    if allow_unserved is None:
        allow_unserved = bool((~grid_on).any())

    load = load_kw.to_numpy(dtype=float)
    pv = pv_available_kw.to_numpy(dtype=float)

    # Firm / deferrable split for the load-management controller.
    if params.load_management and params.deferrable_fraction > 0:
        firm = load * (1.0 - params.deferrable_fraction)
        deferrable = load * params.deferrable_fraction
    else:
        firm = load.copy()
        deferrable = np.zeros_like(load)

    solar_index = (
        trailing_solar_index(pv_available_kw, params.adaptive_solar_index_days)
        if params.adaptive else np.ones(len(index), dtype=float)
    )

    hour_of_day = index.hour.to_numpy()

    def actual_to_usable(soc_pu: float) -> float:
        if e_max <= 0:
            return 0.0
        return (soc_pu - min_soc) / (1.0 - min_soc) * e_max

    def usable_to_actual(e: float) -> float:
        if e_max <= 0:
            return np.nan
        return min_soc + (e / e_max) * (1.0 - min_soc)

    n_hours = len(index)
    passes = 1 if initial_soc_pu is not None else max(1, int(cycles))

    if initial_soc_pu is not None:
        e_start = actual_to_usable(float(initial_soc_pu))
    else:
        # Neutral start: half the usable capacity. The warm-up pass removes
        # sensitivity to this choice.
        e_start = 0.5 * e_max

    columns = [
        "load_kw", "firm_load_kw", "deferrable_served_kw", "deferred_backlog_kwh",
        "served_load_kw", "unserved_kw", "critical_unserved_kw",
        "pv_available_kw", "pv_dc_kw", "pv_curtailed_kw",
        "pv_to_load_dc_kw", "pv_to_battery_dc_kw", "pv_to_export_dc_kw",
        "inverter_dc_input_kw", "inverter_ac_output_kw",
        "battery_dc_kw", "battery_charge_kw", "battery_discharge_kw",
        "battery_usable_soc_kwh", "battery_actual_soc_pu",
        "operating_reserve_soc_pu", "grid_available",
        "pcc_import_kw", "grid_import_kw", "grid_export_kw",
        "curtailment_reason",
    ]

    for pass_no in range(passes):
        e = e_start
        backlog = 0.0
        deferred_age = 0
        rec: dict[str, list] = {c: [] for c in columns}

        for t in range(n_hours):
            grid_now = bool(grid_on[t])
            pv_avail = pv[t]

            # ---- operating reserve ------------------------------------
            if not grid_now:
                reserve = min_soc          # emergency: full usable depth
            elif params.adaptive:
                reserve = float(np.clip(
                    params.adaptive_reserve_min_pu
                    + params.adaptive_reserve_gain * (1.0 - solar_index[t]),
                    params.adaptive_reserve_min_pu,
                    params.adaptive_reserve_max_pu,
                ))
            else:
                reserve = max(min_soc, float(params.reserve_soc_pu))
            e_floor = actual_to_usable(reserve)

            # ---- how much demand to present this hour -----------------
            firm_now = firm[t]
            deferrable_now = deferrable[t]

            pv_ac_possible = min(pv_avail * eta_inv, inv_ac)

            if params.load_management:
                headroom_ac = max(0.0, pv_ac_possible - firm_now)
                # Causal estimate of the import this hour would need if the
                # deferrable demand were served now.
                e_usable_now = max(0.0, e - e_floor)
                battery_ac_possible = min(
                    p_bat * eta_inv,
                    e_usable_now * eta_bat * eta_inv,
                    max(0.0, inv_ac - min(pv_ac_possible, firm_now)),
                )
                projected_import = max(
                    0.0, firm_now - pv_ac_possible - battery_ac_possible)
                trigger = params.import_trigger_pu * import_cap

                last_hour_of_day = hour_of_day[t] == 23
                force = (
                    last_hour_of_day
                    or deferred_age >= params.deferrable_max_defer_hours
                )

                if not grid_now:
                    # During an outage, defer rather than shed.
                    served_deferrable = min(headroom_ac, backlog + deferrable_now)
                elif force:
                    served_deferrable = backlog + deferrable_now
                elif projected_import > trigger:
                    served_deferrable = 0.0
                else:
                    served_deferrable = min(
                        backlog + deferrable_now,
                        max(deferrable_now, headroom_ac),
                    )

                served_deferrable = max(0.0, served_deferrable)
                backlog = max(0.0, backlog + deferrable_now - served_deferrable)
                deferred_age = 0 if backlog <= 1e-12 else deferred_age + 1
            else:
                served_deferrable = deferrable_now
                backlog = 0.0

            demand_now = firm_now + served_deferrable

            # ---- 1. PV serves demand ----------------------------------
            pv_to_load_ac = min(pv_ac_possible, demand_now)
            pv_to_load_dc = pv_to_load_ac / eta_inv if eta_inv > 0 else 0.0
            remaining_dc = max(0.0, pv_avail - pv_to_load_dc)

            # ---- 2. surplus PV charges the battery --------------------
            charge_dc = 0.0
            if e_max > 0 and p_bat > 0 and remaining_dc > 0:
                room_dc = max(0.0, (e_max - e) / eta_bat)
                charge_dc = min(remaining_dc, p_bat, room_dc)
                e += charge_dc * eta_bat
                remaining_dc -= charge_dc

            # ---- 3. residual PV exports -------------------------------
            ac_headroom = max(0.0, inv_ac - pv_to_load_ac)
            export_ac = 0.0
            export_dc = 0.0
            if grid_now and remaining_dc > 0 and export_cap > 0:
                export_ac = min(remaining_dc * eta_inv, ac_headroom, export_cap)
                export_dc = export_ac / eta_inv if eta_inv > 0 else 0.0
                remaining_dc -= export_dc

            curtailed_dc = max(0.0, remaining_dc)

            # ---- curtailment attribution ------------------------------
            # Surplus PV is only lost when the battery CANNOT absorb it AND
            # the AC path CANNOT take it. A single-cause label would be
            # misleading, so the combination of binding limits is recorded.
            if curtailed_dc <= 1e-9:
                reason = "none"
            else:
                if e_max <= 0:
                    storage = "no_battery"
                elif e >= e_max - 1e-9:
                    storage = "battery_full"
                elif charge_dc >= p_bat - 1e-9:
                    storage = "battery_power_limited"
                else:
                    storage = "battery_available"

                if not grid_now:
                    sink = "islanded"
                elif export_cap <= 1e-9:
                    sink = "export_blocked"
                elif export_ac >= export_cap - 1e-9:
                    sink = "export_at_cap"
                elif pv_to_load_ac + export_ac >= inv_ac - 1e-9:
                    sink = "inverter_ac_at_cap"
                else:
                    sink = "ac_path_available"

                reason = f"{storage}+{sink}"

            # ---- 4. battery covers the remaining deficit --------------
            deficit_ac = max(0.0, demand_now - pv_to_load_ac)
            discharge_dc = 0.0
            discharge_ac = 0.0
            if deficit_ac > 0 and e_max > 0 and p_bat > 0:
                e_usable = max(0.0, e - e_floor)
                dc_from_energy = e_usable * eta_bat
                ac_headroom_now = max(0.0, inv_ac - pv_to_load_ac - export_ac)
                discharge_ac = min(deficit_ac,
                                   min(p_bat, dc_from_energy) * eta_inv,
                                   ac_headroom_now)
                discharge_ac = max(0.0, discharge_ac)
                discharge_dc = discharge_ac / eta_inv if eta_inv > 0 else 0.0
                e -= discharge_dc / eta_bat
                e = max(0.0, e)
                deficit_ac -= discharge_ac

            # ---- 5. grid import, then unserved ------------------------
            grid_import = min(deficit_ac, import_cap) if grid_now else 0.0
            unserved = max(0.0, deficit_ac - grid_import)

            if unserved > 1e-9 and not allow_unserved:
                # Grid-connected hour that cannot be balanced: this is a
                # transformer-limit violation, recorded rather than hidden.
                pass

            served = demand_now - unserved

            # Critical load is served first, so shedding falls on the
            # non-critical component until that is exhausted.
            critical_now = load[t] * params.critical_fraction
            critical_unserved = max(0.0, critical_now - served)

            ac_out = pv_to_load_ac + export_ac + discharge_ac
            inverter_dc_input = pv_to_load_dc + export_dc + discharge_dc
            pcc = grid_import - export_ac

            rec["load_kw"].append(load[t])
            rec["firm_load_kw"].append(firm_now)
            rec["deferrable_served_kw"].append(served_deferrable)
            rec["deferred_backlog_kwh"].append(backlog)
            rec["served_load_kw"].append(served)
            rec["unserved_kw"].append(unserved)
            rec["critical_unserved_kw"].append(critical_unserved)
            rec["pv_available_kw"].append(pv_avail)
            rec["pv_dc_kw"].append(pv_avail - curtailed_dc)
            rec["pv_curtailed_kw"].append(curtailed_dc)
            rec["pv_to_load_dc_kw"].append(pv_to_load_dc)
            rec["pv_to_battery_dc_kw"].append(charge_dc)
            rec["pv_to_export_dc_kw"].append(export_dc)
            rec["inverter_dc_input_kw"].append(inverter_dc_input)
            rec["inverter_ac_output_kw"].append(ac_out)
            rec["battery_dc_kw"].append(discharge_dc - charge_dc)
            rec["battery_charge_kw"].append(charge_dc)
            rec["battery_discharge_kw"].append(discharge_dc)
            rec["battery_usable_soc_kwh"].append(e)
            rec["battery_actual_soc_pu"].append(usable_to_actual(e))
            rec["operating_reserve_soc_pu"].append(reserve)
            rec["grid_available"].append(grid_now)
            rec["pcc_import_kw"].append(pcc)
            rec["grid_import_kw"].append(grid_import)
            rec["grid_export_kw"].append(export_ac)
            rec["curtailment_reason"].append(reason)

        # Seed the next pass with the final state so the annual run is
        # near-periodic, mirroring the LP's cyclic state-of-charge condition.
        e_start = e

    dispatch = pd.DataFrame(rec, index=index)
    dispatch.index.name = "timestamp"
    dispatch = add_pcc_apparent_power(dispatch, cfg)

    dispatch.attrs["controller"] = params.name
    dispatch.attrs["export_limit_kw"] = export_cap
    dispatch.attrs["import_limit_kw"] = import_cap
    dispatch.attrs["warmup_passes"] = passes - 1
    dispatch.attrs["final_soc_pu"] = float(usable_to_actual(e))
    dispatch.attrs["deferred_backlog_end_kwh"] = float(backlog)
    return dispatch


# ---------------------------------------------------------------------------
# Consistency checks
# ---------------------------------------------------------------------------


def check_consistency(dispatch: pd.DataFrame, system: ResolvedSystem,
                      homer: dict, tol: float = 1e-7) -> pd.DataFrame:
    """
    Verify that a causal dispatch table obeys the physical model it claims.

    These are hard checks: a failure means the simulator, not the system, is
    wrong.
    """
    eta_inv = float(homer["inverter_efficiency"])
    bank = system.battery
    eta_bat = bank.one_way_efficiency if bank.module_count > 0 else 1.0

    rows = []

    def add(name, value, limit=tol, note=""):
        rows.append({
            "check": name,
            "value": float(value),
            "tolerance": limit,
            "status": "PASS" if abs(float(value)) <= limit else "FAIL",
            "note": note,
        })

    ac_residual = (
        dispatch["served_load_kw"]
        - dispatch["inverter_ac_output_kw"]
        - dispatch["grid_import_kw"]
        + dispatch["grid_export_kw"]
    )
    add("max |AC node residual| [kW]", ac_residual.abs().max(),
        note="served load = inverter AC + import - export")

    dc_residual = (
        dispatch["pv_available_kw"]
        - dispatch["pv_to_load_dc_kw"]
        - dispatch["pv_to_battery_dc_kw"]
        - dispatch["pv_to_export_dc_kw"]
        - dispatch["pv_curtailed_kw"]
    )
    add("max |PV DC split residual| [kW]", dc_residual.abs().max(),
        note="available = to load + to battery + to export + curtailed")

    inverter_residual = (
        dispatch["inverter_ac_output_kw"]
        - dispatch["inverter_dc_input_kw"] * eta_inv
    )
    add("max |inverter conversion residual| [kW]",
        inverter_residual.abs().max(), note=f"AC = DC x {eta_inv}")

    add("inverter AC overshoot [kW]",
        max(0.0, float(dispatch["inverter_ac_output_kw"].max())
            - system.inverter_ac_kw), 1e-9,
        note=f"rating {system.inverter_ac_kw:.3f} kW")

    add("import overshoot [kW]",
        max(0.0, float(dispatch["grid_import_kw"].max())
            - system.import_limit_kw), 1e-9,
        note=f"limit {system.import_limit_kw:.3f} kW")

    export_cap = float(dispatch.attrs.get("export_limit_kw",
                                          system.export_limit_kw))
    add("export overshoot [kW]",
        max(0.0, float(dispatch["grid_export_kw"].max()) - export_cap), 1e-9,
        note=f"limit {export_cap:.3f} kW")

    if bank.usable_kwh > 0:
        soc = dispatch["battery_usable_soc_kwh"]
        add("SOC below zero [kWh]", max(0.0, -float(soc.min())), 1e-9)
        add("SOC above usable capacity [kWh]",
            max(0.0, float(soc.max()) - bank.usable_kwh), 1e-9,
            note=f"usable {bank.usable_kwh:.3f} kWh")

        soc_residual = (
            soc.diff()
            - dispatch["battery_charge_kw"] * eta_bat
            + dispatch["battery_discharge_kw"] / eta_bat
        ).iloc[1:]
        add("max |SOC balance residual| [kWh]", soc_residual.abs().max(),
            note="e(t) - e(t-1) = charge x eta - discharge / eta")

        overlap = ((dispatch["battery_charge_kw"] > tol)
                   & (dispatch["battery_discharge_kw"] > tol)).sum()
        add("simultaneous charge and discharge hours", overlap, 0)

        power_overshoot = max(
            float(dispatch["battery_charge_kw"].max()),
            float(dispatch["battery_discharge_kw"].max()),
        ) - bank.dc_power_kw
        add("battery power overshoot [kW]", max(0.0, power_overshoot), 1e-9,
            note=f"limit {bank.dc_power_kw:.3f} kW")

    grid_hours = dispatch["grid_available"].astype(bool)
    add("unserved energy in grid-connected hours [kWh]",
        float(dispatch.loc[grid_hours, "unserved_kw"].sum()), 1e-6,
        note="non-zero means the import limit could not cover demand")

    add("export during outage hours [kWh]",
        float(dispatch.loc[~grid_hours, "grid_export_kw"].sum()), 1e-9)
    add("import during outage hours [kWh]",
        float(dispatch.loc[~grid_hours, "grid_import_kw"].sum()), 1e-9)

    served_total = float(dispatch["served_load_kw"].sum())
    demand_total = float(dispatch["load_kw"].sum())
    unserved_total = float(dispatch["unserved_kw"].sum())
    backlog_end = float(dispatch.attrs.get("deferred_backlog_end_kwh", 0.0))
    add("demand accounting residual [kWh]",
        demand_total - served_total - unserved_total - backlog_end, 1e-6,
        note="demand = served + unserved + deferred backlog remaining")

    return pd.DataFrame(rows)
