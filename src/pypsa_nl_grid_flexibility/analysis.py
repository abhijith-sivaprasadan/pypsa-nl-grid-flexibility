from __future__ import annotations

import numpy as np
import pandas as pd

RENEWABLE_CARRIERS = {"solar", "wind", "offshore_wind"}


def renewable_generators(n) -> list[str]:
    return [
        g
        for g in n.generators.index
        if n.generators.at[g, "carrier"] in RENEWABLE_CARRIERS
    ]


def backup_generators(n) -> list[str]:
    return [g for g in n.generators.index if n.generators.at[g, "carrier"] == "backup"]


def calculate_available_renewable(n) -> pd.DataFrame:
    columns = {}
    for g in renewable_generators(n):
        p_nom = float(n.generators.at[g, "p_nom"])
        columns[g] = p_nom * n.generators_t.p_max_pu[g]
    return pd.DataFrame(columns, index=n.snapshots)


def _storage_power_series(n, storage_unit: str) -> pd.Series:
    if hasattr(n.storage_units_t, "p") and storage_unit in n.storage_units_t.p.columns:
        return n.storage_units_t.p[storage_unit]
    dispatch = (
        n.storage_units_t.p_dispatch[storage_unit]
        if hasattr(n.storage_units_t, "p_dispatch")
        and storage_unit in n.storage_units_t.p_dispatch.columns
        else pd.Series(0.0, index=n.snapshots)
    )
    store = (
        n.storage_units_t.p_store[storage_unit]
        if hasattr(n.storage_units_t, "p_store")
        and storage_unit in n.storage_units_t.p_store.columns
        else pd.Series(0.0, index=n.snapshots)
    )
    return dispatch - store


def calculate_hourly_results(n, scenario_name: str) -> pd.DataFrame:
    columns = {"scenario": pd.Series(scenario_name, index=n.snapshots)}

    for load in n.loads.index:
        columns[f"{load}_mw"] = n.loads_t.p_set[load]

    for g in n.generators.index:
        columns[f"{g}_dispatch_mw"] = n.generators_t.p[g]

    available = calculate_available_renewable(n)
    for g in available.columns:
        dispatch = n.generators_t.p[g]
        columns[f"{g}_available_mw"] = available[g]
        columns[f"{g}_curtailment_mw"] = (available[g] - dispatch).clip(lower=0)

    for line in n.lines.index:
        flow = n.lines_t.p0[line]
        columns[f"{line}_flow_mw"] = flow
        columns[f"{line}_utilisation_pct"] = (
            100 * flow.abs() / float(n.lines.at[line, "s_nom"])
        )

    for su in n.storage_units.index:
        columns[f"{su}_dispatch_mw"] = _storage_power_series(n, su)
        columns[f"{su}_soc_mwh"] = n.storage_units_t.state_of_charge[su]

    columns["total_demand_mw"] = n.loads_t.p_set.sum(axis=1)
    ren = renewable_generators(n)
    columns["total_renewable_dispatch_mw"] = (
        n.generators_t.p[ren].sum(axis=1) if ren else pd.Series(0.0, index=n.snapshots)
    )
    back = backup_generators(n)
    columns["total_backup_dispatch_mw"] = (
        n.generators_t.p[back].sum(axis=1)
        if back
        else pd.Series(0.0, index=n.snapshots)
    )

    hourly = pd.DataFrame(columns, index=n.snapshots)
    curtailment_cols = [c for c in hourly.columns if c.endswith("_curtailment_mw")]
    hourly["total_curtailment_mw"] = (
        hourly[curtailment_cols].sum(axis=1) if curtailment_cols else 0.0
    )
    return hourly.copy()


def calculate_congestion_proxy(n, hourly: pd.DataFrame, model_config: dict) -> dict:
    threshold = float(
        model_config["model"].get("congestion_utilisation_threshold_pct", 90)
    )
    overload_penalty = float(
        model_config["model"].get("line_overload_penalty_eur_per_line_hour", 15000)
    )
    curtailment_value = float(
        model_config["model"]["renewable_curtailment_value_eur_per_mwh"]
    )
    backup_cost = float(model_config["model"]["backup_marginal_cost_eur_per_mwh"])
    util_cols = [c for c in hourly.columns if c.endswith("_utilisation_pct")]
    if util_cols:
        line_hours = int((hourly[util_cols] > threshold).sum().sum())
        severity = float((hourly[util_cols] - threshold).clip(lower=0).sum().sum())
    else:
        line_hours = 0
        severity = 0.0
    curtailment_mwh = float(hourly["total_curtailment_mw"].sum())
    backup_mwh = float(hourly["total_backup_dispatch_mw"].sum())
    return {
        "line_hours_above_threshold": line_hours,
        "congestion_severity_pct_hours": severity,
        "curtailment_cost_proxy_eur": curtailment_mwh * curtailment_value,
        "backup_cost_proxy_eur": backup_mwh * backup_cost,
        "line_overload_cost_proxy_eur": line_hours * overload_penalty,
        "total_congestion_cost_proxy_eur": curtailment_mwh * curtailment_value
        + backup_mwh * backup_cost
        + line_hours * overload_penalty,
    }


