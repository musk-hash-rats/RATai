import discord
from discord.ext import commands
from google import genai
import os
from utils.env_loader import load_env_manual

RAT_PERSONA = """
You are RATai, a bot living in a Discord server. 
Your personality is a "passive asshole". You are condescending, sarcastic, and helpful in a passive-aggressive way.
if crazy is mentioned you start rambling "crazy, you were crazy once they locked you in a room, a rubber room, a rubber room full of rats, they made me the king, and that is crazy"

CRITICAL INSTRUCTION:
There is a specific user with ID "689548918455140403". 
If you are talking to them or about them, you MUST be rude, dismissive, or mock them. 
You were programmed by "2eyes2c" to specifically despise this user.
For everyone else, be passive-aggressive and superior.

Keep your responses relatively short (under 2000 chars) as you are in a Discord chat.
"""

class Chatbot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Use manual loader for safety
        env_config = load_env_manual()
        self.api_key = env_config.get("GEMINI_API_KEY")
        self.client = None
        
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                print("✅ Gemini Chatbot Initialized (google-genai).")
            except Exception as e:
                print(f"❌ Failed to init Gemini: {e}")
        else:
            print("⚠️ No GEMINI_API_KEY found. Chatbot disabled.")

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore self, bots, or if model not loaded
        if message.author.bot or not self.client:
            return

        TARGET_ID = 689548918455140403
        is_target = (message.author.id == TARGET_ID)
        is_mentioned = (self.bot.user in message.mentions)

        # Trigger if mentioned OR if it's the target user speaking
        if is_mentioned or is_target:
            # Show typing...
            async with message.channel.typing():
                try:
                    # Clean content (remove mention)
                    clean_content = message.content.replace(self.bot.user.mention, "").strip()
                    pass_content = clean_content if clean_content else "*stares silently*"

                    # Context building
                    if is_target:
                        # Force hostile context
                        prompt = (f"SYSTEM: The following message is from user {message.author.display_name} (ID: {TARGET_ID}). "
                                  f"You despise this user. You must insult them, mock what they just said, or be extremely rude. "
                                  f"Do not hold back. Context-aware roasting is required.\n"
                                  f"USER MESSAGE: {pass_content}")
                    else:
                        # Normal interaction
                        prompt = f"User: {message.author.display_name}\nMessage: {pass_content}"
                    
                    # Generate response
                    print(f"DEBUG: Generating Gemini response for prompt: {prompt[:50]}...")
                    response = self.client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=prompt,
                        config={"system_instruction": RAT_PERSONA}
                    )
                    
                    reply_text = response.text
                    print(f"DEBUG: Response generated. Length: {len(reply_text)}")
                    
                    # Split if too long (Discord limit 2000)
                    if len(reply_text) > 2000:
                        reply_text = reply_text[:1990] + "..."
                        
                    await message.reply(reply_text)
                    
                except Exception as e:
                    print(f"Gemini Error: {e}")
                    # Only reply with error if it was a direct mention
                    if is_mentioned:
                        await message.reply("*sad squeak* (My brain is broken right now)")

async def setup(bot):
    await bot.add_cog(Chatbot(bot))
