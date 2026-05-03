from __future__ import annotations

from itertools import product

import pandas as pd

from pypsa_nl_grid_flexibility.analysis import calculate_summary
from pypsa_nl_grid_flexibility.config import TABLE_DIR
from pypsa_nl_grid_flexibility.network import build_network, solve_network


def _get_bess_config(model_config: dict) -> dict:
    """Return BESS sweep configuration with safe defaults."""
    return model_config.get(
        "bess_siting",
        {
            "candidate_regions": ["Noord-Holland", "Flevoland", "Noord-Brabant"],
            "power_mw": [50, 100, 200, 400],
            "duration_h": [1, 2, 4],
            "evaluation_scenario": "high_renewables_for_bess_sweep",
            "max_cases": None,
        },
    )


def _total_congestion_cost(summary: dict) -> float:
    """Return congestion-cost proxy if present, otherwise fall back safely."""
    return float(summary.get("total_congestion_cost_proxy_eur", 0.0))


def _build_bess_case(
    base_scenario: dict,
    region: str,
    power_mw: float,
    duration_h: float,
) -> dict:
    """
    Build a scenario dictionary in the exact format expected by network.py.

    This is the important fix: the sweep must set add_bess=True and pass
    bess_region, bess_power_mw and bess_duration_h directly at scenario level.
    """
    scenario = dict(base_scenario)

    scenario.update(
        {
            "add_bess": True,
            "bess_region": region,
            "bess_power_mw": float(power_mw),
            "bess_duration_h": float(duration_h),
            "flexible_connection": False,
        }
    )

    return scenario


def _build_reference_case(base_scenario: dict) -> dict:
    """Build the no-BESS reference case for the BESS sweep."""
    scenario = dict(base_scenario)

    scenario.update(
        {
            "add_bess": False,
            "bess_region": None,
            "bess_power_mw": 0.0,
            "bess_duration_h": 0.0,
            "flexible_connection": False,
        }
    )

    return scenario


def _calculate_sweep_metrics(
    case_summary: dict,
    reference_summary: dict,
    region: str,
    power_mw: float,
    duration_h: float,
) -> dict:
    """Add BESS-specific comparison metrics against the no-BESS reference."""
    energy_mwh = float(power_mw) * float(duration_h)

    renewable_dispatch_gain = float(case_summary["renewable_dispatch_mwh"]) - float(
        reference_summary["renewable_dispatch_mwh"]
    )

    backup_reduction = float(reference_summary["backup_dispatch_mwh"]) - float(
        case_summary["backup_dispatch_mwh"]
    )

    emissions_reduction = float(reference_summary["emissions_proxy_tco2"]) - float(
        case_summary["emissions_proxy_tco2"]
    )

    line_overload_reduction = int(reference_summary["line_hours_above_90pct"]) - int(
        case_summary["line_hours_above_90pct"]
    )

    congestion_cost_reduction = _total_congestion_cost(
        reference_summary
    ) - _total_congestion_cost(case_summary)

    # Balanced score for BESS ranking.
    # Positive is better.
    sweep_grid_value_score = (
        0.35 * renewable_dispatch_gain / 1000.0
        + 0.30 * backup_reduction / 1000.0
        + 0.20 * congestion_cost_reduction / 1_000_000.0
        + 0.15 * line_overload_reduction
    )

    metrics = dict(case_summary)

    metrics.update(
        {
            "bess_region": region,
            "bess_power_mw": float(power_mw),
            "bess_duration_h": float(duration_h),
            "bess_energy_mwh": energy_mwh,
            "renewable_dispatch_gain_mwh": renewable_dispatch_gain,
            "backup_reduction_mwh": backup_reduction,
            "emissions_reduction_tco2": emissions_reduction,
            "line_overload_reduction_hours": line_overload_reduction,
            "congestion_cost_reduction_eur": congestion_cost_reduction,
            "sweep_grid_value_score": sweep_grid_value_score,
            "congestion_value_per_mwh_bess_eur": (
                congestion_cost_reduction / energy_mwh if energy_mwh else 0.0
            ),
            "backup_reduction_per_mw_bess": (
                backup_reduction / float(power_mw) if power_mw else 0.0
            ),
            "renewable_gain_per_mw_bess": (
                renewable_dispatch_gain / float(power_mw) if power_mw else 0.0
            ),
        }
    )

    return metrics


