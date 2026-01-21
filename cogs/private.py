import discord
from discord import app_commands
from discord.ext import commands
from utils.database import add_private_channel, get_private_channel_owner, remove_private_channel

class PrivateChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="private_create", description="[Boosters] Create your own private channel.")
    async def private_create(self, interaction: discord.Interaction, name: str):
        # Check Booster Status
        if not interaction.user.premium_since and not interaction.user.guild_permissions.administrator:
             return await interaction.response.send_message("You must be a Server Booster to create a private channel!", ephemeral=True)

        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="Private Channels")
        if not category:
            category = await guild.create_category("Private Channels")

        # Create Channel with Overwrites
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        
        channel = await guild.create_text_channel(name, category=category, overwrites=overwrites)
        
        await add_private_channel(channel.id, interaction.user.id)
        await interaction.response.send_message(f"Created {channel.mention}! You are the owner.", ephemeral=True)

    @app_commands.command(name="private_add", description="Add a friend to your private channel.")
    async def private_add(self, interaction: discord.Interaction, member: discord.Member):
        owner_id = await get_private_channel_owner(interaction.channel_id)
        
        if not owner_id:
             return await interaction.response.send_message("This is not a registered private channel.", ephemeral=True)
        
        if owner_id != interaction.user.id and not interaction.user.guild_permissions.administrator:
             return await interaction.response.send_message("You do not own this channel.", ephemeral=True)

        await interaction.channel.set_permissions(member, read_messages=True, send_messages=True)
        await interaction.response.send_message(f"Added {member.mention} to the channel.")

    @app_commands.command(name="private_remove", description="Remove a user from your private channel.")
    async def private_remove(self, interaction: discord.Interaction, member: discord.Member):
        owner_id = await get_private_channel_owner(interaction.channel_id)
        
        if not owner_id:
             return await interaction.response.send_message("This is not a registered private channel.", ephemeral=True)
             
        if owner_id != interaction.user.id and not interaction.user.guild_permissions.administrator:
             return await interaction.response.send_message("You do not own this channel.", ephemeral=True)

        await interaction.channel.set_permissions(member, overwrite=None)
        await interaction.response.send_message(f"Removed {member.mention} from the channel.")

    @app_commands.command(name="private_delete", description="Delete your private channel.")
    async def private_delete(self, interaction: discord.Interaction):
        owner_id = await get_private_channel_owner(interaction.channel_id)
        
        if not owner_id:
             return await interaction.response.send_message("This is not a registered private channel.", ephemeral=True)
             
        if owner_id != interaction.user.id and not interaction.user.guild_permissions.administrator:
             return await interaction.response.send_message("You do not own this channel.", ephemeral=True)
             
        await interaction.response.send_message("Deleting channel in 5 seconds...")
        await remove_private_channel(interaction.channel_id)
        await interaction.channel.delete()

async def setup(bot):
    await bot.add_cog(PrivateChannels(bot))
