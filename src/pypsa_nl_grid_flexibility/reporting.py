from __future__ import annotations

import io
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    LongTable,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
)

from pypsa_nl_grid_flexibility.config import (
    FIGURE_DIR,
    PROJECT_ROOT,
    REPORT_DIR,
    TABLE_DIR,
)


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


def _report_asset_category(path: Path) -> str:
    rel = path.relative_to(PROJECT_ROOT).as_posix()
    if rel.startswith("config/"):
        return "config"
    if rel.startswith("data/raw/"):
        return "raw data"
    if rel.startswith("data/processed/"):
        return "processed data"
    if rel.startswith("outputs/figures/"):
        return "figures"
    if rel.startswith("outputs/tables/"):
        return "tables"
    if rel.startswith("outputs/reports/"):
        return "reports"
    return "inputs"


def _escape_pdf_text(value: object) -> str:
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def _clean_pdf_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = text.replace("**", "")
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = text.replace("## ", "")
    text = text.replace("- ", "")
    return text.strip()


def _pdf_table(df: pd.DataFrame, rename_map: dict[str, str]) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    return df.rename(
        columns={src: dst for src, dst in rename_map.items() if src in df.columns}
    )


def _load_csv_if_exists(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def _format_pdf_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    formatted = df.copy()
    for column in formatted.columns:
        series = formatted[column]
        if pd.api.types.is_numeric_dtype(series):
            if column.endswith("_pct") or "pct" in column.lower():
                formatted[column] = series.map(
                    lambda value: "" if pd.isna(value) else f"{float(value):.1f}"
                )
            elif column in {
                "recommendation_rank",
                "sweep_rank",
                "hours_above_threshold",
                "line_hours_above_90pct",
            }:
                formatted[column] = series.map(
                    lambda value: "" if pd.isna(value) else f"{float(value):.0f}"
                )
            else:
                formatted[column] = series.map(
                    lambda value: "" if pd.isna(value) else f"{float(value):,.2f}"
                )
        else:
            formatted[column] = series.fillna("").astype(str)
    return formatted


def _make_longtable(
    df: pd.DataFrame,
    *,
    doc_width: float,
    title: str | None = None,
    col_widths: list[float] | None = None,
) -> list[object]:
    if df.empty:
        return []

    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        "pdf_table_header",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=6.5,
        leading=7.5,
        textColor=colors.white,
    )
    cell_style = ParagraphStyle(
        "pdf_table_cell",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=6,
        leading=7,
    )

    formatted = _format_pdf_frame(df)
    data = [
        [Paragraph(_escape_pdf_text(col), header_style) for col in formatted.columns]
    ]
    for _, row in formatted.iterrows():
        data.append([Paragraph(_escape_pdf_text(value), cell_style) for value in row])

    if col_widths is None:
        if len(formatted.columns) == 1:
            col_widths = [doc_width]
        else:
            first_width = min(doc_width * 0.28, 2.8 * inch)
            remaining = max(doc_width - first_width, doc_width * 0.4)
            tail_width = remaining / max(len(formatted.columns) - 1, 1)
            col_widths = [first_width] + [tail_width] * (len(formatted.columns) - 1)

    table = LongTable(data, repeatRows=1, colWidths=col_widths)
    table.setStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.white, colors.HexColor("#f3f4f6")],
            ),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
    )

    output: list[object] = []
    if title is not None:
        output.append(
            Paragraph(
                title,
                ParagraphStyle(
                    "pdf_table_title",
                    parent=styles["Heading3"],
                    fontName="Helvetica-Bold",
                    fontSize=11,
                    leading=13,
                    spaceAfter=6,
                ),
            )
        )
    output.append(table)
    output.append(Spacer(1, 0.15 * inch))
    return output


