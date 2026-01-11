"""
Validador de tabelas - compara tabela calculada com fonte oficial
"""
import requests
from lxml import html
from collections import Counter
from typing import List, Dict, Tuple
from fuzzywuzzy import process
import pandas as pd

class TableValidator:
    def __init__(self):
        self.sources = {
            'premierleague': 'https://www.skysports.com/premier-league-table',
            'championship': 'https://www.skysports.com/championship-table',
            'leagueone': 'https://www.skysports.com/league-1-table',
            'leaguetwo': 'https://www.skysports.com/league-2-table',
            'nationalleague': 'https://www.skysports.com/national-league-table'
        }
    
    def fetch_official_table(self, league: str) -> pd.DataFrame:
        """
        Busca tabela oficial do Sky Sports
        
        Returns:
            DataFrame com dados oficiais
        """
        url = self.sources.get(league)
        if not url:
            return None
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            web_content = html.fromstring(response.content)
            
            # XPath para a tabela
            table_xpath = '/html/body/main/div[5]/div/div/div/table'
            table_element = web_content.xpath(table_xpath)
            
            if not table_element:
                # Tentar XPath alternativo
                table_element = web_content.xpath('//table[contains(@class, "standing-table")]')
            
            if not table_element:
                return None
            
            table_element = table_element[0]
            
            # Extrair dados
            table_data = []
            for row in table_element.xpath('.//tr'):
                row_data = [cell.text_content().strip() for cell in row.xpath('.//td')]
                if row_data:
                    table_data.append(row_data)
            
            # Criar DataFrame
            columns = ['Pos', 'Time', 'J', 'V', 'E', 'D', 'GM', 'GS', 'SG', 'Pts']
            extracted_table = pd.DataFrame(table_data, columns=columns)
            extracted_table = extracted_table.drop(columns=['Pos'])
            
            # Converter colunas numéricas
            numeric_columns = ['J', 'V', 'E', 'D', 'GM', 'GS', 'SG', 'Pts']
            for col in numeric_columns:
                extracted_table[col] = extracted_table[col].str.replace('+', '', regex=False).astype(int)
            
            return extracted_table
        
        except Exception as e:
            print(f"Erro ao buscar tabela oficial: {e}")
            return None
    
    def compare_tables(self, calculated_table: List[Dict], official_df: pd.DataFrame) -> pd.DataFrame:
        """
        Compara tabela calculada com oficial usando fuzzy matching
        
        Returns:
            DataFrame com divergências (vazio se tudo ok)
        """
        # Converter calculated_table para DataFrame
        tabela_final = pd.DataFrame(calculated_table)
        tabela_final = tabela_final[['name', 'games', 'wins', 'draws', 'losses', 
                                     'goals_for', 'goals_against', 'goal_difference', 'points']]
        tabela_final.columns = ['Time', 'J', 'V', 'E', 'D', 'GM', 'GS', 'SG', 'Pts']
        
        # Fuzzy matching de nomes
        def get_best_match(name, choices):
            match, score = process.extractOne(name, choices)
            return match
        
        official_df['Time'] = official_df['Time'].apply(
            lambda x: get_best_match(x, tabela_final['Time'].tolist())
        )
        
        # Garantir tipos numéricos
        numeric_columns = ['J', 'V', 'E', 'D', 'GM', 'GS', 'SG', 'Pts']
        for col in numeric_columns:
            tabela_final[col] = tabela_final[col].astype(int)
        
        # Merge e comparação
        comparison = tabela_final.merge(official_df, on='Time', suffixes=('_calculado', '_oficial'))
        
        # Filtrar divergências
        divergencias = comparison[
            (comparison['J_calculado'] != comparison['J_oficial']) |
            (comparison['V_calculado'] != comparison['V_oficial']) |
            (comparison['E_calculado'] != comparison['E_oficial']) |
            (comparison['D_calculado'] != comparison['D_oficial']) |
            (comparison['GM_calculado'] != comparison['GM_oficial']) |
            (comparison['GS_calculado'] != comparison['GS_oficial']) |
            (comparison['SG_calculado'] != comparison['SG_oficial']) |
            (comparison['Pts_calculado'] != comparison['Pts_oficial'])
        ]
        
        return divergencias
    
    def check_duplicate_teams(self, results: List[Dict]) -> List[str]:
        """
        Verifica se há times repetidos nos resultados
        """
        teams = []
        for result in results:
            if result.get('status') == 'normal':
                teams.append(result['home_team'])
                teams.append(result['away_team'])
        
        counts = Counter(teams)
        duplicates = [team for team, cnt in counts.items() if cnt > 1]
        
        return duplicates
    
    def validate_results(self, results: List[Dict], num_teams: int) -> Tuple[bool, List[str]]:
        """
        Valida se há problemas com os resultados inseridos
        """
        warnings = []
        
        duplicates = self.check_duplicate_teams(results)
        
        num_matches = len([r for r in results if r.get('status') == 'normal'])
        
        if duplicates and num_matches <= (num_teams // 2):
            warnings.append(f"⚠️ Times repetidos: {', '.join(duplicates)}")
            warnings.append("Isso pode indicar que há jogos faltando ou duplicados.")
            return False, warnings
        
        return True, warnings