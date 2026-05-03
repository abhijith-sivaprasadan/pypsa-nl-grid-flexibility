from __future__ import annotations

import logging
import warnings

warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    module=r"google\.api_core\._python_version_support",
)

import pandas as pd

from pypsa_nl_grid_flexibility.config import (
    TABLE_DIR,
    ensure_output_dirs,
    load_model_config,
    load_scenarios,
)
from pypsa_nl_grid_flexibility.profiles import generate_profiles
from pypsa_nl_grid_flexibility.network import build_network, optimise_network
from pypsa_nl_grid_flexibility.analysis import (
    add_baseline_comparison,
    calculate_bottleneck_diagnostics,
    calculate_hourly_results,
    calculate_n1_security_proxy,
    calculate_summary,
    validate_scenario_summary,
)
from pypsa_nl_grid_flexibility.bess_siting import (
    add_bess_business_case_metrics,
    run_bess_siting_and_sizing_sweep,
)
from pypsa_nl_grid_flexibility.plotting import plot_bess_sweep, plot_summary
from pypsa_nl_grid_flexibility.reporting import (
    write_pdf_report,
    update_readme_latest_results,
    write_executive_report,
    write_report_bundle,
    write_portfolio_summary,
)


def configure_logging() -> None:
    """Keep routine runs focused on project outputs instead of solver internals."""
    logging.basicConfig(level=logging.WARNING)
    for logger_name in ("linopy", "pypsa", "pypsa.optimization"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def main() -> None:
    configure_logging()
    ensure_output_dirs()

    model_config = load_model_config()
    scenarios = load_scenarios()
    profiles = generate_profiles(model_config)

    summaries = []
    hourly_outputs = []

    for scenario_name, scenario in scenarios.items():
        if scenario_name == "high_renewables_for_bess_sweep":
            continue

        print(f"\n=== Running scenario: {scenario_name} ===")

        network = build_network(
            model_config=model_config,
            scenario_name=scenario_name,
            scenario=scenario,
            profiles=profiles,
        )

        optimise_network(network)

        summaries.append(
            calculate_summary(
                network,
                scenario_name,
                model_config,
            )
        )

        hourly_outputs.append(
            calculate_hourly_results(
                network,
                scenario_name,
            )
        )

    summary = add_baseline_comparison(pd.DataFrame(summaries))
    validation = validate_scenario_summary(summary)

    if hourly_outputs:
        hourly = pd.concat(hourly_outputs, axis=0)
    else:
        hourly = pd.DataFrame()

    summary_path = TABLE_DIR / "scenario_summary.csv"
    validation_path = TABLE_DIR / "validation_summary.csv"
    hourly_path = TABLE_DIR / "hourly_dispatch.csv"

    summary.to_csv(summary_path, index=False)
    validation.to_csv(validation_path, index=False)
    hourly.to_csv(hourly_path, index=True)

    bottlenecks = calculate_bottleneck_diagnostics(hourly, model_config)
    n1_security = calculate_n1_security_proxy(hourly, model_config)

    bottleneck_path = TABLE_DIR / "bottleneck_diagnostics.csv"
    n1_path = TABLE_DIR / "n1_security_proxy.csv"

    bottlenecks.to_csv(bottleneck_path, index=False)
    n1_security.to_csv(n1_path, index=False)

    print(f"\nScenario summary written to: {summary_path}")
    print(f"Validation summary written to: {validation_path}")
    print(f"Hourly dispatch written to: {hourly_path}")
    print(f"Bottleneck diagnostics written to: {bottleneck_path}")
    print(f"N-1 screening proxy written to: {n1_path}")

    print("\n=== Running BESS siting and sizing sweep ===")
    bess_summary = run_bess_siting_and_sizing_sweep(
        model_config,
        scenarios,
        profiles,
    )
    bess_business_case = add_bess_business_case_metrics(bess_summary, model_config)
    bess_business_case.to_csv(TABLE_DIR / "bess_business_case.csv", index=False)

    plot_summary(summary)
    plot_bess_sweep(bess_summary)
    write_executive_report(summary, bess_summary, validation)
    write_portfolio_summary(summary, bess_summary, validation)
    update_readme_latest_results(summary, bess_summary, validation)
    bundle_path = write_report_bundle()
    pdf_path = write_pdf_report(summary, bess_summary, validation)

    print("\nScenario summary:")
    print(summary.round(2).to_string(index=False))
    print("\nValidation summary:")
    print(validation.to_string(index=False))
    print(f"\nPDF report written to: {pdf_path}")
    print(f"\nReport bundle written to: {bundle_path}")
    print(f"\nOutputs written to {TABLE_DIR.parent}")


if __name__ == "__main__":
    main()
