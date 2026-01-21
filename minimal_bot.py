import discord
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

print(f"Minimal Bot Starting... Token Length: {len(token) if token else 0}")

class MyClient(discord.Client):
    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

intents = discord.Intents.default()
client = MyClient(intents=intents)

try:
    client.run(token)
except Exception as e:
    print(f"CRITICAL ERROR: {e}")
