"""Recuperación léxica BM25 para español, sin dependencias externas.

BM25 (Robertson y Zaragoza, 2009) es transparente y reproducible, dos
propiedades que la auditoría necesita para registrar por qué un fragmento
llegó al modelo. La recuperación filtra por nivel de acceso y por
consentimiento antes de puntuar, de modo que un fragmento vedado nunca
compite por entrar a la consulta.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Callable, Iterable

from .corpus import Fragmento
from .util import tokens

PALABRAS_VACIAS = set("""
a al algo algun alguna algunas alguno algunos ante antes como con contra cual cuales cuando de del desde donde
durante e el ella ellas ello ellos en entre era eran es esa esas ese eso esos esta estaba estado estan estas este
esto estos fue fueron ha habia han hasta hay la las le les lo los mas me mi mientras muy nada ni no nos o otra
otras otro otros para pero poco por porque que quien quienes se sea segun ser si sido sin sobre son su sus tambien
tan te tenia tiene tienen todo todos tu un una unas uno unos y ya yo cual qué cómo cuál
""".split())


def raiz(tok: str) -> str:
    """Normalización mínima de plurales para que «masacres» encuentre «masacre»."""
    if len(tok) > 4 and tok.endswith("s") and not tok.endswith("ss"):
        return tok[:-1]
    return tok


def terminos(texto: str) -> list[str]:
    return [raiz(t) for t in tokens(texto) if t not in PALABRAS_VACIAS and len(t) > 1]


class IndiceBM25:
    def __init__(self, fragmentos: Iterable[Fragmento], k1: float = 1.5, b: float = 0.75):
        self.fragmentos = list(fragmentos)
        self.k1, self.b = k1, b
        self._tf = [Counter(terminos(f.texto)) for f in self.fragmentos]
        self._len = [sum(tf.values()) for tf in self._tf]
        self._prom = (sum(self._len) / len(self._len)) if self._len else 0.0
        df = Counter()
        for tf in self._tf:
            df.update(tf.keys())
        n = len(self.fragmentos)
        self._idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def buscar(
        self,
        consulta: str,
        k: int = 5,
        niveles: Iterable[str] | None = None,
        filtro: Callable[[Fragmento], bool] | None = None,
        puntaje_minimo: float = 0.0,
    ) -> list[tuple[Fragmento, float]]:
        """Devuelve hasta k fragmentos permitidos, ordenados por puntaje.

        `niveles` restringe los niveles de acceso admitidos. Los fragmentos de
        testimonios sin consentimiento para procesamiento con IA se excluyen
        siempre.
        """
        permitidos = set(niveles) if niveles is not None else None
        q = terminos(consulta)
        resultados = []
        for i, frag in enumerate(self.fragmentos):
            if permitidos is not None and frag.nivel_acceso not in permitidos:
                continue
            if not frag.documento.consentimiento_ia:
                continue
            if filtro is not None and not filtro(frag):
                continue
            tf, largo = self._tf[i], self._len[i]
            s = 0.0
            for t in q:
                f = tf.get(t, 0)
                if not f:
                    continue
                norm = 1 - self.b + self.b * (largo / self._prom if self._prom else 1)
                s += self._idf.get(t, 0.0) * f * (self.k1 + 1) / (f + self.k1 * norm)
            if s > puntaje_minimo:
                resultados.append((frag, s))
        resultados.sort(key=lambda x: (-x[1], x[0].id))
        return resultados[:k]
