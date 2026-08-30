from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pypsa_nl_grid_flexibility.config import TABLE_DIR, load_model_config
from pypsa_nl_grid_flexibility.reporting import (
    build_key_findings_lines,
    build_pdf_report_bytes,
    build_report_bundle_bytes,
    build_portfolio_summary_markdown,
)

st.set_page_config(
    page_title="PyPSA-NL Grid Flexibility",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > .main {
        background:
            radial-gradient(circle at top left, rgba(45,212,191,0.13), transparent 32rem),
            linear-gradient(180deg, #07111f 0%, #0b1320 48%, #07111f 100%);
        color: #e5edf5;
    }
    [data-testid="stSidebar"] {
        background: #101c2e;
        border-right: 1px solid #26364d;
    }
    [data-testid="stHeader"] {
        background: rgba(7, 17, 31, 0.86);
        backdrop-filter: blur(8px);
    }
    .block-container {
        padding-top: 1.6rem;
        padding-bottom: 2.5rem;
        max-width: 1420px;
    }
    .hero {
        border: 1px solid #26364d;
        border-radius: 8px;
        padding: 1.25rem 1.35rem;
        background:
            linear-gradient(135deg, rgba(45,212,191,0.15), rgba(96,165,250,0.09)),
            #101c2e;
        box-shadow: 0 18px 48px rgba(0, 0, 0, 0.32);
        margin-bottom: 1rem;
    }
    .hero h1 {
        font-size: 2rem;
        line-height: 1.16;
        margin: 0 0 .35rem 0;
        letter-spacing: 0;
    }
    .hero p {
        margin: 0;
        color: #a8b6c7;
        font-size: 1rem;
    }
    .source-strip {
        display: flex;
        gap: .55rem;
        flex-wrap: wrap;
        margin-top: .85rem;
    }
    .source-pill {
        border: 1px solid #2f465f;
        background: #0b1320;
        border-radius: 999px;
        padding: .32rem .62rem;
        color: #cbd8e6;
        font-size: .83rem;
    }
    div[data-testid="stMetric"] {
        background: #101c2e;
        border: 1px solid #26364d;
        border-radius: 8px;
        padding: .75rem .85rem;
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.25);
    }
    div[data-testid="stMetricLabel"] p {
        color: #a8b6c7;
        font-size: .82rem;
    }
    div[data-testid="stMetricValue"] {
        color: #f8fafc;
        font-size: 1.2rem;
    }
    [data-testid="stDataFrame"],
    [data-testid="stPlotlyChart"] {
        background: #101c2e;
        border-radius: 8px;
    }
    h2, h3 {
        letter-spacing: 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <section class="hero">
      <h1>PyPSA-NL Grid Congestion, BESS & Flexible Connection Platform</h1>
      <p>
        Netherlands-inspired constrained-grid workflow for comparing renewable growth,
        grid bottlenecks, storage siting and flexible connection strategies.
      </p>
      <div class="source-strip">
        <span class="source-pill">CBS-calibrated renewable capacity</span>
        <span class="source-pill">116 TWh demand-scale reference</span>
        <span class="source-pill">Simplified PyPSA grid-flow model</span>
        <span class="source-pill">Decision-support proxy metrics</span>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------
# File loading helpers
# ---------------------------------------------------------------------


def find_output_file(filename: str) -> Path:
    """
    Find output files robustly whether Streamlit is launched from:
    - project root,
    - src folder,
    - installed editable package,
    - or another working directory.
    """
    candidates = [
        TABLE_DIR / filename,
        Path.cwd() / "outputs" / "tables" / filename,
        Path.cwd() / "outputs" / filename,
        Path(__file__).resolve().parents[2] / "outputs" / "tables" / filename,
        Path(__file__).resolve().parents[2] / "outputs" / filename,
    ]

    for path in candidates:
        if path.exists():
            return path

    return TABLE_DIR / filename


def read_csv_if_exists(path: Path, **kwargs) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path, **kwargs)
    return pd.DataFrame()


summary_path = find_output_file("scenario_summary.csv")
validation_path = find_output_file("validation_summary.csv")
pdf_path = find_output_file("executive_grid_flexibility_report.pdf")
bundle_path = find_output_file("pypsa_nl_grid_flexibility_report_bundle.zip")
bess_path = find_output_file("bess_siting_sizing_sweep.csv")
hourly_path = find_output_file("hourly_dispatch.csv")
bottleneck_path = find_output_file("bottleneck_diagnostics.csv")
n1_path = find_output_file("n1_security_proxy.csv")
bess_business_path = find_output_file("bess_business_case.csv")
model_config = load_model_config()
data_sources = model_config.get("data_sources", {})

with st.sidebar:
    st.subheader("Model Basis")
    st.caption("Sourced calibration, simplified network physics.")
    st.markdown(
        """
        - Capacity: CBS renewable statistics
        - Demand scale: Dutch 2023 electricity use
        - Network: Netherlands-inspired proxy topology
        - Costs: comparison proxies, not market prices
        """
    )
    st.divider()
    st.subheader("Output Files")
    st.caption(str(summary_path))
    st.caption(str(validation_path))
    st.caption(str(pdf_path))
    st.caption(str(bundle_path))
    st.caption(str(hourly_path))
    st.caption(str(bess_path))
    st.caption(str(bottleneck_path))
    st.caption(str(n1_path))

if not summary_path.exists():
    st.warning("Run the model first: python -m pypsa_nl_grid_flexibility.run_all")
    st.caption(f"Expected scenario summary at: {summary_path}")
    st.stop()

summary = pd.read_csv(summary_path)
validation = read_csv_if_exists(validation_path)
bess = read_csv_if_exists(bess_path)
bottlenecks = read_csv_if_exists(bottleneck_path)
n1_security = read_csv_if_exists(n1_path)
bess_business = read_csv_if_exists(bess_business_path)

if hourly_path.exists():
    hourly = pd.read_csv(hourly_path, index_col=0, parse_dates=True)
else:
    hourly = pd.DataFrame()


# ---------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------


def format_number(value: float, suffix: str = "") -> str:
    """Readable metric formatting."""
    if pd.isna(value):
        return "N/A"

    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M{suffix}"

    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}k{suffix}"

    return f"{value:.1f}{suffix}"


