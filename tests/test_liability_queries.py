"""Listing, grouping and the lifecycle of a liability."""

from liability_helpers import LIABILITIES, create


def test_list_filters_by_liability_type(client, owner):
    create(client, owner, name="Mortgage-like", liability_type="loan")
    create(client, owner, name="VAT due", liability_type="tax")
    listed = client.get(LIABILITIES, headers=owner, params={"liability_type": "tax"})
    assert listed.status_code == 200, listed.text
    assert {item["liability_type"] for item in listed.json()["items"]} == {"tax"}


def test_list_filters_by_several_statuses_at_once(client, owner):
    create(client, owner, name="Overdue one", status="overdue")
    create(client, owner, name="Settled one", status="settled")
    create(client, owner, name="Planned one", status="planned")
    listed = client.get(
        LIABILITIES,
        headers=owner,
        params=[("status", "overdue"), ("status", "settled")],
    )
    assert listed.status_code == 200, listed.text
    assert {item["status"] for item in listed.json()["items"]} == {"overdue", "settled"}


def test_list_filters_by_owner_scope(client, owner):
    create(client, owner, name="Client debt", owner_scope="client")
    create(client, owner, name="Mine")
    listed = client.get(LIABILITIES, headers=owner, params={"owner_scope": "client"})
    assert listed.status_code == 200, listed.text
    assert {item["owner_scope"] for item in listed.json()["items"]} == {"client"}


def test_list_filter_with_an_unknown_status_is_refused(client, owner):
    listed = client.get(LIABILITIES, headers=owner, params={"status": "frozen"})
    assert listed.status_code == 422


def test_list_refuses_a_field_that_is_not_a_filter(client, owner):
    listed = client.get(LIABILITIES, headers=owner, params={"account_id": "1"})
    assert listed.status_code == 422


def test_liabilities_are_listed_in_creation_order(client, owner):
    ids = [create(client, owner, name=f"Order {n}").json()["id"] for n in range(3)]
    listed = client.get(LIABILITIES, headers=owner).json()["items"]
    assert [item["id"] for item in listed] == sorted(ids)


def test_stats_count_liabilities_per_status(client, owner):
    create(client, owner, name="Active one")
    create(client, owner, name="Overdue one", status="overdue")
    stats = client.get(
        f"{LIABILITIES}/stats", headers=owner, params={"group_by": "status"}
    )
    assert stats.status_code == 200, stats.text
    groups = stats.json()["groups"]
    assert groups["active"] >= 1
    assert groups["overdue"] >= 1


def test_stats_count_liabilities_per_type(client, owner):
    create(client, owner, name="Supplier bill", liability_type="payable")
    stats = client.get(
        f"{LIABILITIES}/stats", headers=owner, params={"group_by": "liability_type"}
    )
    assert stats.status_code == 200, stats.text
    assert stats.json()["groups"]["payable"] == 1


def test_stats_refuse_a_field_that_is_not_a_filter(client, owner):
    stats = client.get(
        f"{LIABILITIES}/stats", headers=owner, params={"group_by": "due_date"}
    )
    assert stats.status_code == 422


def test_paying_down_a_liability_bumps_its_version(client, owner):
    liability = create(client, owner, name="Paying", outstanding_amount=1000).json()
    paid = client.patch(
        f"{LIABILITIES}/{liability['id']}",
        headers=owner,
        json={"outstanding_amount": 750},
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["outstanding_amount"] == 750
    assert paid.json()["version"] == 2


def test_settling_a_liability_keeps_its_history(client, owner):
    liability = create(
        client, owner, name="Old loan", principal_amount=500, due_date="2026-09-30"
    ).json()
    settled = client.patch(
        f"{LIABILITIES}/{liability['id']}",
        headers=owner,
        json={"status": "settled", "outstanding_amount": 0},
    )
    assert settled.status_code == 200, settled.text
    assert settled.json()["status"] == "settled"
    assert settled.json()["principal_amount"] == 500
    assert settled.json()["due_date"] == "2026-09-30"


def test_a_patch_that_changes_nothing_keeps_the_version(client, owner):
    liability = create(
        client, owner, name="Stable", metadata={"a": 1}, minimum_payment=10
    ).json()
    same = client.patch(
        f"{LIABILITIES}/{liability['id']}",
        headers=owner,
        json={"name": "Stable", "metadata": {"a": 1}, "minimum_payment": 10},
    )
    assert same.status_code == 200, same.text
    assert same.json()["version"] == 1


def test_a_stale_expected_version_is_refused(client, owner):
    liability = create(client, owner, name="Versioned").json()
    path = f"{LIABILITIES}/{liability['id']}"
    assert client.patch(path, headers=owner, json={"notes": "a"}).status_code == 200
    stale = client.patch(
        path, headers=owner, json={"notes": "b", "expected_version": 1}
    )
    assert stale.status_code == 409


def test_a_negative_amount_is_refused_on_update(client, owner):
    liability = create(client, owner, name="Keep amount", outstanding_amount=75).json()
    path = f"{LIABILITIES}/{liability['id']}"
    refused = client.patch(path, headers=owner, json={"outstanding_amount": -5})
    assert refused.status_code == 422
    assert client.get(path, headers=owner).json()["outstanding_amount"] == 75


def test_a_required_field_cannot_be_cleared(client, owner):
    liability = create(client, owner, name="Needs type").json()
    refused = client.patch(
        f"{LIABILITIES}/{liability['id']}", headers=owner, json={"liability_type": None}
    )
    assert refused.status_code == 422


def test_deleting_a_liability_removes_it(client, owner):
    liability = create(client, owner, name="Short lived").json()
    path = f"{LIABILITIES}/{liability['id']}"
    assert client.delete(path, headers=owner).status_code == 204
    assert client.get(path, headers=owner).status_code == 404
    assert client.delete(path, headers=owner).status_code == 404
