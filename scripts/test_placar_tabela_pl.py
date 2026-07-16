#!/usr/bin/env python3
"""
Teste de geração das imagens de rodada e tabela da Premier League
com uma rodada fictícia (10 jogos, todos os 20 times).

NÃO grava nada em data/ — a tabela é carregada em memória, atualizada
e usada apenas para gerar a imagem. Ao final confirma que
data/tabelas/premierleague.txt continua idêntico.
"""

import os
import sys

ROOT = "/home/alextorres/Desktop/BBI/Codigos/bbi-placares"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from utils.results_parser import ResultsParser
from utils.table_processor import TableProcessor
from utils.image_generator import ImageGenerator

# Rodada fictícia (todos os 20 times, 10 jogos)
RODADA_FICTICIA = """\
ARS 3-1 CHE
MCI 2-2 LIV
MUN 1-0 TOT
AVL 2-1 NEW
BOU 0-0 BHA
SUN 1-2 EVE
BRE 4-2 COV
FUL 2-3 CRY
LEE 1-1 NFO
HUL 0-2 IPS
"""

NUMERO_RODADA = 1

# ── Parse ────────────────────────────────────────────────────────────────────
parser = ResultsParser()
resultados = []
for line in RODADA_FICTICIA.strip().split("\n"):
    r = parser.parse_single_result(line.strip())
    if r is None:
        print(f"FALHA ao parsear: {line!r}")
        sys.exit(1)
    resultados.append(r)
print(f"{len(resultados)} resultados parseados")

times = [r['home_team'] for r in resultados] + [r['away_team'] for r in resultados]
assert len(times) == 20 and len(set(times)) == 20, "rodada não cobre os 20 times"

generator = ImageGenerator()

# ── Imagem da rodada ─────────────────────────────────────────────────────────
img_rodada = generator.generate_results_image(
    league="premierleague", results=resultados,
    round_number=NUMERO_RODADA, is_postponed=False,
)
rodada_path = os.path.join(OUT_DIR, "teste_pl_rodada.png")
img_rodada.save(rodada_path)
print(f"rodada size={img_rodada.size} -> {rodada_path}")

# ── Tabela atualizada (somente em memória) ───────────────────────────────────
processor = TableProcessor()
with open("data/tabelas/premierleague.txt", "r", encoding="utf-8") as f:
    tabela_original = f.read()
processor.load_from_text(tabela_original)
processor.update_with_multiple_results(resultados)
processor.sort_table()

table_data = [{
    'name': t.name, 'position': t.position, 'games': t.games,
    'wins': t.wins, 'draws': t.draws, 'losses': t.losses,
    'goals_for': t.goals_for, 'goals_against': t.goals_against,
    'goal_difference': t.goal_difference, 'points': t.points,
} for t in processor.teams]

confirmations = {pos: {'champion': False, 'ucl': False, 'uel': False,
                       'uecl': False, 'relegated': False} for pos in range(1, 21)}

img_tabela = generator.generate_table_image(
    league="premierleague", table_data=table_data,
    confirmations=confirmations, table_mode=None,
    round_number=NUMERO_RODADA,
)
tabela_path = os.path.join(OUT_DIR, "teste_pl_tabela.png")
img_tabela.save(tabela_path)
print(f"tabela size={img_tabela.size} -> {tabela_path}")

# ── Verificação: base de verdade intocada ────────────────────────────────────
with open("data/tabelas/premierleague.txt", "r", encoding="utf-8") as f:
    assert f.read() == tabela_original, "ARQUIVO DA TABELA FOI MODIFICADO!"
print("OK: data/tabelas/premierleague.txt intocado.")