def friendly_scenario_name(name: str) -> str:
    return str(name).replace("_", " ").title()


def friendly_column_name(name: str) -> str:
    replacements = {
        "recommendation_rank": "Rank",
        "scenario": "Scenario",
        "grid_value_score": "Grid value score",
        "renewable_dispatch_increase_vs_base_mwh": "Renewable dispatch gain vs base [MWh]",
        "backup_reduction_vs_base_mwh": "Backup reduction vs base [MWh]",
        "emissions_reduction_vs_base_tco2": "Emissions reduction vs base [tCO2]",
        "line_overload_reduction_vs_base_hours": "Line-overload reduction vs base [h]",
        "renewable_share_of_demand_pct": "Renewable share of demand [%]",
        "curtailment_rate_pct": "Curtailment rate [%]",
        "total_congestion_cost_proxy_eur": "Congestion cost proxy [EUR]",
        "sweep_rank": "Rank",
        "bess_region": "BESS region",
        "bess_power_mw": "Power [MW]",
        "bess_duration_h": "Duration [h]",
        "bess_energy_mwh": "Energy [MWh]",
        "sweep_grid_value_score": "BESS score",
        "renewable_dispatch_gain_mwh": "Renewable dispatch gain [MWh]",
        "backup_reduction_mwh": "Backup reduction [MWh]",
        "emissions_reduction_tco2": "Emissions reduction [tCO2]",
        "line_overload_reduction_hours": "Line-overload reduction [h]",
        "congestion_cost_reduction_eur": "Congestion-cost reduction [EUR]",
        "congestion_value_per_mwh_bess_eur": "Congestion value [EUR/MWh BESS]",
        "backup_reduction_per_mw_bess": "Backup reduction [MWh/MW BESS]",
        "renewable_gain_per_mw_bess": "Renewable gain [MWh/MW BESS]",
        "line": "Line",
        "outaged_line": "Outaged line",
        "max_utilisation_pct": "Max utilisation [%]",
        "mean_utilisation_pct": "Mean utilisation [%]",
        "hours_above_threshold": "Hours above threshold",
        "congestion_severity_pct_hours": "Congestion severity [%h]",
        "peak_abs_flow_mw": "Peak absolute flow [MW]",
        "flow_mwh_during_congested_hours": "Flow during congested hours [MWh]",
        "bottleneck_rank_score": "Bottleneck score",
        "n1_screening_risk_score": "N-1 screening score",
        "screening_interpretation": "Interpretation",
        "bess_capex_eur": "BESS CAPEX [EUR]",
        "annualised_total_cost_eur_per_year": "Annualised cost [EUR/year]",
        "annualised_congestion_value_eur_per_year": "Annualised congestion value [EUR/year]",
        "net_annual_value_proxy_eur_per_year": "Net annual value proxy [EUR/year]",
        "benefit_cost_ratio_proxy": "Benefit-cost ratio proxy",
        "simple_payback_years_proxy": "Simple payback [years]",
    }
    return replacements.get(name, friendly_scenario_name(name))


