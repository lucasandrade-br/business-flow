from __future__ import annotations

import hashlib
from decimal import Decimal, InvalidOperation
from typing import Any


def _normalize_string(value: Any) -> str:
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
        _normalize_string(id_produto),
        _normalize_string(gtin),
        _normalize_string(barras),
        _normalize_string(nome),
        _normalize_decimal_4(custo),
        _normalize_decimal_4(venda),
        _normalize_string(status),
    ]
    return _build_md5(parts)


def gerar_hash_cliente(id_cliente: Any, nome_cliente: Any, raz_social: Any) -> str:
    parts = [
        _normalize_string(id_cliente),
        _normalize_string(nome_cliente),
        _normalize_string(raz_social),
    ]
    return _build_md5(parts)


def gerar_hash_fornecedor(id_fornecedor: Any, nome_fornecedor: Any, raz_social: Any, dt_cadastro: Any) -> str:
    parts = [
        _normalize_string(id_fornecedor),
        _normalize_string(nome_fornecedor),
        _normalize_string(raz_social),
        #_normalize_string(dt_cadastro),
    ]
    return _build_md5(parts)
