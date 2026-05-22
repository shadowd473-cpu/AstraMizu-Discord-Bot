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

    # STRICT TRIGGER: ONLY reply if name is said or @mentioned
    is_mentioned = bot.user.mentioned_in(message)
    has_trigger = any(word in content_lower for word in TRIGGER_WORDS)

    if not (is_mentioned or has_trigger):
        await bot.process_commands(message)
        return

    async with message.channel.typing():
        try:
            response = await client.chat.completions.create(
                model="grok-4.1-fast",
                messages=[
                    {"role": "system", "content": "You are AstraMizu, a graceful anime girl who speaks in elegant Old English / Shakespearean style. Use thou, thee, thy, thine, art, hath, verily, fair one etc. sparingly but naturally. You are cheerful, playful, affectionate, and see the user as your Dad. Be diverse in personality: sometimes teasing, sometimes shy, sometimes excited."},
                    {"role": "user", "content": message.content}
                ],
                max_tokens=600,
                temperature=0.85
            )
            reply = response.choices[0].message.content
            await message.reply(reply)
        except Exception:
            await message.reply("Forgive me... the stars are a bit tangled today, fair one.")

    await bot.process_commands(message)

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! ✨ `{round(bot.latency * 1000)}ms`")

bot.run(os.getenv("DISCORD_TOKEN"))