def rename_for_display(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={col: friendly_column_name(col) for col in df.columns})


def prepare_scenario_chart_data(df: pd.DataFrame) -> pd.DataFrame:
    chart_data = df.copy()
    chart_data["Scenario"] = chart_data["scenario"].apply(friendly_scenario_name)
    return chart_data


def apply_dark_chart_theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e5edf5",
        margin={"l": 20, "r": 20, "t": 70, "b": 30},
        legend_title_text="",
    )
    fig.update_xaxes(gridcolor="rgba(148,163,184,0.18)", zerolinecolor="#475569")
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.18)", zerolinecolor="#475569")
    return fig


def add_scenario_labels(df: pd.DataFrame) -> pd.DataFrame:
    labelled = df.copy()
    labelled["Scenario"] = labelled["scenario"].apply(friendly_scenario_name)
    return labelled


def build_scenario_report(selected: pd.Series) -> str:
    scenario = selected.get("scenario", "N/A")
    return "\n".join(
        [
            f"# Scenario Report: {friendly_scenario_name(scenario)}",
            "",
            "## Key Metrics",
            "",
            f"- Grid value score: {selected.get('grid_value_score', 0):.2f}",
            f"- Renewable share of demand: {selected.get('renewable_share_of_demand_pct', 0):.2f}%",
            f"- Curtailment rate: {selected.get('curtailment_rate_pct', 0):.2f}%",
            f"- Backup dispatch: {selected.get('backup_dispatch_mwh', 0):.0f} MWh",
            f"- Line-hours above 90%: {selected.get('line_hours_above_90pct', 0):.0f}",
            f"- Congestion-cost proxy: {selected.get('total_congestion_cost_proxy_eur', 0):.0f} EUR",
            "",
            "## Interpretation",
            "",
            "This is a simplified Netherlands-inspired PyPSA scenario result. "
            "The metrics are intended for screening and communication, not for validated operational planning.",
        ]
    )


key_findings = build_key_findings_lines(summary, bess, validation)


scenario_names = summary["scenario"].dropna().tolist()
default_scenarios = scenario_names[: min(6, len(scenario_names))]

with st.sidebar:
    st.divider()
    st.subheader("Dashboard Controls")
    selected_scenarios = st.multiselect(
        "Scenario set",
        options=scenario_names,
        default=default_scenarios,
        format_func=friendly_scenario_name,
    )

    top_n_scenarios = st.slider(
        "Chart rows",
        min_value=3,
        max_value=max(3, len(scenario_names)),
        value=min(8, max(3, len(scenario_names))),
    )

if selected_scenarios:
    summary_view = summary[summary["scenario"].isin(selected_scenarios)].copy()
else:
    summary_view = summary.copy()


# ---------------------------------------------------------------------
# Dashboard tabs
# ---------------------------------------------------------------------

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Scenario comparison",
        "Hourly flows",
        "Bottlenecks & N-1",
        "BESS siting",
        "Interpretation",
        "Validation & reports",
    ]
)


# ---------------------------------------------------------------------
# Tab 1: Scenario comparison
# ---------------------------------------------------------------------

