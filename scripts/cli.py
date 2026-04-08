"""Simple CLI for Price-It.

Usage:
    python scripts/cli.py
    python scripts/cli.py "1406 Bentwood Dr, Garland, TX"

Interactive mode:
    python scripts/cli.py -i
"""

import sys
import argparse
import httpx
from datetime import datetime

API_BASE_URL = "http://localhost:8000"


def get_price_estimate(address_data: dict, radius: float = 1.0, lookback: int = 180):
    """Get price estimate from API."""
    try:
        response = httpx.post(
            f"{API_BASE_URL}/v1/price",
            json={
                "address": address_data,
                "options": {
                    "radius_miles": radius,
                    "sold_lookback_days": lookback
                }
            },
            timeout=30.0
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            print("❌ No comparable sales found. Try expanding search parameters.")
            return None
        else:
            print(f"❌ Error: {response.status_code}")
            return None
            
    except httpx.ConnectError:
        print(f"❌ Cannot connect to API at {API_BASE_URL}")
        print("   Start the server: python src/main.py")
        return None


def display_result(data: dict):
    """Display price estimate in a nice format."""
    if not data:
        return
    
    print("\n" + "=" * 60)
    print("🏠 PRICE ESTIMATE")
    print("=" * 60)
    
    print(f"\n📍 Address: {data['address']['full']}")
    
    print(f"\n💰 Estimated Price Range:")
    print(f"   ${data['price_range']['min']:,} - ${data['price_range']['max']:,}")
    
    print(f"\n📊 Methodology:")
    print(f"   {data['price_range']['methodology']}")
    
    print(f"\n📈 Market Activity:")
    print(f"   • Active Listings: {len(data['available_listings'])}")
    print(f"   • Pending Listings: {len(data['pending_listings'])}")
    print(f"   • Sold Comps Used: {data['metadata']['comps_used']}")
    
    print(f"\n🔍 Search Parameters:")
    print(f"   • Radius: {data['metadata']['search_radius_miles']} miles")
    print(f"   • Lookback: {data['metadata']['sold_lookback_days']} days")
    print(f"   • Cached: {'Yes' if data['metadata']['cached'] else 'No'}")
    
    if data['available_listings']:
        print(f"\n📋 Top Active Listings:")
        for i, listing in enumerate(data['available_listings'][:5], 1):
            print(f"   {i}. {listing['address']}")
            print(f"      List Price: ${listing['list_price']:,} | DOM: {listing['days_on_market']}")
    
    print("\n" + "=" * 60)


def parse_address(address_str: str) -> dict:
    """Parse address string."""
    parts = [p.strip() for p in address_str.split(",")]
    
    if len(parts) >= 3:
        return {
            "street": parts[0],
            "city": parts[1],
            "state": parts[2].split()[0],
            "zip": parts[2].split()[1] if len(parts[2].split()) > 1 else None
        }
    elif len(parts) == 2:
        return {
            "street": parts[0],
            "city": parts[1],
            "state": "TX",
            "zip": None
        }
    else:
        return {
            "street": address_str,
            "city": "Garland",
            "state": "TX",
            "zip": None
        }


def interactive_mode():
    """Run in interactive mode."""
    print("\n🏠 Price-It Interactive CLI")
    print("Type 'quit' to exit, 'help' for commands\n")
    
    while True:
        try:
            user_input = input("Enter address: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if user_input.lower() == 'help':
                print("\nCommands:")
                print("  <address>  - Get price estimate (e.g., '123 Main St, Dallas, TX')")
                print("  help       - Show this help")
                print("  quit       - Exit\n")
                continue
            
            if not user_input:
                continue
            
            address_data = parse_address(user_input)
            result = get_price_estimate(address_data)
            display_result(result)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Price-It CLI")
    parser.add_argument("address", nargs="?", help="Address to estimate")
    parser.add_argument("-i", "--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("-r", "--radius", type=float, default=1.0, help="Search radius in miles")
    parser.add_argument("-l", "--lookback", type=int, default=180, help="Lookback days for sold comps")
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
    elif args.address:
        address_data = parse_address(args.address)
        result = get_price_estimate(address_data, args.radius, args.lookback)
        display_result(result)
    else:
        # Default test address
        print("ℹ️  No address provided. Using default: 1406 Bentwood Dr, Garland, TX")
        print("   Use -i for interactive mode or provide an address\n")
        address_data = parse_address("1406 Bentwood Dr, Garland, TX")
        result = get_price_estimate(address_data)
        display_result(result)


if __name__ == "__main__":
    main()
