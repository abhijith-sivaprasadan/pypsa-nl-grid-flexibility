from __future__ import annotations

import io

import matplotlib.pyplot as plt
import pandas as pd
from pypdf import PdfReader

import pypsa_nl_grid_flexibility.reporting as reporting


def test_pdf_report_bytes_include_pdf_and_attachment(tmp_path, monkeypatch) -> None:
    project_root = tmp_path
    outputs = project_root / "outputs"
    tables_dir = outputs / "tables"
    figures_dir = outputs / "figures"
    reports_dir = outputs / "reports"
    config_dir = project_root / "config"
    raw_dir = project_root / "data" / "raw"
    processed_dir = project_root / "data" / "processed"

    for path in [
        tables_dir,
        figures_dir,
        reports_dir,
        config_dir,
        raw_dir,
        processed_dir,
    ]:
        path.mkdir(parents=True, exist_ok=True)

    (project_root / "README.md").write_text("README", encoding="utf-8")
    (project_root / "pyproject.toml").write_text(
        "[project]\nname = 'demo'\n", encoding="utf-8"
    )
    (project_root / "requirements.txt").write_text("pandas\n", encoding="utf-8")
    (config_dir / "model_config.yaml").write_text("model: {}\n", encoding="utf-8")
    (config_dir / "scenarios.yaml").write_text("scenarios: {}\n", encoding="utf-8")
    (raw_dir / "README.md").write_text("raw\n", encoding="utf-8")
    (processed_dir / "sample.csv").write_text("a,b\n1,2\n", encoding="utf-8")

    summary = pd.DataFrame(
        [
            {
                "scenario": "high_wind_offshore_growth",
                "recommendation_rank": 1,
                "grid_value_score": 60.8,
                "renewable_dispatch_increase_vs_base_mwh": 201_560.84,
                "backup_reduction_vs_base_mwh": 201_560.84,
                "curtailment_rate_pct": 27.8,
                "total_congestion_cost_proxy_eur": 49_929_073.36,
                "renewable_curtailment_mwh": 655_232.62,
                "backup_dispatch_mwh": 525_569.19,
                "renewable_share_of_demand_pct": 76.4,
            },
            {
                "scenario": "base_2026_constrained_grid",
                "recommendation_rank": 2,
                "grid_value_score": 0.0,
                "renewable_dispatch_increase_vs_base_mwh": 0.0,
                "backup_reduction_vs_base_mwh": 0.0,
                "curtailment_rate_pct": 24.4,
                "total_congestion_cost_proxy_eur": 69_077_353.10,
                "renewable_curtailment_mwh": 484_638.39,
                "backup_dispatch_mwh": 727_130.03,
                "renewable_share_of_demand_pct": 67.3,
            },
        ]
    )
    bess_summary = pd.DataFrame(
        [
            {
                "scenario": "bess_case",
                "bess_region": "Groningen",
                "bess_power_mw": 400.0,
                "bess_duration_h": 4.0,
                "bess_energy_mwh": 1600.0,
                "sweep_grid_value_score": 20.5,
                "renewable_dispatch_gain_mwh": 12_500.0,
                "backup_reduction_mwh": 7_100.0,
                "congestion_cost_reduction_eur": 2_200_000.0,
            }
        ]
    )
    validation = pd.DataFrame(
        [
            {
                "check": "curtailment_balance",
                "passed": True,
                "value": "0.0",
                "tolerance": "0.001",
                "details": "OK",
            }
        ]
    )

    bottleneck = pd.DataFrame(
        [
            {
                "scenario": "base_2026_constrained_grid",
                "line": "A__B",
                "max_utilisation_pct": 100.0,
                "hours_above_threshold": 10,
                "congestion_severity_pct_hours": 50.0,
                "bottleneck_rank_score": 1.0,
            }
        ]
    )
    n1 = pd.DataFrame(
        [
            {
                "scenario": "base_2026_constrained_grid",
                "outaged_line": "A__B",
                "max_utilisation_pct": 100.0,
                "hours_above_threshold": 10,
                "n1_screening_risk_score": 2.0,
                "screening_interpretation": "High priority",
            }
        ]
    )
    business = pd.DataFrame(
        [
            {
                "bess_region": "Groningen",
                "bess_power_mw": 400.0,
                "bess_duration_h": 4.0,
                "bess_capex_eur": 1_000_000.0,
                "annualised_total_cost_eur_per_year": 100_000.0,
                "annualised_congestion_value_eur_per_year": 140_000.0,
                "net_annual_value_proxy_eur_per_year": 40_000.0,
                "benefit_cost_ratio_proxy": 1.4,
                "simple_payback_years_proxy": 5.0,
            }
        ]
    )

    summary.to_csv(tables_dir / "scenario_summary.csv", index=False)
    validation.to_csv(tables_dir / "validation_summary.csv", index=False)
    bottleneck.to_csv(tables_dir / "bottleneck_diagnostics.csv", index=False)
    n1.to_csv(tables_dir / "n1_security_proxy.csv", index=False)
    business.to_csv(tables_dir / "bess_business_case.csv", index=False)
    (reports_dir / "executive_grid_flexibility_report.md").write_text(
        "Executive", encoding="utf-8"
    )
    (reports_dir / "portfolio_summary.md").write_text("Portfolio", encoding="utf-8")
    (reports_dir / "scenario_report.md").write_text("Scenario", encoding="utf-8")
    (reports_dir / "bess_siting_report.md").write_text("BESS", encoding="utf-8")

    fig, ax = plt.subplots(figsize=(4, 3))
    ax.plot([0, 1], [0, 1])
    ax.set_title("Demo")
    fig.savefig(figures_dir / "demo.png", dpi=120)
    plt.close(fig)

    monkeypatch.setattr(reporting, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(reporting, "REPORT_DIR", reports_dir)
    monkeypatch.setattr(reporting, "FIGURE_DIR", figures_dir)
    monkeypatch.setattr(reporting, "TABLE_DIR", tables_dir)

    pdf_bytes = reporting.build_pdf_report_bytes(summary, bess_summary, validation)

    assert pdf_bytes.startswith(b"%PDF")

    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1
    assert "pypsa_nl_grid_flexibility_report_bundle.zip" in reader.attachments