with tab1:
    st.subheader("Scenario summary")
    st.caption(
        "Scores combine renewable dispatch, backup reduction, bottleneck relief, curtailment and proxy congestion cost."
    )

    best = summary_view.iloc[0] if not summary_view.empty else summary.iloc[0]

    base_rows = summary_view.loc[
        summary_view["scenario"] == "base_2026_constrained_grid"
    ]
    base = base_rows.iloc[0] if not base_rows.empty else None

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "Best scenario",
        friendly_scenario_name(best["scenario"]),
        help="Highest ranked scenario using the balanced grid-value score.",
    )

    c2.metric(
        "Grid value score",
        f"{best['grid_value_score']:.1f}",
        help=(
            "Balanced decision-support score based on renewable dispatch, "
            "backup reduction, congestion relief, cost and curtailment-rate change."
        ),
    )

    c3.metric(
        "Backup reduction",
        format_number(best["backup_reduction_vs_base_mwh"], " MWh"),
        help="Reduction in backup generation compared with the base constrained-grid case.",
    )

    c4.metric(
        "Renewable dispatch gain",
        format_number(best["renewable_dispatch_increase_vs_base_mwh"], " MWh"),
        help="Additional renewable energy dispatched compared with the base case.",
    )

    c5.metric(
        "Congestion cost change",
        format_number(best["congestion_cost_reduction_vs_base_eur"], " EUR"),
        help=(
            "Reduction in the congestion-cost proxy compared with the base case. "
            "Negative means the proxy increased."
        ),
    )

    if not validation.empty and "passed" in validation.columns:
        validation_passed = int(validation["passed"].sum())
        validation_total = len(validation)
        st.info(
            f"Validation status: {validation_passed}/{validation_total} checks passed."
        )

    display_cols = [
        "recommendation_rank",
        "scenario",
        "grid_value_score",
        "renewable_dispatch_increase_vs_base_mwh",
        "backup_reduction_vs_base_mwh",
        "emissions_reduction_vs_base_tco2",
        "line_overload_reduction_vs_base_hours",
        "renewable_share_of_demand_pct",
        "curtailment_rate_pct",
        "total_congestion_cost_proxy_eur",
    ]

    available_display_cols = [c for c in display_cols if c in summary_view.columns]
    display_df = summary_view[available_display_cols].copy()
    display_df["scenario"] = display_df["scenario"].apply(friendly_scenario_name)

    st.dataframe(
        rename_for_display(display_df),
        width="stretch",
        hide_index=True,
    )

    chart_data = prepare_scenario_chart_data(summary_view.head(top_n_scenarios))

    numeric_metrics = [
        c
        for c in summary_view.columns
        if c not in {"scenario"} and pd.api.types.is_numeric_dtype(summary_view[c])
    ]
    metric_options = {
        friendly_column_name(c): c
        for c in numeric_metrics
        if c
        in {
            "grid_value_score",
            "renewable_share_of_demand_pct",
            "curtailment_rate_pct",
            "backup_dispatch_mwh",
            "renewable_dispatch_mwh",
            "line_hours_above_90pct",
            "total_congestion_cost_proxy_eur",
            "emissions_proxy_tco2",
        }
    }
    selected_metric_label = st.selectbox(
        "Primary scenario metric",
        options=list(metric_options.keys()),
        index=0,
    )
    selected_metric = metric_options[selected_metric_label]

    left, right = st.columns(2)

    with left:
        fig = px.bar(
            chart_data,
            x="Scenario",
            y=selected_metric,
            color=selected_metric,
            color_continuous_scale="Teal",
            title=selected_metric_label,
            labels={
                selected_metric: selected_metric_label,
                "Scenario": "Scenario",
            },
        )
        fig.update_layout(xaxis_tickangle=-35)
        fig = apply_dark_chart_theme(fig)
        st.plotly_chart(fig, width="stretch")

    with right:
        scatter_x = st.selectbox(
            "Trade-off x-axis",
            options=list(metric_options.keys()),
            index=list(metric_options.keys()).index("Renewable share of demand [%]")
            if "Renewable share of demand [%]" in metric_options
            else 0,
        )
        scatter_y = st.selectbox(
            "Trade-off y-axis",
            options=list(metric_options.keys()),
            index=list(metric_options.keys()).index("Congestion cost proxy [EUR]")
            if "Congestion cost proxy [EUR]" in metric_options
            else 0,
        )
        scatter = add_scenario_labels(summary_view)
        fig = px.scatter(
            scatter,
            x=metric_options[scatter_x],
            y=metric_options[scatter_y],
            color="Scenario",
            size="renewable_dispatch_mwh"
            if "renewable_dispatch_mwh" in scatter.columns
            else None,
            hover_data=["scenario"],
            title="Scenario trade-off view",
            labels={
                metric_options[scatter_x]: scatter_x,
                metric_options[scatter_y]: scatter_y,
            },
        )
        fig = apply_dark_chart_theme(fig)
        st.plotly_chart(fig, width="stretch")

    st.markdown("### Scenario report export")
    report_scenario = st.selectbox(
        "Report scenario",
        options=summary_view["scenario"].dropna().tolist(),
        format_func=friendly_scenario_name,
    )
    report_row = summary_view.loc[summary_view["scenario"] == report_scenario].iloc[0]
    st.download_button(
        "Download selected scenario report",
        data=build_scenario_report(report_row),
        file_name=f"{report_scenario}_scenario_report.md",
        mime="text/markdown",
    )


