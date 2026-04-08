"""Unit tests for pricing engine and comparables."""

import pytest
from src.pricing.engine import calculate_price_range, PricingConfig, InsufficientCompsError
from src.pricing.comparables import haversine_distance, select_comps, CompSelectionConfig, SubjectProperty


def test_haversine_distance():
    """Test distance calculation."""
    # Dallas to Garland is about 15 miles
    dallas = (32.7767, -96.7970)
    garland = (32.9126, -96.6389)
    
    distance = haversine_distance(dallas[0], dallas[1], garland[0], garland[1])
    
    # Should be approximately 15 miles (within 10%)
    assert 13 < distance < 17


def test_select_comps_basic():
    """Test comp selection with basic filters."""
    listings = [
        {
            "ListingId": "1",
            "Latitude": 32.9126,
            "Longitude": -96.6389,
            "LivingArea": 1600,
            "BedroomsTotal": 3,
            "ClosePrice": 300000
        },
        {
            "ListingId": "2",
            "Latitude": 32.9126,
            "Longitude": -96.6389,  # Same location
            "LivingArea": 2200,  # Too big
            "BedroomsTotal": 4,
            "ClosePrice": 400000
        },
        {
            "ListingId": "3",
            "Latitude": 32.0000,  # Too far
            "Longitude": -96.0000,
            "LivingArea": 1600,
            "BedroomsTotal": 3,
            "ClosePrice": 250000
        }
    ]
    
    subject = SubjectProperty(lat=32.9126, lng=-96.6389, sqft=1600, bedrooms=3)
    config = CompSelectionConfig(radius_miles=1.0, sqft_tolerance_pct=20, bedroom_tolerance=1)
    
    comps = select_comps(listings, subject, config)
    
    # Should only get listing #1
    assert len(comps) == 1
    assert comps[0]["ListingId"] == "1"


def test_calculate_price_range_basic():
    """Test price range calculation."""
    comps = [
        {"ClosePrice": 300000, "LivingArea": 1500},  # $200/sqft
        {"ClosePrice": 350000, "LivingArea": 1600},  # $218.75/sqft
        {"ClosePrice": 320000, "LivingArea": 1550},  # $206.45/sqft
        {"ClosePrice": 380000, "LivingArea": 1700},  # $223.53/sqft
        {"ClosePrice": 290000, "LivingArea": 1450},  # $200/sqft
    ]
    
    config = PricingConfig(
        price_percentile_low=25,
        price_percentile_high=75,
        min_comps_required=3
    )
    
    result = calculate_price_range(comps, subject_sqft=1500, config=config)
    
    assert result["min"] > 0
    assert result["max"] > result["min"]
    assert "percentile" in result["methodology"].lower()
    assert result["comps_used"] == 5


def test_calculate_price_range_insufficient_comps():
    """Test error when not enough comps."""
    comps = [
        {"ClosePrice": 300000, "LivingArea": 1500}
    ]
    
    config = PricingConfig(min_comps_required=3)
    
    with pytest.raises(InsufficientCompsError):
        calculate_price_range(comps, subject_sqft=1500, config=config)


def test_price_range_with_outliers():
    """Test that outliers are filtered."""
    comps = [
        {"ClosePrice": 300000, "LivingArea": 1500},   # $200/sqft - normal
        {"ClosePrice": 320000, "LivingArea": 1500},   # $213/sqft - normal
        {"ClosePrice": 310000, "LivingArea": 1500},   # $207/sqft - normal
        {"ClosePrice": 600000, "LivingArea": 1500},   # $400/sqft - OUTLIER
        {"ClosePrice": 295000, "LivingArea": 1500},   # $197/sqft - normal
    ]
    
    config = PricingConfig(min_comps_required=3)
    
    result = calculate_price_range(comps, subject_sqft=1500, config=config)
    
    # Outlier should be removed, so max should be based on $213/sqft, not $400
    # After removing outlier, max should be around $213 * 1500 = ~320,000
    assert result["max"] < 400000
    assert result["comps_used"] == 4  # One outlier removed
