from __future__ import annotations

import numpy as np
import pandas as pd

from pypsa_nl_grid_flexibility.config import PROJECT_ROOT


def create_snapshots(model_config: dict) -> pd.DatetimeIndex:
    """Create hourly simulation snapshots from the model config."""
    model = model_config["model"]

    return pd.date_range(
        model["start"],
        periods=int(model["snapshots"]),
        freq="h",
    )


def _normalise_profile(series: pd.Series) -> pd.Series:
    series = pd.to_numeric(series, errors="coerce").interpolate(limit_direction="both")
    max_value = series.max(skipna=True)
    if pd.isna(max_value) or max_value <= 0:
        return pd.Series(0.0, index=series.index)
    return (series / max_value).clip(lower=0.0, upper=1.0)


def load_real_profiles(model_config: dict) -> pd.DataFrame | None:
    """
    Load trusted Netherlands hourly profile shapes when a raw OPSD file exists.

    Expected source file:
    Open Power System Data time_series_60min_singleindex.csv, which includes
    ENTSO-E-derived Netherlands load, solar, wind and offshore wind columns.
    """
    model = model_config["model"]
    if model.get("profile_source", "proxy") != "opsd":
        return None

    raw_path = PROJECT_ROOT / model.get(
        "real_profile_csv",
        "data/raw/opsd_time_series_60min_singleindex.csv",
    )
    if not raw_path.exists():
        return None

    snapshots = create_snapshots(model_config)
    raw = pd.read_csv(raw_path, parse_dates=["utc_timestamp"])
    raw = raw.set_index("utc_timestamp").sort_index()

    required_columns = {
        "demand_pu": "NL_load_actual_entsoe_transparency",
        "solar_pu": "NL_solar_generation_actual",
        "wind_pu": "NL_wind_generation_actual",
        "offshore_wind_pu": "NL_wind_offshore_generation_actual",
    }

    missing = [col for col in required_columns.values() if col not in raw.columns]
    if missing:
        raise ValueError(
            "Real profile CSV is missing required OPSD/ENTSO-E columns: "
            + ", ".join(missing)
        )

    window = raw.iloc[: len(snapshots)].copy()
    if len(window) < len(snapshots):
        raise ValueError(
            f"Real profile CSV has {len(window)} rows, but "
            f"{len(snapshots)} snapshots are required."
        )

    profiles = {
        out_col: _normalise_profile(window[in_col]).to_numpy()
        for out_col, in_col in required_columns.items()
    }
    return pd.DataFrame(profiles, index=snapshots)


def generate_profiles(model_config: dict) -> pd.DataFrame:
    """
    Generate hourly demand, solar, wind and offshore wind profile shapes.

    Installed capacity and annual demand are calibrated in model_config.yaml
    from public Dutch sources. These hourly shapes remain transparent proxy
    profiles so the project can run without API keys or external downloads:
    - demand with daily and weekly variation,
    - solar with daylight and cloud-factor behaviour,
    - onshore wind with variable multi-hour patterns,
    - offshore wind with smoother higher-capacity behaviour.
    """
    real_profiles = load_real_profiles(model_config)
    if real_profiles is not None:
        return real_profiles

    snapshots = create_snapshots(model_config)

    h = np.arange(len(snapshots))
    hour = snapshots.hour.to_numpy()
    day = (h // 24) % 7

    # Demand pattern: morning/evening peaks, night dip, weekday/weekend variation.
    morning_peak = 0.08 * np.exp(-(((hour - 8) / 3.2) ** 2))
    evening_peak = 0.14 * np.exp(-(((hour - 19) / 4.0) ** 2))
    night_dip = -0.08 * np.exp(-(((hour - 3) / 3.5) ** 2))

    weekday_factor = np.where(day < 5, 1.0, 0.92)
    slow_weather_factor = 1.0 + 0.06 * np.sin(2 * np.pi * h / (24 * 5))

    demand_pu = (
        (0.88 + morning_peak + evening_peak + night_dip)
        * weekday_factor
        * slow_weather_factor
    )

    demand_pu = np.clip(demand_pu, 0.65, 1.25)

    # Solar pattern: daylight curve with changing cloudiness by day.
    daylight = np.maximum(0.0, np.sin(np.pi * (hour - 6) / 12))

    cloud_factor_by_day = np.array(
        [
            0.55,
            0.85,
            1.00,
            0.70,
            0.95,
            0.65,
            0.80,
        ]
    )

    solar_pu = daylight * cloud_factor_by_day[day]
    solar_pu = np.clip(solar_pu, 0.0, 1.0)

    # Onshore wind: variable profile with short and medium frequency variation.
    wind_pu = (
        0.42
        + 0.22 * np.sin(2 * np.pi * (h + 5) / 36)
        + 0.14 * np.sin(2 * np.pi * h / 19)
        + 0.07 * np.sin(2 * np.pi * h / 7)
    )

    wind_pu = np.clip(wind_pu, 0.05, 0.95)

    # Offshore wind: smoother and generally stronger than onshore wind.
    offshore_wind_pu = (
        0.56
        + 0.18 * np.sin(2 * np.pi * (h + 11) / 48)
        + 0.10 * np.sin(2 * np.pi * h / 27)
    )

    offshore_wind_pu = np.clip(offshore_wind_pu, 0.12, 0.98)

    return pd.DataFrame(
        {
            "demand_pu": demand_pu,
            "solar_pu": solar_pu,
            "wind_pu": wind_pu,
            "offshore_wind_pu": offshore_wind_pu,
        },
        index=snapshots,
    )


def congestion_window_mask(
    profiles: pd.DataFrame,
    solar_threshold: float = 0.65,
    demand_quantile: float = 0.50,
    wind_threshold: float | None = None,
    **kwargs,
) -> pd.Series:
    """
    Return a boolean mask for hours that are likely to be congested.

    This is a simplified proxy used for flexible connection logic.
    Congested hours are assumed to occur when local renewable availability
    and/or demand are high enough to stress connection capacity.
    """
    if profiles.empty:
        return pd.Series(False, index=profiles.index)

    if "solar_pu" in profiles.columns:
        solar_condition = profiles["solar_pu"] >= solar_threshold
    else:
        solar_condition = pd.Series(False, index=profiles.index)

    if "demand_pu" in profiles.columns:
        demand_threshold = profiles["demand_pu"].quantile(demand_quantile)
        demand_condition = profiles["demand_pu"] >= demand_threshold
    else:
        demand_condition = pd.Series(False, index=profiles.index)

    if wind_threshold is not None and "wind_pu" in profiles.columns:
        wind_condition = profiles["wind_pu"] >= wind_threshold
    else:
        wind_condition = pd.Series(False, index=profiles.index)

    return (solar_condition & demand_condition) | wind_condition
