"""FastAPI application for Price-It API."""

import asyncio
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.api.schemas import (
    PriceRequest, PriceResponse, PriceRange, ListingSummary,
    PriceResponseMetadata, HealthResponse, GeoLocation
)
from src.cache.store import InMemoryCache, generate_address_cache_key
from src.geocoding.service import GeocodingService, GeocodingError
from src.mls.client import MLSClient
from src.pricing.comparables import (
    select_comps, SubjectProperty, CompSelectionConfig,
    estimate_subject_sqft, estimate_subject_bedrooms
)
from src.pricing.engine import calculate_price_range, PricingConfig, InsufficientCompsError


# Global instances
_cache: InMemoryCache = None
_geocoding: GeocodingService = None
_mls_client: MLSClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    global _cache, _geocoding, _mls_client
    
    # Startup
    settings = get_settings()
    _cache = InMemoryCache()
    _geocoding = GeocodingService()
    _mls_client = MLSClient(use_mock=(settings.mls_provider == "mock"))
    
    print(f"🚀 Price-It API starting up")
    print(f"   Environment: {settings.environment}")
    print(f"   MLS Provider: {settings.mls_provider}")
    print(f"   Cache TTL: {settings.cache_ttl_seconds}s")
    
    yield
    
    # Shutdown
    print("👋 Price-It API shutting down")