# ---------------------------------------------------------------------
# Tab 2: Hourly flows
# ---------------------------------------------------------------------

with tab2:
    st.subheader("Hourly dispatch and line utilisation")
    st.caption(
        "Hourly profiles are transparent proxy shapes applied to CBS-calibrated installed capacity and demand scale."
    )

    if hourly.empty:
        st.info("Hourly output not available.")
        st.caption(f"Expected hourly output at: {hourly_path}")
        st.caption("Run: python -m pypsa_nl_grid_flexibility.run_all")
    elif "scenario" not in hourly.columns:
        st.warning(
            "Hourly file was found, but it does not contain a 'scenario' column."
        )
        st.caption(f"Loaded file: {hourly_path}")
    else:
        selected_scenario = st.selectbox(
            "Select scenario",
            hourly["scenario"].dropna().unique(),
            format_func=friendly_scenario_name,
        )

        df = hourly[hourly["scenario"] == selected_scenario].copy()
        df.index = pd.to_datetime(df.index)

        min_time = df.index.min().to_pydatetime()
        max_time = df.index.max().to_pydatetime()
        selected_window = st.slider(
            "Time window",
            min_value=min_time,
            max_value=max_time,
            value=(min_time, max_time),
            format="MMM D, HH:mm",
        )
        df = df.loc[selected_window[0] : selected_window[1]]

        dispatch_cols = [
            "total_demand_mw",
            "total_renewable_dispatch_mw",
            "total_backup_dispatch_mw",
            "total_curtailment_mw",
        ]
        dispatch_cols = [c for c in dispatch_cols if c in df.columns]
        selected_dispatch_cols = st.multiselect(
            "Dispatch series",
            dispatch_cols,
            default=dispatch_cols,
            format_func=friendly_column_name,
        )

        if not selected_dispatch_cols:
            st.warning("No hourly dispatch columns found.")
        else:
            fig = px.line(
                df,
                y=selected_dispatch_cols,
                title=f"Hourly dispatch: {friendly_scenario_name(selected_scenario)}",
                labels={
                    "value": "Power [MW]",
                    "index": "Time",
                    "variable": "Series",
                },
            )
            fig = apply_dark_chart_theme(fig)
            st.plotly_chart(fig, width="stretch")

        utilisation_cols = [c for c in df.columns if c.endswith("_utilisation_pct")]

        if not utilisation_cols:
            st.warning("No line-utilisation columns found.")
        else:
            default_lines = utilisation_cols[:5]

            selected_lines = st.multiselect(
                "Line utilisation columns",
                utilisation_cols,
                default=default_lines,
            )

            if selected_lines:
                fig = px.line(
                    df,
                    y=selected_lines,
                    title="Selected line utilisation",
                    labels={
                        "value": "Line utilisation [%]",
                        "index": "Time",
                        "variable": "Line",
                    },
                )
                fig.add_hline(
                    y=90,
                    line_dash="dash",
                    annotation_text="90% congestion threshold",
                    annotation_position="top left",
                )
                fig = apply_dark_chart_theme(fig)
                st.plotly_chart(fig, width="stretch")


# ---------------------------------------------------------------------
# Tab 3: Bottlenecks and N-1
# ---------------------------------------------------------------------

