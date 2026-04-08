"""Pydantic models for API request/response schemas."""

from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from datetime import datetime


class Address(BaseModel):
    """Address model."""
    street: str = Field(..., description="Street address")
    city: str = Field(..., description="City name")
    state: str = Field(..., description="State abbreviation (e.g., TX)")
    zip: Optional[str] = Field(None, description="ZIP code")
    
    @field_validator('state')
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Normalize state to uppercase."""
        return v.upper()
    
    def to_full_address(self) -> str:
        """Convert to full address string."""
        parts = [self.street, self.city, self.state]
        if self.zip:
            parts.append(self.zip)
        return ", ".join(parts)


class PriceRequestOptions(BaseModel):
    """Options for price estimation request."""
    radius_miles: float = Field(1.0, ge=0.1, le=10.0, description="Search radius in miles")
    sold_lookback_days: int = Field(180, ge=30, le=730, description="Days to look back for sold comps")
    property_type: Literal["Residential", "Condominium", "Townhouse"] = "Residential"


class PriceRequest(BaseModel):
    """Request model for price estimation."""
    address: Address
    options: PriceRequestOptions = Field(default_factory=PriceRequestOptions)


class GeoLocation(BaseModel):
    """Geographic coordinates."""
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")


class PriceRange(BaseModel):
    """Price range model."""
    min: int = Field(..., description="Minimum estimated price")
    max: int = Field(..., description="Maximum estimated price")
    methodology: str = Field(..., description="Calculation methodology description")


class ListingSummary(BaseModel):
    """Summary of a listing."""
    address: str
    list_price: Optional[int] = None
    sold_price: Optional[int] = None
    days_on_market: int


class PriceResponseMetadata(BaseModel):
    """Metadata for price response."""
    comps_used: int
    search_radius_miles: float
    sold_lookback_days: int
    cached: bool
    generated_at: str


class PriceResponse(BaseModel):
    """Response model for price estimation."""
    address: dict[str, Optional[str]]
    price_range: PriceRange
    available_listings: list[ListingSummary]
    pending_listings: list[ListingSummary]
    sold_listings: list[ListingSummary]
    metadata: PriceResponseMetadata


class HealthResponse(BaseModel):
    """Health check response."""
    status: Literal["healthy", "unhealthy"]
    timestamp: str
    version: str


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    message: str
