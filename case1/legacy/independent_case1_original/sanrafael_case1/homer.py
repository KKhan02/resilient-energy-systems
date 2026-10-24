"""
HOMER reference model reader.

Ported unchanged from PyPSA v18 so the accepted component sizes, tariffs,
efficiencies, battery parameters, annual PV production and primary-load
variability settings are read from the same source of truth.

The only additions are type hints, a dataclass wrapper and the derived
reference table; no parsed value and no formula is altered.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# The final HOMER report models the four-battery bank as 19.2 kWh nominal and
# 17.3 kWh usable, even though the product description says 5.12 kWh/module.
# Case 1 follows the HOMER-modelled capacities for benchmark consistency.
HOMER_REFERENCE_BATTERY_NOMINAL_KWH = 19.2
HOMER_REFERENCE_BATTERY_USABLE_KWH = 17.3
HOMER_REFERENCE_BATTERY_ENERGY_IN_KWH = 18.2
HOMER_REFERENCE_BATTERY_ENERGY_OUT_KWH = 17.3
HOMER_REFERENCE_BATTERY_WEAR_USD_PER_KWH = 0.052

MONTHS = ("jan", "feb", "mar", "apr", "may", "jun",
          "jul", "aug", "sep", "oct", "nov", "dec")

MONTH_KEY = {i + 1: m for i, m in enumerate(MONTHS)}


def _text(root, path, default=None):
    node = root.find(path)
    return default if node is None or node.text is None else node.text.strip()


def _float(root, path, default=np.nan):
    x = _text(root, path, None)
    return default if x is None else float(x)


def parse_homer_xml(path: str | Path) -> dict:
    """Read the accepted HOMER model. Identical logic to PyPSA v18."""
    root = ET.parse(path).getroot()
    sd = root.find("system_description")
    ref: dict = {}

    # PV
    ref["pv_kwp"] = _float(sd, "pv/size")
    ref["pv_capex_usd"] = _float(sd, "pv/capital_cost")
    ref["pv_replacement_usd"] = _float(sd, "pv/replacement_cost")
    ref["pv_lifetime_y"] = _float(sd, "pv/lifetime")

    # Converter
    ref["inverter_kw"] = _float(sd, "converter/inverter_size")
    ref["rectifier_kw"] = _float(sd, "converter/rectifier_size")
    ref["converter_capex_usd"] = _float(sd, "converter/capital_cost")
    ref["converter_replacement_usd"] = _float(sd, "converter/replacement_cost")
    ref["converter_lifetime_y"] = _float(sd, "converter/lifetime")
    ref["inverter_efficiency"] = _float(sd, "converter/inverter_efficiency") / 100
    ref["rectifier_efficiency"] = _float(sd, "converter/rectifier_efficiency") / 100

    # Battery
    bat = sd.find("battery")
    ref["battery_description"] = _text(bat, "battery_properties/description")
    ref["battery_modules"] = int(float(_text(bat, "cell_battery/quantity")))
    ref["battery_bank_capex_usd"] = _float(bat, "cell_battery/capital_cost")
    ref["battery_bank_replacement_usd"] = _float(bat, "cell_battery/replacement_cost")
    ref["battery_nominal_ah"] = _float(bat, "battery_properties/nominal_capacity")
    ref["battery_nominal_v"] = _float(bat, "battery_properties/nominal_voltage")
    ref["battery_roundtrip_efficiency"] = _float(
        bat, "battery_properties/roundtrip_efficiency") / 100
    ref["battery_min_soc_pu"] = _float(
        bat, "battery_properties/min_state_of_charge") / 100
    ref["battery_max_charge_current_a"] = _float(
        bat, "battery_properties/max_charge_current")
    ref["battery_lifetime_throughput_kwh_per_module"] = _float(
        bat, "battery_properties/lifetime_throughput")
    ref["battery_float_life_y"] = _float(bat, "battery_properties/float_life")

    # HOMER-modelled module energy from 100 Ah x 48 V = 4.8 kWh/module,
    # 19.2 kWh for four modules, matching the final HOMER system report.
    ref["battery_module_kwh"] = (
        ref["battery_nominal_ah"] * ref["battery_nominal_v"] / 1000
    )
    ref["battery_bank_nominal_kwh_reference"] = HOMER_REFERENCE_BATTERY_NOMINAL_KWH
    ref["battery_bank_usable_kwh_reference"] = HOMER_REFERENCE_BATTERY_USABLE_KWH
    ref["battery_lifetime_throughput_kwh"] = (
        ref["battery_modules"] * ref["battery_lifetime_throughput_kwh_per_module"]
    )
    ref["battery_wear_cost_usd_per_kwh"] = HOMER_REFERENCE_BATTERY_WEAR_USD_PER_KWH

    # Grid
    ref["grid_buy_usd_per_kwh"] = _float(
        sd, "grid/grid_connection/rates/rate/grid_power_price")
    ref["grid_sell_usd_per_kwh"] = _float(
        sd, "grid/grid_connection/rates/rate/sellback_rate")
    ref["grid_purchase_capacity_kw"] = _float(
        sd, "grid/grid_connection/purchase_capacity")
    ref["grid_sale_capacity_kw"] = _float(sd, "grid/grid_connection/sale_capacity")

    # Economics
    ref["discount_rate"] = _float(sd, "economics/annual_real_interest_rate") / 100
    ref["project_lifetime_y"] = int(_float(sd, "economics/project_lifetime"))

    # Load
    ref["reference_houses"] = 4
    ref["daily_load_4hh_kwh"] = _float(sd, "primary_load/scaled_annual_average")
    ref["annual_load_4hh_kwh"] = ref["daily_load_4hh_kwh"] * 365

    weekday_profiles: dict[str, np.ndarray] = {}
    weekend_profiles: dict[str, np.ndarray] = {}

    for month in MONTHS:
        for day_type, store in (("weekday", weekday_profiles),
                                ("weekend", weekend_profiles)):
            arr = _text(
                sd,
                f"primary_load/data/monthly/daily_profiles/{month}/{day_type}/float_array",
            )
            vals = np.array([float(v) for v in arr.split()], dtype=float)
            if len(vals) != 24:
                raise ValueError(f"{month} {day_type}: expected 24 load values")
            store[month] = vals

    ref["monthly_load_profiles_weekday_4hh_kw"] = weekday_profiles
    ref["monthly_load_profiles_weekend_4hh_kw"] = weekend_profiles
    ref["monthly_load_profiles_4hh_kw"] = weekday_profiles

    ref["load_daily_variability_pu"] = _float(
        sd, "primary_load/data/monthly/daily_noise") / 100.0
    ref["load_timestep_variability_pu"] = _float(
        sd, "primary_load/data/monthly/hourly_noise") / 100.0

    # Solar
    rad = sd.find("solar_resource/data/monthly/monthly_average_radiation")
    ref["monthly_radiation_kwh_m2_day"] = np.array(
        [float(n.text) for n in rad.findall("float")]
    )

    # Locale
    lat_deg = _float(sd, "locale/latitude/degrees")
    lat_min = _float(sd, "locale/latitude/minutes")
    lon_deg = _float(sd, "locale/longitude/degrees")
    lon_min = _float(sd, "locale/longitude/minutes")
    ref["homer_lat"] = lat_deg + lat_min / 60
    ref["homer_lon"] = -(lon_deg + lon_min / 60)

    # Benchmark outputs
    sr = root.find("simulation_results")
    if sr is not None:
        ref["homer_npc_usd"] = _float(sr, "cost_summary/total_net_present_cost")
        ref["homer_lcoe_usd_per_kwh"] = _float(sr, "cost_summary/levelized_coe")
        ref["homer_pv_kwh"] = _float(sr, "annual_electric_production/pv")
        ref["homer_grid_import_kwh"] = _float(
            sr, "annual_electric_production/grid_purchases")
        ref["homer_load_served_kwh"] = _float(
            sr, "annual_electric_consumption/ac_primary_load_served")
        ref["homer_grid_export_kwh"] = _float(
            sr, "annual_electric_consumption/grid_sales")
        ref["homer_renewable_fraction"] = _float(
            sr, "annual_statistics/renewable_fraction")
        ref["homer_battery_throughput_kwh"] = _float(sr, "battery/throughput")
        ref["homer_battery_energy_in_kwh"] = HOMER_REFERENCE_BATTERY_ENERGY_IN_KWH
        ref["homer_battery_energy_out_kwh"] = HOMER_REFERENCE_BATTERY_ENERGY_OUT_KWH

    return ref


def homer_reference_table(homer: dict):
    """Derived HOMER metrics, identical definitions to PyPSA v18."""
    import pandas as pd

    pv = homer.get("homer_pv_kwh", np.nan)
    load = homer.get("homer_load_served_kwh", np.nan)
    imports = homer.get("homer_grid_import_kwh", np.nan)
    exports = homer.get("homer_grid_export_kwh", np.nan)
    net_import = imports - exports

    rows = {
        "AC primary load [kWh/yr]": load,
        "PV production [kWh/yr]": pv,
        "PV penetration [%]": 100 * pv / load if load else np.nan,
        "Grid purchases [kWh/yr]": imports,
        "Grid sales [kWh/yr]": exports,
        "Net grid import [kWh/yr]": net_import,
        "Derived operational self-sufficiency [%]":
            100 * (1 - imports / load) if load else np.nan,
        "Derived net grid independence [%]":
            100 * (1 - net_import / load) if load else np.nan,
        "HOMER renewable fraction [%]":
            100 * homer.get("homer_renewable_fraction", np.nan),
        "Battery energy in [kWh/yr]": homer.get("homer_battery_energy_in_kwh", np.nan),
        "Battery energy out [kWh/yr]": homer.get("homer_battery_energy_out_kwh", np.nan),
        "Battery throughput [kWh/yr]": homer.get("homer_battery_throughput_kwh", np.nan),
    }
    return pd.DataFrame({"HOMER reference": pd.Series(rows)})


@dataclass
class BatteryBank:
    """
    Battery bank sizing.

    Case 1 change: the DC power limit is no longer silently capped by the
    inverter AC rating. Energy, DC power and the inverter rating are three
    separate quantities (objective 2), and each is reported.
    """

    module_count: int
    nominal_kwh: float
    usable_kwh: float
    module_dc_power_kw: float
    bank_dc_power_kw: float
    inverter_battery_port_kw: float
    dc_power_kw: float
    min_soc_pu: float
    roundtrip_efficiency: float

    @property
    def one_way_efficiency(self) -> float:
        return float(np.sqrt(self.roundtrip_efficiency))

    @property
    def binding_power_limit(self) -> str:
        if self.module_count <= 0:
            return "none"
        if self.bank_dc_power_kw <= self.inverter_battery_port_kw + 1e-9:
            return "battery modules"
        return "inverter battery port"


def battery_bank(homer: dict, module_count: int,
                 inverter_battery_port_kw: float,
                 power_override_kw: float | None = None) -> BatteryBank:
    """
    Build a battery bank description.

    Energy scales linearly with module count from the HOMER-modelled bank
    (19.2 kWh nominal / 17.3 kWh usable for four modules).

    DC power is the lesser of
      * module count x per-module DC power (48 V x 100 A = 4.8 kW/module), and
      * the inverter's datasheet battery-port power,
    unless an explicit override is supplied.
    """
    if module_count <= 0:
        return BatteryBank(0, 0.0, 0.0, 0.0, 0.0, inverter_battery_port_kw, 0.0,
                           homer["battery_min_soc_pu"],
                           homer["battery_roundtrip_efficiency"])

    scale = module_count / homer["battery_modules"]
    nominal_kwh = homer["battery_bank_nominal_kwh_reference"] * scale
    usable_kwh = homer["battery_bank_usable_kwh_reference"] * scale

    module_dc_power_kw = (
        homer["battery_nominal_v"] * homer["battery_max_charge_current_a"] / 1000
    )
    bank_dc_power_kw = module_count * module_dc_power_kw

    if power_override_kw is not None:
        dc_power_kw = float(power_override_kw)
    else:
        dc_power_kw = min(bank_dc_power_kw, inverter_battery_port_kw)

    return BatteryBank(
        module_count=module_count,
        nominal_kwh=nominal_kwh,
        usable_kwh=usable_kwh,
        module_dc_power_kw=module_dc_power_kw,
        bank_dc_power_kw=bank_dc_power_kw,
        inverter_battery_port_kw=inverter_battery_port_kw,
        dc_power_kw=dc_power_kw,
        min_soc_pu=homer["battery_min_soc_pu"],
        roundtrip_efficiency=homer["battery_roundtrip_efficiency"],
    )


def battery_bank_parameters_v18(homer: dict, module_count: int,
                                converter_kw: float) -> dict:
    """
    EXACT v18 battery sizing, retained only for baseline reproduction.

    v18 capped the bank DC power at the converter rating, which couples
    battery power to the inverter. Case 1 keeps this function so the v18
    numbers can be reproduced bit-for-bit during validation.
    """
    if module_count <= 0:
        return {"nominal_kwh": 0.0, "usable_kwh": 0.0, "dc_power_kw": 0.0}

    scale = module_count / homer["battery_modules"]
    per_module_dc_kw = (
        homer["battery_nominal_v"] * homer["battery_max_charge_current_a"] / 1000
    )
    return {
        "nominal_kwh": homer["battery_bank_nominal_kwh_reference"] * scale,
        "usable_kwh": homer["battery_bank_usable_kwh_reference"] * scale,
        "dc_power_kw": min(converter_kw, module_count * per_module_dc_kw),
    }
