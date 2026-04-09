"""MLS client - supports mock, NTREIS, and CoreLogic/Trestle."""

import random
import asyncio
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from src.api.schemas import GeoLocation
from src.config import get_settings


class MLSClient:
    """MLS client for fetching property listings."""
    
    def __init__(self, use_mock: bool = True):
        """
        Initialize MLS client.
        
        Args:
            use_mock: If True, use mock data instead of real MLS API
        """
        self.use_mock = use_mock
        self._mock_data_generator = MockMLSDataGenerator()
        self._corelogic_client: Optional[CoreLogicClient] = None
        
        if not use_mock:
            settings = get_settings()
            if settings.mls_provider == "corelogic":
                self._corelogic_client = CoreLogicClient()
    
    async def search_active(
        self,
        location: GeoLocation,
        radius_miles: float,
        property_type: str = "Residential"
    ) -> List[Dict[str, Any]]:
        """Search active listings."""
        if self.use_mock:
            return self._mock_data_generator.generate_active_listings(location, radius_miles)
        
        if self._corelogic_client:
            return await self._corelogic_client.search_properties(
                location, radius_miles, "Active", property_type
            )
        
        raise NotImplementedError(f"MLS provider not supported: {get_settings().mls_provider}")
    
    async def search_pending(
        self,
        location: GeoLocation,
        radius_miles: float,
        property_type: str = "Residential"
    ) -> List[Dict[str, Any]]:
        """Search pending listings."""
        if self.use_mock:
            return self._mock_data_generator.generate_pending_listings(location, radius_miles)
        
        if self._corelogic_client:
            return await self._corelogic_client.search_properties(
                location, radius_miles, "Pending", property_type
            )
        
        raise NotImplementedError(f"MLS provider not supported: {get_settings().mls_provider}")
    
    async def search_sold(
        self,
        location: GeoLocation,
        radius_miles: float,
        lookback_days: int,
        property_type: str = "Residential"
    ) -> List[Dict[str, Any]]:
        """Search sold listings within lookback period."""
        if self.use_mock:
            return self._mock_data_generator.generate_sold_listings(
                location, radius_miles, lookback_days
            )
        
        if self._corelogic_client:
            return await self._corelogic_client.search_sold_properties(
                location, radius_miles, lookback_days, property_type
            )
        
        raise NotImplementedError(f"MLS provider not supported: {get_settings().mls_provider}")


