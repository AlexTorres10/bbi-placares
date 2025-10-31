import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import os
import re
import pillow_avif

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

def carregar_escudos(template_path):
    template_name = os.path.basename(template_path).lower()
    
    # Seleção Inglesa - apenas pasta "selecoes"
    if "inglaterra" in template_name:
        if os.path.exists("selecoes"):
            return sorted([f[:-4] for f in os.listdir("selecoes") if f.endswith(".png")])
        return []
    
    # Champions League
    if "ucl" in template_name:
        # Ingleses UCL da pasta escudos-pl
        ingleses_ucl = []
        if os.path.exists("escudos-pl"):
            todos_pl = [f[:-4] for f in os.listdir("escudos-pl") if f.endswith(".png")]
            # Filtrar apenas os ingleses UCL (mantendo ordem de INGLES_UCL)
            ingleses_ucl = [nome for nome in INGLES_UCL if nome in todos_pl]
        
        # Europeus UCL
        europeus_ucl = []
        if os.path.exists("escudos-ucl"):
            europeus_ucl = sorted([f[:-4] for f in os.listdir("escudos-ucl") if f.endswith(".png")])
        
        return ingleses_ucl + europeus_ucl
    
    # Europa League
    if "uel" in template_name:
        # Ingleses UEL da pasta escudos-pl
        ingleses_uel = []
        if os.path.exists("escudos-pl"):
            todos_pl = [f[:-4] for f in os.listdir("escudos-pl") if f.endswith(".png")]
            # Filtrar apenas os ingleses UEL (mantendo ordem de INGLES_UEL)
            ingleses_uel = [nome for nome in INGLES_UEL if nome in todos_pl]
        
        # Europeus UEL
        europeus_uel = []
        if os.path.exists("escudos-uel"):
            europeus_uel = sorted([f[:-4] for f in os.listdir("escudos-uel") if f.endswith(".png")])
        
        return ingleses_uel + europeus_uel
    
    # Conference League
    if "uecl" in template_name:
        # Ingleses UECL da pasta escudos-pl
        ingleses_uecl = []
        if os.path.exists("escudos-pl"):
            todos_pl = [f[:-4] for f in os.listdir("escudos-pl") if f.endswith(".png")]
            # Filtrar apenas os ingleses UECL (mantendo ordem de INGLES_UECL)
            ingleses_uecl = [nome for nome in INGLES_UECL if nome in todos_pl]
        
        # Europeus UECL
        europeus_uecl = []
        if os.path.exists("escudos-uecl"):
            europeus_uecl = sorted([f[:-4] for f in os.listdir("escudos-uecl") if f.endswith(".png")])
        
        return ingleses_uecl + europeus_uecl
    
    # Premier League - apenas escudos-pl
    if "premier" in template_name:
        if os.path.exists("escudos-pl"):
            return sorted([f[:-4] for f in os.listdir("escudos-pl") if f.endswith(".png")])
        return []
    
    # Championship - apenas escudos-ch
    if "championship" in template_name:
        if os.path.exists("escudos-ch"):
            return sorted([f[:-4] for f in os.listdir("escudos-ch") if f.endswith(".png")])
        return []
    
    # FA Cup e EFL Cup - escudos-pl + escudos-ch (PL primeiro)
    if any(comp in template_name for comp in ["facup", "eflcup"]):
        times_pl = []
        times_ch = []

        leagues = ['escudos-pl', 'escudos-ch', 'escudos-l1', 'escudos-l2']

        times_total = []
        for div in leagues:
            if os.path.exists(div):
                times = sorted([f[:-4] for f in os.listdir(div) if f.endswith(".png")])
                times_total.extend(times)

        return times_total
    
    # Fallback - retorna vazio se não encontrar correspondência
    return []


def obter_fontes_por_template(template_path):
    nome = os.path.splitext(os.path.basename(template_path))[0].lower()

    if "premier" in nome:
        return ("fontes/premierleague.ttf", "fontes/premierleague-bold.ttf")
    elif "championship" in nome or "efl" in nome or "eflcup" in nome:
        return ("fontes/efl.ttf", "fontes/efl-bold.ttf")
    elif "facup" in nome:
        return ("fontes/facup.ttf", "fontes/facup-bold.ttf")
    elif "ucl" in nome:
        return ("fontes/ucl.ttf", "fontes/ucl-bold.ttf")
    elif "uel" in nome:
        return ("fontes/uel.ttf", "fontes/uel-bold.ttf")
    elif "inglaterra" in nome:
        return ("fontes/ing.ttf", "fontes/ing.ttf")  # fonte para seleção
    else:
        return ("fontes/FontePlacar.ttf", "fontes/FontePlacar.ttf")  # fallback


