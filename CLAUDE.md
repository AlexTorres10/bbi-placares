# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
# Activate virtualenv first
source venv/bin/activate

# Run the Streamlit app locally
streamlit run app.py
```

Dependencies are in `requirements.txt`. Install with `pip install -r requirements.txt`.

## Maintenance Scripts

```bash
# Rebuild data/posicoes.csv from scratch using historico.csv
python scripts/build_position_history.py

# Filter posicoes.csv to only rows where the team actually played that matchday
python filtrar_posicoes.py
```

## Architecture Overview

This is a **Streamlit web app** that generates social media images for English football leagues (Premier League, Championship, League One, League Two, National League) and cup competitions (FA Cup, EFL Cup, UCL, UEL, UECL).

### Data Flow

1. **User inputs** match results as text (e.g. `ARS 2-1 CHE`) in the Streamlit UI (`app.py`)
2. **`ResultsParser`** converts those strings into structured dicts, using 3-letter abbreviations from `config/team_abbreviations.json`
3. **`TableProcessor`** loads the current standings from `data/tabelas/<league>.txt`, applies new results, re-sorts by English tiebreaker rules (points → goal difference → goals scored), and serializes back to text
4. **`ImageGenerator`** / **`CupGenerator`** / **`NewsGenerator`** render PIL images by compositing PNG templates with team badges, fonts, and dynamic text
5. Generated images are displayed in Streamlit and available for download
6. Updated standings are optionally saved back to GitHub via `GitHubHandler` (GitHub API), which commits both `data/tabelas/<league>.txt` and `data/historico.csv`

### Key Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI — all tabs, forms, session state |
| `utils/results_parser.py` | Parses result strings into dicts; supports normal, penalties `(4-5)`, extra time `(pro)`, postponed `ADI.`, abandoned `ABD.`, future `D-D` / `vs.` |
| `utils/table_processor.py` | `TeamStats` dataclass + table load/update/sort/serialize |
| `utils/image_generator.py` | Generates results and standings images for leagues |
| `utils/cup_generator.py` | Generates cup results images (FA Cup, EFL Cup); handles multi-page layout for large rounds |
| `utils/news_generator.py` | Generates news/headline images with optional background photo |
| `utils/github_handler.py` | GitHub API wrapper (read/update files via base64) |
| `utils/table_validator.py` | Scrapes Sky Sports to compare calculated table vs official |
| `utils/position_history.py` | Matchday detection, table simulation per matchday, read/write of `data/posicoes.csv` |
| `utils/stats_engine.py` | Reads `data/historico.csv` and computes league/team insights via `bbi_functions.py` |
| `utils/bbi_functions.py` | Stats engine ported from the Django `bbistats` project — generates streaks, form, and phase insights |
| `scripts/build_position_history.py` | Retroactively populates `data/posicoes.csv` from `historico.csv`; deletes and rewrites from scratch |
| `filtrar_posicoes.py` | Post-processing filter: removes position rows for teams that didn't play in the correct block window |
| `config/leagues_config.json` | **Central config**: pixel positions, font sizes, badge sizes, promotion zones per league |
| `config/team_abbreviations.json` | 3-letter abbreviation → full team name mapping |
| `config/team_display_names.json` | Shortened display names (per league) for result images |
| `data/tabelas/<league>.txt` | Current standings: one team per line, format: `Team Name J V E D GP GC SG P` |
| `data/historico.csv` | Per-match historical records: `casa,placar,fora,data,liga`. Source of truth for the stats engine and position history. Committed to GitHub on every "Atualizar no GitHub" action. |
| `data/posicoes.csv` | Per-team league position at each matchday: `time,liga,matchday,posicao,data_fim_matchday` |

### Asset Directories

- `escudos-pl/`, `escudos-ch/`, `escudos-l1/`, `escudos-l2/`, `escudos-nl/`, `escudos-nonleague/` — badge PNGs for domestic leagues
- `escudos-ucl/`, `escudos-uel/`, `escudos-uecl/` — badge PNGs for European club competitors (non-English clubs only; English clubs are pulled from `escudos-pl/`)
- `selecoes/` — badge PNGs for national teams (used by the "Seleção Inglesa" template)
- `resultados/` — template PNGs for match result images (e.g. `premierleague-template.png`, `premierleague-rect.png`)
- `tabela/` — template PNGs for standings images, including colored zone rects (e.g. `premierleague-rect-ucl.png`, `premierleague-rect-ucl-conf.png`)
- `noticias/` — template PNGs for news images
- `templates/` — thumbnail previews shown in the UI template selector
- `fontes/` — `.otf`/`.ttf` font files per competition

### Secrets

`.streamlit/secrets.toml` must contain:
```toml
GITHUB_TOKEN = "ghp_..."
GITHUB_REPO = "usuario/repo"
```

The app falls back to local `data/tabelas/` files if GitHub credentials are missing.

### Standings File Format

Each line: `Team Name J V E D GP GC SG P`
Example: `Arsenal 28 18 7 3 56 21 35 61`
(J=played, V=wins, E=draws, D=losses, GP=goals for, GC=goals against, SG=goal diff, P=points)

### Position History System

`data/posicoes.csv` tracks every team's league position at each matchday. It is built from `historico.csv` and is never committed to GitHub — it lives only locally and is rebuilt on demand.

**Matchday grouping** in `position_history.py` uses two calendar blocks:
- **Block A** (Fri/Sat/Sun/Mon): typical weekend round
- **Block B** (Tue/Wed/Thu): midweek round

A new matchday begins when the gap between consecutive game dates exceeds 4 days, or when the block changes. The `data_fim_matchday` stored in `posicoes.csv` is normalized to an "anchor date" (Saturday for Block A, Tuesday for Block B).

**Point deductions** are applied inside `position_history.py` via `_POINT_DEDUCTIONS` — a dict keyed by league string, containing `(team, threshold_date, pts)` tuples. Multiple entries for the same team are cumulative.

### Adding a New League

1. Add entry to `config/leagues_config.json` with all pixel offsets, font sizes, badge folder, and promotion zones
2. Add team abbreviations to `config/team_abbreviations.json`
3. Create badge PNGs in an `escudos-<prefix>/` folder
4. Add template/rect PNGs to `resultados/` and `tabela/`
5. Create initial standings file at `data/tabelas/<league>.txt`
6. Add the league to the relevant UI sections in `app.py`

### Keep-Alive Workflow

`acorda_apps.py` uses Playwright to visit the deployed Streamlit apps every 3 hours (via `.github/workflows/keep-streamlit-alive.yaml`) to prevent Streamlit Community Cloud from sleeping them.