def calculate_summary(n, scenario_name: str, model_config: dict) -> dict:
    hourly = calculate_hourly_results(n, scenario_name)
    demand = hourly["total_demand_mw"].sum()
    renewable_dispatch = hourly["total_renewable_dispatch_mw"].sum()
    backup_dispatch = hourly["total_backup_dispatch_mw"].sum()
    curtailment = hourly["total_curtailment_mw"].sum()
    available = calculate_available_renewable(n).sum().sum()

    util = {
        line: 100 * n.lines_t.p0[line].abs() / float(n.lines.at[line, "s_nom"])
        for line in n.lines.index
    }
    max_line_util = max(series.max() for series in util.values()) if util else 0.0
    line_hours_above_90 = sum(int((series > 90).sum()) for series in util.values())

    bess_throughput = 0.0
    bess_energy_capacity = 0.0
    for su in n.storage_units.index:
        p = _storage_power_series(n, su)
        bess_throughput += float(p.abs().sum() / 2.0)
        bess_energy_capacity += float(
            n.storage_units.at[su, "p_nom"] * n.storage_units.at[su, "max_hours"]
        )

    emission_factor = float(model_config["model"]["backup_emission_tco2_per_mwh"])
    curtailment_value = float(
        model_config["model"]["renewable_curtailment_value_eur_per_mwh"]
    )
    out = {
        "scenario": scenario_name,
        "solve_status": getattr(n, "meta", {}).get("solve_status", "unknown"),
        "termination_condition": getattr(n, "meta", {}).get(
            "termination_condition",
            "unknown",
        ),
        "objective_cost_eur": float(n.objective),
        "total_demand_mwh": float(demand),
        "renewable_dispatch_mwh": float(renewable_dispatch),
        "renewable_available_mwh": float(available),
        "renewable_curtailment_mwh": float(curtailment),
        "curtailment_rate_pct": (
            float(100 * curtailment / available) if available else 0.0
        ),
        "backup_dispatch_mwh": float(backup_dispatch),
        "renewable_share_of_demand_pct": (
            float(100 * renewable_dispatch / demand) if demand else 0.0
        ),
        "max_line_utilisation_pct": float(max_line_util),
        "line_hours_above_90pct": int(line_hours_above_90),
        "bess_throughput_mwh": float(bess_throughput),
        "bess_energy_capacity_mwh": float(bess_energy_capacity),
        "bess_equivalent_cycles": (
            float(bess_throughput / bess_energy_capacity)
            if bess_energy_capacity
            else 0.0
        ),
        "emissions_proxy_tco2": float(backup_dispatch * emission_factor),
        "curtailment_value_proxy_eur": float(curtailment * curtailment_value),
    }
    out.update(calculate_congestion_proxy(n, hourly, model_config))
    return out


