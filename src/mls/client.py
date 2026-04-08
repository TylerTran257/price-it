"""MLS client - currently using mock data for POC."""

import random
from typing import List, Dict, Any
from datetime import datetime, timedelta
from src.api.schemas import GeoLocation


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
    
    async def search_active(
        self,
        location: GeoLocation,
        radius_miles: float,
        property_type: str = "Residential"
    ) -> List[Dict[str, Any]]:
        """Search active listings."""
        if self.use_mock:
            return self._mock_data_generator.generate_active_listings(location, radius_miles)
        # TODO: Implement real NTREIS API call
        raise NotImplementedError("Real MLS API not implemented yet")
    
    async def search_pending(
        self,
        location: GeoLocation,
        radius_miles: float,
        property_type: str = "Residential"
    ) -> List[Dict[str, Any]]:
        """Search pending listings."""
        if self.use_mock:
            return self._mock_data_generator.generate_pending_listings(location, radius_miles)
        raise NotImplementedError("Real MLS API not implemented yet")
    
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
        raise NotImplementedError("Real MLS API not implemented yet")


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
