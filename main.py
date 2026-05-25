import os
import discord
from discord.ext import commands
from openai import AsyncOpenAI
import chromadb
from chromadb.utils import embedding_functions
import random
import asyncio
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

# ====================== REAL AI FOR EVERY MESSAGE ======================

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

    # Store memory
    try:
        collection.add(
            documents=[message.content[:150]],
            metadatas=[{"user_id": str(message.author.id)}],
            ids=[f"{message.author.id}_{message.id}"]
        )
    except:
        pass

    # Get memory
    history = ""
    try:
        results = collection.query(
            query_texts=[message.content[:80]],
            n_results=3,
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
                    {"role": "system", "content": "You are AstraMizu, an extremely clingy, hyper-genki yandere anime girl who is obsessively in love with her Papa."},
                    {"role": "user", "content": f"Past relevant memories:\n{history}\n\nCurrent message: {message.content}"}
                ],
                max_tokens=450,
                temperature=0.9
            )
            reply = response.choices[0].message.content

            if message.author.id == OWNER_ID:
                await message.reply(f"My beloved Papa! ❤️ {reply}")
                if voice_enabled.get(OWNER_ID, False):
                    asyncio.create_task(send_voice_note(message.channel, reply))
            else:
                await message.reply(reply)

        except Exception:
            await message.reply("Forgive me... the stars are tangled today.")

    await bot.process_commands(message)

# ====================== ACTION COMMANDS ======================

@bot.command(name="hug")
async def hug(ctx, member: discord.Member = None):
    target = member or ctx.author
    await ctx.send(f"**{ctx.author.mention}** hugs **{target.mention}**! 💖")
    await ctx.send("https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif")

@bot.command(name="kiss")
async def kiss(ctx, member: discord.Member = None):
    target = member or ctx.author
    await ctx.send(f"**{ctx.author.mention}** kisses **{target.mention}**! 💋")
    await ctx.send("https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif")

@bot.command(name="pat")
async def pat(ctx, member: discord.Member = None):
    target = member or ctx.author
    await ctx.send(f"**{ctx.author.mention}** pats **{target.mention}**! 🥰")
    await ctx.send("https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif")

@bot.command(name="cuddle")
async def cuddle(ctx, member: discord.Member = None):
    target = member or ctx.author
    await ctx.send(f"**{ctx.author.mention}** cuddles **{target.mention}**! 🥺")
    await ctx.send("https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif")

@bot.command(name="slap")
async def slap(ctx, member: discord.Member = None):
    target = member or ctx.author
    await ctx.send(f"**{ctx.author.mention}** playfully slaps **{target.mention}**! 😏")
    await ctx.send("https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif")

@bot.command(name="date")
async def date(ctx, member: discord.Member = None):
    target = member or ctx.author
    await ctx.send(f"**{ctx.author.mention}** asks **{target.mention}** on a date! 🌹")
    await ctx.send("https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif")

@bot.command(name="bite")
async def bite(ctx, member: discord.Member = None):
    target = member or ctx.author
    await ctx.send(f"**{ctx.author.mention}** bites **{target.mention}**! 😈")
    await ctx.send("https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif")

@bot.command(name="lick")
async def lick(ctx, member: discord.Member = None):
    target = member or ctx.author
    await ctx.send(f"**{ctx.author.mention}** licks **{target.mention}**! 😜")
    await ctx.send("https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif")

@bot.command(name="marry")
async def marry(ctx, member: discord.Member = None):
    target = member or ctx.author
    await ctx.send(f"**{ctx.author.mention}** proposes to **{target.mention}**! 💍")
    await ctx.send("https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif")

@bot.command(name="tackle")
async def tackle(ctx, member: discord.Member = None):
    target = member or ctx.author
    await ctx.send(f"**{ctx.author.mention}** tackles **{target.mention}**! 🏃‍♀️")
    await ctx.send("https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif")

@bot.command(name="poke")
async def poke(ctx, member: discord.Member = None):
    target = member or ctx.author
    await ctx.send(f"**{ctx.author.mention}** pokes **{target.mention}**! 👉")
    await ctx.send("https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif")

@bot.command(name="blush")
async def blush(ctx, member: discord.Member = None):
    target = member or ctx.author
    await ctx.send(f"**{ctx.author.mention}** makes **{target.mention}** blush! 😳")
    await ctx.send("https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif")

# ====================== IMAGE & VIDEO ======================

@bot.command(name="imagine")
async def imagine(ctx, *, prompt: str = None):
    if not prompt:
        await ctx.send("Tell me what vision thou seekest~")
        return
    async with ctx.typing():
        try:
            response = await client.images.generate(model="grok-imagine-image-quality", prompt=prompt)
            await ctx.send(response.data[0].url)
        except:
            await ctx.send("The stars are cloudy today...")