def _append_markdown_section(
    story: list[object],
    title: str,
    markdown_path: Path,
    styles: dict[str, ParagraphStyle],
) -> None:
    if not markdown_path.exists():
        return

    story.append(Paragraph(title, styles["section"]))
    story.append(Spacer(1, 0.08 * inch))
    story.append(
        Preformatted(
            markdown_path.read_text(encoding="utf-8"),
            styles["preformatted"],
        )
    )
    story.append(Spacer(1, 0.15 * inch))


def _append_figure_section(
    story: list[object],
    title: str,
    figure_path: Path,
    styles: dict[str, ParagraphStyle],
    doc_width: float,
) -> None:
    if not figure_path.exists():
        return

    story.append(Paragraph(title, styles["section"]))
    story.append(Spacer(1, 0.08 * inch))
    image = Image(str(figure_path))
    original_width = image.imageWidth or doc_width
    original_height = image.imageHeight or (doc_width * 0.6)
    image.drawWidth = doc_width
    image.drawHeight = original_height * doc_width / original_width
    if image.drawHeight > 6.8 * inch:
        scale = (6.8 * inch) / image.drawHeight
        image.drawWidth *= scale
        image.drawHeight *= scale
    story.append(image)
    story.append(Spacer(1, 0.15 * inch))


def _iter_report_bundle_files() -> list[Path]:
    """Collect the files that should ship in the downloadable report bundle."""
    candidates: list[Path] = []
    for pattern in [
        "README.md",
        "pyproject.toml",
        "requirements.txt",
        "config/*.yaml",
        "data/raw/README.md",
        "data/processed/*.csv",
        "outputs/reports/*.md",
        "outputs/figures/*.png",
        "outputs/tables/*.csv",
    ]:
        candidates.extend(PROJECT_ROOT.glob(pattern))

    seen: set[Path] = set()
    files: list[Path] = []
    for path in candidates:
        if not path.is_file():
            continue
        if path.suffix == ".zip":
            continue
        if path in seen:
            continue
        seen.add(path)
        files.append(path)

    return sorted(files)


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
    validation_passed, validation_total, validation_failed = _validation_counts(
        validation
    )

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


def build_report_bundle_bytes() -> tuple[bytes, pd.DataFrame]:
    """Create a zip bundle containing inputs, outputs, figures and reports."""
    files = _iter_report_bundle_files()
    manifest_rows = []
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in files:
            arcname = path.relative_to(PROJECT_ROOT).as_posix()
            bundle.write(path, arcname)
            manifest_rows.append(
                {
                    "path": arcname,
                    "bytes": path.stat().st_size,
                }
            )

        manifest = pd.DataFrame(manifest_rows)
        bundle.writestr(
            "bundle_manifest.json",
            json.dumps(manifest_rows, indent=2, ensure_ascii=False),
        )
        bundle.writestr("bundle_manifest.csv", manifest.to_csv(index=False))

    return buffer.getvalue(), pd.DataFrame(manifest_rows)


