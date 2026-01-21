import discord
from discord import app_commands
from discord.ext import commands
from utils.database import set_counting_channel

class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup", description="[Admin] Automatically sets up roles, channels, and categories for the bot.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_server(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        log = []

        # 1. Create Roles
        jail_role = discord.utils.get(guild.roles, name="Jailed")
        if not jail_role:
            jail_role = await guild.create_role(name="Jailed", color=discord.Color.dark_grey())
            log.append("✅ Created role: **Jailed**")
        else:
            log.append("ℹ️ Role **Jailed** already exists.")

        mod_role = discord.utils.get(guild.roles, name="Jail Mod")
        if not mod_role:
            mod_role = await guild.create_role(name="Jail Mod", color=discord.Color.dark_blue())
            log.append("✅ Created role: **Jail Mod**")
        else:
            log.append("ℹ️ Role **Jail Mod** already exists.")

        # 2. Create Categories
        private_cat = discord.utils.get(guild.categories, name="Private Channels")
        if not private_cat:
            private_cat = await guild.create_category("Private Channels")
            log.append("✅ Created category: **Private Channels**")
        else:
            log.append("ℹ️ Category **Private Channels** already exists.")

        # 3. Create Channels
        # Jail Cell
        jail_channel = discord.utils.get(guild.text_channels, name="jail-cell")
        jail_overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            jail_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if not jail_channel:
            jail_channel = await guild.create_text_channel("jail-cell", overwrites=jail_overwrites)
            log.append("✅ Created channel: **jail-cell**")
        else:
            # Enforce overrides
            await jail_channel.edit(overwrites=jail_overwrites)
            log.append("ℹ️ Channel **jail-cell** exits (updated permissions).")

        # Counting Channel
        counting_channel = discord.utils.get(guild.text_channels, name="counting")
        if not counting_channel:
            counting_channel = await guild.create_text_channel("counting")
            log.append("✅ Created channel: **counting**")
        else:
            log.append("ℹ️ Channel **counting** already exists.")
        
        # Register Counting Channel in DB
        await set_counting_channel(guild.id, counting_channel.id)
        log.append("✅ Registered **counting** channel in database.")

        # 4. Final Report
        report = "\n".join(log)
        await interaction.followup.send(f"**Setup Complete!** 🐀\n\n{report}")

async def setup(bot):
    await bot.add_cog(Setup(bot))
