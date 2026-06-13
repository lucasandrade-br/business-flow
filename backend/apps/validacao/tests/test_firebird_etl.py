from __future__ import annotations

from apps.validacao.services.firebird_etl import _normalizar_dados_cliente_legado


def test_normalizar_dados_cliente_legado_retorna_consumidor_geral_para_id_zero() -> None:
    assert _normalizar_dados_cliente_legado(0, "Cliente XPTO (nao cadastrado)") == (0, "Consumidor Geral")


def test_normalizar_dados_cliente_legado_retorna_consumidor_geral_para_id_vazio() -> None:
    assert _normalizar_dados_cliente_legado("", "Cliente XPTO") == (0, "Consumidor Geral")


def test_normalizar_dados_cliente_legado_mantem_nome_para_id_valido() -> None:
    assert _normalizar_dados_cliente_legado(123, "Mercado Central") == (123, "Mercado Central")
