from pypsa_nl_grid_flexibility.config import load_model_config, load_scenarios


def test_config_loads():
    cfg = load_model_config()
    assert "regions" in cfg
    assert len(cfg["regions"]) >= 10


def test_scenarios_load():
    scenarios = load_scenarios()
    assert "base_2026_constrained_grid" in scenarios
    assert len(scenarios) >= 5