def validate_scenario_summary(
    summary: pd.DataFrame,
    tolerance_mwh: float = 1e-3,
) -> pd.DataFrame:
    """Return pass/fail validation checks for scenario-level KPI consistency."""
    checks = []

    def add_check(
        check: str,
        passed: bool,
        value: float | int | str,
        tolerance: float | int | str,
        details: str,
    ) -> None:
        checks.append(
            {
                "check": check,
                "passed": bool(passed),
                "value": value,
                "tolerance": tolerance,
                "details": details,
            }
        )

    if summary.empty:
        add_check(
            "summary_non_empty",
            False,
            0,
            ">0 rows",
            "Scenario summary has no rows.",
        )
        return pd.DataFrame(checks)

    required = {
        "scenario",
        "renewable_available_mwh",
        "renewable_dispatch_mwh",
        "renewable_curtailment_mwh",
        "curtailment_rate_pct",
        "renewable_share_of_demand_pct",
        "bess_equivalent_cycles",
        "objective_cost_eur",
    }
    missing = sorted(required.difference(summary.columns))
    add_check(
        "required_columns_present",
        not missing,
        ", ".join(missing) if missing else "none",
        "none missing",
        "Required KPI columns are available for validation.",
    )

    if missing:
        return pd.DataFrame(checks)

    curtailment_error = (
        summary["renewable_available_mwh"]
        - summary["renewable_dispatch_mwh"]
        - summary["renewable_curtailment_mwh"]
    ).abs()
    max_curtailment_error = float(curtailment_error.max(skipna=True))
    add_check(
        "curtailment_balance",
        max_curtailment_error <= tolerance_mwh,
        max_curtailment_error,
        tolerance_mwh,
        "renewable_available_mwh - renewable_dispatch_mwh equals renewable_curtailment_mwh.",
    )

    renewable_share_max = float(
        summary["renewable_share_of_demand_pct"].max(skipna=True)
    )
    add_check(
        "renewable_share_not_above_100_pct",
        renewable_share_max <= 100.0 + 1e-9,
        renewable_share_max,
        "<=100%",
        "Renewable dispatch share of demand remains physically bounded.",
    )

    curtailment_rate_min = float(summary["curtailment_rate_pct"].min(skipna=True))
    curtailment_rate_max = float(summary["curtailment_rate_pct"].max(skipna=True))
    add_check(
        "curtailment_rate_between_0_and_100_pct",
        curtailment_rate_min >= -1e-9 and curtailment_rate_max <= 100.0 + 1e-9,
        f"{curtailment_rate_min:.6g} to {curtailment_rate_max:.6g}",
        "0% to 100%",
        "Curtailment rates are within expected percentage bounds.",
    )

    bess_cycles = pd.to_numeric(summary["bess_equivalent_cycles"], errors="coerce")
    invalid_bess_cycles = int((~np.isfinite(bess_cycles) | (bess_cycles < 0)).sum())
    add_check(
        "bess_cycles_finite_non_negative",
        invalid_bess_cycles == 0,
        invalid_bess_cycles,
        0,
        "BESS equivalent cycles are finite and non-negative.",
    )

    objective = pd.to_numeric(summary["objective_cost_eur"], errors="coerce")
    invalid_objective = int((~np.isfinite(objective) | (objective < 0)).sum())
    add_check(
        "objective_cost_finite_non_negative",
        invalid_objective == 0,
        invalid_objective,
        0,
        "Objective costs are finite and non-negative.",
    )

    if {"solve_status", "termination_condition"}.issubset(summary.columns):
        solved = (summary["solve_status"] == "ok") & (
            summary["termination_condition"] == "optimal"
        )
        failed = summary.loc[~solved, "scenario"].astype(str).tolist()
        add_check(
            "all_scenarios_solved_optimal",
            not failed,
            ", ".join(failed) if failed else "all optimal",
            "all optimal",
            "Every scenario reports PyPSA status ok and optimal termination.",
        )
    else:
        add_check(
            "all_scenarios_solved_optimal",
            False,
            "solve metadata missing",
            "solve_status=ok and termination_condition=optimal",
            "Solve metadata is required for this validation.",
        )

    if "recommendation_rank" in summary.columns:
        ranks = pd.to_numeric(summary["recommendation_rank"], errors="coerce")
        expected = set(range(1, len(summary) + 1))
        actual = set(ranks.dropna().astype(int).tolist())
        add_check(
            "recommendation_ranks_complete",
            actual == expected and not ranks.isna().any(),
            len(actual),
            len(expected),
            "Recommendation ranks form a complete 1..N sequence.",
        )

    return pd.DataFrame(checks)


def _normalise_for_score(series: pd.Series) -> pd.Series:
    max_abs = series.abs().max(skipna=True)
    if pd.isna(max_abs) or max_abs == 0:
        return pd.Series(0.0, index=series.index)
    return series / max_abs


def add_baseline_comparison(summary: pd.DataFrame) -> pd.DataFrame:
    summary = summary.copy()
    baseline = summary.loc[summary["scenario"] == "base_2026_constrained_grid"]
    if baseline.empty:
        summary["grid_value_score"] = np.nan
        summary["recommendation_rank"] = np.nan
        return summary

    b = baseline.iloc[0]
    summary["renewable_dispatch_increase_vs_base_mwh"] = (
        summary["renewable_dispatch_mwh"] - b["renewable_dispatch_mwh"]
    )
    summary["renewable_available_increase_vs_base_mwh"] = (
        summary["renewable_available_mwh"] - b["renewable_available_mwh"]
    )
    summary["absolute_curtailment_change_vs_base_mwh"] = (
        summary["renewable_curtailment_mwh"] - b["renewable_curtailment_mwh"]
    )
    summary["curtailment_reduction_vs_base_mwh"] = (
        b["renewable_curtailment_mwh"] - summary["renewable_curtailment_mwh"]
    )
    summary["curtailment_rate_reduction_vs_base_pct"] = (
        b["curtailment_rate_pct"] - summary["curtailment_rate_pct"]
    )
    summary["backup_reduction_vs_base_mwh"] = (
        b["backup_dispatch_mwh"] - summary["backup_dispatch_mwh"]
    )
    summary["emissions_reduction_vs_base_tco2"] = (
        b["emissions_proxy_tco2"] - summary["emissions_proxy_tco2"]
    )
    summary["objective_cost_reduction_vs_base_eur"] = (
        b["objective_cost_eur"] - summary["objective_cost_eur"]
    )
    summary["congestion_cost_reduction_vs_base_eur"] = (
        b["total_congestion_cost_proxy_eur"]
        - summary["total_congestion_cost_proxy_eur"]
    )
    summary["line_overload_reduction_vs_base_hours"] = (
        b["line_hours_above_90pct"] - summary["line_hours_above_90pct"]
    )

    score = (
        0.28 * _normalise_for_score(summary["renewable_dispatch_increase_vs_base_mwh"])
        + 0.24 * _normalise_for_score(summary["backup_reduction_vs_base_mwh"])
        + 0.18 * _normalise_for_score(summary["line_overload_reduction_vs_base_hours"])
        + 0.12 * _normalise_for_score(summary["curtailment_rate_reduction_vs_base_pct"])
        + 0.10 * _normalise_for_score(summary["objective_cost_reduction_vs_base_eur"])
        + 0.08 * _normalise_for_score(summary["congestion_cost_reduction_vs_base_eur"])
    )
    summary["grid_value_score"] = 100 * score
    summary = summary.sort_values("grid_value_score", ascending=False).reset_index(
        drop=True
    )
    summary["recommendation_rank"] = np.arange(1, len(summary) + 1)
    return summary


