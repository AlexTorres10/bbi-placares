#!/usr/bin/env python3
"""
Gera os arquivos data/tabelas/<liga>.txt zerados para a nova temporada,
usando como fonte de times os PNGs de cada pasta de escudos.

Cada linha fica no formato esperado por TableProcessor:
    Nome do Time J V E D GP GC SG P   (todos os campos = 0)

Times em ordem alfabética.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# liga (nome do .txt) -> pasta de escudos
LIGAS = {
    "premierleague": "escudos-pl",
    "championship":  "escudos-ch",
    "leagueone":     "escudos-l1",
    "leaguetwo":     "escudos-l2",
    "nationalleague": "escudos-nl",
}


def times_da_pasta(pasta: str) -> list:
    caminho = os.path.join(ROOT, pasta)
    times = [f[:-4] for f in os.listdir(caminho) if f.lower().endswith(".png")]
    return sorted(times)


def main():
    for liga, pasta in LIGAS.items():
        times = times_da_pasta(pasta)
        linhas = [f"{t} 0 0 0 0 0 0 0 0" for t in times]
        destino = os.path.join(ROOT, "data", "tabelas", f"{liga}.txt")
        with open(destino, "w", encoding="utf-8") as f:
            f.write("\n".join(linhas) + "\n")
        print(f"{liga}: {len(times)} times -> {destino}")


if __name__ == "__main__":
    main()
