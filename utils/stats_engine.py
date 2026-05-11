"""
Motor de estatísticas para o Streamlit app.
Lê data/historico.csv e gera insights usando bbi_functions.
"""
import pandas as pd
from typing import Dict, List, Tuple

from utils.bbi_functions import allinsights, wdl, gf as _gf, gs as _gs, _parse_score, _season_start

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
            v = e = d = 0
            for _, row in sub.iterrows():
                gh, ga = _parse_score(row['placar'])
                if gh > ga:
                    v += 1
                elif gh == ga:
                    e += 1
                else:
                    d += 1
            records.append({'Time': team, 'J': len(sub), 'V': v, 'E': e, 'D': d, 'Pts': v * 3 + e})
    else:
        for team in df_liga['fora'].unique():
            sub = df_liga[df_liga['fora'] == team]
            v = e = d = 0
            for _, row in sub.iterrows():
                gh, ga = _parse_score(row['placar'])
                if ga > gh:
                    v += 1
                elif ga == gh:
                    e += 1
                else:
                    d += 1
            records.append({'Time': team, 'J': len(sub), 'V': v, 'E': e, 'D': d, 'Pts': v * 3 + e})

    return (pd.DataFrame(records)
            .sort_values('Pts', ascending=False)
            .reset_index(drop=True))


def _last_n_games_data(df_liga: pd.DataFrame, teams: List[str]) -> Dict[str, List[str]]:
    """
    Retorna para cada time a lista dos últimos 10 resultados ('V'/'E'/'D'), do mais recente ao mais antigo.
    Armazenado em cache como parte de compute_league_stats para uso pelo slider dinâmico na UI.
    """
    result: Dict[str, List[str]] = {}
    for team in teams:
        sub = df_liga[(df_liga['casa'] == team) | (df_liga['fora'] == team)].copy()
        sub = sub.sort_values('data', ascending=False).head(10)
        games = []
        for _, row in sub.iterrows():
            gh, ga = _parse_score(row['placar'])
            is_home = row['casa'] == team
            gf_val = gh if is_home else ga
            gs_val = ga if is_home else gh
            if gf_val > gs_val:
                games.append('V')
            elif gf_val == gs_val:
                games.append('E')
            else:
                games.append('D')
        result[team] = games
    return result


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
    df_full_liga = load_historico(liga_str)
    if df_full_liga.empty:
        return {
            'insights': [], 'team_insights': {}, 'team_rankings': {}, 'teams': [],
            'best_home': '-', 'worst_home': '-', 'best_away': '-', 'worst_away': '-',
            'best_attack_team': '-', 'best_attack_gols': 0,
            'worst_attack_team': '-', 'worst_attack_gols': 0,
            'best_defense_team': '-', 'best_defense_gols': 0,
            'worst_defense_team': '-', 'worst_defense_gols': 0,
            'home_table_full': pd.DataFrame(), 'away_table_full': pd.DataFrame(),
            'last_n_games_data': {},
        }

    # Filtrar temporada atual: Jul 1 do ano corrente da temporada
    season_start = pd.Timestamp(_season_start())
    df_liga = df_full_liga[df_full_liga['data'] >= season_start].copy()
    if df_liga.empty:
        df_liga = df_full_liga  # fallback se a temporada ainda não tiver dados

    teams = sorted(set(df_liga['casa'].unique()) | set(df_liga['fora'].unique()))

    # DataFrames por time: temporada atual (insights normais) e histórico completo (cross-temporada)
    results_dict = {team: _build_team_df(df_liga, team) for team in teams}
    results_dict_full = {team: _build_team_df(df_full_liga, team) for team in teams}

    # Insights gerais da liga (temporada atual + cross-temporada)
    league_insights = allinsights(results_dict, liga_str, 'liga', df_full=results_dict_full)

    # Insights por time
    team_insights = {
        team: allinsights(results_dict[team], team, 'time', df_full=results_dict_full[team])
        for team in teams
    }

    # Tabelas mandante/visitante e rankings (temporada atual)
    home_table = _home_away_table(df_liga, 'home')
    away_table = _home_away_table(df_liga, 'away')
    team_rankings = {team: _ranking_insights(team, home_table, away_table) for team in teams}

    # Dados para tabela dinâmica de últimos N jogos
    last_n_games = _last_n_games_data(df_liga, teams)

    # Ataque/defesa geral (temporada atual)
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
        'home_table_full': home_table,
        'away_table_full': away_table,
        'last_n_games_data': last_n_games,
        'best_home':  home_table.iloc[0]['Time']  if not home_table.empty  else '-',
        'worst_home': home_table.iloc[-1]['Time'] if not home_table.empty  else '-',
        'best_away':  away_table.iloc[0]['Time']  if not away_table.empty  else '-',
        'worst_away': away_table.iloc[-1]['Time'] if not away_table.empty  else '-',
        'best_attack_team':   best_atk,  'best_attack_gols':   best_atk_gols,
        'worst_attack_team':  worst_atk, 'worst_attack_gols':  worst_atk_gols,
        'best_defense_team':  best_def,  'best_defense_gols':  best_def_gols,
        'worst_defense_team': worst_def, 'worst_defense_gols': worst_def_gols,
    }
