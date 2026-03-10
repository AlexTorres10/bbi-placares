"""
Motor de estatísticas para o Streamlit app.
Lê data/historico.csv e gera insights usando bbi_functions.
"""
import pandas as pd
from typing import Dict, List, Tuple

from utils.bbi_functions import allinsights, wdl, gf as _gf, gs as _gs, _parse_score

HISTORICO_PATH = "data/historico.csv"


def load_historico(liga_str: str) -> pd.DataFrame:
    """Carrega registros históricos de uma liga, ordenados por data."""
    df = pd.read_csv(HISTORICO_PATH, parse_dates=['data'])
    df = df[df['liga'] == liga_str].copy()
    df = df.sort_values('data').reset_index(drop=True)
    return df


def _build_team_df(df_liga: pd.DataFrame, team: str) -> pd.DataFrame:
    """Constrói DataFrame de resultados de um time com colunas result/gf/gs."""
    df = df_liga[(df_liga['casa'] == team) | (df_liga['fora'] == team)].copy()
    df['result'] = df.apply(lambda row: wdl(row, team), axis=1)
    df['gf'] = df.apply(lambda row: _gf(row, team), axis=1)
    df['gs'] = df.apply(lambda row: _gs(row, team), axis=1)
    return df


def _home_away_table(df_liga: pd.DataFrame, mando: str) -> pd.DataFrame:
    """
    Constrói tabela de mandante ou visitante ordenada por pontos.
    mando: 'home' ou 'away'
    """
    records = []
    if mando == 'home':
        for team in df_liga['casa'].unique():
            sub = df_liga[df_liga['casa'] == team]
            pts = 0
            for _, row in sub.iterrows():
                gh, ga = _parse_score(row['placar'])
                pts += 3 if gh > ga else (1 if gh == ga else 0)
            records.append({'Time': team, 'J': len(sub), 'Pts': pts})
    else:
        for team in df_liga['fora'].unique():
            sub = df_liga[df_liga['fora'] == team]
            pts = 0
            for _, row in sub.iterrows():
                gh, ga = _parse_score(row['placar'])
                pts += 3 if ga > gh else (1 if ga == gh else 0)
            records.append({'Time': team, 'J': len(sub), 'Pts': pts})

    return (pd.DataFrame(records)
            .sort_values('Pts', ascending=False)
            .reset_index(drop=True))


def _overall_attack_defense(df_liga: pd.DataFrame, teams: List[str]) -> pd.DataFrame:
    """Computa GM e GS totais por time."""
    records = []
    for team in teams:
        home = df_liga[df_liga['casa'] == team]
        away = df_liga[df_liga['fora'] == team]
        gm = (home['placar'].apply(lambda p: _parse_score(p)[0]).sum() +
              away['placar'].apply(lambda p: _parse_score(p)[1]).sum())
        gs = (home['placar'].apply(lambda p: _parse_score(p)[1]).sum() +
              away['placar'].apply(lambda p: _parse_score(p)[0]).sum())
        records.append({'Time': team, 'GM': int(gm), 'GS': int(gs)})
    return pd.DataFrame(records)


def _ranking_insights(team: str, home_table: pd.DataFrame, away_table: pd.DataFrame) -> List[str]:
    """Gera insights de ranking (melhor/pior mandante/visitante) para um time."""
    insights = []

    melhores_mandantes = home_table['Time'].head(3).tolist()
    piores_mandantes = home_table['Time'].tail(3).tolist()[::-1]  # pior primeiro
    melhores_visitantes = away_table['Time'].head(3).tolist()
    piores_visitantes = away_table['Time'].tail(3).tolist()[::-1]

    for i, t in enumerate(melhores_mandantes):
        if t == team:
            insights.append(f"{team} é o melhor mandante!" if i == 0
                            else f"{team} é o {i+1}º melhor mandante!")

    for i, t in enumerate(piores_mandantes):
        if t == team:
            insights.append(f"{team} é o pior mandante!" if i == 0
                            else f"{team} é o {i+1}º pior mandante!")

    for i, t in enumerate(melhores_visitantes):
        if t == team:
            insights.append(f"{team} é o melhor visitante!" if i == 0
                            else f"{team} é o {i+1}º melhor visitante!")

    for i, t in enumerate(piores_visitantes):
        if t == team:
            insights.append(f"{team} é o pior visitante!" if i == 0
                            else f"{team} é o {i+1}º pior visitante!")

    return insights


