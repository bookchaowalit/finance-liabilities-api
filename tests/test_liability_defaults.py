"""Defaults, uniqueness and imports of a liability."""

from liability_helpers import LIABILITIES, create


def test_new_liability_defaults_to_personal_active_thb(client, owner):
    response = create(client, owner, name="Car loan")
    assert response.status_code == 201, response.text
    liability = response.json()
    assert liability["scope"] == ""
    assert liability["status"] == "active"
    assert liability["currency"] == "THB"
    assert liability["version"] == 1


def test_optional_amounts_start_empty(client, owner):
    liability = create(client, owner, name="Open ended").json()
    for field in (
        "account_id",
        "principal_amount",
        "outstanding_amount",
        "minimum_payment",
        "interest_rate_percent",
        "due_date",
        "metadata",
    ):
        assert liability[field] is None, field


def test_amounts_keep_their_decimal_value(client, owner):
    liability = create(
        client,
        owner,
        name="Decimals",
        principal_amount=100000.5,
        outstanding_amount=87500.25,
        minimum_payment=1999.99,
        interest_rate_percent=6.75,
    ).json()
    assert liability["principal_amount"] == "100000.5000"
    assert liability["outstanding_amount"] == "87500.2500"
    assert liability["minimum_payment"] == "1999.9900"
    assert liability["interest_rate_percent"] == "6.7500000000"


def test_account_id_round_trips_when_the_reference_is_trusted(client, owner):
    # The harness trusts cross-service ids; SPEC-006 checks are in tests/test_cross_references.py.
    liability = create(client, owner, name="Paid from", account_id=424242)
    assert liability.status_code == 201, liability.text
    assert liability.json()["account_id"] == 424242


def test_two_liabilities_may_share_a_name(client, owner):
    assert create(client, owner, name="Twin").status_code == 201
    assert create(client, owner, name="Twin").status_code == 201


def test_metadata_keeps_its_object(client, owner):
    meta = {"lender": "Bank A", "terms": {"months": 48}, "tags": ["car", "secured"]}
    liability = create(client, owner, name="With meta", metadata=meta).json()
    assert liability["metadata"] == meta


def test_an_import_keeps_the_old_id(client, owner):
    imported = create(client, owner, name="Imported", legacy_id=2626)
    assert imported.status_code == 201, imported.text
    assert imported.json()["id"] == 2626
    assert imported.json()["legacy_id"] == 2626
    found = client.get(f"{LIABILITIES}/legacy/2626", headers=owner)
    assert found.status_code == 200, found.text
    assert found.json()["name"] == "Imported"
    assert create(client, owner, name="Again", legacy_id=2626).status_code == 409
