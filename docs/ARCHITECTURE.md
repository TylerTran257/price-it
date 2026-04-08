# Price-It Architecture

## Overview

Price-It is an on-demand service that returns a price range for a given address using MLS data sourced via RESO Web API. Designed for realtors and investors, it operates with minimum computation by caching results and using serverless deployment.

## Tech Stack

| Layer | Choice |
|-------|--------|
| **Runtime** | Python 3.12+ |
| **API Framework** | FastAPI |
| **MLS Adapter** | RESO Web API client (OAuth2) |
| **Cache** | Redis (ElastiCache) or DynamoDB |
| **Deployment** | AWS Lambda + API Gateway |
| **IaC** | AWS SAM |
| **Validation** | Pydantic v2 |
| **HTTP Client** | httpx (async) |
| **Geocoding** | Google Maps / Mapbox / Nominatim (configurable) |

## Project Structure

```
price-it/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── app.py                 # FastAPI app, routes
│   │   └── schemas.py             # Request/Response Pydantic models
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Env vars, settings
│   │   └── logger.py              # Structured logging
│   ├── mls/
│   │   ├── __init__.py
│   │   ├── client.py              # RESO Web API HTTP client
│   │   ├── auth.py                # OAuth2 auth handler
│   │   └── queries.py             # Standardized search queries (Active, Pending, Sold)
│   ├── pricing/
│   │   ├── __init__.py
│   │   ├── engine.py              # Price range calculation (percentile-based)
│   │   └── comparables.py         # Comp selection logic
│   ├── geocoding/
│   │   ├── __init__.py
│   │   └── service.py             # Address → lat/lng
│   └── cache/
│       ├── __init__.py
│       └── store.py               # Redis/DynamoDB cache layer
├── tests/
│   ├── test_api/
│   ├── test_mls/
│   ├── test_pricing/
│   └── test_cache/
├── sam.yaml                       # AWS SAM deployment config
├── requirements.txt
└── .env.example
```

## Request Flow

```
POST /v1/price
  │
  ├─ 1. Cache Check → address hash → HIT? return cached response
  │
  ├─ 2. Geocode → address → lat/lng
  │
  ├─ 3. MLS Client (RESO Web API)
  │     ├─ Query Active listings
  │     ├─ Query Pending listings
  │     └─ Query Sold listings (lookback window)
  │
  ├─ 4. Pricing Engine
  │     ├─ Filter comps (property type, sqft ±20%, bedroom ±1)
  │     ├─ Calculate $/sqft for each sold comp
  │     ├─ 25th percentile → min, 75th percentile → max
  │     └─ Apply to subject property estimated sqft
  │
  └─ 5. Assemble response → Cache → Return JSON
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Percentile-based pricing | Robust to outliers; 25th-75th gives realistic band |
| Cache by address hash | Eliminates redundant MLS calls; TTL configurable (24h) |
| RESO Web API adapter | Standard protocol; swap credentials without code changes |
| Lambda + API Gateway | Scales to zero; pay-per-invocation |
| Email/PDF deferred | Module hooks reserved in `src/notifications/` for future phase |

## Future Phases

- **Phase 2**: Email/PDF delivery module (`src/notifications/`)
- **Phase 3**: ML-based pricing model
- **Phase 4**: Batch processing for multiple addresses
