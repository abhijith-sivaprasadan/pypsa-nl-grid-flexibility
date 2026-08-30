from __future__ import annotations

import pandas as pd
import pypsa

from pypsa_nl_grid_flexibility.profiles import congestion_window_mask


def line_name(bus0: str, bus1: str) -> str:
    """Create a stable line name from two buses."""
    return f"{bus0}__{bus1}"


def add_carriers(network: pypsa.Network) -> None:
    """Add carriers used in the model."""
    carriers = [
        "AC",
        "solar",
        "wind",
        "offshore_wind",
        "backup",
        "battery",
        "flexible_load",
    ]

    for carrier in carriers:
        if carrier not in network.carriers.index:
            network.add("Carrier", carrier)


def add_buses(network: pypsa.Network, model_config: dict) -> None:
    """Add regional grid buses."""
    for region in model_config["regions"]:
        network.add(
            "Bus",
            region,
            carrier="AC",
        )


def add_lines(network: pypsa.Network, model_config: dict, scenario: dict) -> None:
    """Add simplified inter-regional transmission lines."""
    global_multiplier = float(scenario.get("line_capacity_multiplier", 1.0))
    line_reinforcements = scenario.get("line_reinforcements", {}) or {}

    for bus0, bus1, capacity_mw in model_config["network_lines"]:
        name = line_name(bus0, bus1)
        reinforcement_multiplier = float(line_reinforcements.get(name, 1.0))

        network.add(
            "Line",
            name,
            bus0=bus0,
            bus1=bus1,
            x=0.08,
            r=0.01,
            s_nom=float(capacity_mw) * global_multiplier * reinforcement_multiplier,
        )


def add_loads(
    network: pypsa.Network,
    model_config: dict,
    profiles: pd.DataFrame,
) -> None:
    """Add hourly regional demand."""
    for region, base_mw in model_config["demand_base_mw"].items():
        network.add(
            "Load",
            f"load_{region}",
            bus=region,
            p_set=float(base_mw) * profiles["demand_pu"],
        )


def add_renewables(
    network: pypsa.Network,
    model_config: dict,
    scenario: dict,
    profiles: pd.DataFrame,
) -> None:
    """Add solar, wind and offshore wind generation."""
    multipliers = {
        "solar": float(scenario.get("solar_multiplier", 1.0)),
        "wind": float(scenario.get("wind_multiplier", 1.0)),
        "offshore_wind": float(scenario.get("offshore_multiplier", 1.0)),
    }

    profile_columns = {
        "solar": "solar_pu",
        "wind": "wind_pu",
        "offshore_wind": "offshore_wind_pu",
    }

    for carrier, region_capacities in model_config["renewables_mw"].items():
        for region, capacity_mw in region_capacities.items():
            if region not in network.buses.index:
                raise ValueError(
                    f"Renewable generator region '{region}' is not in the bus list."
                )

            network.add(
                "Generator",
                f"{carrier}_{region}",
                bus=region,
                carrier=carrier,
                p_nom=float(capacity_mw) * multipliers[carrier],
                p_max_pu=profiles[profile_columns[carrier]],
                marginal_cost=0.0,
            )


def add_backup_generation(network: pypsa.Network, model_config: dict) -> None:
    """Add dispatchable backup generation at each bus."""
    backup_cost = float(model_config["model"]["backup_marginal_cost_eur_per_mwh"])

    for region in model_config["regions"]:
        network.add(
            "Generator",
            f"backup_{region}",
            bus=region,
            carrier="backup",
            p_nom=9000.0,
            marginal_cost=backup_cost,
        )


def add_bess(
    network: pypsa.Network,
    region: str,
    power_mw: float,
    duration_h: float,
    name_prefix: str = "BESS",
) -> None:
    """Add a battery energy storage system."""
    if region not in network.buses.index:
        raise ValueError(f"BESS region '{region}' is not in the bus list.")

    network.add(
        "StorageUnit",
        f"{name_prefix}_{region}_{int(power_mw)}MW_{int(duration_h)}h",
        bus=region,
        carrier="battery",
        p_nom=float(power_mw),
        max_hours=float(duration_h),
        efficiency_store=0.94,
        efficiency_dispatch=0.94,
        cyclic_state_of_charge=True,
        marginal_cost=1.0,
    )


def add_flexible_connection(
    network: pypsa.Network,
    model_config: dict,
    scenario: dict,
    profiles: pd.DataFrame,
) -> None:
    """
    Add an explicit flexible connection load.

    This represents a contracted flexible connection with lower available
    import capacity during congested hours and full capacity during
    uncongested hours.
    """
    if not scenario.get("flexible_connection", False):
        return

    flex_config = model_config["flexible_connection"]

    region = flex_config["target_region"]
    flexible_load_mw = float(flex_config["flexible_load_mw"])

    if region not in network.buses.index:
        raise ValueError(
            f"Flexible connection region '{region}' is not in the bus list."
        )

    congested_hours = congestion_window_mask(
        profiles,
        solar_threshold=0.65,
        demand_quantile=0.50,
    )

    capacity_factor = pd.Series(
        float(flex_config["uncongested_hour_capacity_factor"]),
        index=profiles.index,
    )

    capacity_factor.loc[congested_hours] = float(
        flex_config["congested_hour_capacity_factor"]
    )

    network.add(
        "Load",
        f"flex_connection_{region}",
        bus=region,
        carrier="flexible_load",
        p_set=flexible_load_mw * capacity_factor,
    )


def build_network(
    model_config: dict,
    scenario_name: str,
    scenario: dict,
    profiles: pd.DataFrame,
) -> pypsa.Network:
    """Build a PyPSA network for one scenario."""
    network = pypsa.Network()
    network.set_snapshots(profiles.index)

    add_carriers(network)
    add_buses(network, model_config)
    add_lines(network, model_config, scenario)
    add_loads(network, model_config, profiles)
    add_renewables(network, model_config, scenario, profiles)
    add_backup_generation(network, model_config)

    if scenario.get("add_bess", False):
        add_bess(
            network,
            region=scenario["bess_region"],
            power_mw=float(scenario["bess_power_mw"]),
            duration_h=float(scenario["bess_duration_h"]),
        )

    add_flexible_connection(network, model_config, scenario, profiles)

    network.meta = {
        "scenario_name": scenario_name,
        "scenario_description": scenario.get("description", ""),
    }

    return network


def optimise_network(network: pypsa.Network) -> tuple[str, str]:
    """Optimise the PyPSA network using HiGHS."""
    status, condition = network.optimize(
        solver_name="highs",
        solver_options={
            "log_to_console": False,
            "output_flag": False,
        },
    )

    network.meta = {
        **getattr(network, "meta", {}),
        "solve_status": status,
        "termination_condition": condition,
    }

    if status != "ok" or condition != "optimal":
        raise RuntimeError(
            f"PyPSA optimisation failed. Status: {status}, condition: {condition}"
        )
    return status, condition


# American spelling alias, in case another file imports this name.
def optimize_network(network: pypsa.Network) -> tuple[str, str]:
    return optimise_network(network)


# Backward-compatible alias for older files that import solve_network.
def solve_network(network: pypsa.Network) -> tuple[str, str]:
    return optimise_network(network)
