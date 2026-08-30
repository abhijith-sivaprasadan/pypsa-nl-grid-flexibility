import pandas as pd

from pypsa_nl_grid_flexibility.reporting import build_key_findings_lines


def test_regeneration_preserves_consistency_check_boundary():
    summary = pd.DataFrame([{"scenario": "reference", "recommendation_rank": 1}])
    validation = pd.DataFrame([{"check": "balance", "passed": True}])
    lines = build_key_findings_lines(summary, validation=validation)
    assert "- Automated consistency checks passed: **1/1**." in lines
    assert not any("Validation checks passed" in line for line in lines)
