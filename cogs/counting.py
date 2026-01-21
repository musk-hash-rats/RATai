import discord
from discord import app_commands
from discord.ext import commands
from utils.database import set_counting_channel, get_counting_data, update_counting_data
import math

def safe_eval(expression):
    # Restricted environment
    allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
    allowed_names["__builtins__"] = None
    
    try:
        # Simple length check to prevent massive operations
        if len(expression) > 50: 
            return None
            
        code = compile(expression, "<string>", "eval")
        
        # Check for disallowed codes if needed, but builtins=None is strong.
        return eval(code, allowed_names, {})
    except:
        return None

class Counting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.locks = {}

    @app_commands.command(name="setup_counting", description="Sets the channel for the counting game.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_counting(self, interaction: discord.Interaction):
        await set_counting_channel(interaction.guild.id, interaction.channel.id)
        await interaction.response.send_message(f"Counting channel set to {interaction.channel.mention}. Start with **1**!")

    @app_commands.command(name="set_count", description="Manually sets the count (Admin only).")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_count(self, interaction: discord.Interaction, count: int):
        data = await get_counting_data(interaction.guild.id)
        if not data:
             return await interaction.response.send_message("Please run /setup_counting first.", ephemeral=True)
        
        # Keep high score, just change current
        await update_counting_data(interaction.guild.id, count, 0, max(data[3], count))
        await interaction.response.send_message(f"Count manually set to **{count}**.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        data = await get_counting_data(message.guild.id)
        if not data:
            return

        # Prepare lock for guild
        if message.guild.id not in self.locks:
            self.locks[message.guild.id] = asyncio.Lock()

        async with self.locks[message.guild.id]:
            # RE-FETCH DATA to ensure atomicity under lock
            data = await get_counting_data(message.guild.id)
            if not data:
                return

            channel_id, current_count, last_user_id, high_score = data
            
            # Check if message is in the counting channel (Double check strictly)
            if message.channel.id != channel_id:
                return

            # LOGIC: Try to evaluate math
            result = safe_eval(message.content)
            
            if result is None or not isinstance(result, (int, float)):
                return

            number = int(result) # floor it? or round? Usually int.
            
            if abs(result - round(result)) > 0.001:
                 pass
            else:
                 number = int(round(result))

            # 1. Double Counting
            if message.author.id == last_user_id:
                await message.add_reaction("❌")
                await message.channel.send(f"**FAILED!** {message.author.mention} counted twice in a row! Resetting to 0.")
                await update_counting_data(message.guild.id, 0, 0, high_score)
                return

            # 2. Correct Number
            if number == current_count + 1:
                await message.add_reaction("✅")
                new_high = max(high_score, number)
                await update_counting_data(message.guild.id, number, message.author.id, new_high)
                
                # Update User Stats
                from utils.database import increment_counting_stat
                await increment_counting_stat(message.author.id, message.guild.id)
                
                # Milestone celebration?
                if number % 100 == 0:
                    await message.add_reaction("🎉")
                    
            else:
                await message.add_reaction("❌")
                await message.channel.send(f"**FAILED!** {message.author.mention} math was off! **{message.content}** = {number}. Expected **{current_count + 1}**. Resetting to 0.")
                await update_counting_data(message.guild.id, 0, 0, high_score)

    @app_commands.command(name="counting_leaderboard", description="Shows the top counters in the server.")
    async def counting_leaderboard(self, interaction: discord.Interaction):
        from utils.database import get_top_counters
        top_counters = await get_top_counters(interaction.guild.id)
        
        if not top_counters:
             return await interaction.response.send_message("No counting stats yet!", ephemeral=True)

        embed = discord.Embed(title="🧮 Counting Leaderboard", color=discord.Color.green())
        description = ""
        
        for i, (user_id, count) in enumerate(top_counters, 1):
            member = interaction.guild.get_member(user_id)
            name = member.display_name if member else f"User {user_id}"
            description += f"**{i}. {name}**: {count} correct counts\n"
            
        embed.description = description
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Counting(bot))
