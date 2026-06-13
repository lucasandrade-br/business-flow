from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.cadastros.models import Cliente, Fornecedor, Produto
from apps.integracao.hash_engine import gerar_hash_cliente, gerar_hash_fornecedor, gerar_hash_produto
from apps.integracao.models import StgClientesNovos, StgFornecedoresNovos, StgProdutosNovos
from apps.validacao.services_legacy import (
    contar_clientes_pendentes_validacao,
    contar_fornecedores_pendentes_validacao,
    contar_produtos_pendentes_validacao,
    listar_clientes_pendentes,
    listar_produtos_pendentes,
)


@pytest.mark.django_db
def test_tolerancia_produto_ignora_ordem_palavras_especiais_e_diferenca_decimal_pequena() -> None:
    Produto.objects.create(
        id_produto=101,
        gtin="789",
        barras="ABC123",
        produto="AGUA COM GAS 1.5l",
        id_und_medida=None,
        custo=Decimal("1.5000"),
        venda=Decimal("2.0000"),
        status="ATIVO",
        markup=Decimal("0.0000"),
        markup_inv=Decimal("0.0000"),
        perda=Decimal("0.0000"),
        fisico=Decimal("0.0000"),
        aliqefc="",
        cod_g3n=0,
        cod_rel=0,
        usuario="",
        hash_md5=gerar_hash_produto(101, "789", "ABC123", "AGUA COM GAS 1.5l", Decimal("1.5000"), Decimal("2.0000"), "ATIVO"),
    )

    StgProdutosNovos.objects.create(
        id_produto=101,
        gtin="789",
        barras="ABC123",
        nome="agua 1.5l com gás \ufffd",
        unidade_comecial="UN",
        custo=Decimal("1.5010"),
        valor_venda=Decimal("2.0900"),
        status="ativo",
        hash_md5="hash_antigo_diferente",
    )

    assert contar_produtos_pendentes_validacao() == 0


@pytest.mark.django_db
def test_tolerancia_cliente_ignora_acento_pontuacao_e_especiais() -> None:
    Cliente.objects.create(
        id_cliente=201,
        nome_cliente="José da Silva",
        raz_social="Comércio de Bebidas S.A.",
        prazo_cob=0,
        hash_md5=gerar_hash_cliente(201, "José da Silva", "Comércio de Bebidas S.A."),
    )

    StgClientesNovos.objects.create(
        id_cliente=201,
        cliente="JOSE, DA SILVA \ufffd",
        raz_social="COMERCIO DE BEBIDAS SA!!",
        hash_md5="hash_antigo_diferente",
    )

    assert contar_clientes_pendentes_validacao() == 0


@pytest.mark.django_db
def test_tolerancia_fornecedor_ignora_acento_pontuacao_e_especiais() -> None:
    Fornecedor.objects.create(
        id_fornecedor=301,
        nome_fornecedor="Açúcar União",
        raz_social="Açúcar União LTDA",
        dt_cadastro=date(2026, 1, 1),
        hash_md5=gerar_hash_fornecedor(301, "Açúcar União", "Açúcar União LTDA", date(2026, 1, 1)),
    )

    StgFornecedoresNovos.objects.create(
        id_fornecedor=301,
        fantasia="ACUCAR, UNIAO \ufffd",
        raz_social="ACUCAR UNIAO LTDA!!!",
        dt_cadastro=date(2026, 1, 1),
        hash_md5="hash_antigo_diferente",
    )

    assert contar_fornecedores_pendentes_validacao() == 0


@pytest.mark.django_db
def test_tolerancia_produto_caso_real_nome_semelhante_passa_sem_pendencia() -> None:
    Produto.objects.create(
        id_produto=401,
        gtin="",
        barras="",
        produto="AGUA MINERAL SCHINCARIOL C/GAS 500ML",
        id_und_medida=None,
        custo=Decimal("3.0000"),
        venda=Decimal("5.0000"),
        status="ATIVO",
        markup=Decimal("0.0000"),
        markup_inv=Decimal("0.0000"),
        perda=Decimal("0.0000"),
        fisico=Decimal("0.0000"),
        aliqefc="",
        cod_g3n=0,
        cod_rel=0,
        usuario="",
        hash_md5=gerar_hash_produto(401, "", "", "AGUA MINERAL SCHINCARIOL C/GAS 500ML", Decimal("3.0000"), Decimal("5.0000"), "ATIVO"),
    )

    StgProdutosNovos.objects.create(
        id_produto=401,
        gtin="",
        barras="",
        nome="AGUA MINERAL PET 500ML COM GAS SCHINCARIOL",
        unidade_comecial="UN",
        custo=Decimal("3.0500"),
        valor_venda=Decimal("5.0500"),
        status="ATIVO",
        hash_md5="hash_antigo_diferente",
    )

    assert contar_produtos_pendentes_validacao() == 0