def write_report_bundle() -> Path:
    """Write the downloadable report bundle to disk."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    bundle_bytes, _ = build_report_bundle_bytes()
    bundle_path = REPORT_DIR / "pypsa_nl_grid_flexibility_report_bundle.zip"
    bundle_path.write_bytes(bundle_bytes)
    return bundle_path


def build_pdf_report_bytes(
    summary: pd.DataFrame,
    bess_summary: pd.DataFrame | None = None,
    validation: pd.DataFrame | None = None,
) -> bytes:
    """Build a human-readable PDF report and embed the full zip bundle as an attachment."""
    bundle_bytes, bundle_manifest = build_report_bundle_bytes()

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="report_title",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="report_subtitle",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=13,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#334155"),
            spaceAfter=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=15,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=8,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#111827"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="bullet",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            leftIndent=12,
            firstLineIndent=-8,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="preformatted",
            parent=styles["Code"],
            fontName="Courier",
            fontSize=6.6,
            leading=8,
            leftIndent=0,
            rightIndent=0,
        )
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.5 * inch,
    )

    story: list[object] = []
    story.append(Paragraph("PyPSA-NL Grid Flexibility Report", styles["report_title"]))
    story.append(
        Paragraph(
            "Human-readable executive report with charts, tables and embedded full data bundle.",
            styles["report_subtitle"],
        )
    )
    story.append(
        Paragraph(
            f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            "The attached ZIP bundle contains the complete machine-readable inputs, outputs, figures and reports.",
            styles["body"],
        )
    )
    story.append(Spacer(1, 0.18 * inch))

    key_findings = build_key_findings_lines(summary, bess_summary, validation)
    story.append(Paragraph("Latest key findings", styles["section"]))
    for line in key_findings:
        story.append(Paragraph(_clean_pdf_text(line), styles["bullet"]))
    story.append(Spacer(1, 0.12 * inch))

    if not summary.empty:
        ranked = summary.sort_values("recommendation_rank").head(9).copy()
        base_rows = summary.loc[summary["scenario"] == "base_2026_constrained_grid"]
        base = base_rows.iloc[0] if not base_rows.empty else None
        core_cols = [
            "scenario",
            "grid_value_score",
            "renewable_dispatch_increase_vs_base_mwh",
            "backup_reduction_vs_base_mwh",
            "curtailment_rate_pct",
            "total_congestion_cost_proxy_eur",
            "recommendation_rank",
        ]
        scenario_table = _pdf_table(
            ranked[core_cols],
            {
                "scenario": "Scenario",
                "grid_value_score": "Score",
                "renewable_dispatch_increase_vs_base_mwh": "Renewable gain [MWh]",
                "backup_reduction_vs_base_mwh": "Backup reduction [MWh]",
                "curtailment_rate_pct": "Curtailment [%]",
                "total_congestion_cost_proxy_eur": "Congestion proxy [EUR]",
                "recommendation_rank": "Rank",
            },
        )
        story.extend(
            _make_longtable(
                scenario_table,
                doc_width=doc.width,
                title="Scenario ranking snapshot",
                col_widths=[
                    doc.width * 0.27,
                    doc.width * 0.08,
                    doc.width * 0.18,
                    doc.width * 0.18,
                    doc.width * 0.12,
                    doc.width * 0.17,
                    doc.width * 0.05,
                ],
            )
        )

        if base is not None:
            base_view = pd.DataFrame(
                [
                    {
                        "Base curtailment [MWh]": base.get("renewable_curtailment_mwh"),
                        "Base curtailment rate [%]": base.get("curtailment_rate_pct"),
                        "Base backup [MWh]": base.get("backup_dispatch_mwh"),
                        "Base congestion cost proxy [EUR]": base.get(
                            "total_congestion_cost_proxy_eur"
                        ),
                        "Base renewable share [%]": base.get(
                            "renewable_share_of_demand_pct"
                        ),
                    }
                ]
            )
            story.extend(
                _make_longtable(
                    base_view,
                    doc_width=doc.width,
                    title="Base-case reference metrics",
                    col_widths=[doc.width / 5.0] * 5,
                )
            )

    if validation is not None and not validation.empty:
        validation_view = validation[
            [
                col
                for col in ["check", "passed", "value", "tolerance", "details"]
                if col in validation.columns
            ]
        ].copy()
        validation_view = _pdf_table(
            validation_view,
            {
                "check": "Check",
                "passed": "Pass",
                "value": "Value",
                "tolerance": "Tolerance",
                "details": "Details",
            },
        )
        story.extend(
            _make_longtable(
                validation_view,
                doc_width=doc.width,
                title="Validation summary",
                col_widths=[
                    doc.width * 0.22,
                    doc.width * 0.08,
                    doc.width * 0.16,
                    doc.width * 0.14,
                    doc.width * 0.40,
                ],
            )
        )

    if bess_summary is not None and not bess_summary.empty:
        bess_view = bess_summary.copy()
        if "scenario" in bess_view.columns:
            bess_view = bess_view[
                bess_view["scenario"] != "bess_sweep_reference_no_bess"
            ].copy()
        if not bess_view.empty:
            bess_view = bess_view.sort_values(
                "sweep_grid_value_score",
                ascending=False,
            ).head(15)
            bess_cols = [
                c
                for c in [
                    "bess_region",
                    "bess_power_mw",
                    "bess_duration_h",
                    "bess_energy_mwh",
                    "sweep_grid_value_score",
                    "renewable_dispatch_gain_mwh",
                    "backup_reduction_mwh",
                    "congestion_cost_reduction_eur",
                ]
                if c in bess_view.columns
            ]
            bess_table = _pdf_table(
                bess_view[bess_cols],
                {
                    "bess_region": "Region",
                    "bess_power_mw": "Power [MW]",
                    "bess_duration_h": "Duration [h]",
                    "bess_energy_mwh": "Energy [MWh]",
                    "sweep_grid_value_score": "Score",
                    "renewable_dispatch_gain_mwh": "Renewable gain [MWh]",
                    "backup_reduction_mwh": "Backup reduction [MWh]",
                    "congestion_cost_reduction_eur": "Congestion relief [EUR]",
                },
            )
            story.extend(
                _make_longtable(
                    bess_table,
                    doc_width=doc.width,
                    title="Top BESS siting and sizing options",
                )
            )

    bottlenecks = _load_csv_if_exists(TABLE_DIR / "bottleneck_diagnostics.csv")
    if not bottlenecks.empty:
        bottleneck_cols = [
            c
            for c in [
                "scenario",
                "line",
                "max_utilisation_pct",
                "hours_above_threshold",
                "congestion_severity_pct_hours",
                "bottleneck_rank_score",
            ]
            if c in bottlenecks.columns
        ]
        bottleneck_table = _pdf_table(
            bottlenecks.sort_values("bottleneck_rank_score", ascending=False).head(12)[
                bottleneck_cols
            ],
            {
                "scenario": "Scenario",
                "line": "Line",
                "max_utilisation_pct": "Max util. [%]",
                "hours_above_threshold": "Hours > threshold",
                "congestion_severity_pct_hours": "Severity [%h]",
                "bottleneck_rank_score": "Score",
            },
        )
        story.extend(
            _make_longtable(
                bottleneck_table,
                doc_width=doc.width,
                title="Bottleneck diagnostics snapshot",
            )
        )

    n1_security = _load_csv_if_exists(TABLE_DIR / "n1_security_proxy.csv")
    if not n1_security.empty:
        n1_cols = [
            c
            for c in [
                "scenario",
                "outaged_line",
                "max_utilisation_pct",
                "hours_above_threshold",
                "n1_screening_risk_score",
                "screening_interpretation",
            ]
            if c in n1_security.columns
        ]
        n1_table = _pdf_table(
            n1_security.sort_values("n1_screening_risk_score", ascending=False).head(
                12
            )[n1_cols],
            {
                "scenario": "Scenario",
                "outaged_line": "Outaged line",
                "max_utilisation_pct": "Max util. [%]",
                "hours_above_threshold": "Hours > threshold",
                "n1_screening_risk_score": "Score",
                "screening_interpretation": "Interpretation",
            },
        )
        story.extend(
            _make_longtable(
                n1_table,
                doc_width=doc.width,
                title="N-1 screening proxy snapshot",
            )
        )

    bess_business = _load_csv_if_exists(TABLE_DIR / "bess_business_case.csv")
    if not bess_business.empty:
        business_cols = [
            c
            for c in [
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
            if c in bess_business.columns
        ]
        business_table = _pdf_table(
            bess_business.sort_values(
                "net_annual_value_proxy_eur_per_year",
                ascending=False,
            ).head(12)[business_cols],
            {
                "bess_region": "Region",
                "bess_power_mw": "Power [MW]",
                "bess_duration_h": "Duration [h]",
                "bess_capex_eur": "CAPEX [EUR]",
                "annualised_total_cost_eur_per_year": "Annual cost [EUR/yr]",
                "annualised_congestion_value_eur_per_year": "Annual value [EUR/yr]",
                "net_annual_value_proxy_eur_per_year": "Net value [EUR/yr]",
                "benefit_cost_ratio_proxy": "BCR",
                "simple_payback_years_proxy": "Payback [yr]",
            },
        )
        story.extend(
            _make_longtable(
                business_table,
                doc_width=doc.width,
                title="BESS business-case proxy snapshot",
            )
        )

    story.append(PageBreak())
    story.append(Paragraph("Figures", styles["section"]))
    figure_paths = [
        path
        for path in sorted(FIGURE_DIR.glob("*.png"))
        if path.name
        not in {"scenario_grid_value_score.png", "top_bottleneck_line_utilisation.png"}
    ]
    for figure_path in figure_paths:
        title = figure_path.stem.replace("_", " ").title()
        _append_figure_section(story, title, figure_path, styles, doc.width)
        story.append(PageBreak())

    markdown_reports = [
        report_path
        for report_path in sorted(REPORT_DIR.glob("*.md"))
        if report_path.name != "README.md"
    ]
    if markdown_reports:
        story.append(Paragraph("Generated report files", styles["section"]))
        report_inventory = pd.DataFrame(
            [
                {
                    "report": report_path.name,
                    "purpose": report_path.stem.replace("_", " ").title(),
                    "size_bytes": report_path.stat().st_size,
                }
                for report_path in markdown_reports
            ]
        )
        story.extend(
            _make_longtable(
                report_inventory,
                doc_width=doc.width,
                title="Markdown and narrative reports generated by the pipeline",
                col_widths=[doc.width * 0.32, doc.width * 0.48, doc.width * 0.20],
            )
        )
        story.append(
            Paragraph(
                "The full narrative content remains available in the repository outputs folder and in the embedded ZIP bundle.",
                styles["body"],
            )
        )
        story.append(Spacer(1, 0.12 * inch))

    story.append(Paragraph("File inventory", styles["section"]))
    inventory = bundle_manifest.copy()
    if not inventory.empty:
        inventory["category"] = inventory["path"].apply(
            lambda value: _report_asset_category(PROJECT_ROOT / value)
        )
        inventory = inventory.sort_values(["category", "path"]).reset_index(drop=True)
        story.extend(
            _make_longtable(
                inventory.rename(columns={"path": "file", "bytes": "size_bytes"})[
                    ["category", "file", "size_bytes"]
                ],
                doc_width=doc.width,
                title="Files included in the downloadable bundle",
                col_widths=[doc.width * 0.16, doc.width * 0.64, doc.width * 0.20],
            )
        )

    story.append(
        Paragraph(
            "The full machine-readable bundle is attached to this PDF as "
            "<b>pypsa_nl_grid_flexibility_report_bundle.zip</b>. "
            "That attachment contains the complete input, output, figure and report set.",
            styles["body"],
        )
    )

    doc.build(story)

    pdf_buffer = io.BytesIO()
    pdf_buffer.write(buffer.getvalue())
    pdf_buffer.seek(0)

    reader = PdfReader(pdf_buffer)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_attachment("pypsa_nl_grid_flexibility_report_bundle.zip", bundle_bytes)
    writer.add_metadata(
        {
            "/Title": "PyPSA-NL Grid Flexibility Report",
            "/Author": "Abhijith Sivaprasadan",
            "/Subject": "Netherlands-inspired grid flexibility portfolio report",
        }
    )
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def write_pdf_report(
    summary: pd.DataFrame,
    bess_summary: pd.DataFrame | None = None,
    validation: pd.DataFrame | None = None,
) -> Path:
    """Write the downloadable PDF report to disk."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_bytes = build_pdf_report_bytes(summary, bess_summary, validation)
    pdf_path = REPORT_DIR / "executive_grid_flexibility_report.pdf"
    pdf_path.write_bytes(pdf_bytes)
    return pdf_path


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
        "The dashboard also exposes the generated PDF report and the full ZIP bundle for download.",
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
