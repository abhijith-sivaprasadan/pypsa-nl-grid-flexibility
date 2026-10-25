"""Synthetic testbed physical arithmetic and like-for-like demand gates."""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

from pypsa_nl_grid_flexibility.comparability import audit_counterfactual_comparability

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "outputs/tables/scenario_summary.csv"
)


def raw():
    return SOURCE.read_text(encoding="utf-8")


def replace_field(text, scenario, field, value):
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    for row in rows:
        if row["scenario"] == scenario:
            row[field] = str(value)
    buff = io.StringIO()
    writer = csv.DictWriter(buff, fieldnames=reader.fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return buff.getvalue()


def test_archived_results_reconcile_and_demand_changes_disclosed():
    report = audit_counterfactual_comparability(raw())
    assert report["scenario_count"] == 9
    names = {
        row["scenario"]
        for row in report["cases"]
        if not row["fixed_demand_boundary"]
    }
    assert names == {"combined_bess_and_flex", "flexible_connection_contract"}
    assert report["changed_demand_count"] == 2


def test_tampered_renewable_balance_detected():
    text = replace_field(raw(), "base_2026_constrained_grid", "renewable_curtailment_mwh", 99)
    with pytest.raises(ValueError, match="Physical KPI identity"):
        audit_counterfactual_comparability(text)


def test_tampered_demand_balance_detected():
    text = replace_field(raw(), "flexible_connection_contract", "total_demand_mwh", 42)
    with pytest.raises(ValueError, match="Physical KPI identity"):
        audit_counterfactual_comparability(text)


def test_nonoptimal_record_fails_closed():
    text = replace_field(raw(), "high_wind_offshore_growth", "termination_condition", "infeasible")
    with pytest.raises(ValueError, match="Non-optimal"):
        audit_counterfactual_comparability(text)


def test_duplicate_scenario_fails_closed():
    text = raw() + raw().splitlines()[1] + "\n"
    with pytest.raises(ValueError, match="duplicate"):
        audit_counterfactual_comparability(text)
