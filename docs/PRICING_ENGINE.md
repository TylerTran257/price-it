# Pricing Engine

## Overview

The pricing engine calculates an estimated price range for a subject property using statistical analysis of comparable sold listings (comps).

## Methodology

**Percentile-based approach using $/sqft from sold comps:**

1. Fetch sold listings within radius and lookback window
2. Filter comps by similarity (property type, sqft, bedrooms)
3. Calculate $/sqft for each comp: `sold_price / living_area`
4. Compute 25th percentile → price floor
5. Compute 75th percentile → price ceiling
6. Apply to subject property's estimated sqft

## Module Structure

```
src/pricing/
├── __init__.py
├── engine.py          # Price range calculation
└── comparables.py     # Comp selection and filtering
```

## Algorithm

### Step 1: Comp Selection

```python
def select_comps(
    sold_listings: list[dict],
    subject_lat: float,
    subject_lng: float,
    subject_sqft: float | None,
    subject_beds: int | None,
    radius_miles: float = 1.0,
    sqft_tolerance_pct: float = 20.0,
    bedroom_tolerance: int = 1,
) -> list[dict]:
```

Filters sold listings by:
- Distance from subject property (Haversine formula)
- Property type match
- Square footage within ±20%
- Bedrooms within ±1
- Sold within lookback window (default 180 days)

### Step 2: Price Per Sqft Calculation

```python
def calculate_price_per_sqft(comps: list[dict]) -> list[float]:
    return [comp["ClosePrice"] / comp["LivingArea"] for comp in comps if comp["LivingArea"] > 0]
```

### Step 3: Percentile Calculation

```python
def calculate_percentiles(prices_per_sqft: list[float], low: float = 25.0, high: float = 75.0) -> tuple[float, float]:
    return numpy.percentile(prices_per_sqft, low), numpy.percentile(prices_per_sqft, high)
```

### Step 4: Price Range Estimation

```python
def estimate_price_range(
    subject_sqft: float,
    price_per_sqft_low: float,
    price_per_sqft_high: float,
) -> dict[str, int]:
    return {
        "min": int(subject_sqft * price_per_sqft_low),
        "max": int(subject_sqft * price_per_sqft_high),
    }
```

## Fallback Logic

If insufficient comps are found:

1. **Expand radius** (1.0 → 2.0 → 5.0 miles)
2. **Extend lookback** (180 → 365 days)
3. **Relax filters** (sqft tolerance ±30%, bedrooms ±2)
4. **Use active/pending listings** as secondary signal (list price $/sqft)
5. **Return error** if still no comps

## Configurable Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `COMPS_RADIUS_MILES` | 1.0 | Initial search radius |
| `SOLD_LOOKBACK_DAYS` | 180 | Days to look back for sold comps |
| `PRICE_PERCENTILE_LOW` | 25 | Lower percentile for price range |
| `PRICE_PERCENTILE_HIGH` | 75 | Upper percentile for price range |
| `SQFT_TOLERANCE_PCT` | 20 | Acceptable sqft deviation (%) |
| `BEDROOM_TOLERANCE` | 1 | Acceptable bedroom deviation |
| `MIN_COMPS_REQUIRED` | 3 | Minimum comps for valid estimate |

## Edge Cases

| Scenario | Handling |
|----------|----------|
| No sold comps | Expand radius/lookback, then use active listings |
| Subject sqft unknown | Use median sqft of comps |
| Subject beds unknown | Skip bedroom filter |
| Outlier comps (extreme $/sqft) | Filter out values outside 1.5 * IQR |
| New construction | Flag in metadata; comps may not be representative |

## Testing

```python
# tests/test_pricing/test_engine.py
def test_price_range_calculation():
    comps = [
        {"ClosePrice": 300000, "LivingArea": 1500},  # $200/sqft
        {"ClosePrice": 350000, "LivingArea": 1600},  # $218.75/sqft
        {"ClosePrice": 320000, "LivingArea": 1550},  # $206.45/sqft
        {"ClosePrice": 380000, "LivingArea": 1700},  # $223.53/sqft
        {"ClosePrice": 290000, "LivingArea": 1450},  # $200/sqft
    ]
    result = calculate_price_range(comps, subject_sqft=1500)
    assert result["min"] > 0
    assert result["max"] > result["min"]
```

## Future Enhancements

- **Weighted comps**: Weight by recency and distance
- **Regression model**: Train on historical data
- **Adjustment factors**: Add value for pools, garages, upgrades
- **Confidence score**: Based on comp count and variance
