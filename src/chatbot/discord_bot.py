"""Discord bot integration for Price-It.

To use:
1. Create a Discord bot at https://discord.com/developers/applications
2. Get the bot token
3. Add DISCORD_TOKEN=your_token_here to .env
4. Run: python src/chatbot/discord_bot.py
5. Invite bot to your server with messaging permissions
"""

import os
import sys
import re
import asyncio
import discord
from discord.ext import commands

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import get_settings

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

API_BASE_URL = "http://localhost:8000"


class PriceItDiscordBot(commands.Cog):
    """Discord bot commands for Price-It."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Called when bot is ready."""
        print(f"✅ Discord bot logged in as {self.bot.user}")
        print(f"   Bot is ready to accept commands!")
        print(f"   Try: !price 1406 Bentwood Dr, Garland, TX")
    
    @commands.command(name="price")
    async def get_price(self, ctx, *, address: str):
        """
        Get price estimate for an address.
        
        Usage: !price <address>
        Example: !price 1406 Bentwood Dr, Garland, TX
        """
        import httpx
        
        print(f"📨 Received request from {ctx.author}: {address}")
        
        # Show typing indicator
        async with ctx.typing():
            try:
                # Parse address
                address_parts = self._parse_address(address)
                
                # Call Price-It API
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{API_BASE_URL}/v1/price",
                        json={
                            "address": address_parts,
                            "options": {
                                "radius_miles": 1.0,
                                "sold_lookback_days": 180
                            }
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        await self._send_price_embed(ctx, data)
                    elif response.status_code == 404:
                        await ctx.send(f"❌ No comparable sales found for: {address}\nTry a different address or expand the search radius.")
                    else:
                        await ctx.send(f"❌ Error: Could not get price estimate. Status: {response.status_code}")
                        
            except httpx.ConnectError:
                await ctx.send("❌ Error: Cannot connect to Price-It API. Is the server running on localhost:8000?")
            except Exception as e:
                print(f"❌ Error: {e}")
                await ctx.send(f"❌ Error processing request: {str(e)}")
    
    @commands.command(name="ping")
    async def ping(self, ctx):
        """Check if bot is responsive."""
        await ctx.send(f"🏓 Pong! Bot latency: {round(self.bot.latency * 1000)}ms")
    
    @commands.command(name="help_price")
    async def help_price(self, ctx):
        """Show help for price command."""
        help_text = """
🤖 **Price-It Bot Commands**

**!price <address>** - Get price estimate
Examples:
  `!price 1406 Bentwood Dr, Garland, TX`
  `!price 123 Main St, Dallas, TX 75201`
  `!price 456 Oak Lane, Plano, TX`

**!ping** - Check bot status

**!help_price** - Show this help message

💡 **Tips:**
- Include city and state for best results
- ZIP code is optional but helpful
- Works best for residential addresses in North Texas
        """
        await ctx.send(help_text)
    
    def _parse_address(self, address_str: str) -> dict:
        """
        Parse address string into components.
        
        Supports formats like:
        - "1406 Bentwood Dr, Garland, TX"
        - "1406 Bentwood Dr, Garland, TX 75041"
        - "123 Main St, Dallas, TX 75201"
        """
        # Try to match pattern: street, city, state [zip]
        parts = [p.strip() for p in address_str.split(",")]
        
        if len(parts) >= 3:
            # Format: "street", "city", "state zip" or "state"
            street = parts[0]
            city = parts[1]
            state_zip = parts[2].strip().split()
            state = state_zip[0]
            zip_code = state_zip[1] if len(state_zip) > 1 else None
            
            return {
                "street": street,
                "city": city,
                "state": state,
                "zip": zip_code
            }
        elif len(parts) == 2:
            # Format: "street", "city state"
            return {
                "street": parts[0],
                "city": parts[1],
                "state": "TX",  # Default to TX
                "zip": None
            }
        else:
            # Can't parse, use as-is
            return {
                "street": address_str,
                "city": "Garland",
                "state": "TX",
                "zip": None
            }
    
    async def _send_price_embed(self, ctx, data: dict):
        """Send formatted price estimate as Discord embed."""
        price_range = data["price_range"]
        metadata = data["metadata"]
        address = data["address"]
        
        # Format prices
        min_price = f"${price_range['min']:,}"
        max_price = f"${price_range['max']:,}"
        
        # Create embed
        embed = discord.Embed(
            title="🏠 Price Estimate",
            description=f"**{address['full']}**",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="💰 Estimated Price Range",
            value=f"**{min_price} - {max_price}**",
            inline=False
        )
        
        embed.add_field(
            name="📊 Methodology",
            value=price_range['methodology'],
            inline=False
        )
        
        # Add market stats
        active_count = len(data.get("available_listings", []))
        pending_count = len(data.get("pending_listings", []))
        sold_count = metadata['comps_used']
        
        embed.add_field(
            name="📈 Market Activity",
            value=f"Active: {active_count} | Pending: {pending_count} | Sold (comps): {sold_count}",
            inline=False
        )
        
        # Add search parameters
        embed.add_field(
            name="🔍 Search Parameters",
            value=f"Radius: {metadata['search_radius_miles']} mi | Lookback: {metadata['sold_lookback_days']} days",
            inline=False
        )
        
        # Add footer
        cached = "✅ Cached" if metadata['cached'] else "🔄 Fresh"
        embed.set_footer(text=f"{cached} | Generated at {metadata['generated_at'][:19]}")
        
        await ctx.send(embed=embed)


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors."""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing address. Usage: `!price <address>`")
    else:
        print(f"Command error: {error}")
        await ctx.send(f"❌ An error occurred: {str(error)}")


def main():
    """Run the Discord bot."""
    settings = get_settings()
    
    if not settings.discord_token:
        print("❌ DISCORD_TOKEN not found in .env")
        print("   Please add: DISCORD_TOKEN=your_bot_token_here")
        print("   Get a token at: https://discord.com/developers/applications")
        return
    
    print("🤖 Starting Discord bot...")
    print(f"   API endpoint: {API_BASE_URL}")
    print("   Make sure the Price-It API is running!")
    
    bot.add_cog(PriceItDiscordBot(bot))
    bot.run(settings.discord_token)


if __name__ == "__main__":
    main()
