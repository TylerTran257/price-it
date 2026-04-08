# Development Guidelines

## Setup

```bash
# Clone repository
git clone <repo-url>
cd price-it

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Copy environment file
cp .env.example .env
# Edit .env with your credentials
```

## Requirements

### requirements.txt

```
fastapi==0.115.6
uvicorn==0.34.0
httpx==0.28.1
pydantic==2.10.4
pydantic-settings==2.7.1
redis==5.2.1
numpy==2.2.1
python-dotenv==1.0.1
```

### requirements-dev.txt

```
pytest==8.3.4
pytest-asyncio==0.25.2
ruff==0.9.4
mypy==1.14.1
httpx==0.28.1
respx==0.22.0
```

## Code Style

### Formatting

Use `ruff` for linting and formatting:

```bash
# Check
ruff check src/

# Fix auto-fixable issues
ruff check --fix src/

# Format
ruff format src/
```

### Type Checking

```bash
mypy src/
```

### Import Order

```python
# Standard library
import os
from datetime import datetime

# Third-party
import httpx
from fastapi import APIRouter
from pydantic import BaseModel

# Local
from src.mls.client import MLSClient
from src.pricing.engine import calculate_price_range
```

## Module Guidelines

### Each module should:

1. Have a single responsibility
2. Export public API via `__init__.py`
3. Include type hints on all functions
4. Include docstrings for public functions/classes
5. Handle errors gracefully (no bare `except:`)

### Example Module Structure

```python
# src/pricing/__init__.py
from .engine import calculate_price_range, estimate_price_range
from .comparables import select_comps, filter_outliers

__all__ = [
    "calculate_price_range",
    "estimate_price_range",
    "select_comps",
    "filter_outliers",
]
```

```python
# src/pricing/engine.py
"""Price range calculation using percentile-based methodology."""

import numpy as np

def calculate_price_per_sqft(comps: list[dict]) -> list[float]:
    """Calculate price per square foot for each comp.

    Args:
        comps: List of comparable sold listings with ClosePrice and LivingArea.

    Returns:
        List of price per sqft values.
    """
    return [
        comp["ClosePrice"] / comp["LivingArea"]
        for comp in comps
        if comp.get("LivingArea", 0) > 0
    ]
```

## Testing

### Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=term-missing

# Specific module
pytest tests/test_pricing/
```

### Test Structure

```
tests/
├── test_api/
│   ├── test_app.py          # FastAPI route tests
│   └── test_schemas.py      # Pydantic model tests
├── test_mls/
│   ├── test_client.py       # MLS client tests (mocked)
│   ├── test_auth.py         # OAuth tests
│   └── test_queries.py      # Query builder tests
├── test_pricing/
│   ├── test_engine.py       # Pricing algorithm tests
│   └── test_comparables.py  # Comp selection tests
├── test_cache/
│   └── test_store.py        # Cache layer tests
└── fixtures/
    ├── mls/                 # Sample MLS responses
    └── pricing/             # Sample comp data
```

### Mocking MLS Responses

```python
# tests/test_mls/test_client.py
import pytest
import respx
from httpx import Response

@respx.mock
@pytest.mark.asyncio
async def test_search_active_listings():
    respx.get("https://api.reso.org/odata/Property").mock(
        return_value=Response(200, json={
            "value": [
                {"ListingId": "123", "ListPrice": 350000, "StandardStatus": "Active"}
            ]
        })
    )

    client = MLSClient(auth=mock_auth, base_url="https://api.reso.org/")
    results = await client.search_active(...)
    assert len(results) == 1
```

## Git Workflow

```bash
# Feature branch
git checkout -b feature/add-cache-layer

# Commit (follow conventional commits)
git commit -m "feat: add Redis cache layer for price responses"

# Push and create PR
git push origin feature/add-cache-layer
```

### Commit Convention

| Type | Description |
|------|-------------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `refactor:` | Code refactoring |
| `test:` | Adding/updating tests |
| `chore:` | Maintenance tasks |

## Local Development

### Run Locally

```bash
# Using uvicorn
uvicorn src.api.app:app --reload --port 8000

# Using SAM (Lambda emulation)
sam build && sam local start-api
```

### Test Endpoint

```bash
curl -X POST http://localhost:8000/v1/price \
  -H "Content-Type: application/json" \
  -d '{
    "address": {
      "street": "123 Main St",
      "city": "Orlando",
      "state": "FL",
      "zip": "32801"
    }
  }'
```

## Debugging

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Common Issues

| Issue | Solution |
|-------|----------|
| MLS 401 errors | Check OAuth credentials and token expiry |
| No comps found | Expand radius/lookback in config |
| Lambda timeout | Increase timeout in sam.yaml (max 30s for REST API) |
| Import errors | Check PYTHONPATH or use relative imports |
