"""Geocoding service using Nominatim (OpenStreetMap) - free, no API key required."""

import httpx
from typing import Optional
from src.api.schemas import Address, GeoLocation


class GeocodingError(Exception):
    """Raised when geocoding fails."""
    pass


class GeocodingService:
    """Service for converting addresses to geographic coordinates."""
    
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    
    def __init__(self, user_agent: str = "PriceItApp/0.1"):
        """
        Initialize geocoding service.
        
        Args:
            user_agent: Required by Nominatim's terms of service
        """
        self.user_agent = user_agent
    
    async def geocode(self, address: Address) -> GeoLocation:
        """
        Convert address to latitude/longitude coordinates.
        
        Args:
            address: Address to geocode
            
        Returns:
            GeoLocation with lat/lng
            
        Raises:
            GeocodingError: If address cannot be geocoded
        """
        query = address.to_full_address()
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.NOMINATIM_URL,
                    params={
                        "q": query,
                        "format": "json",
                        "limit": 1,
                        "addressdetails": 1
                    },
                    headers={"User-Agent": self.user_agent},
                    timeout=10.0
                )
                response.raise_for_status()
                
                data = response.json()
                
                if not data:
                    raise GeocodingError(f"Address not found: {query}")
                
                result = data[0]
                return GeoLocation(
                    lat=float(result["lat"]),
                    lng=float(result["lon"])
                )
                
            except httpx.HTTPError as e:
                raise GeocodingError(f"Geocoding request failed: {e}")
            except (KeyError, ValueError) as e:
                raise GeocodingError(f"Invalid geocoding response: {e}")
