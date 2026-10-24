"""
Stochastic household demand.

Ported unchanged from PyPSA v18: the HOMER monthly weekday/weekend profiles
provide the expected shape, and the XML stochastic settings (20% day-to-day,
25% timestep-to-timestep) are applied independently to each synthetic
household, which is then normalised back to the same annual energy.

The demand model is SYNTHETIC. The variability method and settings come from
the accepted HOMER XML, but the original HOMER random seed is not available,
so this reproduces the method, not HOMER's exact realization.

Case 1 adds only decompositions of that same series:
  * a critical / non-critical split, for outage critical-load coverage
  * a deferrable backlog model, for the causal load-management controller
Neither changes the annual energy or the aggregate hourly series.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DemandConfig
from .homer import MONTH_KEY


def build_deterministic_reference_load(index: pd.DatetimeIndex,
                                       homer: dict) -> pd.Series:
    raw_4hh = np.empty(len(index), dtype=float)

    for i, ts in enumerate(index):
        month = MONTH_KEY[ts.month]
        profiles = (
            homer["monthly_load_profiles_weekend_4hh_kw"]
            if ts.weekday() >= 5
            else homer["monthly_load_profiles_weekday_4hh_kw"]
        )
        raw_4hh[i] = profiles[month][ts.hour]

    target_4hh_kwh = homer["annual_load_4hh_kwh"]
    raw_4hh *= target_4hh_kwh / raw_4hh.sum()

    return pd.Series(raw_4hh, index=index, name="deterministic_load_4hh_kw")


def homer_stochastic_household_profile(deterministic_1hh_kw: pd.Series,
                                       rng: np.random.Generator,
                                       daily_sigma: float,
                                       timestep_sigma: float,
                                       annual_target_kwh: float,
                                       min_factor: float = 0.0,
                                       return_diagnostics: bool = False):
    """HOMER perturbation: alpha = 1 + delta_day + delta_timestep."""
    index = deterministic_1hh_kw.index

    day_codes = index.dayofyear.to_numpy() - 1
    n_days = int(index.dayofyear.max())

    daily_delta = rng.normal(loc=0.0, scale=daily_sigma, size=n_days)
    timestep_delta = rng.normal(loc=0.0, scale=timestep_sigma, size=len(index))

    alpha_raw = 1.0 + daily_delta[day_codes] + timestep_delta

    clipped_mask = alpha_raw < min_factor
    alpha = np.maximum(alpha_raw, min_factor)

    varied = deterministic_1hh_kw.to_numpy(dtype=float) * alpha

    if varied.sum() <= 0:
        raise ValueError(
            "Stochastic profile has zero annual energy before normalization.")

    varied *= annual_target_kwh / varied.sum()

    series = pd.Series(varied, index=index, dtype=float)

    if not return_diagnostics:
        return series

    return series, {
        "clipped_hours": int(clipped_mask.sum()),
        "clipped_share_pct": 100 * float(clipped_mask.mean()),
        "minimum_raw_factor": float(alpha_raw.min()),
        "maximum_raw_factor": float(alpha_raw.max()),
    }


def build_reference_load_8760(homer: dict,
                              cfg: DemandConfig,
                              model_year: int,
                              seed: int | None = None,
                              profile_house_count: int | None = None) -> pd.DataFrame:
    """
    Build the hourly household demand table.

    Returns a DataFrame indexed by timestamp with, for N = profile_house_count:
      deterministic_load_1hh_kw, deterministic_load_4hh_kw,
      house_1_kw .. house_N_kw, load_1hh_kw .. load_Nhh_kw
    """
    seed = cfg.stochastic_load_seed if seed is None else int(seed)
    profile_house_count = int(
        cfg.stochastic_profile_house_count
        if profile_house_count is None
        else profile_house_count
    )

    idx = pd.date_range(f"{model_year}-01-01 00:00",
                        f"{model_year}-12-31 23:00", freq="h")

    deterministic_4hh = build_deterministic_reference_load(idx, homer)
    deterministic_1hh = deterministic_4hh / homer["reference_houses"]
    annual_1hh_kwh = homer["annual_load_4hh_kwh"] / homer["reference_houses"]

    df = pd.DataFrame(index=idx)
    df.index.name = "timestamp"
    df["deterministic_load_1hh_kw"] = deterministic_1hh
    df["deterministic_load_4hh_kw"] = deterministic_4hh

    clipped_total = 0

    if cfg.use_stochastic_household_loads:
        child_seeds = np.random.SeedSequence(int(seed)).spawn(profile_house_count)
        for house in range(1, profile_house_count + 1):
            rng = np.random.default_rng(child_seeds[house - 1])
            profile, diag = homer_stochastic_household_profile(
                deterministic_1hh_kw=deterministic_1hh,
                rng=rng,
                daily_sigma=homer["load_daily_variability_pu"],
                timestep_sigma=homer["load_timestep_variability_pu"],
                annual_target_kwh=annual_1hh_kwh,
                min_factor=cfg.stochastic_min_factor,
                return_diagnostics=True,
            )
            df[f"house_{house}_kw"] = profile
            clipped_total += diag["clipped_hours"]
    else:
        for house in range(1, profile_house_count + 1):
            df[f"house_{house}_kw"] = deterministic_1hh

    running = np.zeros(len(df), dtype=float)
    for houses in range(1, profile_house_count + 1):
        running = running + df[f"house_{houses}_kw"].to_numpy()
        df[f"load_{houses}hh_kw"] = running.copy()

    df["load_1hh_kw"] = df["house_1_kw"]

    denominator = len(df) * profile_house_count
    df.attrs["stochastic_seed"] = int(seed)
    df.attrs["profile_house_count"] = profile_house_count
    df.attrs["clipped_household_hours"] = clipped_total
    df.attrs["clipped_household_hours_pct"] = (
        100 * clipped_total / denominator if denominator else 0.0
    )
    return df


def group_load_kw(ts: pd.DataFrame, houses: int) -> pd.Series:
    col = f"load_{int(houses)}hh_kw"
    if col not in ts.columns:
        raise KeyError(
            f"{col} not available. Generated profiles cover up to "
            f"{ts.attrs.get('profile_house_count', '?')} houses."
        )
    return ts[col]


def household_columns(houses: int) -> list[str]:
    return [f"house_{h}_kw" for h in range(1, int(houses) + 1)]


def demand_summary(ts: pd.DataFrame, house_counts) -> pd.DataFrame:
    rows = []
    for houses in house_counts:
        series = group_load_kw(ts, houses)
        rows.append({
            "houses": houses,
            "annual_load_kwh": float(series.sum()),
            "average_load_kw": float(series.mean()),
            "peak_load_kw": float(series.max()),
            "load_factor": float(series.mean() / series.max()),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Case 1 decompositions
# ---------------------------------------------------------------------------


def split_critical(load_kw: pd.Series, critical_fraction: float):
    """
    Split hourly demand into a critical and a non-critical component.

    This is a flat fractional split, because no appliance survey exists for
    El Arenal. It must not be read as a metered critical-load measurement.
    """
    critical = load_kw * float(critical_fraction)
    return critical, load_kw - critical


def split_deferrable(load_kw: pd.Series, deferrable_fraction: float):
    """
    Split hourly demand into a firm component and a same-day deferrable
    component used by the load-management controller.

    Flat fractional split, same caveat as split_critical.
    """
    deferrable = load_kw * float(deferrable_fraction)
    return load_kw - deferrable, deferrable