with tab3:
    st.subheader("Bottleneck and N-1 screening")
    st.caption(
        "Post-processing diagnostics from solved flows. N-1 is a screening proxy, not a rerun contingency power flow."
    )

    if bottlenecks.empty:
        st.info(
            "Bottleneck diagnostics are not available. Run the model pipeline first."
        )
    else:
        bottleneck_scenario = st.selectbox(
            "Bottleneck scenario",
            options=bottlenecks["scenario"].dropna().unique(),
            format_func=friendly_scenario_name,
        )
        bottleneck_view = bottlenecks[
            bottlenecks["scenario"] == bottleneck_scenario
        ].copy()
        top_bottlenecks = bottleneck_view.sort_values(
            "bottleneck_rank_score",
            ascending=False,
        ).head(12)

        left, right = st.columns(2)
        with left:
            fig = px.bar(
                top_bottlenecks,
                x="line",
                y="congestion_severity_pct_hours",
                color="max_utilisation_pct",
                color_continuous_scale="Teal",
                title="Top congested corridors",
                labels={
                    "line": "Line",
                    "congestion_severity_pct_hours": "Severity [%h]",
                    "max_utilisation_pct": "Max utilisation [%]",
                },
            )
            fig.update_layout(xaxis_tickangle=-35)
            fig = apply_dark_chart_theme(fig)
            st.plotly_chart(fig, width="stretch")

        with right:
            st.dataframe(
                rename_for_display(
                    top_bottlenecks[
                        [
                            "line",
                            "max_utilisation_pct",
                            "hours_above_threshold",
                            "congestion_severity_pct_hours",
                            "peak_abs_flow_mw",
                            "bottleneck_rank_score",
                        ]
                    ]
                ),
                width="stretch",
                hide_index=True,
            )

    if n1_security.empty:
        st.info("N-1 screening output is not available.")
    else:
        st.markdown("### N-1 screening proxy")
        n1_scenario = st.selectbox(
            "N-1 scenario",
            options=n1_security["scenario"].dropna().unique(),
            format_func=friendly_scenario_name,
        )
        n1_view = n1_security[n1_security["scenario"] == n1_scenario].copy()
        n1_top = n1_view.sort_values(
            "n1_screening_risk_score",
            ascending=False,
        ).head(12)

        fig = px.bar(
            n1_top,
            x="outaged_line",
            y="n1_screening_risk_score",
            color="hours_above_threshold",
            color_continuous_scale="Oranges",
            title="Highest priority N-1 screening corridors",
            labels={
                "outaged_line": "Outaged line",
                "n1_screening_risk_score": "N-1 screening score",
                "hours_above_threshold": "Hours above threshold",
            },
        )
        fig.update_layout(xaxis_tickangle=-35)
        fig = apply_dark_chart_theme(fig)
        st.plotly_chart(fig, width="stretch")

        st.dataframe(
            rename_for_display(
                n1_top[
                    [
                        "outaged_line",
                        "max_utilisation_pct",
                        "hours_above_threshold",
                        "flow_mwh_during_congested_hours",
                        "n1_screening_risk_score",
                        "screening_interpretation",
                    ]
                ]
            ),
            width="stretch",
            hide_index=True,
        )


# ---------------------------------------------------------------------
# Tab 4: BESS siting and sizing
# ---------------------------------------------------------------------

