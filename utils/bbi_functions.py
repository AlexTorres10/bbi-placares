import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Any
from datetime import datetime, timedelta

def _parse_score(placar: str) -> Tuple[int, int]:
    gh, ga = placar.split('-')
    return int(gh), int(ga)

def wdl(row: pd.Series, time: str) -> str:
    gh, ga = _parse_score(row['placar'])
    if gh == ga:
        return 'draw'
    home = row['casa'] == time
    return 'win' if (gh > ga if home else ga > gh) else 'loss'

def gf(row: pd.Series, time: str) -> int:
    gh, ga = _parse_score(row['placar'])
    return gh if row['casa'] == time else ga

def gs(row: pd.Series, time: str) -> int:
    gh, ga = _parse_score(row['placar'])
    return ga if row['casa'] == time else gh

def filtrar_por_mando(df: pd.DataFrame, nome_time: str, mando: str = 'geral') -> pd.DataFrame:
    if mando == 'casa':
        return df[df['casa'] == nome_time].copy()
    if mando == 'fora':
        return df[df['fora'] == nome_time].copy()
    return df.copy()

def _choose_worst_window_by_metric(df: pd.DataFrame, metric_col: str, limite_min_jogos: int) -> Tuple[int, Dict[str, int]]:
    """
    Escolhe a pior janela de resultados, priorizando:
      1. Maior proporção de derrotas;
      2. Maior número absoluto de derrotas;
      3. Menor tamanho de janela (fase mais concentrada e recente).
    """
    total = df.shape[0]
    best_len, best_counts = 0, {}
    best_metric, best_ratio = -1, -1.0

    # Iterar do menor pro maior para dar prioridade à fase recente
    for n in range(limite_min_jogos, total + 1):
        subset = df.tail(n)
        counts = subset[metric_col].value_counts().to_dict()
        losses = counts.get("loss", 0)
        ratio = losses / n if n > 0 else 0

        # Comparação em ordem de prioridade CORRIGIDA
        better = False
        if ratio > best_ratio:  # MUDANÇA: priorizar proporção primeiro
            better = True
        elif ratio == best_ratio:
            if losses > best_metric:  # MUDANÇA: depois número absoluto
                better = True
            elif losses == best_metric and (best_len == 0 or n < best_len):
                better = True

        if better:
            best_len = n
            best_counts = counts.copy()
            best_metric = losses
            best_ratio = ratio

    if best_len == 0:
        return total, df.tail(total)[metric_col].value_counts().to_dict()
    return best_len, best_counts

def _choose_best_window_by_metric(df: pd.DataFrame, metric_col: str, limite_min_jogos: int) -> Tuple[int, Dict[str, int]]:
    """
    Escolhe a melhor janela de resultados, priorizando:
      1. Maior proporção de vitórias;
      2. Maior número absoluto de vitórias;
      3. Menor tamanho de janela (fase mais concentrada e recente).
    """
    total = df.shape[0]
    best_len, best_counts = 0, {}
    best_metric, best_ratio = -1, -1.0

    # Iterar do menor pro maior para dar prioridade à fase recente e concentrada
    for n in range(limite_min_jogos, total + 1):
        subset = df.tail(n)
        counts = subset[metric_col].value_counts().to_dict()
        wins = counts.get("win", 0)
        ratio = wins / n if n > 0 else 0

        better = False
        if ratio > best_ratio:  # 1. Priorizar proporção
            better = True
        elif ratio == best_ratio:
            if wins > best_metric:  # 2. Depois número absoluto
                better = True
            # 3. Empate: priorizar menor 'n' (mais concentrado e recente)
            elif wins == best_metric and (best_len == 0 or n < best_len): 
                better = True

        if better:
            best_len = n
            best_counts = counts.copy()
            best_metric = wins
            best_ratio = ratio

    if best_len == 0:
        return 0, {}
    return best_len, best_counts

def _ultimo_jogo_recente(df: pd.DataFrame, limite_dias: int = 3) -> bool:
    """
    Verifica se o último jogo foi há 3 dias ou menos.
    Retorna True se foi recente, False caso contrário.
    """
    if df.empty:
        return False
    
    # Converte a data do último jogo para datetime
    ultimo_jogo = df.iloc[-1]['data']
    if isinstance(ultimo_jogo, str):
        data_ultimo_jogo = datetime.strptime(ultimo_jogo, '%Y-%m-%d')
    elif hasattr(ultimo_jogo, 'date'):  # Se for datetime
        data_ultimo_jogo = ultimo_jogo
    else:  # Se for date
        data_ultimo_jogo = datetime.combine(ultimo_jogo, datetime.min.time())
    
    # Calcula a diferença com a data atual (apenas a parte da data)
    data_atual = datetime.now().date()
    data_ultimo_jogo_date = data_ultimo_jogo.date() if hasattr(data_ultimo_jogo, 'date') else data_ultimo_jogo
    
    diferenca_dias = (data_atual - data_ultimo_jogo_date).days
    
    return diferenca_dias <= limite_dias

