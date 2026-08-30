import pandas as pd
import pypsa
import pytest

from pypsa_nl_grid_flexibility.network import optimise_network


def test_constrained_two_bus_dispatch_has_analytical_solution() -> None:
    """A 40 MW line forces 60 MW of local backup for a 100 MW load."""
    network = pypsa.Network()
    network.set_snapshots(pd.date_range("2026-01-01", periods=1, freq="h"))
    network.add("Bus", "renewable_bus")
    network.add("Bus", "load_bus")
    network.add(
        "Line",
        "constrained_line",
        bus0="renewable_bus",
        bus1="load_bus",
        x=0.1,
        r=0.01,
        s_nom=40.0,
    )
    network.add(
        "Generator",
        "renewable",
        bus="renewable_bus",
        p_nom=100.0,
        marginal_cost=0.0,
    )
    network.add(
        "Generator",
        "backup",
        bus="load_bus",
        p_nom=100.0,
        marginal_cost=100.0,
    )
    network.add("Load", "demand", bus="load_bus", p_set=100.0)

    status, condition = optimise_network(network)

    assert status == "ok"
    assert condition == "optimal"
    assert network.lines_t.p0.iloc[0]["constrained_line"] == pytest.approx(40.0)
    assert network.generators_t.p.iloc[0]["renewable"] == pytest.approx(40.0)
    assert network.generators_t.p.iloc[0]["backup"] == pytest.approx(60.0)
    assert network.objective == pytest.approx(6000.0)
