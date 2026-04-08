# 🏠 Price-It

**MLS-based real estate price estimation API for North Texas (NTREIS)**

A FastAPI application that provides on-demand price range estimates for residential properties using comparable sales data. Designed for realtors, investors, and chatbot integration.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env to add your credentials (or leave defaults for mock mode)
```

### 3. Run the API

```bash
python src/main.py
```

The API will start on `http://localhost:8000`

### 4. Test It

```bash
# Using the test script
python scripts/test_api.py "1406 Bentwood Dr, Garland, TX"

# Or using the CLI
python scripts/cli.py "1406 Bentwood Dr, Garland, TX"

# Or interactive mode
python scripts/cli.py -i
```

## 📖 API Endpoints

### Health Check
```bash
GET /health
```

### Get Price Estimate
```bash
POST /v1/price
Content-Type: application/json

{
  "address": {
    "street": "1406 Bentwood Dr",
    "city": "Garland",
    "state": "TX",
    "zip": "75041"
  },
  "options": {
    "radius_miles": 1.0,
    "sold_lookback_days": 180,
    "property_type": "Residential"
  }
}
```

**Response:**
```json
{
  "address": {
    "street": "1406 Bentwood Dr",
    "city": "Garland",
    "state": "TX",
    "zip": "75041",
    "full": "1406 Bentwood Dr, Garland, TX 75041"
  },
  "price_range": {
    "min": 285000,
    "max": 345000,
    "methodology": "25th-75th percentile of $/sqft from 12 comparable sales"
  },
  "available_listings": [...],
  "pending_listings": [...],
  "sold_listings": [...],
  "metadata": {
    "comps_used": 12,
    "search_radius_miles": 1.0,
    "sold_lookback_days": 180,
    "cached": false,
    "generated_at": "2026-04-08T12:00:00Z"
  }
}
```

## 🤖 Discord Bot

### Setup

1. Create a Discord bot at [Discord Developer Portal](https://discord.com/developers/applications)
2. Copy the bot token
3. Add to `.env`:
   ```
   DISCORD_TOKEN=your_bot_token_here
   ```

### Run Bot

```bash
python src/chatbot/discord_bot.py
```

### Commands

- `!price <address>` - Get price estimate
  - Example: `!price 1406 Bentwood Dr, Garland, TX`
- `!ping` - Check bot status
- `!help_price` - Show help

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  FastAPI    │────▶│  Nominatim  │
│  (Discord   │     │   Server    │     │  (Geocode)  │
│   / HTTP)   │     │             │     └─────────────┘
└─────────────┘     └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
       ┌──────▼──────┐          ┌──────▼──────┐
       │  In-Memory  │          │  Mock MLS   │
       │    Cache    │          │   Client    │
       └─────────────┘          └─────────────┘
```

### Components

- **API Layer** (`src/main.py`): FastAPI routes and request handling
- **Geocoding** (`src/geocoding/`): Nominatim integration (free, no API key)
- **Cache** (`src/cache/`): In-memory cache with TTL
- **MLS Client** (`src/mls/`): Mock data generator (swap for real NTREIS API)
- **Pricing Engine** (`src/pricing/`): Percentile-based price calculation
- **Discord Bot** (`src/chatbot/`): Chatbot integration

## 🧮 Pricing Methodology

1. **Geocode** address to lat/lng
2. **Fetch** Active, Pending, and Sold listings from MLS
3. **Filter** sold comps by:
   - Distance (within radius)
   - Square footage (±20%)
   - Bedrooms (±1)
4. **Calculate** price per sqft for each comp
5. **Remove** outliers using IQR method
6. **Apply** 25th-75th percentiles
7. **Return** price range applied to subject sqft

### Fallback Strategy

If insufficient comps found:
1. Expand radius to 2x
2. Expand radius to 5x
3. Extend lookback to 365 days
4. Relax sqft/bedroom filters

## ⚙️ Configuration

Environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | development | dev/staging/production |
| `MLS_PROVIDER` | mock | mock or ntreis |
| `CACHE_TTL_SECONDS` | 86400 | Cache time-to-live |
| `COMPS_RADIUS_MILES` | 1.0 | Default search radius |
| `SOLD_LOOKBACK_DAYS` | 180 | Days to look back |
| `PRICE_PERCENTILE_LOW` | 25 | Lower percentile |
| `PRICE_PERCENTILE_HIGH` | 75 | Upper percentile |
| `DISCORD_TOKEN` | - | Discord bot token |

## 🔄 Switching to Real NTREIS API

When you have NTREIS credentials:

1. Update `.env`:
   ```
   MLS_PROVIDER=ntreis
   MLS_RESO_URL=https://api.ntreis.net/reso/odata
   MLS_OAUTH_TOKEN_URL=https://api.ntreis.net/oauth/token
   MLS_CLIENT_ID=your_client_id
   MLS_CLIENT_SECRET=your_client_secret
   ```

2. Update `src/mls/client.py` to implement real API calls in the `search_*` methods

3. Restart the server

## 🧪 Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test price estimate
curl -X POST http://localhost:8000/v1/price \
  -H "Content-Type: application/json" \
  -d '{
    "address": {
      "street": "1406 Bentwood Dr",
      "city": "Garland",
      "state": "TX",
      "zip": "75041"
    }
  }'

# Run test script
python scripts/test_api.py

# Run CLI
python scripts/cli.py -i
```

## 📁 Project Structure

```
price-it/
├── src/
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Settings management
│   ├── api/
│   │   └── schemas.py          # Pydantic models
│   ├── cache/
│   │   └── store.py            # In-memory cache
│   ├── geocoding/
│   │   └── service.py          # Nominatim geocoding
│   ├── mls/
│   │   └── client.py           # MLS client (mock/real)
│   ├── pricing/
│   │   ├── comparables.py      # Comp selection
│   │   └── engine.py           # Price calculation
│   └── chatbot/
│       └── discord_bot.py      # Discord integration
├── scripts/
│   ├── test_api.py             # API test script
│   └── cli.py                  # Command-line interface
├── requirements.txt
├── .env.example
└── README.md
```

## 🚧 Roadmap

- [x] Core API with mock data
- [x] Free geocoding (Nominatim)
- [x] In-memory caching
- [x] Percentile-based pricing
- [x] Discord bot integration
- [ ] Real NTREIS API integration
- [ ] WhatsApp bot
- [ ] WeChat bot
- [ ] Redis cache option
- [ ] AWS Lambda deployment
- [ ] ML-based pricing model

## 📝 License

MIT

## 🤝 Support

For issues or questions, please open an issue on GitHub.

---

**Built for North Texas real estate professionals** 🏡
