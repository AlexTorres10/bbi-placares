"""Base de jogadores (sobrenome -> nome completo, por time) usada no Pretty Printer."""
import csv
import os
import unicodedata

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "jogadores.csv")

_EXTRA = str.maketrans({"ø": "o", "Ø": "O", "ł": "l", "Ł": "L", "đ": "d", "Đ": "D", "ß": "ss", "æ": "ae", "Æ": "AE", "œ": "oe", "ı": "i"})
_cache = None


def normalizar(texto):
    """Minúsculas, sem acentos, sem pontuação de espaçamento."""
    t = unicodedata.normalize("NFKD", (texto or "").translate(_EXTRA))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.lower().replace("-", " ").replace(".", ". ").split())


def _carregar():
    global _cache
    if _cache is None:
        _cache = {}
        if os.path.exists(CSV_PATH):
            with open(CSV_PATH, encoding="utf-8", newline="") as f:
                for r in csv.DictReader(f):
                    chave = (normalizar(r["time"]), normalizar(r["sobrenome"]))
                    _cache.setdefault(chave, set()).add(r["nome_completo"])
    return _cache


def buscar_jogador(sobrenome, times):
    """Procura o nome completo em cada time de `times`, na ordem.
    Retorna None se não achar ou se for ambíguo dentro do time."""
    base = _carregar()
    for time in times:
        nomes = base.get((normalizar(time), normalizar(sobrenome)))
        if nomes and len(nomes) == 1:
            return next(iter(nomes))
    return None
