"""Builds the export files: report CSV and PDF, and the account's data ZIP.

Pure functions over data already read and checked by services/exports.py.
"""

import csv
import io
import json
import uuid
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.domain.enums import LabelKind, MovementType
from app.domain.periods import Period
from app.schemas.report import ReportEntry, ReportSummary

MOVEMENTS = {
    MovementType.ALLOCATION: "Allocation",
    MovementType.ADDITION: "Addition",
    MovementType.TRANSFER_IN: "Transfer in",
    MovementType.TRANSFER_OUT: "Transfer out",
}
PERIODS = {
    Period.LAST_MONTH: "This month",
    Period.LAST_6_MONTHS: "Last 6 months",
    Period.LAST_12_MONTHS: "Last 12 months",
    Period.ALL: "All time",
}
KINDS = {LabelKind.EXPENSE: "Spent", LabelKind.SAVING: "Saved", LabelKind.INVESTMENT: "Invested"}
CSV_HEADER = [
    "Month",
    "Date",
    "Label",
    "Kind",
    "Movement",
    "Amount",
    "Signed amount",
    "Other label",
    "Source",
    "Note",
]


@dataclass(frozen=True, slots=True)
class LabelInfo:
    name: str
    kind: LabelKind


def signed(entry: ReportEntry) -> Decimal:
    """The entry's effect on its label: money moved out counts as negative."""
    return -entry.amount if entry.movement_type is MovementType.TRANSFER_OUT else entry.amount


def euros(amount: Decimal) -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}€{abs(amount):,.2f}"


def report_csv(entries: Sequence[ReportEntry], labels: dict[uuid.UUID, LabelInfo]) -> bytes:
    """One row per entry, newest first. UTF-8 with a BOM so spreadsheets read the € signs."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(CSV_HEADER)
    for entry in entries:
        label = labels[entry.label_id]
        other = labels.get(entry.counterpart_label_id) if entry.counterpart_label_id else None
        writer.writerow(
            [
                entry.month,
                entry.occurred_on.isoformat(),
                label.name,
                label.kind.value,
                MOVEMENTS[entry.movement_type],
                f"{entry.amount:.2f}",
                f"{signed(entry):.2f}",
                other.name if other else "",
                entry.source or "",
                _safe_cell(entry.note or ""),
            ]
        )
    return ("﻿" + buffer.getvalue()).encode()


def _safe_cell(text: str) -> str:
    """Notes are user text: keep spreadsheets from running them as formulas."""
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def report_pdf(
    summary: ReportSummary,
    entries: Sequence[ReportEntry],
    labels: dict[uuid.UUID, LabelInfo],
    generated_at: datetime | None = None,
) -> bytes:
    generated_at = generated_at or datetime.now(UTC)
    styles = getSampleStyleSheet()
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title="FinnancialSystem report",
        author="FinnancialSystem",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    window = (
        f"{summary.start_month} to {summary.end_month}"
        if summary.start_month
        else "since the first record"
    )
    story: list[Any] = [
        Paragraph("FinnancialSystem report", styles["Title"]),
        Paragraph(
            f"{PERIODS[summary.period]} ({window}). "
            f"Generated on {generated_at:%Y-%m-%d %H:%M} UTC.",
            styles["Normal"],
        ),
        Spacer(1, 6 * mm),
        Paragraph("Totals", styles["Heading2"]),
        _table(
            [["", "Amount"]]
            + [[KINDS[kind], euros(amount)] for kind, amount in summary.by_kind.items()]
            + [["Total", euros(summary.total)]],
            widths=[60 * mm, 40 * mm],
            bold_last=True,
        ),
        Spacer(1, 6 * mm),
        Paragraph("Labels", styles["Heading2"]),
        _table(
            [["Label", "Kind", "Total", "Share"]]
            + [
                [row.name, row.kind.value, euros(row.total), f"{row.share}%"]
                for row in summary.labels
            ],
            widths=[70 * mm, 30 * mm, 40 * mm, 30 * mm],
        ),
        Spacer(1, 6 * mm),
        Paragraph(f"Entries ({len(entries)})", styles["Heading2"]),
    ]
    if entries:
        story.append(
            _table(
                [["Date", "Label", "Movement", "Amount", "Note"]]
                + [
                    [
                        entry.occurred_on.isoformat(),
                        labels[entry.label_id].name,
                        MOVEMENTS[entry.movement_type],
                        euros(signed(entry)),
                        Paragraph(_escape((entry.note or "")[:120]), styles["BodyText"]),
                    ]
                    for entry in entries
                ],
                widths=[24 * mm, 40 * mm, 26 * mm, 28 * mm, 56 * mm],
            )
        )
    else:
        story.append(Paragraph("No entries match these filters.", styles["Normal"]))
    document.build(story)
    return buffer.getvalue()


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _table(rows: list[list[Any]], widths: list[float], bold_last: bool = False) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1)
    style = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.black),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F4F6")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    if bold_last:
        style.append(("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"))
    table.setStyle(TableStyle(style))
    return table


def account_zip(data: dict[str, Any], files: Sequence[tuple[str, bytes]]) -> bytes:
    """data.json with every record, plus the receipt files under receipts/."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("data.json", json.dumps(data, indent=2, ensure_ascii=False))
        archive.writestr(
            "README.txt",
            "Your FinnancialSystem data.\n\n"
            "data.json holds every record of your account, deleted ones included "
            "(they have a deleted_at date). Amounts are in euros.\n"
            "receipts/ holds the files you attached, named <id>-<file name>.\n",
        )
        for name, content in files:
            archive.writestr(f"receipts/{name}", content)
    return buffer.getvalue()
