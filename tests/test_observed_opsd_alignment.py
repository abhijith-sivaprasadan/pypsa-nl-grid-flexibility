"""Requested year, missingness and non-overlapping wind are strict OPSD gates."""
from __future__ import annotations

import pandas as pd
import pytest

from pypsa_nl_grid_flexibility import profiles


def config(start="2019-01-01 00:00", n=3):
    return {
        "model": {
            "profile_source": "opsd",
            "start": start,
            "snapshots": n,
            "real_profile_csv": "opsd.csv",
        }
    }


def write_source(path, *, drop=None, duplicate=False, missing=False):
    times = ["2015-01-01T00:00:00Z"] + [
        f"2019-01-01T0{i}:00:00Z" for i in range(3)
    ]
    rows = [
        ["2015-01-01T00:00:00Z", 999, 999, 999, 999],
        *[
            [times[i + 1], 100 + i, 10 + i, 20 + i, 40 + i]
            for i in range(3)
        ],
    ]
    if drop is not None:
        del rows[drop]
    if duplicate:
        rows.append(rows[-1][:])
    if missing:
        rows[-1][1] = None
    pd.DataFrame(
        rows,
        columns=[
            "utc_timestamp",
            "NL_load_actual_entsoe_transparency",
            "NL_solar_generation_actual",
            "NL_wind_onshore_generation_actual",
            "NL_wind_offshore_generation_actual",
        ],
    ).to_csv(path, index=False)


def test_exact_2019_utc_alignment_not_first_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(profiles, "PROJECT_ROOT", tmp_path)
    write_source(tmp_path / "opsd.csv")
    frame = profiles.load_real_profiles(config())
    assert frame is not None
    assert len(frame) == 3
    assert frame.iloc[0]["demand_pu"] == pytest.approx(100 / 102)
    assert frame.iloc[0]["wind_pu"] == pytest.approx(20 / 22)
    assert frame.iloc[0]["offshore_wind_pu"] == pytest.approx(40 / 42)


def test_missing_requested_time_not_silently_replaced(tmp_path, monkeypatch):
    monkeypatch.setattr(profiles, "PROJECT_ROOT", tmp_path)
    write_source(tmp_path / "opsd.csv", drop=2)
    with pytest.raises(ValueError, match="exact requested UTC"):
        profiles.load_real_profiles(config())


def test_missing_observation_not_interpolated(tmp_path, monkeypatch):
    monkeypatch.setattr(profiles, "PROJECT_ROOT", tmp_path)
    write_source(tmp_path / "opsd.csv", missing=True)
    with pytest.raises(ValueError, match="missing/nonfinite"):
        profiles.load_real_profiles(config())


def test_duplicate_hours_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(profiles, "PROJECT_ROOT", tmp_path)
    write_source(tmp_path / "opsd.csv", duplicate=True)
    with pytest.raises(ValueError, match="Duplicate UTC"):
        profiles.load_real_profiles(config())


def test_requested_source_cannot_fall_back_to_synthetic(tmp_path, monkeypatch):
    monkeypatch.setattr(profiles, "PROJECT_ROOT", tmp_path)
    with pytest.raises(FileNotFoundError, match="OPSD"):
        profiles.generate_profiles(config())
