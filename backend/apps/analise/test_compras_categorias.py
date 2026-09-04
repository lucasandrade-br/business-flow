from datetime import date
from decimal import Decimal

import pytest
from django.db.models import Sum
from rest_framework.test import APIClient

from apps.analise.models import (
    MovimentoCompraProdutoMensal,
    StatusMovimentoCompraProdutoMensal,
)
from apps.analise.services import (
    montar_analise_compras_categorias,
    montar_analise_compras_produtos,
    reconstruir_movimento_compra_produto_mensal,
)
from apps.cadastros.models import Fornecedor, PlanoConta, Produto, UnidadeMedida
from apps.compras.models import Compra, ItemCompra


pytestmark = pytest.mark.django_db


def _produto(produto_id, nome, categoria=None, status="ATIVO"):
    produto = Produto.objects.create(
        id_produto=produto_id,
        produto=nome,
        custo=Decimal("1"),
        venda=Decimal("2"),
        status=status,
        markup=0,
        markup_inv=0,
        perda=0,
        fisico=0,
        aliqefc="",
        cod_g3n=0,
        cod_rel=0,
    )
    if categoria:
        produto.categorias.add(categoria)
    return produto


def _item(compra, produto, unidade, quantidade, valor):
    quantidade = Decimal(str(quantidade))
    valor = Decimal(str(valor))
    custo = valor / quantidade if quantidade else Decimal("0")
    return ItemCompra.objects.create(
        compra=compra,
        produto=produto,
        unidade_medida=unidade,
        quantidade=quantidade,
        valor_custo=custo,
        valor_total_item=valor,
    )


@pytest.fixture
def cenario_compras():
    raiz = PlanoConta.objects.create(nome_conta="COMPRAS")
    pai = PlanoConta.objects.create(nome_conta="INSUMOS", conta_pai=raiz)
    folha_un = PlanoConta.objects.create(nome_conta="EMBALAGENS", conta_pai=pai)
    folha_kg = PlanoConta.objects.create(nome_conta="FARINHAS", conta_pai=pai)
    folha_zero = PlanoConta.objects.create(nome_conta="SEM COMPRA", conta_pai=raiz)
    unidade_un = UnidadeMedida.objects.create(sigla="UN", descricao="Unidade")
    unidade_kg = UnidadeMedida.objects.create(sigla="KG", descricao="Quilograma")
    fornecedor_a = Fornecedor.objects.create(id_fornecedor=1, nome_fornecedor="FORNECEDOR A")
    fornecedor_b = Fornecedor.objects.create(id_fornecedor=2, nome_fornecedor="FORNECEDOR B")
    produto_un = _produto(201, "SACO", folha_un)
    produto_kg = _produto(202, "FARINHA", folha_kg)
    produto_zero = _produto(203, "SEM MOVIMENTO", folha_un)
    produto_inativo = _produto(204, "INATIVO", folha_un, status="INATIVO")
    produto_sem_categoria = _produto(205, "IGNORADO")

    compra_jan_a = Compra.objects.create(
        id_legado=1001,
        fornecedor=fornecedor_a,
        data_emissao=date(2026, 1, 10),
        valor_total_documento=999,
    )
    _item(compra_jan_a, produto_un, unidade_un, 2, 20)
    _item(compra_jan_a, produto_un, unidade_un, 3, 45)
    _item(compra_jan_a, produto_kg, unidade_kg, "3.5", 35)
    _item(compra_jan_a, produto_sem_categoria, unidade_un, 1, 80)
    _item(compra_jan_a, produto_un, unidade_un, -1, -10)

    compra_jan_b = Compra.objects.create(
        id_legado=1002,
        fornecedor=fornecedor_b,
        data_emissao=date(2026, 1, 15),
        valor_total_documento=50,
    )
    _item(compra_jan_b, produto_un, unidade_un, 1, 50)
    _item(compra_jan_b, produto_inativo, unidade_un, 1, 200)

    compra_cancelada = Compra.objects.create(
        id_legado=1003,
        fornecedor=fornecedor_a,
        data_emissao=date(2026, 12, 20),
        valor_total_documento=500,
        nfe_status="CANCELADA",
    )
    _item(compra_cancelada, produto_un, unidade_un, 10, 500)

    compra_fev = Compra.objects.create(
        id_legado=1004,
        fornecedor=fornecedor_a,
        data_emissao=date(2026, 2, 10),
        valor_total_documento=100,
    )
    _item(compra_fev, produto_un, unidade_un, 5, 100)

    return {
        "raiz": raiz,
        "pai": pai,
        "folha_un": folha_un,
        "folha_zero": folha_zero,
        "fornecedor_a": fornecedor_a,
        "fornecedor_b": fornecedor_b,
        "produto_un": produto_un,
        "produto_zero": produto_zero,
        "produto_inativo": produto_inativo,
    }


