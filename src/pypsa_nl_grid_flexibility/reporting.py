from __future__ import annotations

import pandas as pd

from pypsa_nl_grid_flexibility.config import PROJECT_ROOT, REPORT_DIR


README_RESULTS_START = "<!-- LATEST_RESULTS_START -->"
README_RESULTS_END = "<!-- LATEST_RESULTS_END -->"


def _friendly_name(value: object) -> str:
    return str(value).replace("_", " ").title()


def _fmt_number(value: object, digits: int = 0) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "N/A"
    return f"{float(numeric):,.{digits}f}"


def _fmt_eur(value: object) -> str:
    return f"EUR {_fmt_number(value, 0)}"


def _non_reference_bess(bess_summary: pd.DataFrame | None) -> pd.DataFrame:
    if bess_summary is None or bess_summary.empty:
        return pd.DataFrame()

    bess_data = bess_summary.copy()
    if "scenario" in bess_data.columns:
        bess_data = bess_data[
            bess_data["scenario"] != "bess_sweep_reference_no_bess"
        ].copy()
    if "sweep_grid_value_score" in bess_data.columns:
        bess_data = bess_data.sort_values("sweep_grid_value_score", ascending=False)
    return bess_data


def _validation_counts(validation: pd.DataFrame | None) -> tuple[int, int, list[str]]:
    if validation is None or validation.empty or "passed" not in validation:
        return 0, 0, []

    passed = int(validation["passed"].sum())
    total = len(validation)
    failed = (
        validation.loc[~validation["passed"], "check"].astype(str).tolist()
        if "check" in validation
        else []
    )
    return passed, total, failed


def build_dynamic_findings(
    summary: pd.DataFrame,
    bess_summary: pd.DataFrame | None = None,
    validation: pd.DataFrame | None = None,
) -> dict[str, object]:
    """Derive latest interpretation fields from generated model outputs."""
    if summary.empty:
        return {"has_results": False}

    ranked = summary.sort_values("recommendation_rank").copy()
    best = ranked.iloc[0]
    base_rows = summary.loc[summary["scenario"] == "base_2026_constrained_grid"]
    base = base_rows.iloc[0] if not base_rows.empty else None
    top_bess_rows = _non_reference_bess(bess_summary)
    top_bess = top_bess_rows.iloc[0] if not top_bess_rows.empty else None
    validation_passed, validation_total, validation_failed = _validation_counts(validation)

    curtailment_delta = best.get("absolute_curtailment_change_vs_base_mwh", 0.0)
    curtailment_direction = "higher" if curtailment_delta > 0 else "lower or equal"
    congestion_delta = best.get("congestion_cost_reduction_vs_base_eur", 0.0)
    congestion_direction = "reduced" if congestion_delta >= 0 else "increased"

    return {
        "has_results": True,
        "best": best,
        "base": base,
        "top_bess": top_bess,
        "validation_passed": validation_passed,
        "validation_total": validation_total,
        "validation_failed": validation_failed,
        "curtailment_direction": curtailment_direction,
        "congestion_direction": congestion_direction,
    }


