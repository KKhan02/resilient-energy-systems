"""
Study object: loads the inputs once and runs specifications against them.

A Case1Study holds the HOMER reference, the hourly demand table and the two
PV profiles, so every scenario in the package is driven by exactly the same
verified inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import lp_model
from .config import Case1Config
from .demand import (build_reference_load_8760, demand_summary, group_load_kw,
                     split_critical)
from .homer import homer_reference_table, parse_homer_xml
from .resource import (PvProfile, build_homer_calibrated_profile,
                       build_nasa_ghi_erbs_profile,
                       load_nasa_monthly_radiation)


@dataclass
class Case1Study:
    cfg: Case1Config
    homer: dict = field(init=False)
    ts: pd.DataFrame = field(init=False)
    profiles: dict[str, PvProfile] = field(init=False)
    monthly_radiation: np.ndarray = field(init=False)
    monthly_radiation_source: str = field(init=False)

    def __post_init__(self):
        cfg = self.cfg
        cfg.paths.ensure()

        self.homer = parse_homer_xml(cfg.paths.homer_xml)

        nasa_monthly = cfg.paths.nasa_monthly_csv
        if nasa_monthly is not None:
            self.monthly_radiation = load_nasa_monthly_radiation(nasa_monthly)
            self.monthly_radiation_source = f"NASA POWER: {nasa_monthly.name}"
        else:
            self.monthly_radiation = self.homer["monthly_radiation_kwh_m2_day"].copy()
            self.monthly_radiation_source = (
                "Monthly solar radiation stored in the HOMER XML")

        self.ts = build_reference_load_8760(
            self.homer, cfg.demand, cfg.site.model_year)

        index = self.ts.index
        homer_profile = build_homer_calibrated_profile(
            index, self.homer, self.monthly_radiation, cfg.resource,
            self.monthly_radiation_source)
        nasa_profile = build_nasa_ghi_erbs_profile(
            index, cfg.paths.nasa_hourly_csv, self.homer, cfg.resource)

        self.profiles = {
            homer_profile.label: homer_profile,
            nasa_profile.label: nasa_profile,
        }

    # -- convenience -------------------------------------------------------
    @property
    def decision_profile(self) -> PvProfile:
        """The physical profile used for all decision-facing Case 1 results."""
        return self.profiles["NASA_GHI_ERBS"]

    @property
    def benchmark_profile(self) -> PvProfile:
        """The HOMER-calibrated profile, retained for benchmark comparison."""
        return self.profiles["HOMER_CALIBRATED_SHAPE"]

    def homer_context(self) -> pd.DataFrame:
        return homer_reference_table(self.homer)

    def demand_summary(self) -> pd.DataFrame:
        return demand_summary(self.ts, self.cfg.demand.house_group_size_sweep)

    def load_kw(self, houses: int) -> pd.Series:
        return group_load_kw(self.ts, houses)

    def critical_load_kw(self, houses: int) -> pd.Series:
        critical, _ = split_critical(
            self.load_kw(houses), self.cfg.demand.critical_load_fraction)
        return critical

    def resource_diagnostics(self) -> pd.DataFrame:
        rows = []
        for label, profile in self.profiles.items():
            for key, value in profile.diagnostics.items():
                rows.append({
                    "profile": label,
                    "role": profile.role,
                    "diagnostic": key,
                    "value": value,
                })
        return pd.DataFrame(rows)

    def with_config(self, cfg: Case1Config) -> "Case1Study":
        """
        A view of this study under a different configuration.

        The loaded inputs (HOMER reference, demand table, PV profiles) are
        shared, so sensitivity sweeps over transformer or control settings do
        not re-read or rebuild anything. Only settings that do not change the
        inputs may be varied this way.
        """
        import copy

        clone = copy.copy(self)
        clone.cfg = cfg
        return clone

    # -- running -----------------------------------------------------------
    def resolve(self, spec: lp_model.SystemSpec) -> lp_model.ResolvedSystem:
        return lp_model.resolve_system(spec, self.cfg, self.homer)

    def run_lp(self,
               spec: lp_model.SystemSpec,
               profile: PvProfile | None = None,
               ts: pd.DataFrame | None = None,
               load_series_kw: pd.Series | None = None,
               require_feasible_hardware: bool = False):
        """
        Solve one system with the perfect-foresight LP.

        Returns (network, resolved system, dispatch table).
        """
        profile = profile or self.decision_profile
        ts = self.ts if ts is None else ts

        system = self.resolve(spec)
        if require_feasible_hardware and not system.hardware_feasible:
            raise ValueError(
                f"{spec.label}: hardware infeasible: {system.hardware_notes}")

        per_kwp = profile.per_kwp_kw.reindex(ts.index)
        if per_kwp.isna().any():
            raise ValueError(
                "PV profile does not cover the requested time index. "
                "Stress windows must be sliced from the annual index.")

        n = lp_model.build_network(
            ts, per_kwp, system, self.cfg, self.homer,
            load_series_kw=load_series_kw)
        lp_model.solve_network(n, self.cfg)

        dispatch = lp_model.extract_dispatch(n, system, self.cfg, per_kwp)
        return n, system, dispatch
