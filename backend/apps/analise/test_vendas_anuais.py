from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.analise.models import (
    MovimentoProdutoDiario, MovimentoProdutoMensal,
    StatusMovimentoProdutoMensal, StatusMovimentoProdutoSemanal,
)
from apps.analise.services_vendas_semanais import inicio_semana
from apps.cadastros.models import PlanoConta, Produto, UnidadeMedida, Usuario
from apps.vendas.models import Venda

from .test_categorias import _produto


pytestmark = pytest.mark.django_db


@pytest.fixture
def cenario(monkeypatch):
    monkeypatch.setattr("apps.analise.services_vendas_anuais.timezone.localdate", lambda: date(2026, 3, 1))
    raiz = PlanoConta.objects.create(nome_conta="RECEITAS")
    folha = PlanoConta.objects.create(nome_conta="PADARIA", conta_pai=raiz)
    unidade = UnidadeMedida.objects.create(sigla="UN", descricao="Unidade")
    produto = _produto(501, "PAO", folha)
    outro = _produto(502, "BOLO", folha)
    usuario = Usuario.objects.create(id_usuario=501, nome="Teste")
    for legado, data in enumerate((date(2024, 1, 1), date(2025, 2, 28), date(2026, 2, 28)), 1):
        Venda.objects.create(id_legado=legado, tipo_documento=Venda.TIPO_NFCE,
                             data_venda=data, usuario=usuario, valor_total_documento=1, status="")
    for ano in (2024, 2025):
        for mes in range(1, 13):
            StatusMovimentoProdutoMensal.objects.create(ano=ano, mes=mes, status="PRONTO",
                                                        ultimo_sucesso_em="2026-03-01T10:00:00Z")
    for mes in (1, 2):
        StatusMovimentoProdutoMensal.objects.create(ano=2026, mes=mes, status="PRONTO",
                                                    ultimo_sucesso_em="2026-03-01T10:00:00Z")
    for ano in (2024, 2025, 2026):
        cursor = inicio_semana(date(ano, 1, 1))
        while cursor <= date(ano, 2, 28):
            StatusMovimentoProdutoSemanal.objects.create(semana_inicio=cursor, status="PRONTO",
                                                         ultimo_sucesso_em="2026-03-01T10:00:00Z")
            cursor += timedelta(days=7)
    for data, produto_ref, valor, quantidade in (
        (date(2024, 2, 28), produto, 100, 2),
        (date(2024, 2, 29), produto, 900, 9),
        (date(2025, 2, 28), produto, 200, 4),
        (date(2026, 2, 28), produto, 300, 6),
        (date(2026, 2, 28), outro, 500, 10),
    ):
        MovimentoProdutoDiario.objects.create(
            data=data, produto=produto_ref, unidade_medida_id_origem=unidade.pk,
            unidade_sigla=unidade.sigla, receita_bruta=valor, quantidade=quantidade,
        )
    for ano, produto_ref, valor, quantidade in (
        (2024, produto, 1000, 11), (2025, produto, 200, 4),
        (2026, produto, 300, 6), (2026, outro, 500, 10),
    ):
        MovimentoProdutoMensal.objects.create(
            ano=ano, mes=2, produto=produto_ref, unidade_medida_id_origem=unidade.pk,
            unidade_sigla=unidade.sigla, receita_bruta=valor, quantidade=quantidade,
        )
    return raiz, folha, produto, outro, unidade


def _get(path, params):
    return APIClient().get(path, params, HTTP_HOST="localhost")


def test_corte_anual_ignora_dia_bissexto_e_concilia_folha_com_produtos(cenario):
    raiz, folha, produto, outro, _ = cenario
    params = {"raiz_id": raiz.id_conta, "ano": 2026, "metrica": "valor", "periodo_equivalente": 1}
    categoria = _get("/api/analise/categorias/vendas/anual/", params)
    produtos = _get("/api/analise/categorias/produtos/vendas/anual/", {**params, "categoria_id": folha.id_conta})
    assert categoria.status_code == produtos.status_code == 200
    cat = categoria.json()
    prod = produtos.json()
    assert [item["ano"] for item in cat["anos"]] == [2024, 2025, 2026]
    assert cat["anos"][0]["fim"] == "2024-02-28"
    folha_linha = next(item for item in cat["linhas"] if item["id_conta"] == folha.id_conta)
    assert [Decimal(v) for v in folha_linha["valores"]] == [100, 200, 800]
    assert Decimal(folha_linha["variacao_percentual"]) == 300
    assert [item["id_produto"] for item in prod["linhas"]] == [outro.id_produto, produto.id_produto]
    assert [sum(Decimal(item["valores"][i]) for item in prod["linhas"]) for i in range(3)] == [100, 200, 800]

    completo = _get("/api/analise/categorias/vendas/anual/", {**params, "periodo_equivalente": 0}).json()
    linha = next(item for item in completo["linhas"] if item["id_conta"] == folha.id_conta)
    assert [Decimal(v) for v in linha["valores"]] == [1000, 200, 800]
    assert completo["ano_parcial"] and not completo["periodo_equivalente"]


