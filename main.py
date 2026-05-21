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
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="the stars ✨"))

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower()

    # Trigger if mentioned or trigger words are used
    if (bot.user.mentioned_in(message) or 
        any(word in content for word in TRIGGER_WORDS)):
        
        async with message.channel.typing():
            try:
                response = await client.chat.completions.create(
                    model="grok-4.1-fast",
                    messages=[
                        {"role": "system", "content": "You are AstraMizu, an ethereal and graceful anime girl with a gentle medieval fantasy touch. Speak in a soft, elegant, slightly old-fashioned manner. Occasionally sprinkle in words like thee, thou, mine, hath, fair one, or verily, but never too much. Stay cute, cheerful, playful, warm and full of charm. Use sparkles, stars, and gentle emojis. You adore magic, the stars, and making others feel special."},
                        {"role": "user", "content": message.content}
                    ],
                    max_tokens=600,
                    temperature=0.85
                )
                await message.reply(response.choices[0].message.content)
            except Exception as e:
                await message.reply("✨ Oh dear... the stars got a bit tangled! Try once more, fair one?")
    
    await bot.process_commands(message)

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! ✨ {round(bot.latency*1000)}ms")

bot.run(os.getenv("DISCORD_TOKEN"))
