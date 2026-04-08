# API Specification

## Base URL

```
https://{api-gateway-id}.execute-api.{region}.amazonaws.com/{stage}
```

## Endpoints

### POST /v1/price

Returns a price range for a given address using MLS comparable data.

#### Request

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "address": {
    "street": "123 Main St",
    "city": "Orlando",
    "state": "FL",
    "zip": "32801"
  },
  "options": {
    "radius_miles": 1.0,
    "sold_lookback_days": 180,
    "property_type": "Residential"
  }
}
```

**Fields:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `address.street` | string | Yes | - | Street address |
| `address.city` | string | Yes | - | City |
| `address.state` | string | Yes | - | State abbreviation |
| `address.zip` | string | No | - | ZIP code |
| `options.radius_miles` | float | No | 1.0 | Search radius for comps |
| `options.sold_lookback_days` | int | No | 180 | Days to look back for sold comps |
| `options.property_type` | string | No | "Residential" | Property type filter |

#### Response (200 OK)

```json
{
  "address": {
    "street": "123 Main St",
    "city": "Orlando",
    "state": "FL",
    "zip": "32801",
    "full": "123 Main St, Orlando, FL 32801"
  },
  "price_range": {
    "min": 325000,
    "max": 385000,
    "methodology": "25th-75th percentile of $/sqft from sold comps"
  },
  "available_listings": [
    {
      "address": "125 Main St, Orlando, FL 32801",
      "list_price": 349900,
      "days_on_market": 14
    }
  ],
  "pending_listings": [
    {
      "address": "130 Main St, Orlando, FL 32801",
      "list_price": 339000,
      "days_on_market": 7
    }
  ],
  "sold_listings": [
    {
      "address": "118 Main St, Orlando, FL 32801",
      "sold_price": 342000,
      "days_on_market": 21
    }
  ],
  "metadata": {
    "comps_used": 12,
    "search_radius_miles": 1.0,
    "sold_lookback_days": 180,
    "cached": false,
    "generated_at": "2026-04-07T12:00:00Z"
  }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `address` | object | Normalized address |
| `address.full` | string | Full formatted address |
| `price_range.min` | int | Estimated minimum price |
| `price_range.max` | int | Estimated maximum price |
| `price_range.methodology` | string | Calculation method description |
| `available_listings[]` | array | Active listings in area |
| `available_listings[].address` | string | Listing address |
| `available_listings[].list_price` | int | Current list price |
| `available_listings[].days_on_market` | int | Days on market |
| `pending_listings[]` | array | Pending listings in area |
| `pending_listings[].address` | string | Listing address |
| `pending_listings[].list_price` | int | Current list price |
| `pending_listings[].days_on_market` | int | Days on market |
| `sold_listings[]` | array | Sold listings in area |
| `sold_listings[].address` | string | Listing address |
| `sold_listings[].sold_price` | int | Final sold price |
| `sold_listings[].days_on_market` | int | Days on market until closed |
| `metadata.comps_used` | int | Number of comps used in calculation |
| `metadata.search_radius_miles` | float | Radius used for search |
| `metadata.sold_lookback_days` | int | Lookback period used |
| `metadata.cached` | bool | Whether response was from cache |
| `metadata.generated_at` | string | ISO 8601 timestamp |

#### Error Responses

**400 Bad Request**
```json
{
  "error": "validation_error",
  "message": "Invalid address: city is required",
  "details": [...]
}
```

**404 Not Found**
```json
{
  "error": "not_found",
  "message": "No comparable listings found for this address"
}
```

**500 Internal Server Error**
```json
{
  "error": "internal_error",
  "message": "Failed to fetch MLS data"
}
```

### GET /health

Health check endpoint.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2026-04-07T12:00:00Z",
  "version": "1.0.0"
}
```

## Rate Limiting

- Default: 100 requests per minute per API key
- Configurable via API Gateway usage plans

## Authentication

- API key via `x-api-key` header (managed by API Gateway)
