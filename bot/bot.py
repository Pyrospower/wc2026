import os
from datetime import date
import aiohttp
import discord

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
LEADERBOARD_BASE_URL = "https://wc2026-leaderboard.onrender.com"

# Football-Data.org Config
FOOTBALL_DATA_API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY")
FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"
COMP_CODE = "WC"  # Competition code for FIFA World Cup

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


def get_fd_headers():
    return {
        "X-Auth-Token": FOOTBALL_DATA_API_KEY
    }


# ──────────────────────────────────────────────
# SHARED: find fixture by team name (Football-Data)
# ──────────────────────────────────────────────
async def find_fixture(session, team_name: str):
    url = f"{FOOTBALL_DATA_BASE}/competitions/{COMP_CODE}/matches"
    async with session.get(url, headers=get_fd_headers()) as r:
        if r.status == 200:
            data = await r.json()
            matches = data.get("matches", []) or []
            
            # Search matches for matching team name
            for m in matches:
                home_name = m.get("homeTeam", {}).get("name", "").lower()
                away_name = m.get("awayTeam", {}).get("name", "").lower()
                
                if team_name.lower() in home_name or team_name.lower() in away_name:
                    # Give preference to live games, but return scheduled ones if none are active
                    return m
    return None


def format_match_line(m) -> str:
    home = m.get("homeTeam", {}).get("name", "TBD")
    away = m.get("awayTeam", {}).get("name", "TBD")
    
    score_data = m.get("score", {}).get("fullTime", {})
    home_score = score_data.get("home")
    away_score = score_data.get("away")
    status = m.get("status", "")

    if status in ["IN_PLAY", "PAUSED", "LIVE"]:
        return f"🔴 **{home} {home_score if home_score is not None else 0} - {away_score if away_score is not None else 0} {away}** (Live)"
    elif status == "FINISHED":
        return f"🏁 **{home} {home_score} - {away_score} {away}** (FT)"
    else:
        utc_date = m.get("utcDate", "")
        # Format the date cleanly if string exists
        date_display = utc_date.replace("T", " ").replace("Z", " UTC")[:16] if utc_date else "Scheduled"
        return f"⏳ **{home} vs {away}** (Scheduled: {date_display})"


async def fetch_bracket_data():
    url = f"https://wc2026.roen.us/api/bracket"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=10) as r:
            if r.status != 200:
                return None
            return await r.json()


def build_bracket_embeds(data, filter_round=None):
    stages = data.get("stages", [])
    embeds = []

    for stage in stages:
        stage_name = stage.get("stage_name", "Unknown Stage")
        if filter_round and filter_round.lower() not in stage_name.lower():
            continue

        embed = discord.Embed(
            title=f"🏆 Tournament Bracket — {stage_name}",
            color=3447003
        )
        groups = stage.get("groups", [])
        if not groups:
            embed.description = "*No matches scheduled yet.*"
            embeds.append(embed)
            continue

        for group in groups:
            group_name = group.get("group_name", "")
            matches = group.get("matches", [])
            match_lines = []

            for m in matches:
                m_id = m.get("match_id", "?")
                t1 = m.get("team1_name", "TBD")
                t2 = m.get("team2_name", "TBD")
                s1 = m.get("team1_score")
                s2 = m.get("team2_score")
                status = m.get("status", "")

                if s1 is not None and s2 is not None:
                    score_str = f"**{s1} - {s2}**"
                else:
                    score_str = "vs"

                status_suffix = f" ({status})" if status else ""
                match_lines.append(f"`#{m_id}` {t1} {score_str} {t2}{status_suffix}")

            field_title = group_name if group_name else "Matches"
            embed.add_field(name=field_title, value="\n".join(match_lines) if match_lines else "*No matches*", inline=False)

        embeds.append(embed)
    return embeds


async def fetch_replays(team_name: str):
    url = f"https://wc2026.roen.us/api/replays?team={team_name}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=10) as r:
            if r.status == 404:
                return None, "no_results"
            if r.status != 200:
                return None, "error"
            return await r.json(), "ok"


def build_replays_embed(team_name: str, replays: list):
    embed = discord.Embed(
        title=f"⚽ Goal Replays for {team_name.upper()}",
        color=15105570,
        description="Click the links below to watch individual highlights or check the embedded previews below."
    )
    for r in replays:
        title = r.get("title", "Goal Link")
        url = r.get("url", "")
        created = r.get("created_utc", "")
        time_str = f"<t:{int(created)}:R>" if created else ""
        embed.add_field(name=title, value=f"[Link]({url}) {time_str}", inline=False)
    return embed


