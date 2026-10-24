"""
Design-space exploration for Case 1.

Four studies, in the order the objectives require:

  1. transformer_sensitivity   objective 3: how the 5 kVA apparent-power
                               constraint, its permissible loading factor and
                               the assumed power factor set the active-power
                               envelope, and what that does to the system.
  2. oversizing_grid           objective 2: PV 12/16/20/24 panels x BESS
                               energy x inverter rating, with datasheet
                               feasibility enforced and curtailment reported.
  3. control_comparison        objective 6: the five causal controllers plus
                               the perfect-foresight LP bound, same hardware.
  4. battery_power_study       objective 2: BESS energy and BESS charge or
                               discharge power varied independently.

Every study runs the CAUSAL controller as the decision engine, because a
perfect-foresight LP would overstate what any Case 1 controller can do. The
LP is reported alongside as an explicit upper bound.
"""

from __future__ import annotations

import itertools
from dataclasses import replace

import numpy as np
import pandas as pd

from . import economics as E
from . import kpi as K
from . import rule_dispatch as RD
from .config import Case1Config
from .lp_model import SystemSpec, curtailment_attribution
from .resource import PvProfile
from .study import Case1Study

DEFAULT_CONTROL = "CONVENTIONAL"


# ---------------------------------------------------------------------------
# One system, one controller
# ---------------------------------------------------------------------------


def run_system(study: Case1Study,
               spec: SystemSpec,
               control: str = DEFAULT_CONTROL,
               profile: PvProfile | None = None,
               houses: int | None = None,
               export_limit_kw: float | None = None,
               tariff_usd_per_kwh: float | None = None,
               with_economics: bool = True,
               return_dispatch: bool = False):
    """
    Score one configuration under one causal controller.

    Returns a KPI dict, or (KPI dict, dispatch table) when
    return_dispatch=True.
    """
    cfg = study.cfg
    profile = profile or study.decision_profile
    houses = houses if houses is not None else spec.houses

    system = study.resolve(spec)
    params = RD.ControlParams.from_config(control, cfg,
                                          export_limit_kw=export_limit_kw)

    load = study.load_kw(houses)
    pv = profile.dc_kw(system.pv_kwp)

    dispatch = RD.simulate(load, pv, system, cfg, study.homer, params)

    kpi = K.compute_kpis(dispatch, cfg, study.homer, system.as_row(),
                         case_name=spec.label, control_label=control,
                         critical_load_kw=study.critical_load_kw(houses))
    kpi["pv_profile"] = profile.label
    kpi["engine"] = "CAUSAL_RULE_BASED"
    kpi["perfect_foresight"] = False

    if with_economics:
        kpi.update(E.evaluate_economics(kpi, system, cfg, study.homer,
                                        tariff_usd_per_kwh=tariff_usd_per_kwh))

    if return_dispatch:
        return kpi, dispatch
    return kpi


def run_system_lp(study: Case1Study,
                  spec: SystemSpec,
                  profile: PvProfile | None = None,
                  with_economics: bool = True,
                  return_dispatch: bool = False):
    """Score one configuration with the perfect-foresight LP upper bound."""
    cfg = study.cfg
    profile = profile or study.decision_profile

    _, system, dispatch = study.run_lp(spec, profile=profile)
    kpi = K.compute_kpis(dispatch, cfg, study.homer, system.as_row(),
                         case_name=spec.label,
                         control_label="LP_PERFECT_FORESIGHT",
                         critical_load_kw=study.critical_load_kw(spec.houses))
    kpi["pv_profile"] = profile.label
    kpi["engine"] = "LP_PERFECT_FORESIGHT"
    kpi["perfect_foresight"] = True

    if with_economics:
        kpi.update(E.evaluate_economics(kpi, system, cfg, study.homer))

    if return_dispatch:
        return kpi, dispatch
    return kpi


# ---------------------------------------------------------------------------
# 1. Transformer constraint sensitivity (objective 3)
# ---------------------------------------------------------------------------


