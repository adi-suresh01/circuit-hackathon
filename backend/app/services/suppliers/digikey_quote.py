"""Quote-building helpers using Digi-Key supplier APIs."""

from __future__ import annotations

from uuid import uuid4
from typing import Any

from app.models import BomItem, QuoteLineItem, QuoteResponse, SupplierOffer
from app.services.suppliers.digikey import DigiKeyClient


def _first_present(data: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


def _safe_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    if isinstance(value, dict):
        nested = _first_present(
            value,
            ["Amount", "amount", "Value", "value", "Price", "UnitPrice", "ExtendedPrice"],
        )
        return _as_float(nested)
    return None


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if not cleaned:
            return None
        try:
            return int(float(cleaned))
        except ValueError:
            return None
    if isinstance(value, dict):
        nested = _first_present(value, ["Value", "value", "Amount", "amount"])
        return _as_int(nested)
    return None


def _as_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return None


def _listify(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [entry for entry in value if isinstance(entry, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def build_keyword(bom_item: BomItem) -> str:
    package = bom_item.package or ""
    return " ".join(part for part in [bom_item.value, package, bom_item.type] if part).strip()


def _extract_options(
    pricing_by_qty_response: dict[str, Any],
    product: dict[str, Any],
) -> list[dict[str, Any]]:
    my_options = _listify(pricing_by_qty_response.get("MyPricingOptions")) or _listify(
        product.get("MyPricingOptions")
    )
    std_options = _listify(pricing_by_qty_response.get("StandardPricingOptions")) or _listify(
        product.get("StandardPricingOptions")
    )
    fallback_options = _listify(pricing_by_qty_response.get("PricingOptions")) or _listify(
        product.get("PricingOptions")
    )

    if my_options:
        return my_options
    if std_options:
        return std_options
    return fallback_options


def _option_name(option: dict[str, Any]) -> str:
    name = _first_present(
        option,
        [
            "Name",
            "PricingOptionName",
            "PricingOptionType",
            "OptionType",
            "PriceBreakName",
        ],
    )
    return str(name).strip().lower() if name is not None else ""


def _option_unit_price(option: dict[str, Any]) -> float | None:
    return _as_float(
        _first_present(
            option,
            ["UnitPrice", "Price", "unitPrice", "unit_price"],
        )
    )


def _option_extended_price(
    option: dict[str, Any],
    requested_quantity: int | None,
) -> float | None:
    extended_price = _as_float(
        _first_present(
            option,
            ["ExtendedPrice", "TotalPrice", "extendedPrice", "extended_price"],
        )
    )
    if extended_price is not None:
        return extended_price

    unit_price = _option_unit_price(option)
    quantity = _as_int(
        _first_present(
            option,
            ["QuantityPriced", "BreakQuantity", "Quantity", "RequestedQuantity"],
        )
    )
    if quantity is None:
        quantity = requested_quantity
    if unit_price is None or quantity is None:
        return None
    return float(unit_price * quantity)


def choose_best_offer(pricing_by_qty_response: dict[str, Any]) -> SupplierOffer:
    product = pricing_by_qty_response.get("Product")
    if not isinstance(product, dict):
        product = pricing_by_qty_response

    requested_quantity = _as_int(
        _first_present(pricing_by_qty_response, ["RequestedQuantity", "requestedQuantity"])
    )
    options = _extract_options(pricing_by_qty_response, product)

    chosen_option: dict[str, Any] | None = None
    for option in options:
        if _option_name(option) == "exact":
            chosen_option = option
            break

    if chosen_option is None and options:
        chosen_option = min(
            options,
            key=lambda option: _option_extended_price(option, requested_quantity)
            if _option_extended_price(option, requested_quantity) is not None
            else float("inf"),
        )

    unit_price = _option_unit_price(chosen_option) if chosen_option else None
    extended_price = (
        _option_extended_price(chosen_option, requested_quantity) if chosen_option else None
    )
    quantity_priced = (
        _as_int(
            _first_present(
                chosen_option,
                ["QuantityPriced", "BreakQuantity", "Quantity", "RequestedQuantity"],
            )
        )
        if chosen_option
        else requested_quantity
    )

    manufacturer_obj = product.get("Manufacturer")
    manufacturer = None
    if isinstance(manufacturer_obj, dict):
        manufacturer = _safe_str(
            _first_present(manufacturer_obj, ["Name", "name", "Value", "value"])
        )
    if manufacturer is None:
        manufacturer = _safe_str(_first_present(product, ["ManufacturerName", "Manufacturer"]))

    currency = _safe_str(
        _first_present(
            pricing_by_qty_response,
            ["Currency", "currency", "SearchLocaleCurrency"],
        )
    ) or _safe_str(_first_present(product, ["Currency", "currency"]))

    return SupplierOffer(
        supplier="digikey",
        digikey_product_number=_safe_str(
            _first_present(
                product,
                [
                    "DigiKeyProductNumber",
                    "DigiKeyPartNumber",
                    "ProductNumber",
                ],
            )
        ),
        manufacturer_part_number=_safe_str(
            _first_present(
                product,
                ["ManufacturerProductNumber", "ManufacturerPartNumber", "Mpn"],
            )
        ),
        manufacturer=manufacturer,
        description=_safe_str(
            _first_present(product, ["Description", "ProductDescription", "DetailedDescription"])
        ),
        currency=currency,
        unit_price=unit_price,
        extended_price=extended_price,
        quantity_priced=quantity_priced,
        quantity_available=_as_int(
            _first_present(product, ["QuantityAvailable", "quantityAvailable", "StockQuantity"])
        ),
        marketplace=_as_bool(
            _first_present(
                product,
                ["Marketplace", "IsMarketplace", "IsMarketPlace", "MarketplaceProduct"],
            )
        ),
        source="pricingbyquantity",
        url=_safe_str(_first_present(product, ["ProductUrl", "ProductDetailUrl", "Url"])),
    )


def _extract_keyword_candidates(
    keyword_response: dict[str, Any],
    *,
    exclude_marketplace: bool,
) -> list[dict[str, Any]]:
    products = _listify(keyword_response.get("Products"))
    if not products:
        products = _listify(keyword_response.get("products"))

    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for product in products:
        product_number = _safe_str(
            _first_present(
                product,
                [
                    "DigiKeyProductNumber",
                    "DigiKeyPartNumber",
                    "ProductNumber",
                ],
            )
        )
        if product_number is None or product_number in seen:
            continue

        marketplace = _as_bool(
            _first_present(
                product,
                ["Marketplace", "IsMarketplace", "IsMarketPlace", "MarketplaceProduct"],
            )
        )
        if exclude_marketplace and marketplace is True:
            continue

        manufacturer_obj = product.get("Manufacturer")
        manufacturer = None
        manufacturer_id = None
        if isinstance(manufacturer_obj, dict):
            manufacturer = _safe_str(
                _first_present(manufacturer_obj, ["Name", "name", "Value", "value"])
            )
            manufacturer_id = _safe_str(
                _first_present(manufacturer_obj, ["Id", "id", "ManufacturerId"])
            )
        if manufacturer is None:
            manufacturer = _safe_str(_first_present(product, ["ManufacturerName"]))
        if manufacturer_id is None:
            manufacturer_id = _safe_str(_first_present(product, ["ManufacturerId"]))

        seen.add(product_number)
        candidates.append(
            {
                "digikey_product_number": product_number,
                "manufacturer_part_number": _safe_str(
                    _first_present(
                        product,
                        ["ManufacturerProductNumber", "ManufacturerPartNumber", "Mpn"],
                    )
                ),
                "manufacturer": manufacturer,
                "manufacturer_id": manufacturer_id,
                "description": _safe_str(
                    _first_present(
                        product,
                        ["Description", "ProductDescription", "DetailedDescription"],
                    )
                ),
                "quantity_available": _as_int(
                    _first_present(
                        product, ["QuantityAvailable", "quantityAvailable", "StockQuantity"]
                    )
                ),
                "marketplace": marketplace,
                "url": _safe_str(
                    _first_present(product, ["ProductUrl", "ProductDetailUrl", "Url"])
                ),
            }
        )
    return candidates


def _merge_candidate_defaults(
    offer: SupplierOffer,
    candidate: dict[str, Any],
) -> SupplierOffer:
    return offer.model_copy(
        update={
            "digikey_product_number": offer.digikey_product_number
            or candidate.get("digikey_product_number"),
            "manufacturer_part_number": offer.manufacturer_part_number
            or candidate.get("manufacturer_part_number"),
            "manufacturer": offer.manufacturer or candidate.get("manufacturer"),
            "description": offer.description or candidate.get("description"),
            "quantity_available": offer.quantity_available
            if offer.quantity_available is not None
            else candidate.get("quantity_available"),
            "marketplace": offer.marketplace
            if offer.marketplace is not None
            else candidate.get("marketplace"),
            "url": offer.url or candidate.get("url"),
        }
    )


def _offer_sort_key(offer: SupplierOffer, requested_qty: int) -> tuple[int, float, float]:
    in_stock_rank = 0
    if offer.quantity_available is not None and offer.quantity_available < requested_qty:
        in_stock_rank = 1

    ext = offer.extended_price if offer.extended_price is not None else float("inf")
    unit = offer.unit_price if offer.unit_price is not None else float("inf")
    return in_stock_rank, ext, unit


def _choose_line_offer(
    offers: list[SupplierOffer],
    *,
    prefer_in_stock: bool,
    requested_qty: int,
) -> SupplierOffer | None:
    if not offers:
        return None

    if prefer_in_stock:
        in_stock_offers = [
            offer
            for offer in offers
            if offer.quantity_available is None or offer.quantity_available >= requested_qty
        ]
        if in_stock_offers:
            return min(in_stock_offers, key=lambda offer: _offer_sort_key(offer, requested_qty))

    return min(offers, key=lambda offer: _offer_sort_key(offer, requested_qty))


async def quote_bom(
    bom: list[BomItem],
    prefer_in_stock: bool,
    exclude_marketplace: bool,
) -> QuoteResponse:
    request_id = str(uuid4())
    bom_size = len(bom)
    lines: list[QuoteLineItem] = []
    warnings: list[str] = []

    async with DigiKeyClient() as client:
        for bom_item in bom:
            notes: list[str] = []
            keyword = build_keyword(bom_item)

            keyword_response = await client.keyword_search(
                keywords=keyword,
                limit=3,
                offset=0,
                bom_size=bom_size,
            )

            candidates = _extract_keyword_candidates(
                keyword_response,
                exclude_marketplace=exclude_marketplace,
            )[:2]

            offers: list[SupplierOffer] = []
            for candidate in candidates:
                product_number = candidate.get("digikey_product_number")
                if not isinstance(product_number, str) or not product_number:
                    continue

                pricing_response = await client.pricing_by_quantity(
                    product_number=product_number,
                    requested_quantity=max(bom_item.qty, 1),
                    manufacturer_id=candidate.get("manufacturer_id"),
                    bom_size=bom_size,
                )
                offer = choose_best_offer(pricing_response)
                offer = _merge_candidate_defaults(offer, candidate)

                if exclude_marketplace and offer.marketplace is True:
                    continue
                offers.append(offer)

            chosen = _choose_line_offer(
                offers,
                prefer_in_stock=prefer_in_stock,
                requested_qty=max(bom_item.qty, 1),
            )

            if not offers:
                warning = f"No Digi-Key offers found for '{keyword}'"
                notes.append(warning)
                warnings.append(warning)

            lines.append(
                QuoteLineItem(
                    bom_item=bom_item,
                    offers=offers,
                    chosen=chosen,
                    notes=notes,
                )
            )

    total = 0.0
    for line in lines:
        if line.chosen and line.chosen.extended_price is not None:
            total += line.chosen.extended_price

    return QuoteResponse(
        request_id=request_id,
        lines=lines,
        totals={"parts_total": round(total, 4)},
        warnings=warnings,
    )
