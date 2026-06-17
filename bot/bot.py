import os
from datetime import date
import aiohttp
import discord

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
LEADERBOARD_URL = os.environ.get("LEADERBOARD_URL", "https://wc2026-leaderboard.onrender.com/post")
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY")

API_FOOTBALL_HOST = "v3.football.api-sports.io"
API_FOOTBALL_BASE = f"https://{API_FOOTBALL_HOST}"

WC_LEAGUE_ID = 1
WC_SEASON = 2026

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


def api_headers():
    return {
        "x-apisports-key": API_FOOTBALL_KEY,
        "x-rapidapi-host": API_FOOTBALL_HOST,
    }


# ──────────────────────────────────────────────
# SHARED: find fixture by team name
# ──────────────────────────────────────────────
async def find_fixture(session, team_name: str):
    async with session.get(f"{API_FOOTBALL_BASE}/fixtures", params={"live": "all"}) as r:
        fixtures = (await r.json()).get("response", [])

    match = next(
        (f for f in fixtures if
         team_name.lower() in f["teams"]["home"]["name"].lower() or
         team_name.lower() in f["teams"]["away"]["name"].lower()),
        None
    )

    if not match:
        today = date.today().isoformat()
        async with session.get(f"{API_FOOTBALL_BASE}/fixtures", params={"date": today}) as r:
            fixtures = (await r.json()).get("response", [])
        match = next(
            (f for f in fixtures if
             team_name.lower() in f["teams"]["home"]["name"].lower() or
             team_name.lower() in f["teams"]["away"]["name"].lower()),
            None
        )

    return match


# ──────────────────────────────────────────────
# -match <team>
# ──────────────────────────────────────────────
async def fetch_match_stats(team_name: str):
    async with aiohttp.ClientSession(headers=api_headers()) as session:
        match = await find_fixture(session, team_name)
        if not match:
            return None, "no_match"

        fixture_id = match["fixture"]["id"]
        home = match["teams"]["home"]
        away = match["teams"]["away"]
        status = match["fixture"]["status"]["long"]
        elapsed = match["fixture"]["status"]["elapsed"]

        async with session.get(f"{API_FOOTBALL_BASE}/fixtures/statistics", params={"fixture": fixture_id}) as r:
            stats_response = (await r.json()).get("response", [])

        async with session.get(f"{API_FOOTBALL_BASE}/fixtures/events", params={"fixture": fixture_id}) as r:
            events = (await r.json()).get("response", [])

        def get_stat(team_stats, stat_name):
            for s in team_stats.get("statistics", []):
                if s["type"] == stat_name:
                    return s["value"] if s["value"] is not None else 0
            return 0

        home_stats = next((s for s in stats_response if s["team"]["id"] == home["id"]), {"statistics": []})
        away_stats = next((s for s in stats_response if s["team"]["id"] == away["id"]), {"statistics": []})

        def get_goals(team_id):
            goals = []
            for e in events:
                if e["type"] == "Goal" and e["team"]["id"] == team_id:
                    minute = e["time"]["elapsed"]
                    extra = e["time"]["extra"]
                    min_str = f"{minute}+{extra}'" if extra else f"{minute}'"
                    scorer = e["player"]["name"]
                    assist = e.get("assist", {}).get("name")
                    goals.append({"minute": min_str, "scorer": scorer, "assist": assist})
            return goals

        result = {
            "fixture_id": fixture_id,
            "status": status,
            "elapsed": elapsed,
            "home": {
                "name": home["name"],
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
                "scorers": get_goals(home["id"]),
            },
            "away": {
                "name": away["name"],
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
                "scorers": get_goals(away["id"]),
            },
        }
        return result, "ok"


