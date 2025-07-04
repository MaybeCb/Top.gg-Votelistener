import discord
from discord.ext import commands
from aiohttp import web
import asyncio
import json
import os
from datetime import datetime

# Load settings
with open("settings.json", "r") as f:
    config = json.load(f)

BOT_TOKEN = config["bot_token"]
WEBHOOK_AUTH = config["webhook_auth"]
LOG_CHANNEL_ID = config["vote_channel_id"]  # Renamed for consistency
PORT = config["port"]
EMBED_COLOR = int(config.get("default_embed_color", "0x5865F2"), 16)

# Ensure data folder
os.makedirs("data", exist_ok=True)
VOTES_FILE = "data/votes.json"

# Load vote history
if os.path.exists(VOTES_FILE):
    with open(VOTES_FILE, "r") as f:
        vote_data = json.load(f)
else:
    vote_data = {}

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

routes = web.RouteTableDef()

@routes.post('/vote')
async def vote_handler(request):
    if request.headers.get("Authorization") != WEBHOOK_AUTH:
        return web.Response(status=401, text="Unauthorized")

    try:
        data = await request.json()
        user_id = int(data["user"])
        bot_id = int(data["bot"])
        is_weekend = data.get("isWeekend", False)
    except Exception as e:
        print(f"[Error] Malformed payload: {e}")
        return web.Response(status=400, text="Bad Request")

    # Fetch voter and voted bot info
    try:
        user = await bot.fetch_user(user_id)
    except:
        user = discord.Object(id=user_id)

    try:
        voted_bot = await bot.fetch_user(bot_id)
    except:
        voted_bot = discord.Object(id=bot_id)

    now = datetime.utcnow()
    now_str = now.strftime('%d-%m-%Y %H:%M UTC')

    # Track vote count
    vote_data[str(user_id)] = vote_data.get(str(user_id), 0) + 1
    vote_count = vote_data[str(user_id)]

    # Save updated data
    with open(VOTES_FILE, "w") as f:
        json.dump(vote_data, f, indent=4)

    # Build embed
    embed = discord.Embed(
        description=f"🎉 <@{user_id}> just voted for {voted_bot.mention}!",
        color=EMBED_COLOR,
        timestamp=now
    )
    embed.set_thumbnail(url=getattr(voted_bot, "display_avatar", voted_bot).url)
    embed.add_field(name="Vote Count", value=f"`{vote_count}`", inline=True)
    embed.add_field(name="Weekend?", value="✅" if is_weekend else "❌", inline=True)
    embed.set_footer(text=f"Thanks for supporting! • {now_str}")

    # Send embed to vote log channel
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)

    # Try DMing voter
    try:
        await user.send(f"❤️ Thanks for voting for **{getattr(voted_bot, 'name', 'our bot')}** on Top.gg!")
    except:
        print(f"[DM] Could not send DM to {user_id}")

    return web.Response(status=200, text="Vote processed")

async def start_webhook():
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"[Webhook] Listening on port {PORT}")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    await start_webhook()

bot.run(BOT_TOKEN)
