import os
import time
import aiohttp
import discord
from datetime import datetime, timezone

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
LEADERBOARD_BASE_URL = "https://baburu-wc2026-leaderboard.hf.space"
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

# ── FIFA World Cup 2026 Round of 32 Match Configurations ──
R32_SLOTS = {
    73: {"teams": {"south africa", "canada"}, "default": "South Africa vs Canada"},
    74: {"teams": {"germany", "paraguay"}, "default": "Germany vs Paraguay"},
    75: {"teams": {"netherlands", "morocco"}, "default": "Netherlands vs Morocco"},
    76: {"teams": {"brazil", "japan"}, "default": "Brazil vs Japan"},
    77: {"teams": {"france", "sweden"}, "default": "France vs Sweden"},
    78: {"teams": {"ivory coast", "cote d'ivoire", "norway"}, "default": "Ivory Coast vs Norway"},
    79: {"teams": {"mexico", "ecuador"}, "default": "Mexico vs Ecuador"},
    80: {"teams": {"england", "dr congo", "congo dr"}, "default": "England vs DR Congo"},
    81: {"teams": {"belgium", "senegal"}, "default": "Belgium vs Senegal"},
    82: {"teams": {"united states", "usa", "bosnia and herzegovina", "bosnia"}, "default": "USA vs Bosnia & Herzegovina"},
    83: {"teams": {"portugal", "croatia"}, "default": "Portugal vs Croatia"},
    84: {"teams": {"spain", "austria"}, "default": "Spain vs Austria"},
    85: {"teams": {"colombia", "ghana"}, "default": "Colombia vs Ghana"},
    86: {"teams": {"argentina", "cape verde"}, "default": "Argentina vs Cape Verde"},
    87: {"teams": {"switzerland", "algeria"}, "default": "Switzerland vs Algeria"},
    88: {"teams": {"australia", "egypt"}, "default": "Australia vs Egypt"},
}

def get_r32_slot_number(home_name, away_name):
    h = (home_name or "").lower().strip()
    a = (away_name or "").lower().strip()
    for slot_num, info in R32_SLOTS.items():
        allowed = info["teams"]
        has_home = any(t in h or h in t for t in allowed)
        has_away = any(t in a or a in t for t in allowed)
        if has_home and has_away:
            return slot_num
    return None

def format_bracket_match(m):
    if not m:
        return "TBD vs TBD"
    home = safe_name(m.get("homeTeam", {}), "TBD")
    away = safe_name(m.get("awayTeam", {}), "TBD")
    home_disp = f"{team_flag(home)} {home}".strip()
    away_disp = f"{team_flag(away)} {away}".strip()
    state = m.get("state", {}) or {}
    description = state.get("description", "")
    clock = state.get("clock")
    score_obj = state.get("score") or {}
    score_current = score_obj.get("current")
    penalties = score_obj.get("penalties")
    
    phase = get_match_phase(description)
    if phase == "live":
        score = score_current if score_current else "vs"
        indicator = f"🔴 LIVE {clock}'" if clock else "🔴 LIVE"
    elif phase == "ended":
        score = score_current if score_current else "FT"
        if penalties:
            score += f" (Pens: {penalties})"
        indicator = "🏁 FT"
    elif phase == "scheduled":
        score = "vs"
        kickoff = m.get("date", "")
        indicator = f"⏳ {discord_ts(kickoff, 't')}" if kickoff else "⏳ TBD"
    else:
        score = "vs"
        indicator = description or "?"
        
    return f"{home_disp} **{score}** {away_disp} ({indicator})"

def format_slot(slot_num, match):
    if match:
        return format_bracket_match(match)
    default_text = R32_SLOTS[slot_num]["default"]
    teams = default_text.split(" vs ")
    h_flag = team_flag(teams[0])
    a_flag = team_flag(teams[1]) if len(teams) > 1 else ""
    return f"{h_flag} {teams[0]} vs {teams[1]} {a_flag}".strip() + " (⏳ TBD)"

