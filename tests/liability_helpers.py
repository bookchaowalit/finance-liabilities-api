"""Shared helpers for the liabilities domain tests."""

from typing import Any

LIABILITIES = "/v1/liabilities"


def create(client: Any, owner: dict[str, str], **fields: Any) -> Any:
    return client.post(
        LIABILITIES,
        headers=owner,
        json={"name": "Debt", "liability_type": "loan", **fields},
    )
