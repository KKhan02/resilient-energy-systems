"""
Case Study 1 configuration: Transformer-Constrained PV-BESS Oversizing,
Vulnerability and Adaptive Resilience Assessment.

San Rafael / El Arenal, Antioquia, Colombia. SEEDExchange Resilient Energy Systems.

ALL assumptions live here, each tagged with a provenance class:

    MEASURED   - from EPM asset data, a datasheet, a bill or a downloaded dataset
    DERIVED    - computed from MEASURED values inside this package
    REFERENCE  - taken from the accepted HOMER model / project quotation
    ASSUMED    - engineering assumption; no site-specific value available
    CONTROL    - a study choice (scenario definition, sweep range, screening band)

Nothing in this module invents a physical measurement. Values carried over from
PyPSA v18 and pandapower v5 are reproduced exactly so Case 1 results stay
comparable with the verified baselines.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from pathlib import Path

# ----------------------------------------------------------------------------
# Provenance registry
# ----------------------------------------------------------------------------

PROVENANCE: dict[str, tuple[str, str]] = {}


def _p(name: str, status: str, source: str):
    PROVENANCE[name] = (status, source)


# ============================================================================
# 1. Site and electrical reference
# ============================================================================


@dataclass(frozen=True)
class SiteConfig:
    """EPM asset data for the physical point of common coupling."""

    model_year: int = 2025

    trafo_number: str = "94022"
    trafo_node: str = "931076"
    epm_circuit: str = "221-12"
    trafo_lat: float = 6.246949759
    trafo_lon: float = -75.006208238

    project_reference_lat: float = 6.247444
    project_reference_lon: float = -75.007889

    # Transformer nameplate. NOTE: 5 kVA is APPARENT power, not 5 kW.
    transformer_kva: float = 5.0
    mv_voltage_kv: float = 7.621
    lv_voltage_kv: float = 0.240

    primary_conductor: str = "#2 ACSR"
    secondary_conductor: str = "1/0 AAC"
    primary_length_m: float = 354.2
    secondary_length_m: float = 324.5

    houses_per_lv_branch: int = 2


_p("transformer_kva", "MEASURED", "EPM asset data, transformer 94022 (5 kVA, single-phase)")
_p("mv_voltage_kv", "MEASURED", "EPM asset data: 7.621 kV primary")
_p("lv_voltage_kv", "MEASURED", "EPM asset data: 240/120 V split secondary")
_p("primary_length_m", "MEASURED", "EPM screenshot trace, approx. 354.2 m")
_p("secondary_length_m", "MEASURED", "Corrected EPM secondary trace, approx. 324.5 m")
_p("houses_per_lv_branch", "ASSUMED", "Representative radial layout; service drops not surveyed")


# ============================================================================
# 2. Transformer loading constraint  (NEW IN CASE 1)
# ============================================================================


@dataclass(frozen=True)
class TransformerConstraint:
    """
    The 5 kVA limit is an APPARENT-power limit:

        |S_pcc| = sqrt(P^2 + Q^2) <= S_rated * k_loading

    PyPSA solves active power only, so the constraint enters the energy model
    as a derated ACTIVE-power limit:

        P_import_max = S_rated * k_loading * pf_import
        P_export_max = S_rated * k_loading * pf_export

    pf_import is the household load power factor, because import flows are
    dominated by household demand. pf_export defaults to 1.0 because the
    hybrid inverter exports at unity power factor by default, so at high
    export the residual reactive flow is only the small household Q.

    The derated active-power limit is a screening device. The apparent power
    actually seen by the transformer is recomputed exactly in the pandapower
    stage, which carries household Q, inverter Q and network losses.
    """

    # EPM RA8-017 uses fp = 0.9 for residential conductor sizing. The project
    # lead specifies 0.95 for this community: predominantly lighting and small
    # rural household appliance load.
    pf_import: float = 0.95
    pf_export: float = 1.00

    # Permissible continuous loading as a fraction of nameplate kVA.
    # EPM RA4-100's 120% factor is for metering/CT selection, NOT a continuous
    # transformer loading limit, so it is not the default here.
    loading_limit_pu: float = 0.90

    # Sensitivity grid for objective 3.
    loading_limit_sensitivity: tuple[float, ...] = (0.80, 0.90, 1.00)
    pf_import_sensitivity: tuple[float, ...] = (0.90, 0.95, 1.00)

    def import_limit_kw(self, transformer_kva: float) -> float:
        return transformer_kva * self.loading_limit_pu * self.pf_import

    def export_limit_kw(self, transformer_kva: float) -> float:
        return transformer_kva * self.loading_limit_pu * self.pf_export

    def apparent_kva(self, p_kw: float, q_kvar: float) -> float:
        return math.hypot(p_kw, q_kvar)

    def loading_pct(self, p_kw: float, q_kvar: float, transformer_kva: float) -> float:
        return 100.0 * self.apparent_kva(p_kw, q_kvar) / transformer_kva


_p("pf_import", "ASSUMED", "Project lead: 0.95 for rural household lighting-dominated load; EPM RA8-017 uses 0.90 for sizing")
_p("pf_export", "ASSUMED", "Deye hybrid inverter default unity power factor; 0.8 lead-lag adjustable per datasheet")
_p("loading_limit_pu", "ASSUMED", "Permissible continuous loading; no EPM continuous-rating document obtained. Swept 0.80/0.90/1.00")


# ============================================================================
# 3. Hardware: PV, battery, inverter family  (EXTENDED IN CASE 1)
# ============================================================================


@dataclass(frozen=True)
class PvModuleSpec:
    """Module used in the project quotation."""

    rated_w: float = 435.0


_p("pv_module_rated_w", "REFERENCE", "Project quotation: 12 x 435 Wp = 5.22 kWp")


@dataclass(frozen=True)
class InverterModel:
    """
    One member of the Deye SUN-*-SG02LP2-US split-phase hybrid family.

    Values transcribed from the datasheet supplied with the project
    (inversor-hibrido-deye-de-5kw.pdf), which covers
    SUN-5/6/7.6/8K-SG02LP2-US-AM2 and SUN-10/12K-SG02LP2-US-AM3.

    This is a SPLIT-PHASE 120/240 V unit (grid connection form 2L+N+PE),
    which is the topology that matches the EPM 240/120 V single-phase
    three-wire secondary. It is NOT a three-phase 400 V unit.
    """

    name: str
    rated_ac_kw: float          # Rated AC in/out active power
    max_apparent_kva: float     # Max AC in/out apparent power
    max_pv_dc_kw: float         # Max PV input power
    max_battery_current_a: float  # Max charge / discharge current
    max_ac_current_a: float

    # Datasheet-wide values, identical across the family
    max_pv_dc_voltage_v: float = 500.0
    mppt_voltage_min_v: float = 150.0
    mppt_voltage_max_v: float = 425.0
    battery_voltage_min_v: float = 40.0
    battery_voltage_max_v: float = 60.0
    pf_adjust_min: float = 0.8
    max_efficiency: float = 0.976
    euro_efficiency: float = 0.965
    peak_overload_factor: float = 2.0     # 2x rated for 10 s, off-grid
    peak_overload_seconds: float = 10.0

    def battery_power_kw(self, battery_nominal_voltage_v: float) -> float:
        """DC battery port power limit implied by the current limit."""
        return self.max_battery_current_a * battery_nominal_voltage_v / 1000.0


# Deye SUN-*-SG02LP2-US split-phase hybrid family, from the project datasheet.
INVERTER_FAMILY: dict[str, InverterModel] = {
    "SUN-5K": InverterModel("SUN-5K-SG02LP2-US-AM2", 5.0, 5.0, 7.5, 120.0, 20.9),
    "SUN-6K": InverterModel("SUN-6K-SG02LP2-US-AM2", 6.0, 6.0, 9.0, 135.0, 25.0),
    "SUN-7.6K": InverterModel("SUN-7.6K-SG02LP2-US-AM2", 7.6, 7.6, 11.4, 190.0, 31.7),
    "SUN-8K": InverterModel("SUN-8K-SG02LP2-US-AM2", 8.0, 8.0, 12.0, 190.0, 33.4),
    "SUN-10K": InverterModel("SUN-10K-SG02LP2-US-AM3", 10.0, 10.0, 15.0, 220.0, 41.7),
    "SUN-12K": InverterModel("SUN-12K-SG02LP2-US-AM3", 12.0, 12.0, 18.0, 250.0, 50.0),
}

QUOTED_INVERTER_KEY = "SUN-5K"

_p("inverter_family", "MEASURED", "Deye datasheet supplied with project: SUN-5/6/7.6/8K-SG02LP2-US-AM2, SUN-10/12K-SG02LP2-US-AM3")
_p("inverter_split_phase", "MEASURED", "Datasheet grid connection form 2L+N+PE, 120/240 V - matches EPM single-phase 240/120 V secondary")


@dataclass(frozen=True)
class HardwareConfig:
    """PV / BESS / inverter design space for the oversizing study."""

    module: PvModuleSpec = field(default_factory=PvModuleSpec)

    # --- PV ---------------------------------------------------------------
    reference_panel_count: int = 12
    panel_count_sweep: tuple[int, ...] = (12, 16, 20, 24)
    # Legacy v18 range retained so the baseline sweep can be reproduced.
    panel_count_sweep_v18: tuple[int, ...] = (4, 6, 8, 10, 12)

    # --- BESS -------------------------------------------------------------
    reference_bess_modules: int = 4
    bess_module_sweep: tuple[int, ...] = (0, 2, 4, 6, 8)
    bess_module_sweep_v18: tuple[int, ...] = (0, 1, 2, 3, 4)

    # --- Inverter ---------------------------------------------------------
    inverter_key: str = QUOTED_INVERTER_KEY
    inverter_key_sweep: tuple[str, ...] = ("SUN-5K", "SUN-8K", "SUN-10K", "SUN-12K")

    # Case 1 separates the battery power limit from the inverter rating.
    # When None the limit is the datasheet battery-port power of the selected
    # inverter model, capped by the module count.
    battery_power_kw_override: float | None = None

    def pv_kwp(self, panel_count: int) -> float:
        return panel_count * self.module.rated_w / 1000.0

    def inverter(self, key: str | None = None) -> InverterModel:
        return INVERTER_FAMILY[key or self.inverter_key]


_p("panel_count_sweep", "CONTROL", "Objective 2: extend 12 -> 16/20/24 panels, subject to datasheet DC input limits")
_p("bess_module_sweep", "CONTROL", "Objective 2: BESS energy investigated separately from charge/discharge power")
_p("inverter_key_sweep", "CONTROL", "Objective 2: inverter AC rating as its own axis, within the quoted Deye family")


# ============================================================================
# 4. Demand (unchanged from v18)
# ============================================================================


@dataclass(frozen=True)
class DemandConfig:
    use_stochastic_household_loads: bool = True
    stochastic_load_seed: int = 20250913
    stochastic_profile_house_count: int = 20
    stochastic_min_factor: float = 0.0

    house_group_size_sweep: tuple[int, ...] = (4, 5, 6, 7, 8)
    reference_houses: int = 4

    # Share of hourly demand treated as critical during an outage
    # (lighting, phone charging, refrigeration).
    critical_load_fraction: float = 0.30

    # Share of daily energy that can be time-shifted within the same day by
    # the load-management controller. Causal: no forecast is used.
    deferrable_load_fraction: float = 0.15
    deferrable_max_defer_hours: int = 8


_p("stochastic_load_seed", "REFERENCE", "PyPSA v18 reproducible reference realization, seed 20250913")
_p("critical_load_fraction", "ASSUMED", "No appliance survey available; 30% of hourly demand treated as critical")
_p("deferrable_load_fraction", "ASSUMED", "No appliance survey available; 15% of daily energy treated as shiftable within the day")


# ============================================================================
# 5. Solar resource (unchanged physics from v18 / v5)
# ============================================================================


@dataclass(frozen=True)
class ResourceConfig:
    nasa_site_lat: float = 6.2523
    nasa_site_lon: float = -75.0143
    nasa_site_altitude_m: float = 1291.33
    nasa_timezone_for_solar_position: str = "Etc/GMT+5"
    solar_position_interval_midpoint_min: int = 30

    pv_surface_tilt_deg: float = 5.0
    pv_surface_azimuth_deg: float = 180.0
    pv_derating_factor: float = 0.80
    pv_temp_coeff_per_c: float = -0.003
    pv_noct_c: float = 45.0
    albedo: float = 0.20

    poa_to_ghi_annual_ratio_min: float = 0.98
    poa_to_ghi_annual_ratio_max: float = 1.05
    component_closure_max_rel_error: float = 0.02

    pv_profile_column: str = "pv_available_kw_per_kwp"


_p("pv_surface_tilt_deg", "REFERENCE", "HOMER slope 5.0 deg")
_p("pv_derating_factor", "REFERENCE", "HOMER derating factor 80%")
_p("pv_temp_coeff_per_c", "REFERENCE", "HOMER temperature coefficient -0.300 %/C")
_p("nasa_site_altitude_m", "MEASURED", "NASA POWER grid cell elevation for the project point")
_p("solar_position_interval_midpoint_min", "DERIVED", "NASA POWER hourly values are interval averages; solar position at +30 min midpoint")


# ============================================================================
# 6. Dispatch and control  (EXTENDED IN CASE 1)
# ============================================================================


@dataclass(frozen=True)
class DispatchConfig:
    """
    The LP keeps the v18 operating-priority coefficients. These are NOT
    tariffs: they enforce the community rule
    PV -> load -> battery -> grid import, export last.
    """

    grid_last_resort_penalty_usd_per_kwh: float = 10.0
    residual_export_priority_value_usd_per_kwh: float = 0.001
    allow_grid_battery_charging: bool = False
    unserved_energy_penalty_usd_per_kwh: float = 10.0
    solver: str = "highs"

    # --- Causal controller parameters (no forecasting in Case 1) ----------
    # Fixed emergency reserve: normal grid-connected operation will not
    # discharge the battery below this state of charge.
    fixed_reserve_soc_pu: float = 0.50

    # Adaptive reserve bounds and the trailing window used to form the
    # causal solar-availability index. Trailing only: no forecast.
    adaptive_reserve_min_pu: float = 0.30
    adaptive_reserve_max_pu: float = 0.75
    adaptive_solar_index_days: int = 3
    adaptive_reserve_gain: float = 0.60

    # Import level above which the load-management controller starts
    # deferring deferrable demand, as a fraction of the import limit.
    load_management_import_trigger_pu: float = 0.80


_p("grid_last_resort_penalty_usd_per_kwh", "CONTROL", "v18 operating-priority coefficient, not a tariff")
_p("fixed_reserve_soc_pu", "CONTROL", "Objective 6 strategy definition: fixed emergency SOC reserve")
_p("adaptive_reserve_gain", "CONTROL", "Objective 6 strategy definition: reserve raised when trailing solar availability falls")


# ============================================================================
# 7. Vulnerability / resilience scenarios  (NEW IN CASE 1)
# ============================================================================


@dataclass(frozen=True)
class StressConfig:
    outage_duration_sweep_h: tuple[int, ...] = (4, 8, 12, 24, 48)
    outage_sample_day_of_month: int = 15
    outage_sample_hours: tuple[int, ...] = (0, 3, 6, 9, 12, 15, 18, 21)
    outage_start_soc_pu: float = 0.80

    # Prolonged low solar availability. Windows are located in the ACTUAL
    # 2025 NASA POWER year; the derate factors are an explicit extra stress.
    low_solar_window_days: tuple[int, ...] = (3, 5, 7)
    low_solar_derate_factors: tuple[float, ...] = (1.00, 0.70, 0.50)

    # High coincident demand multipliers applied to the reference realization.
    high_demand_multipliers: tuple[float, ...] = (1.00, 1.25, 1.50)
    high_demand_window_days: int = 3

    # Export restriction imposed by the operator, as kW at the PCC.
    export_restriction_kw: tuple[float, ...] = (0.0, 1.5, 3.0)

    # Monte Carlo (carried over from v18)
    mc_solved_realizations: int = 30
    mc_peak_realizations: int = 300
    mc_peak_percentile: float = 95.0
    mc_base_seed: int = 20260929


_p("low_solar_derate_factors", "CONTROL", "Explicit stress multiplier on the measured low-irradiance window")
_p("high_demand_multipliers", "CONTROL", "Explicit stress multiplier on the reference demand realization")
_p("outage_duration_sweep_h", "CONTROL", "v18 durations extended with a 48 h case")


# ============================================================================
# 8. Economics  (EXTENDED IN CASE 1)
# ============================================================================


@dataclass(frozen=True)
class EconomicsConfig:
    quoted_reference_subtotal_usd: float = 11974.79
    quoted_reference_total_with_vat_usd: float = 14250.00

    linear_pv_capex: bool = True
    linear_bess_capex: bool = True
    linear_converter_capex: bool = True

    # Component lifetimes for replacement scheduling inside the 25 y project.
    pv_lifetime_y: float = 25.0
    inverter_lifetime_y: float = 15.0
    battery_float_life_y: float = 20.0

    # Economically useful size test: an increment is retained while
    # annual benefit / annualised incremental cost >= this ratio.
    useful_size_benefit_cost_ratio: float = 1.0

    # Optional tariff sensitivity. OFF by default: the HOMER tariff remains
    # the Case 1 base so results stay comparable with v18.
    run_tariff_sensitivity: bool = False
    tariff_sensitivity_usd_per_kwh: tuple[float, ...] = (0.10, 0.215, 0.29)


_p("quoted_reference_subtotal_usd", "REFERENCE", "Project quotation subtotal, anchors the installed-cost level")
_p("inverter_lifetime_y", "REFERENCE", "HOMER converter lifetime 15 y")
_p("tariff_sensitivity_usd_per_kwh", "CONTROL", "Optional: EPM invoice-derived subsidised / unsubsidised band vs HOMER 0.29 USD/kWh")


# ============================================================================
# 9. Screening bands for the network stage (from pandapower v5)
# ============================================================================


@dataclass(frozen=True)
class NetworkConfig:
    pp_power_scale: float = 3.0

    load_power_factor: float = 0.95  # Case 1 value; v5 used 0.90

    mv_r_ohm_per_km: float = 0.8320
    mv_x_ohm_per_km: float = 0.40
    mv_max_i_ka: float = 0.184

    lv_r_single_ohm_per_km: float = 0.656
    lv_x_single_ohm_per_km: float = 0.08
    lv_max_i_ka: float = 0.150

    trf_vk_percent: float = 3.0
    trf_vkr_percent: float = 1.8
    trf_pfe_physical_kw: float = 0.030
    trf_i0_percent: float = 2.5

    lv_screen_min_pu: float = 0.97
    lv_screen_max_pu: float = 1.03
    line_limit_percent: float = 100.0

    houses_per_tap: int = 2
    expansion_segment_m: float | None = None

    inverter_pf_sensitivity: tuple[float, ...] = (1.00, 0.98, 0.95)

    @property
    def lv_r_loop_ohm_per_km(self) -> float:
        return 2 * self.lv_r_single_ohm_per_km

    @property
    def lv_x_loop_ohm_per_km(self) -> float:
        return 2 * self.lv_x_single_ohm_per_km


_p("mv_r_ohm_per_km", "MEASURED", "EPM ET-TD-ME01-03, #2 AWG ACSR Sparrow, 0.8320 ohm/km at 20 C")
_p("lv_r_single_ohm_per_km", "MEASURED", "EPM RA8-017 / ET-TD-ME01-02, 1/0 AAC reference 0.656 ohm/km")
_p("mv_max_i_ka", "MEASURED", "Nexans Colombia, #2 ACSR Sparrow ampacity approx. 184 A")
_p("lv_max_i_ka", "ASSUMED", "Installation-specific 1/0 AAC ampacity not available; screening value")
_p("mv_x_ohm_per_km", "ASSUMED", "Installation geometry not available")
_p("lv_x_single_ohm_per_km", "ASSUMED", "Installation geometry not available")
_p("trf_vk_percent", "ASSUMED", "Transformer 94022 nameplate impedance not available; engineering proxy")
_p("lv_screen_min_pu", "MEASURED", "EPM RA8-017 3% voltage-drop design reference, applied as a 0.97-1.03 pu screening band")


# ============================================================================
# 10. Paths and top-level configuration
# ============================================================================


@dataclass
class Paths:
    project_root: Path = field(default_factory=Path.cwd)

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def results_dir(self) -> Path:
        return self.project_root / "results_case1"

    @property
    def figures_dir(self) -> Path:
        return self.results_dir / "figures"

    def ensure(self) -> "Paths":
        for folder in (self.data_dir, self.results_dir, self.figures_dir):
            folder.mkdir(parents=True, exist_ok=True)
        return self

    # --- input discovery -------------------------------------------------
    def find(self, candidates: list[str], required: bool = True) -> Path | None:
        search_dirs = [
            self.project_root,
            self.data_dir,
            self.project_root / "results",
            self.project_root / "NASA Data",
            self.project_root.parent,
        ]
        for directory in search_dirs:
            for name in candidates:
                candidate = directory / name
                if candidate.exists():
                    return candidate
        for directory in search_dirs:
            if not directory.exists():
                continue
            for name in candidates:
                hits = sorted(directory.rglob(name))
                if hits:
                    return hits[0]
        if required:
            raise FileNotFoundError(
                "Could not find any of:\n- " + "\n- ".join(candidates)
            )
        return None

    @property
    def homer_xml(self) -> Path:
        return self.find([
            "SimulacionTampico1k(1).xml",
            "SimulacionTampico1k.xml",
        ])

    @property
    def nasa_monthly_csv(self) -> Path | None:
        return self.find([
            "Nasa Data(2).csv", "Nasa Data(1).csv", "Nasa Data.csv",
            "Nasa_Data.csv",
        ], required=False)

    @property
    def nasa_hourly_csv(self) -> Path:
        return self.find(["NASA_POWER_SanRafael_hourly_2025.csv"])


@dataclass
class Case1Config:
    """Top-level Case 1 configuration object."""

    paths: Paths = field(default_factory=Paths)
    site: SiteConfig = field(default_factory=SiteConfig)
    transformer: TransformerConstraint = field(default_factory=TransformerConstraint)
    hardware: HardwareConfig = field(default_factory=HardwareConfig)
    demand: DemandConfig = field(default_factory=DemandConfig)
    resource: ResourceConfig = field(default_factory=ResourceConfig)
    dispatch: DispatchConfig = field(default_factory=DispatchConfig)
    stress: StressConfig = field(default_factory=StressConfig)
    economics: EconomicsConfig = field(default_factory=EconomicsConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)

    # Reproducibility / reporting
    case_label: str = "CASE1"
    save_figures: bool = True

    # --- convenience ------------------------------------------------------
    @property
    def import_limit_kw(self) -> float:
        return self.transformer.import_limit_kw(self.site.transformer_kva)

    @property
    def export_limit_kw(self) -> float:
        return self.transformer.export_limit_kw(self.site.transformer_kva)

    def with_transformer(self, **kwargs) -> "Case1Config":
        return replace(self, transformer=replace(self.transformer, **kwargs))

    def with_hardware(self, **kwargs) -> "Case1Config":
        return replace(self, hardware=replace(self.hardware, **kwargs))

    def with_dispatch(self, **kwargs) -> "Case1Config":
        return replace(self, dispatch=replace(self.dispatch, **kwargs))


# ============================================================================
# Unit conversions
# ============================================================================

KW_TO_MW = 1e-3
KWH_TO_MWH = 1e-3
USD_PER_KWH_TO_USD_PER_MWH = 1e3


def provenance_table():
    """Return the provenance registry as a DataFrame (pandas imported lazily)."""
    import pandas as pd

    rows = [
        {"parameter": name, "status": status, "source": source}
        for name, (status, source) in sorted(PROVENANCE.items())
    ]
    return pd.DataFrame(rows)