def transformer_sensitivity(study: Case1Study,
                            spec: SystemSpec | None = None,
                            control: str = DEFAULT_CONTROL,
                            houses_list: tuple[int, ...] = (4, 6, 8),
                            profile: PvProfile | None = None) -> pd.DataFrame:
    """
    Sweep the permissible loading factor and the assumed power factor.

    The 5 kVA nameplate is fixed. What changes is the ACTIVE-power envelope it
    implies:

        P_import_max = 5 kVA x k_loading x pf_import
        P_export_max = 5 kVA x k_loading x pf_export

    For each combination the study reports whether the group's demand can be
    served within that envelope, how much energy cannot, and the resulting
    transformer loading.
    """
    cfg = study.cfg
    base = spec or SystemSpec(label="TRAFO_SENS", houses=4, panel_count=12,
                              bess_modules=4, inverter_key="SUN-5K")
    rows = []

    for k_load, pf, houses in itertools.product(
            cfg.transformer.loading_limit_sensitivity,
            cfg.transformer.pf_import_sensitivity,
            houses_list):
        local_cfg = cfg.with_transformer(loading_limit_pu=k_load, pf_import=pf)
        local_study = study.with_config(local_cfg)

        label = f"TRAFO_k{k_load:.2f}_pf{pf:.2f}_{houses}HH"
        local_spec = replace(base, label=label, houses=houses,
                             import_limit_kw=None, export_limit_kw=None)

        kpi = run_system(local_study, local_spec, control=control,
                         profile=profile, houses=houses, with_economics=False)

        peak_load = float(study.load_kw(houses).max())
        rows.append({
            "loading_limit_pu": k_load,
            "pf_import": pf,
            "houses": houses,
            "transformer_kva": cfg.site.transformer_kva,
            "import_limit_kw": local_cfg.import_limit_kw,
            "export_limit_kw": local_cfg.export_limit_kw,
            "group_peak_load_kw": peak_load,
            "peak_load_within_import_limit": peak_load <= local_cfg.import_limit_kw,
            "self_sufficiency_pct": kpi["self_sufficiency_pct"],
            "grid_import_kwh": kpi["grid_import_kwh"],
            "grid_export_kwh": kpi["grid_export_kwh"],
            "pv_curtailed_kwh": kpi["pv_curtailed_kwh"],
            "pv_curtailment_pct": kpi["pv_curtailment_pct"],
            "peak_import_kw": kpi["peak_import_kw"],
            "peak_export_kw": kpi["peak_export_kw"],
            "hours_at_import_limit": kpi["hours_at_import_limit"],
            "hours_at_export_limit": kpi["hours_at_export_limit"],
            "unserved_energy_kwh": kpi["unserved_energy_kwh"],
            "energy_feasible": kpi["unserved_energy_kwh"] <= 1e-6,
            "transformer_peak_loading_pct_estimate": kpi.get(
                "transformer_peak_loading_pct_estimate", np.nan),
            "transformer_hours_above_limit_estimate": kpi.get(
                "transformer_hours_above_limit_estimate", np.nan),
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 2. Oversizing grid (objective 2)
# ---------------------------------------------------------------------------


def oversizing_grid(study: Case1Study,
                    panel_counts: tuple[int, ...] | None = None,
                    bess_modules: tuple[int, ...] | None = None,
                    inverter_keys: tuple[str, ...] | None = None,
                    houses: int = 4,
                    control: str = DEFAULT_CONTROL,
                    export_limits_kw: tuple[float | None, ...] = (None,),
                    profile: PvProfile | None = None,
                    include_infeasible: bool = True) -> pd.DataFrame:
    """
    Cross PV size, BESS energy, inverter rating and export allowance.

    Hardware infeasible combinations (PV above the inverter's datasheet DC
    input, for instance) are RETAINED with hardware_feasible=False rather
    than dropped, so the reason a size is unavailable stays visible.
    """
    cfg = study.cfg
    hw = cfg.hardware
    panel_counts = panel_counts or hw.panel_count_sweep
    bess_modules = bess_modules or hw.bess_module_sweep
    inverter_keys = inverter_keys or hw.inverter_key_sweep

    rows = []
    for panels, modules, key, export_limit in itertools.product(
            panel_counts, bess_modules, inverter_keys, export_limits_kw):
        label = (f"PV{panels}_B{modules}_{key}"
                 + ("" if export_limit is None else f"_EXP{export_limit:.1f}"))
        spec = SystemSpec(label=label, houses=houses, panel_count=panels,
                          bess_modules=modules, inverter_key=key)
        system = study.resolve(spec)

        if not system.hardware_feasible:
            if not include_infeasible:
                continue
            rows.append({
                **system.as_row(),
                "case": label, "control": control,
                "houses": houses,
                "self_sufficiency_pct": np.nan,
                "unserved_energy_kwh": np.nan,
                "pv_curtailment_pct": np.nan,
                "engine": "NOT_RUN",
            })
            continue

        kpi = run_system(study, spec, control=control, profile=profile,
                         houses=houses, export_limit_kw=export_limit)
        kpi["export_control_kw"] = (
            export_limit if export_limit is not None else system.export_limit_kw)
        rows.append(kpi)

    return pd.DataFrame(rows)


def curtailment_breakdown(study: Case1Study, spec: SystemSpec,
                          control: str = DEFAULT_CONTROL,
                          export_limit_kw: float | None = None,
                          profile: PvProfile | None = None) -> pd.DataFrame:
    """Why PV was curtailed, by binding limit, for one configuration."""
    _, dispatch = run_system(study, spec, control=control, profile=profile,
                             export_limit_kw=export_limit_kw,
                             with_economics=False, return_dispatch=True)
    reasons = dispatch["curtailment_reason"]
    total = float(dispatch["pv_curtailed_kw"].sum())

    rows = []
    for reason in sorted(set(reasons) - {"none"}):
        mask = reasons == reason
        energy = float(dispatch.loc[mask, "pv_curtailed_kw"].sum())
        if mask.sum() == 0:
            continue
        storage, _, sink = reason.partition("+")
        rows.append({
            "case": spec.label,
            "control": control,
            "binding_limits": reason,
            "storage_limit": storage,
            "ac_path_limit": sink,
            "hours": int(mask.sum()),
            "curtailed_kwh": energy,
            "share_of_curtailed_pct": 100.0 * energy / total if total > 0 else 0.0,
        })

    table = pd.DataFrame(rows)
    if table.empty:
        table = pd.DataFrame([{
            "case": spec.label, "control": control,
            "binding_limits": "none", "storage_limit": "none",
            "ac_path_limit": "none", "hours": 0, "curtailed_kwh": 0.0,
            "share_of_curtailed_pct": 0.0,
        }])
    table.attrs["total_curtailed_kwh"] = total
    return table


# ---------------------------------------------------------------------------
# 3. Control comparison (objective 6)
# ---------------------------------------------------------------------------


def control_comparison(study: Case1Study,
                       specs: list[SystemSpec],
                       controls: tuple[str, ...] = RD.CONTROLLERS,
                       export_limit_for_limited_kw: float = 1.5,
                       include_lp_bound: bool = True,
                       profile: PvProfile | None = None) -> pd.DataFrame:
    """
    Score each system under every causal controller, plus the LP bound.

    The LP row is labelled LP_PERFECT_FORESIGHT and flagged
    perfect_foresight=True. It is the ceiling on achievable performance, not
    a control option, and must never be reported as realisable reactive
    control.
    """
    rows = []
    for spec in specs:
        system = study.resolve(spec)
        if not system.hardware_feasible:
            continue
        for control in controls:
            export_limit = (
                export_limit_for_limited_kw if control == "EXPORT_LIMITED"
                else None)
            rows.append(run_system(study, spec, control=control,
                                   profile=profile,
                                   export_limit_kw=export_limit))
        if include_lp_bound:
            rows.append(run_system_lp(study, spec, profile=profile))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 4. Battery energy vs battery power (objective 2)
# ---------------------------------------------------------------------------


def battery_power_study(study: Case1Study,
                        modules_list: tuple[int, ...] = (2, 4, 6, 8),
                        power_list_kw: tuple[float, ...] = (2.5, 5.0, 7.5, 10.0),
                        panels: int = 16,
                        inverter_key: str = "SUN-8K",
                        houses: int = 4,
                        control: str = DEFAULT_CONTROL,
                        profile: PvProfile | None = None) -> pd.DataFrame:
    """
    Vary BESS ENERGY and BESS CHARGE/DISCHARGE POWER independently.

    v18 could not do this: it capped battery DC power at the converter
    rating, so energy and power moved together. Separating them answers
    whether the limiting factor on a given day is stored energy or the rate
    at which it can be moved.

    Power settings above the selected inverter's datasheet battery-port limit
    are retained and flagged infeasible rather than silently clipped.
    """
    rows = []
    for modules, power in itertools.product(modules_list, power_list_kw):
        label = f"B{modules}_P{power:.1f}"
        spec = SystemSpec(label=label, houses=houses, panel_count=panels,
                          bess_modules=modules, inverter_key=inverter_key,
                          battery_power_kw=power)
        system = study.resolve(spec)

        if not system.hardware_feasible:
            rows.append({
                **system.as_row(), "case": label, "control": control,
                "requested_battery_power_kw": power,
                "self_sufficiency_pct": np.nan, "engine": "NOT_RUN",
            })
            continue

        kpi = run_system(study, spec, control=control, profile=profile,
                         houses=houses)
        kpi["requested_battery_power_kw"] = power
        kpi["energy_to_power_ratio_h"] = (
            system.battery.usable_kwh / power if power > 0 else np.nan)
        rows.append(kpi)

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Economic screening helpers
# ---------------------------------------------------------------------------


def cheapest_feasible_inverter(cfg: Case1Config, pv_kwp: float,
                               battery_power_kw: float = 0.0) -> str:
    """
    Smallest member of the Deye family whose datasheet limits accept this
    array, which is the inverter a real procurement would buy.

    Using one oversized inverter across a PV sweep loads the small sizes with
    cost they would never incur and makes the marginal comparison meaningless.
    """
    from .config import INVERTER_FAMILY

    candidates = sorted(INVERTER_FAMILY.items(), key=lambda kv: kv[1].rated_ac_kw)
    for key, model in candidates:
        if model.max_pv_dc_kw + 1e-9 < pv_kwp:
            continue
        if battery_power_kw > 0:
            port = model.max_battery_current_a * 48.0 / 1000.0
            if port + 1e-9 < battery_power_kw:
                continue
        return key
    return candidates[-1][0]


def pv_marginal_study(study: Case1Study,
                      panel_counts: tuple[int, ...] = (12, 16, 20, 24),
                      bess_modules: int = 4,
                      inverter_key: str | None = None,
                      houses: int = 4,
                      control: str = DEFAULT_CONTROL,
                      export_limit_kw: float | None = None,
                      profile: PvProfile | None = None,
                      compensation_regime: str = "NET_METERING_HOMER"
                      ) -> tuple[pd.DataFrame, dict]:
    """
    Marginal value of PV capacity.

    `inverter_key=None` (the default) buys the cheapest datasheet-feasible
    inverter for each array size, so the cost path is the one a real project
    would follow. Passing an explicit key holds the inverter fixed instead.

    `compensation_regime` selects how exported energy is valued; see
    `economics.COMPENSATION_REGIMES`. It changes the answer, so it is always
    reported in the returned table.
    """
    regime = E.COMPENSATION_REGIMES[compensation_regime]
    rows = []

    for panels in panel_counts:
        pv_kwp = study.cfg.hardware.pv_kwp(panels)
        key = inverter_key or cheapest_feasible_inverter(study.cfg, pv_kwp)
        spec = SystemSpec(label=f"PV{panels}", houses=houses,
                          panel_count=panels, bess_modules=bess_modules,
                          inverter_key=key)
        system = study.resolve(spec)
        if not system.hardware_feasible:
            continue
        kpi = run_system(study, spec, control=control, profile=profile,
                         houses=houses, export_limit_kw=export_limit_kw,
                         with_economics=False)
        kpi.update(E.evaluate_economics(
            kpi, system, study.cfg, study.homer,
            sellback_usd_per_kwh=regime["sellback_usd_per_kwh"]))
        kpi["compensation_regime"] = compensation_regime
        kpi["compensation_note"] = regime["note"]
        rows.append(kpi)

    table = pd.DataFrame(rows)
    marginal = E.marginal_value_table(table, "panel_count", study.cfg)
    marginal["compensation_regime"] = compensation_regime
    return marginal, E.economically_useful_size(marginal, "panel_count")


def bess_marginal_study(study: Case1Study,
                        modules_list: tuple[int, ...] = (0, 2, 4, 6, 8),
                        panels: int = 16,
                        inverter_key: str | None = None,
                        houses: int = 4,
                        control: str = DEFAULT_CONTROL,
                        profile: PvProfile | None = None,
                        compensation_regime: str = "NET_METERING_HOMER"
                        ) -> tuple[pd.DataFrame, dict]:
    """
    Marginal value of battery energy at a fixed PV size.

    Under near-retail net metering the battery has almost no economic value,
    because the export credit it displaces is worth nearly as much as the
    import it avoids. That is an arithmetic consequence of the tariff, not a
    judgement on storage: the battery's purpose in this project is
    self-sufficiency and resilience, which the vulnerability study scores
    separately.
    """
    regime = E.COMPENSATION_REGIMES[compensation_regime]
    rows = []

    for modules in modules_list:
        pv_kwp = study.cfg.hardware.pv_kwp(panels)
        key = inverter_key or cheapest_feasible_inverter(study.cfg, pv_kwp)
        spec = SystemSpec(label=f"B{modules}", houses=houses,
                          panel_count=panels, bess_modules=modules,
                          inverter_key=key)
        system = study.resolve(spec)
        if not system.hardware_feasible:
            continue
        kpi = run_system(study, spec, control=control, profile=profile,
                         houses=houses, with_economics=False)
        kpi.update(E.evaluate_economics(
            kpi, system, study.cfg, study.homer,
            sellback_usd_per_kwh=regime["sellback_usd_per_kwh"]))
        kpi["compensation_regime"] = compensation_regime
        kpi["compensation_note"] = regime["note"]
        rows.append(kpi)

    table = pd.DataFrame(rows)
    marginal = E.marginal_value_table(table, "bess_modules", study.cfg)
    marginal["compensation_regime"] = compensation_regime
    return marginal, E.economically_useful_size(marginal, "bess_modules")
