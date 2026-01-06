"""
Parser de resultados de partidas
Converte strings como "POR 1-0 SOU" em dados estruturados
"""
import re
import json
from typing import Dict, List, Tuple, Optional

class ResultsParser:
    def __init__(self, abbreviations_path: str = "config/team_abbreviations.json"):
        """Inicializa o parser com o dicionário de abreviações"""
        with open(abbreviations_path, 'r', encoding='utf-8') as f:
            self.abbreviations = json.load(f)
    
    def parse_single_result(self, result_str: str) -> Optional[Dict]:
        """
        Parse de um único resultado
        
        Formato esperado: 
        - "ABV 2-1 XYZ" (resultado normal)
        - "ABV D-D XYZ" (jogo futuro)
        - "ABV ADI. XYZ" (jogo adiado)
        - "ABV ABD. XYZ" (jogo abandonado)
        
        Se a sigla não existir no dicionário, usa a própria sigla como nome
        """
        # Remove espaços extras
        result_str = result_str.strip()
        
        # Padrão 1: Resultado normal "POR 1-0 SOU"
        pattern_normal = r'^([A-Z]{3})\s+(\d+)\s*-\s*(\d+)\s+([A-Z]{3})$'
        match = re.match(pattern_normal, result_str)
        
        if match:
            home_abbr, home_score, away_score, away_abbr = match.groups()
            
            # FALLBACK: Se não encontrar no dicionário, usa a sigla
            home_team = self.abbreviations.get(home_abbr, home_abbr)
            away_team = self.abbreviations.get(away_abbr, away_abbr)
            
            return {
                'home_abbr': home_abbr,
                'away_abbr': away_abbr,
                'home_team': home_team,
                'away_team': away_team,
                'home_score': int(home_score),
                'away_score': int(away_score),
                'status': 'normal'
            }
        
        # Padrão 2: Jogo futuro "POR D-D SOU"
        pattern_future = r'^([A-Z]{3})\s+D\s*-\s*D\s+([A-Z]{3})$'
        match = re.match(pattern_future, result_str, re.IGNORECASE)
        
        if match:
            home_abbr, away_abbr = match.groups()
            
            home_team = self.abbreviations.get(home_abbr, home_abbr)
            away_team = self.abbreviations.get(away_abbr, away_abbr)
            
            return {
                'home_abbr': home_abbr,
                'away_abbr': away_abbr,
                'home_team': home_team,
                'away_team': away_team,
                'home_score': None,
                'away_score': None,
                'status': 'future'
            }
        
        # PADRÃO 2B: Jogo futuro com "vs." - "TOT vs. AVL"
        pattern_vs = r'^([A-Z]{3})\s+vs\.?\s+([A-Z]{3})$'
        match = re.match(pattern_vs, result_str, re.IGNORECASE)

        if match:
            home_abbr, away_abbr = match.groups()
            
            home_team = self.abbreviations.get(home_abbr, home_abbr)
            away_team = self.abbreviations.get(away_abbr, away_abbr)
            
            return {
                'home_abbr': home_abbr,
                'away_abbr': away_abbr,
                'home_team': home_team,
                'away_team': away_team,
                'home_score': None,
                'away_score': None,
                'status': 'vs'  # ← Novo status
            }
        
        # Padrão 3: Jogo adiado "POR ADI. SOU"
        pattern_postponed = r'^([A-Z]{3})\s+ADI\.?\s+([A-Z]{3})$'
        match = re.match(pattern_postponed, result_str, re.IGNORECASE)
        
        if match:
            home_abbr, away_abbr = match.groups()
            
            home_team = self.abbreviations.get(home_abbr, home_abbr)
            away_team = self.abbreviations.get(away_abbr, away_abbr)
            
            return {
                'home_abbr': home_abbr,
                'away_abbr': away_abbr,
                'home_team': home_team,
                'away_team': away_team,
                'home_score': None,
                'away_score': None,
                'status': 'postponed'
            }
        
        # Padrão 4: Jogo abandonado "POR ABD. SOU"
        pattern_abandoned = r'^([A-Z]{3})\s+ABD\.?\s+([A-Z]{3})$'
        match = re.match(pattern_abandoned, result_str, re.IGNORECASE)
        
        if match:
            home_abbr, away_abbr = match.groups()
            
            home_team = self.abbreviations.get(home_abbr, home_abbr)
            away_team = self.abbreviations.get(away_abbr, away_abbr)
            
            return {
                'home_abbr': home_abbr,
                'away_abbr': away_abbr,
                'home_team': home_team,
                'away_team': away_team,
                'home_score': None,
                'away_score': None,
                'status': 'abandoned'
            }
        
        return None


    def parse_multiple_results(self, results_text: str) -> List[Dict]:
        """
        Parse de múltiplos resultados (um por linha)
        
        Args:
            results_text: String com múltiplos resultados, um por linha
        
        Retorna:
            Lista de dicionários com resultados parseados
        """
        lines = results_text.strip().split('\n')
        parsed_results = []
        
        for line in lines:
            line = line.strip()
            if not line:  # Pula linhas vazias
                continue
            
            result = self.parse_single_result(line)
            if result:
                parsed_results.append(result)
        
        return parsed_results
    
    def validate_result(self, result_str: str) -> Tuple[bool, str]:
        """
        Valida se um resultado está no formato correto
        
        Retorna:
            (válido: bool, mensagem: str)
        """
        result_str = result_str.strip()
        
        if not result_str:
            return False, "Resultado vazio"
        
        pattern = r'^([A-Z]{3})\s+(\d+)\s*-\s*(\d+)\s+([A-Z]{3})$'
        match = re.match(pattern, result_str)
        
        if not match:
            return False, f"Formato inválido: '{result_str}'. Use: ABV 1-0 XYZ"
        
        home_abbr, _, _, away_abbr = match.groups()
        
        if home_abbr not in self.abbreviations:
            return False, f"Abreviação '{home_abbr}' não encontrada"
        
        if away_abbr not in self.abbreviations:
            return False, f"Abreviação '{away_abbr}' não encontrada"
        
        return True, "Válido"
    
    def get_team_name(self, abbreviation: str) -> Optional[str]:
        """Retorna o nome completo do time a partir da abreviação"""
        return self.abbreviations.get(abbreviation)
    
    def get_abbreviation(self, team_name: str) -> Optional[str]:
        """Retorna a abreviação a partir do nome completo do time"""
        for abbr, name in self.abbreviations.items():
            if name == team_name:
                return abbr
        return None
