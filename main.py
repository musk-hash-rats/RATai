import discord
import os
import asyncio
from discord.ext import commands
from aiohttp import web
from utils.database import init_db
from utils.env_loader import load_env_manual

# Load environment using manual loader (bypassing python-dotenv)
env_config = load_env_manual()
TOKEN = os.environ.get('DISCORD_TOKEN')

# Fix for Mac/Homebrew Opus
import discord.opus
if not discord.opus.is_loaded():
    try:
        # Common path for Homebrew on Apple Silicon
        discord.opus.load_opus("/opt/homebrew/lib/libopus.dylib")
        print("✅ Manually loaded Opus from Homebrew path.")
    except Exception as e:
        print(f"⚠️ Failed to manually load Opus: {e}")

# Cloud Run Health Check Server
async def health_check(request):
    return web.Response(text="RATai is alive", status=200)

async def start_dummy_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    # Cloud Run injects PORT (default 8080)
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"🌐 Cloud Run Web Server running on port {port}")

class RATaiBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True
        intents.voice_states = True
        
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        # Database init
        await init_db()
        print("Database initialized.")
        
        # Load extensions
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
                print(f'Loaded extension: {filename}')

        # Sync Slash Commands
        guild_id = os.getenv('GUILD_ID')
        if guild_id:
            guild = discord.Object(id=guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Slash commands synced to guild: {guild_id}")
        else:
            await self.tree.sync()
            print("Slash commands synced globally.")

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('RATai is ready! Use /rank to check your stats.')

bot = RATaiBot()

async def main():
    # 1. Start Cloud Run Health Check Server (Critical for deployment)
    await start_dummy_server()
    
    # 2. Check Token
    if not TOKEN:
        print("❌ Error: DISCORD_TOKEN not found in .env or Environment Variables!")
        # Keep web server running so Cloud Run doesn't kill us immediately, allowing logs to be read
        while True:
            await asyncio.sleep(3600)
    
    print(f"DEBUG: Attempting login with token starting with: {TOKEN[:5]}...")
    
    # 3. Start Bot
    async with bot:
        await bot.start(TOKEN)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Handle simple Ctrl+C locally
        pass
    except Exception as e:
        print(f"❌ Fatal Error: {e}")
