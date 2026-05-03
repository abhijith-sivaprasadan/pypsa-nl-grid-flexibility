



# PyPSA-NL Grid Flexibility Modelling Platform

Netherlands-inspired power-system modelling project for grid congestion, renewable curtailment, BESS siting, flexible connection contracts and reinforcement screening.

The repository is built as a transparent portfolio-grade workflow for Grid Flow Modeller, Energy Systems Modeller and flexibility analytics roles. It uses PyPSA to solve simplified constrained-grid dispatch scenarios, then turns the solved network results into decision-support KPIs, validation checks, plots and reports.

This is not a TSO-grade Dutch grid model. The demand and renewable-capacity scale are calibrated from public Dutch statistics where appropriate, while topology, line ratings and hourly profile shapes remain documented modelling assumptions.

## What It Demonstrates

- PyPSA-based grid-flow optimisation across multiple scenarios
- Renewable dispatch, curtailment and backup-generation analysis
- BESS siting and sizing sweep across candidate regions, power ratings and durations
- Flexible connection contract logic under recurring congestion windows
- Grid-reinforcement scenario screening
- Bottleneck and N-1 screening proxy from solved line flows
- Congestion-cost proxy combining curtailment value, backup cost and line-hour penalties
- Automated KPI validation before reporting
- Streamlit dashboard, CSV outputs, figures and executive markdown reports

## Model Scope

The model represents a simplified regional Dutch grid with provincial buses, inter-regional corridors, solar, onshore wind, offshore wind, backup generation, optional BESS and optional flexible load. It solves hourly linear dispatch over the configured snapshot horizon.

Current calibration assumptions are documented in `config/model_config.yaml`:

- National electricity demand scale: approximately 116 TWh per year, based on public Dutch statistics.
- Renewable capacity totals: CBS StatLine public figures for solar PV, onshore wind and offshore wind.
- Provincial renewable distribution: public provincial installed-capacity shares, scaled to selected national totals.
- Grid topology and corridor ratings: simplified portfolio assumptions for congestion-screening demonstration.

## Scenario Workflow

Run the full workflow:

```bash
python -m pypsa_nl_grid_flexibility.run_all
```

The workflow:

1. Builds the configured scenario networks.
2. Solves each PyPSA optimisation with HiGHS.
3. Exports hourly dispatch and scenario KPI tables.
4. Validates KPI consistency and solve status.
5. Runs the BESS siting and sizing sweep.
6. Generates plots and markdown reports.

The solver is configured for quiet routine runs. If a scenario fails to solve, the workflow raises an error rather than producing misleading outputs.

## Dashboard

```bash
streamlit run src/pypsa_nl_grid_flexibility/dashboard_streamlit.py
```

The dashboard reads the generated CSV outputs and supports scenario comparison, congestion review, BESS option ranking and report export.

## Outputs

Main generated files:

```text
outputs/tables/scenario_summary.csv
outputs/tables/validation_summary.csv
outputs/tables/hourly_dispatch.csv
outputs/tables/bottleneck_diagnostics.csv
outputs/tables/n1_security_proxy.csv
outputs/tables/bess_siting_sizing_sweep.csv
outputs/tables/bess_top10_siting_sizing_options.csv
outputs/tables/bess_business_case.csv
outputs/figures/*.png
outputs/reports/executive_grid_flexibility_report.md
```

`validation_summary.csv` is intended as a quick audit trail. It checks:

- all scenarios solved with PyPSA status `ok` and optimal termination,
- renewable curtailment equals renewable availability minus renewable dispatch,
- renewable share and curtailment rates are within physical percentage bounds,
- BESS equivalent cycles are finite and non-negative,
- objective costs are finite and non-negative,
- recommendation ranks are complete.

## Interpreting The Ranking

The recommendation score is a decision-support metric, not a market price. It combines:

- renewable dispatch increase versus base,
- backup dispatch reduction,
- line-overload relief,
- curtailment-rate change,
- objective-cost reduction,
- congestion-cost proxy reduction.

High-renewable scenarios can increase absolute curtailment because renewable availability grows faster than grid capacity. For that reason, absolute curtailment alone is not used as the ranking criterion. The model reports both absolute curtailment and curtailment rate so the tradeoff remains visible.

<!-- LATEST_RESULTS_START -->
## Latest Generated Results

This section is generated from the latest files in `outputs/tables/` when `python -m pypsa_nl_grid_flexibility.run_all` is executed.

- Top-ranked scenario: **High Wind Offshore Growth** with grid-value score **60.8**.
- It adds **201,561 MWh** of renewable dispatch and reduces backup generation by **201,561 MWh** versus base.
- Congestion-cost proxy is reduced by **EUR 7,984,655** versus base.
- Absolute curtailment is **higher** than base by **170,594 MWh**, so the ranking should be read as a multi-KPI trade-off rather than a curtailment-only result.
- Base case curtailment is **484,638 MWh** at **24.4%**.
- Best BESS sweep option: **Groningen 400 MW / 4 h**, with score **8.9**.
- Validation checks passed: **8/8**.

<!-- LATEST_RESULTS_END -->

## Setup

```bash
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows PowerShell
pip install -r requirements.txt
pip install -e .
python -m pypsa_nl_grid_flexibility.run_all
```

Run tests:

```bash
pytest -q
```

## Optional Real Hourly Profiles

The default run is self-contained and uses transparent proxy profile shapes. To use an external hourly profile source, download the Open Power System Data time-series file:

```bash
python scripts/download_opsd_profiles.py
```

Then set:

```yaml
model:
  profile_source: "opsd"
```

in `config/model_config.yaml`.

## Project Structure

```text
config/                         Scenario and model assumptions
src/pypsa_nl_grid_flexibility/   Model build, solve, analysis, plotting and reporting code
tests/                          Regression tests for profiles, config and KPI logic
outputs/                        Generated tables, figures and reports
scripts/                        Optional helper scripts
```

## Professional Use Case

This project is designed to demonstrate an end-to-end modelling workflow:

- convert transparent assumptions into a solvable network model,
- run scenario and sensitivity studies,
- diagnose congestion and curtailment,
- compare flexibility interventions,
- validate outputs before interpretation,
- communicate results through tables, plots, dashboards and concise reports.

## Limitations

- The network is a simplified Netherlands-inspired topology, not a validated transmission model.
- Corridor capacities, profile shapes and congestion windows are proxy assumptions.
- The congestion-cost proxy is not an LMP, redispatch settlement price or formal market-clearing result.
- BESS business-case outputs are screening proxies and do not include full revenue stacking, degradation, imbalance market behaviour or financing detail.
- Results should be read as scenario-screening evidence, not as operational grid-planning advice.

## CV Summary

**PyPSA-NL Grid Flexibility Modelling Platform | Python, PyPSA, pandas, Streamlit**

Built a Netherlands-inspired grid-flexibility modelling workflow to analyse renewable curtailment, congestion, backup dispatch, BESS siting/sizing, flexible connection logic and grid reinforcement scenarios. Developed reproducible PyPSA scenario runs, KPI validation, congestion-cost proxy metrics, BESS ranking, bottleneck screening, Streamlit dashboard outputs and executive reporting for decision-support communication.
