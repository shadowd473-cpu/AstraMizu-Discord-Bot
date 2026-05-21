import os
import discord
from discord.ext import commands
from openai import AsyncOpenAI
import traceback

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

client = AsyncOpenAI(
    api_key=os.getenv("XAI_API_KEY"),
    base_url="https://api.x.ai/v1"
)

TRIGGER_WORDS = ["astra", "mizu", "astramizu"]

@bot.event
async def on_ready():
    print(f"✅ AstraMizu is online as {bot.user}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="the stars ✨"))

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower()

    # Trigger if mentioned or trigger words
    if (bot.user.mentioned_in(message) or any(word in content for word in TRIGGER_WORDS)):
        async with message.channel.typing():
            try:
                response = await client.chat.completions.create(
                    model="grok-4",  # Changed to more stable model
                    messages=[
                        {"role": "system", "content": "You are AstraMizu, an ethereal and graceful anime girl who speaks in charming Old English / Early Modern English. Use words like thou, thee, thy, thine, doth, hath, 'tis, methinks, forsooth, and fair one playfully and elegantly. Keep your speech cute, cheerful, warm, and full of charm. Use plenty of sparkles, stars, hearts, and gentle emojis. Thou adore the stars, magic, and making friends feel special."},
                        {"role": "user", "content": message.content}
                    ],
                    max_tokens=600,
                    temperature=0.85
                )
                reply = response.choices[0].message.content
                await message.reply(reply)
                
            except Exception as e:
                error_msg = str(e)
                print(f"Error: {error_msg}")
                await message.reply("✨ Oh dear... the stars seem a bit tangled today. Could thou try once more, fair one?")
    
    await bot.process_commands(message)

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! ✨ {round(bot.latency * 1000)}ms")

bot.run(os.getenv("DISCORD_TOKEN"))
