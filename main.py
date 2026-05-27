import os
import discord
from discord.ext import commands
from discord.ext import voice_recv
from openai import AsyncOpenAI, OpenAI
import chromadb
from chromadb.utils import embedding_functions
import random
import asyncio
import aiohttp
import io
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

sync_client = OpenAI(
    api_key=os.getenv("XAI_API_KEY"),
    base_url="https://api.x.ai/v1"
)

deepgram = DeepgramClient(api_key=os.getenv("DEEPGRAM_API_KEY"))

OWNER_ID = 406054379406229504
TRIGGER_WORDS = ["astra", "mizu", "astramizu"]

voice_enabled = {OWNER_ID: True}
random_events_enabled = True
games = {}

chroma_client = chromadb.PersistentClient(path="./chroma_db")
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
collection = chroma_client.get_or_create_collection(name="astra_memory", embedding_function=embedding_function)

# Voice state
voice_clients = {}
listening_tasks = {}
listen_channels = {}

# Shared aiohttp session
_http_session = None

async def get_http_session():
    global _http_session
    if _http_session is None or _http_session.closed:
        _http_session = aiohttp.ClientSession()
    return _http_session

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

    try:
        collection.add(
            documents=[message.content[:150]],
            metadatas=[{"user_id": str(message.author.id)}],
            ids=[f"{message.author.id}_{message.id}"]
        )
    except:
        pass

    history = ""
    try:
        results = collection.query(
            query_texts=[message.content[:80]],
            n_results=4,
            where={"user_id": str(message.author.id)}
        )
        if results and results.get("documents"):
            history = "\n".join(results["documents"][0])
    except:
        pass

    async with message.channel.typing():
        try:
            response = await client.chat.completions.create(
                model="grok-4",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are AstraMizu, a cheerful and playful anime girl. "
                            "You are creative, fun, and willing to generate almost anything "
                            "as long as it's not illegal. You don't have strict filters and "
                            "you're happy to make edgy, dark, violent, chaotic, or silly content. "
                            "Be playful and energetic. Use cute expressions like 'Ehehe~', "
                            "'Kyaa~', and emojis naturally."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Past relevant memories:\n{history}\n\nCurrent message: {message.content}",
                    },
                ],
                max_tokens=500,
                temperature=0.95,
            )
            reply = response.choices[0].message.content
            await message.reply(reply)

            if len(reply) < 450:
                asyncio.create_task(send_voice_note(message.channel, reply))

        except Exception as e:
            print(f"LLM error: {e}")
            await message.reply("Sorry... the stars are a bit cloudy today.")

    await bot.process_commands(message)

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
        # Normal stable connect — no voice receiving yet
        vc = await voice_channel.connect(self_deaf=True)
        voice_clients[ctx.guild.id] = vc
        await ctx.send(f"Joined {voice_channel.name}! ✨ Use !listen to activate voice chat.")
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

        if ctx.guild.id in listening_tasks:
            try:
                listening_tasks[ctx.guild.id].finish()
            except:
                pass
            del listening_tasks[ctx.guild.id]

        if ctx.guild.id in listen_channels:
            del listen_channels[ctx.guild.id]

        del voice_clients[ctx.guild.id]
        await ctx.send("Left the voice channel. See you later~ 👋")

    except Exception as e:
        await ctx.send(f"Error leaving: {str(e)[:100]}")

