"""Configuration management using Pydantic Settings."""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Environment
    environment: str = "development"
    
    # Geocoding
    geocoding_provider: str = "nominatim"
    geocoding_api_key: str = ""  # Not needed for Nominatim
    
    # Cache
    cache_ttl_seconds: int = 86400  # 24 hours
    
    # MLS
    mls_provider: str = "mock"  # mock, ntreis, corelogic
    mls_reso_url: str = "https://api.cotality.com/trestle/odata"
    mls_oauth_token_url: str = "https://api.cotality.com/trestle/oidc/connect/token"
    mls_client_id: str = ""
    mls_client_secret: str = ""
    
    # Pricing Engine
    comps_radius_miles: float = Field(1.0, ge=0.1, le=10.0)
    sold_lookback_days: int = Field(180, ge=30, le=730)
    price_percentile_low: float = Field(25.0, ge=0, le=100)
    price_percentile_high: float = Field(75.0, ge=0, le=100)
    sqft_tolerance_pct: float = Field(20.0, ge=0, le=50)
    bedroom_tolerance: int = Field(1, ge=0, le=3)
    min_comps_required: int = Field(3, ge=1, le=10)
    
    # Discord (optional)
    discord_token: str = ""
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
