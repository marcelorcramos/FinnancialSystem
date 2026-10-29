"""Entry list behind a report, with the fixed data of test_reports (Phase 3)."""

from typing import Any

from httpx import AsyncClient

from tests.integration.helpers import ApiUser, new_user
from tests.integration.test_reports import fixed_today, make_book, report

__all__ = ["fixed_today"]


async def entries(client: AsyncClient, user: ApiUser, **params: Any) -> dict[str, Any]:
    response = await client.get("/api/v1/reports/entries", headers=user.headers, params=params)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def test_water_entries_in_the_last_6_months(client: AsyncClient) -> None:
    book = await make_book(client)
    body = await entries(
        client, book.user, period="last_6_months", label_ids=str(book.labels["Water"])
    )
    assert (body["start_month"], body["end_month"]) == ("2026-05", "2026-10")
    assert (body["total"], body["count"]) == ("180.00", 6)
    assert [e["month"] for e in body["entries"]] == [f"2026-{m:02d}" for m in range(10, 4, -1)]
    assert {(e["origin"], e["amount"]) for e in body["entries"]} == {
        ("initial_distribution", "30.00")
    }


async def test_transfer_legs_name_the_other_label_even_outside_the_filter(
    client: AsyncClient,
) -> None:
    book = await make_book(client)
    body = await entries(client, book.user, period="last_month", label_ids=str(book.labels["Food"]))
    assert body["total"] == "212.00"  # 200 allocated + 12 moved in from Savings
    transfer, allocation = body["entries"]  # newest first: the transfer is on the 10th
    assert (transfer["origin"], transfer["amount"]) == ("transfer_in", "12.00")
    assert transfer["counterpart_label_id"] == str(book.labels["Savings"])
    assert (allocation["origin"], allocation["counterpart_label_id"]) == (
        "initial_distribution",
        None,
    )


async def test_additions_carry_their_income_source(client: AsyncClient) -> None:
    book = await make_book(client)
    body = await entries(client, book.user, kinds="investment")
    assert (body["total"], body["count"]) == ("150.00", 2)
    addition = body["entries"][0]
    assert (addition["origin"], addition["source"], addition["month"]) == (
        "external_income",
        "Extra income",
        "2026-09",
    )


async def test_total_matches_the_summary_on_every_page(client: AsyncClient) -> None:
    book = await make_book(client)
    summary = await report(client, book.user)
    first = await entries(client, book.user, limit=10)
    rest = await entries(client, book.user, limit=10, offset=10)
    # 7 Water + Food + Savings + 2 transfer legs + Investments allocation and addition.
    assert (first["count"], len(first["entries"]), len(rest["entries"])) == (13, 10, 3)
    assert first["total"] == rest["total"] == summary["total"]
    ids = [e["id"] for e in first["entries"] + rest["entries"]]
    assert len(set(ids)) == 13
    dates = [e["occurred_on"] for e in first["entries"] + rest["entries"]]
    assert dates == sorted(dates, reverse=True)


async def test_deleted_entries_and_months_do_not_count(client: AsyncClient) -> None:
    book = await make_book(client)
    water = str(book.labels["Water"])
    october = await entries(client, book.user, period="last_month", label_ids=water)
    await client.delete(f"/api/v1/entries/{october['entries'][0]['id']}", headers=book.user.headers)
    september = await book.month(client, 9)
    await client.delete(f"/api/v1/months/{september}", headers=book.user.headers)

    body = await entries(client, book.user, period="last_6_months", label_ids=water)
    assert (body["total"], body["count"]) == ("120.00", 4)
    assert [e["month"] for e in body["entries"]] == ["2026-08", "2026-07", "2026-06", "2026-05"]


async def test_empty_account_and_page_limits(client: AsyncClient) -> None:
    user = await new_user(client)
    body = await entries(client, user)
    assert (body["total"], body["count"], body["entries"]) == ("0.00", 0, [])
    assert (body["limit"], body["offset"]) == (50, 0)
    for params in ({"limit": 0}, {"limit": 201}, {"offset": -1}):
        response = await client.get("/api/v1/reports/entries", headers=user.headers, params=params)
        assert response.status_code == 422, params


async def test_report_entries_are_isolated(client: AsyncClient) -> None:
    alice, bob = await make_book(client), await make_book(client)
    response = await client.get(
        "/api/v1/reports/entries",
        headers=bob.user.headers,
        params={"label_ids": str(alice.labels["Water"])},
    )
    assert response.status_code == 404
    body = await entries(client, bob.user)
    own = {str(label_id) for label_id in bob.labels.values()}
    assert body["count"] == 13
    assert {e["label_id"] for e in body["entries"]} <= own
