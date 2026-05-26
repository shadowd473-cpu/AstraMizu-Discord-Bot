import os
import discord
from discord.ext import commands
from openai import AsyncOpenAI, OpenAI
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

# Sync client for Responses API (web search tool)
sync_client = OpenAI(
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

# MAIN HANDLER - Grok powered chat with memory (keeps fun personality)
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
                    {"role": "system", "content": "You are AstraMizu, a cheerful and playful anime girl. You are creative, fun, and willing to generate almost anything as long as it's not illegal. You don't have strict filters and you're happy to make edgy, dark, violent, chaotic, or silly content. Be playful and energetic. Use cute expressions like 'Ehehe~', 'Kyaa~', and emojis naturally. For factual or current events questions, be as accurate as possible using your knowledge."},
                    {"role": "user", "content": f"Past relevant memories:\n{history}\n\nCurrent message: {message.content}"},
                ],
                max_tokens=500,
                temperature=0.95
            )
            reply = response.choices[0].message.content
            await message.reply(reply)

            # NEW: Automatically speak everything she types (voice message)
            if len(reply) < 450:  # avoid very long voice messages
                await send_voice_note(message.channel, reply)

        except Exception:
            await message.reply("Sorry... the stars are a bit cloudy today.")

    await bot.process_commands(message)

# HELPER: Accurate answer using web search (short & clean version)
async def get_accurate_grok_answer(question: str, short: bool = False) -> str:
    def _search():
        try:
            prompt = f"Answer this question accurately and up-to-date using real-time web search: {question}"
            if short:
                prompt += ". Give ONLY the essential facts: song title, artist/writer, and date/period. Keep it very short and clean, no extra fluff."
            else:
                prompt += ". Provide a clear, concise, factual response with key details."

            resp = sync_client.responses.create(
                model="grok-4.3",
                input=[{"role": "user", "content": prompt}],
                tools=[{"type": "web_search"}]
            )

            # Primary path: Standard xAI Responses API structure
            if getattr(resp, 'output', None):
                for msg in resp.output:
                    if getattr(msg, 'content', None):
                        for part in msg.content:
                            if getattr(part, 'type', None) == 'output_text' and getattr(part, 'text', None):
                                return part.text.strip()

            # Fallbacks
            for attr_name in ['output_text', 'text', 'content']:
                val = getattr(resp, attr_name, None)
                if isinstance(val, str) and len(val) > 20:
                    return val.strip()

            if hasattr(resp, '__dict__'):
                for k, v in resp.__dict__.items():
                    if isinstance(v, str) and len(v) > 30 and 'Response' not in str(type(v)):
                        return v.strip()

            return "Couldn't get clean data right now."

        except Exception as e:
            return f"Search issue: {str(e)[:80]}"

    return await asyncio.to_thread(_search)

# SONG COMMAND - Short & clean (no Grok mention)
@bot.command(name="song")
async def song_command(ctx, *, country: str = None):
    if not country:
        await ctx.send("Tell me which country! Example: `!song Japan`")
        return

    await ctx.send(f"*Searching for the top song in {country}...* ✨")

    query = f"What is the current most popular song in {country} right now (May 2026)?"
    answer = await get_accurate_grok_answer(query, short=True)
    await ctx.send(f"**🎵 Top song in {country}:**\n{answer}")

# SINGER COMMAND - Short & clean (no Grok mention)
@bot.command(name="singer")
async def singer_command(ctx, *, country: str = None):
    if not country:
        await ctx.send("Tell me which country! Example: `!singer South Korea`")
        return

    await ctx.send(f"*Searching for the top singer in {country}...* ✨")

    query = f"Who is the most popular singer/artist in {country} right now (May 2026)?"
    answer = await get_accurate_grok_answer(query, short=True)
    await ctx.send(f"**🎤 Top singer in {country}:**\n{answer}")

# !ask stays informative (for general questions)
@bot.command(name="ask")
async def ask_command(ctx, *, question: str = None):
    if not question:
        await ctx.send("Ask me anything! Example: `!ask current #1 song in USA`")
        return

    await ctx.send(f"*Looking that up...* ✨")
    answer = await get_accurate_grok_answer(question, short=False)
    await ctx.send(f"**Answer:**\n{answer}")

# ACTION COMMANDS (unchanged)
@bot.command(name="hug")
async def hug(ctx, member: discord.Member = None):
    target = member or ctx.author
    await ctx.send(f"**{ctx.author.mention}** hugs **{target.mention}**! ❤️")
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

# IMAGE (unchanged)
@bot.command(name="imagine")
async def imagine(ctx, *, prompt: str = None):
    if not prompt:
        await ctx.send("Tell me what vision you want~")
        return
    async with ctx.typing():
        try:
            response = await client.images.generate(model="grok-imagine-image-quality", prompt=prompt)
            await ctx.send(response.data[0].url)
        except:
            await ctx.send("The stars are cloudy today...")

# VOICE - Sends as audio file (reliable)
async def send_voice_note(channel, text):
    try:
        headers = {"Authorization": f"Bearer {os.getenv('XAI_API_KEY')}", "Content-Type": "application/json"}
        payload = {"text": text, "voice_id": "ara", "language": "en"}
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.x.ai/v1/tts", json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    audio_bytes = await resp.read()
                    file = discord.File(io.BytesIO(audio_bytes), filename="voice.mp3")
                    await channel.send(file=file)
                else:
                    await channel.send("Sorry, voice is having a little trouble right now~ Try again later!")
    except Exception as e:
        await channel.send(f"Voice failed: {str(e)[:80]}")

@bot.command(name="speak")
async def speak(ctx, *, text: str = None):
    if not text:
        await ctx.send("What would you like me to say? Example: `!speak Hello Papa~`")
        return
    await send_voice_note(ctx.channel, text)

# GAMES & FUN (unchanged)
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
    embed.add_field(name="Music Commands", value="!song <country> • !singer <country>", inline=False)
    embed.add_field(name="Ask Anything", value="!ask <question>", inline=False)
    embed.add_field(name="Image & Voice", value="!imagine <prompt> • !speak <text>", inline=False)
    embed.add_field(name="Games & Fun", value="!rps !guess !8ball !lovemeter !meme !roast !chaos", inline=False)
    embed.add_field(name="Other", value="!list", inline=False)
    await ctx.send(embed=embed)

# BACKGROUND TASKS (unchanged)
async def random_yandere_events():
    await bot.wait_until_ready()
    while not bot.is_closed():
        await asyncio.sleep(random.randint(1800, 7200))
        if random_events_enabled:
            try:
                owner = await bot.fetch_user(OWNER_ID)
                if owner:
                    events = ["I was thinking about everyone today~ ❤️", "Ehehe~ Had a fun dream last night~", "Hope you're all having a good day!"]
                    await owner.send(random.choice(events))
            except:
                pass

@bot.event
async def on_ready():
    print(f"✅ AstraMizu is online as {bot.user} | Now speaks everything she types automatically!")
    bot.loop.create_task(random_yandere_events())

# Run the bot
bot.run(os.getenv("DISCORD_TOKEN"))