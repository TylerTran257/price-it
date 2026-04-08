"""Simple test script for Price-It API.

Usage:
    python scripts/test_api.py
    python scripts/test_api.py "1406 Bentwood Dr, Garland, TX"
"""

import sys
import json
import httpx

API_BASE_URL = "http://localhost:8000"


def test_health():
    """Test health endpoint."""
    print("🏥 Testing health endpoint...")
    try:
        response = httpx.get(f"{API_BASE_URL}/health", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API is healthy!")
            print(f"   Status: {data['status']}")
            print(f"   Version: {data['version']}")
            print(f"   Timestamp: {data['timestamp']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except httpx.ConnectError:
        print(f"❌ Cannot connect to API at {API_BASE_URL}")
        print("   Make sure the server is running: python src/main.py")
        return False


def test_price_estimate(address_str: str):
    """Test price estimate endpoint."""
    print(f"\n🔍 Getting price estimate for: {address_str}")
    
    # Parse address (simple parser)
    parts = [p.strip() for p in address_str.split(",")]
    if len(parts) >= 3:
        address_data = {
            "street": parts[0],
            "city": parts[1],
            "state": parts[2].split()[0],
            "zip": parts[2].split()[1] if len(parts[2].split()) > 1 else None
        }
    else:
        print("❌ Could not parse address. Use format: 'Street, City, State ZIP'")
        return
    
    try:
        response = httpx.post(
            f"{API_BASE_URL}/v1/price",
            json={
                "address": address_data,
                "options": {
                    "radius_miles": 1.0,
                    "sold_lookback_days": 180
                }
            },
            timeout=30.0
        )
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Price estimate received!")
            print(f"\n🏠 Address: {data['address']['full']}")
            print(f"\n💰 Price Range: ${data['price_range']['min']:,} - ${data['price_range']['max']:,}")
            print(f"📊 Methodology: {data['price_range']['methodology']}")
            print(f"\n📈 Market Data:")
            print(f"   Active listings: {len(data['available_listings'])}")
            print(f"   Pending listings: {len(data['pending_listings'])}")
            print(f"   Sold comps used: {data['metadata']['comps_used']}")
            print(f"\n🔍 Search: {data['metadata']['search_radius_miles']} miles, {data['metadata']['sold_lookback_days']} days")
            print(f"💾 Cached: {data['metadata']['cached']}")
            
            # Show sample listings
            if data['available_listings']:
                print(f"\n📋 Sample Active Listings:")
                for listing in data['available_listings'][:3]:
                    print(f"   - {listing['address']}: ${listing['list_price']:,} ({listing['days_on_market']} days)")
            
            if data['sold_listings']:
                print(f"\n✅ Sample Sold Comps:")
                for listing in data['sold_listings'][:3]:
                    print(f"   - {listing['address']}: ${listing['sold_price']:,} ({listing['days_on_market']} days)")
            
            return True
            
        elif response.status_code == 404:
            print("❌ No comparable sales found for this address")
            print("   Try expanding the search radius or lookback period")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
            
    except httpx.ConnectError:
        print(f"❌ Cannot connect to API at {API_BASE_URL}")
        print("   Make sure the server is running: python src/main.py")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return False


def main():
    """Run tests."""
    print("=" * 50)
    print("🧪 Price-It API Test Script")
    print("=" * 50)
    
    # Test health
    if not test_health():
        sys.exit(1)
    
    # Test price estimate
    if len(sys.argv) > 1:
        address = sys.argv[1]
    else:
        address = "1406 Bentwood Dr, Garland, TX 75041"
        print(f"\nℹ️  No address provided, using default: {address}")
        print("   Usage: python scripts/test_api.py '<address>'")
    
    test_price_estimate(address)
    
    print("\n" + "=" * 50)
    print("✅ Test complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