def build_match_embed(data: dict) -> discord.Embed:
    home = data["home"]
    away = data["away"]
    elapsed = data["elapsed"]
    status = data["status"]

    title = f"{home['name']}  {home['goals']} – {away['goals']}  {away['name']}"
    description = f"🕐 {status}" + (f" ({elapsed}')" if elapsed else "")

    def format_scorers(scorers):
        if not scorers:
            return ""
        lines = []
        for g in scorers:
            line = f"⚽ {g['minute']} {g['scorer']}"
            if g["assist"]:
                line += f" _(assist: {g['assist']})_"
            lines.append(line)
        return "\n".join(lines)

    home_scorers = format_scorers(home["scorers"])
    away_scorers = format_scorers(away["scorers"])

    scorers_value = ""
    if home_scorers or away_scorers:
        if home_scorers:
            scorers_value += f"**{home['name']}**\n{home_scorers}\n"
        if away_scorers:
            scorers_value += f"**{away['name']}**\n{away_scorers}"

    embed = discord.Embed(title=title, description=description, color=0x1a1a2e)

    if scorers_value:
        embed.add_field(name="⚽ Goal Scorers", value=scorers_value.strip(), inline=False)

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
        name=f"📊 {home['name']}  vs  {away['name']}",
        value="\n".join(stats_lines),
        inline=False
    )
    embed.set_footer(text="Data via API-Football")
    return embed


# ──────────────────────────────────────────────
# -lineup <team>
# ──────────────────────────────────────────────
async def fetch_lineup(team_name: str):
    async with aiohttp.ClientSession(headers=api_headers()) as session:
        match = await find_fixture(session, team_name)
        if not match:
            return None, "no_match"

        fixture_id = match["fixture"]["id"]

        async with session.get(f"{API_FOOTBALL_BASE}/fixtures/lineups", params={"fixture": fixture_id}) as r:
            lineups = (await r.json()).get("response", [])

        if not lineups:
            return None, "no_lineup"

        team_lineup = next(
            (l for l in lineups if team_name.lower() in l["team"]["name"].lower()),
            lineups[0]
        )

        return {
            "fixture_id": fixture_id,
            "home": match["teams"]["home"]["name"],
            "away": match["teams"]["away"]["name"],
            "status": match["fixture"]["status"]["long"],
            "team": team_lineup["team"]["name"],
            "formation": team_lineup.get("formation", "N/A"),
            "startXI": [p["player"] for p in team_lineup.get("startXI", [])],
            "substitutes": [p["player"] for p in team_lineup.get("substitutes", [])],
            "coach": team_lineup.get("coach", {}).get("name", "N/A"),
        }, "ok"


def build_lineup_embed(data: dict) -> discord.Embed:
    embed = discord.Embed(
        title=f"📋 {data['team']} Lineup",
        description=f"{data['home']} vs {data['away']} · {data['status']}",
        color=0x2ecc71
    )
    embed.add_field(name="Formation", value=f"`{data['formation']}`", inline=True)
    embed.add_field(name="Coach", value=data["coach"], inline=True)

    if data["startXI"]:
        starters = "\n".join(
            f"`{p.get('number', '?'):>2}` {p['name']} — *{p.get('pos', '?')}*"
            for p in data["startXI"]
        )
        embed.add_field(name="Starting XI", value=starters, inline=False)

    if data["substitutes"]:
        subs = "\n".join(
            f"`{p.get('number', '?'):>2}` {p['name']} — *{p.get('pos', '?')}*"
            for p in data["substitutes"][:8]
        )
        embed.add_field(name="Substitutes", value=subs, inline=False)

    embed.set_footer(text="Data via API-Football")
    return embed


# ──────────────────────────────────────────────
# -standings
# ──────────────────────────────────────────────
async def fetch_standings():
    async with aiohttp.ClientSession(headers=api_headers()) as session:
        async with session.get(
            f"{API_FOOTBALL_BASE}/standings",
            params={"league": WC_LEAGUE_ID, "season": WC_SEASON}
        ) as r:
            data = (await r.json()).get("response", [])

    if not data:
        return None, "no_data"

    standings = data[0].get("league", {}).get("standings", [])
    return standings, "ok"