def run_bess_siting_and_sizing_sweep(
    model_config: dict,
    scenarios: dict,
    profiles: dict,
    show_progress: bool = True,
) -> pd.DataFrame:
    """
    Run a BESS siting and sizing sweep.

    The sweep compares candidate BESS locations, power ratings and durations
    against a high-renewables no-BESS reference case.
    """
    bess_config = _get_bess_config(model_config)

    base_name = bess_config.get(
        "evaluation_scenario",
        "high_renewables_for_bess_sweep",
    )

    if base_name not in scenarios:
        available = ", ".join(scenarios.keys())
        raise KeyError(
            f"BESS sweep evaluation scenario '{base_name}' not found. "
            f"Available scenarios: {available}"
        )

    base_scenario = scenarios[base_name]

    reference_scenario = _build_reference_case(base_scenario)
    if show_progress:
        print("BESS sweep reference case: no BESS", flush=True)
    reference_network = build_network(
        model_config,
        "bess_sweep_reference_no_bess",
        reference_scenario,
        profiles,
    )
    solve_network(reference_network)

    reference_summary = calculate_summary(
        reference_network,
        "bess_sweep_reference_no_bess",
        model_config,
    )

    rows: list[dict] = [reference_summary]

    candidate_regions = bess_config.get("candidate_regions", [])
    power_values = bess_config.get("power_mw", [50, 100, 200, 400])
    duration_values = bess_config.get("duration_h", [1, 2, 4])
    max_cases = bess_config.get("max_cases", None)

    cases = list(product(candidate_regions, power_values, duration_values))

    if max_cases is not None:
        cases = cases[: int(max_cases)]

    total_cases = len(cases)
    if show_progress:
        print(f"BESS sweep cases: {total_cases}", flush=True)

    for case_index, (region, power_mw, duration_h) in enumerate(cases, start=1):
        if show_progress:
            print(
                "BESS sweep "
                f"{case_index}/{total_cases}: {region}, "
                f"{float(power_mw):.0f} MW, {float(duration_h):.0f} h",
                flush=True,
            )

        scenario = _build_bess_case(
            base_scenario=base_scenario,
            region=region,
            power_mw=float(power_mw),
            duration_h=float(duration_h),
        )

        scenario_name = (
            f"bess_sweep__{region}__{float(power_mw):.0f}MW__"
            f"{float(duration_h):.0f}h"
        )

        network = build_network(
            model_config,
            scenario_name,
            scenario,
            profiles,
        )
        solve_network(network)

        case_summary = calculate_summary(network, scenario_name, model_config)

        row = _calculate_sweep_metrics(
            case_summary=case_summary,
            reference_summary=reference_summary,
            region=region,
            power_mw=float(power_mw),
            duration_h=float(duration_h),
        )

        rows.append(row)

    sweep = pd.DataFrame(rows)

    # Keep reference row, but rank only real BESS cases.
    is_reference = sweep["scenario"] == "bess_sweep_reference_no_bess"

    sweep.loc[is_reference, "sweep_grid_value_score"] = 0.0
    sweep.loc[is_reference, "sweep_rank"] = 0

    bess_only = sweep.loc[~is_reference].copy()

    if not bess_only.empty:
        bess_only = bess_only.sort_values(
            [
                "sweep_grid_value_score",
                "congestion_cost_reduction_eur",
                "renewable_dispatch_gain_mwh",
                "backup_reduction_mwh",
            ],
            ascending=[False, False, False, False],
        )

        bess_only["sweep_rank"] = range(1, len(bess_only) + 1)

        sweep = pd.concat(
            [sweep.loc[is_reference], bess_only],
            ignore_index=True,
        )

    TABLE_DIR.mkdir(parents=True, exist_ok=True)

    sweep.to_csv(TABLE_DIR / "bess_siting_sizing_sweep.csv", index=False)

    top10 = sweep.loc[~is_reference].head(10).copy()
    top10.to_csv(TABLE_DIR / "bess_top10_siting_sizing_options.csv", index=False)

    if show_progress:
        print("BESS sweep complete", flush=True)

    return sweep


def add_bess_business_case_metrics(
    bess_summary: pd.DataFrame,
    model_config: dict,
) -> pd.DataFrame:
    """Add simple annualised BESS business-case proxy metrics."""
    if bess_summary.empty:
        return bess_summary.copy()

    business_config = model_config.get("bess_business_case", {})
    power_capex = float(business_config.get("power_capex_eur_per_kw", 155))
    energy_capex = float(business_config.get("energy_capex_eur_per_kwh", 210))
    fixed_om_pct = float(business_config.get("fixed_om_pct_of_capex_per_year", 0.025))
    lifetime = float(business_config.get("economic_lifetime_years", 15))
    discount_rate = float(business_config.get("discount_rate_pct", 7.0)) / 100.0
    snapshots = float(model_config["model"].get("snapshots", 8760))
    annualisation_factor = 8760.0 / snapshots if snapshots else 1.0

    if discount_rate:
        capital_recovery_factor = (
            discount_rate * (1 + discount_rate) ** lifetime
        ) / ((1 + discount_rate) ** lifetime - 1)
    else:
        capital_recovery_factor = 1.0 / lifetime

    data = bess_summary.copy()
    if "scenario" in data.columns:
        data = data[data["scenario"] != "bess_sweep_reference_no_bess"].copy()

    if data.empty:
        return data

    data["bess_capex_eur"] = (
        data["bess_power_mw"].astype(float) * 1000.0 * power_capex
        + data["bess_energy_mwh"].astype(float) * 1000.0 * energy_capex
    )
    data["annualised_capex_eur_per_year"] = (
        data["bess_capex_eur"] * capital_recovery_factor
    )
    data["fixed_om_eur_per_year"] = data["bess_capex_eur"] * fixed_om_pct
    data["annualised_total_cost_eur_per_year"] = (
        data["annualised_capex_eur_per_year"] + data["fixed_om_eur_per_year"]
    )
    data["annualised_congestion_value_eur_per_year"] = (
        data["congestion_cost_reduction_eur"] * annualisation_factor
    )
    data["net_annual_value_proxy_eur_per_year"] = (
        data["annualised_congestion_value_eur_per_year"]
        - data["annualised_total_cost_eur_per_year"]
    )
    data["benefit_cost_ratio_proxy"] = (
        data["annualised_congestion_value_eur_per_year"]
        / data["annualised_total_cost_eur_per_year"].replace(0, pd.NA)
    ).fillna(0.0)
    data["simple_payback_years_proxy"] = (
        data["bess_capex_eur"]
        / data["annualised_congestion_value_eur_per_year"].where(
            data["annualised_congestion_value_eur_per_year"] > 0
        )
    )

    return data.sort_values(
        ["net_annual_value_proxy_eur_per_year", "benefit_cost_ratio_proxy"],
        ascending=[False, False],
    ).reset_index(drop=True)
