#!/usr/bin/env python3
"""
Teste unitário de geração de imagem de placar da Premier League.

Usa as funções e configurações reais de app.py (desenhar_placar,
obter_config_template, escudos, fontes) em vez de duplicá-las.

Configure as variáveis na seção CONFIGURAÇÕES DO TESTE e execute:
    python scripts/test_placar_pl.py

A imagem gerada é salva como test_output_pl.png na raiz do projeto.
"""

import logging
import os
import sys

# Garante que o script funciona a partir da raiz do projeto
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

# Silencia os avisos "missing ScriptRunContext" do Streamlit em bare mode
logging.getLogger("streamlit").setLevel(logging.ERROR)
for _name in list(logging.Logger.manager.loggerDict):
    if _name.startswith("streamlit"):
        logging.getLogger(_name).setLevel(logging.ERROR)

from app import desenhar_placar  # noqa: E402

# ── CONFIGURAÇÕES DO TESTE ────────────────────────────────────────────────────

TIME_CASA       = "Manchester United"
TIME_FORA       = "Manchester City"
PLACAR          = "2-1"
MARCADORES_CASA = "Bukayo Saka 34'\nKai Havertz 67'"
MARCADORES_FORA = "Ollie Watkins 12'"

# Caminho para foto de fundo (None = sem foto)
FOTO_FUNDO      = "ARSAVL.png"
# "Esquerda", "Centro", "Direita" ou um número de 0 a 100
ALINHAMENTO     = "Centro"

# Template a usar (mesmo caminho que o app monta: TEMPLATE_DIR + arquivo)
TEMPLATE        = "templates/premierleague.png"

# Arquivo de saída
SAIDA           = "test_output_pl.png"

# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Template : {TEMPLATE}")
    print(f"Times    : {TIME_CASA} vs {TIME_FORA}")
    print(f"Placar   : {PLACAR}")
    print(f"Foto     : {FOTO_FUNDO or '(nenhuma)'}")
    print()

    img = desenhar_placar(
        template_path=TEMPLATE,
        escudo_casa=TIME_CASA,
        escudo_fora=TIME_FORA,
        placar_texto=PLACAR,
        marcadores_casa=MARCADORES_CASA,
        marcadores_fora=MARCADORES_FORA,
        background=FOTO_FUNDO,
        alinhamento=ALINHAMENTO,
    )

    img.save(SAIDA)
    print(f"Imagem salva em: {os.path.abspath(SAIDA)}")
