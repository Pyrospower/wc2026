import os
import time
import aiohttp
import discord

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
LEADERBOARD_BASE_URL = "https://wc2026-leaderboard.onrender.com"
HIGHLIGHTLY_API_KEY = os.environ.get("HIGHLIGHTLY_API_KEY")
HIGHLIGHTLY_BASE = "https://football-api.highlightly.net"

# World Cup league ID on Highlightly
WC_LEAGUE_ID = 28

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# ── Simple in-memory cache to avoid hammering the API ──
_cache = {}
CACHE_TTL = 30  # seconds — live data refreshes every 30s

def get_cache(key):
    entry = _cache.get(key)
    if entry and time.time() - entry["ts"] < CACHE_TTL:
        return entry["data"]
    return None

def set_cache(key, data):
    _cache[key] = {"data": data, "ts": time.time()}

def hl_headers():
    return {
        "x-api-key": HIGHLIGHTLY_API_KEY,
        "Accept": "application/json",
    }

async def hl_get(session, path, params=None):
    """Fetch from Highlightly with caching."""
    cache_key = path + str(sorted((params or {}).items()))
    cached = get_cache(cache_key)
    if cached is not None:
        return cached
    url = f"{HIGHLIGHTLY_BASE}{path}"
    async with session.get(url, headers=hl_headers(), params=params, timeout=10) as r:
        if r.status == 200:
            data = await r.json()
            set_cache(cache_key, data)
            return data
        return None

def format_events(events):
    """Format goal/card events into readable lines."""
    lines = []
    for e in events:
        etype = e.get("type", "").upper()
        minute = e.get("minute", "?")
        player = e.get("player", {}).get("name", "Unknown")
        team = e.get("team", {}).get("name", "")
        if etype == "GOAL":
            lines.append(f"⚽ `{minute}'` **{player}** ({team})")
        elif etype == "OWN_GOAL":
            lines.append(f"🙈 `{minute}'` **{player}** OG ({team})")
        elif etype == "PENALTY_GOAL":
            lines.append(f"🎯 `{minute}'` **{player}** (pen) ({team})")
        elif etype == "YELLOW_CARD":
            lines.append(f"🟨 `{minute}'` {player} ({team})")
        elif etype == "RED_CARD":
            lines.append(f"🟥 `{minute}'` {player} ({team})")
    return lines