def kickoff_unix(date_str):
    """Parse Highlightly's ISO date string (e.g. '2026-06-28T19:00:00.000Z') into a unix timestamp."""
    if not date_str:
        return None
    try:
        cleaned = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except (ValueError, TypeError):
        return None

def discord_ts(date_str, style="F"):
    """Build a Discord timestamp tag, e.g. <t:1234567890:F>, that renders in each
    user's own timezone/locale. Falls back to the raw string if parsing fails.
    Styles: t/T (time), d/D (date), f/F (date+time), R (relative, e.g. 'in 3 hours')."""
    ts = kickoff_unix(date_str)
    if ts is None:
        return date_str or "TBD"
    return f"<t:{ts}:{style}>"

def format_venue(venue):
    """venue: {'city': ..., 'name': ..., 'country': ..., 'capacity': ...}"""
    if not isinstance(venue, dict):
        return None
    name = venue.get("name")
    city = venue.get("city")
    country = venue.get("country")
    capacity = venue.get("capacity")
    if not (name or city):
        return None
    line = name or "Unknown venue"
    location_bits = [b for b in (city, country) if b]
    if location_bits:
        line += f" — {', '.join(location_bits)}"
    if capacity:
        line += f"\nCapacity: {capacity}"
    return line

def format_forecast(forecast):
    """forecast: {'status': ..., 'temperature': ...}"""
    if not isinstance(forecast, dict):
        return None
    status = forecast.get("status")
    temp = forecast.get("temperature")
    if not (status or temp):
        return None
    icon = "🌦️"
    s = (status or "").lower()
    if "clear" in s or "sun" in s:
        icon = "☀️" if "night" not in s else "🌙"
    elif "cloud" in s:
        icon = "☁️"
    elif "rain" in s:
        icon = "🌧️"
    parts = [p for p in (status, temp) if p]
    return f"{icon} {' — '.join(parts)}"

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
    live_states = {"first half", "second half", "half time", "extra time",
                   "extra time half time", "penalty shootout", "break time"}
    ended_states = {"finished", "finished aet", "finished ap",
                     "finished after extra time", "finished after penalties"}
    if not description:
        return "scheduled"
    d = description.strip().lower()
    if d in live_states:
        return "live"
    if d in ended_states:
        return "ended"
    if d == "not started":
        return "scheduled"
    return "other"

