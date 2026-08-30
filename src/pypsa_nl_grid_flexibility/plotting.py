from __future__ import annotations

import matplotlib
import pandas as pd

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from pypsa_nl_grid_flexibility.config import FIGURE_DIR


def save_bar(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    ylabel: str,
    filename: str,
    top_n: int | None = None,
) -> None:
    """Save a simple bar chart."""
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    data = df.copy()

    if top_n is not None:
        data = data.head(top_n)

    if data.empty or x not in data.columns or y not in data.columns:
        return

    plt.figure(figsize=(11, 5))
    plt.bar(data[x].astype(str), data[y])
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / filename, dpi=180)
    plt.close()


def plot_summary(summary: pd.DataFrame) -> None:
    """Create scenario-level summary plots."""
    if summary.empty:
        return

    plot_data = summary.copy()

    if "scenario" in plot_data.columns:
        plot_data["scenario_label"] = (
            plot_data["scenario"]
            .astype(str)
            .str.replace("_", " ", regex=False)
            .str.title()
        )
    else:
        plot_data["scenario_label"] = plot_data.index.astype(str)

    if "grid_value_score" in plot_data.columns:
        save_bar(
            plot_data,
            "scenario_label",
            "grid_value_score",
            "Scenario decision-support score",
            "Grid value score [-]",
            "grid_value_score_by_scenario.png",
        )

    if "renewable_share_of_demand_pct" in plot_data.columns:
        save_bar(
            plot_data,
            "scenario_label",
            "renewable_share_of_demand_pct",
            "Renewable share of demand by scenario",
            "Renewable share [%]",
            "renewable_share_by_scenario.png",
        )

    if "total_congestion_cost_proxy_eur" in plot_data.columns:
        save_bar(
            plot_data,
            "scenario_label",
            "total_congestion_cost_proxy_eur",
            "Congestion cost proxy by scenario",
            "Congestion cost proxy [EUR]",
            "congestion_cost_proxy_by_scenario.png",
        )

    if "line_hours_above_90pct" in plot_data.columns:
        save_bar(
            plot_data,
            "scenario_label",
            "line_hours_above_90pct",
            "Line-hours above 90% utilisation",
            "Line-hours",
            "line_overload_hours_by_scenario.png",
        )


def plot_bess_sweep(summary: pd.DataFrame) -> None:
    """Create BESS siting and sizing sweep plots."""
    if summary.empty:
        return

    data = summary.copy()

    if "scenario" in data.columns:
        data = data[data["scenario"] != "bess_sweep_reference_no_bess"].copy()

    if data.empty:
        return

    required_option_cols = {"bess_region", "bess_power_mw", "bess_duration_h"}
    if required_option_cols.issubset(data.columns):
        data["option"] = (
            data["bess_region"].astype(str)
            + " — "
            + data["bess_power_mw"].astype(float).astype(int).astype(str)
            + " MW / "
            + data["bess_duration_h"].astype(float).astype(int).astype(str)
            + " h"
        )
    else:
        data["option"] = data.get("scenario", data.index.astype(str)).astype(str)

    if "sweep_grid_value_score" in data.columns:
        data = data.sort_values("sweep_grid_value_score", ascending=False)

        save_bar(
            data,
            "option",
            "sweep_grid_value_score",
            "Top BESS siting and sizing options",
            "BESS grid-value score [-]",
            "bess_siting_sizing_score.png",
            top_n=15,
        )

    if "congestion_value_per_mwh_bess_eur" in data.columns:
        data_for_value = data.sort_values(
            "congestion_value_per_mwh_bess_eur",
            ascending=False,
        )

        save_bar(
            data_for_value,
            "option",
            "congestion_value_per_mwh_bess_eur",
            "Congestion value proxy per MWh of BESS",
            "EUR/MWh BESS",
            "bess_congestion_value_per_mwh.png",
            top_n=15,
        )


# Backward-compatible aliases for older code versions.
def plot_scenario_summary(summary: pd.DataFrame) -> None:
    plot_summary(summary)


def plot_bess_results(summary: pd.DataFrame) -> None:
    plot_bess_sweep(summary)
