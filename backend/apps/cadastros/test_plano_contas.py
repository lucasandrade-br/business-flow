import pytest
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.cadastros.models import PlanoConta, UnidadeMedida


@pytest.fixture
def arvore(db):
    raiz = PlanoConta.objects.create(nome_conta="RAIZ")
    filhas = [PlanoConta.objects.create(nome_conta=f"FILHA {i}", conta_pai=raiz) for i in range(1, 13)]
    neta = PlanoConta.objects.create(nome_conta="NETA", conta_pai=filhas[0])
    outra_raiz = PlanoConta.objects.create(nome_conta="OUTRA RAIZ")
    return {"raiz": raiz, "filhas": filhas, "neta": neta, "outra_raiz": outra_raiz}


@pytest.fixture
def client():
    return APIClient()


def _get(client, url):
    return client.get(url, HTTP_HOST="localhost")


def test_codigo_ordenacao_zero_padded(arvore):
    assert arvore["raiz"].codigo_ordenacao == "000001."
    assert arvore["filhas"][9].codigo_hierarquico == "1.10."
    assert arvore["filhas"][9].codigo_ordenacao == "000001.000010."


def test_ordenacao_numerica_e_nao_lexicografica(arvore):
    codigos = list(
        PlanoConta.objects.filter(conta_pai=arvore["raiz"]).order_by("codigo_ordenacao").values_list("codigo_hierarquico", flat=True)
    )
    assert codigos[:4] == ["1.1.", "1.2.", "1.3.", "1.4."]
    assert codigos[-1] == "1.12."


def test_opcoes_filtra_subarvore_por_raiz(client, arvore):
    response = _get(client, f"/api/cadastros/plano-contas/opcoes?raiz_id={arvore['raiz'].id_conta}&limit=100")
    assert response.status_code == 200

    ids = {item["id_conta"] for item in response.json()["results"]}
    assert arvore["raiz"].id_conta not in ids
    assert arvore["outra_raiz"].id_conta not in ids
    assert arvore["neta"].id_conta in ids


def test_opcoes_somente_folhas_exclui_intermediarias(client, arvore):
    response = _get(
        client,
        f"/api/cadastros/plano-contas/opcoes?raiz_id={arvore['raiz'].id_conta}&somente_folhas=1&limit=100",
    )
    ids = {item["id_conta"] for item in response.json()["results"]}

    assert arvore["filhas"][0].id_conta not in ids
    assert arvore["neta"].id_conta in ids


def test_opcoes_por_ids_ignora_somente_folhas(client, arvore):
    intermediaria = arvore["filhas"][0]
    response = _get(client, f"/api/cadastros/plano-contas/opcoes?ids={intermediaria.id_conta}&somente_folhas=1")
    results = response.json()["results"]

    assert len(results) == 1
    assert results[0]["id_conta"] == intermediaria.id_conta
    assert results[0]["label"] == f"{intermediaria.codigo_hierarquico} {intermediaria.nome_conta}"


def test_raizes_retorna_apenas_raizes(client, arvore):
    response = _get(client, "/api/cadastros/plano-contas/raizes")
    ids = {item["id_conta"] for item in response.json()}

    assert ids == {arvore["raiz"].id_conta, arvore["outra_raiz"].id_conta}


def _payload_produto(categoria_id):
    return {
        "id_produto": 999001,
        "produto": "PRODUTO TESTE",
        "status": "ATIVO",
        "custo": "1.000000",
        "venda": "2.000000",
        "id_und_medida": UnidadeMedida.objects.create(sigla="UN", descricao="Unidade").id_und_medida,
        "categorias": [categoria_id],
    }


def test_produto_rejeita_categoria_intermediaria(client, arvore):
    response = client.post(
        "/api/cadastros/produtos",
        _payload_produto(arvore["filhas"][0].id_conta),
        format="json",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 400
    assert "folha" in str(response.json()).lower()


def test_produto_aceita_categoria_folha(client, arvore):
    response = client.post(
        "/api/cadastros/produtos",
        _payload_produto(arvore["neta"].id_conta),
        format="json",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 201


def test_produto_rejeita_duas_folhas_da_mesma_familia(client, arvore):
    payload = _payload_produto(arvore["neta"].id_conta)
    payload["categorias"] = [arvore["neta"].id_conta, arvore["filhas"][1].id_conta]
    response = client.post(
        "/api/cadastros/produtos",
        payload,
        format="json",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 400
    assert "familia" in str(response.json()).lower()


def test_produto_aceita_uma_folha_em_familias_diferentes(client, arvore):
    folha_outra = PlanoConta.objects.create(nome_conta="FOLHA OUTRA", conta_pai=arvore["outra_raiz"])
    payload = _payload_produto(arvore["neta"].id_conta)
    payload["categorias"] = [arvore["neta"].id_conta, folha_outra.id_conta]
    response = client.post(
        "/api/cadastros/produtos",
        payload,
        format="json",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 201


def test_relacao_m2m_direta_rejeita_ambiguidade(arvore, produto_em_folha):
    with pytest.raises(ValidationError):
        produto_em_folha.categorias.add(arvore["filhas"][1])


@pytest.fixture
def produto_em_folha(arvore):
    from apps.cadastros.models import Produto

    produto = Produto.objects.create(
        id_produto=999002,
        produto="AGUA EM LATA",
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
    produto.categorias.set([arvore["neta"]])
    return produto


def _ids_filtrados(client, categoria_id):
    response = _get(client, f"/api/cadastros/produtos?categoria_id={categoria_id}")
    assert response.status_code == 200
    return {item["id_produto"] for item in response.json()["results"]}


def test_filtro_inclui_produtos_das_categorias_filhas(client, arvore, produto_em_folha):
    assert produto_em_folha.id_produto in _ids_filtrados(client, arvore["neta"].id_conta)
    assert produto_em_folha.id_produto in _ids_filtrados(client, arvore["filhas"][0].id_conta)
    assert produto_em_folha.id_produto in _ids_filtrados(client, arvore["raiz"].id_conta)


def test_filtro_nao_vaza_para_outra_raiz(client, arvore, produto_em_folha):
    assert _ids_filtrados(client, arvore["outra_raiz"].id_conta) == set()


def test_filtro_ignora_ramo_irmao(client, arvore, produto_em_folha):
    assert _ids_filtrados(client, arvore["filhas"][1].id_conta) == set()


def test_filtro_com_categoria_inexistente_retorna_vazio(client, arvore, produto_em_folha):
    assert _ids_filtrados(client, 99999999) == set()
