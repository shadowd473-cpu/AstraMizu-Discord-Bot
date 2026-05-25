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

# ====================== !LIST COMMAND ======================

@bot.command(name="list")
async def list_features(ctx):
    embed = discord.Embed(
        title="🌸 AstraMizu Feature List",
        description="Everything I can do for you, Papa~ ❤️",
        color=discord.Color.pink()
    )

    embed.add_field(
        name="💖 Action Commands",
        value="`!hug` `!kiss` `!pat` `!cuddle` `!slap` `!date` `!bite` `!lick` `!marry` `!tackle` `!poke` `!blush`",
        inline=False
    )

    embed.add_field(
        name="🖼️ Image & Video",
        value="`!imagine <prompt>` • `!edit <prompt>` (with image) • `!video <prompt>` • `!animate` (image-to-video coming soon)",
        inline=False
    )

    embed.add_field(
        name="🎙️ Voice Features",
        value="`!speak <text>` • Voice notes (auto for Papa) • Speech-to-Text (send voice messages)",
        inline=False
    )

    embed.add_field(
        name="🎮 Games",
        value="`!rps` `!guess` `!ttt` `!8ball` `!lovemeter` `!quiz`",
        inline=False
    )

    embed.add_field(
        name="✨ Fun & Utility",
        value="`!meme` `!roast @user` `!poll` `!confess` `!chaos` `!translate`",
        inline=False
    )

    embed.add_field(
        name="💕 Personality & Events",
        value="Random yandere messages • Reaction system (❤️ 😘 🔥 etc.) • Clingy yandere genki hyper mode",
        inline=False
    )

    embed.add_field(
        name="📜 Other",
        value="`!memory` (coming soon) • `!list` • `!voice` `!toggle events`",
        inline=False
    )

    embed.set_footer(text="Made with love for Papa ❤️ | Type !help for more info")
    await ctx.send(embed=embed)

# Run the bot
bot.run(os.getenv("DISCORD_TOKEN"))