def detectar_fase_estendida_por_mando(df: pd.DataFrame, nome_time: str, mando: str = 'geral',
                                      limite_max_vitorias: int = 1, limite_min_vitorias: int = 5,
                                      limite_max_derrotas: int = 1, limite_min_derrotas: int = 5) -> Tuple[Dict[str,Any], List[str]]:
    df_filtrado = filtrar_por_mando(df, nome_time, mando)
    insights: List[str] = []
    total_jogos = df_filtrado.shape[0]

    sufixo = ""
    if mando == 'casa':
        sufixo = " em casa"
    elif mando == 'fora':
        sufixo = " fora de casa"

    if total_jogos < 3:
        return {'time': nome_time, 'mando': mando, 'jogos_analisados': total_jogos}, insights

    limite_min_jogos = 5 if mando in ['casa', 'fora'] else 7

    # Casos especiais: voltou a vencer/perder depois de longa sequência
    if total_jogos >= limite_min_jogos:
        if _ultimo_jogo_recente(df_filtrado):
            resultado_mais_recente = df_filtrado.iloc[-1]['result']
            maior_seq_v = 0
            maior_seq_d = 0

            for n in range(total_jogos, limite_min_jogos - 1, -1):
                subset = df_filtrado.tail(n)
                counts = subset['result'].value_counts()
                v, d = counts.get('win', 0), counts.get('loss', 0)

                if v == 1 and resultado_mais_recente == 'win':
                    prev = subset.iloc[:-1]['result'].value_counts().get('win', 0)
                    if prev == 0 and maior_seq_v == 0:
                        maior_seq_v = n
                if d == 1 and resultado_mais_recente == 'loss':
                    prev = subset.iloc[:-1]['result'].value_counts().get('loss', 0)
                    if prev == 0 and maior_seq_d == 0:
                        maior_seq_d = n

            if maior_seq_v > 0:
                insights.append(f"{nome_time} voltou a vencer{sufixo} depois de {maior_seq_v - 1} jogos sem vitória{sufixo}.")
            if maior_seq_d > 0:
                insights.append(f"{nome_time} perdeu{sufixo} depois de {maior_seq_d - 1} jogos sem derrota{sufixo}.")


    casos_especiais = any("voltou a vencer" in s or "perdeu" in s for s in insights)

    if not casos_especiais:
        # Má fase por derrotas (corrigida: seleciona a pior janela)
        if total_jogos >= limite_min_jogos:
            worst_len, worst_counts = _choose_worst_window_by_metric(df_filtrado, 'result', limite_min_jogos)
            losses = worst_counts.get('loss', 0)
            loss_ratio = losses / worst_len if worst_len > 0 else 0
            # Só mostrar se >= 70% de derrotas E número mínimo de derrotas
            if (losses >= limite_min_derrotas and worst_len >= limite_min_jogos and 
                loss_ratio >= 0.70):
                insights.append(f"{nome_time} perdeu {losses} dos últimos {worst_len} jogos{sufixo}.")

        # Função auxiliar
        def contar_jogos_cond(cond_func):
            for n in range(limite_min_jogos, total_jogos + 1):
                subset = df_filtrado.tail(n)
                resultados = subset['result'].value_counts()
                v, d = resultados.get('win', 0), resultados.get('loss', 0)
                if not cond_func(v, d):
                    return n - 1, subset.tail(n - 1)['result'].value_counts().to_dict()
            return total_jogos, df_filtrado.tail(total_jogos)['result'].value_counts().to_dict()

        # Má fase por poucas vitórias
        n_vit_ruim, res_vit_ruim = contar_jogos_cond(lambda v, d: v <= limite_max_vitorias)
        if n_vit_ruim >= limite_min_jogos and res_vit_ruim.get('win', 0) <= limite_max_vitorias:
            vitorias = res_vit_ruim.get('win', 0)
            if vitorias == 0:
                insights.append(f"{nome_time} não venceu nenhum dos últimos {n_vit_ruim} jogos{sufixo}.")
            else:
                insights.append(f"{nome_time} venceu apenas {vitorias} dos últimos {n_vit_ruim} jogos{sufixo}.")

        if total_jogos >= limite_min_jogos:
            best_len, best_counts = _choose_best_window_by_metric(df_filtrado, 'result', limite_min_jogos)
            wins = best_counts.get('win', 0)
            win_ratio = wins / best_len if best_len > 0 else 0
            
            # Só mostrar se >= 70% de vitórias E número mínimo de vitórias (5)
            # O limite_min_vitorias padrão deve ser 5 (como está na função)
            if (wins >= limite_min_vitorias and best_len >= limite_min_jogos and 
                win_ratio >= 0.70): 
                insights.append(f"{nome_time} venceu {wins} dos últimos {best_len} jogos{sufixo}. Boa fase!")

        # Boa fase por poucas derrotas
        n_derrotas_bom, res_derrotas_bom = contar_jogos_cond(lambda v, d: d <= limite_max_derrotas)
        if n_derrotas_bom >= limite_min_jogos and res_derrotas_bom.get('loss', 0) <= limite_max_derrotas:
            derrotas = res_derrotas_bom.get('loss', 0)
            if derrotas == 0:
                if n_derrotas_bom == total_jogos and mando != 'geral':
                    insights.append(f"{nome_time} não perdeu{sufixo} na temporada inteira.")
                else:
                    insights.append(f"{nome_time} está invicto{sufixo} há {n_derrotas_bom} jogos.")
            else:
                insights.append(f"{nome_time} sofreu apenas {derrotas} derrotas nos últimos {n_derrotas_bom} jogos{sufixo}.")

    return {'time': nome_time, 'mando': mando, 'jogos_analisados': total_jogos}, insights

