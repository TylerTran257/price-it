"""Comparable property selection logic."""

import math
from typing import List, Dict, Any
from dataclasses import dataclass
from src.api.schemas import GeoLocation


@dataclass
class CompSelectionConfig:
    """Configuration for comp selection."""
    radius_miles: float
    sqft_tolerance_pct: float
    bedroom_tolerance: int


@dataclass
class SubjectProperty:
    """Subject property being evaluated."""
    lat: float
    lng: float
    sqft: float
    bedrooms: int


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate distance between two points in miles using Haversine formula.
    
    Args:
        lat1: Latitude of first point
        lng1: Longitude of first point
        lat2: Latitude of second point
        lng2: Longitude of second point
        
    Returns:
        Distance in miles
    """
    R = 3959  # Earth's radius in miles
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    a = (math.sin(delta_lat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def select_comps(
    listings: List[Dict[str, Any]],
    subject: SubjectProperty,
    config: CompSelectionConfig
) -> List[Dict[str, Any]]:
    """
    Filter listings to find comparable properties.
    
    Filters applied:
    1. Distance within radius
    2. Sqft within ±tolerance%
    3. Bedrooms within ±tolerance
    
    Args:
        listings: List of listing dictionaries from MLS
        subject: Subject property being evaluated
        config: Comp selection configuration
        
    Returns:
        List of comparable listings
    """
    filtered = []
    
    for listing in listings:
        # Check distance
        listing_lat = listing.get("Latitude")
        listing_lng = listing.get("Longitude")
        
        if listing_lat is None or listing_lng is None:
            continue
        
        distance = haversine_distance(
            subject.lat, subject.lng,
            listing_lat, listing_lng
        )
        
        if distance > config.radius_miles:
            continue
        
        # Check sqft tolerance
        listing_sqft = listing.get("LivingArea")
        if listing_sqft and listing_sqft > 0 and subject.sqft > 0:
            sqft_diff_pct = abs(listing_sqft - subject.sqft) / subject.sqft * 100
            if sqft_diff_pct > config.sqft_tolerance_pct:
                continue
        
        # Check bedroom tolerance
        listing_beds = listing.get("BedroomsTotal")
        if listing_beds is not None and subject.bedrooms > 0:
            if abs(listing_beds - subject.bedrooms) > config.bedroom_tolerance:
                continue
        
        # Add distance info for debugging
        listing['_distance_miles'] = round(distance, 2)
        filtered.append(listing)
    
    # Sort by distance (closest first)
    filtered.sort(key=lambda x: x.get('_distance_miles', float('inf')))
    
    return filtered


def estimate_subject_sqft(listings: List[Dict[str, Any]]) -> float:
    """
    Estimate subject property sqft from comparable listings.
    
    Uses median sqft of nearby listings as estimate.
    
    Args:
        listings: List of comparable listings
        
    Returns:
        Estimated square footage
    """
    sqfts = [l.get("LivingArea", 0) for l in listings if l.get("LivingArea", 0) > 0]
    
    if not sqfts:
        return 1800  # Default to typical Garland home size
    
    sqfts.sort()
    mid = len(sqfts) // 2
    
    if len(sqfts) % 2 == 0:
        return (sqfts[mid - 1] + sqfts[mid]) / 2
    else:
        return sqfts[mid]


def estimate_subject_bedrooms(listings: List[Dict[str, Any]]) -> int:
    """
    Estimate subject property bedrooms from comparable listings.
    
    Uses mode (most common) bedroom count.
    
    Args:
        listings: List of comparable listings
        
    Returns:
        Estimated bedroom count
    """
    bedrooms = [l.get("BedroomsTotal", 0) for l in listings if l.get("BedroomsTotal", 0) > 0]
    
    if not bedrooms:
        return 3  # Default to 3 bedrooms
    
    # Return mode (most common)
    from collections import Counter
    return Counter(bedrooms).most_common(1)[0][0]