def test_quantidades_zero_referencia_inativos_e_classificacao_ambigua(cenario):
    raiz, folha, produto, outro, _ = cenario
    outro.status = "INATIVO"
    outro.save(update_fields=["status"])
    params = {"raiz_id": raiz.id_conta, "categoria_id": folha.id_conta,
              "ano": 2026, "metrica": "quantidade", "periodo_equivalente": 1}
    resposta = _get("/api/analise/categorias/produtos/vendas/anual/", params).json()
    assert resposta["paginacao"]["total_produtos"] == 1
    assert resposta["inativos_ocultos"] == 1
    resposta = _get("/api/analise/categorias/produtos/vendas/anual/", {**params, "incluir_inativos": 1}).json()
    assert [item["id_produto"] for item in resposta["linhas"]] == [outro.id_produto, produto.id_produto]
    assert [Decimal(valor) for valor in resposta["linhas"][1]["unidades"][0]["valores"]] == [2, 4, 6]
    assert Decimal(resposta["linhas"][1]["unidades"][0]["variacao_historica_percentual"]) == 100
    assert Decimal(resposta["linhas"][1]["unidades"][0]["variacao_percentual"]) == 50
    assert resposta["linhas"][0]["unidades"][0]["variacao_historica_percentual"] is None
    assert resposta["linhas"][0]["unidades"][0]["variacao_percentual"] is None
    outra_folha = PlanoConta.objects.create(nome_conta="OUTRA", conta_pai=raiz)
    Produto.categorias.through.objects.create(produto_id=produto.id_produto, planoconta_id=outra_folha.id_conta)
    assert _get("/api/analise/categorias/vendas/anual/", {"raiz_id": raiz.id_conta, "ano": 2026, "metrica": "valor"}).status_code == 409


def test_snapshot_ausente_nao_vira_zero_e_falha_com_snapshot_e_aviso(cenario):
    raiz, _, _, _, _ = cenario
    params = {"raiz_id": raiz.id_conta, "ano": 2026, "metrica": "valor", "periodo_equivalente": 1}
    semana = StatusMovimentoProdutoSemanal.objects.get(semana_inicio=inicio_semana(date(2025, 1, 15)))
    semana.delete()
    assert _get("/api/analise/categorias/vendas/anual/", params).status_code == 503
    semana.pk = None
    semana.status = "FALHA"
    semana.save()
    resposta = _get("/api/analise/categorias/vendas/anual/", params)
    assert resposta.status_code == 200
    assert resposta.json()["desatualizado"] is True


def test_mes_sem_movimento_e_snapshot_mensal_ausente(cenario):
    raiz, _, _, _, _ = cenario
    params = {"raiz_id": raiz.id_conta, "ano": 2026, "metrica": "valor", "periodo_equivalente": 0}
    StatusMovimentoProdutoMensal.objects.filter(ano=2025, mes=1).delete()
    assert _get("/api/analise/categorias/vendas/anual/", params).status_code == 200
    StatusMovimentoProdutoMensal.objects.filter(ano=2025, mes=2).delete()
    assert _get("/api/analise/categorias/vendas/anual/", params).status_code == 503


def test_equivalencia_ignorada_em_ano_historico(cenario):
    raiz, _, _, _, _ = cenario
    params = {"raiz_id": raiz.id_conta, "ano": 2025, "metrica": "valor"}
    ligado = _get("/api/analise/categorias/vendas/anual/", {**params, "periodo_equivalente": 1}).json()
    desligado = _get("/api/analise/categorias/vendas/anual/", {**params, "periodo_equivalente": 0}).json()
    assert ligado["linhas"] == desligado["linhas"]
    assert ligado["periodo_equivalente"] is False