def format_match_embed(m, title=None):
    home = m.get("homeTeam", {}).get("name", "TBD")
    away = m.get("awayTeam", {}).get("name", "TBD")
    status = m.get("status", {})
    status_short = status.get("short", "NS")
    elapsed = status.get("elapsed")
    home_score = m.get("homeScore")
    away_score = m.get("awayScore")

    # Score line
    if home_score is not None and away_score is not None:
        score = f"{home_score} - {away_score}"
    else:
        score = "vs"

    # Status indicator
    if status_short in ("1H", "2H", "ET", "BT", "P", "LIVE"):
        status_str = f"🔴 LIVE {elapsed}'" if elapsed else "🔴 LIVE"
        color = 0xff0000
    elif status_short == "HT":
        status_str = "⏸️ Half Time"
        color = 0xffa500
    elif status_short == "FT":
        status_str = "🏁 Full Time"
        color = 0x00aa00
    elif status_short == "NS":
        kickoff = m.get("date", "")
        status_str = f"⏳ {kickoff[:16] if kickoff else 'Scheduled'}"
        color = 0x888888
    else:
        status_str = status_short
        color = 0x888888

    embed = discord.Embed(
        title=title or f"{home} vs {away}",
        description=f"## {home}  {score}  {away}\n{status_str}",
        color=color
    )

    # Events
    events = m.get("events", [])
    if events:
        event_lines = format_events(events)
        if event_lines:
            embed.add_field(name="📋 Events", value="\n".join(event_lines[:20]), inline=False)

    group = m.get("round", {}).get("name", "")
    if group:
        embed.set_footer(text=group)

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

    # ── Leaderboard Commands ──
    if content in ("-lead", "-m1", "-m2", "-m3"):
        board_map = {
            "-lead": {"path": "/preview", "title": "GENERAL CLASSIFICATION"},
            "-m1": {"path": "/m1/preview", "title": "MATCHDAY 1"},
            "-m2": {"path": "/m2/preview", "title": "MATCHDAY 2"},
            "-m3": {"path": "/m3/preview", "title": "MATCHDAY 3"},
        }
        board = board_map[content]
        msg = await message.channel.send(f"⏳ Fetching **{board['title']}**...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{LEADERBOARD_BASE_URL}{board['path']}", timeout=10) as response:
                    if response.status != 200:
                        await msg.edit(content=f"❌ Server error (Status: {response.status})")
                        return
                    data = await response.json()
            if not data.get("ok"):
                await msg.edit(content=f"❌ {data.get('error')}")
                return
            players = data.get("players", [])
            if not players:
                await msg.edit(content="ℹ️ No entries found.")
                return
            lines = ["▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"]
            for rank, player in enumerate(players, start=1):
                line = f"\u001b[1;34m{rank:02d}.\u001b[0m \u001b[0m{player['name']:<15} \u001b[1;33m{player['score']}\u001b[0m"
                lines.append(line)
            lines.append("▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬")
            code_block = "```ansi\n" + "\n".join(lines) + "\n```"
            embed = discord.Embed(title="WORLD CUP 2026", color=16763904,
                                  description=f"🏆 **{board['title']}** 🏆\n{code_block}")
            await msg.delete()
            await message.channel.send(embed=embed)
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")

    # ── Today's WC Matches ──
    elif content == "-today":
        if not HIGHLIGHTLY_API_KEY:
            await message.channel.send("❌ `HIGHLIGHTLY_API_KEY` not set.")
            return
        msg = await message.channel.send("⏳ Fetching today's World Cup matches...")
        try:
            from datetime import date
            today = date.today().isoformat()
            async with aiohttp.ClientSession() as session:
                data = await hl_get(session, "/matches", {"date": today, "leagueId": WC_LEAGUE_ID})
            if not data or not data.get("data"):
                await msg.edit(content="ℹ️ No World Cup matches today.")
                return
            matches = data["data"]
            embed = discord.Embed(title=f"⚽ World Cup 2026 — {today}", color=0x1a3a2a)
            for m in matches:
                home = m.get("homeTeam", {}).get("name", "TBD")
                away = m.get("awayTeam", {}).get("name", "TBD")
                hs = m.get("homeScore")
                aws = m.get("awayScore")
                status_short = m.get("status", {}).get("short", "NS")
                elapsed = m.get("status", {}).get("elapsed")
                if hs is not None and aws is not None:
                    score = f"{hs}–{aws}"
                else:
                    score = "vs"
                if status_short in ("1H","2H","ET","LIVE"):
                    indicator = f"🔴 {elapsed}'" if elapsed else "🔴"
                elif status_short == "HT":
                    indicator = "⏸️ HT"
                elif status_short == "FT":
                    indicator = "🏁 FT"
                else:
                    kickoff = m.get("date", "")
                    indicator = f"⏳ {kickoff[11:16] if len(kickoff) > 11 else ''} UTC"
                embed.add_field(
                    name=f"{home} {score} {away}",
                    value=indicator,
                    inline=False
                )
            await msg.delete()
            await message.channel.send(embed=embed)
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")

    # ── Live Matches ──
    elif content == "-live":
        if not HIGHLIGHTLY_API_KEY:
            await message.channel.send("❌ `HIGHLIGHTLY_API_KEY` not set.")
            return
        msg = await message.channel.send("⏳ Fetching live World Cup matches...")
        try:
            async with aiohttp.ClientSession() as session:
                data = await hl_get(session, "/matches/live", {"leagueId": WC_LEAGUE_ID})
            if not data or not data.get("data"):
                await msg.edit(content="ℹ️ No live World Cup matches right now.")
                return
            matches = data["data"]
            await msg.delete()
            for m in matches:
                embed = format_match_embed(m)
                await message.channel.send(embed=embed)
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")

    # ── Match by team ──
    elif low.startswith("-match "):
        team_name = content[7:].strip()
        if not team_name:
            await message.channel.send("❌ Usage: `-match <team>` — e.g. `-match France`")
            return
        if not HIGHLIGHTLY_API_KEY:
            await message.channel.send("❌ `HIGHLIGHTLY_API_KEY` not set.")
            return
        msg = await message.channel.send(f"⏳ Searching for **{team_name}**'s match...")
        try:
            from datetime import date
            today = date.today().isoformat()
            async with aiohttp.ClientSession() as session:
                data = await hl_get(session, "/matches", {"date": today, "leagueId": WC_LEAGUE_ID})
            if not data or not data.get("data"):
                await msg.edit(content="ℹ️ No matches found today.")
                return
            matches = data["data"]
            found = None
            for m in matches:
                home = m.get("homeTeam", {}).get("name", "").lower()
                away = m.get("awayTeam", {}).get("name", "").lower()
                if team_name.lower() in home or team_name.lower() in away:
                    found = m
                    break
            if not found:
                await msg.edit(content=f"❌ No match found for **{team_name}** today.")
                return
            # Fetch full match details with events
            match_id = found.get("id")
            async with aiohttp.ClientSession() as session:
                detail = await hl_get(session, f"/matches/{match_id}", {})
            if detail and detail.get("data"):
                found = detail["data"]
            embed = format_match_embed(found)
            await msg.delete()
            await message.channel.send(embed=embed)
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")

    # ── Lineup by team ──
    elif low.startswith("-lineup "):
        team_name = content[8:].strip()
        if not team_name:
            await message.channel.send("❌ Usage: `-lineup <team>` — e.g. `-lineup Brazil`")
            return
        if not HIGHLIGHTLY_API_KEY:
            await message.channel.send("❌ `HIGHLIGHTLY_API_KEY` not set.")
            return
        msg = await message.channel.send(f"⏳ Fetching lineup for **{team_name}**...")
        try:
            from datetime import date
            today = date.today().isoformat()
            async with aiohttp.ClientSession() as session:
                data = await hl_get(session, "/matches", {"date": today, "leagueId": WC_LEAGUE_ID})
            if not data or not data.get("data"):
                await msg.edit(content="ℹ️ No matches found today.")
                return
            found = None
            for m in data["data"]:
                home = m.get("homeTeam", {}).get("name", "").lower()
                away = m.get("awayTeam", {}).get("name", "").lower()
                if team_name.lower() in home or team_name.lower() in away:
                    found = m
                    break
            if not found:
                await msg.edit(content=f"❌ No match found for **{team_name}** today.")
                return
            match_id = found.get("id")
            async with aiohttp.ClientSession() as session:
                lineup_data = await hl_get(session, f"/matches/{match_id}/lineups", {})
            if not lineup_data or not lineup_data.get("data"):
                await msg.edit(content=f"⏳ Lineups not available yet for **{team_name}** (available ~30min before kickoff).")
                return
            lineups = lineup_data["data"]
            home_name = found.get("homeTeam", {}).get("name", "Home")
            away_name = found.get("awayTeam", {}).get("name", "Away")
            embed = discord.Embed(
                title=f"📋 Lineups — {home_name} vs {away_name}",
                color=0x1a3a2a
            )
            for side, label in [("home", home_name), ("away", away_name)]:
                team_lineup = lineups.get(side, {})
                formation = team_lineup.get("formation", "")
                players = team_lineup.get("startingXI", [])
                starters = [f"`{p.get('number','?')}` {p.get('name','?')}" for p in players]
                bench = team_lineup.get("substitutes", [])
                bench_list = [f"`{p.get('number','?')}` {p.get('name','?')}" for p in bench]
                value = f"**Formation: {formation}**\n" + "\n".join(starters)
                if bench_list:
                    value += f"\n\n**Bench:** {', '.join(p.get('name','?') for p in bench)}"
                embed.add_field(name=label, value=value or "N/A", inline=True)
            await msg.delete()
            await message.channel.send(embed=embed)
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")

    # ── Standings ──
    elif content == "-standings":
        if not HIGHLIGHTLY_API_KEY:
            await message.channel.send("❌ `HIGHLIGHTLY_API_KEY` not set.")
            return
        msg = await message.channel.send("⏳ Fetching World Cup standings...")
        try:
            async with aiohttp.ClientSession() as session:
                data = await hl_get(session, "/standings", {"leagueId": WC_LEAGUE_ID, "season": 2026})
            if not data or not data.get("data"):
                await msg.edit(content="ℹ️ Standings not available yet.")
                return
            groups = data["data"]
            await msg.delete()
            for group in groups[:6]:  # send first 6 groups to avoid spam
                group_name = group.get("name", "Group")
                embed = discord.Embed(title=f"📊 {group_name}", color=0x1a3a2a)
                rows = group.get("standings", [])
                lines = []
                for row in rows:
                    pos = row.get("position", "?")
                    team = row.get("team", {}).get("name", "?")
                    pts = row.get("points", 0)
                    played = row.get("played", 0)
                    gd = row.get("goalDifference", 0)
                    lines.append(f"`{pos}.` **{team}** | P:{played} GD:{gd:+d} Pts:**{pts}**")
                embed.description = "\n".join(lines) if lines else "No data"
                await message.channel.send(embed=embed)
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")

    # ── Bracket ──
    elif low.startswith("-bracket") :
        ROUND_MAP = {
            "r32":   "Round of 32",
            "r16":   "Round of 16",
            "qf":    "Quarter-finals",
            "sf":    "Semi-finals",
            "final": "Final",
            "3rd":   "3rd Place Final",
        }
        ROUND_COLORS = {
            "r32":   0x4a90d9,
            "r16":   0x7b68ee,
            "qf":    0xe8b84b,
            "sf":    0xff7043,
            "final": 0xffd700,
            "3rd":   0xcd7f32,
        }

        arg = content[8:].strip().lower() if len(content) > 8 else ""

        if not arg:
            # Show all available rounds as a menu
            embed = discord.Embed(
                title="🏆 World Cup 2026 Bracket",
                description="Use `-bracket <round>` to see matches for a specific round:",
                color=0x1a3a2a
            )
            for key, label in ROUND_MAP.items():
                embed.add_field(name=f"`-bracket {key}`", value=label, inline=True)
            await message.channel.send(embed=embed)
            return

        if arg not in ROUND_MAP:
            await message.channel.send(
                f"❌ Unknown round `{arg}`. Use: `r32` `r16` `qf` `sf` `final` `3rd`"
            )
            return

        if not HIGHLIGHTLY_API_KEY:
            await message.channel.send("❌ `HIGHLIGHTLY_API_KEY` not set.")
            return

        round_label = ROUND_MAP[arg]
        msg = await message.channel.send(f"⏳ Fetching **{round_label}** matches...")
        try:
            async with aiohttp.ClientSession() as session:
                data = await hl_get(session, "/matches", {
                    "leagueId": WC_LEAGUE_ID,
                    "round": round_label,
                    "season": 2026,
                    "limit": 20,
                })
            if not data or not data.get("data"):
                await msg.edit(content=f"ℹ️ No matches found for **{round_label}** yet — check back when the knockout stage begins!")
                return

            matches = data["data"]
            embed = discord.Embed(
                title=f"🏆 {round_label}",
                color=ROUND_COLORS.get(arg, 0x1a3a2a)
            )

            for m in matches:
                home = m.get("homeTeam", {}).get("name", "TBD")
                away = m.get("awayTeam", {}).get("name", "TBD")
                hs = m.get("homeScore")
                aws = m.get("awayScore")
                status_short = m.get("status", {}).get("short", "NS")
                elapsed = m.get("status", {}).get("elapsed")

                if hs is not None and aws is not None:
                    score = f"{hs} — {aws}"
                else:
                    score = "vs"

                if status_short in ("1H", "2H", "ET", "LIVE"):
                    indicator = f"🔴 {elapsed}'" if elapsed else "🔴 LIVE"
                elif status_short == "HT":
                    indicator = "⏸️ Half Time"
                elif status_short == "FT":
                    indicator = "🏁 FT"
                else:
                    kickoff = m.get("date", "")
                    indicator = f"⏳ {kickoff[:10] if kickoff else 'TBD'}"

                embed.add_field(
                    name=f"{home}  {score}  {away}",
                    value=indicator,
                    inline=False
                )

            await msg.delete()
            await message.channel.send(embed=embed)
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")

    # ── Help ──
    elif content == "-help":
        embed = discord.Embed(title="⚽ WC2026 Bot Commands", color=0x1a3a2a)
        embed.add_field(name="Leaderboard", value="`-lead` `-m1` `-m2` `-m3`", inline=False)
        embed.add_field(name="-today", value="Today's World Cup matches", inline=False)
        embed.add_field(name="-live", value="Currently live matches with goal scorers", inline=False)
        embed.add_field(name="-match <team>", value="Match details & events — e.g. `-match France`", inline=False)
        embed.add_field(name="-lineup <team>", value="Starting lineup — e.g. `-lineup Brazil`", inline=False)
        embed.add_field(name="-standings", value="Group stage standings", inline=False)
        embed.add_field(name="-bracket", value="Knockout bracket menu", inline=False)
        embed.add_field(name="-bracket <round>", value="`r32` `r16` `qf` `sf` `final` `3rd`", inline=False)
        await message.channel.send(embed=embed)


if TOKEN:
    client.run(TOKEN)
else:
    print("Error: DISCORD_BOT_TOKEN not set.")