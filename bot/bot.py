import os
import time
import aiohttp
import discord

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
LEADERBOARD_BASE_URL = "https://wc2026-leaderboard.onrender.com"
HIGHLIGHTLY_API_KEY = os.environ.get("HIGHLIGHTLY_API_KEY")
HIGHLIGHTLY_BASE = "https://soccer.highlightly.net"

# World Cup league ID on Highlightly
WC_LEAGUE_ID = 1635

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
        "x-rapidapi-key": HIGHLIGHTLY_API_KEY,
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
            raw = await r.json()
            # Normalise: always return {"data": [...]} shape
            if isinstance(raw, list):
                data = {"data": raw}
            elif isinstance(raw, dict) and "data" not in raw:
                # e.g. {"groups": [...], "league": {...}}
                data = {"data": raw.get("groups") or raw.get("matches") or [], "_raw": raw}
            else:
                data = raw
            set_cache(cache_key, data)
            return data
        return None

TEAM_FLAGS = {
    "mexico": "🇲🇽", "canada": "🇨🇦", "united states": "🇺🇸", "usa": "🇺🇸",
    "argentina": "🇦🇷", "brazil": "🇧🇷", "uruguay": "🇺🇾", "colombia": "🇨🇴",
    "ecuador": "🇪🇨", "chile": "🇨🇱", "paraguay": "🇵🇾", "peru": "🇵🇪", "bolivia": "🇧🇴", "venezuela": "🇻🇪",
    "france": "🇫🇷", "germany": "🇩🇪", "spain": "🇪🇸", "england": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "portugal": "🇵🇹",
    "netherlands": "🇳🇱", "belgium": "🇧🇪", "italy": "🇮🇹", "croatia": "🇭🇷", "switzerland": "🇨🇭",
    "denmark": "🇩🇰", "austria": "🇦🇹", "poland": "🇵🇱", "ukraine": "🇺🇦", "serbia": "🇷🇸",
    "scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿", "norway": "🇳🇴", "sweden": "🇸🇪", "czech republic": "🇨🇿", "czechia": "🇨🇿",
    "slovakia": "🇸🇰", "slovenia": "🇸🇮", "romania": "🇷🇴", "turkey": "🇹🇷", "greece": "🇬🇷",
    "hungary": "🇭🇺", "finland": "🇫🇮", "ireland": "🇮🇪", "northern ireland": "🇬🇧", "iceland": "🇮🇸",
    "japan": "🇯🇵", "south korea": "🇰🇷", "korea republic": "🇰🇷", "australia": "🇦🇺", "iran": "🇮🇷",
    "saudi arabia": "🇸🇦", "qatar": "🇶🇦", "uzbekistan": "🇺🇿", "jordan": "🇯🇴", "china": "🇨🇳",
    "iraq": "🇮🇶", "indonesia": "🇮🇩", "north korea": "🇰🇵", "bahrain": "🇧🇭", "kuwait": "🇰🇼",
    "morocco": "🇲🇦", "senegal": "🇸🇳", "tunisia": "🇹🇳", "egypt": "🇪🇬", "algeria": "🇩🇿",
    "nigeria": "🇳🇬", "ghana": "🇬🇭", "cameroon": "🇨🇲", "ivory coast": "🇨🇮", "cote d'ivoire": "🇨🇮",
    "south africa": "🇿🇦", "cape verde": "🇨🇻", "dr congo": "🇨🇩", "mali": "🇲🇱", "gabon": "🇬🇦",
    "jamaica": "🇯🇲", "panama": "🇵🇦", "costa rica": "🇨🇷", "honduras": "🇭🇳", "curacao": "🇨🇼",
    "haiti": "🇭🇹", "new zealand": "🇳🇿", "new caledonia": "🇳🇨",
}

def team_flag(name):
    return TEAM_FLAGS.get((name or "").strip().lower(), "")

