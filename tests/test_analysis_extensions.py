from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from pypsa_nl_grid_flexibility.analysis import (
    calculate_bottleneck_diagnostics,
    calculate_n1_security_proxy,
    calculate_summary,
    validate_scenario_summary,
)
from pypsa_nl_grid_flexibility.bess_siting import add_bess_business_case_metrics


def test_bottleneck_and_n1_proxy_outputs_are_ranked() -> None:
    hourly = pd.DataFrame(
        {
            "scenario": ["base", "base", "base"],
            "A__B_flow_mw": [80.0, 95.0, 110.0],
            "A__B_utilisation_pct": [80.0, 95.0, 110.0],
        }
    )
    config = {"model": {"congestion_utilisation_threshold_pct": 90}}

    bottlenecks = calculate_bottleneck_diagnostics(hourly, config)
    n1 = calculate_n1_security_proxy(hourly, config)

    assert bottlenecks.loc[0, "line"] == "A__B"
    assert bottlenecks.loc[0, "hours_above_threshold"] == 2
    assert n1.loc[0, "outaged_line"] == "A__B"
    assert n1.loc[0, "n1_screening_risk_score"] > 0


def test_bess_business_case_metrics_are_non_empty() -> None:
    sweep = pd.DataFrame(
        {
            "scenario": ["bess_case"],
            "bess_region": ["Groningen"],
            "bess_power_mw": [100.0],
            "bess_duration_h": [2.0],
            "bess_energy_mwh": [200.0],
            "congestion_cost_reduction_eur": [1_000_000.0],
        }
    )
    config = {
        "model": {"snapshots": 168},
        "bess_business_case": {
            "power_capex_eur_per_kw": 100,
            "energy_capex_eur_per_kwh": 200,
            "fixed_om_pct_of_capex_per_year": 0.02,
            "economic_lifetime_years": 10,
            "discount_rate_pct": 5,
        },
    }

    business = add_bess_business_case_metrics(sweep, config)

    assert business.loc[0, "bess_capex_eur"] == 50_000_000.0
    assert business.loc[0, "annualised_congestion_value_eur_per_year"] > 0
    assert "benefit_cost_ratio_proxy" in business.columns


def test_summary_does_not_double_count_total_curtailment() -> None:
    snapshots = pd.RangeIndex(2)
    generators = pd.DataFrame(
        {
            "carrier": ["solar", "backup"],
            "p_nom": [10.0, 100.0],
        },
        index=["solar_A", "backup_A"],
    )
    generator_dispatch = pd.DataFrame(
        {
            "solar_A": [7.0, 8.0],
            "backup_A": [3.0, 2.0],
        },
        index=snapshots,
    )
    generator_availability = pd.DataFrame({"solar_A": [1.0, 1.0]}, index=snapshots)
    load = pd.DataFrame({"load_A": [10.0, 10.0]}, index=snapshots)

    network = SimpleNamespace(
        snapshots=snapshots,
        generators=generators,
        generators_t=SimpleNamespace(
            p=generator_dispatch, p_max_pu=generator_availability
        ),
        loads=pd.DataFrame(index=["load_A"]),
        loads_t=SimpleNamespace(p_set=load),
        lines=pd.DataFrame({"s_nom": []}),
        lines_t=SimpleNamespace(p0=pd.DataFrame(index=snapshots)),
        storage_units=pd.DataFrame(index=[]),
        storage_units_t=SimpleNamespace(),
        objective=200.0,
    )
    config = {
        "model": {
            "backup_emission_tco2_per_mwh": 0.42,
            "renewable_curtailment_value_eur_per_mwh": 65,
            "backup_marginal_cost_eur_per_mwh": 95,
        }
    }

    summary = calculate_summary(network, "case", config)

    assert summary["renewable_available_mwh"] == 20.0
    assert summary["renewable_dispatch_mwh"] == 15.0
    assert summary["renewable_curtailment_mwh"] == 5.0
    assert summary["curtailment_rate_pct"] == 25.0
    assert summary["curtailment_cost_proxy_eur"] == 325.0


def test_validate_scenario_summary_catches_kpi_consistency() -> None:
    summary = pd.DataFrame(
        {
            "scenario": ["base"],
            "solve_status": ["ok"],
            "termination_condition": ["optimal"],
            "renewable_available_mwh": [20.0],
            "renewable_dispatch_mwh": [15.0],
            "renewable_curtailment_mwh": [5.0],
            "curtailment_rate_pct": [25.0],
            "renewable_share_of_demand_pct": [75.0],
            "bess_equivalent_cycles": [0.0],
            "objective_cost_eur": [100.0],
            "recommendation_rank": [1],
        }
    )

    validation = validate_scenario_summary(summary)

    assert validation["passed"].all()
    assert "curtailment_balance" in validation["check"].tolist()