class CoreLogicClient:
    """CoreLogic Trestle WebAPI client."""
    
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.mls_reso_url or "https://api.cotality.com/trestle/odata"
        self.token_url = settings.mls_oauth_token_url or "https://api.cotality.com/trestle/oidc/connect/token"
        self.client_id = settings.mls_client_id
        self.client_secret = settings.mls_client_secret
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
    
    async def _get_token(self) -> str:
        """Get OAuth2 access token, using cached token if valid."""
        if self._token and self._token_expires and datetime.now() < self._token_expires:
            return self._token
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credentials",
                    "scope": "api"
                }
            )
            response.raise_for_status()
            data = response.json()
            self._token = data["access_token"]
            expires_in = data.get("expires_in", 28800)
            self._token_expires = datetime.now() + timedelta(seconds=expires_in - 300)
            return self._token
    
    def _build_geo_filter(self, location: GeoLocation, radius_miles: float) -> str:
        lat = location.lat
        lng = location.lng
        lat_delta = radius_miles / 69.0
        lng_delta = radius_miles / 51.0
        
        return (
            f"Latitude ge {lat - lat_delta} and Latitude le {lat + lat_delta} and "
            f"Longitude ge {lng - lng_delta} and Longitude le {lng + lng_delta}"
        )
    
    async def search_properties(
        self,
        location: GeoLocation,
        radius_miles: float,
        status: str,
        property_type: str = "Residential"
    ) -> List[Dict[str, Any]]:
        """Search properties by status (Active/Pending)."""
        token = await self._get_token()
        
        geo_filter = self._build_geo_filter(location, radius_miles)
        
        property_type_map = {
            "Residential": "A",
            "Condominium": "C",
            "Townhouse": "B"
        }
        prop_type_code = property_type_map.get(property_type, "A")
        
        filter_query = (
            f"{geo_filter} and StandardStatus eq '{status}' and "
            f"PropertyType eq '{prop_type_code}'"
        )
        
        url = f"{self.base_url}/Property"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "$filter": filter_query,
            "$top": 50,
            "$select": (
                "ListingKey,ListingId,ListPrice,DaysOnMarket,StandardStatus,"
                "StreetNumber,StreetName,City,StateOrProvince,PostalCode,"
                "Latitude,Longitude,LivingArea,BedroomsTotal,BathroomsTotal"
            )
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            all_results = []
            while url:
                response = await client.get(url, headers=headers, params=params if "?" not in url else None)
                response.raise_for_status()
                data = response.json()
                all_results.extend(data.get("value", []))
                
                next_link = data.get("@odata.nextLink")
                url = next_link
                params = None
        
        return [self._map_property(p) for p in all_results]
    
    async def search_sold_properties(
        self,
        location: GeoLocation,
        radius_miles: float,
        lookback_days: int,
        property_type: str = "Residential"
    ) -> List[Dict[str, Any]]:
        """Search sold/closed properties within lookback period."""
        token = await self._get_token()
        
        geo_filter = self._build_geo_filter(location, radius_miles)
        
        from datetime import datetime
        cutoff_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        
        property_type_map = {
            "Residential": "A",
            "Condominium": "C",
            "Townhouse": "B"
        }
        prop_type_code = property_type_map.get(property_type, "A")
        
        filter_query = (
            f"{geo_filter} and StandardStatus eq 'Closed' and "
            f"CloseDate ge {cutoff_date} and PropertyType eq '{prop_type_code}'"
        )
        
        url = f"{self.base_url}/Property"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "$filter": filter_query,
            "$top": 100,
            "$select": (
                "ListingKey,ListingId,ClosePrice,CloseDate,DaysOnMarket,StandardStatus,"
                "StreetNumber,StreetName,City,StateOrProvince,PostalCode,"
                "Latitude,Longitude,LivingArea,BedroomsTotal,BathroomsTotal"
            )
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            all_results = []
            while url:
                response = await client.get(url, headers=headers, params=params if "?" not in url else None)
                response.raise_for_status()
                data = response.json()
                all_results.extend(data.get("value", []))
                
                next_link = data.get("@odata.nextLink")
                url = next_link
                params = None
        
        return [self._map_property(p, is_sold=True) for p in all_results]
    
    def _map_property(self, prop: Dict[str, Any], is_sold: bool = False) -> Dict[str, Any]:
        """Map CoreLogic/RESO fields to internal format."""
        return {
            "ListingId": prop.get("ListingId"),
            "ListPrice": prop.get("ListPrice"),
            "ClosePrice": prop.get("ClosePrice"),
            "CloseDate": prop.get("CloseDate"),
            "DaysOnMarket": prop.get("DaysOnMarket", 0),
            "StreetNumber": prop.get("StreetNumber"),
            "StreetName": prop.get("StreetName"),
            "City": prop.get("City"),
            "StateOrProvince": prop.get("StateOrProvince"),
            "PostalCode": prop.get("PostalCode"),
            "Latitude": prop.get("Latitude"),
            "Longitude": prop.get("Longitude"),
            "LivingArea": prop.get("LivingArea"),
            "BedroomsTotal": prop.get("BedroomsTotal"),
            "BathroomsTotal": prop.get("BathroomsTotal"),
            "StandardStatus": prop.get("StandardStatus")
        }


