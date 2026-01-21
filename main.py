import discord
import os
import asyncio
from discord.ext import commands
# from dotenv import load_dotenv # Removed
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

class RATaiBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True
        intents.voice_states = True
        
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
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

if __name__ == '__main__':
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in .env")
    else:
        print(f"DEBUG: Attempting login with token starting with: {TOKEN[:5]}... (Length: {len(TOKEN)})")
        bot.run(TOKEN)
