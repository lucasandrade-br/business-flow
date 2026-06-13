from __future__ import annotations

import hashlib
import re
import unicodedata
from difflib import SequenceMatcher
from decimal import Decimal, InvalidOperation
from typing import Any


TOLERANCIA_NUMERICA_PADRAO = Decimal("0.1")


def _to_decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")

    if isinstance(value, Decimal):
        return value

    try:
        raw = str(value).strip().replace(",", ".")
        return Decimal(raw)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def normalizar_texto_tolerante(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).replace("\ufffd", " ")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.upper()
    text = re.sub(r"[^A-Z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalizar_nome_produto_tolerante(value: Any) -> str:
    normalized = normalizar_texto_tolerante(value)
    if not normalized:
        return ""
    tokens = sorted(token for token in normalized.split(" ") if token)
    return " ".join(tokens)


def percentual_semelhanca_textual(
    valor_a: Any,
    valor_b: Any,
    *,
    ordenar_tokens: bool = False,
) -> float:
    texto_a = normalizar_texto_tolerante(valor_a)
    texto_b = normalizar_texto_tolerante(valor_b)

    if ordenar_tokens:
        texto_a = " ".join(sorted(token for token in texto_a.split(" ") if token))
        texto_b = " ".join(sorted(token for token in texto_b.split(" ") if token))

    if not texto_a and not texto_b:
        return 1.0
    if not texto_a or not texto_b:
        return 0.0

    return SequenceMatcher(None, texto_a, texto_b).ratio()


def textos_semelhantes(
    valor_a: Any,
    valor_b: Any,
    *,
    limiar: float = 0.8,
    ordenar_tokens: bool = False,
) -> bool:
    return percentual_semelhanca_textual(
        valor_a,
        valor_b,
        ordenar_tokens=ordenar_tokens,
    ) >= float(limiar)


def valores_equivalentes_com_tolerancia(
    valor_a: Any,
    valor_b: Any,
    tolerancia: Decimal = TOLERANCIA_NUMERICA_PADRAO,
) -> bool:
    return abs(_to_decimal(valor_a) - _to_decimal(valor_b)) <= tolerancia


def _normalize_string(value: Any) -> str:
    return normalizar_texto_tolerante(value)


def _normalize_identifier(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().upper()


def _normalize_decimal_4(value: Any) -> str:
    if value is None or value == "":
        dec = Decimal("0")
    else:
        try:
            raw = str(value).strip().replace(",", ".")
            dec = Decimal(raw)
        except (InvalidOperation, ValueError, TypeError):
            dec = Decimal("0")
    return f"{dec:.4f}"


def _build_md5(parts: list[str]) -> str:
    base = "|".join(parts)
    return hashlib.md5(base.encode("utf-8")).hexdigest()


def gerar_hash_produto(id_produto: Any, gtin: Any, barras: Any, nome: Any, custo: Any, venda: Any, status: Any) -> str:
    parts = [
        _normalize_identifier(id_produto),
        _normalize_identifier(gtin),
        _normalize_identifier(barras),
        normalizar_nome_produto_tolerante(nome),
        _normalize_decimal_4(custo),
        _normalize_decimal_4(venda),
        normalizar_texto_tolerante(status),
    ]
    return _build_md5(parts)


def gerar_hash_cliente(id_cliente: Any, nome_cliente: Any, raz_social: Any) -> str:
    parts = [
        _normalize_identifier(id_cliente),
        normalizar_texto_tolerante(nome_cliente),
        normalizar_texto_tolerante(raz_social),
    ]
    return _build_md5(parts)


def gerar_hash_fornecedor(id_fornecedor: Any, nome_fornecedor: Any, raz_social: Any, dt_cadastro: Any) -> str:
    parts = [
        _normalize_identifier(id_fornecedor),
        normalizar_texto_tolerante(nome_fornecedor),
        normalizar_texto_tolerante(raz_social),
        #_normalize_string(dt_cadastro),
    ]
    return _build_md5(parts)
