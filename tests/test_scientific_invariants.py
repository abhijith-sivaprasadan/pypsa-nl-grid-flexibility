import pandas as pd
import pypsa
import pytest

from pypsa_nl_grid_flexibility.network import optimise_network


def corridor(limit):
    network = pypsa.Network()
    network.set_snapshots(pd.date_range("2026-01-01", periods=1, freq="h"))
    network.add("Bus", "source")
    network.add("Bus", "sink")
    network.add("Line", "link", bus0="source", bus1="sink", x=0.1, s_nom=limit)
    network.add("Generator", "renewable", bus="source", p_nom=100, marginal_cost=0)
    network.add("Generator", "backup", bus="sink", p_nom=100, marginal_cost=100)
    network.add("Load", "demand", bus="sink", p_set=100)
    return network


def test_more_corridor_capacity_cannot_raise_cost():
    narrow, wide = corridor(40), corridor(70)
    optimise_network(narrow)
    optimise_network(wide)
    assert narrow.objective == pytest.approx(6000)
    assert wide.objective == pytest.approx(3000)
    assert wide.objective <= narrow.objective
    assert 100 - narrow.generators_t.p["renewable"].iloc[0] == pytest.approx(60)


def test_lossless_battery_preserves_energy_over_two_periods():
    network = pypsa.Network()
    network.set_snapshots(pd.date_range("2026-01-01", periods=2, freq="h"))
    network.add("Bus", "bus")
    network.add("Generator", "supply", bus="bus", p_nom=100, marginal_cost=[1, 100])
    network.add("Load", "demand", bus="bus", p_set=[0, 50])
    network.add(
        "StorageUnit",
        "battery",
        bus="bus",
        p_nom=50,
        max_hours=1,
        efficiency_store=1,
        efficiency_dispatch=1,
        standing_loss=0,
        state_of_charge_initial=0,
        cyclic_state_of_charge=True,
    )
    optimise_network(network)
    assert network.generators_t.p["supply"].sum() == pytest.approx(50)
    assert network.storage_units_t.p["battery"].sum() == pytest.approx(0)
    assert network.objective == pytest.approx(50)


@pytest.mark.parametrize(
    "status,condition",
    [("ok", "infeasible"), ("ok", "time_limit"), ("warning", "optimal")],
)
def test_rejects_unverified_solver_termination(status, condition):
    class FailedNetwork:
        meta = {}

        def optimize(self, **kwargs):
            return status, condition

    network = FailedNetwork()
    with pytest.raises(RuntimeError):
        optimise_network(network)
    assert network.meta["termination_condition"] == condition
