import discord
from discord import app_commands
from discord.ext import commands
from utils.database import get_config, set_config
import random
import time
from collections import deque

RAT_DANCE_GIF = "https://media.tenor.com/tT2X1l15Hq8AAAAM/rat-dancing.gif"

class Personality(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_timestamps = deque()

    def update_activity_level(self):
        now = time.time()
        # Remove messages older than 60 seconds
        while self.message_timestamps and now - self.message_timestamps[0] > 60:
            self.message_timestamps.popleft()
        self.message_timestamps.append(now)
        return len(self.message_timestamps)

    @app_commands.command(name="rat_frequency", description="Set how often the rat dances (0-10).")
    @app_commands.checks.has_permissions(administrator=True)
    async def rat_frequency(self, interaction: discord.Interaction, level: int):
        if level < 0 or level > 10:
            return await interaction.response.send_message("Please pick a level between 0 and 10.", ephemeral=True)
            
        await set_config("rat_frequency", str(level))
        await interaction.response.send_message(f"Rat Dance Frequency set to **{level}/10**! 🐀💃")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # 1. Random Cheese (1%)
        if random.randint(1, 100) == 1:
            if random.choice([True, False]):
                await message.add_reaction("🧀")
            else:
                await message.channel.send("*squeak* 🧀")

        # 2. Rat Dance Logic
        # Frequency scale: 0 = Off. 10 = Max.
        # Logic: Chance = (Activity * Frequency) / 100
        # Example: 10 msgs/min * Freq 5 = 50% chance per message? Too high.
        # Maybe per minute? Or check on message with low base?
        # Let's do: Chance = (Activity * Frequency) / 20.
        # If 20 msgs/min (active) * Freq 5 = 100/20 = 5% chance per msg.
        
        freq_str = await get_config("rat_frequency", "3") # Default 3
        try:
            frequency = int(freq_str)
        except:
            frequency = 3
            
        if frequency == 0:
            return

        msgs_per_min = self.update_activity_level()
        
        # Don't spam if inactive
        if msgs_per_min < 3:
            return
            
        # Chance to execute
        dance_chance = (msgs_per_min * frequency) / 50.0 # Adjusted down.
        # 20 msgs * 5 freq = 100 / 50 = 2% chance per msg.
        
        if random.random() * 100 < dance_chance:
            await message.channel.send(f"🐀 **RAT PARTY!** 🐀\n{RAT_DANCE_GIF}")

async def setup(bot):
    await bot.add_cog(Personality(bot))
