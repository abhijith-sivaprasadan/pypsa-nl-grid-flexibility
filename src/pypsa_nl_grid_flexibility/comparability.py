"""Independent comparability gates for the saved synthetic Dutch-grid screening.

Rechecks arithmetic and asks whether case/base demand is matched. This does
not authenticate synthetic topology, estimate real congestion or re-solve PyPSA.
"""

from __future__ import annotations

import csv
import io
import math


def _num(row: dict[str, str], key: str) -> float:
    try:
        value = float(row[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Missing/non-numeric field {key}") from exc
    if not math.isfinite(value):
        raise ValueError(f"Nonfinite field {key}")
    return value


def audit_counterfactual_comparability(
    contents: str, base: str = "base_2026_constrained_grid"
) -> dict:
    reader = csv.DictReader(io.StringIO(contents))
    if not reader.fieldnames:
        raise ValueError("Missing CSV header")
    rows = list(reader)
    if len(rows) < 2 or any(None in row or None in row.values() for row in rows):
        raise ValueError("Empty or malformed scenario summary")
    cases = {}
    for row in rows:
        case = row.get("scenario")
        if not case or case in cases:
            raise ValueError("Missing or duplicate scenario")
        if row.get("solve_status") != "ok" or row.get("termination_condition") != "optimal":
            raise ValueError("Non-optimal scenario must not be published as a result")
        balance_pairs = [
            (
                "renewable_available_mwh",
                _num(row, "renewable_dispatch_mwh") + _num(row, "renewable_curtailment_mwh"),
            ),
        ]
        # Storage losses/charge/discharge also enter the hourly energy balance.
        # Dispatch + backup equals load directly only with inactive BESS.
        if _num(row, "bess_throughput_mwh") < 1e-8:
            balance_pairs.append(
                (
                    "total_demand_mwh",
                    _num(row, "renewable_dispatch_mwh") + _num(row, "backup_dispatch_mwh"),
                )
            )
        for name, expected in balance_pairs:
            actual = _num(row, name)
            if not math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-4):
                raise ValueError(f"Physical KPI identity fails: {case}/{name}")
        if _num(row, "total_demand_mwh") <= 0:
            raise ValueError("Nonpositive demand")
        cases[case] = row
    if base not in cases:
        raise ValueError("Reference scenario missing")
    base_row = cases[base]
    base_demand = _num(base_row, "total_demand_mwh")
    results = []
    for name, row in sorted(cases.items()):
        demand = _num(row, "total_demand_mwh")
        delta = demand - base_demand
        comparable = math.isclose(demand, base_demand, rel_tol=0, abs_tol=1e-4)
        results.append(
            {
                "scenario": name,
                "fixed_demand_boundary": comparable,
                "demand_delta_vs_base_mwh": delta,
                "interpretation": (
                    "SAME_CONFIGURED_DEMAND_PROXY"
                    if comparable
                    else "CHANGED_DEMAND_NOT_LIKE_FOR_LIKE_SERVICE"
                ),
            }
        )
    return {
        "status": "PASS_SAVED_KPI_AND_DEMAND_BOUNDARY_CHECK",
        "scenario_count": len(cases),
        "base_scenario": base,
        "matched_demand_count": sum(x["fixed_demand_boundary"] for x in results),
        "changed_demand_count": sum(not x["fixed_demand_boundary"] for x in results),
        "cases": results,
        "scientific_boundary": (
            "Configured synthetic provincial topology/corridor capacities, not verified Dutch "
            "grid telemetry; identical demand does not by itself establish causal comparability. "
            "Varying demand must not be included in a like-for-like intervention cost ranking."
        ),
    }
