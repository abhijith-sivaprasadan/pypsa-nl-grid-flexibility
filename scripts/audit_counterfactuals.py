"""Reconcile saved PyPSA KPI balances and counterfactual demand boundaries."""

from __future__ import annotations

import json
from pathlib import Path

from pypsa_nl_grid_flexibility.comparability import audit_counterfactual_comparability


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    source = root / "outputs/tables/scenario_summary.csv"
    report = audit_counterfactual_comparability(source.read_text(encoding="utf-8"))
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