@pytest.mark.django_db
def test_tolerancia_produto_nome_muito_diferente_permanece_pendente() -> None:
    Produto.objects.create(
        id_produto=402,
        gtin="",
        barras="",
        produto="REFRIGERANTE COLA 2L",
        id_und_medida=None,
        custo=Decimal("7.0000"),
        venda=Decimal("9.0000"),
        status="ATIVO",
        markup=Decimal("0.0000"),
        markup_inv=Decimal("0.0000"),
        perda=Decimal("0.0000"),
        fisico=Decimal("0.0000"),
        aliqefc="",
        cod_g3n=0,
        cod_rel=0,
        usuario="",
        hash_md5=gerar_hash_produto(402, "", "", "REFRIGERANTE COLA 2L", Decimal("7.0000"), Decimal("9.0000"), "ATIVO"),
    )

    StgProdutosNovos.objects.create(
        id_produto=402,
        gtin="",
        barras="",
        nome="SABAO EM PO LIMPEZA PROFUNDA 1KG",
        unidade_comecial="UN",
        custo=Decimal("7.0000"),
        valor_venda=Decimal("9.0000"),
        status="ATIVO",
        hash_md5="hash_antigo_diferente",
    )

    assert contar_produtos_pendentes_validacao() == 1


@pytest.mark.django_db
def test_listar_produtos_pendentes_inclui_divergencias_estruturadas() -> None:
    Produto.objects.create(
        id_produto=510,
        gtin="789000",
        barras="BARRAS-01",
        produto="BISCOITO RECHEADO CHOCOLATE 120G",
        id_und_medida=None,
        custo=Decimal("3.0000"),
        venda=Decimal("5.0000"),
        status="ATIVO",
        markup=Decimal("0.0000"),
        markup_inv=Decimal("0.0000"),
        perda=Decimal("0.0000"),
        fisico=Decimal("0.0000"),
        aliqefc="",
        cod_g3n=0,
        cod_rel=0,
        usuario="",
        hash_md5=gerar_hash_produto(
            510,
            "789000",
            "BARRAS-01",
            "BISCOITO RECHEADO CHOCOLATE 120G",
            Decimal("3.0000"),
            Decimal("5.0000"),
            "ATIVO",
        ),
    )

    StgProdutosNovos.objects.create(
        id_produto=510,
        gtin="789111",
        barras="BARRAS-02",
        nome="BISCOITO MORANGO 120G",
        unidade_comecial="UN",
        custo=Decimal("4.2000"),
        valor_venda=Decimal("6.3000"),
        status="INATIVO",
        hash_md5="hash_antigo_diferente",
    )

    itens = listar_produtos_pendentes()
    item = next((registro for registro in itens if registro["id_produto"] == 510), None)

    assert item is not None
    assert item["tipo_pendencia"] == "ATUALIZACAO"
    assert isinstance(item.get("divergencias"), list)
    assert len(item["divergencias"]) >= 1
    assert item["divergencias_resumo"]["total"] == len(item["divergencias"])
    assert len(item["divergencias_resumo"]["campos"]) >= 1


@pytest.mark.django_db
def test_listar_clientes_pendentes_novo_retorna_resumo_vazio() -> None:
    StgClientesNovos.objects.create(
        id_cliente=910,
        cliente="CLIENTE NOVO",
        raz_social="CLIENTE NOVO LTDA",
        hash_md5="hash_novo",
    )

    itens = listar_clientes_pendentes()
    item = next((registro for registro in itens if registro["id_cliente"] == 910), None)

    assert item is not None
    assert item["tipo_pendencia"] == "NOVO"
    assert item["divergencias"] == []
    assert item["divergencias_resumo"]["total"] == 0
