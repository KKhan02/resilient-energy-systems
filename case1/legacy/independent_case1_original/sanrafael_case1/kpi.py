"""
Key performance indicators.

KPIs are computed from a STANDARD DISPATCH TABLE, not from a solver object,
so the perfect-foresight LP and the causal rule-based controllers are scored
by exactly the same code. That is what makes the objective 6 control
comparison meaningful.

Required dispatch columns (all physical kW, hourly):
    load_kw, served_load_kw, unserved_kw
    pv_available_kw, pv_dc_kw, pv_curtailed_kw
    inverter_dc_input_kw, inverter_ac_output_kw
    battery_dc_kw            (positive = discharge, negative = charge)
    battery_actual_soc_pu
    pcc_import_kw            (signed: positive = import, negative = export)
    grid_import_kw, grid_export_kw

Metric definitions are carried over from v18 unchanged:

    operational self-sufficiency = 1 - E_import / E_load
    net grid independence        = min(100, 100 * (1 - E_net / E_load))
    PV penetration               = E_pv_dc / E_load
    battery throughput           = (E_charge + E_discharge) / 2
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import Case1Config

REQUIRED_COLUMNS = (
    "load_kw", "served_load_kw", "unserved_kw",
    "pv_available_kw", "pv_dc_kw", "pv_curtailed_kw",
    "inverter_dc_input_kw", "inverter_ac_output_kw",
    "battery_dc_kw", "battery_actual_soc_pu",
    "pcc_import_kw", "grid_import_kw", "grid_export_kw",
)


def validate_dispatch(dispatch: pd.DataFrame) -> None:
    missing = set(REQUIRED_COLUMNS) - set(dispatch.columns)
    if missing:
        raise ValueError(f"Dispatch table missing columns: {sorted(missing)}")


def energy_balance_residual(dispatch: pd.DataFrame,
                            inverter_efficiency: float,
                            one_way_battery_efficiency: float) -> pd.Series:
    """
    Hourly AC-node residual, in kW:

        served_load = inverter_ac_output + grid_import - grid_export

    A non-zero residual means the dispatch table is internally inconsistent.
    Used as a hard check on both the LP extraction and the causal simulator.
    """
    return (
        dispatch["served_load_kw"]
        - dispatch["inverter_ac_output_kw"]
        - dispatch["grid_import_kw"]
        + dispatch["grid_export_kw"]
    )


def compute_kpis(dispatch: pd.DataFrame,
                 cfg: Case1Config,
                 homer: dict,
                 system_row: dict,
                 case_name: str,
                 control_label: str = "LP_PERFECT_FORESIGHT",
                 critical_load_kw: pd.Series | None = None) -> dict:
    """Score one dispatch table."""
    validate_dispatch(dispatch)

    hours = len(dispatch)
    load_kwh = float(dispatch["load_kw"].sum())
    served_kwh = float(dispatch["served_load_kw"].sum())
    unserved_kwh = float(dispatch["unserved_kw"].sum())

    pv_available_kwh = float(dispatch["pv_available_kw"].sum())
    pv_used_kwh = float(dispatch["pv_dc_kw"].sum())
    pv_curtailed_kwh = float(dispatch["pv_curtailed_kw"].sum())

    inverter_ac_kwh = float(dispatch["inverter_ac_output_kw"].sum())
    inverter_dc_kwh = float(dispatch["inverter_dc_input_kw"].sum())

    import_kwh = float(dispatch["grid_import_kw"].sum())
    export_kwh = float(dispatch["grid_export_kw"].sum())
    net_exchange_kwh = import_kwh - export_kwh

    battery = dispatch["battery_dc_kw"]
    discharge_kwh = float(battery.clip(lower=0).sum())
    charge_kwh = float((-battery.clip(upper=0)).sum())
    throughput_kwh = 0.5 * (charge_kwh + discharge_kwh)

    import_hours = int((dispatch["grid_import_kw"] > 1e-8).sum())
    export_hours = int((dispatch["grid_export_kw"] > 1e-8).sum())
    curtail_hours = int((dispatch["pv_curtailed_kw"] > 1e-8).sum())

    self_sufficiency_pct = (
        100 * (1 - import_kwh / load_kwh) if load_kwh else np.nan)
    pv_penetration_pct = 100 * pv_used_kwh / load_kwh if load_kwh else np.nan
    pv_available_penetration_pct = (
        100 * pv_available_kwh / load_kwh if load_kwh else np.nan)
    net_balance_pct = (
        100 * (1 - net_exchange_kwh / load_kwh) if load_kwh else np.nan)
    net_independence_pct = (
        float(np.clip(net_balance_pct, 0, 100)) if load_kwh else np.nan)

    # --- transformer -----------------------------------------------------
    s_kva = dispatch.get("pcc_apparent_kva_estimate")
    loading = dispatch.get("transformer_loading_pct_estimate")
    kva_rating = cfg.site.transformer_kva
    limit_pct = 100.0 * cfg.transformer.loading_limit_pu

    import_limit = float(system_row.get("import_limit_kw", cfg.import_limit_kw))
    export_limit = float(system_row.get("export_limit_kw", cfg.export_limit_kw))

    kpi = {
        "case": case_name,
        "control": control_label,
        **{k: v for k, v in system_row.items() if k != "label"},

        "hours": hours,
        "load_kwh": load_kwh,
        "served_load_kwh": served_kwh,
        "unserved_energy_kwh": unserved_kwh,
        "reliability_pct": 100 * served_kwh / load_kwh if load_kwh else np.nan,

        "pv_available_kwh": pv_available_kwh,
        "pv_used_kwh": pv_used_kwh,
        "pv_dc_generation_kwh": pv_used_kwh,
        "pv_curtailed_kwh": pv_curtailed_kwh,
        "pv_curtailment_pct": (
            100 * pv_curtailed_kwh / pv_available_kwh
            if pv_available_kwh > 0 else 0.0),
        "pv_curtailed_hours": curtail_hours,
        "pv_penetration_pct": pv_penetration_pct,
        "pv_available_penetration_pct": pv_available_penetration_pct,
        "specific_yield_kwh_per_kwp": (
            pv_used_kwh / system_row["pv_kwp"]
            if system_row.get("pv_kwp") else np.nan),

        "inverter_ac_output_kwh": inverter_ac_kwh,
        "inverter_dc_input_kwh": inverter_dc_kwh,
        "inverter_losses_kwh": inverter_dc_kwh - inverter_ac_kwh,
        "inverter_peak_ac_kw": float(dispatch["inverter_ac_output_kw"].max()),
        "inverter_hours_at_limit": int(
            (dispatch["inverter_ac_output_kw"]
             >= float(system_row.get("inverter_ac_kw", np.inf)) - 1e-4).sum()),

        "grid_import_kwh": import_kwh,
        "grid_export_kwh": export_kwh,
        "net_grid_exchange_kwh": net_exchange_kwh,
        "net_grid_balance_pct": net_balance_pct,
        "net_grid_independence_pct": net_independence_pct,
        "net_annual_exporter": bool(net_exchange_kwh < 0),
        "grid_import_hours": import_hours,
        "grid_export_hours": export_hours,
        "grid_independent_hours_pct": 100 * (1 - import_hours / hours) if hours else np.nan,
        "self_sufficiency_pct": self_sufficiency_pct,

        "battery_charge_kwh": charge_kwh,
        "battery_discharge_kwh": discharge_kwh,
        "battery_cycle_energy_sum_kwh": charge_kwh + discharge_kwh,
        "battery_throughput_kwh": throughput_kwh,
        "battery_equivalent_full_cycles": (
            throughput_kwh / system_row["bess_usable_kwh"]
            if system_row.get("bess_usable_kwh") else np.nan),
        "battery_min_soc_pu": float(np.nanmin(dispatch["battery_actual_soc_pu"]))
        if dispatch["battery_actual_soc_pu"].notna().any() else np.nan,
        "battery_mean_soc_pu": float(np.nanmean(dispatch["battery_actual_soc_pu"]))
        if dispatch["battery_actual_soc_pu"].notna().any() else np.nan,

        "peak_import_kw": float(dispatch["pcc_import_kw"].max()),
        "peak_export_kw": float(max(0.0, -dispatch["pcc_import_kw"].min())),
        "import_limit_kw": import_limit,
        "export_limit_kw": export_limit,
        "hours_at_import_limit": int(
            (dispatch["grid_import_kw"] >= import_limit - 1e-4).sum()),
        "hours_at_export_limit": int(
            (dispatch["grid_export_kw"] >= export_limit - 1e-4).sum()
            if export_limit > 0 else 0),
    }

    if s_kva is not None:
        kpi.update({
            "transformer_kva": kva_rating,
            "transformer_loading_limit_pct": limit_pct,
            "pcc_peak_apparent_kva_estimate": float(s_kva.max()),
            "transformer_peak_loading_pct_estimate": float(loading.max()),
            "transformer_hours_above_limit_estimate": int(
                (loading > limit_pct + 1e-6).sum()),
            "transformer_hours_above_100pct_estimate": int((loading > 100.0).sum()),
        })

    if critical_load_kw is not None:
        critical = pd.Series(critical_load_kw, index=dispatch.index).astype(float)
        # Unserved energy is shed from the non-critical component first.
        non_critical = (dispatch["load_kw"] - critical).clip(lower=0)
        critical_shed = (dispatch["unserved_kw"] - non_critical).clip(lower=0)
        critical_total = float(critical.sum())
        kpi.update({
            "critical_load_kwh": critical_total,
            "critical_load_unserved_kwh": float(critical_shed.sum()),
            "critical_load_coverage_pct": (
                float(np.clip(100 * (1 - critical_shed.sum() / critical_total),
                              0.0, 100.0))
                if critical_total > 0 else np.nan),
        })

    return kpi


def kpi_frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Reporting column sets
# ---------------------------------------------------------------------------

ENERGY_COLUMNS = [
    "case", "control", "houses", "panel_count", "pv_kwp", "bess_modules",
    "bess_usable_kwh", "inverter_ac_kw", "dc_ac_ratio",
    "load_kwh", "pv_available_kwh", "pv_used_kwh", "pv_curtailed_kwh",
    "pv_curtailment_pct", "self_sufficiency_pct", "net_grid_independence_pct",
    "grid_import_kwh", "grid_export_kwh", "battery_throughput_kwh",
]

NETWORK_COLUMNS = [
    "case", "control", "houses", "panel_count", "pv_kwp", "inverter_ac_kw",
    "import_limit_kw", "export_limit_kw",
    "peak_import_kw", "peak_export_kw",
    "pcc_peak_apparent_kva_estimate", "transformer_peak_loading_pct_estimate",
    "transformer_hours_above_limit_estimate",
    "hours_at_import_limit", "hours_at_export_limit",
]

RESILIENCE_COLUMNS = [
    "case", "control", "scenario", "houses", "panel_count", "bess_modules",
    "load_kwh", "unserved_energy_kwh", "reliability_pct",
    "critical_load_coverage_pct", "battery_min_soc_pu",
    "self_sufficiency_pct", "pv_curtailment_pct",
]