def build_key_findings_lines(
    summary: pd.DataFrame,
    bess_summary: pd.DataFrame | None = None,
    validation: pd.DataFrame | None = None,
) -> list[str]:
    """Build concise, data-driven finding bullets."""
    findings = build_dynamic_findings(summary, bess_summary, validation)
    if not findings.get("has_results"):
        return ["- No generated scenario results are available yet."]

    best = findings["best"]
    base = findings.get("base")
    top_bess = findings.get("top_bess")
    validation_passed = findings.get("validation_passed", 0)
    validation_total = findings.get("validation_total", 0)

    lines = [
        (
            f"- Top-ranked scenario: **{_friendly_name(best.get('scenario', 'N/A'))}** "
            f"with grid-value score **{_fmt_number(best.get('grid_value_score'), 1)}**."
        ),
        (
            f"- It adds **{_fmt_number(best.get('renewable_dispatch_increase_vs_base_mwh'))} MWh** "
            f"of renewable dispatch and reduces backup generation by "
            f"**{_fmt_number(best.get('backup_reduction_vs_base_mwh'))} MWh** versus base."
        ),
        (
            f"- Congestion-cost proxy is {findings['congestion_direction']} by "
            f"**{_fmt_eur(best.get('congestion_cost_reduction_vs_base_eur'))}** versus base."
        ),
        (
            f"- Absolute curtailment is **{findings['curtailment_direction']}** than base by "
            f"**{_fmt_number(abs(best.get('absolute_curtailment_change_vs_base_mwh', 0)))} MWh**, "
            "so the ranking should be read as a multi-KPI trade-off rather than a curtailment-only result."
        ),
    ]

    if base is not None:
        lines.append(
            f"- Base case curtailment is **{_fmt_number(base.get('renewable_curtailment_mwh'))} MWh** "
            f"at **{_fmt_number(base.get('curtailment_rate_pct'), 1)}%**."
        )

    if top_bess is not None:
        lines.append(
            (
                f"- Best BESS sweep option: **{top_bess.get('bess_region', 'N/A')} "
                f"{_fmt_number(top_bess.get('bess_power_mw'))} MW / "
                f"{_fmt_number(top_bess.get('bess_duration_h'))} h**, with score "
                f"**{_fmt_number(top_bess.get('sweep_grid_value_score'), 1)}**."
            )
        )

    if validation_total:
        lines.append(
            f"- Validation checks passed: **{validation_passed}/{validation_total}**."
        )

    return lines


def build_portfolio_summary_markdown(
    summary: pd.DataFrame,
    bess_summary: pd.DataFrame | None = None,
    validation: pd.DataFrame | None = None,
) -> str:
    """Build a recruiter/interview-ready summary from generated outputs."""
    key_findings = build_key_findings_lines(summary, bess_summary, validation)
    findings = build_dynamic_findings(summary, bess_summary, validation)
    failed = findings.get("validation_failed", [])
    failed_text = ", ".join(failed) if failed else "none"

    lines = [
        "# Portfolio Summary",
        "",
        "## Problem Statement",
        "",
        "The project screens grid-flexibility options for a simplified Netherlands-inspired constrained grid. "
        "It compares renewable growth, storage siting, flexible connection logic and targeted reinforcement "
        "using a reproducible PyPSA workflow.",
        "",
        "## Methodology",
        "",
        "- Build regional PyPSA networks from transparent configuration assumptions.",
        "- Solve hourly linear dispatch for each scenario with HiGHS.",
        "- Export scenario KPIs, hourly dispatch, bottleneck diagnostics and BESS sweep results.",
        "- Validate KPI consistency before writing reports.",
        "- Interpret results through a multi-KPI grid-value score instead of a single curtailment metric.",
        "",
        "## Latest Key Findings",
        "",
        *key_findings,
        "",
        "## Validation",
        "",
        f"- Failed validation checks: **{failed_text}**",
        "- The validation layer checks solver status, curtailment balance, percentage bounds, BESS-cycle sanity, objective costs and rank completeness.",
        "",
        "## Limitations",
        "",
        "- The network is a simplified regional proxy, not a validated Dutch transmission model.",
        "- The congestion-cost metric is a screening proxy, not an LMP or market settlement price.",
        "- Profile shapes, line ratings and congestion windows are transparent modelling assumptions.",
        "- BESS business-case values exclude degradation, revenue stacking and detailed financing.",
        "",
        "## Next Improvements With Production Data",
        "",
        "- Replace proxy topology with validated grid zones and corridor limits.",
        "- Use audited hourly load, wind, solar and offshore production profiles.",
        "- Add contingency-constrained flows or explicit post-contingency screening.",
        "- Extend BESS economics with degradation, reserve markets and imbalance-market revenue.",
        "- Calibrate congestion-cost proxies against observed redispatch or constraint-management costs.",
        "",
    ]
    return "\n".join(lines)


