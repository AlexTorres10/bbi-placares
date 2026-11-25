"""Gera data/jogadores.csv (sobrenome,nome_completo,time) a partir da API oficial do Fantasy Premier League.
Uso: python scripts/atualizar_jogadores.py"""
import csv
import json
import os
import re
import urllib.request

URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
SAIDA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "jogadores.csv")

# nome FPL -> nome usado no app
TIMES = {
    "Man City": "Manchester City", "Man Utd": "Manchester United", "Newcastle": "Newcastle United",
    "Nott'm Forest": "Nottingham Forest", "Spurs": "Tottenham Hotspur", "Leeds": "Leeds United",
    "Wolves": "Wolverhampton", "West Ham": "West Ham",
}


# Ajustes manuais: (time, web_name da FPL) -> nome pelo qual o jogador é conhecido.
# Edite aqui (e não no CSV) para a correção sobreviver a novas execuções.
OVERRIDES = {
    ("Arsenal", "Gabriel"): "Gabriel Magalhães",
    ("Bournemouth", "Rayan"): "Rayan",
    ("Brentford", "O.Dango"): "Dango Ouattara",
    ("Brighton", "Mitoma"): "Kaoru Mitoma",
    ("Crystal Palace", "Yeremy"): "Yéremy Pino",
    ("Leeds United", "Tanaka"): "Ao Tanaka",
    ("Liverpool", "Endo"): "Wataru Endo",
    ("Liverpool", "A.Becker"): "Alisson",
    ("Sunderland", "Jocelin.T"): "Jocelin Ta Bi",
    ("Fulham", "Ángel"): "Ángel",
    ("Ipswich Town", "Florentino"): "Florentino",
    ("Manchester City", "Allan"): "Allan",
    ("Manchester City", "Rúben"): "Rúben Dias",
    ("Nottingham Forest", "John"): "John Victor",
    ("Sunderland", "Reinildo"): "Reinildo",
}

PARTICULAS = {"de", "da", "do", "dos", "das", "di", "van", "von", "der", "den", "el", "al", "le", "la", "ben", "bin", "jr", "jr."}


def _n(t):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c)).lower()


def nome_conhecido(e, time):
    """Nome pelo qual o jogador é mais conhecido (ex.: Bruno Guimarães, Gabriel Jesus, Alysson)."""
    web, first, second = e["web_name"].strip(), e["first_name"].strip(), e["second_name"].strip()
    if (time, web) in OVERRIDES:
        return OVERRIDES[(time, web)]
    ft, st = first.split(), second.split()
    f1 = ft[0] if ft else ""
    primeiro = first if len(ft) <= 3 else f1  # "El Hadji Malick" fica inteiro
    if "." in web:
        partes = [x for x in web.split(".") if x]
        if web.endswith("."):  # "Bruno G." / "Matheus N." -> primeiro nome + 1º sobrenome
            return f"{f1} {st[0]}"
        if len(partes) == 2 and len(partes[0]) > 2 and len(partes[1]) <= 2:  # "Tóth.A", "Kroupi.Jr"
            return f"{f1} {partes[0]}"
        return f"{f1} {partes[-1]}"  # "G.Jesus", "J.Timber"
    if _n(web) == _n(second) and len(st) <= 3:  # "Van de Ven" -> Micky van de Ven
        acentos = lambda t: sum(ord(c) > 127 for c in t)
        return f"{primeiro} {web if acentos(web) > acentos(second) else second}"
    if " " in web:
        if _n(ft[0]) in _n(web).split():  # "Fábio Vieira", "Igor Jesus": já vem completo
            return web
        return f"{primeiro} {web}"  # "Mac Allister", "Di Gregorio"
    if _n(web) in [_n(x) for x in ft]:
        # apelido: mononímia brasileira (nome do meio longo) ou primeiro nome + sobrenome (Tosin Adarabioyo)
        if len(st) >= 3:
            return web
        if len(ft) > 1 and _n(web) == _n(ft[-1]):  # "Igor Thiago"
            return first
        return f"{web} {second}" if len(ft) > 1 else f"{first} {second}"
    return f"{primeiro} {web}"  # só sobrenome (Saka, Gyökeres)


def chaves(e, nome):
    """Formas de sobrenome que o FotMob pode usar: nome conhecido, última palavra dele e o sobrenome curto."""
    second, web = e["second_name"].strip(), e["web_name"].strip()
    ks = {nome, nome.split()[-1]}
    if "." not in web:
        ks.add(web)
    sp = second.split()
    if 0 < len(sp) <= 2:
        ks.add(second)
    return {k for k in ks if len(k) > 1}


def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    times = {t["id"]: TIMES.get(t["name"], t["name"]) for t in d["teams"]}
    linhas = set()
    for e in d["elements"]:
        if e["status"] == "u":  # indisponível = saiu do clube / emprestado
            continue
        time = times[e["team"]]
        nome = nome_conhecido(e, time)
        for k in chaves(e, nome):
            linhas.add((k, nome, time))
    with open(SAIDA, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sobrenome", "nome_completo", "time"])
        w.writerows(sorted(linhas, key=lambda r: (r[2], r[1], r[0])))
    print(f"{len(linhas)} linhas, {len(d['elements'])} jogadores -> {SAIDA}")


if __name__ == "__main__":
    main()
