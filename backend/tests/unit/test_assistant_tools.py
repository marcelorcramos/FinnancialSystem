import pytest

from app.domain.periods import MonthKey
from app.services.assistant_tools import MAX_MONTHS, TOOLS, ToolError, _json, _month, _range


def test_months_are_read_as_yyyy_mm() -> None:
    assert _month("2026-03") == MonthKey(2026, 3)
    for bad in ("2026-13", "2026-3", "March", ""):
        with pytest.raises(ToolError):
            _month(bad)


def test_ranges_are_ordered_and_limited() -> None:
    assert _range({"start_month": "2026-01", "end_month": "2026-02"}) == (
        MonthKey(2026, 1),
        MonthKey(2026, 2),
    )
    with pytest.raises(ToolError, match="must not be after"):
        _range({"start_month": "2026-03", "end_month": "2026-02"})
    with pytest.raises(ToolError, match=f"at most {MAX_MONTHS}"):
        _range({"start_month": "2020-01", "end_month": "2026-01"})


def test_tools_are_strict_and_read_only() -> None:
    names = [tool["name"] for tool in TOOLS]
    assert names == ["list_labels", "month_summary", "totals", "monthly_totals", "goals"]
    for tool in TOOLS:
        schema = tool["input_schema"]
        assert tool["strict"] is True
        assert schema["additionalProperties"] is False
        assert schema["required"] == list(schema["properties"])


def test_amounts_are_written_with_two_decimals() -> None:
    from decimal import Decimal

    assert _json({"total": Decimal("50")}) == '{"total": "50.00"}'
