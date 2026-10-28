"""Time series per label (line chart) with the fixed data of test_reports (Phase 3)."""

from typing import Any

from httpx import AsyncClient

from tests.integration.helpers import ApiUser, new_user
from tests.integration.test_reports import fixed_today, make_book

__all__ = ["fixed_today"]


async def series(client: AsyncClient, user: ApiUser, **params: Any) -> dict[str, Any]:
    response = await client.get("/api/v1/reports/series", headers=user.headers, params=params)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def points(body: dict[str, Any], name: str) -> list[str]:
    label = next(row for row in body["labels"] if row["name"] == name)
    return [point["total"] for point in label["points"]]


async def test_water_month_by_month_in_the_last_6_months(client: AsyncClient) -> None:
    book = await make_book(client)
    body = await series(
        client, book.user, period="last_6_months", label_ids=str(book.labels["Water"])
    )
    assert body["months"] == ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]
    assert points(body, "Water") == ["30.00"] * 6
    assert body["labels"][0]["total"] == "180.00"  # same as the summary report


async def test_months_without_money_are_zero_and_transfers_count(client: AsyncClient) -> None:
    book = await make_book(client)
    body = await series(
        client,
        book.user,
        period="last_6_months",
        label_ids=[str(book.labels["Food"]), str(book.labels["Investments"])],
    )
    assert points(body, "Food") == ["0.00"] * 5 + ["212.00"]
    assert points(body, "Investments") == ["0.00", "0.00", "0.00", "100.00", "50.00", "0.00"]
    assert [p["total"] for p in body["totals"]] == [
        "0.00", "0.00", "0.00", "100.00", "50.00", "212.00"
    ]  # fmt: skip


async def test_all_time_starts_at_the_first_month_with_money(client: AsyncClient) -> None:
    book = await make_book(client)
    body = await series(client, book.user)
    assert (body["start_month"], body["end_month"]) == ("2026-04", "2026-10")
    assert len(body["months"]) == 7
    assert [row["name"] for row in body["labels"]][:2] == ["Savings", "Food"]
    assert points(body, "Savings") == ["0.00"] * 6 + ["288.00"]


async def test_deleted_months_do_not_count(client: AsyncClient) -> None:
    book = await make_book(client)
    september = await book.month(client, 9)
    await client.delete(f"/api/v1/months/{september}", headers=book.user.headers)
    body = await series(
        client, book.user, period="last_6_months", label_ids=str(book.labels["Water"])
    )
    assert points(body, "Water") == ["30.00"] * 4 + ["0.00", "30.00"]


async def test_empty_account_has_no_months(client: AsyncClient) -> None:
    user = await new_user(client)
    body = await series(client, user)
    assert (body["months"], body["totals"], body["start_month"]) == ([], [], None)
    assert all(row["points"] == [] for row in body["labels"])


async def test_series_is_isolated(client: AsyncClient) -> None:
    alice, bob = await make_book(client), await make_book(client)
    response = await client.get(
        "/api/v1/reports/series",
        headers=bob.user.headers,
        params={"label_ids": str(alice.labels["Water"])},
    )
    assert response.status_code == 404
    body = await series(client, bob.user, period="last_month")
    assert [p["total"] for p in body["totals"]] == ["530.00"]
