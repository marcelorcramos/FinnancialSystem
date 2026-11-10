import csv
import io
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from app.domain.enums import LabelKind, MovementType
from app.schemas.report import ReportEntry
from app.services.export_files import LabelInfo, euros, report_csv

FOOD = uuid.uuid4()


def entry(note: str) -> ReportEntry:
    return ReportEntry(
        id=uuid.uuid4(),
        month_id=uuid.uuid4(),
        label_id=FOOD,
        amount=Decimal("5.00"),
        movement_type=MovementType.ALLOCATION,
        transfer_id=None,
        income_id=None,
        occurred_on=date(2026, 10, 1),
        note=note,
        created_at=datetime.now(UTC),
        origin="initial_distribution",
        month="2026-10",
    )


def test_notes_cannot_run_as_spreadsheet_formulas() -> None:
    content = report_csv(
        [entry('=HYPERLINK("http://evil")'), entry("-2+3"), entry("plain")],
        {FOOD: LabelInfo("Food", LabelKind.EXPENSE)},
    )
    notes = [row["Note"] for row in csv.DictReader(io.StringIO(content.decode("utf-8-sig")))]
    assert notes == ['\'=HYPERLINK("http://evil")', "'-2+3", "plain"]


def test_euros() -> None:
    assert euros(Decimal("1234.5")) == "€1,234.50"
    assert euros(Decimal("-12")) == "-€12.00"
