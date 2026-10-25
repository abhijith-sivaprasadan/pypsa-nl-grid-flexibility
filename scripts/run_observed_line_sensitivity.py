"""Registered seven-day 2019 OPSD shape / synthetic-line sensitivity experiment.

Observed national Dutch *generation and demand shapes* come from OPSD,
whereas province allocation, transmission topology, line impedances, line
capacities, costs, and renewable capacity remain modelling assumptions.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pandas as pd

from pypsa_nl_grid_flexibility.analysis import calculate_summary
from pypsa_nl_grid_flexibility.config import (
    PROJECT_ROOT,
    load_model_config,
    load_scenarios,
)
from pypsa_nl_grid_flexibility.network import build_network, optimise_network
from pypsa_nl_grid_flexibility.profiles import (
    first_complete_opsd_window,
    generate_profiles,
)

SCENARIOS = ("base_2026_constrained_grid", "high_wind_offshore_growth")
LINE_FACTORS = (0.75, 1.0, 1.25)
SOURCE_URL = (
    "https://data.open-power-system-data.org/time_series/2020-10-06/"
    "time_series_60min_singleindex.csv"
)


def registered_grid() -> list[tuple[str, float]]:
    return [(scenario, f) for scenario in SCENARIOS for f in LINE_FACTORS]


def build_study_config(base: dict, path: str, start: str = "2019-01-01 00:00") -> dict:
    updated = deepcopy(base)
    updated["model"].update(
        {
            "start": start,
            "snapshots": 168,
            "profile_source": "opsd",
            "real_profile_csv": path,
        }
    )
    return updated


def run(raw_file: Path, out_dir: Path) -> None:
    if not raw_file.is_file():
        raise FileNotFoundError(raw_file)
    digest = hashlib.sha256(raw_file.read_bytes()).hexdigest()
    base = load_model_config()
    # Path is relative to PROJECT_ROOT to be consumed by the existing loader.
    rel = raw_file.resolve().relative_to(PROJECT_ROOT.resolve())
    selected = first_complete_opsd_window(raw_file, year=2019, hours=168)
    config = build_study_config(
        base, str(rel), start=selected.strftime("%Y-%m-%d %H:%M")
    )
    profiles = generate_profiles(config)  # Raises on missing or wrong 2019 hours.
    original = load_scenarios()
    records = []
    for name, factor in registered_grid():
        scenario = deepcopy(original[name])
        scenario["line_capacity_multiplier"] = float(factor)
        network = build_network(config, name, scenario, profiles)
        optimise_network(network)
        result = calculate_summary(network, name, config)
        result.update({"scenario": name, "line_multiplier": factor})
        records.append(result)
    out_dir.mkdir(parents=True, exist_ok=False)
    pd.DataFrame(records).to_csv(out_dir / "six_solved_scenarios.csv", index=False)
    manifest = {
        "status": "SCREENING_SYNTHETIC_NETWORK_WITH_OBSERVED_PROFILE_SHAPES",
        "original_source_url": SOURCE_URL,
        "source_sha256": digest,
        "source_bytes": raw_file.stat().st_size,
        "source_product_version": "2020-10-06",
        "observed_shape_year": 2019,
        "selection_rule": "earliest fully observed contiguous 168 UTC hours in 2019",
        "source_hour_start_utc": str(profiles.index[0]) + " UTC",
        "source_hour_end_utc": str(profiles.index[-1]) + " UTC",
        "source_rows_admitted": len(profiles),
        "research_grid": registered_grid(),
        "limitations": [
            "OPSD 2019 observed load and generation are scaled to unit-maximum shapes.",
            "Observed generation is NOT independent available wind or PV resource.",
            "Synthetic provincial network/corridors/line ratings have not been validated.",
            "Regional load allocation and 2024 capacity remain stylised.",
            "No security-constrained N-1 or market price inference.",
            "No annual comparison: the horizon covers the first complete 168 UTC hours.",
        ],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    run(
        PROJECT_ROOT / "data/raw/opsd_time_series_60min_singleindex.csv",
        PROJECT_ROOT / "runs/observed-2019-lines",
    )