class MockMLSDataGenerator:
    """Generate realistic mock MLS data for testing."""
    
    # Garland, TX area street names for realistic addresses
    GARLAND_STREETS = [
        "Bentwood Dr", "Buckingham Rd", "Country Club Dr", "Firewheel Pkwy",
        "Pleasant Valley Rd", "Belt Line Rd", "Bush Turnpike", "Lavon Dr",
        "Kingsley Rd", "Oates Dr", "Miller Rd", "Spring Valley Rd",
        "Forest Ln", "Walnut St", "Glenbrook Dr", "Meadowdale Ln"
    ]
    
    # Typical Garland home prices (these are realistic for the area)
    BASE_PRICE_PER_SQFT = 180  # ~$180/sqft average in Garland
    PRICE_VARIATION = 0.25  # ±25% price variation
    
    def __init__(self):
        """Initialize with seeded random for reproducibility."""
        self.random = random.Random()
    
    def _generate_address(self, location: GeoLocation, radius_miles: float) -> str:
        """Generate a realistic nearby address."""
        street = self.random.choice(self.GARLAND_STREETS)
        house_number = self.random.randint(1200, 9999)
        return f"{house_number} {street}, Garland, TX"
    
    def _add_random_offset(self, location: GeoLocation, radius_miles: float) -> GeoLocation:
        """Add random offset to coordinates within radius."""
        # Approximate degrees per mile
        lat_offset = (self.random.random() - 0.5) * 2 * (radius_miles / 69)
        lng_offset = (self.random.random() - 0.5) * 2 * (radius_miles / 69)
        
        return GeoLocation(
            lat=location.lat + lat_offset,
            lng=location.lng + lng_offset
        )
    
    def _generate_sqft(self) -> int:
        """Generate realistic square footage for Garland homes."""
        # Typical Garland homes: 1200-2800 sqft
        return self.random.randint(12, 28) * 100
    
    def _generate_bedrooms(self, sqft: int) -> int:
        """Generate realistic bedroom count based on sqft."""
        if sqft < 1400:
            return self.random.choice([2, 3])
        elif sqft < 2000:
            return self.random.choice([3, 4])
        else:
            return self.random.choice([3, 4, 5])
    
    def _generate_price(self, sqft: int) -> int:
        """Generate realistic price based on sqft."""
        base_price = sqft * self.BASE_PRICE_PER_SQFT
        variation = 1 + (self.random.random() - 0.5) * 2 * self.PRICE_VARIATION
        price = int(base_price * variation)
        # Round to nearest thousand
        return (price // 1000) * 1000
    
    def _generate_days_on_market(self, status: str) -> int:
        """Generate realistic days on market."""
        if status == "Active":
            return self.random.randint(1, 60)
        elif status == "Pending":
            return self.random.randint(5, 30)
        else:  # Sold
            return self.random.randint(10, 90)
    
    def generate_active_listings(
        self,
        location: GeoLocation,
        radius_miles: float
    ) -> List[Dict[str, Any]]:
        """Generate mock active listings."""
        # Generate 3-8 active listings
        num_listings = self.random.randint(3, 8)
        listings = []
        
        for _ in range(num_listings):
            loc = self._add_random_offset(location, radius_miles)
            sqft = self._generate_sqft()
            
            listings.append({
                "ListingId": f"ACTIVE_{self.random.randint(100000, 999999)}",
                "ListPrice": self._generate_price(sqft),
                "DaysOnMarket": self._generate_days_on_market("Active"),
                "StreetNumber": str(self.random.randint(1000, 9999)),
                "StreetName": self.random.choice(self.GARLAND_STREETS),
                "City": "Garland",
                "StateOrProvince": "TX",
                "PostalCode": "75041",
                "Latitude": loc.lat,
                "Longitude": loc.lng,
                "LivingArea": sqft,
                "BedroomsTotal": self._generate_bedrooms(sqft),
                "StandardStatus": "Active"
            })
        
        return listings
    
    def generate_pending_listings(
        self,
        location: GeoLocation,
        radius_miles: float
    ) -> List[Dict[str, Any]]:
        """Generate mock pending listings."""
        num_listings = self.random.randint(1, 4)
        listings = []
        
        for _ in range(num_listings):
            loc = self._add_random_offset(location, radius_miles)
            sqft = self._generate_sqft()
            
            listings.append({
                "ListingId": f"PENDING_{self.random.randint(100000, 999999)}",
                "ListPrice": self._generate_price(sqft),
                "DaysOnMarket": self._generate_days_on_market("Pending"),
                "StreetNumber": str(self.random.randint(1000, 9999)),
                "StreetName": self.random.choice(self.GARLAND_STREETS),
                "City": "Garland",
                "StateOrProvince": "TX",
                "PostalCode": "75041",
                "Latitude": loc.lat,
                "Longitude": loc.lng,
                "LivingArea": sqft,
                "BedroomsTotal": self._generate_bedrooms(sqft),
                "StandardStatus": "Pending"
            })
        
        return listings
    
    def generate_sold_listings(
        self,
        location: GeoLocation,
        radius_miles: float,
        lookback_days: int
    ) -> List[Dict[str, Any]]:
        """Generate mock sold listings."""
        # Generate 8-20 sold comps (more is better for pricing)
        num_listings = self.random.randint(8, 20)
        listings = []
        
        now = datetime.now()
        
        for _ in range(num_listings):
            loc = self._add_random_offset(location, radius_miles)
            sqft = self._generate_sqft()
            
            # Random close date within lookback period
            days_ago = self.random.randint(1, lookback_days)
            close_date = now - timedelta(days=days_ago)
            
            listings.append({
                "ListingId": f"SOLD_{self.random.randint(100000, 999999)}",
                "ClosePrice": self._generate_price(sqft),
                "DaysOnMarket": self._generate_days_on_market("Closed"),
                "CloseDate": close_date.strftime("%Y-%m-%d"),
                "StreetNumber": str(self.random.randint(1000, 9999)),
                "StreetName": self.random.choice(self.GARLAND_STREETS),
                "City": "Garland",
                "StateOrProvince": "TX",
                "PostalCode": "75041",
                "Latitude": loc.lat,
                "Longitude": loc.lng,
                "LivingArea": sqft,
                "BedroomsTotal": self._generate_bedrooms(sqft),
                "StandardStatus": "Closed"
            })
        
        return listings
