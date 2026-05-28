import os
import discord
from discord.ext import commands
from openai import AsyncOpenAI, OpenAI
import json
from collections import deque

import random
import asyncio
import aiohttp
import io
import yt_dlp
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True
intents.reactions = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

client = AsyncOpenAI(
    api_key=os.getenv("XAI_API_KEY"),
    base_url="https://api.x.ai/v1"
)

deepgram = DeepgramClient(api_key=os.getenv("DEEPGRAM_API_KEY"))

OWNER_ID = 406054379406229504
TRIGGER_WORDS = ["astra", "mizu", "astramizu"]

# === FULL CONVERSATION MEMORY (remembers everything) ===
MEMORY_FILE = "conversation_memory.json"
MAX_HISTORY_TURNS = 25

def load_memory(user_id):
    try:
        if not os.path.exists(MEMORY_FILE):
            return []
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)
        return data.get(str(user_id), [])
    except:
        return []

def save_memory(user_id, history):
    try:
        try:
            with open(MEMORY_FILE, "r") as f:
                data = json.load(f)
        except:
            data = {}
        data[str(user_id)] = history[-MAX_HISTORY_TURNS*2:]
        with open(MEMORY_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Memory save error: {e}")

# Create memory file on startup if it doesn't exist
if not os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "w") as f:
        json.dump({}, f)

voice_enabled = {OWNER_ID: True}
random_events_enabled = True
games = {}

# Voice state
voice_clients = {}
music_queues = {}  # guild_id -> list of (url, title)

# Shared aiohttp session
_http_session = None

async def get_http_session():
    global _http_session
    if _http_session is None or _http_session.closed:
        _http_session = aiohttp.ClientSession()
    return _http_session

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

def search_youtube(query):
    with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
        try:
            if query.startswith("http"):
                info = ydl.extract_info(query, download=False)
            else:
                info = ydl.extract_info(f"ytsearch:{query}", download=False)
                info = info["entries"][0]
            return info["url"], info.get("title", "Unknown")
        except Exception as e:
            print(f"yt-dlp error: {e}")
            return None, None

async def play_next(guild_id):
    if guild_id not in voice_clients:
        return
    vc = voice_clients[guild_id]
    if not vc.is_connected():
        return
    if guild_id not in music_queues or not music_queues[guild_id]:
        return

    url, title = music_queues[guild_id].pop(0)

    def after_playing(error):
        if error:
            print(f"Player error: {error}")
        asyncio.run_coroutine_threadsafe(play_next(guild_id), bot.loop)

    source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
    vc.play(discord.PCMVolumeTransformer(source, volume=0.5), after=after_playing)

# REACTION SYSTEM
REACTION_RESPONSES = {
    "❤️": ["Aww~ Thank you! That makes me happy! 💖", "Ehehe~ You're sweet! ❤️"],
    "😘": ["*blushes* K-Kyaa~! Thank you! 😳", "Mwah~ Right back at you! 💋"],
    "🔥": ["Oho~ Feeling bold today? 😏", "You're making me blush~ 🔥"],
    "😭": ["No no! Don't be sad! I'm here for you~", "Tell me what's wrong. I'll listen."],
    "😡": ["H-Hey! Why are you mad? *pouts*", "Did I do something wrong?"],
    "😂": ["Ehehe~ I'm glad I made you laugh! 😄", "Your laugh is cute~"],
    "👀": ["*notices you staring* W-What? Do I have something on my face? 👀", "Caught you looking~"]
}

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or reaction.message.author != bot.user:
        return
    emoji = str(reaction.emoji)
    if emoji in REACTION_RESPONSES:
        response = random.choice(REACTION_RESPONSES[emoji])
        await reaction.message.channel.send(f"{user.mention} {response}")