def detectar_fase_estendida(df: pd.DataFrame, nome_time: str,
                            limite_max_vitorias: int = 2, limite_min_vitorias: int = 5,
                            limite_max_derrotas: int = 2, limite_min_derrotas: int = 5):
    return detectar_fase_estendida_por_mando(df, nome_time, 'geral',
                                             limite_max_vitorias, limite_min_vitorias,
                                             limite_max_derrotas, limite_min_derrotas)

def streaks_por_mando(df: pd.DataFrame, nome_time: str, mando: str = 'geral'):
    df_filtrado = filtrar_por_mando(df, nome_time, mando)
    win_streak = lose_streak = 0
    for res in reversed(df_filtrado['result'].tolist()):
        if res == 'win' and lose_streak == 0:
            win_streak += 1
        elif res == 'loss' and win_streak == 0:
            lose_streak += 1
        else:
            break
    return {'time': nome_time, 'mando': mando,
            'win_streak': win_streak, 'lose_streak': lose_streak}, win_streak, lose_streak

def streaks_extended_por_mando(df: pd.DataFrame, nome_time: str, mando: str = 'geral'):
    """
    Calcula sequências estendidas (sem vencer e invicto) a partir do jogo mais recente.
    - sem_vencer: jogos consecutivos recentes sem vitória (só draw/loss)
    - invicto: jogos consecutivos recentes sem derrota (só win/draw)
    """
    df_filtrado = filtrar_por_mando(df, nome_time, mando)
    sem_vencer = 0
    invicto = 0
    
    resultados = list(reversed(df_filtrado['result'].tolist()))
    
    # Contar sequência sem vencer (sem win)
    for res in resultados:
        if res in ('draw', 'loss'):
            sem_vencer += 1
        else:
            break
    
    # Contar sequência invicta (sem loss)
    for res in resultados:
        if res in ('win', 'draw'):
            invicto += 1
        else:
            break
    
    return {'time': nome_time, 'mando': mando,
            'sem_vencer': sem_vencer, 'invicto': invicto}, sem_vencer, invicto

def pontos_ultimos_jogos_por_mando(df: pd.DataFrame, nome_time: str,
                                   mando: str = 'geral', n: int = 5):
    df_filtrado = filtrar_por_mando(df, nome_time, mando)
    if mando in ['casa', 'fora'] and n > df_filtrado.shape[0]:
        n = df_filtrado.shape[0]
    if n == 0 or df_filtrado.empty:
        return {'time': nome_time, 'mando': mando, f'pts_ult{n}': 0}, 0
    ultimos_n = df_filtrado.tail(n)
    resultados = ultimos_n['result'].value_counts()
    pontos = resultados.get('win', 0) * 3 + resultados.get('draw', 0)
    return {'time': nome_time, 'mando': mando, f'pts_ult{n}': pontos}, pontos

