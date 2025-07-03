import discord
from discord.ext import commands
from aiohttp import web
import asyncio
import json
from datetime import datetime

# Load config
with open("settings.json", "r") as f:
    config = json.load(f)

BOT_TOKEN = config["bot_token"]
WEBHOOK_AUTH = config["webhook_auth"]
LOG_CHANNEL_ID = config["log_channel_id"]
PORT = config["port"]

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Aiohttp routes
routes = web.RouteTableDef()

# Optional in-memory vote count for demonstration
user_votes = {}

@routes.post('/vote')
async def vote_handler(request):
    if request.headers.get("Authorization") != WEBHOOK_AUTH:
        return web.Response(status=401, text="Unauthorized")

    data = await request.json()
    user_id = int(data["user"])
    is_weekend = data.get("isWeekend", False)

    user = await bot.fetch_user(user_id)
    now = datetime.utcnow()

    # Simulate tracking vote counts
    user_votes[user_id] = user_votes.get(user_id, 0) + 1
    vote_count = user_votes[user_id]
    streak = vote_count  # Placeholder for streaks

    # Build embed
    embed = discord.Embed(
        title=f"🗳️ {user.name} voted!",
        description=f"<@{user_id}> just voted for **{bot.user.mention}** 🎉",
        color=discord.Color.blue(),
        timestamp=now
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="User", value=f"{user.mention}", inline=True)
    embed.add_field(name="Bot", value=f"{bot.user.mention}", inline=True)
    embed.add_field(name="Vote Count", value=f"`{vote_count}`", inline=True)
    embed.add_field(name="Current Vote Streak", value=f"`{streak}`", inline=True)
    embed.add_field(name="Weekend?", value="✅" if is_weekend else "❌", inline=True)
    embed.set_footer(text=f"Thanks for choosing {bot.user.name}! • {now.strftime('%d-%m-%Y %H:%M')}")

    # Send to log channel
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)

    # Try DM
    try:
        await user.send(f"❤️ Thank you for voting for **{bot.user.name}** on Top.gg!")
    except:
        print(f"Couldn't DM {user_id}")

    return web.Response(status=200, text="Vote processed")

# Start aiohttp webhook server
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
    print(f"Logged in as {bot.user} ({bot.user.id})")
    await start_webhook()

bot.run(BOT_TOKEN)
