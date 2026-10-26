"""Reports by period and category with fixed data (Phase 3)."""

import uuid
from collections.abc import AsyncIterator
from datetime import date
from typing import Any

import pytest
from httpx import AsyncClient

from app.api.deps import get_today
from app.main import app
from tests.integration.helpers import ApiUser, create_month, label_id, new_user

TODAY = date(2026, 10, 26)


@pytest.fixture(autouse=True)
async def fixed_today(client: AsyncClient) -> AsyncIterator[None]:
    app.dependency_overrides[get_today] = lambda: TODAY
    yield
    app.dependency_overrides.pop(get_today, None)


class Book:
    """A user with months from April to October 2026 and known amounts."""

    def __init__(self, user: ApiUser, labels: dict[str, uuid.UUID]) -> None:
        self.user, self.labels, self.months = user, labels, {}

    async def month(self, client: AsyncClient, month: int) -> str:
        if month not in self.months:
            self.months[month] = (await create_month(client, self.user, 2026, month))["id"]
        return str(self.months[month])

    async def allocate(self, client: AsyncClient, month: int, label: str, amount: str) -> None:
        response = await client.put(
            f"/api/v1/months/{await self.month(client, month)}/allocations/{self.labels[label]}",
            headers=self.user.headers,
            json={"amount": amount},
        )
        assert response.status_code == 200, response.text

    async def transfer(
        self, client: AsyncClient, month: int, source: str, target: str, amount: str
    ) -> None:
        response = await client.post(
            f"/api/v1/months/{await self.month(client, month)}/transfers",
            headers=self.user.headers,
            json={
                "from_label_id": str(self.labels[source]),
                "to_label_id": str(self.labels[target]),
                "amount": amount,
                "occurred_on": f"2026-{month:02d}-10",
            },
        )
        assert response.status_code == 201, response.text

    async def add_money(self, client: AsyncClient, month: int, label: str, amount: str) -> None:
        response = await client.post(
            f"/api/v1/months/{await self.month(client, month)}/additions",
            headers=self.user.headers,
            json={
                "label_id": str(self.labels[label]),
                "amount": amount,
                "occurred_on": f"2026-{month:02d}-15",
            },
        )
        assert response.status_code == 201, response.text


async def make_book(client: AsyncClient) -> Book:
    user = await new_user(client)
    names = ("Water", "Food", "Savings", "Investments", "Housing")
    book = Book(user, {n: await label_id(client, user, n) for n in names})
    # Water: €30 every month from April to October; April falls outside the last 6 months.
    for month in range(4, 11):
        await book.allocate(client, month, "Water", "30.00")
    await book.allocate(client, 10, "Food", "200.00")
    await book.allocate(client, 10, "Savings", "300.00")
    await book.transfer(client, 10, "Savings", "Food", "12.00")
    await book.allocate(client, 8, "Investments", "100.00")
    await book.add_money(client, 9, "Investments", "50.00")
    return book


async def report(client: AsyncClient, user: ApiUser, **params: Any) -> dict[str, Any]:
    response = await client.get("/api/v1/reports/summary", headers=user.headers, params=params)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def rows(body: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["name"]: row for row in body["labels"]}


async def test_water_spending_in_the_last_6_months(client: AsyncClient) -> None:
    """Acceptance criterion: "water spending in the last 6 months" returns the right amount."""
    book = await make_book(client)
    body = await report(
        client, book.user, period="last_6_months", label_ids=str(book.labels["Water"])
    )
    assert (body["start_month"], body["end_month"]) == ("2026-05", "2026-10")
    assert body["total"] == "180.00"  # May..October, 6 x €30
    assert list(rows(body)) == ["Water"]


async def test_period_windows(client: AsyncClient) -> None:
    book = await make_book(client)
    water = str(book.labels["Water"])
    expected = {"last_month": "30.00", "last_6_months": "180.00", "last_12_months": "210.00"}
    for period, total in expected.items():
        body = await report(client, book.user, period=period, label_ids=water)
        assert body["total"] == total, period
    assert (await report(client, book.user, label_ids=water))["total"] == "210.00"  # all time