def redimensionar_escudo(filepath, target_size=(100, 100)):
    escudo = Image.open(filepath).convert("RGBA")
    escudo.thumbnail(target_size, Image.LANCZOS)  # mantém proporção

    # Criar imagem de fundo transparente do tamanho fixo
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
            "fonte_normal": "fontes/efl.ttf",
            "fonte_bold": "fontes/efl-bold.ttf",
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


def obter_escudo_path(nome_time):
    # Buscar nas diferentes pastas na ordem de prioridade
    pastas = ["escudos-pl", "escudos-ch", "escudos-ucl", "escudos-uel", "escudos-uecl", 
              "selecoes", "escudos-l1", "escudos-l2"]
    
    for pasta in pastas:
        caminho = os.path.join(pasta, f"{nome_time}.png")
        if os.path.exists(caminho):
            return caminho
    
    return None
    

def desenhar_placar(template_path, escudo_casa, escudo_fora, placar_texto, marcadores_casa, marcadores_fora, background=None):
    base = Image.open(template_path).convert("RGBA")

    # Inserir imagem de fundo proporcional e centralizado
    if background:
        bg_raw = Image.open(background).convert("RGBA")
        # Calcula o fator de escala para garantir que bg seja >= base em ambas dimensões
        scale_w = base.width / bg_raw.width
        scale_h = base.height / bg_raw.height
        scale = max(scale_w, scale_h)
        new_width = int(bg_raw.width * scale)
        new_height = int(bg_raw.height * scale)
        bg_resized = bg_raw.resize((new_width, new_height), Image.LANCZOS)

        # Recorta centralizado para o tamanho exato do base
        left = (new_width - base.width) // 2
        top = (new_height - base.height) // 2
        bg_cropped = bg_resized.crop((left, top, left + base.width, top + base.height))

        # Centraliza o base sobre o fundo
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



st.title("🔢 Gerador de Placares BBI")
st.set_page_config(
    page_title="Gerador de Placares BBI",
    page_icon="bbi.png",  # Emoji como ícone
    layout="centered"
)
templates = [f for f in os.listdir(TEMPLATE_DIR) if f.endswith(".png")]
templates = [f for f in TEMPLATE_ORDER if f in TEMPLATE_LABELS]

template_escolhido_label = st.selectbox(
    "Escolha o Template",
    [TEMPLATE_LABELS[t] for t in templates]
)

# Converter de volta para o nome do arquivo
template_escolhido = [k for k, v in TEMPLATE_LABELS.items() if v == template_escolhido_label][0]
times = carregar_escudos(template_escolhido)
mandante = st.selectbox("Time Mandante", times)
visitante = st.selectbox("Time Visitante", times)
placar = st.text_input("Placar (ex: 1-0 ou 2-1 (3-2 agr.))")
marcadores_mandante = st.text_area("Marcadores do Mandante", placeholder="Jogador A 45'\nJogador B 67'")
marcadores_visitante = st.text_area("Marcadores do Visitante", placeholder="Jogador X 88'")
background = st.file_uploader("Upload da imagem de fundo (opcional)", type=["png", "jpg", "jpeg", "webp", "avif"])

if st.button("Gerar Placar"):
    template_path = os.path.join(TEMPLATE_DIR, template_escolhido)
    bg_path = None
    if background:
        # Abre a imagem com Pillow a partir do upload
        img = Image.open(background).convert("RGBA")

        # Salva sempre como PNG para o uso interno no app
        bg_path = "temp_bg.png"
        img.save(bg_path, format="PNG")
    
    # Gera o placar final (em RGBA)
    img = desenhar_placar(
        template_path, mandante, visitante, placar,
        marcadores_mandante, marcadores_visitante,
        background=bg_path
    )

    st.image(img)

    # Converte para RGB (JPEG não aceita transparência)
    img_rgb = img.convert("RGB")
    img_rgb.save("placar_final.jpg", format="JPEG", quality=100)

    with open("placar_final.jpg", "rb") as f:
        # Monta o nome do arquivo: "Mandante 1-0 Visitante.jpg"
        nome_arquivo = f"{mandante} {placar} {visitante}.jpg".replace("/", "-")
        st.download_button("📥 Baixar Imagem", f, file_name=nome_arquivo)