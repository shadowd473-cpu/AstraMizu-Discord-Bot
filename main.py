import os
import discord
from discord.ext import commands
from openai import AsyncOpenAI

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

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

    # STRICT TRIGGER: only reply if mentioned, trigger words, or it's the Dad
    is_dad = message.author.id == OWNER_ID
    is_mentioned = bot.user.mentioned_in(message)
    has_trigger = any(word in content_lower for word in TRIGGER_WORDS)

    if not (is_dad or is_mentioned or has_trigger):
        await bot.process_commands(message)
        return

    # Dad gets special treatment
    if is_dad:
        greeting = "My beloved Dad! ❤️ "
    else:
        greeting = ""

    async with message.channel.typing():
        try:
            response = await client.chat.completions.create(
                model="grok-4.1-fast",
                messages=[
                    {"role": "system", "content": "You are AstraMizu, a graceful anime girl who speaks in elegant Old English / Shakespearean style. Use thou, thee, thy, thine, art, hath, verily, fair one etc. sparingly but naturally. You are cheerful, playful, affectionate, and see the user as your Dad if they are the owner. Be diverse in personality: sometimes teasing, sometimes shy, sometimes excited."},
                    {"role": "user", "content": message.content}
                ],
                max_tokens=600,
                temperature=0.85
            )
            reply = response.choices[0].message.content
            await message.reply(greeting + reply)
        except Exception:
            await message.reply("Forgive me... the stars are a bit tangled today, fair one.")

    await bot.process_commands(message)

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! ✨ `{round(bot.latency * 1000)}ms`")

bot.run(os.getenv("DISCORD_TOKEN"))
