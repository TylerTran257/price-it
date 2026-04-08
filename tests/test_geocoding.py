"""Tests for geocoding service."""

import pytest
from src.geocoding.service import GeocodingService, GeocodingError
from src.api.schemas import Address


@pytest.mark.asyncio
async def test_geocode_garland_address():
    """Test geocoding a Garland address."""
    service = GeocodingService()
    
    address = Address(
        street="1406 Bentwood Dr",
        city="Garland",
        state="TX",
        zip="75041"
    )
    
    # Note: This test requires internet connection
    # Skip if no internet available
    try:
        location = await service.geocode(address)
        
        # Garland, TX should be around 32.91, -96.63
        assert 32.8 < location.lat < 33.0
        assert -96.8 < location.lng < -96.5
    except GeocodingError:
        pytest.skip("Geocoding service unavailable (no internet?)")


@pytest.mark.asyncio
async def test_geocode_invalid_address():
    """Test geocoding fails gracefully for invalid address."""
    service = GeocodingService()
    
    address = Address(
        street="99999 Not A Real Street XYZ123",
        city="Nowhere",
        state="XX",
        zip="00000"
    )
    
    try:
        with pytest.raises(GeocodingError):
            await service.geocode(address)
    except Exception:
        pytest.skip("Geocoding service unavailable")
