"""Runtime check for Digi-Key optional account-id header behavior."""

from __future__ import annotations

from app.utils.digikey import maybe_add_digikey_account_header


def _build_headers(account_id: str | None) -> dict[str, str]:
    headers = {"X-DIGIKEY-Client-Id": "demo"}
    maybe_add_digikey_account_header(headers, account_id)
    return headers


def main() -> None:
    for candidate in [None, "", "   ", "0", " 0 "]:
        headers = _build_headers(candidate)
        assert "X-DIGIKEY-Account-Id" not in headers, (
            f"account header must be omitted for value={candidate!r}"
        )

    headers = _build_headers("12345")
    assert headers.get("X-DIGIKEY-Account-Id") == "12345", (
        "account header should be included for non-empty, non-zero values"
    )

    print("OK: Digi-Key account header omission/inclusion behavior is correct.")


if __name__ == "__main__":
    main()