def format_statistics(stats, home_name, away_name):
    """
    Parse Highlightly /statistics/{matchId} response.
    Real shape: [{"team": {...}, "statistics": [{"displayName": "Ball possession", "value": 54}, ...]}, ...]
    Returns list of (label, home_val_str, away_val_str) tuples.
    """
    if not stats:
        return []

    def fmt_val(v, is_pct=False):
        if v is None:
            return "—"
        if is_pct:
            pv = round(v * 100) if isinstance(v, float) and v <= 1 else int(v)
            return f"{pv}%"
        if isinstance(v, float) and v != int(v):
            return f"{v:.2f}"
        return str(int(v)) if isinstance(v, (int, float)) else str(v)

    # Ordered display config: (displayName variants lowercased, short label, is_pct)
    DISPLAY_MAP = [
        (["ball possession", "possession"],                           "Possession",       True),
        (["total shots", "shots"],                                    "Shots",            False),
        (["shots on target", "shots on goal", "on target"],          "On Target",        False),
        (["shots off target", "off target"],                          "Off Target",       False),
        (["blocked shots", "blocked"],                                "Blocked",          False),
        (["expected goals", "xg", "xgoals", "expected goals (xg)"],  "xG",               False),
        (["expected assists", "xa"],                                   "xA",               False),
        (["shots accuracy", "shot accuracy"],                         "Shot Accuracy",    True),
        (["corner kicks", "corners"],                                 "Corners",          False),
        (["fouls", "total fouls"],                                    "Fouls",            False),
        (["yellow cards"],                                            "Yellow Cards",     False),
        (["red cards"],                                               "Red Cards",        False),
        (["offsides"],                                                "Offsides",         False),
        (["accurate passes", "pass accuracy", "passes %"],           "Pass Accuracy",    True),
        (["passes", "total passes"],                                  "Passes",           False),
        (["goalkeeper saves", "saves"],                               "Saves",            False),
        (["big chances"],                                             "Big Chances",      False),
        (["big chances missed"],                                      "Chances Missed",   False),
        (["attacks"],                                                 "Attacks",          False),
        (["dangerous attacks"],                                       "Danger. Attacks",  False),
        (["clearances"],                                              "Clearances",       False),
        (["interceptions"],                                           "Interceptions",    False),
        (["tackles"],                                                 "Tackles",          False),
    ]

    # Shape A: real Highlightly shape — list of team-stat objects
    if isinstance(stats, list) and stats and isinstance(stats[0], dict) and "statistics" in stats[0] and "team" in stats[0]:
        def stat_lookup(item):
            return {
                s.get("displayName", "").strip().lower(): s.get("value")
                for s in item.get("statistics", [])
                if isinstance(s, dict) and s.get("displayName") is not None
            }
        home_map = stat_lookup(stats[0]) if len(stats) > 0 else {}
        away_map = stat_lookup(stats[1]) if len(stats) > 1 else {}
        rows = []
        seen = set()
        for keys, label, is_pct in DISPLAY_MAP:
            h_val = next((home_map[k] for k in keys if k in home_map), None)
            a_val = next((away_map[k] for k in keys if k in away_map), None)
            if h_val is not None and a_val is not None and label not in seen:
                rows.append((label, fmt_val(h_val, is_pct), fmt_val(a_val, is_pct)))
                seen.add(label)
        return rows

    # Shape B: flat list of {"name"/"type", "home"/"homeValue", "away"/"awayValue"}
    if isinstance(stats, list):
        FLAT_MAP = {
            "possession": ("Possession", True), "ball possession": ("Possession", True),
            "shots": ("Shots", False), "total shots": ("Shots", False),
            "shots on target": ("On Target", False),
            "expected goals": ("xG", False), "xg": ("xG", False),
            "corners": ("Corners", False), "fouls": ("Fouls", False),
            "yellow cards": ("Yellow Cards", False), "offsides": ("Offsides", False),
            "saves": ("Saves", False), "passes": ("Passes", False),
        }
        rows = []
        seen = set()
        for item in stats:
            if not isinstance(item, dict):
                continue
            name = (item.get("name") or item.get("type") or "").strip().lower()
            h_val = item.get("home") if "home" in item else item.get("homeValue")
            a_val = item.get("away") if "away" in item else item.get("awayValue")
            mapping = FLAT_MAP.get(name)
            if mapping and h_val is not None and a_val is not None:
                label, is_pct = mapping
                if label not in seen:
                    rows.append((label, fmt_val(h_val, is_pct), fmt_val(a_val, is_pct)))
                    seen.add(label)
        return rows

    return []


