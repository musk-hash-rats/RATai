import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio

# Suppress noise about console usage from errors
# Suppress noise about console usage from errors
yt_dlp.utils.bug_reports_message = lambda *args, **kwargs: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5' # Critical for stable streaming
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

    @classmethod
    async def regather_stream(cls, data, *, loop=None):
        """Used for gathering stream from existing data (e.g. playlist entry)"""
        loop = loop or asyncio.get_event_loop()
        # If the URL is expired (long queue), we might need to re-extract (advanced), 
        # but for now we assume direct URL or re-extraction from web_url if needed.
        # Simple version: just return the class with current data. 
        # Ideally, we should re-extract if it's been a long time.
        
        filename = data['url']
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {} # {guild_id: [data_dict, ...]}
        self.voice_clients = {}

    def get_queue(self, guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]

    async def play_next(self, interaction):
        if interaction.guild.id in self.queues and self.queues[interaction.guild.id]:
            # Pop next song
            data = self.queues[interaction.guild.id].pop(0)
            
            # Source creation
            # Note: Streaming URLs expire. Use web_url to re-extract if needed?
            # For simplicity, we re-extract to be safe, or used cached if fresh.
            try:
                # We need to re-extract to get a fresh stream URL usually
                loop = self.bot.loop or asyncio.get_event_loop()
                new_data = await loop.run_in_executor(None, lambda: ytdl.extract_info(data['webpage_url'], download=False))
                if 'entries' in new_data: new_data = new_data['entries'][0]
                
                filename = new_data['url']
                source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(filename, **ffmpeg_options))
                
                vc = interaction.guild.voice_client
                if vc:
                    vc.play(
                        source, 
                        after=lambda e: self.bot.loop.create_task(self.play_next_callback(interaction, e))
                    )
                    await interaction.channel.send(f"Now playing: **{new_data['title']}**")
            except Exception as e:
                print(f"Error playing next: {e}")
                import traceback
                traceback.print_exc()
                await self.play_next(interaction) # Try next one
        else:
             # Queue empty
             pass

    async def play_next_callback(self, interaction, error):
        if error:
            print(f"Player error: {error}")
        await self.play_next(interaction)

    @app_commands.command(name="play", description="Plays a song or playlist from YouTube.")
    async def play(self, interaction: discord.Interaction, search: str):
        await interaction.response.send_message("🎵 **Music Module Coming Soon!** 🎵\nThis feature is currently under construction. Stay tuned for updates!", ephemeral=True)

    @app_commands.command(name="skip", description="Skips the current song.")
    async def skip(self, interaction: discord.Interaction):
        await interaction.response.send_message("🎵 **Music Module Coming Soon!** 🎵", ephemeral=True)

    @app_commands.command(name="stop", description="Stops music and clears queue.")
    async def stop(self, interaction: discord.Interaction):
        await interaction.response.send_message("🎵 **Music Module Coming Soon!** 🎵", ephemeral=True)

    @app_commands.command(name="queue", description="Shows the next 10 songs.")
    async def queue_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_message("🎵 **Music Module Coming Soon!** 🎵", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Music(bot))
