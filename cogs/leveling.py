import discord
from discord.ext import commands, tasks
from discord import app_commands
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from utils.database import add_xp, get_user_data, add_reaction_count, get_top_users, get_reaction_count, add_user_flag, has_user_flag
import time
import random
from collections import deque

TARGET_ID = 689548918455140403

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.analyzer = SentimentIntensityAnalyzer()
        self.voice_states = {} # {member_id: join_time}
        self.live_leaderboard_channel_id = None
        self.live_leaderboard_message_id = None
        
        # Dynamic Reaction State
        self.message_timestamps = deque() # Stores timestamps of recent messages
        
        # Start tasks
        self.update_leaderboard_task.start()

    def cog_unload(self):
        self.update_leaderboard_task.cancel()

    def update_activity_level(self):
        now = time.time()
        # Remove messages older than 60 seconds
        while self.message_timestamps and now - self.message_timestamps[0] > 60:
            self.message_timestamps.popleft()
        self.message_timestamps.append(now)
        
        return len(self.message_timestamps)

    def get_reaction_emoji(self, compound_score):
        # Emojis: 🖕, 😂, 😈, 😭
        if compound_score >= 0.3:
            return random.choice(['😂', '😈'])
        elif compound_score <= -0.3:
            return random.choice(['🖕', '😭'])
        else:
             # Random chance for any if neutral
            return random.choice(['😂', '😈', '🖕', '😭'])

    def calculate_sentiment_multiplier(self, text):
        scores = self.analyzer.polarity_scores(text)
        compound = scores['compound']
        intensity = abs(compound)
        
        # "Toxicity is promoted" -> Reward High Intensity
        if intensity >= 0.5:
            return 2.0, intensity, compound # Return compound for reaction logic
        else:
            return 0.5, intensity, compound

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # --- TARGET HARASSMENT LOGIC ---
        if message.author.id == TARGET_ID:
            intro_sent = await has_user_flag(message.author.id, "harassed_intro_sent")
            if not intro_sent:
                await message.reply("bro, 2eyes2c went out of his way to program me to despise you, your cooked")
                await add_user_flag(message.author.id, "harassed_intro_sent")
            else:
                # Random chance to remove XP and mock
                if random.randint(1, 100) <= 20: # 20% chance
                    await message.add_reaction("😂")
                    await message.reply("lol cooked")
                    # Remove XP
                    await add_xp(message.author.id, message.guild.id, -2.0)
                    return # Exit early, don't give XP

        # Sentiment Analysis
        multiplier, intensity, compound = self.calculate_sentiment_multiplier(message.content)
        base_xp = 10
        
        # Booster Multiplier
        if message.author.premium_since:
            base_xp *= 1.5
            
        xp_to_give = base_xp * multiplier
        
        # Update Activity & Check for Reaction
        msgs_per_min = self.update_activity_level()
        
        # Chance to react increases with activity.
        # Base: 5%. Add 2% per message/min. Cap at 50%.
        reaction_chance = 5 + (msgs_per_min * 2)
        if reaction_chance > 50: reaction_chance = 50
        
        if random.randint(1, 100) <= reaction_chance:
            emoji = self.get_reaction_emoji(compound)
            try:
                await message.add_reaction(emoji)
            except:
                pass # Missing permissions etc.

        # Award XP
        await add_xp(message.author.id, message.guild.id, xp_to_give)
        
        # Debug print (optional, can be removed)
        # print(f"User: {message.author}, Msg: {message.content}, Int: {intensity:.2f}, Mult: {multiplier}, XP: {xp_to_give}")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        
        # Award XP for reacting
        await add_xp(user.id, reaction.message.guild.id, 2)
        await add_reaction_count(user.id, reaction.message.guild.id)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        # User joined a voice channel
        if before.channel is None and after.channel is not None:
            self.voice_states[member.id] = time.time()
        
        # User left a voice channel
        elif before.channel is not None and after.channel is None:
            if member.id in self.voice_states:
                join_time = self.voice_states.pop(member.id)
                duration = time.time() - join_time
                minutes = duration / 60
                
                # 5 XP per minute in VC
                xp_earned = minutes * 5
                await add_xp(member.id, member.guild.id, xp_earned)

    @app_commands.command(name="rank", description="Check your or another user's level and XP.")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        data = await get_user_data(member.id, interaction.guild.id)
        rxn_count = await get_reaction_count(member.id, interaction.guild.id)
        
        if data:
            xp, level = data
            embed = discord.Embed(title=f"{member.name}'s Stats", color=discord.Color.blue())
            embed.add_field(name="Level", value=str(level), inline=True)
            embed.add_field(name="XP", value=f"{xp:.2f}", inline=True)
            embed.add_field(name="Reactions Given", value=str(rxn_count), inline=False)
            embed.set_thumbnail(url=member.display_avatar.url)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"{member.name} has no stats yet.")

    @app_commands.command(name="setleaderboard", description="Sets the current channel for the live leaderboard.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setleaderboard(self, interaction: discord.Interaction):
        """Sets the current channel as the live leaderboard channel."""
        self.live_leaderboard_channel_id = interaction.channel.id
        await interaction.response.send_message("Initializing Live Leaderboard...", ephemeral=True)
        msg = await interaction.channel.send("Loading Leaderboard...")
        self.live_leaderboard_message_id = msg.id

    @tasks.loop(minutes=2)
    async def update_leaderboard_task(self):
        if not self.live_leaderboard_channel_id or not self.live_leaderboard_message_id:
            return

        channel = self.bot.get_channel(self.live_leaderboard_channel_id)
        if not channel:
            return
        
        try:
            message = await channel.fetch_message(self.live_leaderboard_message_id)
        except discord.NotFound:
            # Message deleted, reset? or create new? For now just return
            return
            
        top_users = await get_top_users(channel.guild.id, limit=10)
        
        embed = discord.Embed(title="🏆 RATai Live Leaderboard 🏆", description="Top 10 Users by XP (Updates every 2 mins)", color=discord.Color.gold())
        
        leaderboard_text = ""
        for i, (user_id, xp, level) in enumerate(top_users, 1):
            member = channel.guild.get_member(user_id)
            name = member.display_name if member else f"User {user_id}"
            leaderboard_text += f"**{i}. {name}** - Lv {level} ({xp:.0f} XP)\n"
            
        embed.add_field(name="Rankings", value=leaderboard_text or "No data yet.", inline=False)
        embed.set_footer(text=f"Last Updated: {time.strftime('%H:%M:%S')}")
        
        await message.edit(content="", embed=embed)

    @update_leaderboard_task.before_loop
    async def before_update_leaderboard(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Leveling(bot))