def format_match_embed(m, title=None, statistics=None):
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
        status_str = "🏁 Full Time" if description.strip().lower() == "finished" else f"🏁 {description}"
        color = 0x00aa00
    elif phase == "scheduled":
        kickoff = m.get("date", "")
        status_str = f"⏳ {discord_ts(kickoff, 'F')} ({discord_ts(kickoff, 'R')})" if kickoff else "⏳ Scheduled"
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

    # ── Statistics ──
    # Try stats from the match object itself first, then the separately-fetched statistics arg
    raw_stats = (
        m.get("statistics")
        or m.get("stats")
        or statistics
    )
    if raw_stats and phase in ("live", "ended"):
        stat_rows = format_statistics(raw_stats, home, away)
        if stat_rows:
            h_abbr = home[:9]
            a_abbr = away[:9]
            table_lines = [f"{h_abbr:>9}   {'Stat':<16}   {a_abbr}",
                           "-" * 40]
            for label, h_val, a_val in stat_rows[:16]:
                table_lines.append(f"{h_val:>9}   {label:<16}   {a_val}")
            table = "\n".join(table_lines)
            embed.add_field(
                name="Match Statistics",
                value=f"```\n{table}\n```",
                inline=False
            )

    # Venue & weather (Highlightly returns these on /matches/{id} detail responses)
    venue_line = format_venue(m.get("venue"))
    if venue_line:
        embed.add_field(name="🏟️ Venue", value=venue_line, inline=True)
    forecast_line = format_forecast(m.get("forecast"))
    if forecast_line:
        embed.add_field(name="Weather", value=forecast_line, inline=True)

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
    if content in ("-lead", "-m1", "-m2", "-m3", "-m4"):
        board_map = {
            "-lead": {"path": "/preview", "title": "GENERAL CLASSIFICATION"},
            "-m1": {"path": "/m1/preview", "title": "MATCHDAY 1"},
            "-m2": {"path": "/m2/preview", "title": "MATCHDAY 2"},
            "-m3": {"path": "/m3/preview", "title": "MATCHDAY 3"},
            "-m4": {"path": "/m4/preview", "title": "MATCHDAY 4"},
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
                    indicator = f"⏳ {discord_ts(kickoff, 't')} ({discord_ts(kickoff, 'R')})" if kickoff else "⏳ TBD"
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
                    # Fetch live statistics
                    statistics = None
                    if match_id:
                        stats_data = await hl_get(session, f"/statistics/{match_id}", {})
                        if stats_data:
                            raw = stats_data.get("_raw") or stats_data.get("data") or stats_data
                            if isinstance(raw, (list, dict)):
                                statistics = raw
                    embed = format_match_embed(m, statistics=statistics)
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
                detail_obj = detail.get("_raw") or detail.get("data")
                if isinstance(detail_obj, list) and detail_obj:
                    found = detail_obj[0]
                elif isinstance(detail_obj, dict):
                    found = detail_obj
            elif isinstance(detail, list) and detail:
                found = detail[0]

            # Fetch statistics separately (Highlightly: /statistics/{match_id})
            statistics = None
            if match_id:
                async with aiohttp.ClientSession() as session:
                    stats_data = await hl_get(session, f"/statistics/{match_id}", {})
                if stats_data:
                    raw = stats_data.get("data") or stats_data.get("_raw") or stats_data
                    if isinstance(raw, (list, dict)):
                        statistics = raw

            embed = format_match_embed(found, statistics=statistics)
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
    elif low.startswith("-bracket"):
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

        if arg == "r32":
            if not HIGHLIGHTLY_API_KEY:
                await message.channel.send("❌ `HIGHLIGHTLY_API_KEY` not set.")
                return

            msg = await message.channel.send(f"⏳ Fetching **Round of 32** brackets...")
            try:
                async with aiohttp.ClientSession() as session:
                    data = await hl_get(session, "/matches", {
                        "leagueId": WC_LEAGUE_ID,
                        "season": 2026,
                        "limit": 100,
                    })
                all_matches = (data.get("data") if isinstance(data, dict) else data) or []
                
                # Map matches to slots
                mapped_matches = {i: None for i in range(73, 89)}
                for m in all_matches:
                    if not isinstance(m, dict):
                        continue
                    r = m.get("round", "")
                    if isinstance(r, dict):
                        r = safe_name(r)
                    r = (r or "").lower()
                    if "32" not in r and "thirty-two" not in r:
                        continue
                    
                    home = safe_name(m.get("homeTeam", {}))
                    away = safe_name(m.get("awayTeam", {}))
                    slot_num = get_r32_slot_number(home, away)
                    if slot_num:
                        mapped_matches[slot_num] = m

                # Create Left Bracket Embed
                embed_left = discord.Embed(
                    title="🏆 FIFA World Cup 2026 — LEFT BRACKET",
                    description="Paths leading to **Semi-Final 1**",
                    color=0x4a90d9
                )
                
                # Path 1 (QF 1)
                p1_m74 = format_slot(74, mapped_matches[74])
                p1_m77 = format_slot(77, mapped_matches[77])
                p1_m73 = format_slot(73, mapped_matches[73])
                p1_m75 = format_slot(75, mapped_matches[75])
                
                path1_val = (
                    f"┌─ **Match 74:** {p1_m74}\n"
                    f"└─ **Match 77:** {p1_m77}\n"
                    f"   *↳ Winner plays in R16 Match A*\n\n"
                    f"┌─ **Match 73:** {p1_m73}\n"
                    f"└─ **Match 75:** {p1_m75}\n"
                    f"   *↳ Winner plays in R16 Match B*\n\n"
                    f"👉 *R16 Match A Winner vs Match B Winner in QF 1*"
                )
                embed_left.add_field(name="🌿 Quarter-Final Path 1", value=path1_val, inline=False)

                # Path 2 (QF 2)
                p2_m76 = format_slot(76, mapped_matches[76])
                p2_m78 = format_slot(78, mapped_matches[78])
                p2_m79 = format_slot(79, mapped_matches[79])
                p2_m80 = format_slot(80, mapped_matches[80])
                
                path2_val = (
                    f"┌─ **Match 76:** {p2_m76}\n"
                    f"└─ **Match 78:** {p2_m78}\n"
                    f"   *↳ Winner plays in R16 Match C*\n\n"
                    f"┌─ **Match 79:** {p2_m79}\n"
                    f"└─ **Match 80:** {p2_m80}\n"
                    f"   *↳ Winner plays in R16 Match D*\n\n"
                    f"👉 *R16 Match C Winner vs Match D Winner in QF 2*"
                )
                embed_left.add_field(name="🌿 Quarter-Final Path 2", value=path2_val, inline=False)
                embed_left.set_footer(text="Left Bracket — Winners of QF 1 & QF 2 meet in Semifinal 1")

                # Create Right Bracket Embed
                embed_right = discord.Embed(
                    title="🏆 FIFA World Cup 2026 — RIGHT BRACKET",
                    description="Paths leading to **Semi-Final 2**",
                    color=0x7b68ee
                )

                # Path 3 (QF 3)
                p3_m83 = format_slot(83, mapped_matches[83])
                p3_m84 = format_slot(84, mapped_matches[84])
                p3_m81 = format_slot(81, mapped_matches[81])
                p3_m82 = format_slot(82, mapped_matches[82])
                
                path3_val = (
                    f"┌─ **Match 83:** {p3_m83}\n"
                    f"└─ **Match 84:** {p3_m84}\n"
                    f"   *↳ Winner plays in R16 Match E*\n\n"
                    f"┌─ **Match 81:** {p3_m81}\n"
                    f"└─ **Match 82:** {p3_m82}\n"
                    f"   *↳ Winner plays in R16 Match F*\n\n"
                    f"👉 *R16 Match E Winner vs Match F Winner in QF 3*"
                )
                embed_right.add_field(name="🔥 Quarter-Final Path 3", value=path3_val, inline=False)

                # Path 4 (QF 4)
                p4_m86 = format_slot(86, mapped_matches[86])
                p4_m88 = format_slot(88, mapped_matches[88])
                p4_m85 = format_slot(85, mapped_matches[85])
                p4_m87 = format_slot(87, mapped_matches[87])
                
                path4_val = (
                    f"┌─ **Match 86:** {p4_m86}\n"
                    f"└─ **Match 88:** {p4_m88}\n"
                    f"   *↳ Winner plays in R16 Match G*\n\n"
                    f"┌─ **Match 85:** {p4_m85}\n"
                    f"└─ **Match 87:** {p4_m87}\n"
                    f"   *↳ Winner plays in R16 Match H*\n\n"
                    f"👉 *R16 Match G Winner vs Match H Winner in QF 4*"
                )
                embed_right.add_field(name="🔥 Quarter-Final Path 4", value=path4_val, inline=False)
                embed_right.set_footer(text="Right Bracket — Winners of QF 3 & QF 4 meet in Semifinal 2")

                await msg.delete()
                await message.channel.send(embeds=[embed_left, embed_right])
            except Exception as e:
                await msg.edit(content=f"❌ Error: {e}")
            return

        else:
            round_label = ROUND_MAP[arg]
            ROUND_KEYWORDS = {
                "r16":   ["round of 16", "16"],
                "qf":    ["quarter"],
                "sf":    ["semi"],
                "final": ["final"],
                "3rd":   ["third", "3rd"],
            }
            msg = await message.channel.send(f"⏳ Fetching **{round_label}** matches...")
            try:
                async with aiohttp.ClientSession() as session:
                    data = await hl_get(session, "/matches", {
                        "leagueId": WC_LEAGUE_ID,
                        "season": 2026,
                        "limit": 100,
                    })
                all_matches = (data.get("data") if isinstance(data, dict) else data) or []
                if not all_matches:
                    await msg.edit(content=f"ℹ️ No World Cup matches found yet — check back when the tournament begins!")
                    return

                keywords = ROUND_KEYWORDS.get(arg, [round_label.lower()])

                def round_matches(m):
                    r = m.get("round", "")
                    if isinstance(r, dict):
                        r = safe_name(r)
                    r = (r or "").lower()
                    if arg == "final":
                        return "final" in r and "semi" not in r and "quarter" not in r
                    return any(k in r for k in keywords)

                matches = [m for m in all_matches if round_matches(m)]

                if not matches:
                    await msg.edit(content=f"ℹ️ No matches found for **{round_label}** yet — check back when the knockout stage begins!")
                    return

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
                        indicator = f"⏳ {discord_ts(kickoff, 'd')} {discord_ts(kickoff, 't')}" if kickoff else "⏳ TBD"
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

    # ── Next upcoming match ──
    elif low.startswith("-next"):
        if not HIGHLIGHTLY_API_KEY:
            await message.channel.send("❌ `HIGHLIGHTLY_API_KEY` not set.")
            return
        team_filter = content[5:].strip().lower() if len(content) > 5 else ""
        label = f"**{team_filter.title()}**'s" if team_filter else "the next"
        msg = await message.channel.send(f"⏳ Looking up {label} match...")
        try:
            now_unix = time.time()
            async with aiohttp.ClientSession() as session:
                data = await hl_get(session, "/matches", {
                    "leagueId": WC_LEAGUE_ID,
                    "season": 2026,
                    "limit": 100,
                })
            all_matches = (data.get("data") if isinstance(data, dict) else data) or []
            if not all_matches:
                await msg.edit(content="ℹ️ No World Cup matches found yet — check back when the tournament begins!")
                return

            candidates = []
            for m in all_matches:
                if not isinstance(m, dict):
                    continue
                state = m.get("state", {}) or {}
                if get_match_phase(state.get("description", "")) != "scheduled":
                    continue
                ts = kickoff_unix(m.get("date", ""))
                if ts is None or ts < now_unix:
                    continue
                if team_filter:
                    home = safe_name(m.get("homeTeam", {})).lower()
                    away = safe_name(m.get("awayTeam", {})).lower()
                    if team_filter not in home and team_filter not in away:
                        continue
                candidates.append((ts, m))

            if not candidates:
                if team_filter:
                    await msg.edit(content=f"ℹ️ No upcoming match found for **{team_filter.title()}**.")
                else:
                    await msg.edit(content="ℹ️ No upcoming World Cup matches found.")
                return
            candidates.sort(key=lambda c: c[0])
            ts, found = candidates[0]
            if not candidates:
                if team_filter:
                    await msg.edit(content=f"ℹ️ No upcoming match found for **{team_filter.title()}** in the next two weeks.")
                else:
                    await msg.edit(content="ℹ️ No upcoming World Cup matches found in the next two weeks.")
                return
            candidates.sort(key=lambda c: c[0])
            ts, found = candidates[0]
            # Fetch full detail for venue/forecast if available
            match_id = found.get("id")
            if match_id:
                async with aiohttp.ClientSession() as session:
                    detail = await hl_get(session, f"/matches/{match_id}", {})
                if isinstance(detail, dict):
                    detail_obj = detail.get("_raw") or detail.get("data")
                    if isinstance(detail_obj, list) and detail_obj:
                        found = detail_obj[0]
                    elif isinstance(detail_obj, dict):
                        found = detail_obj
            home = safe_name(found.get("homeTeam", {}), "TBD")
            away = safe_name(found.get("awayTeam", {}), "TBD")
            home_disp = f"{team_flag(home)} {home}".strip()
            away_disp = f"{team_flag(away)} {away}".strip()
            kickoff = found.get("date", "")
            embed = discord.Embed(
                title=f"⏭️ Next match — {home} vs {away}",
                description=f"## {home_disp}  vs  {away_disp}\n"
                            f"🗓️ {discord_ts(kickoff, 'F')}\n"
                            f"⏳ {discord_ts(kickoff, 'R')}",
                color=0x1a3a2a
            )
            venue_line = format_venue(found.get("venue"))
            if venue_line:
                embed.add_field(name="🏟️ Venue", value=venue_line, inline=True)
            forecast_line = format_forecast(found.get("forecast"))
            if forecast_line:
                embed.add_field(name="Weather", value=forecast_line, inline=True)
            group = found.get("round", "")
            if isinstance(group, dict):
                group = safe_name(group)
            if group:
                embed.set_footer(text=str(group))
            await msg.delete()
            await message.channel.send(embed=embed)
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")

    # ── Debug: dump raw match+stats keys for a team ──
    elif low.startswith("-debug "):
        team_name = content[7:].strip()
        if not HIGHLIGHTLY_API_KEY:
            await message.channel.send("\u274c `HIGHLIGHTLY_API_KEY` not set.")
            return
        msg = await message.channel.send(f"\u23f3 Fetching raw debug data for **{team_name}**...")
        try:
            from datetime import date, timedelta
            import json
            dates = [
                (date.today() - timedelta(days=1)).isoformat(),
                date.today().isoformat(),
                (date.today() + timedelta(days=1)).isoformat(),
            ]
            found = None
            _cache.clear()
            async with aiohttp.ClientSession() as session:
                for search_date in dates:
                    data = await hl_get(session, "/matches", {"date": search_date, "leagueId": WC_LEAGUE_ID})
                    if not data:
                        continue
                    matches_list = data.get("data") if isinstance(data, dict) else data
                    for m in (matches_list or []):
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
                await msg.edit(content=f"\u274c No match found for **{team_name}**.")
                return
            match_id = found.get("id")
            async with aiohttp.ClientSession() as session:
                detail = await hl_get(session, f"/matches/{match_id}", {})
                stats_data = await hl_get(session, f"/statistics/{match_id}", {})
            if isinstance(detail, dict):
                detail_obj = detail.get("_raw") or detail.get("data")
                if isinstance(detail_obj, list) and detail_obj:
                    found = detail_obj[0]
                elif isinstance(detail_obj, dict):
                    found = detail_obj
            match_keys = list(found.keys()) if isinstance(found, dict) else []
            stat_like = {k: found[k] for k in match_keys if any(s in k.lower() for s in ["stat", "possession", "shot", "xg", "pass", "corner", "foul"])}
            stats_preview = json.dumps(stats_data, default=str)[:800] if stats_data else "None"
            stats_keys = list(stats_data.keys()) if isinstance(stats_data, dict) else str(type(stats_data).__name__)
            out = (
                f"**Match ID:** `{match_id}`\n"
                f"**Match top-level keys:**\n```{match_keys}```\n"
                f"**Stat-like keys in match:**\n```{json.dumps(stat_like, default=str)[:400]}```\n"
                f"**`/statistics/{match_id}` keys:** `{stats_keys}`\n"
                f"**Stats raw preview:**\n```json\n{stats_preview}\n```"
            )
            await msg.delete()
            if len(out) > 1900:
                await message.channel.send(out[:1900])
                await message.channel.send(out[1900:3800])
            else:
                await message.channel.send(out)
        except Exception as e:
            await msg.edit(content=f"\u274c Error: {e}")

    # ── Help ──
    elif content == "-help":
        embed = discord.Embed(title="⚽ WC2026 Bot Commands", color=0x1a3a2a)
        embed.add_field(name="Leaderboard", value="`-lead` `-m1` `-m2` `-m3` `-m4`", inline=False)
        embed.add_field(name="-tm [yday/tmrw]", value="World Cup matches — e.g. `-tm` or `-tm yday`", inline=False)
        embed.add_field(name="-next [team]", value="Next upcoming match with live countdown timestamp — e.g. `-next` or `-next Brazil`", inline=False)
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