def safe_name(val, default=""):
    """Extract a name whether val is a dict like {'name': 'France'} or already a string."""
    if isinstance(val, dict):
        return val.get("name", default)
    if isinstance(val, str):
        return val
    return default

def format_events(events):
    """Format goal/card events into readable lines."""
    lines = []
    for e in events:
        etype = e.get("type", "")
        minute = e.get("time", "?")
        player = e.get("player", "Unknown")
        team = safe_name(e.get("team", {}))
        flag = team_flag(team)
        team_disp = f"{flag} {team}".strip() if flag else team
        assist = e.get("assist")
        if etype == "Goal":
            extra = f" (assist: {assist})" if assist else ""
            lines.append(f"⚽ `{minute}'` **{player}**{extra} ({team_disp})")
        elif etype == "Own Goal":
            lines.append(f"🙈 `{minute}'` **{player}** OG ({team_disp})")
        elif etype == "Missed Penalty":
            lines.append(f"❌ `{minute}'` **{player}** missed pen ({team_disp})")
        elif etype == "Yellow Card":
            lines.append(f"🟨 `{minute}'` {player} ({team_disp})")
        elif etype == "Red Card":
            lines.append(f"🟥 `{minute}'` {player} ({team_disp})")
        elif etype == "Substitution":
            sub_out = e.get("substituted")
            extra = f" ↔️ {sub_out}" if sub_out else ""
            lines.append(f"🔄 `{minute}'` **{player}**{extra} ({team_disp})")
    return lines

def get_match_phase(description):
    """Collapse Highlightly's state.description into live/ended/scheduled/other."""
    live_states = {"First Half", "Second Half", "Half Time", "Extra Time",
                   "Extra Time Half Time", "Penalty Shootout", "Break Time"}
    ended_states = {"Finished", "Finished AET", "Finished AP",
                     "Finished After Extra Time", "Finished After Penalties"}
    if not description:
        return "scheduled"
    if description in live_states:
        return "live"
    if description in ended_states:
        return "ended"
    if description == "Not Started":
        return "scheduled"
    return "other"