def build_standings_embeds(standings: list, group_filter: str = None) -> list:
    embeds = []
    norm_filter = None
    if group_filter:
        # Normalise "group A" / "a" / "Group A" → "a" for a forgiving match.
        norm_filter = group_filter.lower().replace("group", "").strip()

    for group in standings:
        if not group:
            continue
        group_name = group[0].get("group", "Group")

        if norm_filter:
            norm_name = group_name.lower().replace("group", "").strip()
            if norm_filter != norm_name and norm_filter not in norm_name:
                continue

        embed = discord.Embed(title=f"🏆 WC 2026 — {group_name}", color=0xe74c3c)
        rows = []
        for t in group:
            rank = t["rank"]
            name = t["team"]["name"]
            played = t["all"]["played"]
            won = t["all"]["win"]
            drawn = t["all"]["draw"]
            lost = t["all"]["lose"]
            gd = t["goalsDiff"]
            pts = t["points"]
            gd_str = f"+{gd}" if gd > 0 else str(gd)
            rows.append(f"`{rank}` **{name}** — {played}GP · {won}W {drawn}D {lost}L · GD {gd_str} · **{pts}pts**")
        embed.description = "\n".join(rows)
        embed.set_footer(text="Data via API-Football")
        embeds.append(embed)
    return embeds


# ──────────────────────────────────────────────
# -bracket
# ──────────────────────────────────────────────
async def fetch_bracket():
    async with aiohttp.ClientSession(headers=api_headers()) as session:
        async with session.get(
            f"{API_FOOTBALL_BASE}/fixtures",
            params={"league": WC_LEAGUE_ID, "season": WC_SEASON}
        ) as r:
            fixtures = (await r.json()).get("response", [])

    knockout_rounds = ["Round of 32", "Round of 16", "Quarter-finals", "Semi-finals", "3rd Place Final", "Final"]
    rounds = {}
    for f in fixtures:
        rnd = f["league"].get("round", "")
        if any(k.lower() in rnd.lower() for k in knockout_rounds):
            rounds.setdefault(rnd, []).append(f)

    if not rounds:
        return None, "no_data"

    return rounds, "ok"


# Maps user shorthand → official round label used by the API.
BRACKET_ALIASES = {
    "32": "Round of 32",
    "r32": "Round of 32",
    "ro32": "Round of 32",
    "16": "Round of 16",
    "r16": "Round of 16",
    "ro16": "Round of 16",
    "8": "Quarter-finals",
    "qf": "Quarter-finals",
    "quarter": "Quarter-finals",
    "quarters": "Quarter-finals",
    "quarterfinal": "Quarter-finals",
    "quarterfinals": "Quarter-finals",
    "quarter-finals": "Quarter-finals",
    "4": "Semi-finals",
    "sf": "Semi-finals",
    "semi": "Semi-finals",
    "semis": "Semi-finals",
    "semifinal": "Semi-finals",
    "semifinals": "Semi-finals",
    "semi-finals": "Semi-finals",
    "3rd": "3rd Place Final",
    "third": "3rd Place Final",
    "bronze": "3rd Place Final",
    "final": "Final",
    "finals": "Final",
}


def resolve_bracket_round(arg: str) -> str:
    """Return the official round label for a user shorthand, or None if unknown."""
    return BRACKET_ALIASES.get(arg.lower().strip().replace(" ", ""))