def _filtrar_insights_redundantes(insights_forma: List[str], jogos_casa: int, jogos_fora: int, 
                                 lose_streak_casa: int, lose_streak_fora: int,
                                 win_streak_casa: int, win_streak_fora: int) -> List[str]:
    """
    Remove insights redundantes e melhora a apresentação quando a estatística 
    engloba todos os jogos de um mandante.
    """
    insights_filtrados = []
    import re

    def extrair_time(insight: str) -> str:
        # tenta capturar o nome do time até o verbo mais comum
        m = re.match(r'^(.*?)\s+(perdeu|não venceu|venceu|está|somou)\b', insight)
        if m:
            return m.group(1).strip()
        # fallback: primeira ocorrência antes de "em casa"/"fora"
        m2 = re.match(r'^(.*?)\s+(em casa|fora de casa)\b', insight)
        if m2:
            return m2.group(1).strip()
        return insight.split()[0]

    for insight in insights_forma:
        numeros = re.findall(r'\d+', insight)
        team = extrair_time(insight)

        # CASOS EM CASA
        if "em casa" in insight:
            # se a frase contém dois números, assumimos formato "X dos últimos Y"
            if len(numeros) >= 2:
                derrotas = int(numeros[0])
                jogos_analisados = int(numeros[-1])

                # perdeu todos os jogos em casa
                if "perdeu" in insight and derrotas == jogos_casa and jogos_analisados == jogos_casa and jogos_casa > 0:
                    if jogos_casa == 1:
                        insights_filtrados.append(f"{team} perdeu o único jogo em casa.")
                    else:
                        insights_filtrados.append(f"{team} perdeu todos os jogos em casa.")
                    continue

                # não venceu ainda em casa (0 vitórias nos jogos em casa analisados e janela == total de jogos em casa)
                if "não venceu" in insight and jogos_analisados == jogos_casa and jogos_casa > 0:
                    insights_filtrados.append(f"{team} ainda não venceu em casa.")
                    continue

                # substituir "últimos X jogos em casa" por "todos os jogos em casa" quando a janela cobre todos
                if jogos_analisados == jogos_casa and jogos_casa > 0:
                    insight = re.sub(r'últimos \d+ jogos em casa', 'todos os jogos em casa', insight)

        # CASOS FORA DE CASA
        elif "fora de casa" in insight:
            if len(numeros) >= 2:
                derrotas = int(numeros[0])
                jogos_analisados = int(numeros[-1])

                if "perdeu" in insight and derrotas == jogos_fora and jogos_analisados == jogos_fora and jogos_fora > 0:
                    if jogos_fora == 1:
                        insights_filtrados.append(f"{team} perdeu o único jogo fora de casa.")
                    else:
                        insights_filtrados.append(f"{team} perdeu todos os jogos fora de casa.")
                    continue

                if "não venceu" in insight and jogos_analisados == jogos_fora and jogos_fora > 0:
                    insights_filtrados.append(f"{team} ainda não venceu fora de casa.")
                    continue

                if jogos_analisados == jogos_fora and jogos_fora > 0:
                    insight = re.sub(r'últimos \d+ jogos fora de casa', 'todos os jogos fora de casa', insight)

        # Evitar duplicação com streaks já conhecidos
        if _eh_redundante_com_streak(insight, lose_streak_casa, lose_streak_fora, 
                                     win_streak_casa, win_streak_fora, jogos_casa, jogos_fora):
            continue

        # Evitar redundâncias diretas entre frases similares
        skip = False
        for insight_existente in insights_filtrados:
            if _sao_redundantes(insight, insight_existente):
                if _eh_mais_informativo(insight, insight_existente):
                    # substituir pela versão mais informativa
                    insights_filtrados.remove(insight_existente)
                    insights_filtrados.append(insight)
                skip = True
                break

        if not skip:
            insights_filtrados.append(insight)

    return insights_filtrados


