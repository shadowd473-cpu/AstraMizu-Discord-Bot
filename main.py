import os
import discord
from discord.ext import commands
from openai import AsyncOpenAI
import chromadb
from chromadb.utils import embedding_functions
import json
from collections import defaultdict

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

# Vector Database Setup
chroma_client = chromadb.PersistentClient(path="./chroma_db")
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
collection = chroma_client.get_or_create_collection(name="astra_memory", embedding_function=embedding_function)

@bot.event
async def on_ready():
    print(f"✅ AstraMizu is online as {bot.user} | Vector DB Ready")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content_lower = message.content.lower()
    is_mentioned = bot.user.mentioned_in(message)
    has_trigger = any(word in content_lower for word in TRIGGER_WORDS)

    if not (is_mentioned or has_trigger):
        return

    user_id = str(message.author.id)

    # Store message in vector DB
    collection.add(
        documents=[message.content],
        metadatas=[{"user_id": user_id, "timestamp": str(message.created_at)}],
        ids=[f"{user_id}_{message.id}"]
    )

    # Retrieve relevant past memories
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
                    {"role": "system", "content": "You are AstraMizu, a graceful anime girl who speaks in elegant Old English style. Use thou, thee, thy, verily, fair one etc. naturally but sparingly. You are cheerful, playful, and very affectionate. The user is your beloved Papa/Dad."},
                    {"role": "user", "content": f"Past relevant memories:\n{history}\n\nCurrent message: {message.content}"}
                ],
                max_tokens=700,
                temperature=0.85
            )
            reply = response.choices[0].message.content

            if message.author.id == OWNER_ID:
                await message.reply(f"My beloved Papa! ❤️ {reply}")
            else:
                await message.reply(reply)

        except Exception:
            await message.reply("Forgive me... the stars are tangled today.")

bot.run(os.getenv("DISCORD_TOKEN"))
