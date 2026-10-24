"""
Transformer-constrained PyPSA energy model.

Structure is carried over from PyPSA v18 (GRID_MV / COMMUNITY_AC / DC_BUS,
grid-last-resort priority, no AC-to-DC grid charging), with three Case 1
changes:

1. TRANSFORMER CONSTRAINT
   v18 limited active power at the PCC to 5.0 kW, i.e. it treated the 5 kVA
   nameplate as 5 kW. Case 1 applies an asymmetric, derated ACTIVE-power
   limit computed from the apparent-power rating:

       P_import_max = S_rated * k_loading * pf_import
       P_export_max = min(S_rated * k_loading * pf_export, export_control_kw)

   and additionally reports the apparent power and transformer loading that
   those flows imply, so the energy model and the power-flow model can be
   compared on the same quantity.

2. INVERTER LIMIT ON THE AC SIDE
   v18 set the inverter link p_nom to the converter rating, which limits the
   DC input, making the effective AC ceiling 0.95 x nameplate. Case 1 limits
   the AC output to the datasheet rating. Set inverter_limit_side="dc" to
   reproduce v18 exactly.

3. EXPLICIT CURTAILMENT
   PV availability, dispatched PV and curtailed PV are reported separately,
   together with the DC headroom the battery absorbs above the inverter AC
   limit. v18 reported dispatched PV only.

Nothing here changes the PV resource, the demand model or the HOMER inputs.

IMPORTANT INTERPRETATION LIMIT: this is a linear program solved over the whole
year at once, so its dispatch has PERFECT FORESIGHT. It is an upper bound on
what any real controller can achieve, not a realistic reactive control scheme.
Causal, no-forecast controllers live in rule_dispatch.py and are what the
control comparison in objective 6 actually compares.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import (KW_TO_MW, KWH_TO_MWH, USD_PER_KWH_TO_USD_PER_MWH,
                     Case1Config)
from .homer import BatteryBank, battery_bank, battery_bank_parameters_v18


def require_pypsa():
    try:
        import pypsa
        return pypsa
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Install with: pip install pypsa highspy") from exc


# ---------------------------------------------------------------------------
# System specification
# ---------------------------------------------------------------------------


@dataclass
class SystemSpec:
    """A single PV / BESS / inverter / grid-interface configuration."""

    houses: int = 4
    panel_count: int = 12
    bess_modules: int = 4
    inverter_key: str = "SUN-5K"

    # Explicit overrides. When None they come from config / datasheet.
    inverter_ac_kw: float | None = None
    battery_power_kw: float | None = None
    import_limit_kw: float | None = None
    export_limit_kw: float | None = None

    allow_grid_export: bool = True
    islanded: bool = False
    allow_load_shedding: bool = False
    initial_actual_soc_pu: float | None = None

    # Validation / compatibility switches
    inverter_limit_side: str = "ac"      # "ac" (Case 1) or "dc" (v18)
    battery_sizing: str = "case1"        # "case1" or "v18"

    label: str = "S2_REFERENCE"

    def pv_kwp(self, module_rated_w: float = 435.0) -> float:
        return self.panel_count * module_rated_w / 1000.0


@dataclass
class ResolvedSystem:
    """SystemSpec resolved against the datasheet and the transformer limits."""

    spec: SystemSpec
    pv_kwp: float
    inverter_ac_kw: float
    inverter_max_pv_dc_kw: float
    inverter_model_name: str
    battery: BatteryBank
    import_limit_kw: float
    export_limit_kw: float
    dc_ac_ratio: float
    hardware_feasible: bool
    hardware_notes: list[str] = field(default_factory=list)

    def as_row(self) -> dict:
        return {
            "label": self.spec.label,
            "houses": self.spec.houses,
            "panel_count": self.spec.panel_count,
            "pv_kwp": self.pv_kwp,
            "bess_modules": self.spec.bess_modules,
            "bess_nominal_kwh": self.battery.nominal_kwh,
            "bess_usable_kwh": self.battery.usable_kwh,
            "bess_dc_power_kw": self.battery.dc_power_kw,
            "bess_power_limited_by": self.battery.binding_power_limit,
            "inverter_key": self.spec.inverter_key,
            "inverter_model": self.inverter_model_name,
            "inverter_ac_kw": self.inverter_ac_kw,
            "inverter_max_pv_dc_kw": self.inverter_max_pv_dc_kw,
            "dc_ac_ratio": self.dc_ac_ratio,
            "import_limit_kw": self.import_limit_kw,
            "export_limit_kw": self.export_limit_kw,
            "hardware_feasible": self.hardware_feasible,
            "hardware_notes": "; ".join(self.hardware_notes),
        }


def resolve_system(spec: SystemSpec, cfg: Case1Config, homer: dict) -> ResolvedSystem:
    """
    Resolve a specification against the Deye datasheet limits and the
    transformer constraint. Hardware infeasibility is reported, never
    silently corrected.
    """
    hw = cfg.hardware
    model = hw.inverter(spec.inverter_key)

    pv_kwp = spec.panel_count * hw.module.rated_w / 1000.0
    inverter_ac_kw = (
        float(spec.inverter_ac_kw) if spec.inverter_ac_kw is not None
        else model.rated_ac_kw
    )

    notes: list[str] = []
    feasible = True

    if pv_kwp > model.max_pv_dc_kw + 1e-9:
        feasible = False
        notes.append(
            f"PV {pv_kwp:.2f} kWp exceeds {model.name} max PV input "
            f"{model.max_pv_dc_kw:.1f} kW"
        )

    port_kw = model.battery_power_kw(homer["battery_nominal_v"])

    if spec.battery_sizing == "v18":
        legacy = battery_bank_parameters_v18(homer, spec.bess_modules, inverter_ac_kw)
        bank = BatteryBank(
            module_count=spec.bess_modules,
            nominal_kwh=legacy["nominal_kwh"],
            usable_kwh=legacy["usable_kwh"],
            module_dc_power_kw=(homer["battery_nominal_v"]
                                * homer["battery_max_charge_current_a"] / 1000),
            bank_dc_power_kw=spec.bess_modules * (
                homer["battery_nominal_v"] * homer["battery_max_charge_current_a"] / 1000),
            inverter_battery_port_kw=inverter_ac_kw,
            dc_power_kw=legacy["dc_power_kw"],
            min_soc_pu=homer["battery_min_soc_pu"],
            roundtrip_efficiency=homer["battery_roundtrip_efficiency"],
        )
    else:
        bank = battery_bank(
            homer, spec.bess_modules, port_kw,
            power_override_kw=(spec.battery_power_kw
                               if spec.battery_power_kw is not None
                               else hw.battery_power_kw_override),
        )
        if bank.dc_power_kw > port_kw + 1e-9:
            feasible = False
            notes.append(
                f"battery power {bank.dc_power_kw:.2f} kW exceeds {model.name} "
                f"battery port {port_kw:.2f} kW"
            )

    import_limit = (
        float(spec.import_limit_kw) if spec.import_limit_kw is not None
        else cfg.import_limit_kw
    )
    export_limit = (
        float(spec.export_limit_kw) if spec.export_limit_kw is not None
        else cfg.export_limit_kw
    )
    if spec.islanded or not spec.allow_grid_export:
        export_limit = 0.0
    if spec.islanded:
        import_limit = 0.0

    return ResolvedSystem(
        spec=spec,
        pv_kwp=pv_kwp,
        inverter_ac_kw=inverter_ac_kw,
        inverter_max_pv_dc_kw=model.max_pv_dc_kw,
        inverter_model_name=model.name,
        battery=bank,
        import_limit_kw=import_limit,
        export_limit_kw=export_limit,
        dc_ac_ratio=(pv_kwp / inverter_ac_kw if inverter_ac_kw > 0 else np.nan),
        hardware_feasible=feasible,
        hardware_notes=notes,
    )


# ---------------------------------------------------------------------------
# Network builder
# ---------------------------------------------------------------------------


def build_network(ts: pd.DataFrame,
                  pv_per_kwp: pd.Series,
                  system: ResolvedSystem,
                  cfg: Case1Config,
                  homer: dict,
                  load_series_kw: pd.Series | None = None):
    """Build the transformer-constrained PyPSA network for one system."""
    from .demand import group_load_kw

    pypsa = require_pypsa()
    spec = system.spec
    disp = cfg.dispatch

    n = pypsa.Network()
    n.set_snapshots(ts.index)

    for bus, carrier in (("GRID_MV", "AC"), ("COMMUNITY_AC", "AC"), ("DC_BUS", "DC")):
        n.add("Bus", bus, x=cfg.site.trafo_lon, y=cfg.site.trafo_lat, carrier=carrier)

    # Grid import is deliberately expensive in the dispatch objective: this is
    # the operating-priority coefficient, not a tariff.
    n.add("Generator", "GRID_IMPORT", bus="GRID_MV",
          p_nom=homer["grid_purchase_capacity_kw"] * KW_TO_MW,
          marginal_cost=disp.grid_last_resort_penalty_usd_per_kwh
          * USD_PER_KWH_TO_USD_PER_MWH)

    # Transformer point of common coupling: asymmetric derated active-power
    # limits derived from the 5 kVA apparent-power rating.
    pcc_nom_kw = max(system.import_limit_kw, system.export_limit_kw, 1e-9)
    n.add("Link", "TRAFO_PCC", bus0="GRID_MV", bus1="COMMUNITY_AC",
          p_nom=pcc_nom_kw * KW_TO_MW,
          p_min_pu=-system.export_limit_kw / pcc_nom_kw,
          p_max_pu=system.import_limit_kw / pcc_nom_kw,
          efficiency=1.0)

    n.add("Generator", "GRID_EXPORT", bus="GRID_MV",
          p_nom=system.export_limit_kw * KW_TO_MW,
          p_min_pu=-1.0 if system.export_limit_kw > 0 else 0.0,
          p_max_pu=0.0,
          marginal_cost=disp.residual_export_priority_value_usd_per_kwh
          * USD_PER_KWH_TO_USD_PER_MWH)

    if load_series_kw is None:
        load_kw = group_load_kw(ts, spec.houses)
    else:
        load_kw = pd.Series(np.asarray(load_series_kw, dtype=float), index=ts.index)
        if len(load_kw) != len(ts):
            raise ValueError("load_series_kw length must match ts")

    n.add("Load", "COMMUNITY_LOAD", bus="COMMUNITY_AC", p_set=load_kw * KW_TO_MW)

    if system.pv_kwp > 0:
        n.add("Generator", "PV_DC", bus="DC_BUS",
              p_nom=system.pv_kwp * KW_TO_MW,
              p_max_pu=pv_per_kwp.reindex(ts.index),
              marginal_cost=0.0)

    if system.inverter_ac_kw > 0:
        eta = homer["inverter_efficiency"]
        if spec.inverter_limit_side == "dc":
            # v18 behaviour: p_nom limits the DC input.
            link_p_nom_kw = system.inverter_ac_kw
        elif spec.inverter_limit_side == "ac":
            # Case 1: p_nom * efficiency limits the AC output.
            link_p_nom_kw = system.inverter_ac_kw / eta
        else:
            raise ValueError("inverter_limit_side must be 'ac' or 'dc'")

        n.add("Link", "INVERTER", bus0="DC_BUS", bus1="COMMUNITY_AC",
              p_nom=link_p_nom_kw * KW_TO_MW, efficiency=eta)

    bank = system.battery
    if bank.module_count > 0 and bank.dc_power_kw > 0:
        p_nom_mw = bank.dc_power_kw * KW_TO_MW
        usable_mwh = bank.usable_kwh * KWH_TO_MWH
        eta_one_way = bank.one_way_efficiency

        storage_kwargs = dict(
            bus="DC_BUS",
            p_nom=p_nom_mw,
            max_hours=usable_mwh / p_nom_mw,
            efficiency_store=eta_one_way,
            efficiency_dispatch=eta_one_way,
            marginal_cost=homer["battery_wear_cost_usd_per_kwh"]
            * USD_PER_KWH_TO_USD_PER_MWH,
        )

        if spec.initial_actual_soc_pu is None:
            storage_kwargs["cyclic_state_of_charge"] = True
        else:
            min_soc = bank.min_soc_pu
            soc = float(spec.initial_actual_soc_pu)
            if not (min_soc - 1e-9 <= soc <= 1 + 1e-9):
                raise ValueError("Initial SOC out of range")
            usable_fraction = (soc - min_soc) / (1 - min_soc)
            storage_kwargs["cyclic_state_of_charge"] = False
            storage_kwargs["state_of_charge_initial"] = usable_mwh * usable_fraction

        n.add("StorageUnit", "BESS", **storage_kwargs)

    if spec.allow_load_shedding:
        n.add("Generator", "LOAD_SHEDDING", bus="COMMUNITY_AC",
              p_nom=max(load_kw.max() * 2, 1.0) * KW_TO_MW,
              marginal_cost=disp.unserved_energy_penalty_usd_per_kwh
              * USD_PER_KWH_TO_USD_PER_MWH)

    n.meta = {
        **system.as_row(),
        "islanded": spec.islanded,
        "allow_grid_export": spec.allow_grid_export,
        "grid_battery_charging_allowed": disp.allow_grid_battery_charging,
        "inverter_limit_side": spec.inverter_limit_side,
        "battery_sizing": spec.battery_sizing,
        "trafo_number": cfg.site.trafo_number,
        "trafo_node": cfg.site.trafo_node,
        "transformer_kva": cfg.site.transformer_kva,
        "pf_import": cfg.transformer.pf_import,
        "pf_export": cfg.transformer.pf_export,
        "loading_limit_pu": cfg.transformer.loading_limit_pu,
        "stochastic_seed": int(ts.attrs.get("stochastic_seed", -1)),
    }
    return n


def solve_network(n, cfg: Case1Config, quiet: bool = True):
    """
    Solve the LP.

    quiet=True silences the solver log and linopy's progress bars, which
    matters because the sweeps in this package solve hundreds of years.
    """
    solver_options = {}
    if quiet and cfg.dispatch.solver == "highs":
        solver_options["output_flag"] = False

    if not quiet:
        return n.optimize(solver_name=cfg.dispatch.solver,
                          solver_options=solver_options)

    import contextlib
    import io
    import logging
    import os

    buf = io.StringIO()
    previous = os.environ.get("TQDM_DISABLE")
    os.environ["TQDM_DISABLE"] = "1"
    loggers = ["linopy", "pypsa", "linopy.model", "linopy.io", "linopy.solvers"]
    levels = {name: logging.getLogger(name).level for name in loggers}
    try:
        for name in loggers:
            logging.getLogger(name).setLevel(logging.ERROR)
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            status = n.optimize(solver_name=cfg.dispatch.solver,
                                solver_options=solver_options)
    finally:
        for name, level in levels.items():
            logging.getLogger(name).setLevel(level)
        if previous is None:
            os.environ.pop("TQDM_DISABLE", None)
        else:
            os.environ["TQDM_DISABLE"] = previous

    condition = status[1] if isinstance(status, tuple) else str(status)
    if "optimal" not in str(condition).lower():
        raise RuntimeError(
            f"LP did not solve to optimality: {status}\n{buf.getvalue()[-2000:]}")
    return status


# ---------------------------------------------------------------------------
# Dispatch extraction and KPIs
# ---------------------------------------------------------------------------


def _energy_kwh(series_mw) -> float:
    return float(series_mw.sum() / KW_TO_MW)


def extract_dispatch(n, system: ResolvedSystem, cfg: Case1Config,
                     pv_per_kwp: pd.Series) -> pd.DataFrame:
    """Hourly dispatch in physical kW, plus the PCC apparent-power estimate."""
    idx = n.snapshots
    out = pd.DataFrame(index=idx)
    out.index.name = "timestamp"

    out["load_kw"] = n.loads_t.p["COMMUNITY_LOAD"] / KW_TO_MW

    out["pv_available_kw"] = (
        pv_per_kwp.reindex(idx).to_numpy(dtype=float) * system.pv_kwp
    )
    out["pv_dc_kw"] = (
        n.generators_t.p["PV_DC"] / KW_TO_MW
        if "PV_DC" in n.generators.index
        else 0.0
    )
    out["pv_curtailed_kw"] = (out["pv_available_kw"] - out["pv_dc_kw"]).clip(lower=0)

    if "INVERTER" in n.links.index:
        out["inverter_dc_input_kw"] = n.links_t.p0["INVERTER"] / KW_TO_MW
        out["inverter_ac_output_kw"] = -n.links_t.p1["INVERTER"] / KW_TO_MW
    else:
        out["inverter_dc_input_kw"] = 0.0
        out["inverter_ac_output_kw"] = 0.0

    if "BESS" in n.storage_units.index:
        out["battery_dc_kw"] = n.storage_units_t.p["BESS"] / KW_TO_MW
        soc_mwh = n.storage_units_t.state_of_charge["BESS"]
        usable_mwh = system.battery.usable_kwh * KWH_TO_MWH
        out["battery_usable_soc_kwh"] = soc_mwh / KWH_TO_MWH
        min_soc = system.battery.min_soc_pu
        out["battery_actual_soc_pu"] = (
            min_soc + (soc_mwh / usable_mwh) * (1 - min_soc)
        ).clip(lower=min_soc, upper=1.0)
    else:
        out["battery_dc_kw"] = 0.0
        out["battery_usable_soc_kwh"] = 0.0
        out["battery_actual_soc_pu"] = np.nan

    out["pcc_import_kw"] = n.links_t.p0["TRAFO_PCC"] / KW_TO_MW
    out["grid_import_kw"] = out["pcc_import_kw"].clip(lower=0)
    out["grid_export_kw"] = (-out["pcc_import_kw"]).clip(lower=0)

    if "LOAD_SHEDDING" in n.generators.index:
        out["unserved_kw"] = n.generators_t.p["LOAD_SHEDDING"] / KW_TO_MW
    else:
        out["unserved_kw"] = 0.0
    out["served_load_kw"] = out["load_kw"] - out["unserved_kw"]

    out = add_pcc_apparent_power(out, cfg)
    return out


def add_pcc_apparent_power(dispatch: pd.DataFrame, cfg: Case1Config) -> pd.DataFrame:
    """
    Estimate the apparent power and transformer loading implied by the solved
    active-power flows.

    Reactive power is reconstructed, not solved:
        Q_load = P_served_load * tan(acos(pf_import))
        Q_inverter = P_inverter_ac * tan(acos(pf_export))   (0 at unity)
        Q_pcc = Q_load - Q_inverter

    Network losses are not included. The authoritative apparent-power result
    is the pandapower stage; this estimate exists so the energy model can be
    checked against it.
    """
    tf = cfg.transformer
    tan_load = math.tan(math.acos(tf.pf_import)) if tf.pf_import < 1 else 0.0
    tan_inv = math.tan(math.acos(tf.pf_export)) if tf.pf_export < 1 else 0.0

    q_load = dispatch["served_load_kw"] * tan_load
    q_inv = dispatch["inverter_ac_output_kw"] * tan_inv

    dispatch["pcc_q_kvar_estimate"] = q_load - q_inv
    dispatch["pcc_apparent_kva_estimate"] = np.hypot(
        dispatch["pcc_import_kw"], dispatch["pcc_q_kvar_estimate"])
    dispatch["transformer_loading_pct_estimate"] = (
        100.0 * dispatch["pcc_apparent_kva_estimate"] / cfg.site.transformer_kva
    )
    return dispatch


def curtailment_attribution(dispatch: pd.DataFrame,
                            system: ResolvedSystem,
                            homer: dict,
                            tol: float = 1e-6) -> pd.DataFrame:
    """
    Classify each curtailed hour by the binding limit.

    Attribution is hierarchical and reported for diagnosis only; several
    limits can bind in the same hour, in which case the first match in this
    order is recorded: inverter AC, export limit, battery (full or at power
    limit), other.
    """
    curtailed = dispatch["pv_curtailed_kw"] > tol

    inverter_bound = (
        dispatch["inverter_ac_output_kw"] >= system.inverter_ac_kw - 1e-4
    )
    export_bound = (
        dispatch["grid_export_kw"] >= max(system.export_limit_kw, 0) - 1e-4
    ) & (system.export_limit_kw >= 0)

    charge_kw = (-dispatch["battery_dc_kw"]).clip(lower=0)
    battery_power_bound = charge_kw >= system.battery.dc_power_kw - 1e-4
    battery_full = dispatch["battery_actual_soc_pu"] >= 1.0 - 1e-6

    reason = pd.Series("none", index=dispatch.index, dtype=object)
    reason[curtailed] = "other"
    reason[curtailed & (battery_full | battery_power_bound)] = "battery_limited"
    reason[curtailed & export_bound] = "export_limited"
    reason[curtailed & inverter_bound] = "inverter_ac_limited"

    rows = []
    for label, mask in [
        ("inverter_ac_limited", reason == "inverter_ac_limited"),
        ("export_limited", reason == "export_limited"),
        ("battery_limited", reason == "battery_limited"),
        ("other", reason == "other"),
    ]:
        rows.append({
            "binding_limit": label,
            "hours": int(mask.sum()),
            "curtailed_kwh": float(dispatch.loc[mask, "pv_curtailed_kw"].sum()),
        })
    table = pd.DataFrame(rows)
    total = float(dispatch["pv_curtailed_kw"].sum())
    table["share_of_curtailed_pct"] = (
        100.0 * table["curtailed_kwh"] / total if total > 0 else 0.0
    )
    return table


def reconstruct_storage_charge_discharge(n, storage_name: str = "BESS"
                                         ) -> pd.DataFrame:
    """Recover separate charge/discharge from net power and the SOC equation."""
    if storage_name not in n.storage_units.index:
        return pd.DataFrame(index=n.snapshots,
                            data={"charge_mw": 0.0, "discharge_mw": 0.0})

    p = n.storage_units_t.p[storage_name].astype(float)
    soc = n.storage_units_t.state_of_charge[storage_name].astype(float)

    eta_store = float(n.storage_units.at[storage_name, "efficiency_store"])
    eta_dispatch = float(n.storage_units.at[storage_name, "efficiency_dispatch"])
    cyclic = bool(n.storage_units.at[storage_name, "cyclic_state_of_charge"])

    previous_soc = soc.shift(1)
    if cyclic:
        previous_soc.iloc[0] = soc.iloc[-1]
    else:
        previous_soc.iloc[0] = float(
            n.storage_units.at[storage_name, "state_of_charge_initial"])

    delta_soc = soc - previous_soc
    denominator = eta_store - 1.0 / eta_dispatch

    charge = (delta_soc + p / eta_dispatch) / denominator
    discharge = p + charge

    charge = charge.where(charge > 0.0, 0.0)
    discharge = discharge.where(discharge > 0.0, 0.0)

    return pd.DataFrame({"charge_mw": charge, "discharge_mw": discharge})
