import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import os
import re
import json
import sys
from typing import Dict, List, Optional

# Adicionar utils ao path
sys.path.append(os.path.dirname(__file__))

from utils.results_parser import ResultsParser
from utils.table_processor import TableProcessor
from utils.image_generator import ImageGenerator
from utils.github_handler import GitHubHandler
from utils.news_generator import NewsGenerator

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
    "championship.png": "Championship",
    "inglaterra.png": "Seleção Inglesa",
}

TEMPLATE_ORDER = [
    "premierleague.png",
    "ucl.png",
    "uel.png",
    "uecl.png",
    "facup.png",
    "eflcup.png",
    "championship.png",
    "inglaterra.png"
]

INGLES_UCL = ["Arsenal", "Manchester City", "Liverpool", "Chelsea", "Newcastle United", "Tottenham"]
INGLES_UEL = ["Aston Villa", "Nottingham Forest"]
INGLES_UECL = ["Crystal Palace"]

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
    
    if any(comp in template_name for comp in ["facup", "eflcup"]):
        leagues = ['escudos-pl', 'escudos-ch', 'escudos-l1', 'escudos-l2']
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
    elif "championship" in nome or "efl" in nome or "eflcup" in nome:
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
    elif "championship" in nome or "efl" in nome:
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
              "escudos-ucl", "escudos-uel", "escudos-uecl", "selecoes"]
    
    for pasta in pastas:
        caminho = os.path.join(pasta, f"{team_name}.png")
        if os.path.exists(caminho):
            return caminho
    
    return None


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
    fonte_pequena = ImageFont.truetype(config["fonte_normal"], 25)
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
        else:
            label = ""
            valor = conteudo  # fallback

        agregado_texto = label + valor
        
        path_lower = template_path.lower()
        mais_pra_cima = any(comp in path_lower for comp in ["uel", "uecl", "efl", "championship"])

        y_agregado = 975 if mais_pra_cima else 985

        w_agr = fonte_pequena.getbbox(agregado_texto)[2] - fonte_pequena.getbbox(agregado_texto)[0]
        draw.text(((base.width - w_agr) // 2, y_agregado), agregado_texto, font=fonte_pequena, fill=cor_texto)

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
    
    # Botão de processar
    if st.button("🔄 Processar Resultados", type="primary"):
        if not resultados_texto.strip():
            st.error("❌ Por favor, insira pelo menos um resultado!")
            return
        
        # Parse dos resultados
        parser = ResultsParser()
        resultados = parser.parse_multiple_results(resultados_texto)
        
        if not resultados:
            st.error("❌ Nenhum resultado válido encontrado! Verifique o formato.")
            return
        
        # Mostrar resultados parseados
        st.success(f"✅ {len(resultados)} resultado(s) processado(s)!")
        
        with st.expander("Ver resultados parseados"):
            for r in resultados:
                status = r.get('status', 'normal')
                
                if status == 'normal':
                    st.write(f"**{r['home_team']}** {r['home_score']}-{r['away_score']} **{r['away_team']}**")
                elif status == 'future':
                    st.write(f"**{r['home_team']}** vs **{r['away_team']}** - ⏰ *Jogo futuro*")
                elif status == 'postponed':
                    st.write(f"**{r['home_team']}** vs **{r['away_team']}** - 🔄 *Adiado*")
                elif status == 'abandoned':
                    st.write(f"**{r['home_team']}** vs **{r['away_team']}** - ⚠️ *Abandonado*")
        
        # Salvar na sessão
        st.session_state['resultados_parseados'] = resultados
        st.session_state['tipo_rodada'] = tipo_rodada
        st.session_state['numero_rodada'] = numero_rodada
        st.session_state['liga_selecionada'] = liga_key
        
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
            if st.button("📸 Gerar Imagem da Rodada", type="primary", use_container_width=True):
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
            if st.button("📊 Gerar Imagem da Tabela", type="primary", use_container_width=True):
                try:
                    # Processar tabela com resultados
                    processor = TableProcessor()
                    
                    # Carregar tabela original
                    tabela_path = f"data/tabelas/{st.session_state['liga_selecionada']}.txt"
                    with open(tabela_path, 'r', encoding='utf-8') as f:
                        processor.load_from_text(f.read())
                    
                    # Aplicar resultados
                    processor.update_with_multiple_results(st.session_state['resultados_parseados'])
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
                        if team.name == "Sheffield Wednesday" and team.points < 0:
                            team_dict['penalty_note'] = "Sheffield Wednesday perdeu 18 pontos por administração judicial e atraso de salários"
                        
                        table_data.append(team_dict)
                    
                    # Gerar imagem
                    generator = ImageGenerator()
                    img = generator.generate_table_image(
                        league=st.session_state['liga_selecionada'],
                        table_data=table_data,
                        confirmations=confirmations,
                        table_mode=st.session_state.get('table_mode')
                    )
                    
                    # Salvar na sessão
                    st.session_state['imagem_tabela_gerada'] = img
                    st.session_state['tabela_processada'] = processor.to_text()
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
                        st.download_button(
                            "📥 Baixar Imagem da Rodada", 
                            f, 
                            file_name=f"M{st.session_state.get('numero_rodada', 'atrasados')}-R.png",
                            use_container_width=True
                        )
            
            with col2:
                if 'imagem_tabela_gerada' in st.session_state:
                    st.image(st.session_state['imagem_tabela_gerada'], caption="Imagem da Tabela")
                    
                    # Salvar e oferecer download
                    img_rgb = st.session_state['imagem_tabela_gerada'].convert("RGB")
                    img_rgb.save("tabela.png", format="PNG")
                    
                    with open("tabela.png", "rb") as f:
                        st.download_button(
                            "📥 Baixar Tabela", 
                            f, 
                            file_name=f"M{st.session_state.get('numero_rodada', 'atrasados')}-T.png",
                            use_container_width=True
                        )
            
            # ================================================================
            # BOTÃO DE ATUALIZAR GITHUB (SÓ APARECE SE IMAGENS FORAM GERADAS)
            # ================================================================
            st.divider()
            
            if st.button("🚀 Atualizar Tabela no GitHub", type="secondary", use_container_width=True):
                if 'tabela_processada' not in st.session_state:
                    st.error("❌ Gere a tabela primeiro!")
                else:
                    # Verificar se GitHub está configurado
                    if 'GITHUB_TOKEN' not in st.secrets or 'GITHUB_REPO' not in st.secrets:
                        st.error("❌ Configure GITHUB_TOKEN e GITHUB_REPO em .streamlit/secrets.toml")
                    else:
                        try:
                            github = GitHubHandler(
                                token=st.secrets['GITHUB_TOKEN'],
                                repo=st.secrets['GITHUB_REPO']
                            )
                            
                            file_path = f"data/tabelas/{st.session_state['liga_selecionada']}.txt"
                            
                            # Buscar SHA atual do arquivo
                            _, sha = github.get_file(file_path)
                            
                            if sha:
                                # Mensagem de commit
                                rodada_info = st.session_state.get('numero_rodada', 'atrasados')
                                num_resultados = len(st.session_state['resultados_parseados'])
                                liga_nome = st.session_state['liga_selecionada'].upper()
                                commit_msg = f"[{liga_nome}] Rodada {rodada_info} - {num_resultados} jogo(s)"
                                
                                # Atualizar no GitHub
                                with st.spinner("Enviando para o GitHub..."):
                                    success = github.update_file(
                                        file_path=file_path,
                                        content=st.session_state['tabela_processada'],
                                        commit_message=commit_msg,
                                        sha=sha
                                    )
                                
                                if success:
                                    st.success("✅ Tabela atualizada no GitHub!")
                                    st.balloons()
                                    
                                    # Limpar cache
                                    carregar_tabela_github.clear()
                                else:
                                    st.error("❌ Erro ao atualizar. Verifique as permissões do token.")
                            else:
                                st.error("❌ Arquivo não encontrado no GitHub.")
                        
                        except Exception as e:
                            st.error(f"❌ Erro: {str(e)}")

        
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
                'playoffs': st.session_state.get(f'nl_{pos}_playoffs', False),
                'playoffsqua': st.session_state.get(f'nl_{pos}_playoffsqua', False),
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
    
    selected_mode = st.selectbox("Modo da tabela", table_modes)
    
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


def render_confirmation_checkboxes_pl():
    """Checkboxes de confirmação para Premier League"""
    st.write("**1º Colocado:**")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.checkbox("Campeão", key="pl_1_champion")
    with col2:
        st.checkbox("UCL", key="pl_1_ucl")
    with col3:
        st.checkbox("UEL", key="pl_1_uel")
    with col4:
        st.checkbox("UECL", key="pl_1_uecl")
    
    # Repetir para posições 2-8
    # ... (implementar para todas as posições)
    
    st.write("**Zona de rebaixamento:**")
    for pos in [18, 19, 20]:
        st.checkbox(f"{pos}º Rebaixado", key=f"pl_{pos}_relegated")


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
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write("**2º**")
    with col2:
        st.checkbox("Promovido", key="ch_2_promoted")
    with col3:
        st.checkbox("Play-offs", key="ch_2_playoffs")
    
    # 3º ao 6º - Play-offs
    for pos in range(3, 7):
        col1, col2 = st.columns([1, 2])
        with col1:
            st.write(f"**{pos}º**")
        with col2:
            st.checkbox("Play-offs", key=f"ch_{pos}_playoffs")
    
    st.divider()
    
    st.write("**Zona de Rebaixamento:**")
    for pos in [22, 23, 24]:
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
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write("**2º**")
    with col2:
        st.checkbox("Promovido", key="l1_2_promoted")
    with col3:
        st.checkbox("Play-offs", key="l1_2_playoffs")

    # 3º ao 6º - Play-offs
    for pos in range(3, 7):
        col1, col2 = st.columns([1, 2])
        with col1:
            st.write(f"**{pos}º**")
        with col2:
            st.checkbox("Play-offs", key=f"l1_{pos}_playoffs")
    
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
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write("**1º**")
    with col2:
        st.checkbox("Campeão", key="nl_1_champion")

    # 2º colocado
    for pos in range(2, 4):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**2º**")
        with col2:
            st.checkbox("Promovido", key=f"nl_{pos}_playoff")
    
    
    # 3º ao 6º - Play-offs
    for pos in range(4, 8):
        col1, col2 = st.columns([1, 2])
        with col1:
            st.write(f"**{pos}º**")
        with col2:
            st.checkbox("Play-offs", key=f"nl_{pos}_playoffqua")
    
    st.divider()
    
    st.write("**Zona de Rebaixamento:**")
    for pos in [21, 22, 23, 24]:
        st.checkbox(f"{pos}º colocado - Rebaixado", key=f"nl_{pos}_relegated")


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
    ["📰 Gerar Notícia", "🔢 Gerar Placar", "📊 Gerar Tabela com Resultados"],
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

        st.image(img)

        img_rgb = img.convert("RGB")
        img_rgb.save("placar_final.jpg", format="JPEG", quality=100)

        with open("placar_final.jpg", "rb") as f:
            nome_arquivo = f"{mandante} {placar} {visitante}.jpg".replace("/", "-")
            st.download_button("📥 Baixar Imagem", f, file_name=nome_arquivo)
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
                        use_container_width=True
                    )
                
                # Limpar arquivo temporário
                if bg_path and os.path.exists(bg_path):
                    os.remove(bg_path)
            
            except Exception as e:
                st.error(f"❌ Erro ao gerar notícia: {str(e)}")

else:
    # MODO TABELA COM RESULTADOS
    render_table_mode()