def write_portfolio_summary(
    summary: pd.DataFrame,
    bess_summary: pd.DataFrame | None = None,
    validation: pd.DataFrame | None = None,
) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "portfolio_summary.md").write_text(
        build_portfolio_summary_markdown(summary, bess_summary, validation),
        encoding="utf-8",
    )


def update_readme_latest_results(
    summary: pd.DataFrame,
    bess_summary: pd.DataFrame | None = None,
    validation: pd.DataFrame | None = None,
) -> None:
    """Replace the generated latest-results block in README.md."""
    readme_path = PROJECT_ROOT / "README.md"
    if not readme_path.exists():
        return

    block_lines = [
        README_RESULTS_START,
        "## Latest Generated Results",
        "",
        "This section is generated from the latest files in `outputs/tables/` when `python -m pypsa_nl_grid_flexibility.run_all` is executed.",
        "",
        *build_key_findings_lines(summary, bess_summary, validation),
        "",
        README_RESULTS_END,
    ]
    block = "\n".join(block_lines)

    text = readme_path.read_text(encoding="utf-8")
    if README_RESULTS_START in text and README_RESULTS_END in text:
        prefix = text.split(README_RESULTS_START, 1)[0].rstrip()
        suffix = text.split(README_RESULTS_END, 1)[1].lstrip()
        updated = f"{prefix}\n\n{block}\n\n{suffix}"
    else:
        insertion = "\n\n".join([block, "## Setup"])
        updated = text.replace("## Setup", insertion, 1)

    readme_path.write_text(updated, encoding="utf-8")


