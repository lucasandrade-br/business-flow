from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.cadastros.models import Cliente, Fornecedor, Produto
from apps.integracao.hash_engine import gerar_hash_cliente, gerar_hash_fornecedor, gerar_hash_produto
from apps.integracao.models import StgClientesNovos, StgFornecedoresNovos, StgProdutosNovos


@pytest.mark.django_db
def test_resumo_pendencias_conta_apenas_diferencas_reais() -> None:
    # Produto sincronizado (nao deve contar)
    produto_hash = gerar_hash_produto(
        id_produto=10,
        gtin="00010",
        barras="ABC",
        nome="Produto Igual",
        custo=Decimal("10"),
        venda=Decimal("15"),
        status="ATIVO",
    )
    Produto.objects.create(
        id_produto=10,
        gtin="00010",
        barras="ABC",
        produto="Produto Igual",
        id_und_medida=None,
        custo=Decimal("10"),
        venda=Decimal("15"),
        status="ATIVO",
        markup=Decimal("0.0000"),
        markup_inv=Decimal("0.0000"),
        perda=Decimal("0.0000"),
        fisico=Decimal("0.0000"),
        aliqefc="",
        cod_g3n=0,
        cod_rel=0,
        usuario="",
        hash_md5=produto_hash,
    )
    StgProdutosNovos.objects.create(
        id_produto=10,
        gtin="00010",
        barras="ABC",
        nome="Produto Igual",
        unidade_comecial="UN",
        custo=Decimal("10"),
        valor_venda=Decimal("15"),
        status="ATIVO",
        hash_md5=produto_hash,
    )

    # Produto realmente pendente (sem SOT)
    StgProdutosNovos.objects.create(
        id_produto=11,
        gtin="00011",
        barras="",
        nome="Produto Novo",
        unidade_comecial="UN",
        custo=Decimal("1"),
        valor_venda=Decimal("2"),
        status="ATIVO",
        hash_md5=gerar_hash_produto(11, "00011", "", "Produto Novo", Decimal("1"), Decimal("2"), "ATIVO"),
    )

    # Cliente sincronizado (nao deve contar)
    cliente_hash = gerar_hash_cliente(20, "Cliente Igual", "Razao Igual")
    Cliente.objects.create(
        id_cliente=20,
        nome_cliente="Cliente Igual",
        raz_social="Razao Igual",
        prazo_cob=0,
        hash_md5=cliente_hash,
    )
    StgClientesNovos.objects.create(
        id_cliente=20,
        cliente="Cliente Igual",
        raz_social="Razao Igual",
        hash_md5=cliente_hash,
    )

    # Cliente realmente pendente (sem SOT)
    StgClientesNovos.objects.create(
        id_cliente=21,
        cliente="Cliente Novo",
        raz_social="",
        hash_md5=gerar_hash_cliente(21, "Cliente Novo", ""),
    )

    # Fornecedor sincronizado (nao deve contar)
    fornecedor_hash = gerar_hash_fornecedor(30, "Fornecedor Igual", "Razao For Igual", date(2026, 1, 1))
    Fornecedor.objects.create(
        id_fornecedor=30,
        nome_fornecedor="Fornecedor Igual",
        raz_social="Razao For Igual",
        dt_cadastro=date(2026, 1, 1),
        hash_md5=fornecedor_hash,
    )
    StgFornecedoresNovos.objects.create(
        id_fornecedor=30,
        fantasia="Fornecedor Igual",
        raz_social="Razao For Igual",
        dt_cadastro=date(2026, 1, 1),
        hash_md5=fornecedor_hash,
    )

    # Fornecedor realmente pendente (sem SOT)
    StgFornecedoresNovos.objects.create(
        id_fornecedor=31,
        fantasia="Fornecedor Novo",
        raz_social="",
        dt_cadastro=date(2026, 1, 2),
        hash_md5=gerar_hash_fornecedor(31, "Fornecedor Novo", "", date(2026, 1, 2)),
    )

    client = APIClient()
    response = client.get("/api/validacao/resumo", HTTP_HOST="localhost")

    assert response.status_code == 200
    assert response.data["produtos"] == 1
    assert response.data["clientes"] == 1
    assert response.data["fornecedores"] == 1