def _linha_categoria(payload, conta):
    return next(linha for linha in payload["linhas"] if linha["id_conta"] == conta.id_conta)


def test_reconstrucao_rollup_filtro_fornecedor_e_exclusoes(cenario_compras, monkeypatch):
    monkeypatch.setattr("apps.analise.services.timezone.localdate", lambda: date(2026, 2, 11))
    assert reconstruir_movimento_compra_produto_mensal(2026, 1) == 5
    reconstruir_movimento_compra_produto_mensal(2026, 2)
    reconstruir_movimento_compra_produto_mensal(2026, 1)

    payload = montar_analise_compras_categorias(
        ano=2026,
        raiz_id=cenario_compras["raiz"].id_conta,
        metrica="valor",
        fornecedor_id=cenario_compras["fornecedor_a"].id_fornecedor,
    )
    raiz = _linha_categoria(payload, cenario_compras["raiz"])
    pai = _linha_categoria(payload, cenario_compras["pai"])
    zero = _linha_categoria(payload, cenario_compras["folha_zero"])

    assert Decimal(raiz["valores"][0]) == Decimal("100")
    assert Decimal(raiz["valores"][1]) == Decimal("100")
    assert Decimal(raiz["total"]) == Decimal("200")
    assert pai["valores"] == raiz["valores"]
    assert Decimal(zero["total"]) == 0
    assert payload["fornecedor"]["id_fornecedor"] == 1
    assert MovimentoCompraProdutoMensal.objects.filter(ano=2026, mes=1).count() == 5
    assert StatusMovimentoCompraProdutoMensal.objects.get(ano=2026, mes=1).status == "PRONTO"
    assert payload["ultima_data_disponivel"] == "2026-02-10"
    assert payload["mes_aberto"] == 2


def test_quantidade_e_custo_medio_ponderado_por_unidade(cenario_compras, monkeypatch):
    monkeypatch.setattr("apps.analise.services.timezone.localdate", lambda: date(2026, 2, 11))
    reconstruir_movimento_compra_produto_mensal(2026, 1)
    reconstruir_movimento_compra_produto_mensal(2026, 2)

    quantidade = montar_analise_compras_categorias(
        ano=2026,
        raiz_id=cenario_compras["raiz"].id_conta,
        metrica="quantidade",
        fornecedor_id=1,
    )
    unidades = {item["sigla"]: item for item in _linha_categoria(quantidade, cenario_compras["raiz"])["unidades"]}
    assert Decimal(unidades["UN"]["valores"][0]) == Decimal("5")
    assert Decimal(unidades["KG"]["valores"][0]) == Decimal("3.5")

    custo = montar_analise_compras_produtos(
        ano=2026,
        raiz_id=cenario_compras["raiz"].id_conta,
        categoria_id=cenario_compras["folha_un"].id_conta,
        metrica="custo_medio",
        fornecedor_id=1,
    )
    assert custo["ultima_data_disponivel"] == "2026-02-10"
    assert custo["mes_aberto"] == 2
    linha = next(item for item in custo["linhas"] if item["id_produto"] == 201)
    unidade = linha["unidades"][0]
    assert Decimal(unidade["valores"][0]) == Decimal("13")
    assert Decimal(unidade["valores"][1]) == Decimal("20")
    assert Decimal(unidade["total"]) == Decimal("16.5")