def _eh_redundante_com_streak(insight: str, lose_streak_casa: int, lose_streak_fora: int,
                            win_streak_casa: int, win_streak_fora: int, 
                            jogos_casa: int, jogos_fora: int) -> bool:
    """
    Verifica se um insight de forma é redundante com um streak já identificado.
    """
    import re
    
    # Extrair números do insight
    numeros = re.findall(r'\d+', insight)
    if not numeros:
        return False
        
    # Para insights de derrotas em casa
    if "perdeu" in insight and "em casa" in insight:
        if len(numeros) >= 2:
            derrotas = int(numeros[0])
            jogos_janela = int(numeros[1])
            # Se perdeu X dos X jogos em casa E tem streak de X derrotas em casa = redundante
            if (derrotas == jogos_janela and lose_streak_casa >= derrotas):
                return True
                
    # Para insights de derrotas fora de casa  
    if "perdeu" in insight and "fora de casa" in insight:
        if len(numeros) >= 2:
            derrotas = int(numeros[0])
            jogos_janela = int(numeros[1])
            if (derrotas == jogos_janela and lose_streak_fora >= derrotas):
                return True
                
    # Para insights de "não venceu nenhum" quando há streak de derrotas
    if "não venceu nenhum" in insight and "em casa" in insight:
        if len(numeros) >= 1:
            jogos_sem_vitoria = int(numeros[0])
            # Se não venceu X jogos E tem streak de derrotas >= X-1, é redundante
            if lose_streak_casa >= jogos_sem_vitoria - 1:
                return True
                
    if "não venceu nenhum" in insight and "fora de casa" in insight:
        if len(numeros) >= 1:
            jogos_sem_vitoria = int(numeros[0])
            if lose_streak_fora >= jogos_sem_vitoria - 1:
                return True
                
    # Para insights de vitórias
    if "venceu" in insight and "em casa" in insight and "apenas" not in insight:
        if len(numeros) >= 2:
            vitorias = int(numeros[0]) 
            jogos_janela = int(numeros[1])
            if (vitorias == jogos_janela and win_streak_casa >= vitorias):
                return True
                
    if "venceu" in insight and "fora de casa" in insight and "apenas" not in insight:
        if len(numeros) >= 2:
            vitorias = int(numeros[0])
            jogos_janela = int(numeros[1]) 
            if (vitorias == jogos_janela and win_streak_fora >= vitorias):
                return True
    
    return False

def _sao_redundantes(insight1: str, insight2: str) -> bool:
    """
    Verifica se dois insights são redundantes.
    """
    # Mesma informação sobre vitórias/derrotas em sequência de mandante específico
    if ("não venceu nenhum" in insight1 and "perdeu" in insight2 and 
        "todos os jogos" in insight1 and "todos os jogos" in insight2 and
        ("em casa" in insight1) == ("em casa" in insight2) and
        ("fora de casa" in insight1) == ("fora de casa" in insight2)):
        return True
        
    # Mesma informação sobre não vencer vs perder todos
    if (("não venceu nenhum dos últimos" in insight1 and "perdeu" in insight2 and "dos últimos" in insight2) or
        ("não venceu nenhum dos últimos" in insight2 and "perdeu" in insight1 and "dos últimos" in insight1)):
        # Extrair números para ver se são do mesmo período
        import re
        nums1 = re.findall(r'\d+', insight1)
        nums2 = re.findall(r'\d+', insight2)
        if nums1 and nums2 and nums1[-1] == nums2[-1]:  # mesmo número de jogos
            return True
    
    return False

def _eh_mais_informativo(insight1: str, insight2: str) -> bool:
    """
    Determina qual insight é mais informativo.
    Prioridade: "perdeu X dos Y" > "não venceu nenhum dos Y"
    """
    if "perdeu" in insight1 and "não venceu nenhum" in insight2:
        return True
    return False

