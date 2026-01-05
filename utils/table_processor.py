"""
Processador de tabelas de ligas
Atualiza estatísticas com base em resultados de partidas
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
import copy

@dataclass
class TeamStats:
    """Estatísticas de um time na tabela"""
    name: str
    position: int
    games: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    
    def __repr__(self):
        return f"{self.position}. {self.name} - {self.points}pts"

class TableProcessor:
    def __init__(self):
        """Inicializa o processador de tabelas"""
        self.teams: List[TeamStats] = []
    
    def load_from_text(self, table_text: str) -> None:
        """
        Carrega tabela a partir de arquivo de texto
        
        Formato esperado (cada linha):
        Nome do Time J V E D GP GC SG P
        
        Exemplo:
        Coventry City 25 15 7 3 55 26 29 52
        """
        self.teams = []
        lines = table_text.strip().split('\n')
        
        for idx, line in enumerate(lines, start=1):
            parts = line.strip().split()
            
            # O nome do time pode ter múltiplas palavras
            # As últimas 8 colunas são sempre: J V E D GP GC SG P
            if len(parts) < 9:  # Nome + 8 estatísticas
                continue
            
            stats_values = parts[-8:]  # Pega as últimas 8 colunas
            team_name = ' '.join(parts[:-8])  # Tudo antes das estatísticas é o nome
            
            try:
                team = TeamStats(
                    name=team_name,
                    position=idx,
                    games=int(stats_values[0]),
                    wins=int(stats_values[1]),
                    draws=int(stats_values[2]),
                    losses=int(stats_values[3]),
                    goals_for=int(stats_values[4]),
                    goals_against=int(stats_values[5]),
                    goal_difference=int(stats_values[6]),
                    points=int(stats_values[7])
                )
                self.teams.append(team)
            except ValueError as e:
                print(f"Erro ao processar linha {idx}: {line}")
                print(f"Erro: {e}")
                continue
    
    def find_team(self, team_name: str) -> Optional[TeamStats]:
        """Encontra um time na tabela pelo nome"""
        for team in self.teams:
            if team.name == team_name:
                return team
        return None
    
    def update_with_result(self, home_team: str, away_team: str, 
                          home_score: int, away_score: int) -> bool:
        """
        Atualiza a tabela com o resultado de uma partida
        
        Retorna True se a atualização foi bem-sucedida
        """
        home = self.find_team(home_team)
        away = self.find_team(away_team)
        
        if not home or not away:
            return False
        
        # Atualizar jogos
        home.games += 1
        away.games += 1
        
        # Atualizar gols
        home.goals_for += home_score
        home.goals_against += away_score
        away.goals_for += away_score
        away.goals_against += home_score
        
        # Atualizar saldo de gols
        home.goal_difference = home.goals_for - home.goals_against
        away.goal_difference = away.goals_for - away.goals_against
        
        # Determinar resultado e atualizar pontos
        if home_score > away_score:  # Vitória do mandante
            home.wins += 1
            home.points += 3
            away.losses += 1
        elif home_score < away_score:  # Vitória do visitante
            away.wins += 1
            away.points += 3
            home.losses += 1
        else:  # Empate
            home.draws += 1
            away.draws += 1
            home.points += 1
            away.points += 1
        
        return True
    
    def update_with_multiple_results(self, results: List[Dict]) -> List[str]:
        """
        Atualiza a tabela com múltiplos resultados
        
        Args:
            results: Lista de dicionários com 'home_team', 'away_team', 
                    'home_score', 'away_score', 'status'
        
        Retorna:
            Lista de mensagens de erro (vazia se tudo ok)
        """
        errors = []
        
        for result in results:
            # Pular jogos que não têm resultado final
            if result.get('status') in ['future', 'postponed', 'abandoned']:
                continue  # Não atualiza a tabela
            
            success = self.update_with_result(
                result['home_team'],
                result['away_team'],
                result['home_score'],
                result['away_score']
            )
            
            if not success:
                errors.append(
                    f"Erro ao processar: {result['home_team']} vs {result['away_team']}"
                )
        
        return errors
    
    
    def sort_table(self) -> None:
        """
        Ordena a tabela pelos critérios INGLESES:
        1. Pontos (maior)
        2. Saldo de gols (maior)
        3. Gols marcados (maior)
        """
        self.teams.sort(
            key=lambda t: (-t.points, -t.goal_difference, -t.goals_for, t.name)
        )
        
        # Atualizar posições
        for idx, team in enumerate(self.teams, start=1):
            team.position = idx
    
    def to_text(self) -> str:
        """
        Converte a tabela de volta para o formato de texto
        
        Retorna string no formato:
        Nome do Time J V E D GP GC SG P
        """
        lines = []
        for team in self.teams:
            line = f"{team.name} {team.games} {team.wins} {team.draws} {team.losses} " \
                   f"{team.goals_for} {team.goals_against} {team.goal_difference} {team.points}"
            lines.append(line)
        
        return '\n'.join(lines)
    
    def get_max_games(self) -> int:
        """Retorna o número máximo de jogos de qualquer time"""
        if not self.teams:
            return 0
        return max(team.games for team in self.teams)
    
    def get_copy(self) -> 'TableProcessor':
        """Retorna uma cópia profunda do processador"""
        new_processor = TableProcessor()
        new_processor.teams = copy.deepcopy(self.teams)
        return new_processor
