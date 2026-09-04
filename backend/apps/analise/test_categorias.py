from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.analise.models import MovimentoProdutoMensal, StatusMovimentoProdutoMensal
from apps.analise.services import (
    montar_analise_vendas_categorias,
    montar_analise_vendas_produtos,
    reconstruir_movimento_produto_mensal,
)
from apps.cadastros.models import PlanoConta, Produto, UnidadeMedida, Usuario
from apps.vendas.models import ItemVenda, Venda


pytestmark = pytest.mark.django_db


def _produto(produto_id, nome, categoria=None):
    produto = Produto.objects.create(
        id_produto=produto_id,
        produto=nome,
        custo=Decimal("1"),
        venda=Decimal("2"),
        status="ATIVO",
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


@pytest.fixture
def cenario():
    raiz = PlanoConta.objects.create(nome_conta="RECEITAS")
    pai = PlanoConta.objects.create(nome_conta="ALIMENTOS", conta_pai=raiz)
    folha_un = PlanoConta.objects.create(nome_conta="PADARIA", conta_pai=pai)
    folha_kg = PlanoConta.objects.create(nome_conta="CONFEITARIA", conta_pai=pai)
    folha_zero = PlanoConta.objects.create(nome_conta="SEM MOVIMENTO", conta_pai=raiz)
    unidade_un = UnidadeMedida.objects.create(sigla="UN", descricao="Unidade")
    unidade_kg = UnidadeMedida.objects.create(sigla="KG", descricao="Quilograma")
    usuario = Usuario.objects.create(id_usuario=1, nome="Operador")

    produto_un = _produto(101, "PAO", folha_un)
    produto_kg = _produto(102, "BOLO", folha_kg)
    produto_sem_categoria = _produto(103, "OUTRO")

    venda_jan = Venda.objects.create(
        id_legado=1,
        tipo_documento=Venda.TIPO_NFCE,
        data_venda=date(2026, 1, 10),
        usuario=usuario,
        valor_total_documento=999,
    )
    ItemVenda.objects.create(venda=venda_jan, produto=produto_un, unidade_medida=unidade_un, quantidade=2, valor_unitario=10, valor_total_item=20)
    ItemVenda.objects.create(venda=venda_jan, produto=produto_kg, unidade_medida=unidade_kg, quantidade=Decimal("3.5"), valor_unitario=10, valor_total_item=35)
    ItemVenda.objects.create(venda=venda_jan, produto=produto_sem_categoria, unidade_medida=unidade_un, quantidade=5, valor_unitario=10, valor_total_item=50)
    ItemVenda.objects.create(venda=venda_jan, produto=produto_un, unidade_medida=unidade_un, quantidade=-1, valor_unitario=10, valor_total_item=-10)
    ItemVenda.objects.create(venda=venda_jan, produto=produto_un, unidade_medida=unidade_un, quantidade=4, valor_unitario=10, valor_total_item=40, cancelado=True)

    venda_cancelada = Venda.objects.create(
        id_legado=2,
        tipo_documento=Venda.TIPO_NFCE,
        data_venda=date(2026, 12, 20),
        status="C",
        usuario=usuario,
        valor_total_documento=70,
    )
    ItemVenda.objects.create(venda=venda_cancelada, produto=produto_un, unidade_medida=unidade_un, quantidade=7, valor_unitario=10, valor_total_item=70)

    venda_fev = Venda.objects.create(
        id_legado=3,
        tipo_documento=Venda.TIPO_NFCE,
        data_venda=date(2026, 2, 10),
        usuario=usuario,
        valor_total_documento=10,
    )
    ItemVenda.objects.create(venda=venda_fev, produto=produto_un, unidade_medida=unidade_un, quantidade=1, valor_unitario=10, valor_total_item=10)

    return {
        "raiz": raiz,
        "pai": pai,
        "folha_un": folha_un,
        "folha_kg": folha_kg,
        "folha_zero": folha_zero,
        "produto_un": produto_un,
    }


def _linha(payload, conta):
    return next(item for item in payload["linhas"] if item["id_conta"] == conta.id_conta)


def test_reconstrucao_e_rollup_financeiro(cenario, monkeypatch):
    monkeypatch.setattr("apps.analise.services.timezone.localdate", lambda: date(2026, 2, 11))
    assert reconstruir_movimento_produto_mensal(2026, 1) == 3
    reconstruir_movimento_produto_mensal(2026, 2)
    # A reconstrução deve ser idempotente.
    reconstruir_movimento_produto_mensal(2026, 1)

    payload = montar_analise_vendas_categorias(ano=2026, raiz_id=cenario["raiz"].id_conta, metrica="valor")
    raiz = _linha(payload, cenario["raiz"])
    pai = _linha(payload, cenario["pai"])
    zero = _linha(payload, cenario["folha_zero"])

    assert Decimal(raiz["valores"][0]) == Decimal("55")
    assert Decimal(raiz["valores"][1]) == Decimal("10")
    assert Decimal(raiz["total"]) == Decimal("65")
    assert pai["valores"] == raiz["valores"]
    assert Decimal(zero["total"]) == 0
    assert len(payload["linhas"]) == 5
    assert MovimentoProdutoMensal.objects.filter(ano=2026, mes=1).count() == 3
    assert StatusMovimentoProdutoMensal.objects.get(ano=2026, mes=1).status == "PRONTO"
    assert payload["ultima_data_disponivel"] == "2026-02-10"
    assert payload["mes_aberto"] == 2


def test_quantidades_permanecem_separadas_por_unidade(cenario):
    reconstruir_movimento_produto_mensal(2026, 1)
    reconstruir_movimento_produto_mensal(2026, 2)
    payload = montar_analise_vendas_categorias(ano=2026, raiz_id=cenario["raiz"].id_conta, metrica="quantidade")
    unidades = {item["sigla"]: item for item in _linha(payload, cenario["raiz"])["unidades"]}

    assert Decimal(unidades["UN"]["valores"][0]) == Decimal("2")
    assert Decimal(unidades["UN"]["valores"][1]) == Decimal("1")
    assert Decimal(unidades["KG"]["valores"][0]) == Decimal("3.5")


def test_api_metadata_aviso_e_conflito(cenario):
    reconstruir_movimento_produto_mensal(2026, 1)
    client = APIClient()
    metadata = client.get("/api/analise/categorias/vendas/", HTTP_HOST="localhost")
    assert metadata.status_code == 200
    assert metadata.json()["anos_disponiveis"] == [2026]

    StatusMovimentoProdutoMensal.objects.filter(ano=2026, mes=1).update(status="FALHA")
    response = client.get(
        f"/api/analise/categorias/vendas/?ano=2026&raiz_id={cenario['raiz'].id_conta}&metrica=valor",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 200
    assert response.json()["desatualizado"] is True

    # Simula um vinculo legado anterior às validações atuais, sem emitir o sinal M2M.
    Produto.categorias.through.objects.create(
        produto_id=cenario["produto_un"].id_produto,
        planoconta_id=cenario["folha_kg"].id_conta,
    )
    response = client.get(
        f"/api/analise/categorias/vendas/?ano=2026&raiz_id={cenario['raiz'].id_conta}&metrica=valor",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 409
    assert response.json()["produtos_conflitantes"][0]["id_produto"] == cenario["produto_un"].id_produto


def test_analise_produtos_filtra_status_inclui_zeros_e_ordena_por_receita(cenario):
    reconstruir_movimento_produto_mensal(2026, 1)
    reconstruir_movimento_produto_mensal(2026, 2)
    produto_zero = _produto(104, "SEM VENDA", cenario["folha_un"])
    produto_inativo = _produto(105, "VENDA INATIVA", cenario["folha_un"])
    produto_inativo.status = "INATIVO"
    produto_inativo.save(update_fields=["status"])
    MovimentoProdutoMensal.objects.create(
        ano=2026,
        mes=1,
        produto=produto_inativo,
        unidade_medida_id_origem=1,
        unidade_sigla="UN",
        receita_bruta=Decimal("100"),
        quantidade=Decimal("10"),
    )
    MovimentoProdutoMensal.objects.create(
        ano=2026,
        mes=1,
        produto=produto_inativo,
        unidade_medida_id_origem=2,
        unidade_sigla="KG",
        receita_bruta=Decimal("5"),
        quantidade=Decimal("1.5"),
    )

    payload = montar_analise_vendas_produtos(
        ano=2026,
        raiz_id=cenario["raiz"].id_conta,
        categoria_id=cenario["pai"].id_conta,
        metrica="valor",
    )
    ids = [linha["id_produto"] for linha in payload["linhas"]]

    assert ids == [102, 101, produto_zero.id_produto]
    assert payload["linhas"][-1]["valores"] == ["0"] * 12
    assert payload["inativos_ocultos"] == 1
    assert payload["paginacao"]["total_produtos"] == 3

    com_inativos = montar_analise_vendas_produtos(
        ano=2026,
        raiz_id=cenario["raiz"].id_conta,
        categoria_id=cenario["pai"].id_conta,
        metrica="quantidade",
        incluir_inativos=True,
    )
    assert com_inativos["linhas"][0]["id_produto"] == produto_inativo.id_produto
    assert com_inativos["linhas"][0]["status"] == "INATIVO"
    unidades = {item["sigla"]: item for item in com_inativos["linhas"][0]["unidades"]}
    assert Decimal(unidades["UN"]["valores"][0]) == Decimal("10")
    assert Decimal(unidades["KG"]["valores"][0]) == Decimal("1.5")


def test_analise_produtos_recorta_subarvore_e_busca(cenario, monkeypatch):
    monkeypatch.setattr("apps.analise.services.timezone.localdate", lambda: date(2026, 2, 11))
    reconstruir_movimento_produto_mensal(2026, 1)

    folha = montar_analise_vendas_produtos(
        ano=2026,
        raiz_id=cenario["raiz"].id_conta,
        categoria_id=cenario["folha_un"].id_conta,
        metrica="valor",
    )
    assert [linha["id_produto"] for linha in folha["linhas"]] == [101]
    assert folha["ultima_data_disponivel"] == "2026-02-10"
    assert folha["mes_aberto"] == 2

    busca_nome = montar_analise_vendas_produtos(
        ano=2026,
        raiz_id=cenario["raiz"].id_conta,
        categoria_id=cenario["raiz"].id_conta,
        metrica="valor",
        search="bolo",
    )
    assert [linha["id_produto"] for linha in busca_nome["linhas"]] == [102]

    busca_codigo = montar_analise_vendas_produtos(
        ano=2026,
        raiz_id=cenario["raiz"].id_conta,
        categoria_id=cenario["raiz"].id_conta,
        metrica="valor",
        search="101",
    )
    assert [linha["id_produto"] for linha in busca_codigo["linhas"]] == [101]

    # Um vinculo legado duplicado dentro da familia nao pode duplicar a linha nem a receita.
    Produto.categorias.through.objects.create(
        produto_id=cenario["produto_un"].id_produto,
        planoconta_id=cenario["folha_kg"].id_conta,
    )
    legado = montar_analise_vendas_produtos(
        ano=2026,
        raiz_id=cenario["raiz"].id_conta,
        categoria_id=cenario["raiz"].id_conta,
        metrica="valor",
        search="101",
    )
    assert len(legado["linhas"]) == 1
    assert Decimal(legado["linhas"][0]["total"]) == Decimal("20")


def test_api_produtos_pagina_e_valida_categoria_da_familia(cenario):
    reconstruir_movimento_produto_mensal(2026, 1)
    outros = [
        Produto(
            id_produto=1000 + indice,
            produto=f"PRODUTO {indice:03d}",
            custo=1,
            venda=2,
            status="ATIVO",
            markup=0,
            markup_inv=0,
            perda=0,
            fisico=0,
            aliqefc="",
            cod_g3n=0,
            cod_rel=0,
        )
        for indice in range(101)
    ]
    Produto.objects.bulk_create(outros)
    Produto.categorias.through.objects.bulk_create([
        Produto.categorias.through(produto_id=produto.id_produto, planoconta_id=cenario["folha_un"].id_conta)
        for produto in outros
    ])

    client = APIClient()
    response = client.get(
        "/api/analise/categorias/produtos/vendas/",
        {
            "ano": 2026,
            "raiz_id": cenario["raiz"].id_conta,
            "categoria_id": cenario["folha_un"].id_conta,
            "metrica": "valor",
            "page": 2,
        },
        HTTP_HOST="localhost",
    )
    assert response.status_code == 200
    assert response.json()["paginacao"] == {
        "pagina": 2,
        "por_pagina": 100,
        "total_produtos": 102,
        "total_paginas": 2,
    }
    assert len(response.json()["linhas"]) == 2

    outra_raiz = PlanoConta.objects.create(nome_conta="OUTRA FAMILIA")
    response = client.get(
        "/api/analise/categorias/produtos/vendas/",
        {
            "ano": 2026,
            "raiz_id": outra_raiz.id_conta,
            "categoria_id": cenario["folha_un"].id_conta,
            "metrica": "valor",
        },
        HTTP_HOST="localhost",
    )
    assert response.status_code == 400
