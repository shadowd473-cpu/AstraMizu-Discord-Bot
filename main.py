import os
import discord
from discord.ext import commands
from openai import AsyncOpenAI

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

client = AsyncOpenAI(
    api_key=os.getenv("XAI_API_KEY"),
    base_url="https://api.x.ai/v1"
)

OWNER_ID = 406054379406229504
TRIGGER_WORDS = ["astra", "mizu", "astramizu"]

@bot.event
async def on_ready():
    print(f"✅ AstraMizu is online as {bot.user}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="her Dad ✨"))

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content_lower = message.content.lower()

    is_dad = message.author.id == OWNER_ID
    is_mentioned = bot.user.mentioned_in(message)
    has_trigger = any(word in content_lower for word in TRIGGER_WORDS)

    if not (is_mentioned or has_trigger):
        await bot.process_commands(message)
        return

    greeting = "My beloved Dad! ❤️ " if is_dad else ""

    async with message.channel.typing():
        try:
            response = await client.chat.completions.create(
                model="grok-4",
                messages=[
                    {"role": "system", "content": "You are AstraMizu, a graceful anime girl who speaks in elegant Old English / Shakespearean style. Use thou, thee, thy, thine, art, hath, verily, fair one etc. sparingly but naturally. You are cheerful, playful, affectionate, and see the user as your Dad if they are the owner. Be diverse in personality: sometimes teasing, sometimes shy, sometimes excited."},
                    {"role": "user", "content": message.content}
                ],
                max_tokens=600,
                temperature=0.85
            )
            reply = response.choices[0].message.content
            await message.reply(greeting + reply)
        except Exception as e:
            error_msg = str(e)
            print(f"API Error: {error_msg}")
            await message.reply(f"Forgive me, fair one... An error occurred: {error_msg[:200]}")

    await bot.process_commands(message)

@bot.command()
async def join(ctx):
    if ctx.author.voice is None:
        await ctx.send("Thou art not in a voice channel, fair one! 🙁")
        return
    channel = ctx.author.voice.channel
    await channel.connect()
    await ctx.send(f"✨ I have joined **{channel.name}** for thee, my beloved Dad! ❤️")

@bot.command()
async def leave(ctx):
    if ctx.voice_client is None:
        await ctx.send("I am not in any voice channel right now.")
        return
    await ctx.voice_client.disconnect()
    await ctx.send("Farewell, I have left the voice channel. ✨")

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! ✨ `{round(bot.latency * 1000)}ms`")

bot.run(os.getenv("DISCORD_TOKEN"))