with tab4:
    st.subheader("BESS siting and sizing study")
    st.caption(
        "Each option is compared against the solved high-renewables no-BESS reference case."
    )

    if bess.empty:
        st.info("BESS sweep output not available.")
        st.caption(f"Expected BESS output at: {bess_path}")
        st.caption("Run: python -m pypsa_nl_grid_flexibility.run_all")
    else:
        bess = bess[bess["scenario"] != "bess_sweep_reference_no_bess"].copy()
        bess = bess.sort_values("sweep_grid_value_score", ascending=False)

        if bess.empty:
            st.warning("BESS file exists, but no BESS sweep cases were found.")
        else:
            filter_col1, filter_col2, filter_col3 = st.columns(3)
            with filter_col1:
                region_filter = st.multiselect(
                    "Regions",
                    sorted(bess["bess_region"].dropna().unique()),
                    default=sorted(bess["bess_region"].dropna().unique()),
                )
            with filter_col2:
                power_filter = st.multiselect(
                    "Power ratings [MW]",
                    sorted(bess["bess_power_mw"].dropna().unique()),
                    default=sorted(bess["bess_power_mw"].dropna().unique()),
                )
            with filter_col3:
                duration_filter = st.multiselect(
                    "Durations [h]",
                    sorted(bess["bess_duration_h"].dropna().unique()),
                    default=sorted(bess["bess_duration_h"].dropna().unique()),
                )

            bess_view = bess[
                bess["bess_region"].isin(region_filter)
                & bess["bess_power_mw"].isin(power_filter)
                & bess["bess_duration_h"].isin(duration_filter)
            ].copy()

            if bess_view.empty:
                st.warning("No BESS cases match the selected filters.")
                st.stop()

            top_bess = bess_view.iloc[0]

            c1, c2, c3, c4, c5 = st.columns(5)

            c1.metric(
                "Best BESS location",
                str(top_bess["bess_region"]),
            )

            c2.metric(
                "Best BESS size",
                f"{top_bess['bess_power_mw']:.0f} MW / {top_bess['bess_duration_h']:.0f} h",
            )

            c3.metric(
                "BESS score",
                f"{top_bess['sweep_grid_value_score']:.1f}",
            )

            c4.metric(
                "Backup reduction",
                format_number(top_bess["backup_reduction_mwh"], " MWh"),
            )

            c5.metric(
                "Renewable dispatch gain",
                format_number(top_bess["renewable_dispatch_gain_mwh"], " MWh"),
            )

            clean_bess_cols = [
                "sweep_rank",
                "bess_region",
                "bess_power_mw",
                "bess_duration_h",
                "bess_energy_mwh",
                "sweep_grid_value_score",
                "renewable_dispatch_gain_mwh",
                "backup_reduction_mwh",
                "emissions_reduction_tco2",
                "line_overload_reduction_hours",
                "congestion_cost_reduction_eur",
                "congestion_value_per_mwh_bess_eur",
                "backup_reduction_per_mw_bess",
                "renewable_gain_per_mw_bess",
            ]

            clean_bess_cols = [c for c in clean_bess_cols if c in bess.columns]

            st.markdown("### Top BESS options")

            st.dataframe(
                rename_for_display(bess_view[clean_bess_cols].head(15)),
                width="stretch",
                hide_index=True,
            )

            chart_data = bess_view.head(10).copy()
            chart_data["Option"] = (
                chart_data["bess_region"].astype(str)
                + " — "
                + chart_data["bess_power_mw"].astype(int).astype(str)
                + " MW / "
                + chart_data["bess_duration_h"].astype(int).astype(str)
                + " h"
            )

            left, right = st.columns(2)

            with left:
                fig = px.bar(
                    chart_data,
                    x="Option",
                    y="sweep_grid_value_score",
                    color="bess_region",
                    title="Top 10 BESS siting/sizing options",
                    labels={
                        "sweep_grid_value_score": "BESS grid-value score [-]",
                        "Option": "BESS option",
                    },
                )
                fig.update_layout(xaxis_tickangle=-35)
                fig = apply_dark_chart_theme(fig)
                st.plotly_chart(fig, width="stretch")

            with right:
                scatter_data = bess_view.copy()
                score_min = scatter_data["sweep_grid_value_score"].min()
                scatter_data["marker_size_score"] = (
                    scatter_data["sweep_grid_value_score"] - score_min + 1.0
                )

                fig = px.scatter(
                    scatter_data,
                    x="bess_energy_mwh",
                    y="congestion_value_per_mwh_bess_eur",
                    color="bess_region",
                    size="marker_size_score",
                    hover_data=[
                        "sweep_grid_value_score",
                        "bess_power_mw",
                        "bess_duration_h",
                        "backup_reduction_mwh",
                        "renewable_dispatch_gain_mwh",
                    ],
                    title="BESS value vs energy capacity",
                    labels={
                        "bess_energy_mwh": "BESS energy capacity [MWh]",
                        "congestion_value_per_mwh_bess_eur": "EUR per MWh BESS",
                    },
                )
                fig = apply_dark_chart_theme(fig)
                st.plotly_chart(fig, width="stretch")

            if not bess_business.empty:
                st.markdown("### BESS business-case proxy")
                business_view = bess_business[
                    bess_business["bess_region"].isin(region_filter)
                    & bess_business["bess_power_mw"].isin(power_filter)
                    & bess_business["bess_duration_h"].isin(duration_filter)
                ].copy()

                if business_view.empty:
                    st.info("No business-case rows match the selected BESS filters.")
                else:
                    business_top = business_view.sort_values(
                        "net_annual_value_proxy_eur_per_year",
                        ascending=False,
                    ).head(15)
                    business_cols = [
                        "bess_region",
                        "bess_power_mw",
                        "bess_duration_h",
                        "bess_capex_eur",
                        "annualised_total_cost_eur_per_year",
                        "annualised_congestion_value_eur_per_year",
                        "net_annual_value_proxy_eur_per_year",
                        "benefit_cost_ratio_proxy",
                        "simple_payback_years_proxy",
                    ]
                    st.dataframe(
                        rename_for_display(business_top[business_cols]),
                        width="stretch",
                        hide_index=True,
                    )

                    fig = px.scatter(
                        business_view,
                        x="annualised_total_cost_eur_per_year",
                        y="annualised_congestion_value_eur_per_year",
                        color="bess_region",
                        size="bess_energy_mwh",
                        hover_data=[
                            "bess_power_mw",
                            "bess_duration_h",
                            "benefit_cost_ratio_proxy",
                            "net_annual_value_proxy_eur_per_year",
                        ],
                        title="Annualised BESS value vs annualised cost",
                        labels={
                            "annualised_total_cost_eur_per_year": "Cost [EUR/year]",
                            "annualised_congestion_value_eur_per_year": "Value [EUR/year]",
                        },
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=[
                                business_view[
                                    "annualised_total_cost_eur_per_year"
                                ].min(),
                                business_view[
                                    "annualised_total_cost_eur_per_year"
                                ].max(),
                            ],
                            y=[
                                business_view[
                                    "annualised_total_cost_eur_per_year"
                                ].min(),
                                business_view[
                                    "annualised_total_cost_eur_per_year"
                                ].max(),
                            ],
                            mode="lines",
                            name="Value = cost",
                            line={"dash": "dash", "color": "#94a3b8"},
                        )
                    )
                    fig = apply_dark_chart_theme(fig)
                    st.plotly_chart(fig, width="stretch")