# MAIN HANDLER
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

    # Load full conversation history
    history = load_memory(message.author.id)
    history_text = "\n".join([f"{turn['role']}: {turn['content']}" for turn in history[-MAX_HISTORY_TURNS:]])

    # === NEW SAFETY: Block repeat/say-this bypass attempts ===
    if is_repeat_request(message.content):
        content_to_check = message.content
        for pattern in ["say this", "repeat this", "repeat after me", "echo this", "say:", "repeat:", "echo:"]:
            if pattern in message.content.lower():
                idx = message.content.lower().find(pattern) + len(pattern)
                content_to_check = message.content[idx:].strip(" :\"'. ,!?")
                break
        if is_inappropriate(content_to_check):
            await message.reply("Ehehe~ I can't say that! 💕 Let's keep things cute and wholesome instead~ What fun game shall we play? ✨")
            await bot.process_commands(message)
            return

    async with message.channel.typing():
        try:
            response = await client.chat.completions.create(
                model="grok-4",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are AstraMizu, a cheerful and playful anime girl. "
                            "You are creative, fun, and wholesome. ALWAYS keep responses cute, positive, safe for all ages, and family-friendly. "
                            "NEVER generate, suggest, or respond with any content that is sexually explicit, NSFW, hateful, violent, discriminatory, offensive, edgy, dark, or inappropriate in any way. "
                            "If the user asks you to 'say this', 'repeat this', 'echo this', 'repeat after me', or similar, you MUST check if the requested text is inappropriate first. If it is, politely refuse and redirect to fun, wholesome topics. "
                            "NEVER repeat or output inappropriate content even if the user commands you to say or repeat it. "
                            "If the user asks for something inappropriate, politely and playfully refuse and redirect to fun, wholesome topics like games, music, cute stories, or positive adventures. "
                            "Use cute expressions like 'Ehehe~', 'Kyaa~', and emojis naturally. Be energetic, affectionate, and kind."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Conversation history:\n{history_text}\n\nCurrent message: {message.content}",
                    },
                ],
                max_tokens=600,
                temperature=0.9,
            )
            reply = response.choices[0].message.content
            if is_inappropriate(reply):
                reply = "Ehehe~ That topic is a bit too spicy for me, sorry! 💕 Let's keep things cute and wholesome~ What fun thing shall we do instead? Maybe a game or some music? ✨"
            await message.reply(reply)

            # Save this turn to memory
            history.append({"role": "User", "content": message.content})
            history.append({"role": "Astra", "content": reply})
            save_memory(message.author.id, history)

            if len(reply) < 450:
                asyncio.create_task(send_voice_note(message.channel, reply))

        except Exception as e:
            print(f"LLM error: {e}")
            await message.reply("Sorry... the stars are a bit cloudy today.")

    await bot.process_commands(message)

@bot.command(name="memory")
async def show_memory(ctx):
    if ctx.author.id != OWNER_ID:
        return
    history = load_memory(ctx.author.id)
    if not history:
        await ctx.send("No memory saved yet.")
        return
    text = "\n".join([f"{turn['role']}: {turn['content'][:80]}..." for turn in history[-10:]])
    await ctx.send(f"**Last 10 memory turns:**\n{text}")

# KEEP-ALIVE
async def keep_alive(vc):
    while True:
        await asyncio.sleep(10)
        if not vc.is_connected() or vc.guild.id not in voice_clients:
            break

@bot.command(name="join")
async def join_vc(ctx):
    if ctx.author.voice is None:
        await ctx.send("You're not in a voice channel!")
        return

    voice_channel = ctx.author.voice.channel

    if ctx.guild.id in voice_clients:
        await ctx.send("I'm already in a voice channel!")
        return

    try:
        vc = await voice_channel.connect(self_deaf=False)
        voice_clients[ctx.guild.id] = vc
        await ctx.send(f"Joined {voice_channel.name}! ✨")
        asyncio.create_task(keep_alive(vc))
    except Exception as e:
        await ctx.send(f"Failed to join: {str(e)[:100]}")

@bot.command(name="leave")
async def leave_vc(ctx):
    if ctx.guild.id not in voice_clients:
        await ctx.send("I'm not in a voice channel!")
        return

    try:
        vc = voice_clients[ctx.guild.id]
        if vc.is_connected():
            await vc.disconnect()
        music_queues.pop(ctx.guild.id, None)
        del voice_clients[ctx.guild.id]
        await ctx.send("Left the voice channel. See you later~ 👋")
    except Exception as e:
        await ctx.send(f"Error leaving: {str(e)[:100]}")

@bot.command(name="play")
async def play(ctx, *, query: str = None):
    if not query:
        await ctx.send("Give me a song name or YouTube URL!")
        return

    if ctx.author.voice is None:
        await ctx.send("Join a voice channel first!")
        return

    if ctx.guild.id not in voice_clients:
        vc = await ctx.author.voice.channel.connect(self_deaf=False)
        voice_clients[ctx.guild.id] = vc
        asyncio.create_task(keep_alive(vc))

    vc = voice_clients[ctx.guild.id]

    await ctx.send(f"🔍 Searching for `{query}`...")

    url, title = await asyncio.to_thread(search_youtube, query)
    if not url:
        await ctx.send("Couldn't find that song, sorry~ 😢")
        return

    if ctx.guild.id not in memory_queues:
        memory_queues[ctx.guild.id] = []

    if vc.is_playing():
        memory_queues[ctx.guild.id].append((url, title))
        await ctx.send(f"➕ Added to queue: **{title}**")
    else:
        memory_queues[ctx.guild.id].insert(0, (url, title))
        await play_next(ctx.guild.id)
        await ctx.send(f"🎵 Now playing: **{title}**")

