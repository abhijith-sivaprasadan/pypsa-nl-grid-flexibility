from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"

OUTPUT_DIR = PROJECT_ROOT / "outputs"
TABLE_DIR = OUTPUT_DIR / "tables"
FIGURE_DIR = OUTPUT_DIR / "figures"
REPORT_DIR = OUTPUT_DIR / "reports"


def ensure_output_dirs() -> None:
    """Create all output folders used by the project."""
    for path in [OUTPUT_DIR, TABLE_DIR, FIGURE_DIR, REPORT_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML file."""
    with Path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_model_config() -> dict[str, Any]:
    """Load the main model configuration."""
    return load_yaml(CONFIG_DIR / "model_config.yaml")


def load_scenarios() -> dict[str, Any]:
    """Load scenario definitions."""
    data = load_yaml(CONFIG_DIR / "scenarios.yaml")
    return data["scenarios"]