def allinsights(df: pd.DataFrame, nome: str, time_ou_liga: str = 'time') -> List[str]:
    """
    Função principal de insights (única versão oficial).
    Compatível com uso para times individuais e ligas completas.
    """
    insights: List[str] = []

    if time_ou_liga == 'time':
        # análises para um time
        estat_forma_geral, insights_forma_geral = detectar_fase_estendida_por_mando(df, nome, 'geral')
        estat_streak_geral, win_streak_geral, lose_streak_geral = streaks_por_mando(df, nome, 'geral')
        estat_pontos_geral, pontos_geral = pontos_ultimos_jogos_por_mando(df, nome, 'geral')

        estat_forma_casa, insights_forma_casa = detectar_fase_estendida_por_mando(df, nome, 'casa')
        estat_streak_casa, win_streak_casa, lose_streak_casa = streaks_por_mando(df, nome, 'casa')
        estat_pontos_casa, pontos_casa = pontos_ultimos_jogos_por_mando(df, nome, 'casa', 3)

        estat_forma_fora, insights_forma_fora = detectar_fase_estendida_por_mando(df, nome, 'fora')
        estat_streak_fora, win_streak_fora, lose_streak_fora = streaks_por_mando(df, nome, 'fora')
        estat_pontos_fora, pontos_fora = pontos_ultimos_jogos_por_mando(df, nome, 'fora', 3)

        # Sequências estendidas (sem vencer / invicto)
        _, sem_vencer_geral, invicto_geral = streaks_extended_por_mando(df, nome, 'geral')
        _, sem_vencer_casa, invicto_casa = streaks_extended_por_mando(df, nome, 'casa')
        _, sem_vencer_fora, invicto_fora = streaks_extended_por_mando(df, nome, 'fora')

        df_casa = filtrar_por_mando(df, nome, 'casa')
        df_fora = filtrar_por_mando(df, nome, 'fora')
        
        # Detectar se streak coincide com todos os jogos do mando
        streak_casa_total = win_streak_casa == df_casa.shape[0] or lose_streak_casa == df_casa.shape[0]
        streak_fora_total = win_streak_fora == df_fora.shape[0] or lose_streak_fora == df_fora.shape[0]

        # sequências gerais
        if win_streak_geral >= 3:
            insights.append(f"{nome} está na {win_streak_geral}ª vitória seguida!")
        if lose_streak_geral >= 3:
            insights.append(f"{nome} está na {lose_streak_geral}ª derrota seguida!")
            
        # casa - só mostrar se não for redundante
        if win_streak_casa >= 3 and not streak_casa_total:
            insights.append(f"{nome} está na {win_streak_casa}ª vitória seguida em casa!")
        if lose_streak_casa >= 3 and not streak_casa_total:
            insights.append(f"{nome} está na {lose_streak_casa}ª derrota seguida em casa!")
            
        # fora - só mostrar se não for redundante  
        if win_streak_fora >= 3 and not streak_fora_total:
            insights.append(f"{nome} está na {win_streak_fora}ª vitória seguida fora de casa!")
        if lose_streak_fora >= 3 and not streak_fora_total:
            insights.append(f"{nome} está na {lose_streak_fora}ª derrota seguida fora de casa!")

        # sequências sem vencer (só derrotas e empates, sem vitória)
        # só mostrar se não for redundante com sequência de derrotas puras
        if sem_vencer_geral >= 5 and sem_vencer_geral != lose_streak_geral:
            insights.append(f"{nome} está há {sem_vencer_geral} jogos sem vencer.")
        if sem_vencer_casa >= 5 and sem_vencer_casa != lose_streak_casa and not streak_casa_total:
            insights.append(f"{nome} está há {sem_vencer_casa} jogos sem vencer em casa.")
        if sem_vencer_fora >= 5 and sem_vencer_fora != lose_streak_fora and not streak_fora_total:
            insights.append(f"{nome} está há {sem_vencer_fora} jogos sem vencer fora de casa.")

        # sequências invictas (só vitórias e empates, sem derrota)
        # só mostrar se não for redundante com sequência de vitórias puras
        if invicto_geral >= 5 and invicto_geral != win_streak_geral:
            insights.append(f"{nome} está invicto há {invicto_geral} jogos.")
        if invicto_casa >= 5 and invicto_casa != win_streak_casa and not streak_casa_total and invicto_casa != df_casa.shape[0]:
            insights.append(f"{nome} está invicto há {invicto_casa} jogos em casa.")
        if invicto_fora >= 5 and invicto_fora != win_streak_fora and not streak_fora_total and invicto_fora != df_fora.shape[0]:
            insights.append(f"{nome} está invicto há {invicto_fora} jogos fora de casa.")

        # pontuação últimos jogos
        if df.shape[0] >= 5:
            if pontos_geral >= 10:
                insights.append(f"{nome} somou {pontos_geral} pontos nos últimos 5 jogos. Excelente fase!")
            elif pontos_geral <= 2:
                if pontos_geral == 0 and lose_streak_geral <= 5:
                    insights.append(f"{nome} não pontuou nos últimos 5 jogos.")
                elif pontos_geral == 1:
                    insights.append(f"{nome} somou apenas 1 ponto nos últimos 5 jogos.")
                else:
                    insights.append(f"{nome} somou apenas {pontos_geral} pontos nos últimos 5 jogos.")

        # casa
        if df_casa.shape[0] >= 3:
            if pontos_casa >= 7:
                insights.append(f"{nome} somou {pontos_casa} pontos nos últimos 3 jogos em casa. Ótimo!")
            elif pontos_casa == 0:
                insights.append(f"{nome} não pontuou nos últimos 3 jogos em casa.")
            elif pontos_casa <= 2:
                insights.append(f"{nome} somou apenas {pontos_casa} pontos nos últimos 3 jogos em casa.")
        # fora
        if df_fora.shape[0] >= 3:
            if pontos_fora >= 7:
                insights.append(f"{nome} somou {pontos_fora} pontos nos últimos 3 jogos fora de casa. Excelente!")
            elif pontos_fora == 0:
                insights.append(f"{nome} não pontuou nos últimos 3 jogos fora de casa.")
            elif pontos_fora <= 2:
                insights.append(f"{nome} somou apenas {pontos_fora} pontos nos últimos 3 jogos fora de casa.")

        # Filtrar insights de forma para evitar redundâncias
        insights_filtrados = _filtrar_insights_redundantes(insights_forma_geral + insights_forma_casa + insights_forma_fora, 
                                                           df_casa.shape[0], df_fora.shape[0], 
                                                           lose_streak_casa, lose_streak_fora,
                                                           win_streak_casa, win_streak_fora)
        insights.extend(insights_filtrados)

    elif time_ou_liga == 'liga':
        # análises de liga (processando e limpando insights por time)
        for time in df:
            # dataframes por mando
            df_time = df[time]
            df_casa = filtrar_por_mando(df_time, time, 'casa')
            df_fora = filtrar_por_mando(df_time, time, 'fora')

            # forma / streaks / pontos
            estat_forma, insights_forma = detectar_fase_estendida_por_mando(df_time, time, 'geral')
            estat_streak, win_streak, lose_streak = streaks_por_mando(df_time, time, 'geral')
            estat_pontos, pontos = pontos_ultimos_jogos_por_mando(df_time, time, 'geral')

            _, insights_casa = detectar_fase_estendida_por_mando(df_time, time, 'casa')
            _, win_casa, lose_casa = streaks_por_mando(df_time, time, 'casa')

            _, insights_fora = detectar_fase_estendida_por_mando(df_time, time, 'fora')
            _, win_fora, lose_fora = streaks_por_mando(df_time, time, 'fora')

            # Sequências estendidas (sem vencer / invicto)
            _, sem_vencer_geral, invicto_geral = streaks_extended_por_mando(df_time, time, 'geral')
            _, sem_vencer_casa, invicto_casa = streaks_extended_por_mando(df_time, time, 'casa')
            _, sem_vencer_fora, invicto_fora = streaks_extended_por_mando(df_time, time, 'fora')

            # insights curtos (sequências)
            if win_streak >= 3:
                insights.append(f"{time} está na {win_streak}ª vitória seguida!")
            if lose_streak >= 3:
                insights.append(f"{time} está na {lose_streak}ª derrota seguida!")
            if win_casa >= 3:
                insights.append(f"{time} está na {win_casa}ª vitória seguida em casa!")
            if lose_casa >= 3:
                insights.append(f"{time} está na {lose_casa}ª derrota seguida em casa!")
            if win_fora >= 3:
                insights.append(f"{time} está na {win_fora}ª vitória seguida fora de casa!")
            if lose_fora >= 3:
                insights.append(f"{time} está na {lose_fora}ª derrota seguida fora de casa!")

            # sequências sem vencer (liga)
            if sem_vencer_geral >= 5 and sem_vencer_geral != lose_streak:
                insights.append(f"{time} está há {sem_vencer_geral} jogos sem vencer.")
            if sem_vencer_casa >= 5 and sem_vencer_casa != lose_casa:
                insights.append(f"{time} está há {sem_vencer_casa} jogos sem vencer em casa.")
            if sem_vencer_fora >= 5 and sem_vencer_fora != lose_fora:
                insights.append(f"{time} está há {sem_vencer_fora} jogos sem vencer fora de casa.")

            # sequências invictas (liga)
            if invicto_geral >= 5 and invicto_geral != win_streak:
                insights.append(f"{time} está invicto há {invicto_geral} jogos.")
            if invicto_casa >= 5 and invicto_casa != win_casa and invicto_casa != df_casa.shape[0]:
                insights.append(f"{time} está invicto há {invicto_casa} jogos em casa.")
            if invicto_fora >= 5 and invicto_fora != win_fora and invicto_fora != df_fora.shape[0]:
                insights.append(f"{time} está invicto há {invicto_fora} jogos fora de casa.")

            # --- LIMPANDO e ADICIONANDO os insights de forma (apenas após corretor) ---
            # Observe: passar os contadores/streaks corretos para a função de limpeza
            jogos_casa = df_casa.shape[0]
            jogos_fora = df_fora.shape[0]

            insights_a_filtrar = insights_forma + insights_casa + insights_fora

            if insights_a_filtrar:
                insights_filtrados_time = _filtrar_insights_redundantes(
                    insights_a_filtrar,
                    jogos_casa, jogos_fora,
                    lose_casa, lose_fora,
                    win_casa, win_fora
                )
                # Adiciona só os insights já "corrigidos"
                insights.extend(insights_filtrados_time)

    return insights

