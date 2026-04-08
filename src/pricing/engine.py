"""Pricing engine for calculating price ranges from comparable sales."""

import numpy as np
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class PricingConfig:
    """Configuration for pricing calculations."""
    price_percentile_low: float = 25.0
    price_percentile_high: float = 75.0
    min_comps_required: int = 3


class InsufficientCompsError(Exception):
    """Raised when not enough comparable sales are found."""
    pass


def calculate_price_per_sqft(listing: Dict[str, Any]) -> float:
    """
    Calculate price per square foot for a listing.
    
    Args:
        listing: Listing dictionary with price and sqft
        
    Returns:
        Price per square foot
    """
    price = listing.get("ClosePrice") or listing.get("ListPrice", 0)
    sqft = listing.get("LivingArea", 0)
    
    if sqft and sqft > 0:
        return price / sqft
    return 0


def filter_outliers(values: List[float]) -> List[float]:
    """
    Remove outliers using 1.5 * IQR rule.
    
    Args:
        values: List of values
        
    Returns:
        List with outliers removed
    """
    if len(values) < 4:
        return values
    
    q1 = np.percentile(values, 25)
    q3 = np.percentile(values, 75)
    iqr = q3 - q1
    
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    
    return [v for v in values if lower_bound <= v <= upper_bound]


def calculate_price_range(
    sold_comps: List[Dict[str, Any]],
    subject_sqft: float,
    config: PricingConfig
) -> Dict[str, Any]:
    """
    Calculate price range from sold comparables using percentile-based methodology.
    
    Algorithm:
    1. Calculate $/sqft for each sold comp
    2. Filter outliers using IQR method
    3. Get 25th and 75th percentiles of $/sqft
    4. Apply percentiles to subject property sqft
    
    Args:
        sold_comps: List of sold comparable listings
        subject_sqft: Square footage of subject property
        config: Pricing configuration
        
    Returns:
        Dictionary with min, max prices and methodology
        
    Raises:
        InsufficientCompsError: If not enough comps
    """
    # Calculate price per sqft for each comp
    prices_per_sqft = []
    for comp in sold_comps:
        ppsf = calculate_price_per_sqft(comp)
        if ppsf > 0:
            prices_per_sqft.append(ppsf)
    
    if len(prices_per_sqft) < config.min_comps_required:
        raise InsufficientCompsError(
            f"Need {config.min_comps_required}+ comparable sales, found {len(prices_per_sqft)}"
        )
    
    # Filter outliers
    filtered_prices = filter_outliers(prices_per_sqft)
    
    # If outlier filtering removed too many, use unfiltered
    if len(filtered_prices) < config.min_comps_required:
        filtered_prices = prices_per_sqft
    
    # Calculate percentiles
    p_low = np.percentile(filtered_prices, config.price_percentile_low)
    p_high = np.percentile(filtered_prices, config.price_percentile_high)
    
    # Apply to subject property
    min_price = int(subject_sqft * p_low)
    max_price = int(subject_sqft * p_high)
    
    # Round to nearest thousand
    min_price = (min_price // 1000) * 1000
    max_price = (max_price // 1000) * 1000
    
    return {
        "min": min_price,
        "max": max_price,
        "methodology": (
            f"{config.price_percentile_low:.0f}th-{config.price_percentile_high:.0f}th percentile "
            f"of ${ppsf:.0f}/sqft from {len(filtered_prices)} comparable sales"
        ),
        "ppsf_low": round(p_low, 2),
        "ppsf_high": round(p_high, 2),
        "comps_used": len(filtered_prices)
    }


def apply_fallback_strategies(
    mls_client,
    location,
    radius_miles: float,
    lookback_days: int,
    property_type: str,
    subject,
    config,
    min_comps_required: int
):
    """
    Apply fallback strategies when insufficient comps found.
    
    Fallback chain:
    1. Expand radius (2x, then 5x)
    2. Extend lookback period (365 days)
    3. Relax sqft/bedroom filters
    
    Args:
        mls_client: MLS client instance
        location: Subject location
        radius_miles: Initial search radius
        lookback_days: Initial lookback period
        property_type: Property type
        subject: Subject property
        config: Comp selection config
        min_comps_required: Minimum comps needed
        
    Returns:
        List of comparable listings
        
    Raises:
        InsufficientCompsError: If all fallbacks exhausted
    """
    from src.pricing.comparables import select_comps, CompSelectionConfig
    
    # Strategy 1: Expand radius
    for expanded_radius in [radius_miles * 2, radius_miles * 5]:
        listings = await mls_client.search_sold(
            location, expanded_radius, lookback_days, property_type
        )
        comps = select_comps(listings, subject, config)
        if len(comps) >= min_comps_required:
            return comps
    
    # Strategy 2: Extend lookback period
    extended_listings = await mls_client.search_sold(
        location, radius_miles, 365, property_type
    )
    comps = select_comps(extended_listings, subject, config)
    if len(comps) >= min_comps_required:
        return comps
    
    # Strategy 3: Relax filters
    relaxed_config = CompSelectionConfig(
        radius_miles=radius_miles * 5,
        sqft_tolerance_pct=30.0,
        bedroom_tolerance=2
    )
    all_listings = await mls_client.search_sold(
        location, radius_miles * 5, 365, property_type
    )
    comps = select_comps(all_listings, subject, relaxed_config)
    if len(comps) >= min_comps_required:
        return comps
    
    raise InsufficientCompsError(
        f"No comparable listings found after applying all fallback strategies. "
        f"Found {len(comps)} comps, need {min_comps_required}."
    )


# Note: The apply_fallback_strategies function needs to be async, 
# so it's used in the pricing_service.py instead
