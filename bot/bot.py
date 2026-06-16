import os
import asyncio
import aiohttp
import discord

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
LEADERBOARD_URL = os.environ.get("LEADERBOARD_URL", "https://wc2026-leaderboard.onrender.com/post")
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY")  # Add this to your environment variables

API_FOOTBALL_HOST = "v3.football.api-sports.io"
API_FOOTBALL_BASE = f"https://{API_FOOTBALL_HOST}"

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


async def fetch_match_stats(team_name: str):
    """Search for a live or today's match involving the given team and return stats."""
    headers = {
        "x-apisports-key": API_FOOTBALL_KEY,
        "x-rapidapi-host": API_FOOTBALL_HOST,
    }

    async with aiohttp.ClientSession(headers=headers) as session:

        # Step 1: Search for live fixtures first
        async with session.get(f"{API_FOOTBALL_BASE}/fixtures", params={"live": "all"}) as resp:
            live_data = await resp.json()

        fixtures = live_data.get("response", [])

        # Filter by team name (case-insensitive)
        match = next(
            (f for f in fixtures if
             team_name.lower() in f["teams"]["home"]["name"].lower() or
             team_name.lower() in f["teams"]["away"]["name"].lower()),
            None
        )

        # Step 2: If no live match, look at today's fixtures
        if not match:
            from datetime import date
            today = date.today().isoformat()
            async with session.get(f"{API_FOOTBALL_BASE}/fixtures", params={"date": today}) as resp:
                today_data = await resp.json()

            fixtures = today_data.get("response", [])
            match = next(
                (f for f in fixtures if
                 team_name.lower() in f["teams"]["home"]["name"].lower() or
                 team_name.lower() in f["teams"]["away"]["name"].lower()),
                None
            )

        if not match:
            return None, "no_match"

        fixture_id = match["fixture"]["id"]
        home = match["teams"]["home"]
        away = match["teams"]["away"]
        score = match["score"]["fulltime"]
        halftime = match["score"]["halftime"]
        status = match["fixture"]["status"]["long"]
        elapsed = match["fixture"]["status"]["elapsed"]

        # Step 3: Fetch statistics for this fixture
        async with session.get(f"{API_FOOTBALL_BASE}/fixtures/statistics", params={"fixture": fixture_id}) as resp:
            stats_data = await resp.json()

        stats_response = stats_data.get("response", [])

        def get_stat(team_stats, stat_name):
            for s in team_stats.get("statistics", []):
                if s["type"] == stat_name:
                    return s["value"] if s["value"] is not None else 0
            return 0

        home_stats = next((s for s in stats_response if s["team"]["id"] == home["id"]), {"statistics": []})
        away_stats = next((s for s in stats_response if s["team"]["id"] == away["id"]), {"statistics": []})

        result = {
            "fixture_id": fixture_id,
            "status": status,
            "elapsed": elapsed,
            "home": {
                "name": home["name"],
                "logo": home["logo"],
                "goals": match["goals"]["home"] or 0,
                "possession": get_stat(home_stats, "Ball Possession"),
                "shots_total": get_stat(home_stats, "Total Shots"),
                "shots_on": get_stat(home_stats, "Shots on Goal"),
                "corners": get_stat(home_stats, "Corner Kicks"),
                "xg": get_stat(home_stats, "expected_goals"),
                "fouls": get_stat(home_stats, "Fouls"),
                "yellow_cards": get_stat(home_stats, "Yellow Cards"),
                "red_cards": get_stat(home_stats, "Red Cards"),
                "offsides": get_stat(home_stats, "Offsides"),
            },
            "away": {
                "name": away["name"],
                "logo": away["logo"],
                "goals": match["goals"]["away"] or 0,
                "possession": get_stat(away_stats, "Ball Possession"),
                "shots_total": get_stat(away_stats, "Total Shots"),
                "shots_on": get_stat(away_stats, "Shots on Goal"),
                "corners": get_stat(away_stats, "Corner Kicks"),
                "xg": get_stat(away_stats, "expected_goals"),
                "fouls": get_stat(away_stats, "Fouls"),
                "yellow_cards": get_stat(away_stats, "Yellow Cards"),
                "red_cards": get_stat(away_stats, "Red Cards"),
                "offsides": get_stat(away_stats, "Offsides"),
            },
        }

        return result, "ok"


def build_match_embed(data: dict) -> discord.Embed:
    home = data["home"]
    away = data["away"]
    status = data["status"]
    elapsed = data["elapsed"]

    title = f"{home['name']}  {home['goals']} – {away['goals']}  {away['name']}"
    description = f"🕐 {status}" + (f" ({elapsed}')" if elapsed else "")

    embed = discord.Embed(title=title, description=description, color=0x1a1a2e)

    def stat_row(label, home_val, away_val):
        return f"`{str(home_val):>6}` · **{label}** · `{str(away_val):<6}`"

    stats_lines = [
        stat_row("Possession", home["possession"], away["possession"]),
        stat_row("Total Shots", home["shots_total"], away["shots_total"]),
        stat_row("Shots on Target", home["shots_on"], away["shots_on"]),
        stat_row("Corner Kicks", home["corners"], away["corners"]),
        stat_row("Fouls", home["fouls"], away["fouls"]),
        stat_row("Offsides", home["offsides"], away["offsides"]),
        stat_row("Yellow Cards 🟨", home["yellow_cards"], away["yellow_cards"]),
        stat_row("Red Cards 🟥", home["red_cards"], away["red_cards"]),
    ]

    if home["xg"] or away["xg"]:
        stats_lines.insert(0, stat_row("xG", home["xg"], away["xg"]))

    embed.add_field(
        name=f"📊  {home['name']}  vs  {away['name']}",
        value="\n".join(stats_lines),
        inline=False
    )

    embed.set_footer(text="Data via API-Football")
    return embed


@client.event
async def on_message(message):
    if message.author.bot:
        return

    # --- Existing leaderboard command ---
    if message.content.strip().lower() == "-lead":
        msg = await message.channel.send("⏳ Fetching leaderboard...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(LEADERBOARD_URL, timeout=aiohttp.ClientTimeout(total=60)) as response:
                    data = await response.json()
                    if not data.get("ok"):
                        await msg.edit(content="❌ Failed to fetch leaderboard.")
                    else:
                        await msg.delete()
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")

    # --- New match stats command ---
    elif message.content.strip().lower().startswith("!match "):
        if not API_FOOTBALL_KEY:
            await message.channel.send("❌ API_FOOTBALL_KEY is not set in environment variables.")
            return

        team_name = message.content.strip()[7:].strip()  # everything after "!match "
        if not team_name:
            await message.channel.send("❌ Usage: `!match <team name>` — e.g. `!match France`")
            return

        msg = await message.channel.send(f"⏳ Searching for a match with **{team_name}**...")

        try:
            data, status = await fetch_match_stats(team_name)

            if status == "no_match":
                await msg.edit(content=f"❌ No live or scheduled match found today for **{team_name}**.")
                return

            embed = build_match_embed(data)
            await msg.delete()
            await message.channel.send(embed=embed)

        except Exception as e:
            await msg.edit(content=f"❌ Error fetching match data: {e}")


client.run(TOKEN)
