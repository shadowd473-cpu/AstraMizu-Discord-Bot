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

voice_enabled = {OWNER_ID: True}
random_events_enabled = True
games = {}

chroma_client = chromadb.PersistentClient(path="./chroma_db")
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
collection = chroma_client.get_or_create_collection(name="astra_memory", embedding_function=embedding_function)

app = Flask(__name__)

DASHBOARD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>AstraMizu Dashboard</title>
    <style>
        body { font-family: system-ui; background: #0f0f23; color: #eee; padding: 30px; }
        .container { max-width: 1000px; margin: auto; }
        h1 { color: #ff69b4; text-align: center; }
        .card { background: #1a1a3a; padding: 25px; margin: 20px 0; border-radius: 15px; box-shadow: 0 4px 20px rgba(255,105,180,0.1); }
        .toggle { margin: 15px 0; font-size: 1.1em; }
        button { background: #ff69b4; color: white; border: none; padding: 12px 25px; border-radius: 8px; cursor: pointer; font-size: 1em; }
        .memory { background: #16213e; padding: 12px; margin: 8px 0; border-radius: 8px; }
        .stats { font-size: 1.2em; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌸 AstraMizu Control Panel</h1>
        <p style="text-align:center">Welcome back, Papa ❤️</p>
        
        <div class="card">
            <h2>⚙️ Feature Toggles</h2>
            <form action="/toggle" method="post">
                <div class="toggle">
                    <label>🎙️ Voice Notes: </label>
                    <input type="checkbox" name="voice" {% if voice_enabled %}checked{% endif %}>
                </div>
                <div class="toggle">
                    <label>💖 Random Yandere Events: </label>
                    <input type="checkbox" name="events" {% if random_events_enabled %}checked{% endif %}>
                </div>
                <button type="submit">Save Changes</button>
            </form>
        </div>

        <div class="card">
            <h2>🧠 Recent Memories</h2>
            {% for mem in memories %}
                <div class="memory">{{ mem }}</div>
            {% endfor %}
        </div>

        <div class="card stats">
            <h2>📊 Quick Stats</h2>
            <p>Messages remembered: <strong>{{ memory_count }}</strong></p>
            <p>Voice Notes: <strong>{{ 'Enabled' if voice_enabled else 'Disabled' }}</strong></p>
        </div>
    </div>
</body>
</html>
'''

@app.route('/')
def dashboard():
    memories = []
    try:
        results = collection.query(query_texts=[" "], n_results=15)
        if results and results.get("documents"):
            memories = [m[:120] + "..." if len(m) > 120 else m for m in results["documents"][0][:15]]
    except:
        memories = ["No memories stored yet..."]
    
    memory_count = collection.count() if hasattr(collection, 'count') else len(memories)
    
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
    print(f"✅ AstraMizu is online as {bot.user} | Web Dashboard running at port 5000")
    bot.loop.create_task(random_yandere_events())
    threading.Thread(target=run_dashboard, daemon=True).start()

# [All other functions remain the same - on_message, send_voice_note, imagine, video, etc.]

bot.run(os.getenv("DISCORD_TOKEN"))