def write_executive_report(
    summary: pd.DataFrame,
    bess_summary: pd.DataFrame | None = None,
    validation: pd.DataFrame | None = None,
) -> None:
    """
    Write a short executive markdown report for the grid-flexibility study.
    """
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    if summary.empty:
        report_text = "# Executive Grid Flexibility Report\n\nNo scenario summary data available.\n"
        (REPORT_DIR / "executive_grid_flexibility_report.md").write_text(
            report_text,
            encoding="utf-8",
        )
        return

    best = summary.iloc[0]
    key_findings = build_key_findings_lines(summary, bess_summary, validation)

    base_rows = summary.loc[summary["scenario"] == "base_2026_constrained_grid"]
    base = base_rows.iloc[0] if not base_rows.empty else None

    lines = [
        "# Executive Grid Flexibility Report",
        "",
        "## Purpose",
        "",
        "This project evaluates Netherlands-inspired grid congestion scenarios using PyPSA. "
        "It focuses on connection-capacity constraints, renewable curtailment, BESS siting, "
        "flexible connection logic and a congestion-cost proxy for decision support.",
        "",
        "## Main scenario result",
        "",
        f"- Top-ranked scenario: **{_friendly_name(best.get('scenario', 'N/A'))}**",
        f"- Decision-support score: **{_fmt_number(best.get('grid_value_score'), 1)}**",
        f"- Renewable dispatch increase vs base: **{_fmt_number(best.get('renewable_dispatch_increase_vs_base_mwh'))} MWh**",
        f"- Backup reduction vs base: **{_fmt_number(best.get('backup_reduction_vs_base_mwh'))} MWh**",
        f"- Emissions reduction vs base: **{_fmt_number(best.get('emissions_reduction_vs_base_tco2'))} tCO2**",
        f"- Congestion-cost proxy change vs base: **{_fmt_eur(best.get('congestion_cost_reduction_vs_base_eur'))}**",
        "",
        "## Why absolute curtailment is not enough",
        "",
        "High-renewable scenarios can increase absolute curtailment because renewable availability rises faster "
        "than grid capacity. The ranking therefore combines renewable dispatch, backup reduction, line-overload "
        "relief, curtailment-rate change, system cost and congestion-cost proxy.",
        "",
        "## Dynamic key findings",
        "",
        *key_findings,
        "",
    ]

    if base is not None:
        lines += [
            "## Base-case reference",
            "",
            f"- Base renewable share of demand: **{_fmt_number(base.get('renewable_share_of_demand_pct'), 1)}%**",
            f"- Base backup dispatch: **{_fmt_number(base.get('backup_dispatch_mwh'))} MWh**",
            f"- Base line-hours above 90% utilisation: **{_fmt_number(base.get('line_hours_above_90pct'))}**",
            f"- Base congestion-cost proxy: **{_fmt_eur(base.get('total_congestion_cost_proxy_eur'))}**",
            "",
        ]

    if validation is not None and not validation.empty:
        passed = int(validation["passed"].sum()) if "passed" in validation else 0
        total = len(validation)
        failed = (
            validation.loc[~validation["passed"], "check"].astype(str).tolist()
            if "passed" in validation and "check" in validation
            else []
        )
        lines += [
            "## Validation summary",
            "",
            f"- Validation checks passed: **{passed}/{total}**",
        ]
        if failed:
            lines.append(f"- Failed checks: **{', '.join(failed)}**")
        else:
            lines.append("- Failed checks: **none**")
        lines += [
            "",
            "The validation layer checks solver status, curtailment balance, percentage bounds, "
            "BESS-cycle sanity and recommendation-rank completeness before the report is written.",
            "",
        ]

    if bess_summary is not None and not bess_summary.empty:
        bess_data = bess_summary.copy()

        if "scenario" in bess_data.columns:
            bess_data = bess_data[
                bess_data["scenario"] != "bess_sweep_reference_no_bess"
            ].copy()

        if not bess_data.empty:
            if "sweep_grid_value_score" in bess_data.columns:
                bess_data = bess_data.sort_values(
                    "sweep_grid_value_score",
                    ascending=False,
                )

            top_bess = bess_data.iloc[0]

            lines += [
                "## BESS siting and sizing result",
                "",
                (
                    f"- Top BESS option: **{top_bess.get('bess_region', 'N/A')} — "
                    f"{top_bess.get('bess_power_mw', 0):.0f} MW / "
                    f"{top_bess.get('bess_duration_h', 0):.0f} h**"
                ),
                f"- BESS score: **{top_bess.get('sweep_grid_value_score', 0):.1f}**",
                f"- Backup reduction: **{_fmt_number(top_bess.get('backup_reduction_mwh'))} MWh**",
                f"- Renewable dispatch gain: **{_fmt_number(top_bess.get('renewable_dispatch_gain_mwh'))} MWh**",
                f"- Congestion-cost reduction: **{_fmt_eur(top_bess.get('congestion_cost_reduction_eur'))}**",
                "",
                "The BESS sweep compares candidate locations, power ratings and durations. The best option is not "
                "necessarily the largest battery; it is the option with the best combination of renewable-dispatch "
                "gain, backup reduction, congestion-cost relief and utilisation per MW/MWh of battery capacity.",
                "",
            ]

    lines += [
        "## Modelling limitations",
        "",
        "- The grid topology and time series are synthetic and intended for portfolio demonstration.",
        "- The congestion-cost proxy is not a formal market price or locational marginal price.",
        "- The model is designed for scenario screening and communication, not TSO-grade planning.",
        "",
    ]

    (REPORT_DIR / "executive_grid_flexibility_report.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


# Backward-compatible aliases for older code versions.
def write_report(
    summary: pd.DataFrame,
    bess_summary: pd.DataFrame | None = None,
    validation: pd.DataFrame | None = None,
) -> None:
    write_executive_report(summary, bess_summary, validation)


def generate_report(
    summary: pd.DataFrame,
    bess_summary: pd.DataFrame | None = None,
    validation: pd.DataFrame | None = None,
) -> None:
    write_executive_report(summary, bess_summary, validation)


def write_markdown_report(
    summary: pd.DataFrame,
    bess_summary: pd.DataFrame | None = None,
    validation: pd.DataFrame | None = None,
) -> None:
    write_executive_report(summary, bess_summary, validation)