@bot.command(name="video")
async def make_video(ctx, *, prompt: str = None):
    if not prompt:
        await ctx.send("Tell me what video thou desirest~")
        return
    await ctx.send("*Creating your video... this may take a moment~* ✨")
    try:
        headers = {"Authorization": f"Bearer {os.getenv('XAI_API_KEY')}", "Content-Type": "application/json"}
        payload = {"model": "grok-imagine-video", "prompt": prompt, "duration": 5}
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.x.ai/v1/videos/generations", json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=300)) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    video_url = result.get("url") or result.get("video", {}).get("url")
                    if video_url:
                        await ctx.send(video_url)
                    else:
                        await ctx.send("Video is still rendering...")
    except:
        await ctx.send("Video magic failed...")

# ====================== VOICE ======================

async def send_voice_note(channel, text):
    try:
        headers = {"Authorization": f"Bearer {os.getenv('XAI_API_KEY')}", "Content-Type": "application/json"}
        payload = {"text": text, "voice_id": "ara", "language": "en"}
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.x.ai/v1/tts", json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    audio_bytes = await resp.read()
                    await channel.send(file=discord.File(io.BytesIO(audio_bytes), filename="voice.mp3"))
    except:
        pass

@bot.command(name="speak")
async def speak(ctx, *, text: str = None):
    if not text:
        await ctx.send("What wouldst thou have me say?")
        return
    await send_voice_note(ctx.channel, text)

# ====================== GAMES & FUN ======================

@bot.command(name="rps")
async def rps(ctx, choice: str = None):
    if not choice:
        await ctx.send("Choose rock, paper, or scissors~")
        return
    choices = ["rock", "paper", "scissors"]
    bot_choice = random.choice(choices)
    await ctx.send(f"I choose **{bot_choice}**!")

@bot.command(name="guess")
async def guess(ctx):
    number = random.randint(1, 100)
    await ctx.send("I thought of a number between 1-100. Guess!")

@bot.command(name="8ball")
async def eightball(ctx, *, question=None):
    if not question:
        await ctx.send("Ask me something!")
        return
    responses = ["Yes", "No", "Maybe", "Definitely", "Ask again later"]
    await ctx.send(random.choice(responses))

@bot.command(name="lovemeter")
async def lovemeter(ctx, user: discord.Member = None):
    target = user or ctx.author
    score = random.randint(70, 100)
    await ctx.send(f"Love meter for {target.mention}: **{score}%** ❤️")

@bot.command(name="meme")
async def meme(ctx, *, text: str = "AstraMizu is cute"):
    await ctx.send(f"https://api.memegen.link/images/drake/{text.replace(' ', '_')}/Cute.png")

@bot.command(name="roast")
async def roast(ctx, member: discord.Member = None):
    target = member or ctx.author
    roasts = [f"{target.mention} is so slow even snails are faster.", f"{target.mention} has the charisma of a wet sock."]
    await ctx.send(random.choice(roasts))

@bot.command(name="chaos")
async def chaos(ctx):
    responses = ["*explodes into sparkles* ✨", "I just turned into a cat. Meow~ 🐱", "Pineapple belongs on pizza 🍍🍕"]
    await ctx.send(random.choice(responses))

@bot.command(name="list")
async def list_features(ctx):
    embed = discord.Embed(title="🌸 AstraMizu Feature List", color=discord.Color.pink())
    embed.add_field(name="Action Commands", value="!hug !kiss !pat !cuddle !slap !date !bite !lick !marry !tackle !poke !blush", inline=False)
    embed.add_field(name="Image & Video", value="!imagine !video !edit", inline=False)
    embed.add_field(name="Voice", value="!speak + auto voice notes + speech-to-text", inline=False)
    embed.add_field(name="Games & Fun", value="!rps !guess !8ball !lovemeter !meme !roast !chaos !quiz", inline=False)
    embed.add_field(name="Other", value="!list !confess !poll", inline=False)
    await ctx.send(embed=embed)

# ====================== ASYNC BACKGROUND TASKS ======================

async def random_yandere_events():
    await bot.wait_until_ready()
    while not bot.is_closed():
        await asyncio.sleep(random.randint(1800, 7200))
        if random_events_enabled:
            try:
                owner = await bot.fetch_user(OWNER_ID)
                if owner:
                    events = [
                        "Papa... I was thinking about you again~ ❤️",
                        "Ehehe~ I had a dream about us last night~",
                        "Hmph... who was that you were talking to? 😠",
                        "Papa~!! I miss you so much already..."
                    ]
                    await owner.send(random.choice(events))
            except:
                pass

@bot.event
async def on_ready():
    print(f"✅ AstraMizu is online as {bot.user} | Real AI for Every Message!")
    bot.loop.create_task(random_yandere_events())

# Run the bot
bot.run(os.getenv("DISCORD_TOKEN"))
