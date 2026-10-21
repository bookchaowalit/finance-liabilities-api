"""What liabilities refuse: unknown kinds, oversize names, negative money, non-object metadata."""

from liability_helpers import LIABILITIES, create


def test_name_is_required(client, owner):
    response = client.post(LIABILITIES, headers=owner, json={"liability_type": "loan"})
    assert response.status_code == 422


def test_name_is_limited_to_200_characters(client, owner):
    assert create(client, owner, name="x" * 201).status_code == 422
    assert create(client, owner, name="y" * 200).status_code == 201


def test_liability_type_is_required(client, owner):
    response = client.post(LIABILITIES, headers=owner, json={"name": "Untyped"})
    assert response.status_code == 422


def test_liability_type_must_be_a_known_kind(client, owner):
    response = create(client, owner, name="Odd kind", liability_type="mortgage")
    assert response.status_code == 422


def test_every_listed_liability_type_is_accepted(client, owner):
    for kind in ("loan", "credit", "tax", "payable", "subscription", "other"):
        response = create(client, owner, name=f"Kind {kind}", liability_type=kind)
        assert response.status_code == 201, (kind, response.text)


def test_owner_scope_must_be_a_known_scope(client, owner):
    response = create(client, owner, name="Odd scope", owner_scope="family")
    assert response.status_code == 422


def test_status_must_be_a_known_status(client, owner):
    response = create(client, owner, name="Odd status", status="frozen")
    assert response.status_code == 422


def test_every_listed_status_is_accepted(client, owner):
    for status in ("planned", "active", "overdue", "settled", "cancelled"):
        response = create(client, owner, name=f"Status {status}", status=status)
        assert response.status_code == 201, (status, response.text)


def test_money_amounts_cannot_be_negative(client, owner):
    for field in ("principal_amount", "outstanding_amount", "minimum_payment"):
        refused = create(client, owner, name=f"Neg {field}", **{field: -1})
        assert refused.status_code == 422, field
        accepted = create(client, owner, name=f"Zero {field}", **{field: 0})
        assert accepted.status_code == 201, field


def test_interest_rate_cannot_be_negative(client, owner):
    refused = create(client, owner, name="Neg rate", interest_rate_percent=-0.1)
    assert refused.status_code == 422
    zero = create(client, owner, name="Zero rate", interest_rate_percent=0)
    assert zero.status_code == 201


def test_currency_code_is_at_most_12_characters(client, owner):
    assert create(client, owner, name="Long ccy", currency="C" * 13).status_code == 422
    assert create(client, owner, name="USD debt", currency="USD").status_code == 201


def test_due_date_must_be_a_real_calendar_date(client, owner):
    response = create(client, owner, name="Bad date", due_date="2026-02-30")
    assert response.status_code == 422


def test_account_id_must_be_a_whole_number(client, owner):
    response = create(client, owner, name="Bad account", account_id="abc")
    assert response.status_code == 422


def test_metadata_must_be_an_object(client, owner):
    for bad in (["not", "an", "object"], "text", 5):
        response = create(client, owner, name="Bad meta", metadata=bad)
        assert response.status_code == 422, bad
    assert create(client, owner, name="Good meta", metadata={"a": 1}).status_code == 201


def test_unknown_fields_are_refused(client, owner):
    response = create(client, owner, name="Extra", colour="red")
    assert response.status_code == 422