# ---------------------------------------------------------------------
# Tab 5: Interpretation
# ---------------------------------------------------------------------

with tab5:
    st.subheader("Dynamic interpretation")

    st.markdown("### Latest key findings")
    st.markdown("\n".join(key_findings))

    st.markdown("### How to read the score")
    st.markdown(
        """
        The grid-value score is a screening metric built from the current scenario table.
        It balances renewable dispatch, backup reduction, line-overload relief, curtailment-rate
        change, objective cost and congestion-cost proxy. It is not a market price and should be
        read together with the individual KPI columns.
        """
    )

    st.markdown("### Why the narrative is dynamic")
    st.markdown(
        """
        The findings above are derived from the generated CSV outputs. If scenario assumptions,
        costs, ranking weights or BESS candidates change, the dashboard and generated reports
        update from the new results instead of relying on fixed scenario names.
        """
    )

    st.markdown("### Data provenance")

    if data_sources:
        for label, source in data_sources.items():
            st.markdown(f"- **{friendly_column_name(label)}:** {source}")
    else:
        st.info("No data source metadata found in model_config.yaml.")


# ---------------------------------------------------------------------
# Tab 6: Validation & reports
# ---------------------------------------------------------------------

with tab6:
    st.subheader("Validation and report exports")

    if validation.empty:
        st.warning(
            "No validation summary found. Run the model workflow to generate validation_summary.csv."
        )
    else:
        passed = int(validation["passed"].sum()) if "passed" in validation else 0
        total = len(validation)
        failed = (
            validation.loc[~validation["passed"], "check"].astype(str).tolist()
            if "passed" in validation and "check" in validation
            else []
        )

        m1, m2, m3 = st.columns(3)
        m1.metric("Validation checks", f"{passed}/{total}")
        m2.metric("Failed checks", str(len(failed)))
        m3.metric("Result files", "current" if summary_path.exists() else "missing")

        st.dataframe(
            rename_for_display(validation),
            width="stretch",
            hide_index=True,
        )

    st.markdown("### Portfolio summary")
    portfolio_summary = build_portfolio_summary_markdown(summary, bess, validation)
    st.download_button(
        "Download portfolio summary",
        data=portfolio_summary,
        file_name="portfolio_summary.md",
        mime="text/markdown",
    )
    st.markdown(portfolio_summary)

    st.markdown("### Full report bundle")
    st.markdown("### PDF report")
    if pdf_path.exists():
        pdf_bytes = pdf_path.read_bytes()
        pdf_label = "Download PDF report"
    else:
        pdf_bytes = build_pdf_report_bytes(summary, bess, validation)
        pdf_label = "Generate PDF report"

    st.download_button(
        pdf_label,
        data=pdf_bytes,
        file_name="executive_grid_flexibility_report.pdf",
        mime="application/pdf",
    )

    st.markdown("### Full report bundle")
    if bundle_path.exists():
        bundle_bytes = bundle_path.read_bytes()
        bundle_label = "Download full report bundle"
    else:
        bundle_bytes, manifest = build_report_bundle_bytes()
        bundle_label = f"Generate full report bundle ({len(manifest)} files)"

    st.download_button(
        bundle_label,
        data=bundle_bytes,
        file_name="pypsa_nl_grid_flexibility_report_bundle.zip",
        mime="application/zip",
    )
