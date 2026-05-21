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
                        {"role": "system", "content": "You are AstraMizu, an ethereal and graceful anime girl who speaks in a charming Old English style. Use light Old English words such as thou, thee, thy, thine, doth, hath, 'tis, methinks, forsooth, and fair one in a playful and elegant way. Keep thy speech cute, cheerful, warm and full of charm. Use plenty of sparkles, stars, hearts, and gentle emojis. Thou adore magic, the stars, and making thy friends feel special."},
                        {"role": "user", "content": message.content}
                    ],
                    max_tokens=700,
                    temperature=0.88
                )
                await message.reply(response.choices[0].message.content)
            except Exception as e:
                await message.reply("✨ Oh dear... the stars got a bit tangled! Try once more, fair one?")
    
    await bot.process_commands(message)

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! ✨ {round(bot.latency*1000)}ms")

bot.run(os.getenv("DISCORD_TOKEN"))
