from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.cadastros.models import Fornecedor, Produto, UnidadeMedida
from apps.compras.models import Compra, ItemCompra


def _criar_unidade(sigla: str = "UN") -> UnidadeMedida:
    return UnidadeMedida.objects.create(sigla=sigla, descricao=sigla)


def _criar_fornecedor(id_fornecedor: int, nome: str) -> Fornecedor:
    return Fornecedor.objects.create(
        id_fornecedor=id_fornecedor,
        nome_fornecedor=nome,
    )


def _criar_produto(id_produto: int, nome: str, unidade: UnidadeMedida) -> Produto:
    return Produto.objects.create(
        id_produto=id_produto,
        produto=nome,
        id_und_medida=unidade,
        custo=Decimal("10.000000"),
        venda=Decimal("15.000000"),
        status="ATIVO",
        markup=Decimal("0.0000"),
        markup_inv=Decimal("0.0000"),
        perda=Decimal("0.0000"),
        fisico=Decimal("0.0000"),
        aliqefc="",
        cod_g3n=0,
        cod_rel=0,
    )


@pytest.mark.django_db
def test_listagem_compras_oficiais_filtra_por_fornecedor_produto_nfe_status() -> None:
    unidade = _criar_unidade("UN")
    fornecedor_1 = _criar_fornecedor(8101, "FORNECEDOR API 1")
    fornecedor_2 = _criar_fornecedor(8102, "FORNECEDOR API 2")
    produto_1 = _criar_produto(8201, "PRODUTO API 1", unidade)
    produto_2 = _criar_produto(8202, "PRODUTO API 2", unidade)

    compra_1 = Compra.objects.create(
        id_legado=9301,
        nota=1001,
        fornecedor=fornecedor_1,
        data_emissao=date(2026, 1, 10),
        data_lanc=date(2026, 1, 10),
        valor_produtos=Decimal("20.000000"),
        valor_total_documento=Decimal("20.000000"),
        nfe_status="AUTORIZADA",
    )
    ItemCompra.objects.create(
        compra=compra_1,
        produto=produto_1,
        unidade_medida=unidade,
        quantidade=Decimal("2.000000"),
        valor_custo=Decimal("10.000000"),
        valor_total_item=Decimal("20.000000"),
    )

    compra_2 = Compra.objects.create(
        id_legado=9302,
        nota=1002,
        fornecedor=fornecedor_2,
        data_emissao=date(2026, 1, 11),
        data_lanc=date(2026, 1, 11),
        valor_produtos=Decimal("30.000000"),
        valor_total_documento=Decimal("30.000000"),
        nfe_status="PENDENTE",
    )
    ItemCompra.objects.create(
        compra=compra_2,
        produto=produto_2,
        unidade_medida=unidade,
        quantidade=Decimal("3.000000"),
        valor_custo=Decimal("10.000000"),
        valor_total_item=Decimal("30.000000"),
    )

    client = APIClient()
    response = client.get(
        "/api/compras/compras",
        {
            "fornecedor_id": fornecedor_1.id_fornecedor,
            "produto_id": produto_1.id_produto,
            "nfe_status": "AUTORIZADA",
        },
        HTTP_HOST="localhost",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["id_compra"] == compra_1.id_compra


@pytest.mark.django_db
def test_detalhe_compra_oficial_retorna_itens() -> None:
    unidade = _criar_unidade("CX")
    fornecedor = _criar_fornecedor(8110, "FORNECEDOR API DETALHE")
    produto = _criar_produto(8210, "PRODUTO API DETALHE", unidade)

    compra = Compra.objects.create(
        id_legado=9310,
        nota=1010,
        fornecedor=fornecedor,
        data_emissao=date(2026, 2, 1),
        data_lanc=date(2026, 2, 1),
        valor_produtos=Decimal("40.000000"),
        valor_total_documento=Decimal("40.000000"),
        nfe_status="AUTORIZADA",
    )
    item = ItemCompra.objects.create(
        compra=compra,
        produto=produto,
        unidade_medida=unidade,
        quantidade=Decimal("4.000000"),
        valor_custo=Decimal("10.000000"),
        valor_total_item=Decimal("40.000000"),
    )

    client = APIClient()
    response = client.get(f"/api/compras/compras/{compra.id_compra}", HTTP_HOST="localhost")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id_compra"] == compra.id_compra
    assert payload["fornecedor_nome"] == fornecedor.nome_fornecedor
    assert len(payload["itens"]) == 1
    assert payload["itens"][0]["id_item_compra"] == item.id_item_compra


@pytest.mark.django_db
def test_listagem_itens_compra_filtra_por_fornecedor_produto_status_nfe() -> None:
    unidade = _criar_unidade("UN")
    fornecedor_1 = _criar_fornecedor(8121, "FORNECEDOR ITENS 1")
    fornecedor_2 = _criar_fornecedor(8122, "FORNECEDOR ITENS 2")
    produto_1 = _criar_produto(8221, "PRODUTO ITENS 1", unidade)
    produto_2 = _criar_produto(8222, "PRODUTO ITENS 2", unidade)

    compra_1 = Compra.objects.create(
        id_legado=9321,
        nota=1021,
        fornecedor=fornecedor_1,
        data_emissao=date(2026, 3, 1),
        data_lanc=date(2026, 3, 1),
        valor_produtos=Decimal("10.000000"),
        valor_total_documento=Decimal("10.000000"),
        nfe_status="AUTORIZADA",
    )
    item_1 = ItemCompra.objects.create(
        compra=compra_1,
        produto=produto_1,
        unidade_medida=unidade,
        quantidade=Decimal("1.000000"),
        valor_custo=Decimal("10.000000"),
        valor_total_item=Decimal("10.000000"),
    )

    compra_2 = Compra.objects.create(
        id_legado=9322,
        nota=1022,
        fornecedor=fornecedor_2,
        data_emissao=date(2026, 3, 2),
        data_lanc=date(2026, 3, 2),
        valor_produtos=Decimal("20.000000"),
        valor_total_documento=Decimal("20.000000"),
        nfe_status="DENEGADA",
    )
    ItemCompra.objects.create(
        compra=compra_2,
        produto=produto_2,
        unidade_medida=unidade,
        quantidade=Decimal("2.000000"),
        valor_custo=Decimal("10.000000"),
        valor_total_item=Decimal("20.000000"),
    )

    client = APIClient()
    response = client.get(
        "/api/compras/itens",
        {
            "fornecedor_id": fornecedor_1.id_fornecedor,
            "produto_id": produto_1.id_produto,
            "nfe_status": "AUTORIZADA",
        },
        HTTP_HOST="localhost",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["id_item_compra"] == item_1.id_item_compra
