import uuid
from typing import Any

from httpx import AsyncClient

from app.domain.default_labels import DEFAULT_LABELS
from tests.integration.helpers import ApiUser, create_month, label_id, new_user


class Ctx:
    def __init__(self, user: ApiUser, month: dict[str, Any], labels: dict[str, uuid.UUID]):
        self.user, self.month, self.labels = user, month, labels
        self.url = f"/api/v1/months/{month['id']}"

    async def post(self, client: AsyncClient, path: str, body: dict[str, Any]) -> dict[str, Any]:
        response = await client.post(f"{self.url}{path}", headers=self.user.headers, json=body)
        assert response.status_code == 201, response.text
        result: dict[str, Any] = response.json()
        return result

    async def allocate(self, client: AsyncClient, label: str, amount: str) -> None:
        response = await client.put(
            f"{self.url}/allocations/{self.labels[label]}",
            headers=self.user.headers,
            json={"amount": amount},
        )
        assert response.status_code == 200

    async def summary(self, client: AsyncClient) -> dict[str, Any]:
        response = await client.get(f"{self.url}/summary", headers=self.user.headers)
        assert response.status_code == 200, response.text
        result: dict[str, Any] = response.json()
        return result


async def setup(client: AsyncClient) -> Ctx:
    user = await new_user(client)
    month = await create_month(client, user)
    names = ("Food", "Savings", "Investments", "Housing")
    return Ctx(user, month, {n: await label_id(client, user, n) for n in names})


def by_name(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["name"]: row for row in summary["labels"]}


async def test_full_month_summary(client: AsyncClient) -> None:
    """Salary split across labels, money added mid-month and a transfer between labels."""
    ctx = await setup(client)
    await ctx.post(
        client, "/incomes", {"source": "Salary", "amount": "1000.00", "received_on": "2026-10-01"}
    )
    await ctx.allocate(client, "Food", "200.00")
    await ctx.allocate(client, "Savings", "300.00")
    await ctx.allocate(client, "Investments", "100.00")
    await ctx.post(
        client,
        "/additions",
        {
            "label_id": str(ctx.labels["Investments"]),
            "amount": "50.00",
            "occurred_on": "2026-10-15",
        },
    )
    await ctx.post(
        client,
        "/transfers",
        {
            "from_label_id": str(ctx.labels["Savings"]),
            "to_label_id": str(ctx.labels["Food"]),
            "amount": "12.00",
            "occurred_on": "2026-10-20",
        },
    )

    summary = await ctx.summary(client)
    assert (summary["year"], summary["month"]) == (2026, 10)
    assert summary["income_total"] == "1050.00"
    assert summary["distributed"] == "650.00"
    assert summary["unallocated"] == "400.00"
    assert summary["over_allocated"] is False
    assert summary["month_total"] == "650.00"
    assert summary["by_kind"] == {
        "expense": "212.00",
        "saving": "288.00",
        "investment": "150.00",
    }

    rows = by_name(summary)
    food = rows["Food"]
    assert (food["allocation"], food["transfer_in"], food["total"]) == ("200.00", "12.00", "212.00")
    savings = rows["Savings"]
    assert (savings["allocation"], savings["transfer_out"], savings["total"]) == (
        "300.00",
        "12.00",
        "288.00",
    )
    investments = rows["Investments"]
    assert (investments["allocation"], investments["addition"], investments["total"]) == (
        "100.00",
        "50.00",
        "150.00",
    )
    assert rows["Housing"]["total"] == "0.00"


async def test_empty_month_lists_every_label_at_zero(client: AsyncClient) -> None:
    ctx = await setup(client)
    summary = await ctx.summary(client)
    assert (summary["income_total"], summary["unallocated"], summary["month_total"]) == (
        "0.00",
        "0.00",
        "0.00",
    )
    assert {row["name"] for row in summary["labels"]} == {t.name for t in DEFAULT_LABELS}
    assert all(row["total"] == "0.00" for row in summary["labels"])
    kinds = [row["kind"] for row in summary["labels"]]
    assert kinds == sorted(kinds, key=["expense", "saving", "investment"].index)


async def test_over_allocation_is_flagged_not_blocked(client: AsyncClient) -> None:
    ctx = await setup(client)
    await ctx.post(
        client, "/incomes", {"source": "Salary", "amount": "100.00", "received_on": "2026-10-01"}
    )
    await ctx.allocate(client, "Food", "300.00")
    summary = await ctx.summary(client)
    assert (summary["unallocated"], summary["over_allocated"]) == ("-200.00", True)


async def test_deleted_entries_and_incomes_are_ignored(client: AsyncClient) -> None:
    ctx = await setup(client)
    income = await ctx.post(
        client, "/incomes", {"source": "Salary", "amount": "500.00", "received_on": "2026-10-01"}
    )
    transfer = await ctx.post(
        client,
        "/transfers",
        {
            "from_label_id": str(ctx.labels["Savings"]),
            "to_label_id": str(ctx.labels["Food"]),
            "amount": "40.00",
            "occurred_on": "2026-10-20",
        },
    )
    await client.delete(f"/api/v1/incomes/{income['id']}", headers=ctx.user.headers)
    await client.delete(f"/api/v1/transfers/{transfer['transfer_id']}", headers=ctx.user.headers)

    summary = await ctx.summary(client)
    assert summary["income_total"] == "0.00"
    assert by_name(summary)["Food"]["total"] == "0.00"


async def test_archived_label_shows_only_with_movements(client: AsyncClient) -> None:
    ctx = await setup(client)
    await ctx.allocate(client, "Food", "80.00")
    for name in ("Food", "Housing"):
        await client.post(f"/api/v1/labels/{ctx.labels[name]}/archive", headers=ctx.user.headers)

    rows = by_name(await ctx.summary(client))
    assert rows["Food"]["archived"] is True
    assert rows["Food"]["total"] == "80.00"
    assert "Housing" not in rows


async def test_closed_month_summary_is_still_readable(client: AsyncClient) -> None:
    ctx = await setup(client)
    await ctx.allocate(client, "Food", "50.00")
    await client.post(f"{ctx.url}/close", headers=ctx.user.headers)
    summary = await ctx.summary(client)
    assert summary["closed_at"] is not None
    assert by_name(summary)["Food"]["total"] == "50.00"


async def test_users_cannot_read_each_others_summary(client: AsyncClient) -> None:
    alice, bob = await setup(client), await setup(client)
    response = await client.get(f"{alice.url}/summary", headers=bob.user.headers)
    assert response.status_code == 404
