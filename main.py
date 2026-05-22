import os
import discord
from discord.ext import commands
from openai import AsyncOpenAI
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

MEMORY_FILE = "memory.json"

def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            return defaultdict(list, json.load(f))
    except:
        return defaultdict(list)

def save_memory():
    with open(MEMORY_FILE, "w") as f:
        json.dump(dict(conversation_memory), f)

conversation_memory = load_memory()

@bot.event
async def on_ready():
    print(f"✅ AstraMizu is online as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content_lower = message.content.lower()

    # === SUPER STRICT TRIGGER ===
    is_mentioned = bot.user.mentioned_in(message)
    has_trigger = any(word in content_lower for word in TRIGGER_WORDS)

    if not (is_mentioned or has_trigger):
        return  # ←←← NO REPLY AT ALL

    # Add to memory
    conversation_memory[message.channel.id].append(f"User: {message.content}")
    if len(conversation_memory[message.channel.id]) > 15:
        conversation_memory[message.channel.id].pop(0)
    save_memory()

    history = "\n".join(conversation_memory[message.channel.id])

    async with message.channel.typing():
        try:
            response = await client.chat.completions.create(
                model="grok-4",
                messages=[
                    {"role": "system", "content": "You are AstraMizu, a graceful anime girl who speaks in elegant Old English style. Use thou, thee, thy, verily, fair one etc. naturally but sparingly. You are cheerful, playful, and affectionate. The user is your beloved Papa/Dad."},
                    {"role": "user", "content": f"Conversation history:\n{history}\n\nCurrent message: {message.content}"}
                ],
                max_tokens=700,
                temperature=0.85
            )
            reply = response.choices[0].message.content

            if message.author.id == OWNER_ID:
                await message.reply(f"My beloved Papa! ❤️ {reply}")
            else:
                await message.reply(reply)

            # Save bot reply to memory
            conversation_memory[message.channel.id].append(f"AstraMizu: {reply}")
            save_memory()

        except Exception:
            await message.reply("Forgive me... the stars are tangled today.")

bot.run(os.getenv("DISCORD_TOKEN"))
