import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import time
import asyncio
from utils.database import add_active_jail, get_active_jail, remove_active_jail, get_expired_jails

class Jail(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.jail_check_loop.start()

    def cog_unload(self):
        self.jail_check_loop.cancel()

    async def get_jail_roles(self, guild):
        jail_role = discord.utils.get(guild.roles, name="Jailed")
        mod_role = discord.utils.get(guild.roles, name="Jail Mod")
        return jail_role, mod_role

    @app_commands.command(name="setup_jail", description="Creates the Jailed role, Jail Mod role, and jail-cell channel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_jail(self, interaction: discord.Interaction):
        guild = interaction.guild
        await interaction.response.send_message("Setting up Jail System...", ephemeral=True)
        
        # 1. Create Roles
        jail_role = discord.utils.get(guild.roles, name="Jailed")
        if not jail_role:
            jail_role = await guild.create_role(name="Jailed", color=discord.Color.dark_grey())
        
        mod_role = discord.utils.get(guild.roles, name="Jail Mod")
        if not mod_role:
            mod_role = await guild.create_role(name="Jail Mod", color=discord.Color.dark_blue())

        # 2. Create Channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            jail_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        channel = discord.utils.get(guild.text_channels, name="jail-cell")
        if not channel:
            channel = await guild.create_text_channel("jail-cell", overwrites=overwrites)
        else:
            await channel.edit(overwrites=overwrites)
            
        await interaction.followup.send(f"Setup Complete!\nRoles: {jail_role.mention}, {mod_role.mention}\nChannel: {channel.mention}")

    @app_commands.command(name="grant_jailmod", description="Grants the Jail Mod role to a user.")
    @app_commands.checks.has_permissions(administrator=True)
    async def grant_jailmod(self, interaction: discord.Interaction, member: discord.Member):
        _, mod_role = await self.get_jail_roles(interaction.guild)
        if not mod_role:
            return await interaction.response.send_message("Please run /setup_jail first.", ephemeral=True)
        
        await member.add_roles(mod_role)
        await interaction.response.send_message(f"Granted Jail Mod to {member.mention}.")

    @app_commands.command(name="jail", description="Jails a user.")
    @app_commands.describe(
        duration="Duration in minutes (e.g. 10). Leave 0 or empty for indefinite/password only.",
        password="4-letter password for release. Leave empty for time-only."
    )
    async def jail(self, interaction: discord.Interaction, member: discord.Member, duration: int = 0, password: str = None):
        # Check permission
        _, mod_role = await self.get_jail_roles(interaction.guild)
        if mod_role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("You need the 'Jail Mod' role to use this.", ephemeral=True)

        if password and (len(password) != 4 or not password.isalpha()):
            return await interaction.response.send_message("Password must be exactly 4 letters.", ephemeral=True)

        jail_role, _ = await self.get_jail_roles(interaction.guild)
        if not jail_role:
             return await interaction.response.send_message("Please run /setup_jail first.", ephemeral=True)

        # Save roles
        saved_roles = [r.id for r in member.roles if r.name != "@everyone" and r.name != "Jailed"]
        roles_json = json.dumps(saved_roles)
        
        # Strip roles and add Jail role
        try:
            await member.edit(roles=[jail_role])
        except discord.Forbidden:
             return await interaction.response.send_message("I don't have permission to change that user's roles.", ephemeral=True)

        # Calculate release time
        release_at = None
        if duration > 0:
            release_at = time.time() + (duration * 60)

        await add_active_jail(member.id, interaction.guild.id, release_at, password, roles_json)
        
        msg = f"{member.mention} has been JAILED!"
        if duration > 0:
            msg += f"\nTime: {duration} minutes."
        if password:
            msg += f"\nPassword Required: (Ask the Jail Mod)"
            
        await interaction.response.send_message(msg)

    async def unjail_user(self, member, guild, roles_data):
        jail_role = discord.utils.get(guild.roles, name="Jailed")
        if jail_role:
            await member.remove_roles(jail_role)
        
        # Restore roles
        role_ids = json.loads(roles_data)
        roles_to_add = []
        for r_id in role_ids:
            role = guild.get_role(r_id)
            if role:
                roles_to_add.append(role)
        
        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add)
            except:
                pass # Ignored failed role adds
                
        await remove_active_jail(member.id, guild.id)

    @app_commands.command(name="unjail", description="Manually releases a user.")
    async def unjail(self, interaction: discord.Interaction, member: discord.Member):
        _, mod_role = await self.get_jail_roles(interaction.guild)
        if mod_role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("You need the 'Jail Mod' role.", ephemeral=True)

        data = await get_active_jail(member.id, interaction.guild.id)
        if not data:
            return await interaction.response.send_message("That user is not in jail.", ephemeral=True)

        await self.unjail_user(member, interaction.guild, data[2]) # data[2] is roles_data
        await interaction.response.send_message(f"Released {member.mention}.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not isinstance(message.channel, discord.TextChannel):
            return

        if message.channel.name == "jail-cell":
            data = await get_active_jail(message.author.id, message.guild.id)
            if data:
                password = data[1] # data[1] is password
                if password and message.content.strip().lower() == password.lower():
                    await message.channel.send(f"Correct password! Releasing {message.author.mention}...")
                    await self.unjail_user(message.author, message.guild, data[2])

    @tasks.loop(minutes=1)
    async def jail_check_loop(self):
        # We need a way to check all guilds, but get_expired_jails returns user_id, guild_id.
        # We have to fetch the guild object from the bot.
        now = time.time()
        expired = await get_expired_jails(now)
        
        for user_id, guild_id, roles_data in expired:
            guild = self.bot.get_guild(guild_id)
            if guild:
                member = guild.get_member(user_id)
                if member:
                    await self.unjail_user(member, guild, roles_data)
                    # Notify in jail channel?? tough without channel ID active.
                    # Just unjail is fine.

    @jail_check_loop.before_loop
    async def before_jail_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Jail(bot))
