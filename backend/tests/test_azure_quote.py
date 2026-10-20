import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "azure_quote", Path(__file__).resolve().parents[2] / "scripts/azure_price_check.py"
)
quote = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quote)


def price(**updates):
    return {
        "armRegionName": "australiaeast",
        "armSkuName": "Standard_B4as_v2",
        "currencyCode": "USD",
        "type": "Consumption",
        "unitOfMeasure": "1 Hour",
        "isPrimaryMeterRegion": True,
        "retailPrice": 0.1,
        "productName": "Virtual Machines Basv2 Series",
        "meterName": "B4as v2",
        **updates,
    }


def test_compute_quote_excludes_windows_spot_and_nonstandard_rates():
    result = quote.estimate_compute(
        [
            price(),
            price(productName="Basv2 Series Cloud Services", retailPrice=0.001),
            price(productName="Virtual Machines Basv2 Series Windows", retailPrice=0.01),
            price(meterName="B4as v2 Spot", retailPrice=0.01),
            price(type="DevTestConsumption"),
            price(isPrimaryMeterRegion=False),
        ],
        "australiaeast",
        "Standard_B4as_v2",
        168,
    )
    assert result["estimated_compute_only"] == 16.8
    assert result["excludes"] and result["not_verified"]


@pytest.mark.parametrize("items", [[], [price(), price(retailPrice=0.2)], [price(retailPrice=-1)]])
def test_no_guess_when_quote_missing_or_ambiguous(items):
    with pytest.raises(ValueError):
        quote.estimate_compute(items, "australiaeast", "Standard_B4as_v2", 168)


@pytest.mark.parametrize(
    "region,sku,hours",
    [
        ("eastus' or true", "Standard_B4as_v2", 1),
        ("eastus", "https://bad.example", 1),
        ("eastus", "Standard_B4as_v2", 0),
        ("eastus", "Standard_B4as_v2", 1000),
    ],
)
def test_reject_filter_injection_and_unbounded_estimates(region, sku, hours):
    with pytest.raises(ValueError):
        quote.estimate_compute([], region, sku, hours)
