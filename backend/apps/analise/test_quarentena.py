from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from apps.analise.models import (
    CategoriaVendaQuarentena, MovimentoProdutoDiario, MovimentoProdutoMensal,
    MovimentoProdutoSemanal, StatusMovimentoProdutoMensal, StatusMovimentoProdutoSemanal,
)
from apps.cadastros.models import PlanoConta, UnidadeMedida, Usuario
from apps.vendas.models import Venda

from .test_categorias import _produto


pytestmark = pytest.mark.django_db
BASE = "/api/analise/categorias/vendas/quarentena/"


def api():
    return APIClient(HTTP_HOST="localhost")


@pytest.fixture
def familias():
    primeira = PlanoConta.objects.create(nome_conta="PRIMEIRA")
    segunda = PlanoConta.objects.create(nome_conta="SEGUNDA")
    folha_a = PlanoConta.objects.create(nome_conta="A", conta_pai=primeira)
    folha_b = PlanoConta.objects.create(nome_conta="B", conta_pai=segunda)
    return primeira, segunda, folha_a, folha_b


def test_marcacao_idempotente_so_para_folhas_e_remocao(familias):
    raiz, _, folha, outra = familias
    client = api()
    assert client.post(BASE, {"categoria_id": raiz.pk}).status_code == 400
    assert client.post(BASE, {"categoria_id": 99999}).status_code == 404
    assert client.post(BASE, {"categoria_id": "x"}).status_code == 400
    assert client.post(BASE, {"categoria_id": folha.pk}).status_code == 201
    assert client.post(BASE, {"categoria_id": folha.pk}).status_code == 200
    assert CategoriaVendaQuarentena.objects.count() == 1
    assert [item["id_conta"] for item in client.get(BASE).json()["categorias"]] == [folha.pk]
    assert client.delete(f"{BASE}{folha.pk}/").status_code == 204
    assert client.delete(f"{BASE}{folha.pk}/").status_code == 204
    assert client.post(BASE, {"categoria_id": outra.pk}).status_code == 201
    outra.delete()
    assert CategoriaVendaQuarentena.objects.count() == 0


def test_estrutura_atual_reagrupa_e_mantem_categoria_que_ganhou_filhos(familias):
    primeira, segunda, folha, outra = familias
    client = api()
    client.post(BASE, {"categoria_id": folha.pk})
    client.post(BASE, {"categoria_id": outra.pk})
    folha.conta_pai = segunda
    folha.save(update_fields=["conta_pai"])
    itens = client.get(BASE).json()["categorias"]
    assert {item["raiz_id"] for item in itens} == {segunda.pk}
    PlanoConta.objects.create(nome_conta="FILHA NOVA", conta_pai=folha)
    item = next(item for item in client.get(BASE).json()["categorias"] if item["id_conta"] == folha.pk)
    assert not item["folha_valida"]
    assert client.post(BASE, {"categoria_id": folha.pk}).status_code == 400
    assert client.delete(f"{BASE}{folha.pk}/").status_code == 204


@pytest.fixture
def agregados(familias):
    primeira, segunda, folha_a, folha_b = familias
    unidade = UnidadeMedida.objects.create(sigla="UN", descricao="Unidade")
    usuario = Usuario.objects.create(id_usuario=801, nome="Teste")
    for indice, (folha, valor) in enumerate(((folha_a, 10), (folha_b, 30)), 1):
        produto = _produto(800 + indice, f"PRODUTO {indice}", folha)
        for ano, data in ((2025, date(2025, 12, 28)), (2026, date(2026, 1, 4))):
            MovimentoProdutoMensal.objects.create(
                ano=ano, mes=data.month, produto=produto, unidade_medida_id_origem=unidade.pk,
                unidade_sigla="UN", receita_bruta=valor * (ano - 2024), quantidade=indice,
            )
            MovimentoProdutoSemanal.objects.create(
                semana_inicio=data, produto=produto, unidade_medida_id_origem=unidade.pk,
                unidade_sigla="UN", receita_bruta=valor * (ano - 2024), quantidade=indice,
            )
            MovimentoProdutoDiario.objects.create(
                data=data, produto=produto, unidade_medida_id_origem=unidade.pk,
                unidade_sigla="UN", receita_bruta=valor * (ano - 2024), quantidade=indice,
            )
    for ano in (2025, 2026):
        Venda.objects.create(id_legado=ano, tipo_documento=Venda.TIPO_NFCE,
                             data_venda=date(ano, 12, 28) if ano == 2025 else date(ano, 1, 4),
                             usuario=usuario, valor_total_documento=1, status="")
    for mes in range(1, 13):
        StatusMovimentoProdutoMensal.objects.create(
            ano=2025, mes=mes, status="PRONTO", ultimo_sucesso_em="2026-01-05T10:00:00Z",
        )
    StatusMovimentoProdutoMensal.objects.create(
        ano=2026, mes=1, status="PRONTO", ultimo_sucesso_em="2026-01-05T10:00:00Z",
    )
    cursor = date(2024, 12, 29)
    while cursor <= date(2026, 1, 4):
        StatusMovimentoProdutoSemanal.objects.create(
            semana_inicio=cursor, status="PRONTO", ultimo_sucesso_em="2026-01-05T10:00:00Z",
        )
        cursor += timedelta(days=7)
    return familias


