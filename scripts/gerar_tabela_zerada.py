#!/usr/bin/env python3
"""
Gera imagens de tabela de liga zerada (início de temporada).
Lê os times de cada pasta de escudos e aplica regras especiais por liga.

Regras especiais:
  - Premier League: 4 vagas UCL + 1 vaga UEL (posição 5)
  - Championship: play-offs vão até o 8º colocado; Southampton com -4 pts (Spygate 2.0)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from utils.image_generator import ImageGenerator

OUTPUT_DIR = "tabelas-zeradas"

# Zonas customizadas que diferem da config padrão
SPECIAL_ZONES = {
    'premierleague': {
        "neutral": {"positions": [], "rect": "premierleague-rect.png"},
        "champion": {
            "positions": [1],
            "rect": "premierleague-rect-c.png",
            "rect_confirmed": "premierleague-rect-c-conf.png",
        },
        "ucl": {
            "positions": [1, 2, 3, 4],
            "rect": "premierleague-rect-ucl.png",
            "rect_confirmed": "premierleague-rect-ucl-conf.png",
        },
        "uel": {
            "positions": [5],
            "rect": "premierleague-rect-uel.png",
            "rect_confirmed": "premierleague-rect-uel-conf.png",
        },
        "uecl": {
            "positions": [],
            "rect": "premierleague-rect-uecl.png",
            "rect_confirmed": "premierleague-rect-uecl-conf.png",
        },
        "relegation": {
            "positions": [18, 19, 20],
            "rect": "premierleague-rect-r.png",
            "rect_confirmed": "premierleague-rect-r-conf.png",
        },
    },
    'championship': {
        "neutral": {"positions": [], "rect": "championship-rect.png"},
        "champion": {
            "positions": [1],
            "rect": "championship-rect-c.png",
            "rect_confirmed": "championship-rect-c-conf.png",
        },
        "promoted": {
            "positions": [1, 2],
            "rect": "championship-rect-p.png",
            "rect_confirmed": "championship-rect-p-conf.png",
        },
        # Play-offs agora vão até o 8º colocado
        "playoffs": {
            "positions": [3, 4, 5, 6, 7, 8],
            "rect": "championship-rect-po.png",
            "rect_confirmed": "championship-rect-po-conf.png",
        },
        "relegation": {
            "positions": [22, 23, 24],
            "rect": "championship-rect-r.png",
            "rect_confirmed": "championship-rect-r-conf.png",
        },
    },
}

# Deduções de pontos por liga: {time: pontos}
POINT_DEDUCTIONS = {
    'championship': {
        'Southampton': -4,
    },
}

# Texto da nota de penalidade
DEDUCTION_NOTES = {
    'championship': {
        'Southampton': 'Southampton: -4 pts (Spygate 2.0)',
    },
}


def get_teams_from_folder(folder: str) -> list:
    teams = []
    for filename in sorted(os.listdir(folder)):
        if filename.lower().endswith('.png'):
            teams.append(filename[:-4])
    return teams


def build_zeroed_table(teams: list, deductions: dict = None, notes: dict = None) -> list:
    deductions = deductions or {}
    notes = notes or {}
    table = []
    for team in teams:
        pts = deductions.get(team, 0)
        entry = {
            'name': team,
            'games': 0,
            'wins': 0,
            'draws': 0,
            'losses': 0,
            'goals_for': 0,
            'goals_against': 0,
            'goal_difference': 0,
            'points': pts,
            'penalty_note': notes.get(team) if pts < 0 else None,
        }
        table.append(entry)
    # Times com penalidade vão para o final; entre iguais mantém ordem alfabética
    table.sort(key=lambda x: x['points'], reverse=True)
    return table


def generate_table(generator: ImageGenerator, league: str):
    config = generator.leagues_config[league]
    folder = config['badges_folder']
    teams = get_teams_from_folder(folder)

    deductions = POINT_DEDUCTIONS.get(league, {})
    notes = DEDUCTION_NOTES.get(league, {})
    table_data = build_zeroed_table(teams, deductions, notes)

    # Substituir zonas temporariamente se houver regras especiais
    original_zones = None
    if league in SPECIAL_ZONES:
        original_zones = config['promotion_zones']
        config['promotion_zones'] = SPECIAL_ZONES[league]

    try:
        image = generator.generate_table_image(league, table_data)
    finally:
        if original_zones is not None:
            config['promotion_zones'] = original_zones

    out_path = os.path.join(OUTPUT_DIR, f"tabela-zerada-{league}.png")
    image.save(out_path)
    print(f"  Salvo: {out_path}  ({len(teams)} times)")
    return image


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    generator = ImageGenerator(config_path="config/leagues_config.json")

    leagues = [
        'premierleague',
        'championship',
        'leagueone',
        'leaguetwo',
        'nationalleague',
    ]

    print(f"Gerando tabelas zeradas em '{OUTPUT_DIR}/'...\n")
    for league in leagues:
        print(f"[{league}]")
        try:
            generate_table(generator, league)
        except Exception as e:
            print(f"  ERRO: {e}")
        print()

    print("Pronto.")


if __name__ == '__main__':
    main()
