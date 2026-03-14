"""
Position history utilities.

Provides matchday detection from historico.csv, table simulation, and
CSV management for data/posicoes.csv.
"""
from __future__ import annotations

import csv
import os
from datetime import datetime, timedelta
from typing import Optional

POSICOES_CSV = "data/posicoes.csv"
POSICOES_FIELDNAMES = ["time", "liga", "matchday", "posicao", "data_fim_matchday"]

# Weekday sets for English football calendar blocks
_BLOCK_A = {4, 5, 6, 0}  # Fri, Sat, Sun, Mon

# ── Point deductions ────────────────────────────────────────────────────────
# Structure: {liga_str: [(team, threshold_date_str, pts_to_deduct), ...]}
# Multiple rows for the same team are cumulative (each applies independently).
_POINT_DEDUCTIONS: dict[str, list[tuple[str, str, int]]] = {
    "Championship": [
        ("Sheffield Wednesday", "2024-10-24", 12),
        ("Sheffield Wednesday", "2024-12-01",  6),  # additional → total 18
        ("Leicester City",      "2026-02-05",  6),
    ],
}


def _apply_deductions(
    liga_str: str,
    stats: dict[str, dict],
    data_fim: str,
) -> None:
    """
    Mutates stats[team]['pts'] in place by subtracting the applicable
    point deductions. Points never go below 0.
    """
    rules = _POINT_DEDUCTIONS.get(liga_str, [])
    for team, threshold, pts in rules:
        if team not in stats:
            continue
        if data_fim >= threshold:
            stats[team]["pts"] = max(0, stats[team]["pts"] - pts)


def _block(weekday: int) -> str:
    return "A" if weekday in _BLOCK_A else "B"


