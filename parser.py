import csv
import json
import re
import urllib.error
import urllib.request
from datetime import datetime


def parse_rankings(filepath: str) -> tuple[dict, list]:
    """
    Parse the rankings CSV.

    Format: each column is a tournament (header = date), rows are players in rank order.
    Example:
        2025-01-15,2025-02-15,2025-03-15
        Alice,Bob,Alice
        Bob,Alice,Charlie
        Charlie,,Bob

    Returns:
        rankings: {tournament_date: {player_name_lower: rank}}  (rank starts at 1)
        tournaments: list of tournament dates sorted ascending (oldest first, newest last)
    """
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        raise ValueError("Rankings CSV is empty.")

    # First row = tournament date headers
    date_headers = [h.strip() for h in rows[0]]

    # Parse and sort dates
    def parse_date(d):
        for fmt in ("%Y%m%d", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(d, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Cannot parse date: {d!r}")

    indexed_dates = []
    for col_idx, d in enumerate(date_headers):
        if d:
            indexed_dates.append((col_idx, d, parse_date(d)))

    # Sort by date ascending
    indexed_dates.sort(key=lambda x: x[2])

    tournaments = [d for _, d, _ in indexed_dates]

    # Build rankings dict: {date: {player_lower: rank}}
    rankings = {d: {} for d in tournaments}

    for row_idx, row in enumerate(rows[1:], start=1):
        for col_idx, date_str, _ in indexed_dates:
            if col_idx < len(row):
                player = row[col_idx].strip()
                if player:
                    rankings[date_str][player.lower()] = row_idx

    # Store original casing for display: {player_lower: player_display}
    # We extract this separately so we can preserve the original name
    display_names = {}
    for row in rows[1:]:
        for cell in row:
            name = cell.strip()
            if name:
                display_names[name.lower()] = name

    return rankings, tournaments, display_names


def fetch_playtomic_signups(url_or_id: str) -> list[str]:
    """
    Fetch signed-up player names from a Playtomic tournament URL or ID.
    Returns a list of full_name strings in registration order.
    """
    uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    match = re.search(uuid_pattern, url_or_id, re.IGNORECASE)
    if not match:
        raise ValueError(f"Could not find a tournament ID in: {url_or_id!r}")
    tournament_id = match.group(0)

    url = f"https://api.playtomic.io/v1/tournaments/{tournament_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Playtomic API error {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error: {e.reason}") from e

    players = data.get("registered_players") or []
    names = [p["full_name"] for p in players if p.get("full_name")]
    if not names:
        raise ValueError("No registered players found in this tournament.")
    return names


def parse_signups(filepath: str) -> list[str]:
    """
    Parse signup list: one player name per line.
    Returns list of names (stripped, deduped, preserving order).
    """
    seen = set()
    players = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            name = line.strip()
            if name and name.lower() not in seen:
                seen.add(name.lower())
                players.append(name)
    return players