app = FastAPI(
    title="Price-It API",
    description="MLS-based real estate price estimation for NTREIS (North Texas)",
    version="0.1.0",
    lifespan=lifespan
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle unexpected exceptions."""
    print(f"❌ Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": str(exc)}
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="0.1.0"
    )


@app.post("/v1/price", response_model=PriceResponse)
async def get_price_estimate(request: PriceRequest):
    """
    Get price range estimate for an address using MLS comparable data.
    
    This endpoint:
    1. Checks cache for existing estimate
    2. Geocodes the address to get lat/lng
    3. Fetches Active, Pending, and Sold listings from MLS
    4. Filters sold listings to find comparable properties
    5. Calculates 25th-75th percentile price range
    6. Caches and returns the result
    """
    settings = get_settings()
    
    # 1. Check cache
    cache_key = generate_address_cache_key(request.address)
    cached_result = await _cache.get(cache_key)
    
    if cached_result:
        print(f"✅ Cache hit for {request.address.to_full_address()}")
        cached_result["metadata"]["cached"] = True
        return PriceResponse(**cached_result)
    
    print(f"🔍 Processing: {request.address.to_full_address()}")
    
    try:
        # 2. Geocode address
        location = await _geocoding.geocode(request.address)
        print(f"📍 Geocoded to: {location.lat}, {location.lng}")
        
        # 3. Fetch MLS data in parallel
        radius = request.options.radius_miles
        property_type = request.options.property_type
        
        active_listings, pending_listings, sold_listings = await asyncio.gather(
            _mls_client.search_active(location, radius, property_type),
            _mls_client.search_pending(location, radius, property_type),
            _mls_client.search_sold(
                location, radius, 
                request.options.sold_lookback_days, 
                property_type
            )
        )
        
        print(f"📊 Found: {len(active_listings)} active, {len(pending_listings)} pending, {len(sold_listings)} sold")
        
        # 4. Estimate subject property characteristics from nearby listings
        subject_sqft = estimate_subject_sqft(sold_listings + active_listings)
        subject_beds = estimate_subject_bedrooms(sold_listings + active_listings)
        
        subject = SubjectProperty(
            lat=location.lat,
            lng=location.lng,
            sqft=subject_sqft,
            bedrooms=subject_beds
        )
        
        # 5. Filter sold comps
        comp_config = CompSelectionConfig(
            radius_miles=radius,
            sqft_tolerance_pct=settings.sqft_tolerance_pct,
            bedroom_tolerance=settings.bedroom_tolerance
        )
        
        sold_comps = select_comps(sold_listings, subject, comp_config)
        print(f"🏠 Found {len(sold_comps)} comparable sales after filtering")
        
        # 6. Apply fallback strategies if insufficient comps
        if len(sold_comps) < settings.min_comps_required:
            print(f"⚠️ Insufficient comps ({len(sold_comps)}), applying fallbacks...")
            sold_comps = await _apply_fallbacks(
                location, radius, request.options.sold_lookback_days,
                property_type, subject, comp_config, settings.min_comps_required
            )
            print(f"✅ Fallback found {len(sold_comps)} comps")
        
        # 7. Calculate price range
        pricing_config = PricingConfig(
            price_percentile_low=settings.price_percentile_low,
            price_percentile_high=settings.price_percentile_high,
            min_comps_required=settings.min_comps_required
        )
        
        price_data = calculate_price_range(sold_comps, subject_sqft, pricing_config)
        
        price_range = PriceRange(
            min=price_data["min"],
            max=price_data["max"],
            methodology=price_data["methodology"]
        )
        
        # 8. Build response
        response_data = {
            "address": {
                "street": request.address.street,
                "city": request.address.city,
                "state": request.address.state,
                "zip": request.address.zip,
                "full": request.address.to_full_address()
            },
            "price_range": price_range.model_dump(),
            "available_listings": [
                ListingSummary(
                    address=f"{l['StreetNumber']} {l['StreetName']}, {l['City']}, {l['StateOrProvince']}",
                    list_price=l.get("ListPrice"),
                    days_on_market=l.get("DaysOnMarket", 0)
                ).model_dump()
                for l in active_listings[:5]  # Limit to top 5
            ],
            "pending_listings": [
                ListingSummary(
                    address=f"{l['StreetNumber']} {l['StreetName']}, {l['City']}, {l['StateOrProvince']}",
                    list_price=l.get("ListPrice"),
                    days_on_market=l.get("DaysOnMarket", 0)
                ).model_dump()
                for l in pending_listings[:3]
            ],
            "sold_listings": [
                ListingSummary(
                    address=f"{l['StreetNumber']} {l['StreetName']}, {l['City']}, {l['StateOrProvince']}",
                    sold_price=l.get("ClosePrice"),
                    days_on_market=l.get("DaysOnMarket", 0)
                ).model_dump()
                for l in sold_comps[:10]  # Show comps used
            ],
            "metadata": {
                "comps_used": len(sold_comps),
                "search_radius_miles": radius,
                "sold_lookback_days": request.options.sold_lookback_days,
                "cached": False,
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
        # 9. Cache result
        await _cache.set(cache_key, response_data, settings.cache_ttl_seconds)
        
        print(f"💰 Price estimate: ${price_range.min:,} - ${price_range.max:,}")
        
        return PriceResponse(**response_data)
        
    except GeocodingError as e:
        print(f"❌ Geocoding error: {e}")
        raise HTTPException(status_code=400, detail=f"Address not found: {e}")
    except InsufficientCompsError as e:
        print(f"❌ Insufficient comps: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


async def _apply_fallbacks(
    location: GeoLocation,
    radius_miles: float,
    lookback_days: int,
    property_type: str,
    subject: SubjectProperty,
    config: CompSelectionConfig,
    min_comps_required: int
):
    """Apply fallback strategies when insufficient comps found."""
    
    # Strategy 1: Expand radius to 2x
    print(f"  Fallback 1: Expanding radius to {radius_miles * 2} miles")
    listings = await _mls_client.search_sold(
        location, radius_miles * 2, lookback_days, property_type
    )
    comps = select_comps(listings, subject, config)
    if len(comps) >= min_comps_required:
        return comps
    
    # Strategy 2: Expand radius to 5x
    print(f"  Fallback 2: Expanding radius to {radius_miles * 5} miles")
    listings = await _mls_client.search_sold(
        location, radius_miles * 5, lookback_days, property_type
    )
    comps = select_comps(listings, subject, config)
    if len(comps) >= min_comps_required:
        return comps
    
    # Strategy 3: Extend lookback to 365 days
    print(f"  Fallback 3: Extending lookback to 365 days")
    listings = await _mls_client.search_sold(
        location, radius_miles * 5, 365, property_type
    )
    comps = select_comps(listings, subject, config)
    if len(comps) >= min_comps_required:
        return comps
    
    # Strategy 4: Relax filters
    print(f"  Fallback 4: Relaxing filters")
    relaxed_config = CompSelectionConfig(
        radius_miles=radius_miles * 5,
        sqft_tolerance_pct=30.0,
        bedroom_tolerance=2
    )
    listings = await _mls_client.search_sold(
        location, radius_miles * 5, 365, property_type
    )
    comps = select_comps(listings, subject, relaxed_config)
    if len(comps) >= min_comps_required:
        return comps
    
    raise InsufficientCompsError(
        f"No comparable listings found after applying all fallback strategies. "
        f"Found {len(comps)} comps, need {min_comps_required}."
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
