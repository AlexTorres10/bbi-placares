"""
Gerador de imagens para resultados e tabelas
"""
from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Optional, Tuple
import json
import os

class ImageGenerator:
    def __init__(self, config_path: str = "config/leagues_config.json"):
        """Inicializa o gerador com as configurações das ligas"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.leagues_config = json.load(f)
        
        # Carregar nomes de exibição encurtados por liga
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
        """
        badge = self._load_image(badge_path)
        badge.thumbnail(target_size, Image.LANCZOS)
        
        # Centralizar em canvas transparente
        canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
        pos_x = (target_size[0] - badge.width) // 2
        pos_y = (target_size[1] - badge.height) // 2
        canvas.paste(badge, (pos_x, pos_y), badge)
        
        return canvas
    
    def _get_badge_path(self, team_name: str, badges_folder: str) -> str:
        """
        Retorna o caminho do escudo de um time
        SEMPRE usa o nome COMPLETO (original) para buscar o escudo
        """
        # Lista de pastas de escudos para tentar
        possible_folders = [
            badges_folder,  # Pasta específica da liga
            "escudos-pl",
            "escudos-ch", 
            "escudos-l1",
            "escudos-l2",
            "escudos-nl",
            "escudos-nonleague"
        ]
        
        for folder in possible_folders:
            badge_path = os.path.join(folder, f"{team_name}.png")
            if os.path.exists(badge_path):
                return badge_path
        
        # Fallback: retornar caminho esperado (vai gerar erro claro)
        return os.path.join(badges_folder, f"{team_name}.png")
    
    def _get_display_name(self, team_name: str, league: str, context: str = 'results') -> str:
        """
        Retorna o nome de exibição do time
        
        Args:
            team_name: Nome completo do time
            league: Liga atual
            context: 'results' (encurtar) ou 'table' (manter completo)
        
        Returns:
            Nome para exibir
        """
        # TABELAS: sempre nome completo
        if context == 'table':
            return team_name
        
        # RESULTADOS: aplicar encurtamento se existir
        if context == 'results':
            if league in self.display_names:
                return self.display_names[league].get(team_name, team_name)
        
        return team_name
    
    def _adjust_european_zones_for_mode(self, zones: dict, table_mode_name: str) -> dict:
        """
        Ajusta as posições das zonas europeias baseado no modo selecionado
        
        Args:
            zones: Zonas originais da configuração
            table_mode_name: Nome do modo selecionado (ex: "G6 Europeu (5 UCL + 1 UEL)")
        
        Returns:
            Zonas ajustadas com posições corretas
        """
        if not table_mode_name:
            return zones
        
        # Criar cópia para não modificar o original
        adjusted_zones = zones.copy()
        
        # Mapear modos para configurações
        if "G6" in table_mode_name:
            # G6: 5 UCL + 1 UEL
            adjusted_zones['ucl']['positions'] = [1, 2, 3, 4, 5]
            adjusted_zones['uel']['positions'] = [6]
            adjusted_zones['uecl']['positions'] = []
        
        elif "G7" in table_mode_name and "1 UEL + 1 UECL" in table_mode_name:
            # G7: 5 UCL + 1 UEL + 1 UECL
            adjusted_zones['ucl']['positions'] = [1, 2, 3, 4, 5]
            adjusted_zones['uel']['positions'] = [6]
            adjusted_zones['uecl']['positions'] = [7]
        
        elif "G7" in table_mode_name and "2 UEL" in table_mode_name:
            # G7: 5 UCL + 2 UEL
            adjusted_zones['ucl']['positions'] = [1, 2, 3, 4, 5]
            adjusted_zones['uel']['positions'] = [6, 7]
            adjusted_zones['uecl']['positions'] = []
        
        elif "G8" in table_mode_name:
            # G8: 5 UCL + 2 UEL + 1 UECL
            adjusted_zones['ucl']['positions'] = [1, 2, 3, 4, 5]
            adjusted_zones['uel']['positions'] = [6, 7]
            adjusted_zones['uecl']['positions'] = [8]
        
        return adjusted_zones
    
    def _calculate_centered_rects(self, total_slots: int, num_matches: int, 
                                  start_y: int, gap: int) -> List[int]:
        """
        Calcula as posições Y dos rects centralizados
        
        Args:
            total_slots: Número total de slots disponíveis (10 ou 12)
            num_matches: Número de partidas a exibir
            start_y: Posição Y inicial
            gap: Espaçamento entre rects
        
        Retorna:
            Lista com as posições Y de cada rect
        """
        if num_matches > total_slots:
            num_matches = total_slots
        
        # Slots vão de 1 a total_slots
        # Se temos 4 jogos em 12 slots, usar slots 5, 6, 7, 8 (meio)
        first_slot = (total_slots - num_matches) // 2 + 1
        
        positions = []
        for i in range(num_matches):
            slot_number = first_slot + i
            y_pos = start_y + (slot_number - 1) * gap
            positions.append(y_pos)
        
        return positions
    
    def generate_results_image(self, league: str, results: List[Dict], 
                              round_number: Optional[int] = None,
                              is_postponed: bool = False) -> Image.Image:
        """
        Gera imagem de resultados de uma rodada
        
        Args:
            league: Nome da liga (premierleague, championship, etc)
            results: Lista de resultados parseados
            round_number: Número da rodada (ou None para "Jogos Atrasados")
            is_postponed: Se True, mostra "Jogos Atrasados" ao invés do número
        
        Retorna:
            Imagem PIL gerada
        """
        config = self.leagues_config[league]
        rt = config['results_template']
        
        # Carregar template base
        template_path = os.path.join("resultados", rt['template_file'])
        base = self._load_image(template_path)

        # Carregar rect base
        rect_path = os.path.join("resultados", rt['rect_file'])
        rect_base = self._load_image(rect_path)
        
        # Limitar número de resultados exibidos
        max_display = config['max_results_display']
        results_to_display = results[:max_display]
        
        # Calcular posições centralizadas
        rect_positions = self._calculate_centered_rects(
            total_slots=max_display,
            num_matches=len(results_to_display),
            start_y=rt['rect_start_position']['y'],
            gap=rt['rect_gap']
        )
        
        # Preparar fonte
        font_path = self._get_font_for_league(league, bold=False)
        font_team = ImageFont.truetype(font_path, rt['font_team_size'])
        font_score = ImageFont.truetype(self._get_font_for_league(league, bold=True), rt['font_score_size'])
        font_round = ImageFont.truetype(font_path, rt['font_round_size'])
        
        draw = ImageDraw.Draw(base)
        
        # Desenhar texto da rodada
        if is_postponed:
            round_text = "JOGOS ATRASADOS"
        else:
            round_text = f"RODADA {round_number}" if round_number else ""
        
        if round_text:
            # Medir largura do texto
            bbox = draw.textbbox((0, 0), round_text, font=font_round)
            text_width = bbox[2] - bbox[0]
            
            # CONDIÇÃO: National League usa X do JSON, outras centralizam
            if league == 'nationalleague':
                # National League: usar X do JSON (alinhado à esquerda)
                x_pos = rt['round_text_position']['x']
            else:
                # Outras ligas: centralizar
                x_pos = (base.width - text_width) // 2
            
            draw.text(
                (x_pos, rt['round_text_position']['y']),
                round_text,
                font=font_round,
                fill=rt['color_text']
            )
        
        # Desenhar cada resultado
        badges_folder = config['badges_folder']
        
        for idx, result in enumerate(results_to_display):
            y_pos = rect_positions[idx]
            x_pos = rt['rect_start_position']['x']
            
            # Colar rect
            base.paste(rect_base, (x_pos, y_pos), rect_base)
            
            # Carregar e colar escudos
            home_badge = self._resize_badge(
                self._get_badge_path(result['home_team'], badges_folder),  # ← Nome original
                (rt['badge_size']['width'], rt['badge_size']['height'])
            )

            away_badge = self._resize_badge(
                self._get_badge_path(result['away_team'], badges_folder),  # ← Nome original
                (rt['badge_size']['width'], rt['badge_size']['height'])
            )
                        
            base.paste(
                home_badge,
                (x_pos + rt['badge_home_offset']['x'], 
                 y_pos + rt['badge_home_offset']['y']),
                home_badge
            )
            base.paste(
                away_badge,
                (x_pos + rt['badge_away_offset']['x'],
                 y_pos + rt['badge_away_offset']['y']),
                away_badge
            )
            
            # Desenhar nomes dos times
            home_name = self._get_display_name(result['home_team'], league, 'results').upper()
            away_name = self._get_display_name(result['away_team'], league, 'results').upper()

            # NOME DO TIME MANDANTE - CENTRALIZADO
            bbox_home = draw.textbbox((0, 0), home_name, font=font_team)
            home_width = bbox_home[2] - bbox_home[0]
            home_x_centered = x_pos + rt['team_name_home_offset']['x'] - (home_width // 2)

            draw.text(
                (home_x_centered,
                y_pos + rt['team_name_home_offset']['y']),
                home_name,
                font=font_team,
                fill=rt['color_text']
            )

            # NOME DO TIME VISITANTE - CENTRALIZADO
            bbox_away = draw.textbbox((0, 0), away_name, font=font_team)
            away_width = bbox_away[2] - bbox_away[0]
            away_x_centered = x_pos + rt['team_name_away_offset']['x'] - (away_width // 2)

            draw.text(
                (away_x_centered,
                y_pos + rt['team_name_away_offset']['y']),
                away_name,
                font=font_team,
                fill=rt['color_text']
            )
            
            # Desenhar placar centralizado
            status = result.get('status', 'normal')

            if status == 'normal':
                # Placar normal
                score_text = f"{result['home_score']} - {result['away_score']}"
            elif status == 'future':
                # Jogo futuro - não mostrar nada
                score_text = ""
            elif status == 'vs':
                # Jogo futuro com vs.
                score_text = "vs."
            elif status == 'postponed':
                # Jogo adiado
                score_text = "ADI."
            elif status == 'abandoned':
                # Jogo abandonado
                score_text = "ABD."
            else:
                score_text = ""

            if score_text:  # Só desenha se tiver texto
                bbox_score = draw.textbbox((0, 0), score_text, font=font_score)
                score_width = bbox_score[2] - bbox_score[0]
                
                draw.text(
                    (x_pos + rt['score_offset']['x'] - score_width // 2,
                    y_pos + rt['score_offset']['y']),
                    score_text,
                    font=font_score,
                    fill=rt['color_score']
                )
        
        return base
    
    def _get_font_for_league(self, league: str, bold : bool) -> str:
        """Retorna o caminho da fonte para uma liga"""
        # Mapeamento simples - ajustar conforme suas fontes
        if not bold:
            font_map = {
                'premierleague': 'fontes/premierleague.otf',
                'championship': 'fontes/efl.otf',
                'leagueone': 'fontes/efl.otf',
                'leaguetwo': 'fontes/efl.otf',
                'nationalleague': 'fontes/nationalleague.otf'
            }
        else:
            font_map = {
                'premierleague': 'fontes/premierleague-bold.otf',
                'championship': 'fontes/efl-bold.otf',
                'leagueone': 'fontes/efl-bold.otf',
                'leaguetwo': 'fontes/efl-bold.otf',
                'nationalleague': 'fontes/nationalleague.otf'
            }
        return font_map.get(league, 'fontes/FontePlacar.ttf')
    
    def generate_table_image(self, league: str, table_data: List[Dict],
                            confirmations: Optional[Dict] = None,
                            table_mode: Optional[Dict] = None) -> Image.Image:
        """
        Gera imagem da tabela de classificação
        
        Args:
            league: Nome da liga
            table_data: Lista de dicionários com dados dos times
            confirmations: Dict com confirmações {position: {'champion': True, 'ucl': True, ...}}
            table_mode: Para PL, dict com configuração de vagas europeias
        
        Retorna:
            Imagem PIL gerada
        """
        config = self.leagues_config[league]
        tt = config['table_template']
        
        # Carregar template da tabela como base
        template_file = tt.get('template_file', f'{league}-template.png')
        template_path = os.path.join("tabela", template_file)
        
        if os.path.exists(template_path):
            base = self._load_image(template_path)
        else:
            # Se não existir template específico, tentar usar o template geral
            fallback_path = os.path.join("tabela", f"template-{league}.png")
            if os.path.exists(fallback_path):
                base = self._load_image(fallback_path)
            else:
                raise FileNotFoundError(f"Template de tabela não encontrado: {template_path} ou {fallback_path}")
        
        draw = ImageDraw.Draw(base)
        
        # Carregar fontes
        font_path = self._get_font_for_league(league, bold=False)
        font_normal = ImageFont.truetype(font_path, tt['font_size'])
        font_bold = ImageFont.truetype(self._get_font_for_league(league, bold=True), tt['font_bold_size'])

        badges_folder = config['badges_folder']
        # AJUSTAR ZONAS EUROPEIAS PARA PREMIER LEAGUE
        zones = config['promotion_zones'].copy()
        if league == 'premierleague' and table_mode:
            zones = self._adjust_european_zones_for_mode(zones, table_mode)

        if league == 'nationalleague':
            header_y = tt['table_start']['y'] - 35  # Nacional precisa de mais espaço
        else:
            header_y = tt['table_start']['y'] - 30
        header_labels = {
            'J': 'J',
            'V': 'V', 
            'E': 'E',
            'D': 'D',
            'SG': 'SG',
            'PTS': 'PTS'
        }
        
        for key, label in header_labels.items():
            if key in tt['stats_columns']:
                x_pos = tt['stats_columns'][key]
                
                # Centralizar texto
                bbox = draw.textbbox((0, 0), label, font=font_bold)
                label_width = bbox[2] - bbox[0]
                
                draw.text(
                    (x_pos - label_width // 2, header_y),
                    label,
                    font=font_bold,
                    fill=tt['color_text']
                )
        
        # Desenhar cada linha da tabela
        for idx, team in enumerate(table_data):
            y_pos = tt['table_start']['y'] + (idx * tt['row_height'])
            
            # Determinar qual rect usar baseado na posição
            rect_img = self._get_rect_for_position(
                league, idx + 1, confirmations, zones
            )
            
            if rect_img:
                rect_x = tt['table_start']['x']
                base.paste(rect_img, (rect_x, y_pos), rect_img)
            
            # DESENHAR NÚMERO DA POSIÇÃO (BOLD, BRANCO)
            position_number = str(idx + 1)
            position_x = tt['table_start']['x'] + tt.get('position_offset', {}).get('x', 30)
            position_y = y_pos + tt.get('position_offset', {}).get('y', 18)

            # Medir largura para centralizar
            bbox_pos = font_bold.getbbox(position_number)
            pos_width = bbox_pos[2] - bbox_pos[0]

            # Desenhar texto branco, bold
            draw.text(
                (position_x - pos_width // 2, position_y),
                position_number,
                font=font_bold,
                fill=tt['color_text']
            )
            
            # Escudo
            badge = self._resize_badge(
                self._get_badge_path(team['name'], badges_folder),
                (tt['badge_size']['width'], tt['badge_size']['height'])
            )
            base.paste(
                badge,
                (tt['table_start']['x'] + tt['badge_offset']['x'], y_pos + tt['badge_offset']['y']),
                badge
            )
            
            # Nome do time
            team_name = team['name']  # ← MANTER COMPLETO, sem aplicar display_name


            # Verificar se time tem penalidade
            if 'penalty_note' in team and team['penalty_note']:
                team_name += "*"  # Adiciona asterisco

            draw.text(
                (tt['table_start']['x'] + tt['team_name_offset']['x'], y_pos + tt['team_name_offset']['y']),
                team_name.upper(),  # ← Nome completo
                font=font_normal,
                fill=tt['color_text']
            )

            
            # Estatísticas
            stats = [
                str(team['games']),
                str(team['wins']),
                str(team['draws']),
                str(team['losses']),
                str(team['goal_difference']),
                str(team['points'])
            ]

            stat_keys = ['J', 'V', 'E', 'D', 'SG', 'PTS']

            for stat, key in zip(stats, stat_keys):
                x_pos = tt['stats_columns'][key]
                
                # Pontos em negrito
                current_font = font_bold if key == 'PTS' else font_normal
                
                # Centralizar texto na coluna
                bbox = draw.textbbox((0, 0), stat, font=current_font)
                stat_width = bbox[2] - bbox[0]
                
                # AJUSTE VERTICAL PARA BOLD NAS LIGAS EFL
                y_offset = 0
                if key == 'PTS' and league in ['championship', 'leagueone', 'leaguetwo']:
                    y_offset = 13
                
                draw.text(
                    (x_pos - stat_width // 2, y_pos + tt['team_name_offset']['y'] + y_offset),
                    stat,
                    font=current_font,
                    fill=tt['color_text']
                )

            penalty_notes = []
            for team in table_data:
                if 'penalty_note' in team and team['penalty_note']:
                    penalty_notes.append(f"* {team['penalty_note']}")

            if penalty_notes:
                # Posição da primeira nota
                notes_y = tt['table_start']['y'] + (len(table_data) * tt['row_height']) + 20
                font_note = ImageFont.truetype(self._get_font_for_league(league, bold=False), tt.get('font_note_size', 20))

                for idx, note in enumerate(penalty_notes):
                    draw.text(
                        (tt['table_start']['x'] - 30, notes_y + (idx * 25)),  # ← -30 em vez de +20 (mais à esquerda)
                        note,
                        font=font_note,
                        fill=tt['color_text']
                    )
            
        return base
    
    def _get_rect_for_position(self, league: str, position: int,
                           confirmations: Optional[Dict],
                           table_mode: Optional[Dict]) -> Optional[Image.Image]:
        """
        Retorna a imagem do rect apropriado para uma posição
        """
        config = self.leagues_config[league]
        zones = config['promotion_zones']
        
        # Para Premier League, verificar confirmações
        if league == "premierleague" and confirmations and position in confirmations:
            pos_conf = confirmations[position]
            
            # Verificar na ordem: champion > ucl > uel > uecl > relegation
            if pos_conf.get('champion'):
                rect_file = zones['champion']['rect_confirmed']
            elif pos_conf.get('ucl'):
                rect_file = zones['ucl']['rect_confirmed']
            elif pos_conf.get('uel'):
                rect_file = zones['uel']['rect_confirmed']
            elif pos_conf.get('uecl'):
                rect_file = zones['uecl']['rect_confirmed']
            elif pos_conf.get('relegated'):
                rect_file = zones['relegation']['rect_confirmed']
            else:
                # Não confirmado, usar rect padrão baseado na posição
                return self._get_default_rect_for_position(league, position, zones)
            
            rect_path = os.path.join("tabela", rect_file)
            if os.path.exists(rect_path):
                return self._load_image(rect_path)
        
        # Lógica padrão para outras ligas ou sem confirmação
        return self._get_default_rect_for_position(league, position, zones)

    def _get_default_rect_for_position(self, league: str, position: int, zones: dict):
        """Retorna rect padrão baseado na posição"""
        # Primeiro tenta encontrar em alguma zona específica
        for zone_name, zone_config in zones.items():
            if position in zone_config['positions']:
                rect_file = zone_config['rect']
                rect_path = os.path.join("tabela", rect_file)
                if os.path.exists(rect_path):
                    return self._load_image(rect_path)
        
        # Se não estiver em nenhuma zona, usar rect neutro
        neutral_rect = f"{league}-rect.png"
        rect_path = os.path.join("tabela", neutral_rect)
        if os.path.exists(rect_path):
            return self._load_image(rect_path)
        
        return None