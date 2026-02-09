"""
Gerador de imagens de notícias
"""
from PIL import Image, ImageDraw, ImageFont
import textwrap
import os

class NewsGenerator:
    def __init__(self):
        self.templates_dir = "noticias"
    
    def _load_image(self, path: str) -> Image.Image:
        """Carrega uma imagem e converte para RGBA"""
        return Image.open(path).convert("RGBA")
    
    def _get_font_for_league(self, league: str, bold: bool = True) -> str:
        """Retorna o caminho da fonte para uma liga"""
        font_map = {
            'premierleague': {
                'normal': 'fontes/premierleague.otf',
                'bold': 'fontes/premierleague-bold.otf'
            },
            'championship': {
                'normal': 'fontes/efl.otf',
                'bold': 'fontes/efl-bold.otf'
            }
        }
        
        league_fonts = font_map.get(league, {
            'normal': 'fontes/FontePlacar.ttf',
            'bold': 'fontes/FontePlacar.ttf'
        })
        
        font_type = 'bold' if bold else 'normal'
        return league_fonts[font_type]
    
    def _split_headline_balanced(self, text: str, font: ImageFont.FreeTypeFont, 
                                 max_width: int) -> list:
        """
        Divide o texto em linhas balanceadas (mesmo tamanho)
        """
        draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
        
        # Se cabe em uma linha, retorna
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        
        if text_width <= max_width:
            return [text]
        
        # Dividir em palavras
        words = text.split()
        
        # Tentar dividir em 2 linhas balanceadas
        best_split = None
        best_diff = float('inf')
        
        for i in range(1, len(words)):
            line1 = ' '.join(words[:i])
            line2 = ' '.join(words[i:])
            
            bbox1 = draw.textbbox((0, 0), line1, font=font)
            bbox2 = draw.textbbox((0, 0), line2, font=font)
            
            width1 = bbox1[2] - bbox1[0]
            width2 = bbox2[2] - bbox2[0]
            
            # Verificar se ambas cabem
            if width1 <= max_width and width2 <= max_width:
                # Calcular diferença de tamanho
                diff = abs(width1 - width2)
                
                if diff < best_diff:
                    best_diff = diff
                    best_split = [line1, line2]
        
        if best_split:
            return best_split
        
        # Se não conseguiu balancear em 2 linhas, tentar 3 linhas
        for i in range(1, len(words) - 1):
            for j in range(i + 1, len(words)):
                line1 = ' '.join(words[:i])
                line2 = ' '.join(words[i:j])
                line3 = ' '.join(words[j:])
                
                bbox1 = draw.textbbox((0, 0), line1, font=font)
                bbox2 = draw.textbbox((0, 0), line2, font=font)
                bbox3 = draw.textbbox((0, 0), line3, font=font)
                
                width1 = bbox1[2] - bbox1[0]
                width2 = bbox2[2] - bbox2[0]
                width3 = bbox3[2] - bbox3[0]
                
                if width1 <= max_width and width2 <= max_width and width3 <= max_width:
                    return [line1, line2, line3]
        
        # Último recurso: quebrar palavra por palavra até caber
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            test_width = bbox[2] - bbox[0]
            
            if test_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def _apply_bottom_gradient(self, image: Image.Image, intensity: float = 0.8) -> Image.Image:
        """
        Aplica um gradiente preto transparente da metade para o fim da imagem
        """
        width, height = image.size
        # Criar uma camada separada para o gradiente
        gradient = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(gradient)

        # Começa o gradiente em 50% da imagem até o final
        start_y = height // 2
        for y in range(start_y, height):
            # Calcula a opacidade (alpha) aumentando conforme desce
            # 0 no meio, 'intensity' no fundo
            alpha = int(255 * intensity * ((y - start_y) / (height - start_y)))
            draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
        
        # Sobrepor o gradiente na imagem original
        return Image.alpha_composite(image, gradient)
    

    def generate_news_image(self, league: str, headline: str, 
                           background: str = None, alinhamento: str = "Centro") -> Image.Image:
        """
        Gera imagem de notícia
        
        Args:
            league: 'premierleague' ou 'championship'
            headline: Texto da manchete
            background: Caminho da imagem de fundo (opcional)
            alinhamento: 'Centro', 'Esquerda' ou 'Direita'
        
        Returns:
            Imagem PIL gerada
        """
        # Carregar template
        template_file = f"{league}-template.png"
        template_path = os.path.join(self.templates_dir, template_file)
        base = self._load_image(template_path)
        
        # ADICIONAR IMAGEM DE FUNDO (se fornecida)
        if background and os.path.exists(background):
            bg_original = Image.open(background).convert("RGBA")
            
            # Calcular dimensões para cobrir TODO o template
            bg_width = base.width
            bg_height = base.height
            
            # Calcular qual dimensão precisa ser ajustada para cobrir tudo
            width_ratio = bg_width / bg_original.width
            height_ratio = bg_height / bg_original.height
            
            # Usar o MAIOR ratio para garantir que cobre tudo
            scale_ratio = max(width_ratio, height_ratio)
            
            new_width = int(bg_original.width * scale_ratio)
            new_height = int(bg_original.height * scale_ratio)
            
            bg_resized = bg_original.resize((new_width, new_height), Image.LANCZOS)
            
            # Calcular crop baseado no alinhamento
            if alinhamento == "Centro":
                crop_x = (bg_resized.width - bg_width) // 2
                crop_y = (bg_resized.height - bg_height) // 2
            elif alinhamento == "Esquerda":
                crop_x = 0
                crop_y = (bg_resized.height - bg_height) // 2
            else:  # Direita
                crop_x = bg_resized.width - bg_width
                crop_y = (bg_resized.height - bg_height) // 2
            
            # Garantir que crop não seja negativo
            crop_x = max(0, crop_x)
            crop_y = max(0, crop_y)
            
            # Crop para o tamanho exato do template
            bg_cropped = bg_resized.crop((
                crop_x, 
                crop_y, 
                crop_x + bg_width, 
                crop_y + bg_height
            ))

            if league == 'championship':
                bg_cropped = self._apply_bottom_gradient(bg_cropped, intensity=0.9)
            
            # Criar imagem final com background cobrindo tudo
            final_img = Image.new("RGBA", base.size)
            final_img.paste(bg_cropped, (0, 0))
            final_img.paste(base, (0, 0), base)
            base = final_img
        
        draw = ImageDraw.Draw(base)
        
        # Configurações por liga
        if league == 'premierleague':
            font_size = 80
            bg_color = (0, 0, 0)  # Preto
            text_color = (255, 255, 255)  # Branco
            text_area_y = 1050  # MAIS PRA BAIXO
            # USAR LARGURA DO TEMPLATE com margem de segurança
            max_width = base.width - 200  # 100px de margem de cada lado
            
            # ADICIONAR LOGO NO CANTO SUPERIOR DIREITO
            logo_path = os.path.join(self.templates_dir, "logo.png")
            if os.path.exists(logo_path):
                logo = self._load_image(logo_path)
                
                # Redimensionar para 300px de altura mantendo proporção
                aspect_ratio = logo.width / logo.height
                new_height = 300
                new_width = int(new_height * aspect_ratio)
                logo = logo.resize((new_width, new_height), Image.LANCZOS)
                
                # Posicionar no canto superior direito
                logo_x = base.width - logo.width - 50  # 50px da borda direita
                logo_y = 50  # 50px do topo
                base.paste(logo, (logo_x, logo_y), logo)
        
        else:  # championship
            font_size = 70
            bg_color = (255, 20, 20)  # Vermelho
            text_color = (255, 255, 255)  # Branco
            text_area_y = 1050
            # USAR LARGURA DO TEMPLATE com margem de segurança
            max_width = base.width - 200  # 100px de margem de cada lado
        
        # Carregar fonte
        font_path = self._get_font_for_league(league, bold=True)
        font = ImageFont.truetype(font_path, font_size)
        
        # Dividir texto em linhas balanceadas
        headline_upper = headline.upper()
        lines = self._split_headline_balanced(headline_upper, font, max_width)
        
        # Calcular altura total do texto
        line_height = font_size + 20  # Espaçamento entre linhas
        total_text_height = len(lines) * line_height
        
        # Calcular posição Y inicial (centralizar verticalmente na área)
        start_y = text_area_y - (total_text_height // 2)
        
        # Desenhar cada linha
        for i, line in enumerate(lines):
            # Medir largura da linha
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Calcular posição X (centralizar)
            x = (base.width - text_width) // 2
            y = start_y + (i * line_height)
            
            # Desenhar background preto/vermelho atrás do texto
            padding = 20
            bg_x1 = x - padding
            bg_y1 = y - padding
            bg_x2 = x + text_width + padding
            bg_y2 = y + text_height + padding
            
            draw.rectangle([bg_x1, bg_y1, bg_x2, bg_y2], fill=bg_color)
            
            # Desenhar texto
            draw.text((x, y), line, font=font, fill=text_color)
        
        return base