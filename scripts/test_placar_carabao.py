#!/usr/bin/env python3
"""
Teste de geração das imagens da Carabao Cup (EFL Cup).

A fase fictícia tem 12 jogos e mistura os três tipos de resultado que o
ResultsParser reconhece com placar:
  - normal:       "ARS 2-1 CHE"
  - prorrogação:  "PNE 0-1(pro) WIG"   -> "Finalizado após prorrogação"
  - pênaltis:     "WRE 3-3(4-5) NFO"   -> "Pênaltis: 4-5"

Segue o mesmo caminho do app: ResultsParser -> CupGenerator.generate_cup_images().
Não grava nada em data/.
"""

import os
import sys

ROOT = "/home/alextorres/Desktop/BBI/Codigos/bbi-placares"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from utils.results_parser import ResultsParser
from utils.cup_generator import CupGenerator

TITULO_FASE = "3ª FASE - RESULTADOS"

# 12 jogos: 6 normais, 3 após prorrogação, 3 por pênaltis
FASE_FICTICIA = """\
ARS 2-1 CHE
MCI 3-0 BLP
LIV 1-0 PNE
MUN 4-2 BAR
TOT 2-0 CAM
NEW 1-0 EXE
AVL 2-1(pro) SUN
BOU 1-0(pro) OXF
EVE 3-2(pro) POR
WRE 3-3(4-5) NFO
LEE 1-1(2-4) BRE
FUL 0-0(5-3) SWA
"""

parser = ResultsParser()
resultados = []
for linha in FASE_FICTICIA.strip().split("\n"):
    r = parser.parse_single_result(linha.strip())
    if r is None:
        print(f"FALHA ao parsear: {linha!r}")
        sys.exit(1)
    resultados.append(r)

por_status = {}
for r in resultados:
    por_status.setdefault(r['status'], []).append(r)
print(f"{len(resultados)} resultados parseados: "
      + ", ".join(f"{k}={len(v)}" for k, v in sorted(por_status.items())))

for r in resultados:
    if r.get('extra_info'):
        print(f"  {r['home_abbr']} {r['home_score']}-{r['away_score']} {r['away_abbr']}"
              f"  -> {r['extra_info']}")

generator = CupGenerator()
images = generator.generate_cup_images(
    cup="eflcup", results=resultados, title=TITULO_FASE,
)

for idx, img in enumerate(images, start=1):
    sufixo = "" if len(images) == 1 else f"-{idx}"
    path = os.path.join(OUT_DIR, f"teste_carabao{sufixo}.png")
    img.save(path)
    print(f"imagem {idx}/{len(images)} size={img.size} -> {path}")
