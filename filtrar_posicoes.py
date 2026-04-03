"""
filtrar_posicoes.py
-------------------
Filters posicoes.csv keeping only rows where the team played a match
in historico.csv during the correct block for that matchday.

Block A — matchday ends on Fri/Sat/Sun/Mon → window: preceding Friday → data_fim_matchday
Block B — matchday ends on Tue/Wed/Thu     → window: preceding Tuesday → data_fim_matchday

Output: data/posicoes.csv  (overwrites with filtered rows, same columns)
"""

import pandas as pd
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent
POSICOES_PATH  = BASE_DIR / "data" / "posicoes.csv"
HISTORICO_PATH = BASE_DIR / "data" / "historico.csv"
OUTPUT_PATH    = BASE_DIR / "data" / "posicoes.csv"

# Block A: Fri=4, Sat=5, Sun=6, Mon=0
BLOCK_A = {4, 5, 6, 0}


def block_window(date: pd.Timestamp) -> tuple[str, pd.Timestamp, pd.Timestamp]:
    """Return (bloco, window_start, window_end) for a given data_fim_matchday."""
    wd = date.weekday()  # Mon=0 ... Sun=6
    if wd in BLOCK_A:
        days_since_fri = (wd - 4) % 7
        return "A", date - timedelta(days=days_since_fri), date
    else:
        days_since_tue = (wd - 1) % 7
        return "B", date - timedelta(days=days_since_tue), date


def main():
    posicoes  = pd.read_csv(POSICOES_PATH)
    historico = pd.read_csv(HISTORICO_PATH)

    posicoes["data_fim_matchday"] = pd.to_datetime(posicoes["data_fim_matchday"])
    historico["data"] = pd.to_datetime(historico["data"])

    kept_rows = []
    for _, row in posicoes.iterrows():
        bloco, w_start, w_end = block_window(row["data_fim_matchday"])

        mask = (
            (historico["liga"] == row["liga"])
            & (historico["data"] >= w_start)
            & (historico["data"] <= w_end)
            & ((historico["casa"] == row["time"]) | (historico["fora"] == row["time"]))
        )
        matches = historico[mask]

        if not matches.empty:
            kept_rows.append(row.to_dict())

    result = pd.DataFrame(kept_rows)
    result["data_fim_matchday"] = result["data_fim_matchday"].dt.strftime("%Y-%m-%d")
    result.to_csv(OUTPUT_PATH, index=False)

    removed = len(posicoes) - len(result)
    print(f"Original : {len(posicoes):,} rows")
    print(f"Filtered : {len(result):,} rows")
    print(f"Removed  : {removed:,} rows")
    print(f"Saved to : {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
