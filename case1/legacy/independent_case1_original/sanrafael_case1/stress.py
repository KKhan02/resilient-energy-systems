"""
Vulnerability and adaptive-resilience assessment (objectives 5, 6, 7).

Five stressor families, each applied to the SAME verified reference year so
results are comparable:

  LOW_SOLAR               prolonged low solar availability
  GRID_OUTAGE             EPM supply unavailable
  HIGH_DEMAND             high coincident household demand
  HIGH_PV_EXPORT_LIMITED  high PV output with a restricted export allowance
  COMBINED                stressors applied together

Two things keep this honest:

1. The low-solar and high-PV windows are LOCATED IN THE MEASURED 2025 NASA
   POWER YEAR. The episodes are real; only the additional derate or demand
   multiplier is an explicit extra stress, and it is always reported.

2. Every window starts from the state of charge the system ACTUALLY HAD at
   that moment in the annual causal run with the same controller. A stress
   test that starts from a convenient state of charge measures nothing.

OUTAGE RESULTS ARE CONDITIONAL
------------------------------
Real islanding capability at this site is UNCONFIRMED. The Deye datasheet
describes off-grid operation and integrated anti-islanding, but no
installation, backup-panel wiring or utility interconnection agreement has
been verified for El Arenal. Every outage metric produced here therefore
carries `islanding_confirmed = False` and must be reported as the energy
available for islanded operation IF islanding is commissioned, not as
demonstrated backup performance.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import kpi as K
from . import rule_dispatch as RD
from .config import Case1Config
from .lp_model import ResolvedSystem
from .resource import PvProfile, worst_low_solar_windows
from .study import Case1Study


@dataclass
class StressScenario:
    """One stressor applied to a window of the reference year."""

    name: str
    family: str
    start: pd.Timestamp
    duration_h: int
    pv_scale: float = 1.0
    demand_scale: float = 1.0
    grid_available: bool = True
    export_limit_kw: float | None = None
    note: str = ""

    def describe(self) -> dict:
        return {
            "scenario": self.name,
            "family": self.family,
            "window_start": self.start,
            "duration_h": self.duration_h,
            "pv_scale": self.pv_scale,
            "demand_scale": self.demand_scale,
            "grid_available": self.grid_available,
            "export_limit_kw": self.export_limit_kw,
            "note": self.note,
        }


@dataclass
class ResilienceRunner:
    """Runs stress scenarios for one system under one controller."""

    study: Case1Study
    system: ResolvedSystem
    params: RD.ControlParams
    profile: PvProfile
    houses: int = 4
    _annual: pd.DataFrame | None = field(default=None, init=False, repr=False)

    @property
    def cfg(self) -> Case1Config:
        return self.study.cfg

    @property
    def annual(self) -> pd.DataFrame:
        """Annual causal reference run, cached. Supplies window start states."""
        if self._annual is None:
            self._annual = RD.simulate(
                self.study.load_kw(self.houses),
                self.profile.dc_kw(self.system.pv_kwp),
                self.system, self.cfg, self.study.homer, self.params,
            )
        return self._annual

    def start_soc(self, start: pd.Timestamp) -> float:
        """Actual state of charge immediately before `start` in the annual run."""
        soc = self.annual["battery_actual_soc_pu"]
        start = pd.Timestamp(start)
        if start not in soc.index:
            raise KeyError(f"{start} is not in the reference year")
        position = soc.index.get_loc(start)
        previous = position - 1 if position > 0 else len(soc) - 1
        value = float(soc.iloc[previous])
        if not np.isfinite(value):
            return float(self.system.battery.min_soc_pu)
        return value

    def run(self, scenario: StressScenario) -> tuple[dict, pd.DataFrame]:
        """Simulate one scenario. Returns (metrics, hourly dispatch)."""
        cfg = self.cfg
        homer = self.study.homer

        start = pd.Timestamp(scenario.start)
        end = start + pd.Timedelta(hours=scenario.duration_h - 1)

        load = self.study.load_kw(self.houses).loc[start:end]
        if len(load) != scenario.duration_h:
            raise ValueError(
                f"{scenario.name}: requested {scenario.duration_h} h, "
                f"found {len(load)} h in the reference year")

        pv = self.profile.dc_kw(self.system.pv_kwp).loc[start:end]

        load_stressed = load * scenario.demand_scale
        pv_stressed = pv * scenario.pv_scale

        grid = pd.Series(scenario.grid_available, index=load.index)

        params = self.params
        if scenario.export_limit_kw is not None:
            params = RD.ControlParams(**{
                **params.__dict__,
                "export_limit_kw": scenario.export_limit_kw,
            })

        dispatch = RD.simulate(
            load_stressed, pv_stressed, self.system, cfg, homer, params,
            initial_soc_pu=self.start_soc(start),
            grid_available=grid,
            allow_unserved=True,
        )

        critical = load_stressed * cfg.demand.critical_load_fraction
        metrics = K.compute_kpis(
            dispatch, cfg, homer, self.system.as_row(),
            case_name=scenario.name, control_label=params.name,
            critical_load_kw=critical,
        )
        metrics.update(scenario.describe())
        metrics.update(self._resilience_metrics(dispatch, critical, scenario))
        return metrics, dispatch

    def _resilience_metrics(self, dispatch: pd.DataFrame,
                            critical: pd.Series,
                            scenario: StressScenario) -> dict:
        unserved = dispatch["unserved_kw"]
        first_shortfall = np.argmax(unserved.to_numpy() > 1e-9) \
            if (unserved > 1e-9).any() else None

        survival_h = (
            int(first_shortfall) if first_shortfall is not None
            else int(scenario.duration_h)
        )

        critical_unserved = dispatch["critical_unserved_kw"]
        first_critical = np.argmax(critical_unserved.to_numpy() > 1e-9) \
            if (critical_unserved > 1e-9).any() else None
        critical_survival_h = (
            int(first_critical) if first_critical is not None
            else int(scenario.duration_h)
        )

        loading = dispatch.get("transformer_loading_pct_estimate")

        # Load management SHIFTS demand rather than losing it, so a window can
        # end with a deferred backlog that was neither served nor lost. Two
        # measures are reported and NEITHER is presented alone:
        #
        #   FIRM        no firm (non-deferrable) demand went unserved. This is
        #               the reliability measure, and it credits deferral.
        #   ALL-DEMAND  no firm demand went unserved AND nothing was still
        #               deferred at the end of the window. This is the strict
        #               measure, and it credits nothing to deferral.
        #
        # The truth sits between them: deferred load is real demand that has
        # to be served later, which is acceptable for a pump or a washing
        # machine and unacceptable for demand that cannot wait.
        backlog = float(dispatch.attrs.get("deferred_backlog_end_kwh", 0.0))
        unserved_total = float(unserved.sum())

        return {
            "survival_hours_full_load": survival_h,
            "survived_firm_load": survival_h >= scenario.duration_h,
            "survived_full_window": survival_h >= scenario.duration_h,
            "survival_hours_critical_load": critical_survival_h,
            "survived_critical_full_window": (
                critical_survival_h >= scenario.duration_h),
            "energy_not_served_kwh": unserved_total,
            "critical_energy_not_served_kwh": float(critical_unserved.sum()),
            "deferred_backlog_end_kwh": backlog,
            "energy_shortfall_including_backlog_kwh": unserved_total + backlog,
            "served_all_demand_in_window": bool(
                survival_h >= scenario.duration_h and backlog <= 1e-6),
            "survived_full_window_strict": bool(
                survival_h >= scenario.duration_h and backlog <= 1e-6),
            "ending_soc_pu": float(dispatch["battery_actual_soc_pu"].iloc[-1]),
            "minimum_soc_pu": float(dispatch["battery_actual_soc_pu"].min()),
            "window_transformer_peak_loading_pct_estimate": (
                float(loading.max()) if loading is not None else np.nan),
            # Objective 8: outage results are conditional on commissioning.
            "islanding_confirmed": False,
            "hardware_confirmed_installed": False,
        }


# ---------------------------------------------------------------------------
# Scenario builders
# ---------------------------------------------------------------------------


def low_solar_scenarios(profile: PvProfile, cfg: Case1Config,
                        top_n: int = 1) -> list[StressScenario]:
    """Worst measured low-irradiance windows, with optional extra derate."""
    scenarios: list[StressScenario] = []
    stress = cfg.stress

    for days in stress.low_solar_window_days:
        windows = worst_low_solar_windows(profile, days, top_n=top_n)
        for rank, row in windows.iterrows():
            for derate in stress.low_solar_derate_factors:
                tag = "measured" if derate == 1.0 else f"derate{derate:.2f}"
                scenarios.append(StressScenario(
                    name=f"LOW_SOLAR_{days}D_{tag}_r{rank + 1}",
                    family="LOW_SOLAR",
                    start=pd.Timestamp(row["start"]),
                    duration_h=int(days * 24),
                    pv_scale=float(derate),
                    note=(
                        f"worst measured {days}-day window in the 2025 NASA year "
                        f"({row['window_mean_per_kwp_kwh_per_day']:.2f} kWh/kWp/day, "
                        f"{row['vs_annual_mean_pct']:.0f}% of the annual mean)"
                        + ("" if derate == 1.0
                           else f"; PV additionally derated to {derate:.0%}")
                    ),
                ))
    return scenarios


def outage_scenarios(cfg: Case1Config, model_year: int,
                     durations: tuple[int, ...] | None = None,
                     months: tuple[int, ...] | None = None,
                     hours: tuple[int, ...] | None = None
                     ) -> list[StressScenario]:
    """
    Islanded windows on an explicit month x hour-of-day grid.

    The grid is explicit rather than evenly spaced array indices, so seasonal
    and time-of-day coverage is transparent (carried over from v18).
    """
    stress = cfg.stress
    durations = durations or stress.outage_duration_sweep_h
    months = months or tuple(range(1, 13))
    hours = hours or stress.outage_sample_hours

    scenarios = []
    for month in months:
        for hour in hours:
            start = pd.Timestamp(year=model_year, month=month,
                                 day=stress.outage_sample_day_of_month, hour=hour)
            for duration in durations:
                if start + pd.Timedelta(hours=duration - 1) > pd.Timestamp(
                        year=model_year, month=12, day=31, hour=23):
                    continue
                scenarios.append(StressScenario(
                    name=f"OUTAGE_{duration}H_M{month:02d}_H{hour:02d}",
                    family="GRID_OUTAGE",
                    start=start, duration_h=int(duration),
                    grid_available=False,
                    note="EPM supply unavailable; islanding capability unconfirmed",
                ))
    return scenarios


def high_demand_scenarios(study: Case1Study, houses: int,
                          cfg: Case1Config) -> list[StressScenario]:
    """High coincident demand, anchored on the measured annual peak-demand day."""
    load = study.load_kw(houses)
    daily = load.resample("D").sum()
    window_days = cfg.stress.high_demand_window_days

    rolled = load.resample("D").sum().rolling(window_days).sum()
    worst_end = rolled.idxmax()
    start = pd.Timestamp(worst_end) - pd.Timedelta(days=window_days - 1)

    peak_day = pd.Timestamp(daily.idxmax())

    scenarios = []
    for multiplier in cfg.stress.high_demand_multipliers:
        tag = "reference" if multiplier == 1.0 else f"x{multiplier:.2f}"
        scenarios.append(StressScenario(
            name=f"HIGH_DEMAND_{window_days}D_{tag}",
            family="HIGH_DEMAND",
            start=start, duration_h=int(window_days * 24),
            demand_scale=float(multiplier),
            note=(f"highest {window_days}-day demand window of the reference "
                  f"realization (peak day {peak_day:%Y-%m-%d})"
                  + ("" if multiplier == 1.0
                     else f"; demand scaled by {multiplier:.2f}")),
        ))
    return scenarios


def high_pv_export_limited_scenarios(profile: PvProfile, cfg: Case1Config,
                                      window_days: int = 3
                                      ) -> list[StressScenario]:
    """Highest measured irradiance window against restricted export."""
    daily = profile.per_kwp_kw.resample("D").sum()
    rolled = daily.rolling(window_days).sum()
    best_end = rolled.idxmax()
    start = pd.Timestamp(best_end) - pd.Timedelta(days=window_days - 1)

    scenarios = []
    for limit in cfg.stress.export_restriction_kw:
        scenarios.append(StressScenario(
            name=f"HIGH_PV_EXPORT_{limit:.1f}KW",
            family="HIGH_PV_EXPORT_LIMITED",
            start=start, duration_h=int(window_days * 24),
            export_limit_kw=float(limit),
            note=(f"highest measured {window_days}-day irradiance window "
                  f"({rolled.max() / window_days:.2f} kWh/kWp/day); "
                  f"export restricted to {limit:.1f} kW at the PCC"),
        ))
    return scenarios


def combined_scenarios(study: Case1Study, profile: PvProfile, houses: int,
                       cfg: Case1Config) -> list[StressScenario]:
    """
    Combined stressors. These are the cases that reveal whether a control
    strategy is actually robust, because single stressors are survivable at
    this hardware size.
    """
    stress = cfg.stress
    scenarios: list[StressScenario] = []

    worst = worst_low_solar_windows(profile, 5, top_n=1)
    if worst.empty:
        return scenarios
    low_start = pd.Timestamp(worst.iloc[0]["start"])
    low_note = (f"worst measured 5-day low-solar window "
                f"({worst.iloc[0]['window_mean_per_kwp_kwh_per_day']:.2f} "
                f"kWh/kWp/day)")

    # 1. Low solar and high demand together, grid available.
    scenarios.append(StressScenario(
        name="COMBINED_LOW_SOLAR_HIGH_DEMAND",
        family="COMBINED",
        start=low_start, duration_h=5 * 24,
        pv_scale=0.70, demand_scale=1.25,
        note=low_note + "; demand scaled by 1.25 and PV derated to 70%",
    ))

    # 2. Outage arriving at the END of the low-solar window, so the battery
    #    starts depleted rather than conveniently full.
    outage_start = low_start + pd.Timedelta(days=5)
    for duration in (12, 24):
        scenarios.append(StressScenario(
            name=f"COMBINED_LOW_SOLAR_THEN_OUTAGE_{duration}H",
            family="COMBINED",
            start=outage_start, duration_h=duration,
            pv_scale=0.70, grid_available=False,
            note=(low_note
                  + f"; {duration} h outage begins immediately afterwards with "
                    "PV still derated to 70%; islanding unconfirmed"),
        ))

    # 3. Outage during the high-demand window.
    high = high_demand_scenarios(study, houses, cfg)
    if high:
        scenarios.append(StressScenario(
            name="COMBINED_HIGH_DEMAND_OUTAGE_24H",
            family="COMBINED",
            start=pd.Timestamp(high[0].start) + pd.Timedelta(hours=18),
            duration_h=24, demand_scale=1.25, grid_available=False,
            note=("24 h outage beginning in the evening of the highest-demand "
                  "window, demand scaled by 1.25; islanding unconfirmed"),
        ))

    # 4. High PV with export blocked and the battery already full-ish.
    scenarios.extend([
        StressScenario(
            name="COMBINED_HIGH_PV_ZERO_EXPORT_LOW_DEMAND",
            family="COMBINED",
            start=pd.Timestamp(
                profile.per_kwp_kw.resample("D").sum().idxmax()),
            duration_h=48, demand_scale=0.75, export_limit_kw=0.0,
            note=("highest measured irradiance day with demand scaled to 75% "
                  "and export blocked: the maximum-curtailment condition"),
        ),
    ])
    return scenarios


def build_scenario_set(study: Case1Study, profile: PvProfile, houses: int,
                       outage_months: tuple[int, ...] = (3, 6, 9, 12),
                       outage_hours: tuple[int, ...] = (6, 12, 18, 0),
                       ) -> list[StressScenario]:
    """
    The default Case 1 scenario set.

    The outage grid is reduced from v18's 12 months x 8 hours to a 4 x 4
    sample for the control comparison, because every scenario is now run for
    every controller. `outage_scenarios` can be called with the full grid for
    the final single-controller distributional study.
    """
    cfg = study.cfg
    scenarios: list[StressScenario] = []
    scenarios += low_solar_scenarios(profile, cfg, top_n=1)
    scenarios += outage_scenarios(cfg, cfg.site.model_year,
                                  months=outage_months, hours=outage_hours)
    scenarios += high_demand_scenarios(study, houses, cfg)
    scenarios += high_pv_export_limited_scenarios(profile, cfg)
    scenarios += combined_scenarios(study, profile, houses, cfg)
    return scenarios


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def summarise_by_family(results: pd.DataFrame) -> pd.DataFrame:
    """Aggregate scenario results by stressor family and controller."""
    grouped = results.groupby(["family", "control"], sort=False)
    rows = []
    for (family, control), group in grouped:
        rows.append({
            "family": family,
            "control": control,
            "scenarios": int(len(group)),
            # Firm: no non-deferrable demand unserved (credits deferral).
            "survived_firm_load_pct": 100.0 * float(
                group["survived_firm_load"].mean()),
            # All-demand: nothing unserved and nothing left deferred.
            "served_all_demand_pct": 100.0 * float(
                group["served_all_demand_in_window"].mean()),
            # Legacy aliases, kept so older result readers do not break.
            "survived_full_window_pct": 100.0 * float(
                group["survived_full_window"].mean()),
            "survived_full_window_strict_pct": 100.0 * float(
                group["survived_full_window_strict"].mean()),
            "survived_critical_pct": 100.0 * float(
                group["survived_critical_full_window"].mean()),
            "median_survival_hours": float(group["survival_hours_full_load"].median()),
            "worst_survival_hours": float(group["survival_hours_full_load"].min()),
            "total_energy_not_served_kwh": float(group["energy_not_served_kwh"].sum()),
            "worst_energy_not_served_kwh": float(group["energy_not_served_kwh"].max()),
            "worst_shortfall_including_backlog_kwh": float(
                group["energy_shortfall_including_backlog_kwh"].max()),
            "worst_deferred_backlog_kwh": float(
                group["deferred_backlog_end_kwh"].max()),
            "p95_energy_not_served_kwh": float(
                group["energy_not_served_kwh"].quantile(0.95)),
            "worst_critical_energy_not_served_kwh": float(
                group["critical_energy_not_served_kwh"].max()),
            "median_critical_coverage_pct": float(
                group["critical_load_coverage_pct"].median()),
            "worst_critical_coverage_pct": float(
                group["critical_load_coverage_pct"].min()),
            "worst_minimum_soc_pu": float(group["minimum_soc_pu"].min()),
            "max_curtailment_pct": float(group["pv_curtailment_pct"].max()),
            "max_transformer_loading_pct_estimate": float(
                group["window_transformer_peak_loading_pct_estimate"].max()),
        })
    return pd.DataFrame(rows)


def vulnerability_index(summary: pd.DataFrame,
                        metric: str = "worst_shortfall_including_backlog_kwh"
                        ) -> pd.DataFrame:
    """
    Rank controllers by the shortfall they leave across stressor families.

    Deliberately simple and transparent: the mean, across families, of the
    share of that family's worst observed shortfall. A controller scoring 0
    never fell short; 1 is the worst in every family.

    The default metric counts a deferred load-management backlog as a
    shortfall, so a controller cannot rank well by postponing demand.
    """
    work = summary.copy()
    if metric not in work.columns:
        metric = "worst_energy_not_served_kwh"
    worst_by_family = work.groupby("family")[metric].transform("max")
    work["family_relative_exposure"] = np.where(
        worst_by_family > 0,
        work[metric] / worst_by_family,
        0.0,
    )
    ranked = (
        work.groupby("control")["family_relative_exposure"].mean()
        .sort_values().rename("vulnerability_index").reset_index()
    )
    ranked["rank"] = np.arange(1, len(ranked) + 1)
    ranked["metric"] = metric
    return ranked


def vulnerability_index_both(summary: pd.DataFrame) -> pd.DataFrame:
    """
    Both readings of the index side by side.

    firm         counts only non-deferrable demand that went unserved, so a
                 load-management controller is credited for deferring.
    all_demand   additionally counts anything still deferred at the end of a
                 window, so deferral earns nothing.

    A controller that ranks well on one and badly on the other is shifting
    demand, not supplying it, and the two columns make that visible.
    """
    firm = vulnerability_index(summary, "worst_energy_not_served_kwh")
    strict = vulnerability_index(summary,
                                 "worst_shortfall_including_backlog_kwh")

    merged = firm[["control", "vulnerability_index", "rank"]].rename(
        columns={"vulnerability_index": "vulnerability_index_firm",
                 "rank": "rank_firm"}
    ).merge(
        strict[["control", "vulnerability_index", "rank"]].rename(
            columns={"vulnerability_index": "vulnerability_index_all_demand",
                     "rank": "rank_all_demand"}),
        on="control", how="outer")

    merged["shifts_rather_than_supplies"] = (
        merged["rank_all_demand"] - merged["rank_firm"] >= 2)
    return merged.sort_values("rank_firm").reset_index(drop=True)