def test_parametros_invalidos_e_ano_sem_historico(cenario):
    raiz, folha, _, _, _ = cenario
    caminho = "/api/analise/categorias/produtos/vendas/anual/"
    assert _get(caminho, {"raiz_id": raiz.id_conta}).status_code == 400
    assert _get(caminho, {"raiz_id": raiz.id_conta, "categoria_id": folha.id_conta, "ano": 2023, "metrica": "valor"}).status_code == 404
    assert _get(caminho, {"raiz_id": raiz.id_conta, "categoria_id": folha.id_conta, "ano": 2026, "metrica": "valor", "page": 0}).status_code == 400


def test_ano_pronto_sem_vendas_e_zero_historico(cenario):
    raiz, folha, _, _, _ = cenario
    Venda.objects.filter(data_venda__year=2025).delete()
    MovimentoProdutoDiario.objects.filter(data__year=2025).delete()
    MovimentoProdutoMensal.objects.filter(ano=2025).delete()
    resposta = _get("/api/analise/categorias/vendas/anual/", {
        "raiz_id": raiz.id_conta, "ano": 2025, "metrica": "valor", "periodo_equivalente": 1,
    })
    assert resposta.status_code == 200
    payload = resposta.json()
    assert payload["periodo_equivalente"] is False
    linha = next(item for item in payload["linhas"] if item["id_conta"] == folha.id_conta)
    assert [Decimal(v) for v in linha["valores"]] == [1000, 0]
    assert Decimal(linha["variacao_percentual"]) == -100
    metadata = _get("/api/analise/categorias/vendas/anual/", {}).json()
    assert 2025 in metadata["anos_disponiveis"]


def test_paginacao_e_unidades_independentes(cenario):
    raiz, folha, produto, outro, _ = cenario
    pacote = UnidadeMedida.objects.create(sigla="PCT", descricao="Pacote")
    MovimentoProdutoDiario.objects.create(data=date(2026, 2, 28), produto=produto,
                                          unidade_medida_id_origem=pacote.pk, unidade_sigla="PCT",
                                          receita_bruta=20, quantidade=3)
    MovimentoProdutoMensal.objects.create(ano=2026, mes=2, produto=produto,
                                           unidade_medida_id_origem=pacote.pk, unidade_sigla="PCT",
                                           receita_bruta=20, quantidade=3)
    for codigo in range(503, 602):
        _produto(codigo, f"ITEM {codigo}", folha)
    params = {"raiz_id": raiz.id_conta, "categoria_id": folha.id_conta,
              "ano": 2026, "metrica": "quantidade", "incluir_inativos": 1}
    primeira = _get("/api/analise/categorias/produtos/vendas/anual/", params).json()
    segunda = _get("/api/analise/categorias/produtos/vendas/anual/", {**params, "page": 2}).json()
    assert primeira["paginacao"]["total_produtos"] == 101
    assert len(primeira["linhas"]) == 100
    assert len(segunda["linhas"]) == 1
    assert [item["id_produto"] for item in primeira["linhas"][:2]] == [outro.id_produto, produto.id_produto]
    unidades = primeira["linhas"][1]["unidades"]
    assert {item["sigla"] for item in unidades} == {"UN", "PCT"}
    assert next(item for item in unidades if item["sigla"] == "PCT")["variacao_percentual"] is None
    resposta_folha = _get("/api/analise/categorias/vendas/anual/", {
        "raiz_id": raiz.id_conta, "ano": 2026, "metrica": "quantidade",
    }).json()
    folha_linha = next(item for item in resposta_folha["linhas"] if item["id_conta"] == folha.id_conta)
    for unidade in folha_linha["unidades"]:
        for indice in range(3):
            soma = sum(Decimal(produto_linha["valores"][indice]) for produto_linha in (
                unidade_linha for linha in primeira["linhas"] + segunda["linhas"]
                for unidade_linha in linha["unidades"] if unidade_linha["sigla"] == unidade["sigla"]
            ))
            assert soma == Decimal(unidade["valores"][indice])