def build_bracket_embeds(rounds: dict, round_filter: str = None) -> list:
    round_order = ["Round of 32", "Round of 16", "Quarter-finals", "Semi-finals", "3rd Place Final", "Final"]
    if round_filter:
        round_order = [round_filter]
    embeds = []

    for rnd_label in round_order:
        # "Final" is a substring of "3rd Place Final", so match exactly first
        # and only fall back to substring matching for the other rounds.
        key = next((k for k in rounds if rnd_label.lower() == k.lower()), None)
        if not key and rnd_label != "Final":
            key = next((k for k in rounds if rnd_label.lower() in k.lower()), None)
        if not key:
            continue

        matches = rounds[key]
        embed = discord.Embed(title=f"🏟️ {key}", color=0x9b59b6)
        rows = []
        for f in matches:
            home = f["teams"]["home"]["name"]
            away = f["teams"]["away"]["name"]
            gh = f["goals"]["home"]
            ga = f["goals"]["away"]
            status = f["fixture"]["status"]["short"]

            if status in ("NS", "TBD"):
                match_date = f["fixture"]["date"][:10] if f["fixture"]["date"] else "TBD"
                rows.append(f"🔲 **{home}** vs **{away}** — {match_date}")
            elif status == "FT":
                rows.append(f"✅ **{home} {gh} – {ga} {away}**")
            else:
                elapsed = f["fixture"]["status"]["elapsed"] or ""
                rows.append(f"🔴 **{home} {gh} – {ga} {away}** `{elapsed}'`")

        embed.description = "\n".join(rows) if rows else "No matches yet."
        embed.set_footer(text="Data via API-Football")
        embeds.append(embed)

    return embeds


# ──────────────────────────────────────────────
# -replays <team>  — scrape r/soccer
# ──────────────────────────────────────────────
REDDIT_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DiscordBot/1.0)"}
REPLAY_KEYWORDS = ["goal:", "goal |", "highlight", "match thread"]
VIDEO_DOMAINS = ["streamable.com", "youtube.com", "youtu.be", "v.redd.it"]


async def fetch_replays(team_name: str):
    # Use reddit's search endpoint (restricted to r/soccer) so we actually find
    # the team's clips instead of only scanning the 100 newest posts.
    url = "https://www.reddit.com/r/soccer/search.json"
    params = {
        "q": team_name,
        "restrict_sr": "on",
        "sort": "top",
        "t": "month",
        "limit": 100,
    }

    async with aiohttp.ClientSession(headers=REDDIT_HEADERS) as session:
        async with session.get(url, params=params) as r:
            if r.status != 200:
                return None, "no_results"
            data = await r.json()

    posts = data.get("data", {}).get("children", [])
    results = []

    for post in posts:
        p = post["data"]
        title = p.get("title", "")
        post_url = p.get("url", "")
        permalink = "https://reddit.com" + p.get("permalink", "")

        # Must mention the team name
        if team_name.lower() not in title.lower():
            continue

        # Must look like a goal or highlight post
        title_low = title.lower()
        if not any(kw in title_low for kw in REPLAY_KEYWORDS):
            continue

        # Use direct video link if available, otherwise reddit post
        is_video = any(domain in post_url for domain in VIDEO_DOMAINS)
        link = post_url if is_video else permalink

        results.append({
            "title": title,
            "url": link,
            "score": p.get("score", 0),
        })

    if not results:
        return None, "no_results"

    # Sort by upvotes, return top 5
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:5], "ok"


def build_replays_embed(team_name: str, replays: list) -> discord.Embed:
    embed = discord.Embed(
        title=f"🎬 Goal Replays — {team_name}",
        description="Top clips from r/soccer · Video links posted below for preview",
        color=0xff4500
    )
    for i, r in enumerate(replays, 1):
        embed.add_field(
            name=f"{i}. {r['title']}",
            value=f"👍 {r['score']} upvotes",
            inline=False
        )
    embed.set_footer(text="Source: r/soccer — No API key needed")
    return embed


# ──────────────────────────────────────────────
# COMMAND ROUTER
# ──────────────────────────────────────────────
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