@pytest.mark.parametrize("visao,periodo", [
    ("semanal", {"semana_inicio": "2026-01-04"}),
    ("mensal", {"ano": 2026}),
    ("anual", {"ano": 2026}),
])
@pytest.mark.parametrize("metrica", ["valor", "quantidade"])
@pytest.mark.parametrize("equivalente", [0, 1])
def test_matriz_concilia_com_analise_original_em_todas_as_visoes(agregados, visao, periodo, metrica, equivalente):
    primeira, segunda, folha_a, folha_b = agregados
    client = api()
    for folha in (folha_a, folha_b):
        assert client.post(BASE, {"categoria_id": folha.pk}).status_code == 201
    params = {"visao": visao, "metrica": metrica, "periodo_equivalente": equivalente, **periodo}
    resultado = client.get(f"{BASE}matriz/", params).json()
    assert resultado["total_categorias"] == 2
    assert len(resultado["grupos"]) == 2
    for grupo in resultado["grupos"]:
        assert grupo["erro"] is None
        assert len(grupo["dados"]["linhas"]) == 1
        rota = "/api/analise/categorias/vendas/" + (f"{visao}/" if visao != "mensal" else "")
        original = client.get(rota, {"raiz_id": grupo["familia"]["id_conta"], **params}).json()
        folha_id = grupo["categorias"][0]["id_conta"]
        linha_original = next(item for item in original["linhas"] if item["id_conta"] == folha_id)
        assert grupo["dados"]["linhas"][0] == linha_original
    filtrado = client.get(f"{BASE}matriz/", {**params, "raiz_id": primeira.pk}).json()
    assert [grupo["familia"]["id_conta"] for grupo in filtrado["grupos"]] == [primeira.pk]


def test_erro_de_uma_familia_nao_esconde_a_outra(agregados):
    primeira, segunda, folha_a, folha_b = agregados
    client = api()
    for folha in (folha_a, folha_b):
        client.post(BASE, {"categoria_id": folha.pk})
    conflito = PlanoConta.objects.create(nome_conta="OUTRA", conta_pai=segunda)
    produto = folha_b.produtos_vinculados.first()
    produto.categorias.through.objects.create(produto_id=produto.pk, planoconta_id=conflito.pk)
    resposta = client.get(f"{BASE}matriz/", {
        "visao": "semanal", "semana_inicio": "2026-01-04", "metrica": "valor",
    })
    assert resposta.status_code == 200
    grupos = {item["familia"]["id_conta"]: item for item in resposta.json()["grupos"]}
    assert grupos[primeira.pk]["dados"]["linhas"][0]["id_conta"] == folha_a.pk
    assert grupos[segunda.pk]["dados"] is None
    assert grupos[segunda.pk]["erro"]["status"] == 409


def test_periodo_sem_snapshot_nao_vira_zero_e_parametros_invalidos(agregados):
    primeira, _, folha, _ = agregados
    client = api()
    client.post(BASE, {"categoria_id": folha.pk})
    StatusMovimentoProdutoSemanal.objects.filter(semana_inicio=date(2026, 1, 4)).delete()
    payload = client.get(f"{BASE}matriz/", {
        "visao": "semanal", "semana_inicio": "2026-01-04", "metrica": "valor",
    }).json()
    assert payload["grupos"][0]["dados"] is None
    assert payload["grupos"][0]["erro"]["status"] == 404
    assert client.get(f"{BASE}matriz/", {
        "visao": "semanal", "semana_inicio": "2026-01-05", "metrica": "valor",
    }).status_code == 400
    assert client.get(f"{BASE}matriz/", {
        "visao": "anual", "ano": 2026, "metrica": "valor", "raiz_id": 99999,
    }).status_code == 404