def format_match_embed(m, title=None):
    home = safe_name(m.get("homeTeam", {}), "TBD")
    away = safe_name(m.get("awayTeam", {}), "TBD")
    home_flag = team_flag(home)
    away_flag = team_flag(away)
    home_disp = f"{home_flag} {home}".strip()
    away_disp = f"{away_flag} {away}".strip()
    state = m.get("state", {}) or {}
    description = state.get("description", "")
    clock = state.get("clock")
    score_obj = state.get("score") or {}
    score_current = score_obj.get("current")
    penalties = score_obj.get("penalties")

    # Score line
    score = score_current if score_current else "vs"

    phase = get_match_phase(description)
    if phase == "live":
        status_str = f"🔴 LIVE {clock}'" if clock else f"🔴 LIVE ({description})"
        color = 0xff0000
    elif phase == "ended":
        status_str = "🏁 Full Time" if description == "Finished" else f"🏁 {description}"
        color = 0x00aa00
    elif phase == "scheduled":
        kickoff = m.get("date", "")
        status_str = f"⏳ {kickoff[:16] if kickoff else 'Scheduled'}"
        color = 0x888888
    else:
        status_str = description or "Unknown"
        color = 0x888888

    if penalties:
        score = f"{score} (Pens: {penalties})"

    embed = discord.Embed(
        title=title or f"{home} vs {away}",
        description=f"## {home_disp}  {score}  {away_disp}\n{status_str}",
        color=color
    )

    # Events
    events = m.get("events", [])
    if events:
        event_lines = format_events(events)
        if event_lines:
            embed.add_field(name="📋 Events", value="\n".join(event_lines[:20]), inline=False)

    group = m.get("round", "")
    if isinstance(group, dict):
        group = safe_name(group)
    if group:
        embed.set_footer(text=str(group))

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
    elif low.startswith("-tm"):
        if not HIGHLIGHTLY_API_KEY:
            await message.channel.send("❌ `HIGHLIGHTLY_API_KEY` not set.")
            return
        arg = content[3:].strip().lower()
        from datetime import date, timedelta
        if arg == "yesterday" or arg == "yday":
            search_date = (date.today() - timedelta(days=1)).isoformat()
            label = "Yesterday"
        elif arg == "tomorrow" or arg == "tmrw":
            search_date = (date.today() + timedelta(days=1)).isoformat()
            label = "Tomorrow"
        else:
            search_date = date.today().isoformat()
            label = "Today"
        today = search_date
        msg = await message.channel.send(f"⏳ Fetching {label}'s World Cup matches...")
        try:
            from datetime import date
            async with aiohttp.ClientSession() as session:
                data = await hl_get(session, "/matches", {"date": today, "leagueId": WC_LEAGUE_ID})
            if not data:
                await msg.edit(content="ℹ️ No World Cup matches today.")
                return
            matches = data.get("data") if isinstance(data, dict) else data
            if not matches:
                await msg.edit(content="ℹ️ No World Cup matches today.")
                return
            embed = discord.Embed(title=f"⚽ World Cup 2026 — {today}", color=0x1a3a2a)
            for m in matches:
                home = safe_name(m.get("homeTeam", {}), "TBD")
                away = safe_name(m.get("awayTeam", {}), "TBD")
                home_disp = f"{team_flag(home)} {home}".strip()
                away_disp = f"{team_flag(away)} {away}".strip()
                state = m.get("state", {}) or {}
                description = state.get("description", "")
                clock = state.get("clock")
                score_current = (state.get("score") or {}).get("current")
                score = score_current if score_current else "vs"
                phase = get_match_phase(description)
                if phase == "live":
                    indicator = f"🔴 {clock}'" if clock else "🔴 LIVE"
                elif phase == "ended":
                    indicator = "🏁 FT"
                elif phase == "scheduled":
                    kickoff = m.get("date", "")
                    indicator = f"⏳ {kickoff[11:16] if len(kickoff) > 11 else ''} UTC"
                else:
                    indicator = description or "?"
                embed.add_field(
                    name=f"{home_disp} {score} {away_disp}",
                    value=indicator,
                    inline=False
                )
            await msg.delete()
            await message.channel.send(embed=embed)
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")

    # ── Live Matches ──
    elif low.startswith("-live"):
        team_filter = content[5:].strip().lower() if len(content) > 5 else ""
        if not HIGHLIGHTLY_API_KEY:
            await message.channel.send("❌ `HIGHLIGHTLY_API_KEY` not set.")
            return
        label = f"**{team_filter.title()}**" if team_filter else "all"
        msg = await message.channel.send(f"⏳ Fetching live World Cup matches ({label})...")
        try:
            async with aiohttp.ClientSession() as session:
                data = await hl_get(session, "/matches/live", {"leagueId": WC_LEAGUE_ID})
            if not data:
                await msg.edit(content="ℹ️ No live World Cup matches right now.")
                return
            matches = data.get("data") if isinstance(data, dict) else data
            if not matches:
                await msg.edit(content="ℹ️ No live World Cup matches right now.")
                return
            if team_filter:
                matches = [
                    m for m in matches
                    if team_filter in safe_name(m.get("homeTeam", {})).lower()
                    or team_filter in safe_name(m.get("awayTeam", {})).lower()
                ]
                if not matches:
                    await msg.edit(content=f"ℹ️ **{team_filter.title()}** is not playing live right now.")
                    return
            await msg.delete()
            async with aiohttp.ClientSession() as session:
                for m in matches:
                    match_id = m.get("id")
                    detail = await hl_get(session, f"/matches/{match_id}", {})
                    if isinstance(detail, dict):
                        detail_obj = detail.get("_raw") or detail.get("data")
                        if isinstance(detail_obj, list) and detail_obj:
                            m = detail_obj[0]
                        elif isinstance(detail_obj, dict):
                            m = detail_obj
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
            from datetime import date, timedelta
            # Search yesterday, today, and tomorrow to handle timezone differences
            dates = [
                (date.today() - timedelta(days=1)).isoformat(),
                date.today().isoformat(),
                (date.today() + timedelta(days=1)).isoformat(),
            ]
            found = None
            # Clear cache to avoid stale data
            _cache.clear()
            async with aiohttp.ClientSession() as session:
                for search_date in dates:
                    data = await hl_get(session, "/matches", {"date": search_date, "leagueId": WC_LEAGUE_ID})
                    if not data:
                        continue
                    matches_list = data.get("data") if isinstance(data, dict) else data
                    if not matches_list:
                        continue
                    for m in matches_list:
                        if not isinstance(m, dict):
                            continue
                        home = safe_name(m.get("homeTeam", {})).lower()
                        away = safe_name(m.get("awayTeam", {})).lower()
                        if team_name.lower() in home or team_name.lower() in away:
                            found = m
                            break
                    if found:
                        break
            if not found:
                await msg.edit(content=f"❌ No recent match found for **{team_name}**.")
                return
            # Fetch full match details with events
            match_id = found.get("id")
            async with aiohttp.ClientSession() as session:
                detail = await hl_get(session, f"/matches/{match_id}", {})
            if isinstance(detail, dict):
                # hl_get's generic normalisation only recognises "groups"/"matches" keys;
                # a single match-detail object has neither, so it's preserved under "_raw".
                detail_obj = detail.get("_raw") or detail.get("data")
                if isinstance(detail_obj, list) and detail_obj:
                    found = detail_obj[0]
                elif isinstance(detail_obj, dict):
                    found = detail_obj
            elif isinstance(detail, list) and detail:
                found = detail[0]
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
                home = safe_name(m.get("homeTeam", {})).lower()
                away = safe_name(m.get("awayTeam", {})).lower()
                if team_name.lower() in home or team_name.lower() in away:
                    found = m
                    break
            if not found:
                await msg.edit(content=f"❌ No match found for **{team_name}** today.")
                return
            match_id = found.get("id")
            async with aiohttp.ClientSession() as session:
                lineup_data = await hl_get(session, f"/lineups/{match_id}", {})
            if not lineup_data:
                await msg.edit(content=f"⏳ Lineups not available yet for **{team_name}** (available ~30min before kickoff).")
                return
            # hl_get's generic normalisation expects "groups"/"matches" keys; lineups responses
            # have neither, so the real object is preserved under "_raw" instead.
            lineups = lineup_data.get("_raw") or lineup_data.get("data") or lineup_data
            if isinstance(lineups, list):
                lineups = lineups[0] if lineups else {}
            if not lineups or not (lineups.get("homeTeam") or lineups.get("awayTeam")):
                await msg.edit(content=f"⏳ Lineups not available yet for **{team_name}** (available ~30min before kickoff).")
                return
            home_name = safe_name(found.get("homeTeam", {}), "Home")
            away_name = safe_name(found.get("awayTeam", {}), "Away")
            embed = discord.Embed(
                title=f"📋 Lineups — {home_name} vs {away_name}",
                color=0x1a3a2a
            )
            for side, label in [("homeTeam", home_name), ("awayTeam", away_name)]:
                team_lineup = lineups.get(side, {}) or {}
                formation = team_lineup.get("formation", "")
                starting_raw = team_lineup.get("initialLineup", [])
                # initialLineup is grouped into rows (GK, DEF, MID, FWD) — flatten it
                players = []
                for row in starting_raw:
                    if isinstance(row, list):
                        players.extend(row)
                    elif isinstance(row, dict):
                        players.append(row)
                starters = [f"`{p.get('shirtNumber') or p.get('number','?')}` {p.get('name','?')}" for p in players]
                bench = team_lineup.get("substitutes", [])
                value = f"**Formation: {formation}**\n" + ("\n".join(starters) if starters else "N/A")
                if bench:
                    bench_names = [p.get('name','?') for p in bench]
                    value += f"\n\n**Bench:** {', '.join(bench_names)}"
                embed.add_field(name=label, value=value or "N/A", inline=True)
            await msg.delete()
            await message.channel.send(embed=embed)
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")

    # ── Standings ──
    elif content == "-standings" or low.startswith("-standings "):
        if not HIGHLIGHTLY_API_KEY:
            await message.channel.send("❌ `HIGHLIGHTLY_API_KEY` not set.")
            return
        group_filter = content[11:].strip().upper() if low.startswith("-standings ") else None
        msg = await message.channel.send("⏳ Fetching World Cup standings...")
        try:
            async with aiohttp.ClientSession() as session:
                data = await hl_get(session, "/standings", {"leagueId": WC_LEAGUE_ID, "season": 2026})
            if not data:
                await msg.edit(content="ℹ️ No response from API.")
                return
            # Response uses "groups" key
            groups = data.get("_raw", {}).get("groups") or data.get("data")
            if not groups:
                await msg.edit(content="ℹ️ Standings not available yet.")
                return

            if group_filter:
                def group_matches(g):
                    name = (g.get("name") or "").upper()
                    return name == group_filter or name == f"GROUP {group_filter}" or name.endswith(f" {group_filter}")
                groups = [g for g in groups if group_matches(g)]
                if not groups:
                    await msg.edit(content=f"❌ No group found matching **{group_filter}**.")
                    return

            await msg.delete()
            for group in groups[:6]:
                group_name = group.get("name", "Group")
                embed = discord.Embed(title=f"📊 {group_name}", color=0x1a3a2a)
                # Try both "standings" and "teams" as possible keys
                rows = group.get("standings") or group.get("teams") or []
                lines = []
                for row in rows:
                    pos = row.get("position") or row.get("rank", "?")
                    team = safe_name(row.get("team", {})) or row.get("name", "?")
                    pts = row.get("points", 0)
                    flag = team_flag(team)
                    lines.append(f"`{pos}.` {flag} **{team}** — **{pts}** pts")
                embed.description = "\n".join(lines) if lines else "No data yet"
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
                home = safe_name(m.get("homeTeam", {}), "TBD")
                away = safe_name(m.get("awayTeam", {}), "TBD")
                home_disp = f"{team_flag(home)} {home}".strip()
                away_disp = f"{team_flag(away)} {away}".strip()
                state = m.get("state", {}) or {}
                description = state.get("description", "")
                clock = state.get("clock")
                score_current = (state.get("score") or {}).get("current")

                score = score_current if score_current else "vs"

                phase = get_match_phase(description)
                if phase == "live":
                    indicator = f"🔴 {clock}'" if clock else "🔴 LIVE"
                elif phase == "ended":
                    indicator = "🏁 FT"
                elif phase == "scheduled":
                    kickoff = m.get("date", "")
                    indicator = f"⏳ {kickoff[:10] if kickoff else 'TBD'}"
                else:
                    indicator = description or "?"

                embed.add_field(
                    name=f"{home_disp}  {score}  {away_disp}",
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
        embed.add_field(name="-tm [yday/tmrw]", value="World Cup matches — e.g. `-tm` or `-tm yday`", inline=False)
        embed.add_field(name="-live [team]", value="Live matches with goal scorers — e.g. `-live` or `-live France`", inline=False)
        embed.add_field(name="-match <team>", value="Match details & events — e.g. `-match France`", inline=False)
        embed.add_field(name="-lineup <team>", value="Starting lineup — e.g. `-lineup Brazil`", inline=False)
        embed.add_field(name="-standings [group]", value="Group stage standings — e.g. `-standings` or `-standings A`", inline=False)
        embed.add_field(name="-bracket", value="Knockout bracket menu", inline=False)
        embed.add_field(name="-bracket <round>", value="`r32` `r16` `qf` `sf` `final` `3rd`", inline=False)
        await message.channel.send(embed=embed)


if TOKEN:
    client.run(TOKEN)
else:
    print("Error: DISCORD_BOT_TOKEN not set.")