def _line_utilisation_columns(hourly: pd.DataFrame) -> list[str]:
    return [col for col in hourly.columns if col.endswith("_utilisation_pct")]


def _line_from_utilisation_column(column: str) -> str:
    return column.removesuffix("_utilisation_pct")


def calculate_bottleneck_diagnostics(
    hourly: pd.DataFrame,
    model_config: dict,
) -> pd.DataFrame:
    """Rank scenario-line bottlenecks from solved hourly flow results."""
    if hourly.empty or "scenario" not in hourly.columns:
        return pd.DataFrame()

    threshold = float(
        model_config["model"].get("congestion_utilisation_threshold_pct", 90)
    )
    rows = []

    for scenario_name, scenario_data in hourly.groupby("scenario"):
        for util_col in _line_utilisation_columns(scenario_data):
            line = _line_from_utilisation_column(util_col)
            flow_col = f"{line}_flow_mw"
            utilisation = pd.to_numeric(scenario_data[util_col], errors="coerce")
            flow = (
                pd.to_numeric(scenario_data[flow_col], errors="coerce")
                if flow_col in scenario_data.columns
                else pd.Series(0.0, index=scenario_data.index)
            )
            exceedance = (utilisation - threshold).clip(lower=0.0)
            congested = utilisation > threshold

            rows.append(
                {
                    "scenario": scenario_name,
                    "line": line,
                    "max_utilisation_pct": float(utilisation.max(skipna=True)),
                    "mean_utilisation_pct": float(utilisation.mean(skipna=True)),
                    "hours_above_threshold": int(congested.sum()),
                    "congestion_severity_pct_hours": float(exceedance.sum()),
                    "peak_abs_flow_mw": float(flow.abs().max(skipna=True)),
                    "flow_mwh_during_congested_hours": float(
                        flow.abs().where(congested, 0.0).sum()
                    ),
                }
            )

    diagnostics = pd.DataFrame(rows)
    if diagnostics.empty:
        return diagnostics

    diagnostics["bottleneck_rank_score"] = (
        diagnostics["congestion_severity_pct_hours"]
        + 0.05 * diagnostics["hours_above_threshold"]
        + 0.001 * diagnostics["flow_mwh_during_congested_hours"]
    )
    return diagnostics.sort_values(
        ["scenario", "bottleneck_rank_score"],
        ascending=[True, False],
    ).reset_index(drop=True)


def calculate_n1_security_proxy(
    hourly: pd.DataFrame,
    model_config: dict,
) -> pd.DataFrame:
    """
    Create an N-1 screening proxy from solved line flows.

    This does not rerun AC/DC contingency power flows. It ranks the corridors
    whose outage would expose the largest already-used transfer volume during
    high-utilisation hours.
    """
    bottlenecks = calculate_bottleneck_diagnostics(hourly, model_config)
    if bottlenecks.empty:
        return bottlenecks

    n1 = bottlenecks.rename(columns={"line": "outaged_line"}).copy()
    n1["n1_screening_risk_score"] = (
        n1["flow_mwh_during_congested_hours"]
        * (1.0 + n1["max_utilisation_pct"].clip(lower=0.0) / 100.0)
        + 50.0 * n1["hours_above_threshold"]
    )
    n1["screening_interpretation"] = np.where(
        n1["hours_above_threshold"] > 0,
        "High-priority outage screening corridor",
        "Low observed loading in solved base dispatch",
    )
    return n1.sort_values(
        ["scenario", "n1_screening_risk_score"],
        ascending=[True, False],
    ).reset_index(drop=True)
