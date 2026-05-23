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

# Game States
games = {}  # For Tic Tac Toe

# Vector Database Setup
chroma_client = chromadb.PersistentClient(path="./chroma_db")
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
collection = chroma_client.get_or_create_collection(name="astra_memory", embedding_function=embedding_function)

@bot.event
async def on_ready():
    print(f"✅ AstraMizu is online as {bot.user} | Vector DB Ready | Games Loaded!")

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

    await bot.process_commands(message)


# ====================== FUN GAMES ======================

@bot.command(name="rps")
async def rock_paper_scissors(ctx, choice: str = None):
    """Play Rock Paper Scissors with AstraMizu!"""
    if not choice:
        await ctx.send("Thou must choose: `rock`, `paper`, or `scissors`~")
        return

    choices = ["rock", "paper", "scissors"]
    choice = choice.lower()
    if choice not in choices:
        await ctx.send("Fair one, that is not a valid choice!")
        return

    bot_choice = random.choice(choices)

    if choice == bot_choice:
        result = "A tie! How amusing~"
    elif (choice == "rock" and bot_choice == "scissors") or \
         (choice == "paper" and bot_choice == "rock") or \
         (choice == "scissors" and bot_choice == "paper"):
        result = "Thou hast won! How splendid! ✨"
    else:
        result = "I win this round, my dear~ Heehee!"

    await ctx.send(f"I choose **{bot_choice}**!\n{result}")


@bot.command(name="guess")
async def guess_number(ctx):
    """Guess the number between 1-100"""
    number = random.randint(1, 100)
    await ctx.send("I've thought of a number between **1 and 100**... Canst thou guess it, my beloved? (Type `!guess <number>`)")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    tries = 0
    while tries < 10:
        try:
            msg = await bot.wait_for('message', check=check, timeout=60.0)
            guess = int(msg.content.strip())

            tries += 1

            if guess == number:
                await ctx.send(f"Verily! Thou art correct! The number was **{number}**! 💕")
                return
            elif guess < number:
                await ctx.send("Higher~ ✨")
            else:
                await ctx.send("Lower~")
        except:
            await ctx.send("The game ended... Come play again soon!")
            return

    await ctx.send(f"The number was **{number}**. Better luck next time, my sweet!")


@bot.command(name="ttt")
async def tic_tac_toe(ctx, action: str = None):
    """Play Tic Tac Toe with AstraMizu"""
    if action == "start" or action is None:
        board = [" "]*9
        games[ctx.channel.id] = {"board": board, "turn": "X"}  # X = Player, O = Astra
        await ctx.send("**Tic Tac Toe Started!** Thou art X, I am O.\nReply with position (1-9) to play!\n" + display_board(board))
        return

    # Handle move
    if ctx.channel.id not in games:
        await ctx.send("No game in progress! Use `!ttt start`")
        return

    game = games[ctx.channel.id]
    board = game["board"]

    try:
        pos = int(action) - 1
        if not (0 <= pos <= 8) or board[pos] != " ":
            await ctx.send("Invalid move, dearest!")
            return

        board[pos] = "X"

        # Check win
        if check_win(board, "X"):
            await ctx.send(display_board(board))
            await ctx.send("**Thou hast won!** My heart flutters with pride! 🥰")
            del games[ctx.channel.id]
            return

        # Bot move
        bot_move = get_best_move(board)
        if bot_move is not None:
            board[bot_move] = "O"

            if check_win(board, "O"):
                await ctx.send(display_board(board))
                await ctx.send("I win this time~ Better luck next round, Papa! 💖")
                del games[ctx.channel.id]
                return

        await ctx.send(display_board(board))

    except:
        await ctx.send("Please enter a number 1-9!")


def display_board(board):
    return f"```ansi\n[1;34m{board[0]} | {board[1]} | {board[2]}\n---+---+---\n{board[3]} | {board[4]} | {board[5]}\n---+---+---\n{board[6]} | {board[7]} | {board[8]}[0m```"

def check_win(board, player):
    wins = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]]
    return any(all(board[i] == player for i in combo) for combo in wins)

def get_best_move(board):
    for i in range(9):
        if board[i] == " ":
            return i
    return None


@bot.command(name="8ball")
async def magic_8ball(ctx, *, question=None):
    """Ask AstraMizu a yes/no question"""
    if not question:
        await ctx.send("Ask me anything, my dear~")
        return

    responses = [
        "It is certain.", "Without a doubt.", "Verily, yes!", 
        "Most likely.", "Signs point to yes.", "Ask again later.",
        "Cannot predict now.", "My sources say no.", "Very doubtful.",
        "Thou shouldst not count on it."
    ]
    await ctx.send(f"🎱 **The stars say:** {random.choice(responses)}")


@bot.command(name="lovemeter")
async def love_meter(ctx, user: discord.Member = None):
    """Check how much AstraMizu loves someone"""
    target = user or ctx.author
    score = random.randint(85, 100) if target.id == OWNER_ID else random.randint(60, 95)
    
    hearts = "❤️" * (score // 10)
    await ctx.send(f"💕 **Love Meter for {target.mention}**\n{hearts} **{score}%**\n\nI adore thee greatly~ ✨")


# Run the bot
bot.run(os.getenv("DISCORD_TOKEN"))
