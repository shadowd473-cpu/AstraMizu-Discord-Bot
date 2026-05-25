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
from flask import Flask, render_template_string, request, redirect, url_for
import threading

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

# Voice settings
voice_enabled = {OWNER_ID: True}
random_events_enabled = True

# Game States
games = {}  # For Tic Tac Toe

# Vector Database Setup
chroma_client = chromadb.PersistentClient(path="./chroma_db")
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
collection = chroma_client.get_or_create_collection(name="astra_memory", embedding_function=embedding_function)

# Flask Dashboard
app = Flask(__name__)

DASHBOARD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>AstraMizu Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }
        .container { max-width: 900px; margin: auto; }
        h1 { color: #ff69b4; }
        .card { background: #16213e; padding: 20px; margin: 15px 0; border-radius: 10px; }
        .toggle { margin: 10px 0; }
        button { background: #ff69b4; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
        .memory { background: #0f3460; padding: 10px; margin: 5px 0; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌸 AstraMizu Dashboard</h1>
        <p>Welcome back, Papa ❤️</p>
        
        <div class="card">
            <h2>Feature Toggles</h2>
            <form action="/toggle" method="post">
                <div class="toggle">
                    <label>Voice Notes: </label>
                    <input type="checkbox" name="voice" {% if voice_enabled %}checked{% endif %}>
                </div>
                <div class="toggle">
                    <label>Random Yandere Events: </label>
                    <input type="checkbox" name="events" {% if random_events_enabled %}checked{% endif %}>
                </div>
                <button type="submit">Save Settings</button>
            </form>
        </div>

        <div class="card">
            <h2>Recent Memories</h2>
            {% for mem in memories %}
                <div class="memory">{{ mem }}</div>
            {% endfor %}
        </div>

        <div class="card">
            <h2>Quick Stats</h2>
            <p>Messages in memory: {{ memory_count }}</p>
            <p>Voice Notes: {{ 'Enabled' if voice_enabled else 'Disabled' }}</p>
        </div>
    </div>
</body>
</html>
'''

@app.route('/')
def dashboard():
    memories = []
    try:
        results = collection.query(query_texts=[" "], n_results=10)
        if results and results.get("documents"):
            memories = results["documents"][0][:10]
    except:
        memories = ["No memories yet..."]
    
    memory_count = collection.count() if hasattr(collection, 'count') else 0
    
    return render_template_string(DASHBOARD_HTML, 
        memories=memories,
        memory_count=memory_count,
        voice_enabled=voice_enabled.get(OWNER_ID, False),
        random_events_enabled=random_events_enabled
    )

@app.route('/toggle', methods=['POST'])
def toggle_features():
    global voice_enabled, random_events_enabled
    voice_enabled[OWNER_ID] = 'voice' in request.form
    random_events_enabled = 'events' in request.form
    return redirect(url_for('dashboard'))


def run_dashboard():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

@bot.event
async def on_ready():
    print(f"✅ AstraMizu is online as {bot.user} | Dashboard running on port 5000")
    bot.loop.create_task(random_yandere_events())
    # Start Flask in background
    threading.Thread(target=run_dashboard, daemon=True).start()

# ... (rest of the code remains the same as before)

# [All previous functions like on_message, send_voice_note, imagine, video, etc. remain unchanged]

# Run the bot
bot.run(os.getenv("DISCORD_TOKEN"))