async def test_all_labels_in_the_current_month_include_transfers(client: AsyncClient) -> None:
    book = await make_book(client)
    body = await report(client, book.user, period="last_month")
    labels = rows(body)
    assert labels["Food"]["total"] == "212.00"
    assert labels["Savings"]["total"] == "288.00"
    assert labels["Water"]["total"] == "30.00"
    assert labels["Housing"]["total"] == "0.00"  # usable labels are listed even at zero
    assert body["total"] == "530.00"
    assert body["by_kind"] == {"expense": "242.00", "saving": "288.00", "investment": "0.00"}
    names = [row["name"] for row in body["labels"]]
    assert names[:3] == ["Savings", "Food", "Water"]  # largest total first


async def test_several_labels_combined(client: AsyncClient) -> None:
    book = await make_book(client)
    body = await report(
        client,
        book.user,
        period="last_6_months",
        label_ids=[str(book.labels["Food"]), str(book.labels["Investments"])],
    )
    assert set(rows(body)) == {"Food", "Investments"}
    assert rows(body)["Investments"]["allocation"] == "100.00"
    assert rows(body)["Investments"]["addition"] == "50.00"
    assert body["total"] == "362.00"  # Food 212 + Investments 150


async def test_kinds_combine_with_labels_as_a_union(client: AsyncClient) -> None:
    book = await make_book(client)
    body = await report(
        client,
        book.user,
        period="last_12_months",
        kinds="investment",
        label_ids=str(book.labels["Water"]),
    )
    assert set(rows(body)) == {"Water", "Investments"}
    assert body["by_kind"]["investment"] == "150.00"
    assert body["by_kind"]["expense"] == "210.00"


async def test_donut_shares(client: AsyncClient) -> None:
    book = await make_book(client)
    body = await report(client, book.user, period="last_month")
    shares = {name: row["share"] for name, row in rows(body).items() if row["share"] != "0.00"}
    # 530 distributed: Savings 288, Food 212, Water 30.
    assert shares == {"Savings": "54.34", "Food": "40.00", "Water": "5.66"}
    assert body["kind_shares"] == {"expense": "45.66", "saving": "54.34", "investment": "0.00"}


async def test_label_with_money_moved_out_has_no_slice(client: AsyncClient) -> None:
    book = await make_book(client)
    await book.transfer(client, 10, "Housing", "Food", "40.00")  # Housing goes to -40
    labels = rows(await report(client, book.user, period="last_month"))
    assert (labels["Housing"]["total"], labels["Housing"]["share"]) == ("-40.00", "0.00")


async def test_deleted_entries_and_months_do_not_count(client: AsyncClient) -> None:
    book = await make_book(client)
    water = str(book.labels["Water"])
    september = await book.month(client, 9)
    await client.delete(f"/api/v1/months/{september}", headers=book.user.headers)
    body = await report(client, book.user, period="last_6_months", label_ids=water)
    assert body["total"] == "150.00"


async def test_empty_account(client: AsyncClient) -> None:
    user = await new_user(client)
    body = await report(client, user, period="last_6_months")
    assert body["total"] == "0.00"
    assert all(row["share"] == "0.00" for row in body["labels"])
    assert body["reference_date"] == "2026-10-26"


async def test_invalid_filters(client: AsyncClient) -> None:
    user = await new_user(client)
    for params in ({"period": "last_7_days"}, {"kinds": "gift"}, {"label_ids": "nope"}):
        response = await client.get("/api/v1/reports/summary", headers=user.headers, params=params)
        assert response.status_code == 422, params


async def test_reports_are_isolated(client: AsyncClient) -> None:
    alice, bob = await make_book(client), await make_book(client)
    # Bob cannot filter by Alice's label, and Alice's money never shows in Bob's report.
    response = await client.get(
        "/api/v1/reports/summary",
        headers=bob.user.headers,
        params={"label_ids": str(alice.labels["Water"])},
    )
    assert response.status_code == 404
    body = await report(client, bob.user, period="last_month")
    assert body["total"] == "530.00"
