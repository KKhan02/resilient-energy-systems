"""
Solar resource and PV availability.

Two representations are kept strictly separate, exactly as in PyPSA v18:

  HOMER_CALIBRATED_SHAPE
      A deterministic hourly daylight shape reconstructed from solar geometry
      and monthly NASA radiation, then scaled so the 5.22 kWp reference array
      reproduces HOMER's accepted 7,326.3 kWh/year. Benchmark only.

  NASA_GHI_ERBS
      The un-normalised weather-derived profile built from the raw 2025 NASA
      POWER hourly file. GHI is the irradiance anchor; DNI/DHI are derived
      with Erbs at the +30 minute hourly midpoint; POA via isotropic
      transposition; NOCT cell temperature; derating and temperature
      coefficient from HOMER. This is the physical / decision profile and the
      default grid-study handoff.

The profile is normalised per kWp, so a larger array scales linearly. That is
correct for the available DC resource; inverter clipping and curtailment are
handled downstream in the dispatch models, not here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .config import ResourceConfig


@dataclass
class PvProfile:
    """Per-kWp hourly DC availability plus its provenance and diagnostics."""

    label: str
    role: str
    per_kwp_kw: pd.Series
    diagnostics: dict
    source_file: str | None = None

    def dc_kw(self, pv_kwp: float) -> pd.Series:
        return self.per_kwp_kw * float(pv_kwp)

    @property
    def annual_per_kwp_kwh(self) -> float:
        return float(self.per_kwp_kw.sum())


# ---------------------------------------------------------------------------
# HOMER-calibrated benchmark shape
# ---------------------------------------------------------------------------


def load_nasa_monthly_radiation(path: str | Path) -> np.ndarray:
    """Long-term monthly mean ALLSKY_SFC_SW_DWN in kWh/m2/day."""
    raw = pd.read_csv(path, skiprows=13)
    solar = raw[raw["PARAMETER"] == "ALLSKY_SFC_SW_DWN"].copy()

    month_cols = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                  "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

    if solar.empty:
        raise ValueError("ALLSKY_SFC_SW_DWN not found in NASA POWER file.")

    solar[month_cols] = solar[month_cols].apply(pd.to_numeric, errors="coerce")
    monthly = solar[month_cols].mean(axis=0).to_numpy(dtype=float)

    if np.isnan(monthly).any():
        raise ValueError("NASA monthly solar radiation contains missing values.")
    return monthly


def solar_day_shape(index: pd.DatetimeIndex, latitude_deg: float) -> np.ndarray:
    lat = np.deg2rad(latitude_deg)
    doy = index.dayofyear.to_numpy()
    hour = index.hour.to_numpy() + 0.5

    decl = np.deg2rad(23.45) * np.sin(2 * np.pi * (284 + doy) / 365.0)
    cos_ws = np.clip(-np.tan(lat) * np.tan(decl), -1, 1)
    ws = np.arccos(cos_ws)

    daylength = 24 * ws / np.pi
    sunrise = 12 - daylength / 2
    sunset = 12 + daylength / 2

    x = (hour - sunrise) / np.maximum(daylength, 1e-6)

    return np.where((hour >= sunrise) & (hour <= sunset),
                    np.sin(np.pi * np.clip(x, 0, 1)), 0.0)


def build_homer_calibrated_profile(index: pd.DatetimeIndex,
                                   homer: dict,
                                   monthly_radiation: np.ndarray,
                                   cfg: ResourceConfig,
                                   source_label: str) -> PvProfile:
    daylight = solar_day_shape(index, homer["homer_lat"])
    monthly_weight = np.array([monthly_radiation[m - 1] for m in index.month])

    base = daylight * monthly_weight
    base = base / base.max()

    # HOMER reports PV production on the DC side.
    target_kwh = homer["homer_pv_kwh"]
    reference_pv_kwp = homer["pv_kwp"]
    raw_energy_kwh = (reference_pv_kwp * base).sum()
    calibrated = base * (target_kwh / raw_energy_kwh)

    series = pd.Series(calibrated, index=index, name=cfg.pv_profile_column)

    return PvProfile(
        label="HOMER_CALIBRATED_SHAPE",
        role="benchmark annual-energy reference",
        per_kwp_kw=series,
        diagnostics={
            "method": "HOMER_CALIBRATED_GEOMETRIC_SHAPE",
            "monthly_radiation_source": source_label,
            "annual_pv_dc_kwh_at_reference_kwp": float(
                (reference_pv_kwp * series).sum()),
            "homer_annual_pv_dc_kwh": float(target_kwh),
            "peak_pv_dc_kw_at_reference_kwp": float(
                (reference_pv_kwp * series).max()),
        },
    )


# ---------------------------------------------------------------------------
# NASA POWER GHI + Erbs physical profile
# ---------------------------------------------------------------------------


def build_nasa_ghi_erbs_profile(index: pd.DatetimeIndex,
                                path: str | Path,
                                homer: dict,
                                cfg: ResourceConfig) -> PvProfile:
    """
    Build hourly DC availability directly from the raw NASA POWER hourly file.

    Identical physics to PyPSA v18 / pandapower v5, including the diagnostic
    gates on the annual POA/GHI ratio and the Erbs component closure.
    """
    import pvlib

    path = Path(path)
    raw = pd.read_csv(path, parse_dates=["timestamp_lst"])
    required = {"timestamp_lst", "ALLSKY_SFC_SW_DWN", "T2M"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(
            f"{path.name} is missing required NASA hourly columns: {sorted(missing)}")

    work = raw.rename(columns={"timestamp_lst": "timestamp"}).copy()
    for col in ("ALLSKY_SFC_SW_DWN", "T2M"):
        work[col] = pd.to_numeric(work[col], errors="coerce")
        work.loc[work[col] <= -900, col] = np.nan
    if work[["ALLSKY_SFC_SW_DWN", "T2M"]].isna().any().any():
        raise ValueError("NASA hourly GHI/T2M contains missing or fill values.")

    work = work.set_index("timestamp").reindex(index)
    if work[["ALLSKY_SFC_SW_DWN", "T2M"]].isna().any().any():
        raise ValueError(
            "Raw NASA hourly timestamps do not align with the model year.")

    solar_times = pd.DatetimeIndex(index).tz_localize(
        cfg.nasa_timezone_for_solar_position)
    solar_times_midpoint = solar_times + pd.Timedelta(
        minutes=cfg.solar_position_interval_midpoint_min)

    solar_position = pvlib.solarposition.get_solarposition(
        time=solar_times_midpoint,
        latitude=cfg.nasa_site_lat,
        longitude=cfg.nasa_site_lon,
        altitude=cfg.nasa_site_altitude_m,
    )

    ghi = work["ALLSKY_SFC_SW_DWN"].to_numpy(dtype=float)
    zenith = solar_position["zenith"].to_numpy(dtype=float)
    apparent_zenith = solar_position["apparent_zenith"].to_numpy(dtype=float)
    solar_azimuth = solar_position["azimuth"].to_numpy(dtype=float)
    cos_zenith = np.clip(np.cos(np.deg2rad(zenith)), 0.0, None)

    erbs = pvlib.irradiance.erbs(ghi=ghi, zenith=zenith,
                                 datetime_or_doy=solar_times_midpoint)
    dni = np.clip(np.asarray(erbs["dni"], dtype=float), 0.0, None)
    dhi = np.clip(np.asarray(erbs["dhi"], dtype=float), 0.0, None)
    horizontal_reconstructed = dni * cos_zenith + dhi

    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt=cfg.pv_surface_tilt_deg,
        surface_azimuth=cfg.pv_surface_azimuth_deg,
        solar_zenith=apparent_zenith,
        solar_azimuth=solar_azimuth,
        dni=dni, ghi=ghi, dhi=dhi,
        albedo=cfg.albedo, model="isotropic",
    )
    poa_global = np.clip(np.asarray(poa["poa_global"], dtype=float), 0.0, None)

    cell_temperature = (
        work["T2M"].to_numpy(dtype=float)
        + ((cfg.pv_noct_c - 20.0) / 800.0 * poa_global)
    )
    temperature_factor = np.clip(
        1.0 + cfg.pv_temp_coeff_per_c * (cell_temperature - 25.0), 0.0, None)

    # Per-kWp DC availability.
    per_kwp_kw = poa_global / 1000.0 * cfg.pv_derating_factor * temperature_factor

    annual_ghi = float(ghi.sum())
    annual_poa = float(poa_global.sum())
    poa_to_ghi = annual_poa / annual_ghi

    daylight = (ghi > 20.0) & (zenith < 87.0)
    relative_closure_error = (
        np.abs(horizontal_reconstructed[daylight] - ghi[daylight])
        / np.maximum(ghi[daylight], 1e-9)
    )
    max_closure_error = float(relative_closure_error.max())

    if not (cfg.poa_to_ghi_annual_ratio_min
            <= poa_to_ghi <= cfg.poa_to_ghi_annual_ratio_max):
        raise ValueError(
            f"NASA PV profile failed POA/GHI diagnostic: {poa_to_ghi:.4f}")
    if max_closure_error > cfg.component_closure_max_rel_error:
        raise ValueError(
            f"NASA PV profile failed Erbs closure diagnostic: {max_closure_error:.4%}")

    reference_kwp = homer["pv_kwp"]
    diagnostics = {
        "source": path.name,
        "method": "NASA_GHI_ERBS_MIDPOINT",
        "annual_ghi_kwh_m2": annual_ghi / 1000.0,
        "annual_poa_kwh_m2": annual_poa / 1000.0,
        "poa_to_ghi_ratio": poa_to_ghi,
        "erbs_max_daylight_closure_error": max_closure_error,
        "erbs_p95_daylight_closure_error": float(
            np.quantile(relative_closure_error, 0.95)),
        "annual_pv_dc_kwh_at_reference_kwp": float(
            (reference_kwp * per_kwp_kw).sum()),
        "peak_pv_dc_kw_at_reference_kwp": float((reference_kwp * per_kwp_kw).max()),
        "reference_kwp": reference_kwp,
    }

    series = pd.Series(per_kwp_kw, index=index, name=cfg.pv_profile_column)

    extra = pd.DataFrame({
        "ghi_wm2": ghi,
        "poa_global_wm2": poa_global,
        "erbs_dni_wm2": dni,
        "erbs_dhi_wm2": dhi,
        "t2m_c": work["T2M"].to_numpy(dtype=float),
        "cell_temperature_c": cell_temperature,
    }, index=index)

    profile = PvProfile(
        label="NASA_GHI_ERBS",
        role="GHI-anchored weather-derived physical case and default grid handoff",
        per_kwp_kw=series,
        diagnostics=diagnostics,
        source_file=path.name,
    )
    profile.weather = extra  # type: ignore[attr-defined]
    return profile


# ---------------------------------------------------------------------------
# Low-solar episode detection (Case 1 vulnerability input)
# ---------------------------------------------------------------------------


def daily_resource_energy(profile: PvProfile) -> pd.Series:
    """Daily per-kWp DC energy, used to locate measured low-solar episodes."""
    return profile.per_kwp_kw.resample("D").sum()


def worst_low_solar_windows(profile: PvProfile,
                            window_days: int,
                            top_n: int = 5) -> pd.DataFrame:
    """
    Locate the lowest rolling-sum windows of consecutive days in the ACTUAL
    weather year. Nothing is synthesised: these are measured episodes.

    Returns one row per non-overlapping candidate, worst first.
    """
    daily = daily_resource_energy(profile)
    rolled = daily.rolling(window_days).sum().dropna()

    long_run_mean = float(daily.mean()) * window_days
    candidates = rolled.sort_values()

    chosen: list[pd.Timestamp] = []
    rows = []
    for end_day, energy in candidates.items():
        start_day = end_day - pd.Timedelta(days=window_days - 1)
        if any(abs((start_day - c).days) < window_days for c in chosen):
            continue
        chosen.append(start_day)
        rows.append({
            "window_days": int(window_days),
            "start": start_day,
            "end": end_day,
            "window_per_kwp_kwh": float(energy),
            "window_mean_per_kwp_kwh_per_day": float(energy / window_days),
            "vs_annual_mean_pct": 100.0 * float(energy) / long_run_mean,
        })
        if len(rows) >= top_n:
            break

    return pd.DataFrame(rows)