def test_taxas_anuais_com_quatro_anos_e_cortes_equivalentes(cenario):
    raiz, folha, produto, _, unidade = cenario
    usuario = Usuario.objects.get(id_usuario=501)
    Venda.objects.create(id_legado=99, tipo_documento=Venda.TIPO_NFCE,
                         data_venda=date(2023, 2, 28), usuario=usuario,
                         valor_total_documento=50, status="")
    for mes in range(1, 13):
        StatusMovimentoProdutoMensal.objects.create(ano=2023, mes=mes, status="PRONTO",
                                                    ultimo_sucesso_em="2026-03-01T10:00:00Z")
    cursor = inicio_semana(date(2023, 1, 1))
    while cursor <= date(2023, 2, 28):
        StatusMovimentoProdutoSemanal.objects.create(semana_inicio=cursor, status="PRONTO",
                                                     ultimo_sucesso_em="2026-03-01T10:00:00Z")
        cursor += timedelta(days=7)
    MovimentoProdutoDiario.objects.create(data=date(2023, 2, 28), produto=produto,
                                          unidade_medida_id_origem=unidade.pk, unidade_sigla="UN",
                                          receita_bruta=50, quantidade=1)
    MovimentoProdutoMensal.objects.create(ano=2023, mes=2, produto=produto,
                                           unidade_medida_id_origem=unidade.pk, unidade_sigla="UN",
                                           receita_bruta=50, quantidade=1)
    params = {"raiz_id": raiz.id_conta, "ano": 2026, "metrica": "valor"}
    ligado = _get("/api/analise/categorias/vendas/anual/", {**params, "periodo_equivalente": 1}).json()
    linha = next(item for item in ligado["linhas"] if item["id_conta"] == folha.id_conta)
    assert [Decimal(v) for v in linha["valores"]] == [50, 100, 200, 800]
    assert Decimal(linha["variacao_historica_percentual"]) == 100
    assert Decimal(linha["variacao_percentual"]) == 300
    produto_payload = _get("/api/analise/categorias/produtos/vendas/anual/", {
        **params, "categoria_id": folha.id_conta, "periodo_equivalente": 1,
    }).json()
    produto_linha = next(item for item in produto_payload["linhas"] if item["id_produto"] == produto.id_produto)
    assert Decimal(produto_linha["variacao_historica_percentual"]) == 100
    assert Decimal(produto_linha["variacao_percentual"]) == 50
    desligado = _get("/api/analise/categorias/vendas/anual/", {**params, "periodo_equivalente": 0}).json()
    linha_completa = next(item for item in desligado["linhas"] if item["id_conta"] == folha.id_conta)
    assert Decimal(linha_completa["variacao_historica_percentual"]) == 910
    assert Decimal(linha_completa["variacao_percentual"]) == 300


def test_taxa_historica_com_tres_dois_um_ano_e_base_zero(cenario):
    raiz, folha, _, _, _ = cenario
    params = {"raiz_id": raiz.id_conta, "metrica": "valor", "periodo_equivalente": 1}
    tres = _get("/api/analise/categorias/vendas/anual/", {**params, "ano": 2026}).json()
    linha_tres = next(item for item in tres["linhas"] if item["id_conta"] == folha.id_conta)
    assert Decimal(linha_tres["variacao_historica_percentual"]) == 100
    dois = _get("/api/analise/categorias/vendas/anual/", {**params, "ano": 2025}).json()
    linha_dois = next(item for item in dois["linhas"] if item["id_conta"] == folha.id_conta)
    assert linha_dois["variacao_historica_percentual"] is None
    assert Decimal(linha_dois["variacao_percentual"]) == -80
    um = _get("/api/analise/categorias/vendas/anual/", {**params, "ano": 2024}).json()
    linha_um = next(item for item in um["linhas"] if item["id_conta"] == folha.id_conta)
    assert linha_um["variacao_historica_percentual"] is None
    assert linha_um["variacao_percentual"] is None
    MovimentoProdutoDiario.objects.filter(data__year=2024).delete()
    MovimentoProdutoMensal.objects.filter(ano=2024).delete()
    base_zero = _get("/api/analise/categorias/vendas/anual/", {**params, "ano": 2026}).json()
    linha_zero = next(item for item in base_zero["linhas"] if item["id_conta"] == folha.id_conta)
    assert linha_zero["variacao_historica_percentual"] is None
    assert Decimal(linha_zero["variacao_percentual"]) == 300