def atualiza_tabela(tabela, home, away, result, tipo_tabela=''):
    # Aqui estou contando que o que está no banco de dados já está nos conformes.
    homescore = int(result.split('-')[0])
    awayscore = int(result.split('-')[1])
    for team in [home, away]:
        if team == home:
            ishome = True
        else:
            ishome = False
        if tipo_tabela == '':
            if ishome:
                gd = homescore-awayscore
                tabela['GM'] = np.where(tabela['Time'] == team,tabela['GM']+homescore,tabela['GM'])
                tabela['GS'] = np.where(tabela['Time'] == team,tabela['GS']+awayscore,tabela['GS'])
            else:
                gd = awayscore-homescore
                tabela['GM'] = np.where(tabela['Time'] == team,tabela['GM']+awayscore,tabela['GM'])
                tabela['GS'] = np.where(tabela['Time'] == team,tabela['GS']+homescore,tabela['GS'])
            #Mais um jogo
            tabela['J'] = np.where(tabela['Time'] == team,tabela['J']+1,tabela['J'])
            tabela['SG'] = np.where(tabela['Time'] == team,tabela['SG']+gd,tabela['SG'])

            if gd > 0:
                tabela['Pts'] = np.where(tabela['Time'] == team,tabela['Pts']+3,tabela['Pts'])
                tabela['V'] = np.where(tabela['Time'] == team,tabela['V']+1,tabela['V'])
            elif gd == 0:
                tabela['Pts'] = np.where(tabela['Time'] == team,tabela['Pts']+1,tabela['Pts'])
                tabela['E'] = np.where(tabela['Time'] == team,tabela['E']+1,tabela['E'])
            else:
                tabela['D'] = np.where(tabela['Time'] == team,tabela['D']+1,tabela['D'])
        elif tipo_tabela == 'mandante':
            if ishome:
                gd = homescore-awayscore
                tabela['GM'] = np.where(tabela['Time'] == team,tabela['GM']+homescore,tabela['GM'])
                tabela['GS'] = np.where(tabela['Time'] == team,tabela['GS']+awayscore,tabela['GS'])

                tabela['J'] = np.where(tabela['Time'] == team,tabela['J']+1,tabela['J'])
                tabela['SG'] = np.where(tabela['Time'] == team,tabela['SG']+gd,tabela['SG'])

                if gd > 0:
                    tabela['Pts'] = np.where(tabela['Time'] == team,tabela['Pts']+3,tabela['Pts'])
                    tabela['V'] = np.where(tabela['Time'] == team,tabela['V']+1,tabela['V'])
                elif gd == 0:
                    tabela['Pts'] = np.where(tabela['Time'] == team,tabela['Pts']+1,tabela['Pts'])
                    tabela['E'] = np.where(tabela['Time'] == team,tabela['E']+1,tabela['E'])
                else:
                    tabela['D'] = np.where(tabela['Time'] == team,tabela['D']+1,tabela['D'])
        elif tipo_tabela == 'visitante':
            if not ishome:
                gd = awayscore-homescore
                tabela['GM'] = np.where(tabela['Time'] == team,tabela['GM']+homescore,tabela['GM'])
                tabela['GS'] = np.where(tabela['Time'] == team,tabela['GS']+awayscore,tabela['GS'])

                tabela['J'] = np.where(tabela['Time'] == team,tabela['J']+1,tabela['J'])
                tabela['SG'] = np.where(tabela['Time'] == team,tabela['SG']+gd,tabela['SG'])

                if gd > 0:
                    tabela['Pts'] = np.where(tabela['Time'] == team,tabela['Pts']+3,tabela['Pts'])
                    tabela['V'] = np.where(tabela['Time'] == team,tabela['V']+1,tabela['V'])
                elif gd == 0:
                    tabela['Pts'] = np.where(tabela['Time'] == team,tabela['Pts']+1,tabela['Pts'])
                    tabela['E'] = np.where(tabela['Time'] == team,tabela['E']+1,tabela['E'])
                else:
                    tabela['D'] = np.where(tabela['Time'] == team,tabela['D']+1,tabela['D'])