@client.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()
    low = content.lower()

    # ── -lead ──
    if low == "-lead":
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

    # ── -m1 / -m2 / -m3 ──
    elif low in ("-m1", "-m2", "-m3"):
        key = low[1:]  # strips the "-" → "m1", "m2", "m3"
        url = LEADERBOARD_URL.replace("/post", f"/{key}")
        msg = await message.channel.send(f"⏳ Fetching {key.upper()} leaderboard...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                    data = await response.json()
                    if not data.get("ok"):
                        await msg.edit(content=f"❌ Failed to fetch {key.upper()} leaderboard.")
                    else:
                        await msg.delete()
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")

    # ── -match <team> ──
    elif low.startswith("-match "):
        if not API_FOOTBALL_KEY:
            await message.channel.send("❌ `API_FOOTBALL_KEY` env variable not set.")
            return
        team_name = content[7:].strip()
        if not team_name:
            await message.channel.send("❌ Usage: `-match <team>` — e.g. `-match France`")
            return
        msg = await message.channel.send(f"⏳ Looking up match for **{team_name}**...")
        try:
            data, status = await fetch_match_stats(team_name)
            if status == "no_match":
                await msg.edit(content=f"❌ No match found today for **{team_name}**.")
                return
            embed = build_match_embed(data)
            await msg.delete()
            await message.channel.send(embed=embed)
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")

    # ── -lineup <team> ──
    elif low.startswith("-lineup "):
        if not API_FOOTBALL_KEY:
            await message.channel.send("❌ `API_FOOTBALL_KEY` env variable not set.")
            return
        team_name = content[8:].strip()
        if not team_name:
            await message.channel.send("❌ Usage: `-lineup <team>` — e.g. `-lineup France`")
            return
        msg = await message.channel.send(f"⏳ Fetching lineup for **{team_name}**...")
        try:
            data, status = await fetch_lineup(team_name)
            if status == "no_match":
                await msg.edit(content=f"❌ No match found today for **{team_name}**.")
            elif status == "no_lineup":
                await msg.edit(content=f"❌ Lineup not released yet for **{team_name}**.")
            else:
                embed = build_lineup_embed(data)
                await msg.delete()
                await message.channel.send(embed=embed)
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")

    # ── -standings [group] ──
    elif low == "-standings" or low.startswith("-standings "):
        if not API_FOOTBALL_KEY:
            await message.channel.send("❌ `API_FOOTBALL_KEY` env variable not set.")
            return
        group_filter = content[len("-standings"):].strip() or None
        label = f" — {group_filter}" if group_filter else ""
        msg = await message.channel.send(f"⏳ Fetching WC 2026 standings{label}...")
        try:
            data, status = await fetch_standings()
            if status == "no_data":
                await msg.edit(content="❌ No standings data available yet.")
                return
            embeds = build_standings_embeds(data, group_filter)
            if not embeds:
                await msg.edit(content=f"❌ No standings found for **{group_filter}**. Try `-standings group A`.")
                return
            await msg.delete()
            for i in range(0, len(embeds), 10):
                await message.channel.send(embeds=embeds[i:i+10])
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")

    # ── -bracket [round] ──
    elif low == "-bracket" or low.startswith("-bracket "):
        if not API_FOOTBALL_KEY:
            await message.channel.send("❌ `API_FOOTBALL_KEY` env variable not set.")
            return
        arg = content[len("-bracket"):].strip()
        round_filter = None
        if arg:
            round_filter = resolve_bracket_round(arg)
            if not round_filter:
                await message.channel.send(
                    "❌ Unknown round. Try `-bracket 32`, `-bracket 16`, "
                    "`-bracket quarters`, `-bracket semi`, `-bracket final`."
                )
                return
        label = f" — {round_filter}" if round_filter else ""
        msg = await message.channel.send(f"⏳ Fetching WC 2026 bracket{label}...")
        try:
            data, status = await fetch_bracket()
            if status == "no_data":
                await msg.edit(content="❌ Knockout bracket not available yet (group stage may still be ongoing).")
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

    # ── -replays <team> ──
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
            # Post links separately so Discord auto-previews the videos
            links = "\n".join(r["url"] for r in replays)
            await message.channel.send(links)
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")


client.run(TOKEN)
