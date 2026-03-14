import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import re
import json
import sys
import base64
from typing import Dict, List, Optional
from utils.cup_generator import CupGenerator
from streamlit_clickable_images import clickable_images

# Adicionar utils ao path
sys.path.append(os.path.dirname(__file__))

from datetime import date, timedelta
import csv
import plotly.graph_objects as go

from utils.results_parser import ResultsParser
from utils.table_processor import TableProcessor
from utils.image_generator import ImageGenerator
from utils.github_handler import GitHubHandler
from utils.news_generator import NewsGenerator
from utils.table_validator import TableValidator
from utils.stats_engine import compute_league_stats
from utils.position_history import (
    detect_matchdays,
    compute_table_at_matchday,
    append_matchday_positions,
    compute_position_delta,
    POSICOES_CSV,
)

st.set_page_config(
    page_title="Gerador de Conteúdo BBI",
    page_icon="bbi.png",  # ← Seu favicon
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================================
# CONFIGURAÇÕES GLOBAIS
# ============================================================================

TEMPLATE_DIR = "templates"

TEMPLATE_LABELS = {
    "premierleague.png": "Premier League",
    "ucl.png": "Champions League",
    "uel.png": "Europa League",
    "uecl.png": "Conference League",
    "facup.png": "FA Cup",
    "eflcup.png": "EFL Cup",
    "inglaterra.png": "Seleção Inglesa",
    "championship.png": "Championship",
    "leagueone.png": "League One",
    "leaguetwo.png": "League Two",
}

TEMPLATE_ORDER = [
    "premierleague.png",
    "ucl.png",
    "uel.png",
    "uecl.png",
    "facup.png",
    "eflcup.png",
    "inglaterra.png",
    "championship.png",
    "leagueone.png",
    "leaguetwo.png"
]

INGLES_UCL = ["Arsenal", "Manchester City", "Liverpool", "Chelsea", "Newcastle United", "Tottenham"]
INGLES_UEL = ["Aston Villa", "Nottingham Forest"]
INGLES_UECL = ["Crystal Palace"]

LIGA_DISPLAY_NAMES = {
    "premierleague": "Premier League",
    "championship":  "Championship",
    "leagueone":     "League One",
    "leaguetwo":     "League Two",
    "nationalleague":"National League",
}

@st.cache_data(ttl=300)  # Cache por 5 minutos
def carregar_tabela_github(liga: str):
    """
    Carrega tabela do GitHub com cache e fallback local
    
    Returns:
        (content: str, sha: str, source: str)
    """
    # Tentar carregar do GitHub primeiro
    try:
        if 'GITHUB_TOKEN' in st.secrets and 'GITHUB_REPO' in st.secrets:
            github = GitHubHandler(
                token=st.secrets['GITHUB_TOKEN'],
                repo=st.secrets['GITHUB_REPO']
            )
            content, sha = github.get_file(f"data/tabelas/{liga}.txt")
            if content:
                return content, sha, 'github'
    except Exception as e:
        print(f"Erro ao carregar do GitHub: {e}")
    
    # Fallback: arquivo local
    try:
        with open(f"data/tabelas/{liga}.txt", 'r', encoding='utf-8') as f:
            return f.read(), None, 'local'
    except Exception as e:
        return None, None, 'error'

def carregar_escudos(template_path):
    template_name = os.path.basename(template_path).lower()
    
    if "inglaterra" in template_name:
        if os.path.exists("selecoes"):
            return sorted([f[:-4] for f in os.listdir("selecoes") if f.endswith(".png")])
        return []
    
    if "ucl" in template_name:
        ingleses_ucl = []
        if os.path.exists("escudos-pl"):
            todos_pl = [f[:-4] for f in os.listdir("escudos-pl") if f.endswith(".png")]
            ingleses_ucl = [nome for nome in INGLES_UCL if nome in todos_pl]
        
        europeus_ucl = []
        if os.path.exists("escudos-ucl"):
            europeus_ucl = sorted([f[:-4] for f in os.listdir("escudos-ucl") if f.endswith(".png")])
        
        return ingleses_ucl + europeus_ucl
    
    if "uel" in template_name:
        ingleses_uel = []
        if os.path.exists("escudos-pl"):
            todos_pl = [f[:-4] for f in os.listdir("escudos-pl") if f.endswith(".png")]
            ingleses_uel = [nome for nome in INGLES_UEL if nome in todos_pl]
        
        europeus_uel = []
        if os.path.exists("escudos-uel"):
            europeus_uel = sorted([f[:-4] for f in os.listdir("escudos-uel") if f.endswith(".png")])
        
        return ingleses_uel + europeus_uel
    
    if "uecl" in template_name:
        ingleses_uecl = []
        if os.path.exists("escudos-pl"):
            todos_pl = [f[:-4] for f in os.listdir("escudos-pl") if f.endswith(".png")]
            ingleses_uecl = [nome for nome in INGLES_UECL if nome in todos_pl]
        
        europeus_uecl = []
        if os.path.exists("escudos-uecl"):
            europeus_uecl = sorted([f[:-4] for f in os.listdir("escudos-uecl") if f.endswith(".png")])
        
        return ingleses_uecl + europeus_uecl
    
    if "premier" in template_name:
        if os.path.exists("escudos-pl"):
            return sorted([f[:-4] for f in os.listdir("escudos-pl") if f.endswith(".png")])
        return []
    
    if "championship" in template_name:
        if os.path.exists("escudos-ch"):
            return sorted([f[:-4] for f in os.listdir("escudos-ch") if f.endswith(".png")])
        return []
    
    if "leagueone" in template_name:
        if os.path.exists("escudos-l1"):
            return sorted([f[:-4] for f in os.listdir("escudos-l1") if f.endswith(".png")])
        return []
    
    if "leaguetwo" in template_name:
        if os.path.exists("escudos-l2"):
            return sorted([f[:-4] for f in os.listdir("escudos-l2") if f.endswith(".png")])
        return []
    
    if "eflcup" in template_name:
        leagues = ['escudos-pl', 'escudos-ch', 'escudos-l1', 'escudos-l2']
        times_total = []
        for div in leagues:
            if os.path.exists(div):
                times = sorted([f[:-4] for f in os.listdir(div) if f.endswith(".png")])
                times_total.extend(times)
        return times_total

    if "facup" in template_name:
        leagues = ['escudos-pl', 'escudos-ch', 'escudos-l1', 'escudos-l2', 'escudos-nl', 'escudos-nonleague']
        times_total = []
        for div in leagues:
            if os.path.exists(div):
                times = sorted([f[:-4] for f in os.listdir(div) if f.endswith(".png")])
                times_total.extend(times)
        return times_total
    
    return []


def obter_fontes_por_template(template_path):
    nome = os.path.splitext(os.path.basename(template_path))[0].lower()

    if "premier" in nome:
        return ("fontes/premierleague.ttf", "fontes/premierleague-bold.ttf")
    elif "championship" in nome or "efl" in nome or "league" in nome:
        return ("fontes/efl.otf", "fontes/efl-bold.otf")
    elif "facup" in nome:
        return ("fontes/facup.ttf", "fontes/facup-bold.ttf")
    elif "ucl" in nome:
        return ("fontes/ucl.ttf", "fontes/ucl-bold.ttf")
    elif "uel" in nome:
        return ("fontes/uel.ttf", "fontes/uel-bold.ttf")
    elif "inglaterra" in nome:
        return ("fontes/ing.ttf", "fontes/ing.ttf")
    else:
        return ("fontes/FontePlacar.ttf", "fontes/FontePlacar.ttf")


def redimensionar_escudo(filepath, target_size=(100, 100)):
    escudo = Image.open(filepath).convert("RGBA")
    escudo.thumbnail(target_size, Image.LANCZOS)

    canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
    pos_x = (target_size[0] - escudo.width) // 2
    pos_y = (target_size[1] - escudo.height) // 2
    canvas.paste(escudo, (pos_x, pos_y), escudo)

    return canvas



def obter_config_template(template_path):
    nome = os.path.splitext(os.path.basename(template_path))[0].lower()
    
    if "premier" in nome:
        h = 913
        return {
            "fonte_normal": "fontes/premierleague.otf",
            "fonte_bold": "fontes/premierleague-bold.otf",
            "escudo_tamanho": (60, 60),
            "pos_home": (121, h),
            "pos_away": (-181, h), # valor negativo será tratado como relativo ao width,
            "cor_texto": "#3b0643",
            "cor_texto_placar": "#3b0643",
            "pos_nome_home": (334, h+18),  # Posição absoluta
            "pos_nome_away": (742, h+18),
            "pos_placar": 922,
        }
    elif "championship" in nome or "efl" in nome or "league" in nome:
        h = 920
        return {
            "fonte_normal": "fontes/efl.otf",
            "fonte_bold": "fontes/efl-bold.otf",
            "escudo_tamanho": (50, 50),
            "pos_home": (130, h),
            "pos_away": (-180, h),
            "cor_texto": "#3241a1",
            "cor_texto_placar": "white",
            "pos_nome_home": (336, h),  # Posição absoluta
            "pos_nome_away": (739, h),
            "pos_placar": 923,
        }
    elif "facup" in nome:
        h = 914
        return {
            "fonte_normal": "fontes/facup.otf",
            "fonte_bold": "fontes/facup-bold.otf",
            "escudo_tamanho": (60, 60),
            "pos_home": (121, h),
            "pos_away": (-181, h),
            "cor_texto_times": "#383b38",
            "cor_texto": "white",
            "cor_texto_placar": "white",
            "pos_nome_home": (336, h+18),  # Posição absoluta
            "pos_nome_away": (742, h+18),
            "pos_placar": 920,
        }
    elif "ucl" in nome:
        h = 880
        return {
            "fonte_normal": "fontes/ucl.ttf",
            "fonte_bold": "fontes/ucl-bold.ttf",
            "escudo_tamanho": (120, 120),
            "pos_home": (70, h),
            "pos_away": (-180, h),
            "cor_texto": "white",
            "cor_texto_placar": "white",
            "pos_nome_home": (317, h+45),  # Posição absoluta
            "pos_nome_away": (758, h+45),
            "pos_placar": 915,
        }
    elif "uel" in nome or "uecl" in nome:
        h = 912
        return {
            "fonte_normal": "fontes/uel.ttf",
            "fonte_bold": "fontes/uel-bold.ttf",
            "escudo_tamanho": (60, 60),
            "pos_home": (120, h),
            "pos_away": (-180, h),
            "cor_texto": "white",
            "cor_texto_placar": "black",
            "pos_nome_home": (335, h+15),  # Posição absoluta
            "pos_nome_away": (743, h+15),  # Posição absoluta
            "pos_placar": 915,
        }
    elif "inglaterra" in nome:
        h = 915
        return {
            "fonte_normal": "fontes/ing.ttf",
            "fonte_bold": "fontes/ing.ttf",
            "escudo_tamanho": (60, 60),
            "pos_home": (120, h),
            "pos_away": (-180, h),
            "cor_texto": "#0c113c",
            "cor_texto_placar": "white",
            "pos_nome_home": (330, h+17),  # Posição absoluta
            "pos_nome_away": (760, h+17),
            "pos_placar": 920,
        }
    else:
        return {
            "fonte_normal": "fontes/facup.ttf",
            "fonte_bold": "fontes/facup-bold.ttf",
            "escudo_tamanho": (100, 100),
            "pos_home": (50, h),
            "pos_away": (-150, h),
            "cor_texto": "white",
            "cor_texto_placar": "white",
            "pos_nome_home": (360, 870),  # Posição absoluta
            "pos_nome_away": (-360, 870),
            "pos_placar": 915,
        }



def obter_escudo_path(team_name, template_path=None):
    """Busca o escudo em múltiplas pastas"""
    pastas = ["escudos-pl", "escudos-ch", "escudos-l1", "escudos-l2", 
              "escudos-ucl", "escudos-uel", "escudos-uecl", "selecoes", "escudos-nl", "escudos-nonleague"]
    
    for pasta in pastas:
        caminho = os.path.join(pasta, f"{team_name}.png")
        if os.path.exists(caminho):
            return caminho
    
    return None

def apply_bottom_gradient(image: Image.Image, intensity: float = 0.9) -> Image.Image:
        """Cria o efeito de sombra na parte inferior para destacar o texto"""
        width, height = image.size
        gradient = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(gradient)
        start_y = int(height * 0.4) # Começa o gradiente um pouco acima do meio
        for y in range(start_y, height):
            alpha = int(255 * intensity * ((y - start_y) / (height - start_y)))
            draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
        return Image.alpha_composite(image, gradient)

def desenhar_placar(template_path, escudo_casa, escudo_fora, placar_texto, marcadores_casa, marcadores_fora, background=None, alinhamento="Centro"):
    base = Image.open(template_path).convert("RGBA")

    if background:
        bg_raw = Image.open(background).convert("RGBA")
        scale_w = base.width / bg_raw.width
        scale_h = base.height / bg_raw.height
        scale = max(scale_w, scale_h)
        new_width = int(bg_raw.width * scale)
        new_height = int(bg_raw.height * scale)
        bg_resized = bg_raw.resize((new_width, new_height), Image.LANCZOS)

        # Ajusta o recorte baseado no alinhamento
        if alinhamento == "Esquerda":
            left = 0
        elif alinhamento == "Direita":
            left = new_width - base.width
        else:  # Centro
            left = (new_width - base.width) // 2
        
        top = (new_height - base.height) // 2
        bg_cropped = bg_resized.crop((left, top, left + base.width, top + base.height))

        if 'championship' in template_path.lower() or 'efl' in template_path.lower() or "league" in template_path.lower():
                bg_cropped = apply_bottom_gradient(bg_cropped, intensity=0.9)

        final_img = Image.new("RGBA", bg_cropped.size, (0, 0, 0, 0))
        base_x = (bg_cropped.width - base.width) // 2
        base_y = (bg_cropped.height - base.height) // 2
        final_img.paste(bg_cropped, (0, 0))
        final_img.paste(base, (base_x, base_y), base)
        base = final_img

    # Configurações do template
    config = obter_config_template(template_path)
    path_lower = template_path.lower()

    if any(comp in path_lower for comp in ["uel", "uecl"]):
        fonte_normal = ImageFont.truetype(config["fonte_bold"], 28)
    else:
        fonte_normal = ImageFont.truetype(config["fonte_normal"], 32)
    fonte_bold = ImageFont.truetype(config["fonte_bold"], 48)
    fonte_pequena = ImageFont.truetype(config["fonte_normal"], 26)
    fonte_mais_pequena = ImageFont.truetype(config["fonte_normal"], 18)
    cor_texto = config["cor_texto"]
    cor_texto_placar = config["cor_texto_placar"]

    draw = ImageDraw.Draw(base)

    # Redimensionar escudos com proporção preservada
    escudo_home = redimensionar_escudo(obter_escudo_path(escudo_casa), config["escudo_tamanho"])
    escudo_away = redimensionar_escudo(obter_escudo_path(escudo_fora), config["escudo_tamanho"])

    # Posição dos escudos
    pos_home = config["pos_home"]
    pos_away_raw = config["pos_away"]
    pos_away = (
        base.width + pos_away_raw[0] if pos_away_raw[0] < 0 else pos_away_raw[0],
        pos_away_raw[1]
    )

    base.paste(escudo_home, pos_home, escudo_home)
    base.paste(escudo_away, pos_away, escudo_away)
    europeu = any(comp in path_lower for comp in ["ucl", "uel", "uecl"])
    efl = any(comp in path_lower for comp in ["efl", "champ"])
    ing = any(comp in path_lower for comp in ["inglaterra"])

    # 🏷️ Nomes dos times
    for nome, pos_key in [(escudo_casa, "pos_nome_home"), (escudo_fora, "pos_nome_away")]:
        pos = config.get(pos_key)
        if not pos:
            continue
        
        x, y = pos
        if europeu and nome == "Nottingham Forest":
            nome = "Nott'm Forest"
        if europeu and nome == "Borussia Dortmund":
            nome = "Bor. Dortmund"
        if "facup" in path_lower and nome == "Queens Park Rangers":
            nome = "QPR"
        nome_maiusculo = nome.upper()

        # Decide a fonte
        fonte_usada = fonte_normal if any(comp in path_lower for comp in ["ucl", "uel", "uecl"]) else fonte_pequena

        # Mede e centraliza
        w_text = fonte_usada.getbbox(nome_maiusculo)[2] - fonte_usada.getbbox(nome_maiusculo)[0]
        x_centered = x - w_text // 2

        # Desenha
        if ing:
            draw.text((x_centered, y), nome_maiusculo, font=fonte_usada, fill=cor_texto)
        elif "facup" in path_lower:
            draw.text((x_centered, y), nome_maiusculo, font=fonte_usada, fill=config["cor_texto_times"])
        else:
            draw.text((x_centered, y), nome_maiusculo, font=fonte_usada, fill='white')


    # Placar principal centralizado
    placar = placar_texto.split('(')[0].strip()

    # Remove espaços ao redor de hífens
    placar = re.sub(r'\s*-\s*', '-', placar)

    # Agora, se for Premier League, aplicar estilo com espaços
    if "premier" in path_lower:
        placar = placar.replace('-', ' - ')  # estiliza com espaços
    w_placar = fonte_bold.getbbox(placar)[2] - fonte_bold.getbbox(placar)[0]
    draw.text(((base.width - w_placar) // 2, config["pos_placar"]), placar, font=fonte_bold, fill=cor_texto_placar)

    # Agregado ou pênaltis (centralizado)
    if '(' in placar_texto and ')' in placar_texto:
        conteudo = placar_texto.split('(')[1].replace(')', '').strip().lower()

        if "agr" in conteudo:
            label = "Agregado: "
            valor = conteudo.replace("agr.", "").replace("agr", "").strip()
        elif "pên" in conteudo:
            label = "Pênaltis: "
            valor = conteudo.replace("pên.", "").replace("pên", "").strip()
        elif "pen" in conteudo:
            label = "Pênaltis: "
            valor = conteudo.replace("pen.", "").replace("pen", "").strip()
        elif "pro" in conteudo:
            label = "Prorrogação"
            valor = ""
        else:
            label = ""
            valor = conteudo  # fallback

        agregado_texto = label + valor
        
        path_lower = template_path.lower()
        mais_pra_cima = any(comp in path_lower for comp in ["uel", "uecl", "efl", "championship"])

        y_agregado = 975 if mais_pra_cima else 985

        w_agr = fonte_mais_pequena.getbbox(agregado_texto)[2] - fonte_mais_pequena.getbbox(agregado_texto)[0]
        draw.text(((base.width - w_agr) // 2, y_agregado), agregado_texto, font=fonte_mais_pequena, fill=cor_texto)

    # 🟩 Marcadores
    espaco_linha = 34  # Aumente/diminua conforme necessário
    y_base = 990

    # Casa (alinhamento à esquerda)
    for i, linha in enumerate(marcadores_casa.split('\n')):
        if europeu:
            y_base = 1000
            linha = linha.upper()
            draw.text((140, y_base + i * espaco_linha), linha, font=fonte_pequena, fill=cor_texto)
        elif efl:
            y_base = 980
            draw.text((200, y_base + i * espaco_linha), linha, font=fonte_pequena, fill=cor_texto)
        elif ing:
            draw.text((200, y_base + i * espaco_linha), linha.upper(), font=fonte_pequena, fill=cor_texto)
        else:
            draw.text((200, y_base + i * espaco_linha), linha, font=fonte_pequena, fill=cor_texto)

    # Visitante (alinhado à direita)
    for i, linha in enumerate(marcadores_fora.split('\n')):
        if europeu:
            linha = linha.upper()
            w_linha = fonte_pequena.getbbox(linha)[2] - fonte_pequena.getbbox(linha)[0]
            draw.text((base.width - 140 - w_linha, y_base + i * espaco_linha), linha, font=fonte_pequena, fill=cor_texto)
        elif efl:
            w_linha = fonte_pequena.getbbox(linha)[2] - fonte_pequena.getbbox(linha)[0]
            y_base = 980
            draw.text((base.width - 200 - w_linha, y_base + i * espaco_linha), linha, font=fonte_pequena, fill=cor_texto)
        elif ing:
            linha = linha.upper()
            w_linha = fonte_pequena.getbbox(linha)[2] - fonte_pequena.getbbox(linha)[0]
            draw.text((base.width - 200 - w_linha, y_base + i * espaco_linha), linha, font=fonte_pequena, fill=cor_texto)

        else:
            w_linha = fonte_pequena.getbbox(linha)[2] - fonte_pequena.getbbox(linha)[0]
            draw.text((base.width - 200 - w_linha, y_base + i * espaco_linha), linha, font=fonte_pequena, fill=cor_texto)

    return base


# ============================================================================
# UTILITÁRIO: HISTÓRICO LOCAL
# ============================================================================

def is_already_in_historico(home_team: str, away_team: str, liga_str: str) -> bool:
    """Returns True if (home_team, away_team, liga_str) exists in data/historico.csv."""
    path = "data/historico.csv"
    if not os.path.exists(path):
        return False
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (row.get('casa') == home_team and
                    row.get('fora') == away_team and
                    row.get('liga') == liga_str):
                return True
    return False


def _append_to_historico(resultados: list, data_rodada, liga_str: str) -> dict:
    """
    Adiciona resultados finalizados a data/historico.csv.
    - Ignora partidas com mesmo placar já registrado.
    - Detecta conflito quando (casa, fora, liga) existe com placar diferente.
    Retorna {'added': int, 'conflicts': list}.
    """
    data_str = (data_rodada.strftime('%Y-%m-%d')
                if hasattr(data_rodada, 'strftime') else str(data_rodada))

    # Ler pares já registrados: (casa, fora, liga) → placar
    existing = {}
    historico_path = "data/historico.csv"
    if os.path.exists(historico_path):
        with open(historico_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing[(row['casa'], row['fora'], row['liga'])] = row['placar']

    new_rows = []
    conflicts = []
    for r in resultados:
        if r.get('status') not in ('normal', 'penalties', 'extra_time'):
            continue
        new_score = f"{r['home_score']}-{r['away_score']}"
        key = (r['home_team'], r['away_team'], liga_str)
        row_date = r.get('data', data_str)
        if key in existing:
            if existing[key] != new_score:
                conflicts.append({
                    'home_team': r['home_team'],
                    'away_team': r['away_team'],
                    'liga': liga_str,
                    'old_score': existing[key],
                    'new_score': new_score,
                    'date_str': row_date,
                })
            # same score → skip silently
            continue
        new_rows.append([r['home_team'], new_score, r['away_team'], row_date, liga_str])
        existing[key] = new_score  # evita duplicatas dentro do mesmo lote

    if new_rows:
        with open(historico_path, 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerows(new_rows)
    return {'added': len(new_rows), 'conflicts': conflicts}


def _update_historico_row(home_team: str, away_team: str, liga_str: str,
                          new_score: str, new_date_str: str):
    """Sobrescreve o placar (e data) de uma linha existente em historico.csv."""
    path = "data/historico.csv"
    rows = []
    fieldnames = None
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if (row['casa'] == home_team and row['fora'] == away_team
                    and row['liga'] == liga_str):
                row['placar'] = new_score
                row['data'] = new_date_str
            rows.append(row)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ============================================================================
# FUNÇÕES DE SNAPSHOT / POSIÇÕES
# ============================================================================

# Position history logic lives in utils/position_history.py.
# POSICOES_CSV and compute_position_delta are imported from there.


# ============================================================================
# FUNÇÕES DO MODO TABELA
# ============================================================================

def render_table_mode():
    """Renderiza o modo de geração de tabela com resultados"""
    st.header("📊 Gerar Tabela com Resultados")
    
    # Seleção da liga
    ligas_disponiveis = {
        "Premier League": "premierleague",
        "Championship": "championship",
        "League One": "leagueone",
        "League Two": "leaguetwo",
        "National League": "nationalleague"
    }
    
    liga_selecionada = st.selectbox(
        "Escolha a Liga",
        list(ligas_disponiveis.keys())
    )
    
    liga_key = ligas_disponiveis[liga_selecionada]
    
    st.divider()
    
    # Seção de resultados
    st.subheader("⚽ Inserir Resultados")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        resultados_texto = st.text_area(
            "Cole os resultados (um por linha)",
            placeholder="POR 1-0 SOU\nCOV 2-1 WAT\nHUL 0-0 NOR",
            height=150,
            help="Formato: ABV 1-0 XYZ (abreviação de 3 letras, espaço, placar, espaço, abreviação)"
        )
    
    with col2:
        tipo_rodada = st.radio(
            "Tipo",
            ["Rodada", "Jogos Atrasados"]
        )
        
        if tipo_rodada == "Rodada":
            try:
                # Carregar tabela para pegar número de jogos
                tabela_content, _, _ = carregar_tabela_github(liga_key)
                
                if tabela_content:
                    processor = TableProcessor()
                    processor.load_from_text(tabela_content)
                    
                    # Pegar time com mais jogos
                    max_jogos = max(team.games for team in processor.teams)
                    rodada_sugerida = max_jogos + 1
                else:
                    rodada_sugerida = 1
            except:
                rodada_sugerida = 1
            
            numero_rodada = st.number_input(
                "Nº Rodada",
                min_value=1,
                max_value=50,
                value=rodada_sugerida,  # ← Valor calculado automaticamente
                help=f"Rodada sugerida baseada na tabela atual: {rodada_sugerida}"
            )
        else:
            numero_rodada = None

        data_rodada = st.date_input(
            "Data da Rodada",
            value=date.today(),
            help="Data usada para registrar os resultados no histórico de estatísticas"
        )

    # Botão de processar
    if st.button("🔄 Processar Resultados", type="primary"):
        if not resultados_texto.strip():
            st.error("❌ Por favor, insira pelo menos um resultado!")
            return
        
        # Parse dos resultados com suporte a prefixo de data (-N dias)
        parser = ResultsParser()
        _prefix_re = re.compile(r'^(-\d+)\s+')
        resultados = []
        for _line in resultados_texto.strip().split('\n'):
            _line = _line.strip()
            if not _line:
                continue
            _m = _prefix_re.match(_line)
            if _m:
                _days_offset = int(_m.group(1))
                _resolved_date = data_rodada + timedelta(days=_days_offset)
                _clean_line = _line[_m.end():]
            else:
                _resolved_date = data_rodada
                _clean_line = _line
            _result = parser.parse_single_result(_clean_line)
            if _result:
                _result['data'] = _resolved_date.strftime('%Y-%m-%d')
                resultados.append(_result)

        if not resultados:
            st.error("❌ Nenhum resultado válido encontrado! Verifique o formato.")
            return
        
        # Mostrar resultados parseados
        st.success(f"✅ {len(resultados)} resultado(s) processado(s)!")
        
        with st.expander("Ver resultados parseados"):
            for r in resultados:
                status = r.get('status', 'normal')
                _date_label = ""
                if 'data' in r:
                    from datetime import date as _date_cls
                    _d = _date_cls.fromisoformat(r['data'])
                    _date_label = f" — {_d.strftime('%d/%m')}"

                if status == 'normal':
                    st.write(f"**{r['home_team']}** {r['home_score']}-{r['away_score']} **{r['away_team']}**{_date_label}")
                elif status == 'penalties':
                    st.write(f"**{r['home_team']}** {r['home_score']}-{r['away_score']} **{r['away_team']}** (Pênaltis: {r['pen_home']}-{r['pen_away']}) 🥅{_date_label}")
                elif status == 'extra_time':
                    st.write(f"**{r['home_team']}** {r['home_score']}-{r['away_score']} **{r['away_team']}** (Prorrogação) ⏱️{_date_label}")
                elif status == 'future':
                    st.write(f"**{r['home_team']}** vs **{r['away_team']}** - ⏰ *Jogo futuro*{_date_label}")
                elif status == 'vs':
                    st.write(f"**{r['home_team']}** vs. **{r['away_team']}** - 🆚 *Jogo a realizar*{_date_label}")
                elif status == 'postponed':
                    st.write(f"**{r['home_team']}** vs **{r['away_team']}** - 🔄 *Adiado*{_date_label}")
                elif status == 'abandoned':
                    st.write(f"**{r['home_team']}** vs **{r['away_team']}** - ⚠️ *Abandonado*{_date_label}")
        # Salvar na sessão
        st.session_state['resultados_parseados'] = resultados
        st.session_state['tipo_rodada'] = tipo_rodada
        st.session_state['numero_rodada'] = numero_rodada
        st.session_state['liga_selecionada'] = liga_key
        st.session_state['data_rodada'] = data_rodada
        
        # Limpar imagens anteriores
        if 'imagem_rodada_gerada' in st.session_state:
            del st.session_state['imagem_rodada_gerada']
        if 'imagem_tabela_gerada' in st.session_state:
            del st.session_state['imagem_tabela_gerada']
    
    # ========================================================================
    # SE RESULTADOS FORAM PROCESSADOS, MOSTRAR OPÇÕES
    # ========================================================================
    if 'resultados_parseados' in st.session_state:
        st.divider()
        st.subheader("📋 Configurar Tabela")
        
        # Configurações específicas por liga
        if st.session_state['liga_selecionada'] == "premierleague":
            render_premier_league_table_options()
        else:
            render_standard_league_table_options(st.session_state['liga_selecionada'])
        
        st.divider()
        
        # ====================================================================
        # BOTÕES DE GERAR IMAGENS
        # ====================================================================
        st.subheader("🖼️ Gerar Imagens")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📸 Gerar Imagem da Rodada", type="primary", width='stretch'):
                generator = ImageGenerator()
                try:
                    generator = ImageGenerator()
                    
                    img = generator.generate_results_image(
                        league=st.session_state['liga_selecionada'],
                        results=st.session_state['resultados_parseados'],
                        round_number=st.session_state.get('numero_rodada'),
                        is_postponed=st.session_state['tipo_rodada'] == "Jogos Atrasados"
                    )
                    
                    # Salvar na sessão
                    st.session_state['imagem_rodada_gerada'] = img
                    st.success("✅ Imagem da rodada gerada com sucesso!")
                    
                except Exception as e:
                    st.error(f"❌ Erro ao gerar imagem: {str(e)}")
        
        with col2:
            if st.button("📊 Gerar Imagem da Tabela", type="primary", width='stretch'):
                try:
                    # Processar tabela com resultados
                    processor = TableProcessor()
                    
                    # Carregar tabela original
                    tabela_path = f"data/tabelas/{st.session_state['liga_selecionada']}.txt"
                    with open(tabela_path, 'r', encoding='utf-8') as f:
                        processor.load_from_text(f.read())
                    
                    # Aplicar resultados — excluir partidas já registradas no histórico
                    _liga_str_tab = LIGA_DISPLAY_NAMES.get(st.session_state['liga_selecionada'], '')
                    _todos_tab = st.session_state['resultados_parseados']
                    _novos_tab = []
                    _duplicados_tab = []
                    for _r_tab in _todos_tab:
                        if is_already_in_historico(_r_tab['home_team'], _r_tab['away_team'], _liga_str_tab):
                            _duplicados_tab.append(_r_tab)
                        else:
                            _novos_tab.append(_r_tab)
                    if _duplicados_tab:
                        _dup_names = ", ".join(
                            f"{_r['home_team']} vs {_r['away_team']}" for _r in _duplicados_tab
                        )
                        st.info(f"ℹ️ {len(_duplicados_tab)} resultado(s) já registrado(s) no histórico ignorado(s) no cálculo da tabela: {_dup_names}")
                    processor.update_with_multiple_results(_novos_tab)
                    processor.sort_table()
                    
                    # Coletar confirmações
                    confirmations = collect_confirmations(st.session_state['liga_selecionada'])
                    
                    # Converter para formato de imagem
                    table_data = []
                    for team in processor.teams:
                        team_dict = {
                            'name': team.name,
                            'position': team.position,
                            'games': team.games,
                            'wins': team.wins,
                            'draws': team.draws,
                            'losses': team.losses,
                            'goals_for': team.goals_for,
                            'goals_against': team.goals_against,
                            'goal_difference': team.goal_difference,
                            'points': team.points
                        }
                        
                        # ADICIONAR NOTA DE PENALIDADE SE EXISTIR
                        # Verificar se o time tem pontos negativos ou penalidade conhecida
                        if team.name == "Sheffield Wednesday":
                            team_dict['penalty_note'] = "Sheffield Wednesday perdeu 18 pontos por adm. judicial e atraso de salários."
                        if team.name == "Leicester City":
                            team_dict['penalty_note'] = "Leicester City perdeu 6 pontos por violação das regras de lucratividade e sustentabilidade."
                        
                        table_data.append(team_dict)
                    
                    # Gerar imagem
                    generator = ImageGenerator()
                    img = generator.generate_table_image(
                        league=st.session_state['liga_selecionada'],
                        table_data=table_data,
                        confirmations=confirmations,
                        table_mode=st.session_state.get('table_mode')
                    )
                    
                    # ================================================================
                    # VALIDAÇÃO DA TABELA (ANTES DE SALVAR)
                    # ================================================================
                    validator = TableValidator()

                    has_divergences = False 
                    
                    # 1. Verificar times repetidos
                    num_teams = len(processor.teams)  # Usar o número de times da tabela
                    is_valid, warnings = validator.validate_results(
                        st.session_state['resultados_parseados'],
                        num_teams
                    )
                    
                    if warnings:
                        for warning in warnings:
                            st.warning(warning)
                    
                    # 2. Comparar com tabela oficial
                    with st.spinner("🔍 Validando tabela com fonte oficial..."):
                        official_table = validator.fetch_official_table(st.session_state['liga_selecionada'])

                    if official_table is not None and not official_table.empty:
                        divergencias = validator.compare_tables(table_data, official_table)
                        
                        if divergencias.empty:
                            st.success("✅ Tabela validada! Nenhuma divergência encontrada.")
                            has_divergences = False
                        else:
                            st.error("❌ Divergências encontradas com a fonte oficial:")
                            has_divergences = True
                            
                            # Mostrar divergências em formato tabela
                            colunas_exibir = ['Time', 'J_calculado', 'J_oficial', 'Pts_calculado', 'Pts_oficial', 
                                            'SG_calculado', 'SG_oficial']
                            
                            # Só mostrar colunas que existem
                            colunas_exibir = [col for col in colunas_exibir if col in divergencias.columns]
                            
                            st.dataframe(divergencias[colunas_exibir], width='stretch')
                    else:
                        st.info("ℹ️ Não foi possível buscar a tabela oficial para validação (verifique sua conexão).")
                        has_divergences = False
                    
                    # ================================================================
                    # Salvar na sessão
                    st.session_state['imagem_tabela_gerada'] = img
                    st.session_state['tabela_processada'] = processor.to_text()
                    
                    if not has_divergences or official_table is None:
                        st.success("✅ Imagem da tabela gerada com sucesso!")
                    
                except Exception as e:
                    st.error(f"❌ Erro ao gerar tabela: {str(e)}")
        
        # ====================================================================
        # MOSTRAR IMAGENS GERADAS
        # ====================================================================
        if 'imagem_rodada_gerada' in st.session_state or 'imagem_tabela_gerada' in st.session_state:
            st.divider()
            st.subheader("📷 Preview das Imagens")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if 'imagem_rodada_gerada' in st.session_state:
                    st.image(st.session_state['imagem_rodada_gerada'], caption="Imagem da Rodada")
                    
                    # Salvar e oferecer download
                    img_rgb = st.session_state['imagem_rodada_gerada'].convert("RGB")
                    img_rgb.save("rodada.png", format="PNG")
                    
                    with open("rodada.png", "rb") as f:
                        rodada_num = st.session_state.get('numero_rodada', 'atrasados')
                        
                        # MAPEAR PREFIXOS
                        prefixos = {
                            'premierleague': 'PL',
                            'championship': 'CH',
                            'leagueone': 'L1',
                            'leaguetwo': 'L2',
                            'nationalleague': 'NL'
                        }
                        
                        liga_key = st.session_state['liga_selecionada']
                        prefixo = prefixos.get(liga_key, 'XX')
                        
                        st.download_button(
                            "📥 Baixar Imagem da Rodada", 
                            f, 
                            file_name=f"{prefixo}-M{rodada_num}-R.png",  # ← AGORA COM PREFIXO
                            width='stretch'
                        )
            
            with col2:
                if 'imagem_tabela_gerada' in st.session_state:
                    st.image(st.session_state['imagem_tabela_gerada'], caption="Imagem da Tabela")
                    
                    # Salvar como PNG
                    st.session_state['imagem_tabela_gerada'].save("tabela.png", format="PNG")
                    
                    with open("tabela.png", "rb") as f:
                        rodada_num = st.session_state.get('numero_rodada', 'atrasados')
                        
                        # MAPEAR PREFIXOS
                        prefixos = {
                            'premierleague': 'PL',
                            'championship': 'CH',
                            'leagueone': 'L1',
                            'leaguetwo': 'L2',
                            'nationalleague': 'NL'
                        }
                        
                        liga_key = st.session_state['liga_selecionada']
                        prefixo = prefixos.get(liga_key, 'XX')
                        
                        st.download_button(
                            "📥 Baixar Tabela", 
                            f, 
                            file_name=f"{prefixo}-M{rodada_num}-T.png",  # ← AGORA COM PREFIXO
                            width='stretch'
                        )
            
            # ================================================================
            # BOTÃO ÚNICO: FECHAR RODADA + ATUALIZAR GITHUB
            # ================================================================
            st.divider()

            if st.button("☁️ Atualizar Tabelas e Histórico no GitHub", type="primary", width='stretch'):
                if 'tabela_processada' not in st.session_state:
                    st.error("❌ Gere a tabela primeiro!")
                elif 'GITHUB_TOKEN' not in st.secrets or 'GITHUB_REPO' not in st.secrets:
                    st.error("❌ Configure GITHUB_TOKEN e GITHUB_REPO em .streamlit/secrets.toml")
                else:
                    _liga_key_uni = st.session_state.get('liga_selecionada')
                    _liga_str_uni = LIGA_DISPLAY_NAMES.get(_liga_key_uni, _liga_key_uni)
                    rodada_info = st.session_state.get('numero_rodada', 'atrasados')
                    num_resultados = len(st.session_state['resultados_parseados'])
                    liga_nome = _liga_key_uni.upper()
                    commit_msg = f"[{liga_nome}] Rodada {rodada_info} - {num_resultados} jogo(s)"

                    _summary = []
                    _errors = []

                    with st.spinner("Processando..."):

                        # ── PASSO 1: Fechar rodada (posicoes.csv local) ──────────────
                        _current_md = None
                        _data_fim_uni = None
                        _added_pos = 0
                        try:
                            from datetime import date as _date_cls
                            _today = _date_cls.today()
                            _md_map = detect_matchdays(_liga_str_uni)
                            if not _md_map:
                                _errors.append("Nenhum dado histórico encontrado para fechar rodada.")
                            else:
                                for _md_num in sorted(_md_map.keys(), reverse=True):
                                    _last_date = max(
                                        _date_cls.fromisoformat(d)
                                        for d in _md_map[_md_num]
                                    )
                                    if _last_date <= _today:
                                        _current_md = _md_num
                                        _data_fim_uni = _last_date.strftime("%Y-%m-%d")
                                        break
                                if _current_md is None:
                                    _errors.append("Nenhum matchday passado encontrado para registrar.")
                                else:
                                    _positions_uni = compute_table_at_matchday(
                                        _liga_str_uni, _current_md, _md_map
                                    )
                                    _added_pos = append_matchday_positions(
                                        _liga_str_uni,
                                        _positions_uni, _data_fim_uni,
                                    )
                                    _summary.append(
                                        f"Rodada {_current_md} fechada ({_added_pos} times, data fim: {_data_fim_uni})"
                                    )
                        except Exception as _e_pos:
                            _errors.append(f"Erro ao fechar rodada: {_e_pos}")

                        # ── PASSO 2: Salvar histórico local ──────────────────────────
                        hist_result = _append_to_historico(
                            st.session_state['resultados_parseados'],
                            st.session_state.get('data_rodada', date.today()),
                            _liga_str_uni
                        )
                        n_hist = hist_result['added']
                        if hist_result['conflicts']:
                            st.session_state['historico_conflitos'] = hist_result['conflicts']
                            st.session_state['historico_conflitos_liga'] = _liga_key_uni
                            st.warning(f"⚠️ {len(hist_result['conflicts'])} resultado(s) com placar diferente do registrado. Verifique abaixo.")

                        # ── PASSO 3: Push para GitHub ────────────────────────────────
                        try:
                            github = GitHubHandler(
                                token=st.secrets['GITHUB_TOKEN'],
                                repo=st.secrets['GITHUB_REPO']
                            )

                            # 3a. tabelas/{liga}.txt
                            _tabela_path = f"data/tabelas/{_liga_key_uni}.txt"
                            _, _tabela_sha = github.get_file(_tabela_path)
                            if _tabela_sha:
                                _ok_tabela = github.update_file(
                                    file_path=_tabela_path,
                                    content=st.session_state['tabela_processada'],
                                    commit_message=commit_msg,
                                    sha=_tabela_sha
                                )
                                if _ok_tabela:
                                    _summary.append("Tabela enviada ao GitHub")
                                else:
                                    _errors.append("Falha ao atualizar tabela no GitHub.")
                            else:
                                _errors.append(f"Arquivo {_tabela_path} não encontrado no GitHub.")

                            # 3b. historico.csv
                            try:
                                with open("data/historico.csv", 'r', encoding='utf-8') as _fh:
                                    _hist_content = _fh.read()
                                _, _hist_sha = github.get_file("data/historico.csv")
                                if _hist_sha:
                                    github.update_file(
                                        file_path="data/historico.csv",
                                        content=_hist_content,
                                        commit_message=commit_msg,
                                        sha=_hist_sha
                                    )
                                else:
                                    github.create_file(
                                        file_path="data/historico.csv",
                                        content=_hist_content,
                                        commit_message=commit_msg
                                    )
                                _summary.append(f"historico.csv enviado ({n_hist} novo(s))")
                            except Exception as _e_hist:
                                _errors.append(f"Erro ao sincronizar historico.csv: {_e_hist}")

                            # 3c. posicoes.csv
                            try:
                                with open("data/posicoes.csv", 'r', encoding='utf-8') as _fp:
                                    _pos_content = _fp.read()
                                _, _pos_sha = github.get_file("data/posicoes.csv")
                                if _pos_sha:
                                    github.update_file(
                                        file_path="data/posicoes.csv",
                                        content=_pos_content,
                                        commit_message=commit_msg,
                                        sha=_pos_sha
                                    )
                                else:
                                    github.create_file(
                                        file_path="data/posicoes.csv",
                                        content=_pos_content,
                                        commit_message=commit_msg
                                    )
                                _summary.append("posicoes.csv enviado ao GitHub")
                            except Exception as _e_pcs:
                                _errors.append(f"Erro ao sincronizar posicoes.csv: {_e_pcs}")

                            carregar_tabela_github.clear()

                        except Exception as _e_gh:
                            _errors.append(f"Erro de conexão com GitHub: {_e_gh}")

                    for _err in _errors:
                        st.error(f"❌ {_err}")
                    if _summary:
                        st.success("✅ " + " · ".join(_summary))
                        st.balloons()

    # Conflict resolution — persists across reruns via session_state
    if st.session_state.get('historico_conflitos'):
        st.divider()
        st.subheader("⚠️ Resultados com placar diferente do registrado")
        remaining = []
        for conflict in st.session_state['historico_conflitos']:
            col1, col2, col3 = st.columns([4, 1, 1])
            col1.write(
                f"**{conflict['home_team']} vs {conflict['away_team']}** "
                f"({conflict['liga']})  \n"
                f"Registrado: `{conflict['old_score']}` → Novo: `{conflict['new_score']}`"
            )
            key_base = f"conf_{conflict['home_team']}_{conflict['away_team']}"
            if col2.button("✅ Atualizar", key=f"{key_base}_sim"):
                _update_historico_row(
                    conflict['home_team'], conflict['away_team'],
                    conflict['liga'], conflict['new_score'], conflict['date_str']
                )
                try:
                    github = GitHubHandler(st.secrets['GITHUB_TOKEN'], st.secrets['GITHUB_REPO'])
                    with open("data/historico.csv", 'r', encoding='utf-8') as f:
                        hist_content = f.read()
                    _, hist_sha = github.get_file("data/historico.csv")
                    github.update_file(
                        "data/historico.csv", hist_content,
                        f"[CORRECAO] {conflict['home_team']} {conflict['new_score']} {conflict['away_team']}",
                        hist_sha
                    )
                    st.success(f"✅ Placar atualizado para {conflict['new_score']}.")
                except Exception as e:
                    st.warning(f"CSV atualizado localmente, mas não foi possível sincronizar: {e}")
            elif col3.button("❌ Ignorar", key=f"{key_base}_nao"):
                pass  # drop from remaining
            else:
                remaining.append(conflict)
        st.session_state['historico_conflitos'] = remaining


def collect_confirmations(liga_key: str) -> Dict:
    """
    Coleta todas as confirmações dos checkboxes
    
    Returns:
        Dict com {position: {'champion': bool, 'ucl': bool, ...}}
    """
    confirmations = {}
    
    if liga_key == 'premierleague':
        for pos in range(1, 21):
            confirmations[pos] = {
                'champion': st.session_state.get(f'pl_{pos}_champion', False),
                'ucl': st.session_state.get(f'pl_{pos}_ucl', False),
                'uel': st.session_state.get(f'pl_{pos}_uel', False),
                'uecl': st.session_state.get(f'pl_{pos}_uecl', False),
                'relegated': st.session_state.get(f'pl_{pos}_relegated', False)
            }
    
    elif liga_key == 'championship':
        for pos in range(1, 25):
            confirmations[pos] = {
                'champion': st.session_state.get(f'ch_{pos}_champion', False),
                'promoted': st.session_state.get(f'ch_{pos}_promoted', False),
                'playoffs': st.session_state.get(f'ch_{pos}_playoffs', False),
                'relegated': st.session_state.get(f'ch_{pos}_relegated', False)
            }
    
    elif liga_key == 'leagueone':
        for pos in range(1, 25):
            confirmations[pos] = {
                'champion': st.session_state.get(f'l1_{pos}_champion', False),
                'promoted': st.session_state.get(f'l1_{pos}_promoted', False),
                'playoffs': st.session_state.get(f'l1_{pos}_playoffs', False),
                'relegated': st.session_state.get(f'l1_{pos}_relegated', False)
            }
    
    elif liga_key == 'leaguetwo':
        for pos in range(1, 25):
            confirmations[pos] = {
                'champion': st.session_state.get(f'l2_{pos}_champion', False),
                'promoted': st.session_state.get(f'l2_{pos}_promoted', False),
                'playoffs': st.session_state.get(f'l2_{pos}_playoffs', False),
                'relegated': st.session_state.get(f'l2_{pos}_relegated', False)
            }
    elif liga_key == 'nationalleague':
        for pos in range(1, 25):
            confirmations[pos] = {
                'champion': st.session_state.get(f'nl_{pos}_champion', False),
                'playoffs_semi': st.session_state.get(f'nl_{pos}_playoffs_semi', False),
                'playoffs_quarter': st.session_state.get(f'nl_{pos}_playoffs_quarter', False),
                'relegated': st.session_state.get(f'nl_{pos}_relegated', False)
            }
    
    
    return confirmations

def render_premier_league_table_options():
    """Opções específicas para Premier League"""
    
    # Carregar times da tabela
    processor = TableProcessor()
    
    # Tentar carregar tabela real ou usar padrão
    try:
        with open('data/tabelas/premierleague.txt', 'r', encoding='utf-8') as f:
            processor.load_from_text(f.read())
        times_pl = [team.name for team in processor.teams]
    except:
        times_pl = ["Arsenal", "Manchester City", "Liverpool", "Chelsea", 
                    "Aston Villa", "Manchester United", "Tottenham", 
                    "Newcastle United", "Brighton", "Brentford",
                    "Fulham", "Crystal Palace", "Everton", "West Ham",
                    "Bournemouth", "Nottingham Forest", "Wolves",
                    "Burnley", "Sheffield United", "Luton Town"]
    
    st.write("### ⚙️ Configuração das vagas europeias")
    
    table_modes = [
        "G6 Europeu (5 UCL + 1 UEL)",
        "G7 Europeu (5 UCL + 2 UEL)",
        "G7 Europeu (5 UCL + 1 UEL + 1 UECL)",
        "G8 Europeu (5 UCL + 2 UEL + 1 UECL)"
    ]
    
    selected_mode = st.selectbox("Modo da tabela", table_modes, index=2)
    
    st.divider()
    
    st.write("### 🏆 Times confirmados em competições europeias")
    
    col1, col2 = st.columns(2)
    
    with col1:
        confirmed_uel = st.multiselect(
            "Confirmados na UEL (máx. 2)",
            options=times_pl,
            max_selections=2,
            help="Times que garantiram vaga na Europa League por copa"
        )
    
    with col2:
        confirmed_uecl = st.multiselect(
            "Confirmados na UECL (máx. 1)",
            options=times_pl,
            max_selections=1,
            help="Times que garantiram vaga na Conference League por copa"
        )
    
    st.divider()
    
    st.write("### ✅ Confirmações de Classificação")
    
    # Campeão e posições europeias (1-8)
    st.write("**Zona Europeia:**")
    
    for pos in range(1, 9):
        cols = st.columns([1, 2, 2, 2, 2])
        
        with cols[0]:
            st.write(f"**{pos}º**")
        
        with cols[1]:
            if pos == 1:
                st.checkbox("Campeão", key=f"pl_{pos}_champion")
            else:
                st.write("")
        
        with cols[2]:
            if pos <= 5:
                st.checkbox("UCL", key=f"pl_{pos}_ucl")
            else:
                st.write("")
        
        with cols[3]:
            if pos <= 7:
                st.checkbox("UEL", key=f"pl_{pos}_uel")
            else:
                st.write("")
            
        
        with cols[4]:
            st.checkbox("UECL", key=f"pl_{pos}_uecl")
    
    st.divider()
    
    # Zona de rebaixamento (18-20)
    st.write("**Zona de Rebaixamento:**")
    
    for pos in [18, 19, 20]:
        st.checkbox(f"{pos}º colocado - Rebaixado", key=f"pl_{pos}_relegated")
    
    # Salvar configurações na sessão
    st.session_state['table_mode'] = selected_mode
    st.session_state['confirmed_uel'] = confirmed_uel
    st.session_state['confirmed_uecl'] = confirmed_uecl

def render_standard_league_table_options(liga_key):
    """Opções para Championship, League One, League Two e National League"""
    st.write("**Confirmações de classificação:**")
    
    # Checkboxes baseados na liga
    if liga_key == "championship":
        render_confirmation_checkboxes_championship()
    elif liga_key == "leagueone":
        render_confirmation_checkboxes_leagueone()
    elif liga_key == "leaguetwo":
        render_confirmation_checkboxes_leaguetwo()
    elif liga_key == "nationalleague":
        render_confirmation_checkboxes_nationalleague()


def render_confirmation_checkboxes_championship():
    """Checkboxes para Championship"""
    st.write("**Zona de Promoção e Play-offs:**")
    
    # 1º colocado
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.write("**1º**")
    with col2:
        st.checkbox("Campeão", key="ch_1_champion")
    with col3:
        st.checkbox("Promovido", key="ch_1_promoted")
    with col4:
        st.checkbox("Play-offs", key="ch_1_playoffs")
    
    # 2º colocado
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.write("**2º**")
    with col2:
        st.checkbox("Promovido", key="ch_2_promoted")
    with col3:
        st.checkbox("Play-offs", key="ch_2_playoffs")
    with col4:
        st.write("")
    
    # 3º ao 6º - Play-offs
    for pos in range(3, 7):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.write(f"**{pos}º**")
        with col2:
            st.checkbox("Play-offs", key=f"ch_{pos}_playoffs")
        with col3:
            st.write("")
        with col4:
            st.write("")
    
    st.divider()
    
    st.write("**Zona de Rebaixamento:**")
    for pos in [22, 23, 24]:
        if pos == 24:
            st.checkbox(f"{pos}º colocado - Rebaixado", key=f"ch_{pos}_relegated", value=True)
        else:
            st.checkbox(f"{pos}º colocado - Rebaixado", key=f"ch_{pos}_relegated")


def render_confirmation_checkboxes_leagueone():
    """Checkboxes para League One"""
    # 1º colocado
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.write("**1º**")
    with col2:
        st.checkbox("Campeão", key="l1_1_champion")
    with col3:
        st.checkbox("Promovido", key="l1_1_promoted")
    with col4:
        st.checkbox("Play-offs", key="l1_1_playoffs")
    
    # 2º colocado
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.write("**2º**")
    with col2:
        st.checkbox("Promovido", key="l1_2_promoted")
    with col3:
        st.checkbox("Play-offs", key="l1_2_playoffs")
    with col4:
        st.write("")

    # 3º ao 6º - Play-offs
    for pos in range(3, 7):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.write(f"**{pos}º**")
        with col2:
            st.checkbox("Play-offs", key=f"l1_{pos}_playoffs")
        with col3:
            st.write("")
        with col4:
            st.write("")
    
    st.divider()
    
    st.write("**Zona de Rebaixamento:**")
    for pos in [21, 22, 23, 24]:
        st.checkbox(f"{pos}º colocado - Rebaixado", key=f"l1_{pos}_relegated")


def render_confirmation_checkboxes_leaguetwo():
    """Checkboxes para League Two"""
    # 1º colocado
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.write("**1º**")
    with col2:
        st.checkbox("Campeão", key="l2_1_champion")
    with col3:
        st.checkbox("Promovido", key="l2_1_promoted")
    with col4:
        st.checkbox("Play-offs", key="l2_1_playoffs")

    # 2º colocado
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.write("**2º**")
    with col2:
        st.checkbox("Promovido", key="l2_2_promoted")
    with col3:
        st.checkbox("Play-offs", key="l2_2_playoffs")
    with col4:
        st.write("")

    # 3º colocado
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.write("**3º**")
    with col2:
        st.checkbox("Promovido", key="l2_3_promoted")
    with col3:
        st.checkbox("Play-offs", key="l2_3_playoffs")
    with col4:
        st.write("")
    
    # 3º ao 6º - Play-offs
    for pos in range(4, 8):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.write(f"**{pos}º**")
        with col2:
            st.checkbox("Play-offs", key=f"l2_{pos}_playoffs")
        with col3:
            st.write("")
        with col4:
            st.write("")
    
    st.divider()
    
    st.write("**Zona de Rebaixamento:**")
    for pos in [23, 24]:
        st.checkbox(f"{pos}º colocado - Rebaixado", key=f"l2_{pos}_relegated")


def render_confirmation_checkboxes_nationalleague():
    """Checkboxes para National League"""
    # 1º colocado
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.write("**1º**")
    with col2:
        st.checkbox("Campeão", key="nl_1_champion")
    with col3:
        st.checkbox("Play-offs Semi", key="nl_1_playoffs_semi")
    with col4:
        st.checkbox("Play-offs Quartas", key="nl_1_playoffs_quarter")
    # 2º colocado
    for pos in range(2, 4):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.write(f"**{pos}º**")
        with col2:
            st.checkbox("Play-offs Semi", key=f"nl_{pos}_playoffs_semi")
        with col3:
            st.checkbox("Play-offs Quartas", key=f"nl_{pos}_playoffs_quarter")
        with col4:
            st.write("")
    
    
    # 3º ao 6º - Play-offs
    for pos in range(4, 8):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.write(f"**{pos}º**")
        with col2:
            st.checkbox("Play-offs Quartas", key=f"nl_{pos}_playoffs_quarter")
        with col3:
            st.write("")
        with col4:
            st.write("")
    
    st.divider()
    
    st.write("**Zona de Rebaixamento:**")
    for pos in [21, 22, 23, 24]:
        st.checkbox(f"{pos}º colocado - Rebaixado", key=f"nl_{pos}_relegated")


# ============================================================================
# UTILITÁRIOS — ESTATÍSTICAS
# ============================================================================

def process_badge_for_dark_mode(img_bytes: bytes) -> bytes:
    """Inverts monochromatic dark badges so they remain visible in dark mode."""
    import statistics
    img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    pixels = list(img.getdata())
    opaque = [(px[0], px[1], px[2]) for px in pixels if px[3] > 10]
    if not opaque:
        return img_bytes
    all_channels = [v for p in opaque for v in p]
    avg_brightness = sum(all_channels) / len(all_channels)
    std_dev = statistics.stdev(all_channels)
    if std_dev >= 30 or avg_brightness >= 80:
        return img_bytes
    r, g, b, a = img.split()
    r = r.point(lambda x: 255 - x)
    g = g.point(lambda x: 255 - x)
    b = b.point(lambda x: 255 - x)
    result = Image.merge("RGBA", (r, g, b, a))
    out = io.BytesIO()
    result.save(out, format="PNG")
    return out.getvalue()


def _get_recent_form(selected_team: str, liga_str: str, n: int = 5) -> list:
    """Returns list of 'V'/'E'/'D' for the last n matches of selected_team in liga_str."""
    csv_path = os.path.join("data", "historico.csv")
    if not os.path.exists(csv_path):
        return []
    games = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('liga') != liga_str:
                continue
            if row.get('casa') == selected_team or row.get('fora') == selected_team:
                games.append(row)
    from datetime import datetime
    def _parse_date(row):
        try:
            return datetime.strptime(row['data'], '%Y-%m-%d')
        except Exception:
            return datetime.min
    games.sort(key=_parse_date, reverse=True)
    games = games[:n]
    results = []
    for g in games:
        placar_clean = re.sub(r'\s*\(.*?\)', '', g.get('placar', '')).strip()
        parts = placar_clean.split('-')
        if len(parts) != 2:
            continue
        try:
            home_score = int(parts[0].strip())
            away_score = int(parts[1].strip())
        except ValueError:
            continue
        if g.get('casa') == selected_team:
            results.append('V' if home_score > away_score else ('E' if home_score == away_score else 'D'))
        else:
            results.append('V' if away_score > home_score else ('E' if away_score == home_score else 'D'))
    return results


# ============================================================================
# MODO ESTATÍSTICAS
# ============================================================================

# Primary shirt/brand color per team.
# Fallback for any team not listed: "white".
TEAM_COLORS: dict[str, str] = {
    # ── Premier League ──────────────────────────────────────────────────
    "Arsenal":              "red",          # CSS named color
    "Aston Villa":          "#670E36",      # hex – claret (CSS maroon too dark/cool)
    "Bournemouth":          "#da291c",      # hex – cherry red
    "Brentford":            "#e30613",      # hex – no close CSS named color
    "Brighton":             "#0057B8",      # hex – Brighton blue
    "Burnley":              "#6C1D45",      # hex – claret
    "Chelsea":              "#034694",      # hex – royal blue (CSS blue/navy off)
    "Crystal Palace":       "red",          # CSS named color
    "Everton":              "#003399",      # hex – royal blue
    "Fulham":               "white",        # CSS named color
    "Leeds United":         "white",        # CSS named color
    "Liverpool":            "red",          # CSS named color
    "Manchester City":      "#6cabdd",      # hex – sky blue (CSS skyblue too light)
    "Manchester United":    "red",          # CSS named color
    "Newcastle United":     "black",        # CSS named color
    "Nottingham Forest":    "red",          # CSS named color
    "Sunderland":           "red",          # CSS named color
    "Tottenham":            "white",        # CSS named color
    "West Ham":             "#7a263a",      # hex – claret
    "Wolverhampton":        "#fdb913",      # hex – old gold (CSS gold too yellow)
    # ── Championship ────────────────────────────────────────────────────
    "Birmingham City":      "blue",         # CSS named color
    "Blackburn Rovers":     "#009EE3",      # hex – Blackburn blue
    "Bristol City":         "red",          # CSS named color
    "Charlton Athletic":    "red",          # CSS named color
    "Coventry City":        "#59cbe8",      # hex – sky blue
    "Derby County":         "white",        # CSS named color
    "Hull City":            "#f5a12d",      # hex – amber (CSS orange close but off)
    "Ipswich Town":         "#0070bf",      # hex – Ipswich blue
    "Leicester City":       "#003090",      # hex – Leicester blue
    "Middlesbrough":        "red",          # CSS named color
    "Millwall":             "navy",         # CSS named color
    "Norwich City":         "yellow",       # CSS named color
    "Oxford United":        "yellow",       # CSS named color
    "Portsmouth":           "navy",         # CSS named color
    "Preston North End":    "white",        # CSS named color
    "Queens Park Rangers":  "#1D5BA4",      # hex – QPR blue
    "Sheffield United":     "red",          # CSS named color
    "Sheffield Wednesday":  "#003893",      # hex – Wednesday blue
    "Southampton":          "red",          # CSS named color
    "Stoke City":           "red",          # CSS named color
    "Swansea City":         "white",        # CSS named color
    "Watford":              "yellow",       # CSS named color
    "West Bromwich":        "navy",         # CSS named color
    "Wrexham":              "red",          # CSS named color
    # ── League One ──────────────────────────────────────────────────────
    "AFC Wimbledon":        "#1766A6",      # hex – Wimbledon blue
    "Barnsley":             "red",          # CSS named color
    "Blackpool":            "orange",       # CSS named color – tangerine
    "Bolton Wanderers":     "white",        # CSS named color
    "Bradford City":        "#801638",      # hex – claret
    "Burton Albion":        "yellow",       # CSS named color
    "Cardiff City":         "#0070b5",      # hex – Cardiff blue
    "Doncaster Rovers":     "red",          # CSS named color
    "Exeter City":          "red",          # CSS named color
    "Huddersfield Town":    "#0E63AD",      # hex – Huddersfield blue
    "Leyton Orient":        "red",          # CSS named color
    "Lincoln City":         "red",          # CSS named color
    "Luton Town":           "orange",       # CSS named color
    "Mansfield Town":       "gold",         # CSS named color – amber
    "Northampton Town":     "maroon",       # CSS named color
    "Peterborough":         "navy",         # CSS named color
    "Plymouth Argyle":      "green",        # CSS named color
    "Port Vale":            "white",        # CSS named color
    "Reading":              "#004494",      # hex – Reading blue
    "Rotherham United":     "red",          # CSS named color
    "Stevenage":            "red",          # CSS named color
    "Stockport County":     "#0052a5",      # hex – Stockport blue
    "Wigan Athletic":       "#1D3784",      # hex – Wigan blue
    "Wycombe Wanderers":    "navy",         # CSS named color
    # ── League Two ──────────────────────────────────────────────────────
    "Accrington":           "red",          # CSS named color
    "Barnet":               "#F5A623",      # hex – amber (CSS gold too yellow)
    "Barrow":               "#003090",      # hex – Barrow blue
    "Bristol Rovers":       "#005197",      # hex – Bristol Rovers blue
    "Bromley":              "white",        # CSS named color
    "Cambridge United":     "#f5a800",      # hex – amber
    "Cheltenham Town":      "red",          # CSS named color
    "Chesterfield":         "#1E3A71",      # hex – Chesterfield blue
    "Colchester United":    "navy",         # CSS named color
    "Crawley Town":         "red",          # CSS named color
    "Crewe Alexandra":      "red",          # CSS named color
    "Fleetwood Town":       "red",          # CSS named color
    "Gillingham":           "navy",         # CSS named color
    "Grimsby Town":         "black",        # CSS named color
    "Harrogate Town":       "yellow",       # CSS named color
    "Milton Keynes Dons":   "white",        # CSS named color
    "Newport County":       "#f5a800",      # hex – amber
    "Notts County":         "black",        # CSS named color
    "Oldham Athletic":      "blue",         # CSS named color
    "Salford City":         "red",          # CSS named color
    "Shrewsbury Town":      "blue",         # CSS named color
    "Swindon Town":         "red",          # CSS named color
    "Tranmere Rovers":      "white",        # CSS named color
    "Walsall":              "red",          # CSS named color
    # ── National League ─────────────────────────────────────────────────
    "Aldershot Town":       "red",          # CSS named color
    "Altrincham":           "red",          # CSS named color
    "Boston United":        "gold",         # CSS named color
    "Boreham Wood":         "white",        # CSS named color
    "Brackley Town":        "red",          # CSS named color
    "Braintree Town":       "orange",       # CSS named color
    "Carlisle United":      "blue",         # CSS named color
    "Eastleigh":            "navy",         # CSS named color
    "FC Halifax Town":      "navy",         # CSS named color
    "Forest Green Rovers":  "green",        # CSS named color
    "Gateshead":            "white",        # CSS named color
    "Hartlepool United":    "#1D3784",      # hex – Victoria blue
    "Morecambe":            "red",          # CSS named color
    "Rochdale":             "blue",         # CSS named color
    "Scunthorpe United":    "#591F2D",      # hex – claret
    "Solihull Moors":       "yellow",       # CSS named color
    "Southend United":      "navy",         # CSS named color
    "Sutton United":        "#F5A800",      # hex – amber/old gold
    "Tamworth":             "red",          # CSS named color
    "Truro City":           "red",        # CSS named color
    "Wealdstone":           "red",          # CSS named color
    "Woking":               "red",          # CSS named color
    "Yeovil Town":          "green",        # CSS named color
    "York City":            "red",          # CSS named color
}


def render_stats_mode():
    st.header("📈 Estatísticas")

    LIGAS_STATS = {
        "Premier League":  ("premierleague",  "Premier League"),
        "Championship":    ("championship",   "Championship"),
        "League One":      ("leagueone",      "League One"),
        "League Two":      ("leaguetwo",      "League Two"),
        "National League": ("nationalleague", "National League"),
    }

    liga_label = st.selectbox("Liga", list(LIGAS_STATS.keys()))
    liga_key, liga_str = LIGAS_STATS[liga_label]

    _BADGE_FOLDERS = {
        "premierleague":  "escudos-pl",
        "championship":   "escudos-ch",
        "leagueone":      "escudos-l1",
        "leaguetwo":      "escudos-l2",
        "nationalleague": "escudos-nl",
    }

    if st.button("🔄 Atualizar Estatísticas", type="primary"):
        with st.spinner("Calculando estatísticas..."):
            try:
                data = compute_league_stats(liga_str)
                if 'stats_cache' not in st.session_state:
                    st.session_state['stats_cache'] = {}
                st.session_state['stats_cache'][liga_key] = data

                # Pre-process and cache badge base64 strings eagerly
                badge_folder = _BADGE_FOLDERS.get(liga_key, "escudos-pl")
                badge_cache = []
                for team in data['teams']:
                    badge_path = f"{badge_folder}/{team}.png"
                    if os.path.exists(badge_path):
                        with open(badge_path, "rb") as _f:
                            _raw = _f.read()
                        _processed = process_badge_for_dark_mode(_raw)
                        _b64 = base64.b64encode(_processed).decode()
                        badge_cache.append(f"data:image/png;base64,{_b64}")
                    else:
                        badge_cache.append("")
                if 'badges_cache' not in st.session_state:
                    st.session_state['badges_cache'] = {}
                st.session_state['badges_cache'][liga_key] = badge_cache

                st.success("✅ Estatísticas atualizadas!")
            except Exception as e:
                st.error(f"❌ Erro ao calcular estatísticas: {e}")
                import traceback
                with st.expander("Detalhes do erro"):
                    st.code(traceback.format_exc())

    cache = st.session_state.get('stats_cache', {})
    if liga_key not in cache:
        st.info("Clique em '🔄 Atualizar Estatísticas' para gerar os dados.")
        return

    data = cache[liga_key]

    if not data.get('teams'):
        st.warning("Nenhum dado histórico encontrado para esta liga em data/historico.csv.")
        return

    # ── Destaques ─────────────────────────────────────────────────────────
    st.subheader("🏆 Destaques da Liga")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"🏠 **Melhor mandante:** {data['best_home']}")
        st.markdown(f"🏠 **Pior mandante:** {data['worst_home']}")
        st.markdown(f"⚽ **Melhor ataque:** {data['best_attack_team']} ({data['best_attack_gols']} gols)")
        st.markdown(f"😟 **Pior ataque:** {data['worst_attack_team']} ({data['worst_attack_gols']} gols)")
    with col2:
        st.markdown(f"✈️ **Melhor visitante:** {data['best_away']}")
        st.markdown(f"✈️ **Pior visitante:** {data['worst_away']}")
        st.markdown(f"🛡️ **Melhor defesa:** {data['best_defense_team']} ({data['best_defense_gols']} sofridos)")
        st.markdown(f"😬 **Pior defesa:** {data['worst_defense_team']} ({data['worst_defense_gols']} sofridos)")

    st.divider()

    # ── Insights gerais ────────────────────────────────────────────────────
    selected_team = None
    if data['insights']:
        # Map each team to the subset of insights that mention it (all teams shown)
        team_insight_map = {
            team: [ins for ins in data['insights'] if team in ins]
            for team in data['teams']
        }
        all_teams = data['teams']

        filter_key = f'stats_team_filter_{liga_key}'
        if filter_key not in st.session_state:
            st.session_state[filter_key] = None
        selected_team = st.session_state[filter_key]

        insights_col, badges_col = st.columns([3, 1])

        # Badge filter — 4 crests per row inside the right column
        with badges_col:
            images_b64 = st.session_state.get('badges_cache', {}).get(liga_key, [])

            clicked = clickable_images(
                images_b64,
                titles=all_teams,
                div_style={"display": "grid", "grid-template-columns": "repeat(4, 1fr)", "gap": "6px"},
                img_style={"width": "100%", "height": "60px", "object-fit": "contain", "cursor": "pointer", "border-radius": "6px"},
                key=f"clickable_{liga_key}",
            )

            if clicked > -1:
                team_clicado = all_teams[clicked]
                st.session_state[filter_key] = None if selected_team == team_clicado else team_clicado
                selected_team = st.session_state[filter_key]

        # Insights list on the left
        with insights_col:
            heading = f"📊 Insights de {selected_team}" if selected_team else "📊 Insights da Liga"
            st.subheader(heading)

            if selected_team:
                # Forma recente
                form = _get_recent_form(selected_team, liga_str)
                if form:
                    _COLOR_MAP = {'V': '#22c55e', 'E': '#6b7280', 'D': '#ef4444'}
                    badges_html = " ".join(
                        f'<span style="background:{_COLOR_MAP[r]};color:white;font-weight:bold;'
                        f'font-size:16px;padding:4px 10px;border-radius:4px;">{r}</span>'
                        for r in reversed(form)
                    )
                    st.markdown(
                        f"<small>Forma (últimos 5 jogos):</small><br>{badges_html}",
                        unsafe_allow_html=True
                    )
                    st.write("")

                # Delta de posição (entre as duas últimas rodadas registradas)
                _d = compute_position_delta(selected_team, liga_str)
                if _d is not None:
                    if _d > 0:
                        st.markdown(
                            f'<span style="color:#22c55e;font-weight:bold;font-size:16px;">▲{_d}</span>'
                            f'<span style="color:#22c55e;font-size:14px;"> posições desde a rodada anterior</span>',
                            unsafe_allow_html=True
                        )
                    elif _d < 0:
                        st.markdown(
                            f'<span style="color:#ef4444;font-weight:bold;font-size:16px;">▼{abs(_d)}</span>'
                            f'<span style="color:#ef4444;font-size:14px;"> posições desde a rodada anterior</span>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            '<span style="color:#6b7280;font-size:14px;">─ Mesma posição</span>',
                            unsafe_allow_html=True
                        )
                    st.write("")

                team_insights = team_insight_map.get(selected_team, [])
                if team_insights:
                    for insight in team_insights:
                        st.write(f"• {insight}")
                else:
                    st.write("• Sem insights relevantes")
            else:
                for insight in data['insights']:
                    st.write(f"• {insight}")

                # ── Variação de Posições ───────────────────────────────────
                st.write("")
                st.markdown("**Variação de Posições**")
                _deltas = []
                for _team in data['teams']:
                    _d = compute_position_delta(_team, liga_str)
                    if _d is not None:
                        _deltas.append((_team, _d))
                _deltas.sort(key=lambda x: x[1], reverse=True)
                for _team, _d in _deltas:
                    if _d > 0:
                        _badge = (
                            f'<span style="color:#22c55e;font-weight:bold;">▲{_d}</span>'
                        )
                    elif _d < 0:
                        _badge = (
                            f'<span style="color:#ef4444;font-weight:bold;">▼{abs(_d)}</span>'
                        )
                    else:
                        _badge = (
                            '<span style="color:#6b7280;">─ Mesma posição</span>'
                        )
                    st.markdown(
                        f'{_team} {_badge}',
                        unsafe_allow_html=True
                    )

    # Gráfico de trajetória (fora das colunas, abaixo dos insights)
    if selected_team:
        if not os.path.exists(POSICOES_CSV):
            st.info("Feche ao menos duas rodadas para gerar o gráfico de trajetória.")
        else:
            import pandas as pd
            _df = pd.read_csv(POSICOES_CSV, dtype=str)
            _df_team = _df[
                (_df['time'] == selected_team) & (_df['liga'] == liga_str)
            ].copy()
            _df_team['matchday'] = _df_team['matchday'].astype(int)
            _df_team['posicao'] = _df_team['posicao'].astype(int)
            _df_team['data_fim_matchday'] = pd.to_datetime(_df_team['data_fim_matchday'])
            _df_team = _df_team.sort_values('matchday')

            if len(_df_team) < 2:
                st.info(
                    "Feche ao menos duas rodadas para gerar o gráfico de trajetória."
                )
            else:
                _num_times = len(data.get('teams', []))
                _max_pos = _num_times if _num_times > 0 else 24
                fig = go.Figure()
                _team_color = TEAM_COLORS.get(selected_team, "white")
                fig.add_trace(go.Scatter(
                    x=_df_team['data_fim_matchday'],
                    y=_df_team['posicao'],
                    mode='lines+markers',
                    line=dict(color=_team_color, width=2),
                    marker=dict(color=_team_color, size=7),
                    name=selected_team,
                ))
                fig.update_layout(
                    title=f"Trajetória de {selected_team}",
                    xaxis_title="Data",
                    yaxis_title="Posição",
                    xaxis=dict(tickformat="%d/%m"),
                    yaxis=dict(
                        autorange='reversed',
                        range=[_max_pos + 0.5, 0.5],
                        dtick=1,
                    ),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white"),
                    height=350,
                    margin=dict(l=40, r=20, t=50, b=40),
                )
                st.plotly_chart(fig, width='stretch')


# ============================================================================
# INTERFACE PRINCIPAL
# ============================================================================

st.set_page_config(
    page_title="Gerador BBI",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ Gerador de Conteúdo BBI")

# Seleção do modo
modo = st.radio(
    "Escolha o modo:",
    ["📰 Gerar Notícia", "🔢 Gerar Placar", "📊 Gerar Tabela com Resultados", "🏆 Gerar Copa", "📈 Estatísticas"],
    horizontal=True
)

st.divider()

if modo == "🔢 Gerar Placar":
    # MODO ORIGINAL DE PLACAR
    st.header("Gerador de Placares")
    
    templates = [f for f in TEMPLATE_ORDER if f in TEMPLATE_LABELS]
    
    template_escolhido_label = st.selectbox(
        "Escolha o Template",
        [TEMPLATE_LABELS[t] for t in templates]
    )
    
    template_escolhido = [k for k, v in TEMPLATE_LABELS.items() if v == template_escolhido_label][0]
    times = carregar_escudos(template_escolhido)
    
    col1, col2 = st.columns(2)
    
    with col1:
        mandante = st.selectbox("Time Mandante", times)
    
    with col2:
        visitante = st.selectbox("Time Visitante", times)
    
    placar = st.text_input("Placar (ex: 1-0 ou 2-1 (3-2 agr.))")
    
    col3, col4 = st.columns(2)
    
    with col3:
        marcadores_mandante = st.text_area("Marcadores do Mandante", placeholder="Jogador A 45'\nJogador B 67'")
    
    with col4:
        marcadores_visitante = st.text_area("Marcadores do Visitante", placeholder="Jogador X 88'")
    
    background = st.file_uploader("Upload da imagem de fundo (opcional)", type=["png", "jpg", "jpeg", "webp", "avif"])
    alinhamento = st.radio("Alinhamento da imagem de fundo:", ["Centro", "Esquerda", "Direita"], horizontal=True)

    if st.button("Gerar Placar", type="primary"):
        template_path = os.path.join(TEMPLATE_DIR, template_escolhido)
        bg_path = None

        if background:
            img = Image.open(background).convert("RGBA")
            bg_path = "temp_bg.png"
            img.save(bg_path, format="PNG")

        img = desenhar_placar(
            template_path, mandante, visitante, placar,
            marcadores_mandante, marcadores_visitante,
            background=bg_path,
            alinhamento=alinhamento if alinhamento else "Centro"
        )

        img_rgb = img.convert("RGB")
        img_rgb.save("placar_final.jpg", format="JPEG", quality=100)

        st.session_state['placar_gerado'] = {
            'template': template_escolhido,
            'mandante': mandante,
            'visitante': visitante,
            'placar_str': placar,
        }

    _PLACAR_LIGA_MAP = {
        "premierleague.png": "Premier League",
        "championship.png":  "Championship",
        "leagueone.png":     "League One",
        "leaguetwo.png":     "League Two",
        "nationalleague.png":"National League",
    }

    if 'placar_gerado' in st.session_state and os.path.exists("placar_final.jpg"):
        _pg = st.session_state['placar_gerado']
        st.image("placar_final.jpg")
        with open("placar_final.jpg", "rb") as f:
            _nome_arquivo = f"{_pg['mandante']} {_pg['placar_str']} {_pg['visitante']}.jpg".replace("/", "-")
            st.download_button("📥 Baixar Imagem", f, file_name=_nome_arquivo)
        _liga_str_pg = _PLACAR_LIGA_MAP.get(_pg['template'])
        if _liga_str_pg:
            if st.button("💾 Salvar no Histórico"):
                _score_m = re.match(r'(\d+)-(\d+)', _pg['placar_str'].strip())
                if not _score_m:
                    st.error("❌ Não foi possível extrair o placar. Use o formato X-Y.")
                else:
                    _result_pg = {
                        'home_team': _pg['mandante'],
                        'away_team': _pg['visitante'],
                        'home_score': int(_score_m.group(1)),
                        'away_score': int(_score_m.group(2)),
                        'status': 'normal',
                    }
                    _hist_pg = _append_to_historico([_result_pg], date.today(), _liga_str_pg)
                    if _hist_pg['added'] > 0:
                        st.success("✅ Resultado salvo no histórico.")
                    elif _hist_pg['conflicts']:
                        st.error(f"⚠️ Conflito: placar diferente já registrado para {_pg['mandante']} vs {_pg['visitante']}.")
                    else:
                        st.warning("⚠️ Resultado já existe no histórico.")

elif modo == "📰 Gerar Notícia":
    # MODO NOTÍCIA
    st.header("📰 Gerador de Notícias")
    
    # Seleção da liga
    liga_noticia = st.selectbox(
        "Escolha a Liga",
        ["Premier League", "Championship"]
    )
    
    # Mapear para chave
    liga_key_map = {
        "Premier League": "premierleague",
        "Championship": "championship"
    }
    liga_key = liga_key_map[liga_noticia]
    
    # Input da manchete
    manchete = st.text_area(
        "Digite a manchete",
        placeholder="Ex: JOGADOR X CONTRATADO",
        height=100,
        help="O texto será automaticamente dividido em linhas balanceadas se for muito longo"
    )
    
    # Upload de imagem de fundo (NOVO)
    background = st.file_uploader(
        "Upload da imagem de fundo (opcional)", 
        type=["png", "jpg", "jpeg", "webp", "avif"]
    )
    
    # Alinhamento do background (NOVO)
    alinhamento = st.radio(
        "Alinhamento da imagem de fundo:", 
        ["Centro", "Esquerda", "Direita"], 
        horizontal=True
    )
    
    if st.button("🖼️ Gerar Notícia", type="primary"):
        if not manchete.strip():
            st.error("❌ Digite uma manchete!")
        else:
            try:
                # Salvar background temporário se foi enviado
                bg_path = None
                if background:
                    img = Image.open(background).convert("RGBA")
                    bg_path = "temp_bg_noticia.png"
                    img.save(bg_path, format="PNG")
                
                generator = NewsGenerator()
                
                img = generator.generate_news_image(
                    league=liga_key,
                    headline=manchete,
                    background=bg_path,
                    alinhamento=alinhamento
                )
                
                st.image(img, caption="Notícia Gerada")
                
                # Salvar como PNG
                img.save("noticia.png", format="PNG")
                
                with open("noticia.png", "rb") as f:
                    # Nome do arquivo baseado na manchete (primeiras palavras)
                    palavras = manchete.split()[:3]
                    nome_arquivo = "-".join(palavras).replace(" ", "-") + ".png"
                    
                    st.download_button(
                        "📥 Baixar Notícia",
                        f,
                        file_name=nome_arquivo,
                        width='stretch'
                    )
                
                # Limpar arquivo temporário
                if bg_path and os.path.exists(bg_path):
                    os.remove(bg_path)
            
            except Exception as e:
                st.error(f"❌ Erro ao gerar notícia: {str(e)}")
elif modo == "🏆 Gerar Copa":
    # MODO COPA
    st.header("🏆 Gerador de Copas")
    
    # Seleção da copa
    copa_selecionada = st.selectbox(
        "Escolha a Copa",
        ["FA Cup", "EFL Cup"]
    )
    
    copa_key = "facup" if copa_selecionada == "FA Cup" else "eflcup"
    
    # Título da fase
    titulo_fase = st.text_input(
        "Título da Fase",
        placeholder="Ex: 3ª RODADA - RESULTADOS",
        help="Texto que aparecerá no topo da imagem"
    )
    
    # Input dos resultados
    resultados_texto = st.text_area(
        "Cole os resultados (um por linha)",
        placeholder="POR 1-0 SOU\nCOV 2-1 WAT\nHUL D-D MID",
        height=200,
        help="Formato: ABV 1-0 XYZ. Use D-D para jogos futuros, ADI. para adiados, ABD. para abandonados"
    )
    
    if st.button("🖼️ Gerar Imagens da Copa", type="primary"):
        if not titulo_fase.strip():
            st.error("❌ Digite um título para a fase!")
        elif not resultados_texto.strip():
            st.error("❌ Insira pelo menos um resultado!")
        else:
            try:
                # Parse dos resultados
                from utils.results_parser import ResultsParser
                parser = ResultsParser()
                resultados = parser.parse_multiple_results(resultados_texto)
                
                if not resultados:
                    st.error("❌ Nenhum resultado válido encontrado! Verifique o formato.")
                else:
                    st.success(f"✅ {len(resultados)} resultado(s) processado(s)!")
                    
                    # Gerar imagens
                    generator = CupGenerator()
                    images = generator.generate_cup_images(
                        cup=copa_key,
                        results=resultados,
                        title=titulo_fase
                    )
                    
                    # SALVAR NA SESSÃO (para não perder após download)
                    st.session_state['imagens_copa_geradas'] = images
                    st.session_state['copa_selecionada'] = copa_selecionada
                    
                    st.success(f"✅ {len(images)} imagem(ns) gerada(s)!")
            
            except Exception as e:
                st.error(f"❌ Erro ao gerar imagens: {str(e)}")
                import traceback
                with st.expander("Ver detalhes do erro"):
                    st.code(traceback.format_exc())

    # ========================================================
    # MOSTRAR E BAIXAR IMAGENS (FORA DO BOTÃO)
    # ========================================================
    if 'imagens_copa_geradas' in st.session_state:
        st.divider()
        st.subheader("📸 Imagens Geradas")
        
        images = st.session_state['imagens_copa_geradas']
        copa_nome = st.session_state.get('copa_selecionada', 'Copa')
        
        # BOTÃO PARA BAIXAR TODAS DE UMA VEZ
        if len(images) > 1:
            import io
            import zipfile
            
            # Criar ZIP em memória
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for idx, img in enumerate(images, start=1):
                    # Salvar imagem em buffer
                    img_buffer = io.BytesIO()
                    img.save(img_buffer, format="PNG")
                    img_buffer.seek(0)
                    
                    # Adicionar ao ZIP
                    filename = f"{copa_nome.replace(' ', '-')}-{idx}.png"
                    zip_file.writestr(filename, img_buffer.getvalue())
            
            zip_buffer.seek(0)
            
            st.download_button(
                "📦 Baixar Todas as Imagens (ZIP)",
                zip_buffer,
                file_name=f"{copa_nome.replace(' ', '-')}-todas.zip",
                mime="application/zip",
                width='stretch',
                type="primary"
            )
            
            st.divider()
        
        # Mostrar cada imagem individualmente
        for idx, img in enumerate(images, start=1):
            st.image(img, caption=f"Imagem {idx} de {len(images)}")
            
            # Salvar temporariamente
            filename = f"copa_{idx}.png"
            img.save(filename, format="PNG")
            
            # Botão de download individual
            with open(filename, "rb") as f:
                st.download_button(
                    f"📥 Baixar Imagem {idx}",
                    f,
                    file_name=f"{copa_nome.replace(' ', '-')}-{idx}.png",
                    mime="image/png",
                    width='stretch',
                    key=f"download_copa_{idx}"  # ← Key única evita conflitos
                )
            
            if idx < len(images):
                st.divider()
elif modo == "📈 Estatísticas":
    render_stats_mode()
else:
    # MODO TABELA COM RESULTADOS
    render_table_mode()