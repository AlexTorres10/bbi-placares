"""
File-based cache for computed league stats (data/insights_cache.json).

Keys in the JSON file are liga_str values (e.g. "Premier League"),
matching the 'liga' column in data/historico.csv.
"""
import json
import os
from datetime import datetime
from typing import Optional

import pandas as pd

CACHE_PATH = "data/insights_cache.json"
HISTORICO_PATH = "data/historico.csv"


def _load_raw() -> dict:
    if not os.path.exists(CACHE_PATH):
        return {}
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_raw(raw: dict) -> None:
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)


def historico_last_date(liga_str: str) -> Optional[str]:
    """Max game date in historico.csv for this liga, as YYYY-MM-DD string."""
    if not os.path.exists(HISTORICO_PATH):
        return None
    try:
        df = pd.read_csv(HISTORICO_PATH, parse_dates=["data"])
        df = df[df["liga"] == liga_str]
        if df.empty:
            return None
        return df["data"].max().strftime("%Y-%m-%d")
    except Exception:
        return None


def get_cache_meta(liga_str: str) -> Optional[dict]:
    """Returns {'last_game_date': ..., 'updated_at': ...} or None if no entry."""
    entry = _load_raw().get(liga_str)
    if not entry:
        return None
    return {
        "last_game_date": entry.get("last_game_date"),
        "updated_at": entry.get("updated_at"),
    }


def is_stale(liga_str: str) -> bool:
    """True only when a cache entry exists AND historico.csv has newer games."""
    entry = _load_raw().get(liga_str)
    if not entry:
        return False
    cached_date = entry.get("last_game_date")
    if not cached_date:
        return True
    current = historico_last_date(liga_str)
    return bool(current and current > cached_date)


_DATAFRAME_FIELDS = ("home_table_full", "away_table_full")


def _serialize_data(data: dict) -> dict:
    """Converts DataFrame fields to list-of-records for JSON serialisation."""
    out = {}
    for k, v in data.items():
        if k in _DATAFRAME_FIELDS and hasattr(v, "to_dict"):
            out[k] = v.to_dict(orient="records")
        else:
            out[k] = v
    return out


def _deserialize_data(data: dict) -> dict:
    """Restores DataFrame fields from list-of-records after JSON deserialisation."""
    out = {}
    for k, v in data.items():
        if k in _DATAFRAME_FIELDS and isinstance(v, list):
            out[k] = pd.DataFrame(v)
        else:
            out[k] = v
    return out


def save_stats(liga_str: str, data: dict) -> None:
    """Persists the computed stats dict alongside the current last_game_date."""
    raw = _load_raw()
    raw[liga_str] = {
        "last_game_date": historico_last_date(liga_str),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "data": _serialize_data(data),
    }
    _save_raw(raw)


def load_cached_stats(liga_str: str) -> Optional[dict]:
    """Returns the cached stats dict for a liga, or None if not cached."""
    entry = _load_raw().get(liga_str)
    if not entry:
        return None
    raw_data = entry.get("data")
    return _deserialize_data(raw_data) if raw_data else None


def rebuild_for_liga(liga_str: str) -> dict:
    """Computes stats via stats_engine, saves to cache, returns the data dict."""
    from utils.stats_engine import compute_league_stats
    data = compute_league_stats(liga_str)
    save_stats(liga_str, data)
    return data
