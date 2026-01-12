"""
Gerador de imagens para copas (FA Cup e EFL Cup)
"""
from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Tuple
import json
import os
import math

class CupGenerator:
    def __init__(self, config_path: str = "config/leagues_config.json"):
        """Inicializa o gerador de copas"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.leagues_config = json.load(f)
        
        # Carregar nomes de exibição encurtados
        display_names_path = "config/team_display_names.json"
        if os.path.exists(display_names_path):
            with open(display_names_path, 'r', encoding='utf-8') as f:
                self.display_names = json.load(f)
        else:
            self.display_names = {}
    
    def _load_image(self, path: str) -> Image.Image:
        """Carrega uma imagem e converte para RGBA"""
        return Image.open(path).convert("RGBA")
    
    def _resize_badge(self, badge_path: str, target_size: Tuple[int, int]) -> Image.Image:
        """
        Redimensiona um escudo mantendo proporções e centralizando
        O escudo NUNCA ultrapassa o target_size
        """
        badge = self._load_image(badge_path)
        
        # Usar thumbnail para manter proporções SEM ultrapassar o target
        badge.thumbnail(target_size, Image.LANCZOS)
        
        # Centralizar em canvas transparente
        canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
        pos_x = (target_size[0] - badge.width) // 2
        pos_y = (target_size[1] - badge.height) // 2
        canvas.paste(badge, (pos_x, pos_y), badge)
        
        return canvas
   

    def _get_badge_path(self, team_name: str, cup: str) -> str:
        """
        Retorna o caminho do escudo de um time
        Procura em todas as pastas de escudos
        """
        badge_folders = [
            "escudos-pl",
            "escudos-ch",
            "escudos-l1",
            "escudos-l2",
            "escudos-nl",
            "escudos-nonleague"
        ]
        
        for folder in badge_folders:
            badge_path = os.path.join(folder, f"{team_name}.png")
            if os.path.exists(badge_path):
                return badge_path
        
        # Se não encontrou, retornar caminho padrão
        return os.path.join("escudos-pl", f"{team_name}.png")
    
    def _get_display_name(self, team_name: str, cup: str) -> str:
        """Retorna o nome de exibição do time (encurtado se necessário)"""
        # Para copas, usar nomes encurtados de todas as ligas
        for league_names in self.display_names.values():
            if team_name in league_names:
                return league_names[team_name]
        return team_name
    
    def _get_font_for_cup(self, cup: str, bold: bool = False) -> str:
        """Retorna o caminho da fonte para uma copa"""
        font_map = {
            'facup': {
                'normal': 'fontes/facup.otf',
                'bold': 'fontes/facup-bold.otf'
            },
            'eflcup': {
                'normal': 'fontes/efl.otf',
                'bold': 'fontes/efl-bold.otf'
            }
        }
        
        cup_fonts = font_map.get(cup, {
            'normal': 'fontes/FontePlacar.ttf',
            'bold': 'fontes/FontePlacar.ttf'
        })
        
        font_type = 'bold' if bold else 'normal'
        return cup_fonts[font_type]
    
    def distribuir_jogos(self, num_jogos: int, num_artes: int, max_camadas: int) -> List[int]:
        """
        Distribui jogos de forma balanceada entre múltiplas artes
        Exemplo: 19 jogos em 8 slots = [7, 6, 6] ao invés de [8, 8, 3]
        """
        jogos_por_arte = num_jogos // num_artes
        artes_com_jogo_extra = num_jogos % num_artes
        
        distribuicao = []
        
        for i in range(num_artes):
            if i < artes_com_jogo_extra:
                distribuicao.append(min(jogos_por_arte + 1, max_camadas))
            else:
                distribuicao.append(min(jogos_por_arte, max_camadas))
        
        return distribuicao
    
    def calcular_layers(self, distribuicao: List[int], max_slots: int) -> List[List[int]]:
        """
        Calcula quais slots usar em cada arte para centralizar os jogos
        """
        layers = []
        
        for dist in distribuicao:
            diff = max_slots - dist
            if diff > 0:
                # Centralizar: pular slots do início e fim
                inicio = math.floor(diff / 2)
                fim = max_slots - math.ceil(diff / 2)
                layers.append(list(range(inicio, fim)))
            else:
                layers.append(list(range(max_slots)))
        
        return layers
    
    def _create_double_badge(self, team1: str, team2: str, target_size: Tuple[int, int], cup: str) -> Image.Image:
        """
        Cria escudo duplo para times indefinidos (/)
        
        Os escudos ficam nos cantos: superior esquerdo e inferior direito
        Cada escudo tem metade do tamanho do target (50x50 se target é 100x100)
        
        Args:
            team1: Primeiro time (ex: Liverpool)
            team2: Segundo time (ex: Barnsley)
            target_size: Tamanho total (ex: 100x100)
            cup: Copa atual
        
        Returns:
            Imagem com 2 escudos nos cantos
        """
        # Cada escudo terá metade do tamanho
        half_size = (target_size[0] // 2, target_size[1] // 2)
        
        # Carregar e redimensionar escudos
        badge1_path = self._get_badge_path(team1, cup)
        badge2_path = self._get_badge_path(team2, cup)
        
        badge1 = self._resize_badge(badge1_path, half_size)
        badge2 = self._resize_badge(badge2_path, half_size)
        
        # Criar canvas transparente do tamanho completo
        double_badge = Image.new('RGBA', target_size, (0, 0, 0, 0))
        
        # Colar badge1 no canto SUPERIOR ESQUERDO (0, 0)
        double_badge.paste(badge1, (0, 0), badge1)
        
        # Colar badge2 no canto INFERIOR DIREITO
        pos_x = target_size[0] - half_size[0]  # Alinhado à direita
        pos_y = target_size[1] - half_size[1]  # Alinhado embaixo
        double_badge.paste(badge2, (pos_x, pos_y), badge2)
        
        return double_badge
    
    def _get_display_name_smart(self, team_name: str, cup: str, max_width: int, font) -> str:
        """
        Retorna nome de exibição, encurtando automaticamente se necessário
        
        Args:
            team_name: Nome do time (pode conter /)
            cup: Copa atual
            max_width: Largura máxima em pixels
            font: Fonte usada para medir
        
        Returns:
            Nome ajustado
        """
        from PIL import ImageDraw
        
        # Verificar se está no display_names (manual)
        display_name = self._get_display_name(team_name, cup)
        
        # Medir largura
        draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
        bbox = draw.textbbox((0, 0), display_name, font=font)
        width = bbox[2] - bbox[0]
        
        # Se cabe, retorna
        if width <= max_width:
            return display_name
        
        # Se tem /, encurtar cada time
        if '/' in display_name:
            teams = display_name.split('/')
            
            # Encurtar cada time individualmente
            shortened = []
            for team in teams:
                # Tentar abreviações comuns
                team = team.replace('United', 'Utd')
                team = team.replace('City', '')
                team = team.replace('Town', '')
                team = team.replace('Sheffield', 'Sheff')
                team = team.strip()
                
                # Se ainda grande, pegar primeiras 7 letras
                if len(team) > 8:
                    team = team[:7] + '.'
                
                shortened.append(team)
            
            return '/'.join(shortened)
        
        # Sem /, truncar normal
        if len(display_name) > 12:
            return display_name[:10] + '...'
        
        return display_name
    
    def generate_cup_images(self, cup: str, results: List[Dict], 
                           title: str) -> List[Image.Image]:
        """
        Gera imagens de copa (pode gerar múltiplas imagens)
        
        Args:
            cup: 'facup' ou 'eflcup'
            results: Lista de resultados parseados
            title: Título da fase (ex: "3ª FASE - RESULTADOS")
        
        Returns:
            Lista de imagens PIL geradas
        """
        # Configuração por copa
        if cup == 'facup':
            template_file = "facup-template.png"
            rect_file = "facup-rect.png"
            max_matches = 8
            font_size_team = 48
            font_size_score = 64
            font_size_title = 48
        else:  # eflcup
            template_file = "eflcup-template.png"
            rect_file = "eflcup-rect.png"
            max_matches = 12
            font_size_team = 28
            font_size_score = 36
            font_size_title = 36
        
        # Calcular distribuição
        num_jogos = len(results)
        num_artes = math.ceil(num_jogos / max_matches)
        distribuicao = self.distribuir_jogos(num_jogos, num_artes, max_matches)
        layers = self.calcular_layers(distribuicao, max_matches)
        
        # Gerar imagens
        images = []
        match_index = 0
        
        for arte_idx, slots_usados in enumerate(layers):
            # Carregar template
            template_path = os.path.join("resultados", template_file)
            base = self._load_image(template_path)
            
            # Carregar rect
            rect_path = os.path.join("resultados", rect_file)
            rect_base = self._load_image(rect_path)
            
            draw = ImageDraw.Draw(base)
            
            # Carregar fontes
            font_team = ImageFont.truetype(self._get_font_for_cup(cup, bold=False), font_size_team)
            font_score = ImageFont.truetype(self._get_font_for_cup(cup, bold=True), font_size_score)
            font_title = ImageFont.truetype(self._get_font_for_cup(cup, bold=True), font_size_title)
            
            # Desenhar título (centralizado)
            title_upper = title.upper()
            bbox = draw.textbbox((0, 0), title_upper, font=font_title)
            title_width = bbox[2] - bbox[0]
            title_x = (base.width - title_width) // 2
            
            # Posição do título (ajustar conforme template)
            title_y = 200 if cup == 'facup' else 160
            
            draw.text((title_x, title_y), title_upper, font=font_title, fill="#FFFFFF")
            
            # Configurações de posição (ajustar conforme seus templates)
            if cup == 'facup':
                rect_start_y = 260
                rect_gap = 155
                rect_x = 30
                badge_size = (100, 100)
                badge_home_x = 3
                badge_away_x = 1338
                badge_y = 3
                team_name_home_x = 382
                team_name_away_x = 1060
                team_name_y = 36
                score_x = 724
                score_y = 28
            else:  # eflcup
                rect_start_y = 220
                rect_gap = 75
                rect_x = 100
                badge_size = (50, 50)
                badge_home_x = 8
                badge_away_x = 818
                badge_y = 7
                team_name_home_x = 225
                team_name_away_x = 638
                team_name_y = 10
                score_x = 430
                score_y = 18
            
            # Desenhar cada jogo nos slots usados
            for slot_idx, slot in enumerate(slots_usados):
                result = results[match_index]
                match_index += 1
                
                # Calcular posição Y
                y_pos = rect_start_y + (slot * rect_gap)
                
                # Colar rect
                base.paste(rect_base, (rect_x, y_pos), rect_base)
                
                # ========================================
                # CARREGAR ESCUDOS (com suporte a TBD)
                # ========================================
                
                if result.get('is_home_tbd'):
                    # Time indefinido: criar escudo duplo
                    teams = result['home_team'].split('/')
                    home_badge = self._create_double_badge(
                        teams[0].strip(), 
                        teams[1].strip(), 
                        badge_size,
                        cup
                    )
                else:
                    # Time definido: escudo normal
                    home_badge = self._resize_badge(
                        self._get_badge_path(result['home_team'], cup),
                        badge_size
                    )

                if result.get('is_away_tbd'):
                    teams = result['away_team'].split('/')
                    away_badge = self._create_double_badge(
                        teams[0].strip(), 
                        teams[1].strip(), 
                        badge_size,
                        cup
                    )
                else:
                    away_badge = self._resize_badge(
                        self._get_badge_path(result['away_team'], cup),
                        badge_size
                    )

                # Colar escudos
                base.paste(home_badge, (rect_x + badge_home_x, y_pos + badge_y), home_badge)
                base.paste(away_badge, (rect_x + badge_away_x, y_pos + badge_y), away_badge)
                
                # ========================================
                # DESENHAR NOMES (com encurtamento smart)
                # ========================================
                
                home_name = self._get_display_name_smart(
                    result['home_team'], 
                    cup, 
                    max_width=400,  # Ajustar conforme necessário
                    font=font_team
                ).upper()
                
                away_name = self._get_display_name_smart(
                    result['away_team'], 
                    cup, 
                    max_width=400,
                    font=font_team
                ).upper()
                
                bbox_home = draw.textbbox((0, 0), home_name, font=font_team)
                home_width = bbox_home[2] - bbox_home[0]
                home_x_centered = rect_x + team_name_home_x - (home_width // 2)
                
                bbox_away = draw.textbbox((0, 0), away_name, font=font_team)
                away_width = bbox_away[2] - bbox_away[0]
                away_x_centered = rect_x + team_name_away_x - (away_width // 2)

                if cup == 'facup':
                    draw.text((home_x_centered, y_pos + team_name_y), home_name, 
                            font=font_team, fill="#383b38")
                    draw.text((away_x_centered, y_pos + team_name_y), away_name, 
                            font=font_team, fill="#383b38")
                else:
                    draw.text((home_x_centered, y_pos + team_name_y), home_name, 
                            font=font_team, fill="#FFFFFF")
                    draw.text((away_x_centered, y_pos + team_name_y), away_name, 
                            font=font_team, fill="#FFFFFF")
                
                # Desenhar placar
                status = result.get('status', 'normal')

                # Sempre mostrar placar para jogos normais, pênaltis e prorrogação
                if status in ['normal', 'penalties', 'extra_time']:
                    if cup == 'facup':
                        score_text = f"{result['home_score']}-{result['away_score']}"
                    else:
                        score_text = f"{result['home_score']} - {result['away_score']}"
                elif status == 'future':
                    score_text = ""
                elif status == 'vs':
                    score_text = "vs."
                elif status == 'postponed':
                    score_text = "ADI."
                elif status == 'abandoned':
                    score_text = "ABD."
                else:
                    score_text = ""

                if score_text:
                    bbox_score = draw.textbbox((0, 0), score_text, font=font_score)
                    score_width = bbox_score[2] - bbox_score[0]
                    
                    draw.text(
                        (rect_x + score_x - score_width // 2, y_pos + score_y),
                        score_text,
                        font=font_score,
                        fill="#FFFFFF"
                    )

                # DESENHAR INFORMAÇÃO EXTRA (Pênaltis ou Prorrogação)
                extra_info = result.get('extra_info')
                if extra_info:
                    # Fonte menor para info extra
                    font_extra_size = font_size_score - 22  # 14 pontos menor que o placar
                    font_extra = ImageFont.truetype(self._get_font_for_cup(cup, bold=False), font_extra_size)
                    
                    bbox_extra = draw.textbbox((0, 0), extra_info, font=font_extra)
                    extra_width = bbox_extra[2] - bbox_extra[0]
                    
                    # Posicionar abaixo do placar
                    extra_y = y_pos + score_y + 80  # 40px abaixo do placar
                    
                    draw.text(
                        (rect_x + score_x - extra_width // 2, extra_y),
                        extra_info,
                        font=font_extra,
                        fill="#FFFFFF"
                    )
            
            images.append(base)
        
        return images