def compute_league_stats(liga_str: str) -> dict:
    """
    Calcula todas as estatísticas de uma liga a partir do histórico CSV.

    Retorna dict com:
        insights        : list[str] — insights gerais da liga
        team_insights   : dict[str, list[str]] — insights por time
        team_rankings   : dict[str, list[str]] — ranking mandante/visitante por time
        teams           : list[str]
        best_home / worst_home / best_away / worst_away : str
        best_attack_team / best_attack_gols : str / int
        worst_attack_team / worst_attack_gols : str / int
        best_defense_team / best_defense_gols : str / int
        worst_defense_team / worst_defense_gols : str / int
    """
    df_liga = load_historico(liga_str)
    if df_liga.empty:
        return {
            'insights': [], 'team_insights': {}, 'team_rankings': {}, 'teams': [],
            'best_home': '-', 'worst_home': '-', 'best_away': '-', 'worst_away': '-',
            'best_attack_team': '-', 'best_attack_gols': 0,
            'worst_attack_team': '-', 'worst_attack_gols': 0,
            'best_defense_team': '-', 'best_defense_gols': 0,
            'worst_defense_team': '-', 'worst_defense_gols': 0,
        }

    teams = sorted(set(df_liga['casa'].unique()) | set(df_liga['fora'].unique()))

    # DataFrame por time com colunas result/gf/gs
    results_dict = {team: _build_team_df(df_liga, team) for team in teams}

    # Insights gerais da liga
    league_insights = allinsights(results_dict, liga_str, 'liga')

    # Insights por time
    team_insights = {team: allinsights(results_dict[team], team, 'time') for team in teams}

    # Tabelas mandante/visitante
    home_table = _home_away_table(df_liga, 'home')
    away_table = _home_away_table(df_liga, 'away')

    # Rankings por time
    team_rankings = {team: _ranking_insights(team, home_table, away_table) for team in teams}

    # Ataque/defesa geral (com empates)
    ovr = _overall_attack_defense(df_liga, teams)
    best_atk_gols  = int(ovr['GM'].max())
    worst_atk_gols = int(ovr['GM'].min())
    best_def_gols  = int(ovr['GS'].min())
    worst_def_gols = int(ovr['GS'].max())

    best_atk  = ', '.join(ovr[ovr['GM'] == best_atk_gols]['Time'].tolist())
    worst_atk = ', '.join(ovr[ovr['GM'] == worst_atk_gols]['Time'].tolist())
    best_def  = ', '.join(ovr[ovr['GS'] == best_def_gols]['Time'].tolist())
    worst_def = ', '.join(ovr[ovr['GS'] == worst_def_gols]['Time'].tolist())

    return {
        'insights': league_insights,
        'team_insights': team_insights,
        'team_rankings': team_rankings,
        'teams': teams,
        'best_home':  home_table.iloc[0]['Time']  if not home_table.empty  else '-',
        'worst_home': home_table.iloc[-1]['Time'] if not home_table.empty  else '-',
        'best_away':  away_table.iloc[0]['Time']  if not away_table.empty  else '-',
        'worst_away': away_table.iloc[-1]['Time'] if not away_table.empty  else '-',
        'best_attack_team':   best_atk,  'best_attack_gols':   best_atk_gols,
        'worst_attack_team':  worst_atk, 'worst_attack_gols':  worst_atk_gols,
        'best_defense_team':  best_def,  'best_defense_gols':  best_def_gols,
        'worst_defense_team': worst_def, 'worst_defense_gols': worst_def_gols,
    }
