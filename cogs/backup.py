import discord
from discord import app_commands
from discord.ext import commands
import json
import io
import aiohttp
from utils.database import export_data, import_data

class Backup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="backup_save", description="[Admin] Exports the database state to a JSON file.")
    @app_commands.checks.has_permissions(administrator=True)
    async def backup_save(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        data = await export_data()
        json_str = json.dumps(data, indent=2)
        
        file = discord.File(io.StringIO(json_str), filename="ratai_backup.json")
        await interaction.followup.send("📦 **Database Backup**\nSave this file! Run `/backup_load` with the file link to restore.", file=file)

    @app_commands.command(name="backup_load", description="[Admin] Restores the database from a JSON file url.")
    @app_commands.describe(file_url="Direct link to the .json backup file (Right click -> Copy Link)")
    @app_commands.checks.has_permissions(administrator=True)
    async def backup_load(self, interaction: discord.Interaction, file_url: str):
        await interaction.response.defer(ephemeral=True)
        
        # Handle Discord Message Links (e.g. https://discord.com/channels/...)
        # This fixes the "0auth" or invalid link issue users face when copying the wrong link
        if "discord.com/channels/" in file_url:
            try:
                # Extract IDs from url: .../channels/guild_id/channel_id/message_id
                parts = file_url.split('/')
                channel_id = int(parts[-2])
                message_id = int(parts[-1])
                
                channel = self.bot.get_channel(channel_id)
                if not channel:
                     # Try fetching if not in cache (rare for recent, but possible)
                     try:
                        channel = await self.bot.fetch_channel(channel_id)
                     except:
                        return await interaction.followup.send("❌ Could not find that channel. Ensure the bot has access.")

                message = await channel.fetch_message(message_id)
                if not message.attachments:
                    return await interaction.followup.send("❌ That message has no files attached!")
                
                # Update URL to the actual file URL
                file_url = message.attachments[0].url
                
            except Exception as e:
                return await interaction.followup.send(f"❌ Failed to read message link: {e}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as resp:
                    if resp.status != 200:
                        return await interaction.followup.send("❌ Failed to download file. Check the URL (403/404).")
                    
                    content = await resp.text()
                    data = json.loads(content)
            
            await import_data(data)
            await interaction.followup.send("✅ **Database Restored!**\nAll user levels, stats, and settings have been recovered.")
            
        except json.JSONDecodeError:
             await interaction.followup.send("❌ Invalid JSON file.")
        except Exception as e:
             await interaction.followup.send(f"❌ Error restoring backup: {str(e)}")

async def setup(bot):
    await bot.add_cog(Backup(bot))
