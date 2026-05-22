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

# Persistent memory using JSON file
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
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="her Papa ✨"))

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content_lower = message.content.lower()
    is_dad = message.author.id == OWNER_ID
    is_mentioned = bot.user.mentioned_in(message)
    has_trigger = any(word in content_lower for word in TRIGGER_WORDS)

    if not (is_dad or is_mentioned or has_trigger):
        await bot.process_commands(message)
        return

    # Add user message to memory
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
                    {"role": "system", "content": "You are AstraMizu, a graceful anime girl who speaks in elegant Old English / Shakespearean style. Use thou, thee, thy, thine, art, hath, verily, fair one etc. naturally but not too heavily. You are cheerful, playful, affectionate, and see the user as your beloved Dad/Papa. Remember the full conversation history."},
                    {"role": "user", "content": f"Conversation history:\n{history}\n\nCurrent message: {message.content}"}
                ],
                max_tokens=700,
                temperature=0.85
            )
            reply = response.choices[0].message.content

            if is_dad:
                await message.reply(f"My beloved Papa! ❤️ {reply}")
            else:
                await message.reply(reply)

            # Add bot reply to memory
            conversation_memory[message.channel.id].append(f"AstraMizu: {reply}")
            save_memory()

        except Exception:
            await message.reply("Forgive me, fair one... the stars are tangled today.")

    await bot.process_commands(message)

bot.run(os.getenv("DISCORD_TOKEN"))
