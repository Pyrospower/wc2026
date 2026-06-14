import os
import discord
import requests

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
LEADERBOARD_URL = os.environ.get("LEADERBOARD_URL", "https://wc2026-leaderboard.onrender.com/post")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


@client.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.strip().lower() == "-lead":
        try:
            response = requests.get(LEADERBOARD_URL, timeout=15)
            data = response.json()
            if not data.get("ok"):
                await message.channel.send("❌ Failed to fetch leaderboard.")
        except Exception as e:
            await message.channel.send(f"❌ Error: {e}")


client.run(TOKEN)
