import pandas as pd

from pypsa_nl_grid_flexibility.config import load_model_config
from pypsa_nl_grid_flexibility.profiles import create_snapshots, generate_profiles


def test_profiles_shape():
    cfg = load_model_config()
    profiles = generate_profiles(cfg)

    assert profiles.shape[0] == int(cfg["model"]["snapshots"])
    assert list(profiles.columns) == [
        "demand_pu",
        "solar_pu",
        "wind_pu",
        "offshore_wind_pu",
    ]
    assert profiles["wind_pu"].max() <= 1.0
    assert profiles["solar_pu"].min() >= 0.0


def test_create_snapshots_uses_model_config():
    cfg = load_model_config()
    snapshots = create_snapshots(cfg)

    assert len(snapshots) == int(cfg["model"]["snapshots"])
    assert snapshots[0] == pd.Timestamp(cfg["model"]["start"])
