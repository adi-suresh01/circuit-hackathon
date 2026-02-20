"""Digi-Key helper utilities."""

from __future__ import annotations


def normalize_digikey_account_id(account_id: str | None) -> str | None:
    """Normalize account id values so empty values do not emit headers."""
    if account_id is None:
        return None

    normalized = account_id.strip()
    if not normalized or normalized == "0":
        return None
    return normalized


def maybe_add_digikey_account_header(
    headers: dict[str, str],
    account_id: str | None,
) -> None:
    """Conditionally add the Digi-Key account id header when value is valid."""
    normalized = normalize_digikey_account_id(account_id)
    if normalized is not None:
        headers["X-DIGIKEY-Account-Id"] = normalized
