#!/usr/bin/env python3
"""
Teste de geração das imagens de rodada e tabela da Championship, League One
e League Two com uma rodada fictícia (12 jogos, todos os 24 times).

A rodada é montada a partir dos times de data/tabelas/<liga>.txt, pareados
na ordem do arquivo, com placares variados para cobrir vitória, empate e
derrota.

NÃO grava nada em data/ — a tabela é carregada em memória, atualizada e
usada apenas para gerar a imagem. Ao final confirma que cada
data/tabelas/<liga>.txt continua idêntico.
"""

import json
import os
import sys

ROOT = "/home/alextorres/Desktop/BBI/Codigos/bbi-placares"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from utils.results_parser import ResultsParser
from utils.table_processor import TableProcessor
from utils.image_generator import ImageGenerator

LIGAS = ["championship", "leagueone", "leaguetwo"]
NUMERO_RODADA = 1

# Mesmas notas de penalidade que o app aplica em compute_updated_table()
PENALTY_NOTES = {
    "championship": {
        "Southampton": "Southampton perdeu 4 pontos por Spygate.",
    },
}

# Placares fictícios, um por jogo (12 jogos por rodada)
PLACARES = [(3, 1), (2, 2), (1, 0), (0, 3), (2, 1), (1, 1),
            (4, 0), (0, 0), (2, 3), (1, 2), (5, 1), (0, 1)]


def abreviacoes():
    """Mapa nome completo -> abreviação de 3 letras"""
    with open("config/team_abbreviations.json", encoding="utf-8") as f:
        ab = json.load(f)
    rev = {}
    for sigla, nome in ab.items():
        rev.setdefault(nome, sigla)
    return rev


def times_da_liga(liga):
    """Nomes dos times na ordem do arquivo de tabela"""
    with open(f"data/tabelas/{liga}.txt", encoding="utf-8") as f:
        linhas = f.read().strip().split("\n")
    return [linha.rsplit(" ", 8)[0] for linha in linhas]


def monta_rodada(liga, rev):
    """Gera as linhas de resultado (ex.: 'BIR 3-1 BLB') cobrindo todos os times"""
    times = times_da_liga(liga)
    if len(times) != 24:
        print(f"{liga}: esperados 24 times, encontrados {len(times)}")
        sys.exit(1)

    linhas = []
    for idx in range(0, 24, 2):
        casa, fora = times[idx], times[idx + 1]
        gols_casa, gols_fora = PLACARES[idx // 2]
        linhas.append(f"{rev[casa]} {gols_casa}-{gols_fora} {rev[fora]}")
    return linhas


rev = abreviacoes()
parser = ResultsParser()
generator = ImageGenerator()

for liga in LIGAS:
    print(f"\n── {liga} ─────────────────────────────────────────────")

    # ── Parse ────────────────────────────────────────────────────────────────
    resultados = []
    for linha in monta_rodada(liga, rev):
        r = parser.parse_single_result(linha)
        if r is None:
            print(f"FALHA ao parsear: {linha!r}")
            sys.exit(1)
        resultados.append(r)
    print(f"{len(resultados)} resultados parseados")

    times = [r['home_team'] for r in resultados] + [r['away_team'] for r in resultados]
    assert len(times) == 24 and len(set(times)) == 24, f"{liga}: rodada não cobre os 24 times"

    # ── Imagem da rodada ─────────────────────────────────────────────────────
    img_rodada = generator.generate_results_image(
        league=liga, results=resultados,
        round_number=NUMERO_RODADA, is_postponed=False,
    )
    rodada_path = os.path.join(OUT_DIR, f"teste_{liga}_rodada.png")
    img_rodada.save(rodada_path)
    print(f"rodada size={img_rodada.size} -> {rodada_path}")

    # ── Tabela atualizada (somente em memória) ───────────────────────────────
    processor = TableProcessor()
    with open(f"data/tabelas/{liga}.txt", encoding="utf-8") as f:
        tabela_original = f.read()
    processor.load_from_text(tabela_original)
    processor.update_with_multiple_results(resultados)
    processor.sort_table()

    notas = PENALTY_NOTES.get(liga, {})
    table_data = [{
        'name': t.name, 'position': t.position, 'games': t.games,
        'wins': t.wins, 'draws': t.draws, 'losses': t.losses,
        'goals_for': t.goals_for, 'goals_against': t.goals_against,
        'goal_difference': t.goal_difference, 'points': t.points,
        'penalty_note': notas.get(t.name),
    } for t in processor.teams]

    confirmations = {pos: {'champion': False, 'promoted': False, 'playoffs': False,
                           'relegated': False} for pos in range(1, 25)}

    img_tabela = generator.generate_table_image(
        league=liga, table_data=table_data,
        confirmations=confirmations, table_mode=None,
        round_number=NUMERO_RODADA,
    )
    tabela_path = os.path.join(OUT_DIR, f"teste_{liga}_tabela.png")
    img_tabela.save(tabela_path)
    print(f"tabela size={img_tabela.size} -> {tabela_path}")

    # ── Verificação: base de verdade intocada ────────────────────────────────
    with open(f"data/tabelas/{liga}.txt", encoding="utf-8") as f:
        assert f.read() == tabela_original, f"ARQUIVO {liga}.txt FOI MODIFICADO!"
    print(f"OK: data/tabelas/{liga}.txt intocado.")
