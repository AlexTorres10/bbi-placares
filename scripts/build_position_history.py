#!/usr/bin/env python3
"""
Retroactive population of data/posicoes.csv from data/historico.csv.

Run from the project root:
    python scripts/build_position_history.py

The script:
  1. Deletes the existing posicoes.csv so stale data is never kept.
  2. Prints all detected matchdays for each liga for visual validation.
  3. Simulates the accumulated table at every matchday and writes
     a position record for every team (even those that haven't played yet).
"""
import os
import sys

# Ensure project root is on the path so utils/ can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.position_history import (
    POSICOES_CSV,
    detect_matchdays,
    compute_table_at_matchday,
    append_matchday_positions,
)

LIGAS = [
    "Premier League",
    "Championship",
    "League One",
    "League Two",
    "National League",
]


def _delete_posicoes_csv() -> None:
    if os.path.exists(POSICOES_CSV):
        bak = POSICOES_CSV + ".bak"
        os.rename(POSICOES_CSV, bak)
        print(f"Arquivo existente renomeado para {bak}")
    # Also remove any schema-migration .bak left by _ensure_new_schema
    old_bak = POSICOES_CSV + ".bak"
    # (already handled above if it existed)


def main() -> None:
    _delete_posicoes_csv()

    total_matchdays = 0
    total_rows = 0

    for liga in LIGAS:
        print(f"\n{'=' * 60}")
        print(f"Liga: {liga}")

        matchday_map = detect_matchdays(liga)
        if not matchday_map:
            print("  Nenhum dado encontrado.")
            continue

        # ── Print all detected matchdays for visual validation ──────────
        print(f"  {len(matchday_map)} matchdays detectados:")
        for md in sorted(matchday_map.keys()):
            dates = matchday_map[md]
            date_range = (
                dates[0] if len(dates) == 1
                else f"{dates[0]} → {dates[-1]}"
            )
            print(f"    Rodada {md:3d}: {date_range}  ({len(dates)} dia(s))")

        # ── Compute and save positions ───────────────────────────────────
        print()
        liga_matchdays = 0
        liga_rows = 0

        for md in sorted(matchday_map.keys()):
            dates = matchday_map[md]
            data_fim = sorted(dates)[-1]

            positions = compute_table_at_matchday(liga, md, matchday_map)
            if not positions:
                print(f"  Rodada {md:3d} | sem dados, ignorado")
                continue

            added = append_matchday_positions(liga, positions, data_fim)
            print(
                f"  Rodada {md:3d} | data_fim: {data_fim} | "
                f"{added} times registrados"
            )
            if added > 0:
                liga_matchdays += 1
                liga_rows += added

        print(
            f"  → {liga_matchdays} rodadas inseridas, "
            f"{liga_rows} registros adicionados"
        )
        total_matchdays += liga_matchdays
        total_rows += liga_rows

    print(f"\n{'=' * 60}")
    print(
        f"TOTAL: {total_matchdays} rodadas e {total_rows} registros inseridos."
    )


if __name__ == "__main__":
    main()