@client.event
async def on_ready():
    print(f"Logged in as {client.user}", flush=True)


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    content = message.content.strip()
    low = content.lower()

    # ── Leaderboard Commands (-lead, -m1, -m2, -m3) ──
    if content in ("-lead", "-m1", "-m2", "-m3"):
        board_map = {
            "-lead": {"path": "/preview", "title": "GENERAL CLASSIFICATION"},
            "-m1": {"path": "/m1/preview", "title": "MATCHDAY 1"},
            "-m2": {"path": "/m2/preview", "title": "MATCHDAY 2"},
            "-m3": {"path": "/m3/preview", "title": "MATCHDAY 3"},
        }
        
        board = board_map[content]
        msg = await message.channel.send(f"⏳ Fetching **{board['title']}** details...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{LEADERBOARD_BASE_URL}{board['path']}", timeout=10) as response:
                    if response.status != 200:
                        await msg.edit(content=f"❌ Error talking to server (Status: {response.status})")
                        return
                    data = await response.json()

            if not data.get("ok"):
                await msg.edit(content=f"❌ Server error: {data.get('error')}")
                return

            players = data.get("players", [])
            if not players:
                await msg.edit(content="ℹ️ No player entries found for this category.")
                return

            lines = ["▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"]
            for rank, player in enumerate(players, start=1):
                rank_str = f"{rank:02d}"
                name = player["name"]
                score = player["score"]
                line = f"\u001b[1;34m{rank_str}.\u001b[0m \u001b[0m{name:<15} \u001b[1;33m{score}\u001b[0m"
                lines.append(line)
            lines.append("▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬")
            
            code_block = "```ansi\n" + "\n".join(lines) + "\n```"
            description = f"🏆 **{board['title']}** 🏆\n" + code_block

            embed = discord.Embed(
                title="WORLD CUP 2026",
                color=16763904,
                description=description
            )
            
            await msg.delete()
            await message.channel.send(embed=embed)

        except Exception as e:
            await msg.edit(content=f"❌ Network or processing error: {e}")

    # ── Live Schedule/Results Command (-live <team>) ──
    elif low.startswith("-live "):
        team_name = content[6:].strip()
        if not team_name:
            await message.channel.send("❌ Usage: `-live <team>` — e.g. `-live France`")
            return

        if not FOOTBALL_DATA_API_KEY:
            await message.channel.send("❌ API configuration missing. `FOOTBALL_DATA_API_KEY` is not set.")
            return

        msg = await message.channel.send(f"⏳ Searching Football-Data for fixture with **{team_name}**...")
        try:
            async with aiohttp.ClientSession() as session:
                match = await find_fixture(session, team_name)

            if not match:
                await msg.edit(content=f"❌ No matching World Cup fixtures found for **{team_name}**.")
                return

            await msg.delete()
            await message.channel.send(format_match_line(match))
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")

    # ── Standings Command (-standings) ──
    elif content == "-standings":
        if not FOOTBALL_DATA_API_KEY:
            await message.channel.send("❌ API configuration missing. `FOOTBALL_DATA_API_KEY` is not set.")
            return

        msg = await message.channel.send("⏳ Fetching tournament standings...")
        try:
            url = f"{FOOTBALL_DATA_BASE}/competitions/{COMP_CODE}/standings"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=get_fd_headers()) as r:
                    if r.status != 200:
                        await msg.edit(content=f"❌ Error fetching standings tables (Status: {r.status})")
                        return
                    data = await r.json()
            
            standings_list = data.get("standings", [])
            if not standings_list:
                await msg.edit(content="ℹ️ No standings tables available yet.")
                return
            
            await msg.delete()
            # Send the first few group tables cleanly to stay under Discord limits
            for group_table in standings_list[:4]:
                group_name = group_table.get("group", "Group Stage").replace("_", " ")
                embed = discord.Embed(title=f"📊 {group_name}", color=discord.Color.green())
                
                table_text = ""
                for pos in group_table.get("table", []):
                    t_name = pos["team"]["name"]
                    rank = pos["position"]
                    pts = pos["points"]
                    played = pos["playedGames"]
                    gd = pos["goalDifference"]
                    table_text += f"`{rank}.` **{t_name}** | P: {played} | GD: {gd} | **Pts: {pts}**\n"
                
                embed.description = table_text
                await message.channel.send(embed=embed)
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")

    # ── Bracket Command (-bracket) ──
    elif content == "-bracket":
        msg = await message.channel.send("⏳ Fetching tournament bracket data...")
        try:
            data = await fetch_bracket_data()
            if not data:
                await msg.edit(content="❌ Bracket data not available yet (group stage may still be ongoing).")
                return
            embeds = build_bracket_embeds(data)
            if not embeds:
                await msg.edit(content="❌ No matches scheduled in any stage yet.")
                return
            await msg.delete()
            for i in range(0, len(embeds), 10):
                await message.channel.send(embeds=embeds[i:i+10])
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")

    # ── Bracket Round Command (-bracket <round>) ──
    elif low.startswith("-bracket "):
        round_filter = content[9:].strip()
        if not round_filter:
            await message.channel.send("❌ Usage: `-bracket <round>` — e.g. `-bracket Round of 32`")
            return
        msg = await message.channel.send(f"⏳ Fetching bracket data for round **{round_filter}**...")
        try:
            data = await fetch_bracket_data()
            if not data:
                await msg.edit(content="❌ Bracket data not available yet (group stage may still be ongoing).")
                return
            embeds = build_bracket_embeds(data, round_filter)
            if not embeds:
                await msg.edit(content=f"❌ No matches found for **{round_filter}** yet.")
                return
            await msg.delete()
            for i in range(0, len(embeds), 10):
                await message.channel.send(embeds=embeds[i:i+10])
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")

    # ── Replays Command (-replays <team>) ──
    elif low.startswith("-replays "):
        team_name = content[9:].strip()
        if not team_name:
            await message.channel.send("❌ Usage: `-replays <team>` — e.g. `-replays France`")
            return
        msg = await message.channel.send(f"⏳ Searching r/soccer for **{team_name}** replays...")
        try:
            replays, status = await fetch_replays(team_name)
            if status == "no_results":
                await msg.edit(content=f"❌ No goal replays found on r/soccer for **{team_name}**.")
                return
            embed = build_replays_embed(team_name, replays)
            await msg.delete()
            await message.channel.send(embed=embed)
            links = "\n".join(r["url"] for r in replays)
            await message.channel.send(links)
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")


if TOKEN:
    client.run(TOKEN)
else:
    print("Error: DISCORD_BOT_TOKEN environment variable not set.")