# MLS Integration Guide

## RESO Web API Overview

The RESO Web API is a RESTful API based on OData protocol. It provides standardized access to MLS listing data.

## Authentication

RESO Web API uses OAuth 2.0 client credentials flow.

### Flow

```
1. Client sends POST to MLS OAuth token endpoint
2. MLS returns access_token (JWT)
3. Include token in subsequent requests: Authorization: Bearer <token>
4. Token expires; refresh as needed
```

### Configuration

```env
MLS_RESO_URL=https://api.reso.org/
MLS_OAUTH_TOKEN_URL=https://auth.reso.org/token
MLS_CLIENT_ID=your_client_id
MLS_CLIENT_SECRET=your_client_secret
```

## Module Structure

```
src/mls/
├── __init__.py
├── client.py      # RESO Web API HTTP client
├── auth.py        # OAuth2 auth handler
└── queries.py     # Standardized search queries
```

## Implementation Details

### auth.py

Handles OAuth2 token management with automatic refresh.

```python
class MLSAuth:
    async def get_token(self) -> str
    async def refresh_token(self) -> str
    def is_token_valid(self) -> bool
```

### client.py

Async HTTP client for RESO Web API endpoints.

```python
class MLSClient:
    def __init__(self, auth: MLSAuth, base_url: str)
    async def search(self, resource: str, filters: dict, select: list) -> list[dict]
    async def get_property(self, listing_id: str) -> dict
```

### queries.py

Pre-built query builders for common MLS searches.

```python
class MLSQueries:
    @staticmethod
    def active_listings(lat: float, lng: float, radius: float, property_type: str) -> dict
    @staticmethod
    def pending_listings(lat: float, lng: float, radius: float, property_type: str) -> dict
    @staticmethod
    def sold_listings(lat: float, lng: float, radius: float, lookback_days: int, property_type: str) -> dict
```

## RESO Web API Resources

| Resource | Description |
|----------|-------------|
| Property | Property characteristics (sqft, beds, baths, year built, etc.) |
| Listing | Listing details (status, list price, days on market, etc.) |
| Media | Photos, documents, virtual tours |

## Standard Fields Used

### Listing Fields

| Field | RESO Standard Name | Type |
|-------|-------------------|------|
| Listing ID | `ListingId` | string |
| Status | `StandardStatus` | string (Active, Pending, Closed) |
| List Price | `ListPrice` | int |
| Original List Price | `OriginalListPrice` | int |
| Days on Market | `DaysOnMarket` | int |
| Listing Date | `ListingContractDate` | date |
| Close Date | `CloseDate` | date |

### Property Fields

| Field | RESO Standard Name | Type |
|-------|-------------------|------|
| Street Number | `StreetNumber` | string |
| Street Name | `StreetName` | string |
| City | `City` | string |
| State/Province | `StateOrProvince` | string |
| Postal Code | `PostalCode` | string |
| Latitude | `Latitude` | float |
| Longitude | `Longitude` | float |
| Living Area | `LivingArea` | float |
| Bedrooms Total | `BedroomsTotal` | int |
| Bathrooms Total Integer | `BathroomsTotalInteger` | int |
| Property Type | `PropertyType` | string |
| Property Sub Type | `PropertySubType` | string |

## OData Query Examples

### Active Listings within Radius

```
GET /odata/Property?$filter=
  StandardStatus eq 'Active'
  and PropertyType eq 'Residential'
  and LivingArea gt 1000
  and LivingArea lt 3000
&$select=ListingId,ListPrice,DaysOnMarket,StreetNumber,StreetName,City,StateOrProvince,PostalCode,Latitude,Longitude,LivingArea,BedroomsTotal
```

### Sold Listings (Last 180 Days)

```
GET /odata/Property?$filter=
  StandardStatus eq 'Closed'
  and CloseDate ge 2025-10-09
  and PropertyType eq 'Residential'
&$select=ListingId,ClosePrice,DaysOnMarket,CloseDate,StreetNumber,StreetName,City,StateOrProvince,PostalCode,Latitude,Longitude,LivingArea,BedroomsTotal
```

## Error Handling

| HTTP Status | Meaning | Action |
|-------------|---------|--------|
| 401 | Unauthorized | Refresh OAuth token |
| 403 | Forbidden | Check credentials/permissions |
| 429 | Rate Limited | Implement backoff |
| 500 | Server Error | Retry with exponential backoff |

## Credentials Management

MLS credentials are stored as environment variables and injected via AWS Secrets Manager in production.

```python
# src/core/config.py
class Settings(BaseSettings):
    mls_reso_url: str
    mls_oauth_token_url: str
    mls_client_id: str
    mls_client_secret: str

    class Config:
        env_file = ".env"
```

## Testing

Use mocked MLS responses for unit tests. Store sample RESO responses in `tests/fixtures/mls/`.

```python
# tests/test_mls/test_client.py
@pytest.mark.asyncio
async def test_search_active_listings(mock_mls_client):
    results = await mock_mls_client.search_active(...)
    assert len(results) > 0
    assert all(r["StandardStatus"] == "Active" for r in results)
```
