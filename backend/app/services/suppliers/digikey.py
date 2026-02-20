"""Digi-Key OAuth + Product Information v4 client."""

from __future__ import annotations

import asyncio
import time
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import HTTPException

from app.config import settings
from app.tracing import tracer


def _rate_limited_exception(
    response: httpx.Response,
    message_prefix: str = "Digi-Key API rate limited",
) -> HTTPException:
    retry_after = response.headers.get("retry-after")
    detail = message_prefix
    if retry_after:
        detail = f"{detail}; retry-after={retry_after}"
    return HTTPException(status_code=502, detail=detail)


class DigiKeyAuth:
    """2-legged OAuth token manager with in-memory cache."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        host: str,
        timeout_s: int,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._host = host
        self._timeout_s = timeout_s
        self._access_token: str | None = None
        self._expires_at_epoch_s: float = 0.0
        self._lock = asyncio.Lock()

    def _token_valid(self) -> bool:
        if not self._access_token:
            return False
        return time.time() < self._expires_at_epoch_s

    async def get_token(
        self,
        *,
        force_refresh: bool = False,
        bom_size: int | None = None,
    ) -> str:
        with tracer.trace("supplier.digikey.token") as span:
            span.set_tag("supplier", "digikey")
            span.set_tag("bom_size", bom_size or 0)
            span.set_tag("product_number", "")
            span.set_tag("requested_quantity", 0)

            if not force_refresh and self._token_valid():
                span.set_tag("cache_hit", True)
                span.set_tag("http.status_code", 200)
                return str(self._access_token)

            span.set_tag("cache_hit", False)
            async with self._lock:
                if not force_refresh and self._token_valid():
                    span.set_tag("cache_hit", True)
                    span.set_tag("http.status_code", 200)
                    return str(self._access_token)

                url = f"https://{self._host}/v1/oauth2/token"
                payload = {
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "grant_type": "client_credentials",
                }
                headers = {"Content-Type": "application/x-www-form-urlencoded"}

                try:
                    async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                        response = await client.post(url, data=payload, headers=headers)
                except httpx.RequestError as exc:
                    raise HTTPException(
                        status_code=502,
                        detail="Digi-Key token request failed",
                    ) from exc

                span.set_tag("http.status_code", response.status_code)

                if response.status_code == 429:
                    raise _rate_limited_exception(
                        response,
                        "Digi-Key token endpoint rate limited",
                    )
                if response.status_code >= 400:
                    raise HTTPException(
                        status_code=502,
                        detail=f"Digi-Key token request failed ({response.status_code})",
                    )

                try:
                    body = response.json()
                except ValueError as exc:
                    raise HTTPException(
                        status_code=502,
                        detail="Digi-Key token response was not valid JSON",
                    ) from exc

                access_token = body.get("access_token")
                expires_in_raw = body.get("expires_in", 300)
                try:
                    expires_in = int(expires_in_raw)
                except (TypeError, ValueError):
                    expires_in = 300

                if not isinstance(access_token, str) or not access_token.strip():
                    raise HTTPException(
                        status_code=502,
                        detail="Digi-Key token response missing access_token",
                    )

                self._access_token = access_token
                self._expires_at_epoch_s = time.time() + max(expires_in - 30, 30)
                return access_token


class DigiKeyClient:
    """Digi-Key Product Information v4 API client."""

    def __init__(self) -> None:
        self._host = settings.digikey_host()
        self._timeout_s = settings.digikey_http_timeout_s
        self._client_id = settings.digikey_client_id or ""
        self._account_id = settings.digikey_account_id

        if not self._client_id or not (settings.digikey_client_secret or "").strip():
            raise HTTPException(
                status_code=400,
                detail="Digi-Key credentials are not configured",
            )

        self._auth = DigiKeyAuth(
            client_id=self._client_id,
            client_secret=str(settings.digikey_client_secret),
            host=self._host,
            timeout_s=self._timeout_s,
        )
        self._client = httpx.AsyncClient(timeout=self._timeout_s)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "DigiKeyClient":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.aclose()

    def _build_headers(self, bearer_token: str) -> dict[str, str]:
        headers: dict[str, str] = {
            "X-DIGIKEY-Client-Id": self._client_id,
            "Authorization": f"Bearer {bearer_token}",
            "X-DIGIKEY-Locale-Site": settings.digikey_locale_site,
            "X-DIGIKEY-Locale-Language": settings.digikey_locale_language,
            "X-DIGIKEY-Locale-Currency": settings.digikey_locale_currency,
        }
        if self._account_id:
            headers["X-DIGIKEY-Account-Id"] = self._account_id
        return headers

    async def _request_with_token_retry(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str],
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        bom_size: int | None = None,
    ) -> httpx.Response:
        try:
            response = await self._client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_body,
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail="Digi-Key upstream request failed",
            ) from exc

        if response.status_code != 401:
            return response

        refreshed_token = await self._auth.get_token(
            force_refresh=True,
            bom_size=bom_size,
        )
        retry_headers = self._build_headers(refreshed_token)
        try:
            retry_response = await self._client.request(
                method=method,
                url=url,
                headers=retry_headers,
                params=params,
                json=json_body,
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail="Digi-Key upstream request retry failed",
            ) from exc
        return retry_response

    async def _request_json(
        self,
        *,
        span_name: str,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        bom_size: int | None = None,
        product_number: str | None = None,
        requested_quantity: int | None = None,
    ) -> dict[str, Any]:
        with tracer.trace(span_name) as span:
            span.set_tag("supplier", "digikey")
            span.set_tag("bom_size", bom_size or 0)
            span.set_tag("product_number", product_number or "")
            span.set_tag("requested_quantity", requested_quantity or 0)

            bearer_token = await self._auth.get_token(bom_size=bom_size)
            headers = self._build_headers(bearer_token)
            url = f"https://{self._host}{path}"
            response = await self._request_with_token_retry(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json_body=json_body,
                bom_size=bom_size,
            )

            span.set_tag("http.status_code", response.status_code)

            if response.status_code == 429:
                raise _rate_limited_exception(response)
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=502,
                    detail=f"Digi-Key API request failed ({response.status_code})",
                )

            try:
                parsed: dict[str, Any] = response.json()
            except ValueError as exc:
                raise HTTPException(
                    status_code=502,
                    detail="Digi-Key API response was not valid JSON",
                ) from exc
            return parsed

    async def keyword_search(
        self,
        keywords: str,
        limit: int = 5,
        offset: int = 0,
        *,
        bom_size: int | None = None,
    ) -> dict[str, Any]:
        body = {
            "Keywords": keywords,
            "Limit": limit,
            "Offset": offset,
        }
        return await self._request_json(
            span_name="supplier.digikey.keyword_search",
            method="POST",
            path="/products/v4/search/keyword",
            json_body=body,
            bom_size=bom_size,
        )

    async def product_pricing(
        self,
        product_number: str,
        in_stock: bool = True,
        exclude_marketplace: bool = True,
        limit: int = 5,
        offset: int = 0,
        *,
        bom_size: int | None = None,
    ) -> dict[str, Any]:
        encoded_product_number = quote(product_number, safe="")
        params = {
            "limit": limit,
            "offset": offset,
            "inStock": str(in_stock).lower(),
            "excludeMarketplace": str(exclude_marketplace).lower(),
        }
        return await self._request_json(
            span_name="supplier.digikey.product_pricing",
            method="GET",
            path=f"/products/v4/search/{encoded_product_number}/pricing",
            params=params,
            bom_size=bom_size,
            product_number=product_number,
        )

    async def pricing_by_quantity(
        self,
        product_number: str,
        requested_quantity: int,
        manufacturer_id: str | None = None,
        *,
        bom_size: int | None = None,
    ) -> dict[str, Any]:
        encoded_product_number = quote(product_number, safe="")
        params: dict[str, Any] | None = None
        if manufacturer_id:
            params = {"manufacturerId": manufacturer_id}

        return await self._request_json(
            span_name="supplier.digikey.pricing_by_quantity",
            method="GET",
            path=(
                f"/products/v4/search/{encoded_product_number}/pricingbyquantity/"
                f"{requested_quantity}"
            ),
            params=params,
            bom_size=bom_size,
            product_number=product_number,
            requested_quantity=requested_quantity,
        )
