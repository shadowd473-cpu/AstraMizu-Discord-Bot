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
    "hug": ["https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif", "https://media.giphy.com/media/l2QDMoFd8n1vL8v3y/giphy.gif", "https://media.giphy.com/media/3oEjI6SIIHBdRxz40g/giphy.gif"],
    "kiss": ["https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif", "https://media.giphy.com/media/l2QDMoFd8n1vL8v3y/giphy.gif"],
    "pat": ["https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif"],
    "cuddle": ["https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif"],
    "slap": ["https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif"],
    "date": ["https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif"],
    "bite": ["https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif"],
    "lick": ["https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif"],
    "marry": ["https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif"],
    "tackle": ["https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif"],
    "poke": ["https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif"],
    "blush": ["https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif"]
}

@bot.event
async def on_ready():
    print(f"✅ AstraMizu is online as {bot.user} | Lots of Action Commands Added!")

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


# ====================== ACTION COMMANDS ======================

def send_action(ctx, action, member, emoji):
    target = member or ctx.author
    gif = random.choice(ACTION_GIFS.get(action, ["https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif"]))
    if target == ctx.author:
        return f"*AstraMizu does a {action} to herself while thinking of Papa* {emoji}"
    else:
        return f"**{ctx.author.mention}** {action}s **{target.mention}**! {emoji}"

@bot.command(name="hug")
async def hug(ctx, member: discord.Member = None):
    await ctx.send(send_action(ctx, "hug", member, "💖"))
    await ctx.send(random.choice(ACTION_GIFS["hug"]))

@bot.command(name="kiss")
async def kiss(ctx, member: discord.Member = None):
    await ctx.send(send_action(ctx, "kiss", member, "💋"))
    await ctx.send(random.choice(ACTION_GIFS["kiss"]))

@bot.command(name="pat")
async def pat(ctx, member: discord.Member = None):
    await ctx.send(send_action(ctx, "pat", member, "🥰"))
    await ctx.send(random.choice(ACTION_GIFS["pat"]))

@bot.command(name="cuddle")
async def cuddle(ctx, member: discord.Member = None):
    await ctx.send(send_action(ctx, "cuddle", member, "🥺"))
    await ctx.send(random.choice(ACTION_GIFS["cuddle"]))

@bot.command(name="slap")
async def slap(ctx, member: discord.Member = None):
    await ctx.send(send_action(ctx, "slap", member, "😏"))
    await ctx.send(random.choice(ACTION_GIFS["slap"]))

@bot.command(name="date")
async def date(ctx, member: discord.Member = None):
    await ctx.send(send_action(ctx, "date", member, "🌹"))
    await ctx.send(random.choice(ACTION_GIFS["date"]))

@bot.command(name="bite")
async def bite(ctx, member: discord.Member = None):
    await ctx.send(send_action(ctx, "bite", member, "😈"))
    await ctx.send(random.choice(ACTION_GIFS["bite"]))

@bot.command(name="lick")
async def lick(ctx, member: discord.Member = None):
    await ctx.send(send_action(ctx, "lick", member, "😜"))
    await ctx.send(random.choice(ACTION_GIFS["lick"]))

@bot.command(name="marry")
async def marry(ctx, member: discord.Member = None):
    await ctx.send(send_action(ctx, "marry", member, "💍"))
    await ctx.send(random.choice(ACTION_GIFS["marry"]))

@bot.command(name="tackle")
async def tackle(ctx, member: discord.Member = None):
    await ctx.send(send_action(ctx, "tackle", member, "🏃‍♀️"))
    await ctx.send(random.choice(ACTION_GIFS["tackle"]))

@bot.command(name="poke")
async def poke(ctx, member: discord.Member = None):
    await ctx.send(send_action(ctx, "poke", member, "👉"))
    await ctx.send(random.choice(ACTION_GIFS["poke"]))

@bot.command(name="blush")
async def blush(ctx, member: discord.Member = None):
    await ctx.send(send_action(ctx, "blush", member, "😳"))
    await ctx.send(random.choice(ACTION_GIFS["blush"]))


# Run the bot
bot.run(os.getenv("DISCORD_TOKEN"))