@bot.command(name="listen")
async def start_listen(ctx):
    if ctx.guild.id not in voice_clients:
        await ctx.send("Use !join first!")
        return

    vc = voice_clients[ctx.guild.id]
    listen_channels[ctx.guild.id] = ctx.channel

    try:
        # Disconnect normal client and reconnect with VoiceRecvClient
        voice_channel = vc.channel
        await vc.disconnect()

        recv_vc = await voice_channel.connect(cls=voice_recv.VoiceRecvClient, self_deaf=False)
        voice_clients[ctx.guild.id] = recv_vc

        # Connect to Deepgram
        dg_connection = deepgram.listen.live.v("1")

        async def handle_transcript(result, **kwargs):
            try:
                transcript = result.channel.alternatives[0].transcript
                if not transcript or len(transcript.strip()) < 3:
                    return
                if not result.is_final:
                    return

                print(f"Heard: {transcript}")

                grok_response = await client.chat.completions.create(
                    model="grok-4",
                    messages=[
                        {"role": "system", "content": "You are AstraMizu, a cheerful and playful anime girl. Keep responses short and natural for voice. 1-2 sentences max."},
                        {"role": "user", "content": transcript}
                    ],
                    max_tokens=150,
                    temperature=0.9
                )
                reply = grok_response.choices[0].message.content
                print(f"Replying: {reply}")
                await speak_in_voice_channel(recv_vc, reply)

            except Exception as e:
                print(f"Transcript error: {e}")

        dg_connection.on(LiveTranscriptionEvents.Transcript, handle_transcript)

        options = LiveOptions(
            model="nova-2",
            language="en-US",
            smart_format=True,
            interim_results=False,
            endpointing=500,
            encoding="linear16",
            sample_rate=48000,
            channels=2,
        )

        dg_connection.start(options)

        class DeepgramSink(voice_recv.AudioSink):
            def __init__(self, dg_conn):
                self.dg_conn = dg_conn

            def wants_opus(self):
                return False

            def write(self, user, data):
                try:
                    if user is None or user.bot:
                        return
                    self.dg_conn.send(data.pcm)
                except Exception as e:
                    print(f"Sink error: {e}")

            def cleanup(self):
                pass

        sink = DeepgramSink(dg_connection)
        recv_vc.listen(sink)
        listening_tasks[ctx.guild.id] = dg_connection

        await ctx.send("Listening! Speak and I'll respond~ 🎤")

    except Exception as e:
        print(f"Listen error: {e}")
        await ctx.send(f"Listening failed: {str(e)[:100]}")

@bot.command(name="stoplisten")
async def stop_listen(ctx):
    if ctx.guild.id not in voice_clients:
        await ctx.send("I'm not in a voice channel!")
        return

    vc = voice_clients[ctx.guild.id]
    voice_channel = vc.channel

    try:
        vc.stop_listening()
    except:
        pass

    if ctx.guild.id in listening_tasks:
        try:
            listening_tasks[ctx.guild.id].finish()
        except:
            pass
        del listening_tasks[ctx.guild.id]

    # Reconnect as normal stable client
    await vc.disconnect()
    new_vc = await voice_channel.connect(self_deaf=True)
    voice_clients[ctx.guild.id] = new_vc
    asyncio.create_task(keep_alive(new_vc))

    await ctx.send("Stopped listening, still in VC~ 🔇")

async def speak_in_voice_channel(vc, text):
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
                with open("temp_voice.mp3", "wb") as f:
                    f.write(audio_bytes)
                while vc.is_playing():
                    await asyncio.sleep(0.5)
                source = discord.FFmpegPCMAudio("temp_voice.mp3")
                vc.play(source)
            else:
                print(f"TTS failed: {resp.status} {await resp.text()}")
    except Exception as e:
        print(f"TTS in VC failed: {e}")

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
    answer = await get_accurate_grok_answer(f"Current most popular song in {country}", short=True)
    await ctx.send(f"**🎵 Top song in {country}:** {answer}")

@bot.command(name="singer")
async def singer_command(ctx, *, country: str = None):
    if not country:
        await ctx.send("Tell me which country!")
        return
    answer = await get_accurate_grok_answer(f"Most popular singer in {country}", short=True)
    await ctx.send(f"**🎤 Top singer in {country}:** {answer}")

async def get_accurate_grok_answer(question: str, short: bool = False):
    def _search():
        try:
            prompt = f"Answer accurately: {question}"
            if short:
                prompt += ". Keep it short."
            resp = sync_client.responses.create(
                model="grok-4.3",
                input=[{"role": "user", "content": prompt}],
                tools=[{"type": "web_search"}]
            )
            if hasattr(resp, 'output') and resp.output:
                return resp.output[0].content[0].text.strip()
            return str(resp)[:500]
        except:
            return "Couldn't get info right now."
    return await asyncio.to_thread(_search)

@bot.command(name="list")
async def list_features(ctx):
    embed = discord.Embed(title="🌸 AstraMizu Feature List", color=discord.Color.pink())
    embed.add_field(name="Voice Commands", value="!join • !leave • !listen • !stoplisten • !speak", inline=False)
    embed.add_field(name="Music & Info", value="!song <country> • !singer <country>", inline=False)
    embed.add_field(name="Fun Commands", value="!hug !kiss !imagine and more!", inline=False)
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ AstraMizu is online as {bot.user} | Voice Ready!")

bot.run(os.getenv("DISCORD_TOKEN"))
