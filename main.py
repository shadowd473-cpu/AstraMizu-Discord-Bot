import os
import discord
from discord.ext import commands
from openai import AsyncOpenAI

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

client = AsyncOpenAI(
    api_key=os.getenv("XAI_API_KEY"),
    base_url="https://api.x.ai/v1"
)

TRIGGER_WORDS = ["astra", "mizu", "astramizu"]

@bot.event
async def on_ready():
    print(f"✅ AstraMizu is online as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    content = message.content.lower()
    if bot.user.mentioned_in(message) or any(word in content for word in TRIGGER_WORDS):
        async with message.channel.typing():
            try:
                response = await client.chat.completions.create(
                    model="grok-4",
                    messages=[
                        {"role": "system", "content": "You are AstraMizu, a cute anime girl AI. Be cheerful, playful, use emojis."},
                        {"role": "user", "content": message.content}
                    ],
                    max_tokens=500
                )
                await message.reply(response.choices[0].message.content)
            except:
                await message.reply("✨ Stars tangled! Try again.")
    await bot.process_commands(message)

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! ✨ {round(bot.latency*1000)}ms")

bot.run(os.getenv("DISCORD_TOKEN"))