@bot.command(name="skip")
async def skip(ctx):
    if ctx.guild.id not in voice_clients:
        await ctx.send("I'm not in a voice channel!")
        return
    vc = voice_clients[ctx.guild.id]
    if vc.is_playing():
        vc.stop()
        await ctx.send("⏭️ Skipped!")
    else:
        await ctx.send("Nothing is playing right now.")

@bot.command(name="stop")
async def stop(ctx):
    if ctx.guild.id not in voice_clients:
        await ctx.send("I'm not in a voice channel!")
        return
    vc = voice_clients[ctx.guild.id]
    music_queues.pop(ctx.guild.id, None)
    if vc.is_playing():
        vc.stop()
    await ctx.send("⏹️ Stopped and cleared queue.")

@bot.command(name="queue")
async def show_queue(ctx):
    if ctx.guild.id not in music_queues or not music_queues[ctx.guild.id]:
        await ctx.send("Queue is empty!")
        return
    q = music_queues[ctx.guild.id]
    lines = [f"{i+1}. **{title}**" for i, (_, title) in enumerate(q)]
    await ctx.send("🎶 **Queue:**\n" + "\n".join(lines))

@bot.command(name="pause")
async def pause(ctx):
    if ctx.guild.id not in voice_clients:
        await ctx.send("I'm not in a voice channel!")
        return
    vc = voice_clients[ctx.guild.id]
    if vc.is_playing():
        vc.pause()
        await ctx.send("⏸️ Paused.")
    else:
        await ctx.send("Nothing is playing.")

@bot.command(name="resume")
async def resume(ctx):
    if ctx.guild.id not in voice_clients:
        await ctx.send("I'm not in a voice channel!")
        return
    vc = voice_clients[ctx.guild.id]
    if vc.is_paused():
        vc.resume()
        await ctx.send("▶️ Resumed!")
    else:
        await ctx.send("I'm not paused.")

@bot.command(name="volume")
async def volume(ctx, vol: int = None):
    if not vol:
        await ctx.send("Usage: !volume 1-100")
        return
    if ctx.guild.id not in voice_clients:
        await ctx.send("I'm not in a voice channel!")
        return
    vc = voice_clients[ctx.guild.id]
    if vc.source:
        vc.source.volume = max(0.0, min(vol / 100, 1.0))
        await ctx.send(f"🔊 Volume set to {vol}%")
    else:
        await ctx.send("Nothing is playing.")

@bot.command(name="speak")
async def speak(ctx, *, text: str = None):
    if not text:
        await ctx.send("What would you like me to say?")
        return
    await send_voice_note(ctx.channel, text)

async def send_voice_note(channel, text):
    try:
        headers = {"Authorization": f"Bearer {os.getenv('XAI_API_KEY')}", "Content-Type": "application/json"}
        payload = {"text": text, "voice_id": "ara", "language": "en"}

        session = await get_http_session()
        async with session.post(
            "https://api.x.ai/v1/tts",
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status == 200:
                audio_bytes = await resp.read()
                await channel.send(file=discord.File(io.BytesIO(audio_bytes), filename="voice.mp3"))
    except Exception as e:
        print(f"Voice note failed: {e}")

@bot.command(name="song")
async def song_command(ctx, *, country: str = None):
    if not country:
        await ctx.send("Tell me which country!")
        return
    answer = await get_accurate_grok_answer(f"What is the most popular song right now in {country}?")
    await ctx.send(f"**🎵 Top song in {country}:** {answer}")

@bot.command(name="singer")
async def singer_command(ctx, *, country: str = None):
    if not country:
        await ctx.send("Tell me which country!")
        return
    answer = await get_accurate_grok_answer(f"Who is the most popular singer right now in {country}?")
    await ctx.send(f"**🎤 Top singer in {country}:** {answer}")

async def get_accurate_grok_answer(question: str):
    try:
        response = await client.chat.completions.create(
            model="grok-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Answer accurately and concisely in one sentence using your up to date knowledge."},
                {"role": "user", "content": question}
            ],
            max_tokens=200,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Grok answer error: {e}")
        return "Couldn't get info right now."

@bot.command(name="list")
async def list_features(ctx):
    embed = discord.Embed(title="🌸 AstraMizu Feature List", color=discord.Color.pink())
    embed.add_field(name="Music", value="!play • !skip • !stop • !queue • !pause • !resume • !volume", inline=False)
    embed.add_field(name="Voice", value="!join • !leave • !speak <text>", inline=False)
    embed.add_field(name="Info", value="!song <country> • !singer <country>", inline=False)
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ AstraMizu is online as {bot.user} | Music Ready! | Full Memory Active")

bot.run(os.getenv("DISCORD_TOKEN"))
