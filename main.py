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
intents.reactions = True

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

# ====================== REACTION SYSTEM ======================
REACTION_RESPONSES = {
    "❤️": ["Aww~ Thank you Papa! My heart is melting! 💖", "Ehehe~ I love you too! ❤️"],
    "😘": ["*blushes hard* K-Kyaa~! You kissed me through the screen! 😳", "Mwah~ Right back at you! 💋"],
    "🔥": ["Oho~ Feeling spicy today, are we? 😏", "Papa is so hot when he's like this~ 🔥"],
    "😭": ["No no no! Don't cry! I'm here for you... *hugs tightly*", "Papa... tell me what's wrong. I'll make it better."],
    "😡": ["H-Hey! Why are you mad at me?! *pouts*", "If you're angry... is it because of someone else? 😠"],
    "😂": ["Ehehe~ Did I make you laugh? Mission accomplished! 😄", "Your laugh is my favorite sound~"],
    "👀": ["*notices you staring* W-What is it? Do I look cute? 👀", "Caught you looking~"]
}

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or reaction.message.author != bot.user:
        return

    emoji = str(reaction.emoji)
    if emoji in REACTION_RESPONSES:
        response = random.choice(REACTION_RESPONSES[emoji])
        await reaction.message.channel.send(f"{user.mention} {response}")

# ====================== NEW FEATURES (1-10) ======================

@bot.command(name="meme")
async def meme(ctx, *, text: str = None):
    if not text:
        text = "AstraMizu is too cute"
    await ctx.send(f"Here's your meme, Papa~ 😂\nhttps://api.memegen.link/images/drake/{text.replace(' ', '_')}/AstraMizu_is_cute.png")

@bot.command(name="roast")
async def roast(ctx, member: discord.Member = None):
    target = member or ctx.author
    roasts = [
        f"{target.mention} is so slow, even snails are faster.",
        f"{target.mention}'s personality is like plain rice — boring.",
        f"{target.mention} is the human version of a participation trophy.",
        f"{target.mention} has the charisma of a wet sock."
    ]
    await ctx.send(random.choice(roasts))

@bot.command(name="quiz")
async def quiz(ctx):
    questions = [
        ("What is AstraMizu's favorite word?", "Papa"),
        ("What color is AstraMizu's hair?", "Pink"),
        ("What does AstraMizu love most?", "Her Papa")
    ]
    q, a = random.choice(questions)
    await ctx.send(f"**Quiz Time!** {q}")
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    try:
        msg = await bot.wait_for('message', check=check, timeout=15.0)
        if msg.content.lower() == a.lower():
            await ctx.send("Correct! You're so smart~ ✨")
        else:
            await ctx.send(f"Wrong~ The answer was **{a}**!")
    except:
        await ctx.send("Time's up! The answer was **{a}**.")

@bot.command(name="confess")
async def confess(ctx, *, confession: str = None):
    if not confession:
        await ctx.send("Write your confession after the command!")
        return
    channel = discord.utils.get(ctx.guild.text_channels, name="confessions")
    if channel:
        await channel.send(f"📝 **Anonymous Confession:** {confession}")
        await ctx.send("Your confession has been sent anonymously~")
    else:
        await ctx.send("There's no #confessions channel yet!")

@bot.command(name="poll")
async def poll(ctx, question: str, *options):
    if len(options) < 2:
        await ctx.send("You need at least 2 options!")
        return
    poll_text = f"**{question}**\n"
    for i, opt in enumerate(options, 1):
        poll_text += f"{i}. {opt}\n"
    msg = await ctx.send(poll_text)
    for i in range(len(options)):
        await msg.add_reaction(chr(0x1f1e6 + i))

@bot.command(name="translate")
async def translate(ctx, lang: str, *, text: str):
    await ctx.send(f"**Translated to {lang}:**\n(Feature coming soon - for now here's the original)\n{text}")

@bot.command(name="chaos")
async def chaos(ctx):
    responses = [
        "*explodes into sparkles* ✨💥",
        "I just turned into a cat. Meow~ 🐱",
        "The stars told me to say: 'Pineapple belongs on pizza' 🍍🍕",
        "*starts breakdancing* 🕺"
    ]
    await ctx.send(random.choice(responses))

# Run the bot
bot.run(os.getenv("DISCORD_TOKEN"))