def test_produtos_status_zeros_busca_e_ordenacao_por_valor(cenario_compras):
    reconstruir_movimento_compra_produto_mensal(2026, 1)
    reconstruir_movimento_compra_produto_mensal(2026, 2)
    payload = montar_analise_compras_produtos(
        ano=2026,
        raiz_id=cenario_compras["raiz"].id_conta,
        categoria_id=cenario_compras["pai"].id_conta,
        metrica="quantidade",
    )
    ids = [linha["id_produto"] for linha in payload["linhas"]]
    assert ids == [201, 202, 203]
    assert payload["linhas"][-1]["unidades"] == []
    assert payload["inativos_ocultos"] == 1

    com_inativos = montar_analise_compras_produtos(
        ano=2026,
        raiz_id=cenario_compras["raiz"].id_conta,
        categoria_id=cenario_compras["pai"].id_conta,
        metrica="custo_medio",
        incluir_inativos=True,
        search="204",
    )
    assert [linha["id_produto"] for linha in com_inativos["linhas"]] == [204]
    assert com_inativos["linhas"][0]["status"] == "INATIVO"


def test_api_metadata_aviso_conflito_e_validacoes(cenario_compras):
    reconstruir_movimento_compra_produto_mensal(2026, 1)
    client = APIClient()
    metadata = client.get("/api/analise/categorias/compras/", HTTP_HOST="localhost")
    assert metadata.status_code == 200
    assert metadata.json()["anos_disponiveis"] == [2026]

    StatusMovimentoCompraProdutoMensal.objects.filter(ano=2026, mes=1).update(status="FALHA")
    response = client.get(
        "/api/analise/categorias/compras/",
        {"ano": 2026, "raiz_id": cenario_compras["raiz"].id_conta, "metrica": "valor"},
        HTTP_HOST="localhost",
    )
    assert response.status_code == 200
    assert response.json()["desatualizado"] is True

    response = client.get(
        "/api/analise/categorias/produtos/compras/",
        {
            "ano": 2026,
            "raiz_id": cenario_compras["raiz"].id_conta,
            "categoria_id": cenario_compras["raiz"].id_conta,
            "metrica": "custo_medio",
            "fornecedor_id": 999999,
        },
        HTTP_HOST="localhost",
    )
    assert response.status_code == 404

    Produto.categorias.through.objects.create(
        produto_id=cenario_compras["produto_un"].id_produto,
        planoconta_id=cenario_compras["folha_zero"].id_conta,
    )
    response = client.get(
        "/api/analise/categorias/compras/",
        {"ano": 2026, "raiz_id": cenario_compras["raiz"].id_conta, "metrica": "valor"},
        HTTP_HOST="localhost",
    )
    assert response.status_code == 409
    assert response.json()["produtos_conflitantes"][0]["id_produto"] == 201


def test_reconstrucao_preserva_snapshot_e_recupera_apos_falha(cenario_compras, monkeypatch):
    reconstruir_movimento_compra_produto_mensal(2026, 1)
    total_anterior = MovimentoCompraProdutoMensal.objects.filter(ano=2026, mes=1).aggregate(
        total=Sum("valor_comprado")
    )["total"]

    compra = Compra.objects.create(
        id_legado=1999,
        fornecedor=cenario_compras["fornecedor_a"],
        data_emissao=date(2026, 1, 25),
        valor_total_documento=300,
    )
    unidade = UnidadeMedida.objects.get(sigla="UN")
    _item(compra, cenario_compras["produto_un"], unidade, 3, 300)

    manager = MovimentoCompraProdutoMensal.objects
    original_bulk_create = manager.bulk_create

    def falhar_bulk_create(*args, **kwargs):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(manager, "bulk_create", falhar_bulk_create)
    with pytest.raises(RuntimeError, match="falha simulada"):
        reconstruir_movimento_compra_produto_mensal(2026, 1)

    total_apos_falha = MovimentoCompraProdutoMensal.objects.filter(ano=2026, mes=1).aggregate(
        total=Sum("valor_comprado")
    )["total"]
    assert total_apos_falha == total_anterior
    assert StatusMovimentoCompraProdutoMensal.objects.get(ano=2026, mes=1).status == "FALHA"

    monkeypatch.setattr(manager, "bulk_create", original_bulk_create)
    reconstruir_movimento_compra_produto_mensal(2026, 1)
    total_recuperado = MovimentoCompraProdutoMensal.objects.filter(ano=2026, mes=1).aggregate(
        total=Sum("valor_comprado")
    )["total"]
    assert total_recuperado == total_anterior + Decimal("300")
    assert StatusMovimentoCompraProdutoMensal.objects.get(ano=2026, mes=1).status == "PRONTO"
