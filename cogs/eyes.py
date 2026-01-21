import discord
from discord import app_commands
from discord.ext import commands
from utils.database import get_eyes_index, update_eyes_index

COPYPASTA = [
    "Crazy?",
    "I was crazy once.",
    "They locked me in a room.",
    "A rubber room.",
    "A rubber room with rats.",
    "And rats make me crazy."
]

ZERO_WIDTH_SPACE = '\u200b' # 0
ZERO_WIDTH_NON_JOINER = '\u200c' # 1
# Separator to find start/end if needed, or just append to end.
# We will just append to end of message.

def encode_text(text):
    binary = ''.join(format(ord(c), '08b') for c in text)
    encoded = ''
    for bit in binary:
        if bit == '0':
            encoded += ZERO_WIDTH_SPACE
        else:
            encoded += ZERO_WIDTH_NON_JOINER
    return encoded

def decode_text(encoded_string):
    # Filter only our ZWSP chars
    bits = ''
    for char in encoded_string:
        if char == ZERO_WIDTH_SPACE:
            bits += '0'
        elif char == ZERO_WIDTH_NON_JOINER:
            bits += '1'
    
    if not bits:
        return None
        
    chars = []
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        if len(byte) == 8:
            chars.append(chr(int(byte, 2)))
    return ''.join(chars)

class Eyes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Context Menu
        self.ctx_menu = app_commands.ContextMenu(
            name="Decode Whisper",
            callback=self.decode_whisper,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def get_eyes_role(self, guild):
        return discord.utils.get(guild.roles, name="eyes")

    @app_commands.command(name="eyes_grant", description="Grants the 'eyes' role to see secret messages.")
    @app_commands.checks.has_permissions(administrator=True)
    async def eyes_grant(self, interaction: discord.Interaction, member: discord.Member):
        role = await self.get_eyes_role(interaction.guild)
        if not role:
            role = await interaction.guild.create_role(name="eyes", color=discord.Color.purple())
        
        await member.add_roles(role)
        await interaction.response.send_message(f"Granted **eyes** to {member.mention}.", ephemeral=True)

    @app_commands.command(name="whisper", description="Send a secret encoded message.")
    async def whisper(self, interaction: discord.Interaction, message: str):
        # Check Role
        role = await self.get_eyes_role(interaction.guild)
        if not role or role not in interaction.user.roles:
            return await interaction.response.send_message("You do not have the eyes to whisper.", ephemeral=True)

        # Get Copypasta Line
        index = await get_eyes_index(interaction.channel_id)
        line = COPYPASTA[index % len(COPYPASTA)]
        
        # Increment Index
        await update_eyes_index(interaction.channel_id, index + 1)
        
        # Encode
        encoded_hidden = encode_text(message)
        
        # Send
        # We send as the user? No, slash commands send as Bot via 'interaction.response.send_message'
        # But we want it to look like the bot sending it? 
        # The user request said "they are just doing the copy pasta", implies USER sends it.
        # Bots can't make users send messages. 
        # So the BOT will send the message "Crazy? <hidden>".
        # It's a "bot that counts/plays music/etc", so it makes sense the bot participates in the spam.
        
        final_content = f"{line}{encoded_hidden}"
        await interaction.response.send_message(final_content)

    async def decode_whisper(self, interaction: discord.Interaction, message: discord.Message):
        # Check Role
        role = await self.get_eyes_role(interaction.guild)
        if not role or role not in interaction.user.roles:
            return await interaction.response.send_message("You cannot see what is hidden.", ephemeral=True)

        decoded = decode_text(message.content)
        if decoded:
            await interaction.response.send_message(f"💀 **Secret**: {decoded}", ephemeral=True)
        else:
            await interaction.response.send_message("No secret found in this message.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Eyes(bot))