def _ensure_new_schema() -> None:
    """
    If posicoes.csv exists with the old schema (no 'matchday' column),
    rename it to posicoes.csv.bak so the new schema can be written cleanly.
    """
    if not os.path.exists(POSICOES_CSV):
        return
    with open(POSICOES_CSV, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return
    if "matchday" not in header:
        bak = POSICOES_CSV + ".bak"
        os.rename(POSICOES_CSV, bak)


def _anchor_date(data_fim: str) -> str:
    """
    Adjusts data_fim to the 'anchor' display date for the matchday:
      Monday (0)   → subtract 2 days → Saturday
      Wednesday (2) → subtract 1 day  → Tuesday
      Thursday (3) → subtract 2 days → Tuesday
      Other days   → unchanged
    """
    from datetime import date as date_cls
    d = date_cls.fromisoformat(data_fim)
    wd = d.weekday()
    if wd == 0:
        d -= timedelta(days=2)
    elif wd == 2:
        d -= timedelta(days=1)
    elif wd == 3:
        d -= timedelta(days=2)
    return d.strftime("%Y-%m-%d")


def detect_matchdays(liga_str: str) -> dict[int, list[str]]:
    """
    Reads data/historico.csv, filters by liga_str, and groups game dates into
    matchdays.

    A new matchday starts when ANY of the following is true:
      a) gap between the current date and the previous date is > 4 days.
      b) current date belongs to a different block than the previous date,
         where Block A = Fri/Sat/Sun/Mon and Block B = Tue/Wed/Thu.

    Returns {matchday_number: [list of YYYY-MM-DD strings]}.
    """
    csv_path = os.path.join("data", "historico.csv")
    if not os.path.exists(csv_path):
        return {}

    from datetime import date as date_cls

    dates_set: set[date_cls] = set()
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("liga") != liga_str:
                continue
            try:
                d = datetime.strptime(row["data"], "%Y-%m-%d").date()
                dates_set.add(d)
            except (ValueError, KeyError):
                continue

    if not dates_set:
        return {}

    sorted_dates = sorted(dates_set)
    matchdays: dict[int, list[str]] = {}
    matchday_num = 1
    current_block = _block(sorted_dates[0].weekday())
    matchdays[matchday_num] = [sorted_dates[0].strftime("%Y-%m-%d")]

    for i in range(1, len(sorted_dates)):
        prev = sorted_dates[i - 1]
        curr = sorted_dates[i]
        gap = (curr - prev).days
        curr_block = _block(curr.weekday())

        if gap > 4 or curr_block != current_block:
            matchday_num += 1
            current_block = curr_block
            matchdays[matchday_num] = []

        matchdays[matchday_num].append(curr.strftime("%Y-%m-%d"))

    return matchdays


def _all_teams_in_liga(liga_str: str) -> set[str]:
    """Returns the set of all team names that appear in historico.csv for the liga."""
    csv_path = os.path.join("data", "historico.csv")
    teams: set[str] = set()
    if not os.path.exists(csv_path):
        return teams
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("liga") != liga_str:
                continue
            if row.get("casa"):
                teams.add(row["casa"])
            if row.get("fora"):
                teams.add(row["fora"])
    return teams


def compute_table_at_matchday(
    liga_str: str,
    up_to_matchday: int,
    matchday_map: dict[int, list[str]],
) -> dict[str, int]:
    """
    Simulates the league table from matchday 1 up to (and including)
    up_to_matchday.

    ALL teams in the liga are included — even those that have not yet played
    by up_to_matchday — so that the position history CSV has a continuous
    series for every team.

    Point deductions (defined in _POINT_DEDUCTIONS) are applied after
    accumulating all game points, before sorting.

    Returns {team_name: position} sorted by standard English tiebreaker
    rules (points → goal difference → goals for → name).
    """
    target_dates: set[str] = set()
    for md in range(1, up_to_matchday + 1):
        for d in matchday_map.get(md, []):
            target_dates.add(d)

    # data_fim of the matchday being computed (for deduction thresholds)
    this_matchday_dates = matchday_map.get(up_to_matchday, [])
    data_fim = sorted(this_matchday_dates)[-1] if this_matchday_dates else ""

    csv_path = os.path.join("data", "historico.csv")
    if not os.path.exists(csv_path):
        return {}

    # Initialise all teams with zeroed stats so every team appears in
    # every matchday snapshot.
    all_teams = _all_teams_in_liga(liga_str)
    stats: dict[str, dict] = {t: {"pts": 0, "gd": 0, "gf": 0} for t in all_teams}

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("liga") != liga_str:
                continue
            if row.get("data") not in target_dates:
                continue
            placar = row.get("placar", "")
            # Only parse clean X-Y scores; skip ADI., ABD., D-D, etc.
            try:
                left, right = placar.split("-")
                gols_casa = int(left.strip())
                gols_fora = int(right.strip())
            except (ValueError, AttributeError):
                continue

            home, away = row["casa"], row["fora"]
            stats[home]["gf"] += gols_casa
            stats[home]["gd"] += gols_casa - gols_fora
            stats[away]["gf"] += gols_fora
            stats[away]["gd"] += gols_fora - gols_casa

            if gols_casa > gols_fora:
                stats[home]["pts"] += 3
            elif gols_casa == gols_fora:
                stats[home]["pts"] += 1
                stats[away]["pts"] += 1
            else:
                stats[away]["pts"] += 3

    # Apply point deductions before sorting
    _apply_deductions(liga_str, stats, data_fim)

    sorted_teams = sorted(
        stats.keys(),
        key=lambda t: (-stats[t]["pts"], -stats[t]["gd"], -stats[t]["gf"], t),
    )
    return {team: pos for pos, team in enumerate(sorted_teams, start=1)}


def append_matchday_positions(
    liga_str: str,
    positions: dict[str, int],
    data_fim: str,
) -> int:
    """
    Appends position records to data/posicoes.csv.

    Applies anchor-day adjustment to data_fim before storing:
      Monday  → Saturday (−2 days)
      Wednesday → Tuesday (−1 day)
      Thursday  → Tuesday (−2 days)
      Other days → unchanged

    The replace-vs-insert decision and the stored matchday number are both
    derived automatically from day-of-week blocks:
      Block A: Friday (4), Saturday (5), Sunday (6), Monday (0)
      Block B: Tuesday (1), Wednesday (2), Thursday (3)

    - No previous matchday for the liga in posicoes.csv
        → INSERT, stored matchday = 1.
    - data_fim_matchday of the last registered matchday is in the same block
      as today → REPLACE: existing rows for (liga_str, last_md) are removed
      and rewritten with stored matchday = last_md.
    - Last registered matchday is in a different block
        → INSERT, stored matchday = last_md + 1.

    Returns the number of rows added.
    """
    from datetime import date as _date_cls
    _ensure_new_schema()

    today_block = _block(_date_cls.today().weekday())

    # Find the last recorded matchday number and its data_fim_matchday
    last_md: Optional[int] = None
    last_data_fim: Optional[str] = None
    if os.path.exists(POSICOES_CSV):
        with open(POSICOES_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("liga") != liga_str:
                    continue
                try:
                    md_val = int(row["matchday"])
                except (ValueError, KeyError):
                    continue
                if last_md is None or md_val > last_md:
                    last_md = md_val
                    last_data_fim = row.get("data_fim_matchday", "")

    # Decide: REPLACE or INSERT, and compute the matchday number to store
    if last_md is None:
        # No prior data for this liga → first entry
        stored_matchday = 1
        do_replace = False
    else:
        try:
            last_block = _block(_date_cls.fromisoformat(last_data_fim).weekday())
        except (ValueError, TypeError):
            last_block = None
        if last_block == today_block:
            # Same block → still within the same open matchday
            stored_matchday = last_md
            do_replace = True
        else:
            # Different block → new matchday
            stored_matchday = last_md + 1
            do_replace = False

    if do_replace:
        # Remove existing rows for (liga_str, stored_matchday) before rewriting
        surviving_rows = []
        with open(POSICOES_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                if not (
                    row.get("liga") == liga_str
                    and str(row.get("matchday")) == str(stored_matchday)
                ):
                    surviving_rows.append(row)
        with open(POSICOES_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames or POSICOES_FIELDNAMES)
            writer.writeheader()
            writer.writerows(surviving_rows)

    anchored = _anchor_date(data_fim)

    new_rows = [
        {
            "time": team,
            "liga": liga_str,
            "matchday": stored_matchday,
            "posicao": pos,
            "data_fim_matchday": anchored,
        }
        for team, pos in positions.items()
    ]

    write_header = not os.path.exists(POSICOES_CSV)
    with open(POSICOES_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=POSICOES_FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerows(new_rows)

    return len(new_rows)


def compute_position_delta(team: str, liga_str: str) -> Optional[int]:
    """
    Reads data/posicoes.csv and returns the position change between the last
    two recorded matchdays for the given team/liga.

    Returns pos[N-1] - pos[N]:
        positive  → moved up
        negative  → dropped
        0         → same position

    Returns None if fewer than 2 records exist.
    """
    if not os.path.exists(POSICOES_CSV):
        return None

    records: list[tuple[int, int]] = []
    with open(POSICOES_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("liga") == liga_str and row.get("time") == team:
                try:
                    records.append((int(row["matchday"]), int(row["posicao"])))
                except (ValueError, KeyError):
                    continue

    if len(records) < 2:
        return None

    records.sort(key=lambda r: r[0], reverse=True)
    pos_last = records[0][1]
    pos_prev = records[1][1]
    return pos_prev - pos_last
