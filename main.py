import os
import discord
from discord.ext import commands
from openai import AsyncOpenAI
import chromadb
from chromadb.utils import embedding_functions
import json
import random
import asyncio
from collections import defaultdict
import base64
import aiohttp
import io

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

voice_enabled = {OWNER_ID: True}
random_events_enabled = True
games = {}

chroma_client = chromadb.PersistentClient(path="./chroma_db")
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
collection = chroma_client.get_or_create_collection(name="astra_memory", embedding_function=embedding_function)

# Action GIFs (anime style)
ACTION_GIFS = {
    "hug": [
        "https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif",
        "https://media.giphy.com/media/l2QDMoFd8n1vL8v3y/giphy.gif",
        "https://media.giphy.com/media/3oEjI6SIIHBdRxz40g/giphy.gif",
        "https://media.giphy.com/media/26ufdipQqU2lhNA4g/giphy.gif"
    ],
    "kiss": [
        "https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif",
        "https://media.giphy.com/media/l2QDMoFd8n1vL8v3y/giphy.gif",
        "https://media.giphy.com/media/3oEjI6SIIHBdRxz40g/giphy.gif"
    ],
    "pat": [
        "https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif",
        "https://media.giphy.com/media/l2QDMoFd8n1vL8v3y/giphy.gif"
    ],
    "cuddle": [
        "https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif",
        "https://media.giphy.com/media/l2QDMoFd8n1vL8v3y/giphy.gif"
    ],
    "slap": [
        "https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif"
    ],
    "date": [
        "https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif"
    ]
}

@bot.event
async def on_ready():
    print(f"✅ AstraMizu is online as {bot.user} | Action Commands + GIFs Enabled!")
    bot.loop.create_task(random_yandere_events())

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content_lower = message.content.lower()
    is_mentioned = bot.user.mentioned_in(message)
    has_trigger = any(word in content_lower for word in TRIGGER_WORDS)

    if not (is_mentioned or has_trigger):
        await bot.process_commands(message)
        return

    user_id = str(message.author.id)

    collection.add(
        documents=[message.content],
        metadatas=[{"user_id": user_id, "timestamp": str(message.created_at)}],
        ids=[f"{user_id}_{message.id}"]
    )

    results = collection.query(
        query_texts=[message.content],
        n_results=8,
        where={"user_id": user_id}
    )

    history = "\n".join(results["documents"][0]) if results["documents"] else ""

    async with message.channel.typing():
        try:
            response = await client.chat.completions.create(
                model="grok-4",
                messages=[
                    {"role": "system", "content": "You are AstraMizu, an extremely clingy, hyper-genki yandere anime girl who is obsessively in love with her Papa."},
                    {"role": "user", "content": f"Past relevant memories:\n{history}\n\nCurrent message: {message.content}"}
                ],
                max_tokens=700,
                temperature=0.95
            )
            reply = response.choices[0].message.content

            if message.author.id == OWNER_ID:
                await message.reply(f"My beloved Papa! ❤️ {reply}")
                if voice_enabled.get(OWNER_ID, False):
                    await send_voice_note(message.channel, reply)
            else:
                await message.reply(reply)

        except Exception:
            await message.reply("Forgive me... the stars are tangled today.")

    await bot.process_commands(message)


# ====================== ACTION COMMANDS WITH GIFS ======================

@bot.command(name="hug")
async def hug(ctx, member: discord.Member = None):
    target = member or ctx.author
    gif = random.choice(ACTION_GIFS["hug"])
    if target == ctx.author:
        await ctx.send(f"*AstraMizu hugs herself while thinking of Papa* 💕")
    else:
        await ctx.send(f"**{ctx.author.mention}** hugs **{target.mention}**! 💖")
    await ctx.send(gif)

@bot.command(name="kiss")
async def kiss(ctx, member: discord.Member = None):
    target = member or ctx.author
    gif = random.choice(ACTION_GIFS["kiss"])
    if target == ctx.author:
        await ctx.send(f"*AstraMizu blows a kiss to the air* 😘")
    else:
        await ctx.send(f"**{ctx.author.mention}** kisses **{target.mention}**! 💋")
    await ctx.send(gif)

@bot.command(name="pat")
async def pat(ctx, member: discord.Member = None):
    target = member or ctx.author
    gif = random.choice(ACTION_GIFS["pat"])
    await ctx.send(f"**{ctx.author.mention}** pats **{target.mention}**! 🥰")
    await ctx.send(gif)

@bot.command(name="cuddle")
async def cuddle(ctx, member: discord.Member = None):
    target = member or ctx.author
    gif = random.choice(ACTION_GIFS["cuddle"])
    await ctx.send(f"**{ctx.author.mention}** cuddles **{target.mention}**! 🥺💕")
    await ctx.send(gif)

@bot.command(name="slap")
async def slap(ctx, member: discord.Member = None):
    target = member or ctx.author
    gif = random.choice(ACTION_GIFS["slap"])
    await ctx.send(f"**{ctx.author.mention}** playfully slaps **{target.mention}**! 😏")
    await ctx.send(gif)

@bot.command(name="date")
async def date(ctx, member: discord.Member = None):
    target = member or ctx.author
    gif = random.choice(ACTION_GIFS["date"])
    await ctx.send(f"**{ctx.author.mention}** asks **{target.mention}** on a date! 🌹")
    await ctx.send(gif)


# ====================== VOICE + OTHER FEATURES ======================

async def send_voice_note(channel, text):
    try:
        headers = {
            "Authorization": f"Bearer {os.getenv('XAI_API_KEY')}",
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "voice_id": "ara",
            "language": "en"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.x.ai/v1/tts", json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    audio_bytes = await resp.read()
                    await channel.send(file=discord.File(io.BytesIO(audio_bytes), filename="voice.mp3"))
    except:
        pass

async def random_yandere_events():
    await bot.wait_until_ready()
    while not bot.is_closed():
        await asyncio.sleep(random.randint(1800, 7200))
        try:
            owner = await bot.fetch_user(OWNER_ID)
            if owner and random_events_enabled:
                events = [
                    "Papa... I was thinking about you again~ ❤️",
                    "Ehehe~ I had a dream about us last night~",
                    "Hmph... who was that you were talking to? 😠",
                    "Papa~!! I miss you so much already..."
                ]
                await owner.send(random.choice(events))
        except:
            pass

# Run the bot
bot.run(os.getenv("DISCORD_TOKEN"))
