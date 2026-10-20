"""Read-only public Linux VM retail quote. No Azure login, resource creation or payment."""

import argparse
import json
import math
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://prices.azure.com/api/retail/prices"


def validate_inputs(region, sku, hours):
    if not re.fullmatch(r"[a-z0-9]{2,40}", region):
        raise ValueError("Use the Azure region code, not a URL or display name.")
    if not re.fullmatch(r"Standard_[A-Za-z0-9_]{2,70}", sku):
        raise ValueError("Use a complete Azure Standard_ VM SKU.")
    if not 1 <= hours <= 744:
        raise ValueError("Estimate between 1 and 744 hours.")


def estimate_compute(items, region, sku, hours):
    validate_inputs(region, sku, hours)
    rates = []
    for item in items:
        price = item.get("retailPrice")
        if (
            item.get("armRegionName") != region
            or item.get("armSkuName") != sku
            or item.get("currencyCode") != "USD"
            or item.get("type") != "Consumption"
            or item.get("unitOfMeasure") != "1 Hour"
            or item.get("isPrimaryMeterRegion") is not True
            or not item.get("productName", "").startswith("Virtual Machines ")
            or "windows" in item.get("productName", "").lower()
            or any(word in item.get("meterName", "").lower() for word in ("spot", "low priority"))
            or type(price) not in (int, float)
            or not math.isfinite(price)
            or price <= 0
        ):
            continue
        rates.append(item)
    if not rates or len({item["retailPrice"] for item in rates}) != 1:
        raise ValueError("No unambiguous regular Linux hourly rate found. Check the portal; do not guess.")
    return {
        "region": region,
        "sku": sku,
        "currency": "USD",
        "hours": hours,
        "retail_compute_per_hour": rates[0]["retailPrice"],
        "estimated_compute_only": round(rates[0]["retailPrice"] * hours, 4),
        "product": rates[0]["productName"],
        "meter": rates[0]["meterName"],
        "excludes": ["managed disks", "public IP", "network transfers", "other services and taxes"],
        "not_verified": ["student quota", "allowed regions", "capacity", "actual subscription pricing"],
        "warning": "Compute-only estimate, not total cost or permission to create resources.",
    }


def fetch_items(region, sku):
    # Validate user-controlled filter fragments before constructing the public query.
    validate_inputs(region, sku, 1)
    query = (
        "serviceName eq 'Virtual Machines' and armRegionName eq '"
        + region
        + "' and armSkuName eq '"
        + sku
        + "' and priceType eq 'Consumption'"
    )
    url = API + "?" + urllib.parse.urlencode({"$filter": query, "currencyCode": "'USD'"})
    items = []
    for _ in range(5):
        parsed = urllib.parse.urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "prices.azure.com"
            or not parsed.path.startswith("/api/retail/prices")
        ):
            raise ValueError("Unexpected pricing pagination destination rejected.")
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read(2 * 1024**2))
        items.extend(data.get("Items", []))
        url = data.get("NextPageLink")
        if not url:
            return items
    raise ValueError("Pricing response exceeded the bounded page limit.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True)
    parser.add_argument("--sku", required=True)
    parser.add_argument("--hours", type=int, default=168, help="Default: a proposed seven-day review window")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        validate_inputs(args.region, args.sku, args.hours)
        result = estimate_compute(fetch_items(args.region, args.sku), args.region, args.sku, args.hours)
    except (ValueError, OSError) as exc:
        raise SystemExit("Quote unavailable: " + str(exc)) from None
    result["checked_utc"] = datetime.now(timezone.utc).isoformat()
    result["source"] = API
    output = json.dumps(result, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
