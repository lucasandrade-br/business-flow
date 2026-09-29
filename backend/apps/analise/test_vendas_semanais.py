from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.analise.models import MovimentoProdutoDiario, MovimentoProdutoSemanal, StatusMovimentoProdutoSemanal
from apps.analise.services import montar_analise_vendas_categorias, reconstruir_movimento_produto_mensal
from apps.analise.services_vendas_semanais import inicio_semana, reconstruir_movimento_produto_semanal, reconstruir_movimentos_produto_semanais
from apps.cadastros.models import PlanoConta, Produto, UnidadeMedida, Usuario
from apps.vendas.models import ItemVenda, Venda

from .test_categorias import _produto


pytestmark = pytest.mark.django_db


@pytest.fixture
def base():
    raiz = PlanoConta.objects.create(nome_conta="RECEITAS")
    folha = PlanoConta.objects.create(nome_conta="PADARIA", conta_pai=raiz)
    unidade = UnidadeMedida.objects.create(sigla="UN", descricao="Unidade")
    usuario = Usuario.objects.create(id_usuario=501, nome="Teste")
    produto = _produto(501, "PAO", folha)
    return raiz, folha, unidade, usuario, produto


def vender(base, legado, data, valor, *, quantidade=1, cancelada=False, item_cancelado=False):
    _, _, unidade, usuario, produto = base
    venda = Venda.objects.create(
        id_legado=legado, tipo_documento=Venda.TIPO_NFCE, data_venda=data,
        usuario=usuario, valor_total_documento=Decimal(str(valor)),
        status="C" if cancelada else "",
    )
    ItemVenda.objects.create(
        venda=venda, produto=produto, unidade_medida=unidade,
        quantidade=Decimal(str(quantidade)), valor_unitario=Decimal(str(valor)),
        valor_total_item=Decimal(str(valor)), cancelado=item_cancelado,
    )
    return venda


def linha_raiz(payload, raiz):
    return next(linha for linha in payload["linhas"] if linha["id_conta"] == raiz.id_conta)


def test_reconstrucao_cruza_ano_filtra_itens_e_preserva_snapshot_em_falha(base, monkeypatch):
    inicio = date(2025, 12, 28)
    assert inicio_semana(date(2026, 1, 1)) == inicio
    vender(base, 1, inicio, 10)
    vender(base, 2, date(2026, 1, 1), 20)
    vender(base, 3, date(2026, 1, 2), 100, cancelada=True)
    vender(base, 4, date(2026, 1, 2), 100, item_cancelado=True)
    vender(base, 5, date(2026, 1, 2), -5, quantidade=-1)

    assert reconstruir_movimento_produto_semanal(inicio) == 1
    assert reconstruir_movimento_produto_semanal(inicio) == 1
    assert MovimentoProdutoDiario.objects.filter(data__gte=inicio, data__lte=date(2026, 1, 3)).count() == 2
    assert MovimentoProdutoSemanal.objects.get(semana_inicio=inicio).receita_bruta == 30
    assert sum(MovimentoProdutoDiario.objects.values_list("receita_bruta", flat=True)) == 30
    reconstruir_movimento_produto_mensal(2025, 12)
    reconstruir_movimento_produto_mensal(2026, 1)
    assert sum(MovimentoProdutoDiario.objects.filter(data__year=2025).values_list("receita_bruta", flat=True)) == 10
    assert sum(MovimentoProdutoDiario.objects.filter(data__year=2026).values_list("receita_bruta", flat=True)) == 20

    def falhar(*args, **kwargs):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(MovimentoProdutoSemanal.objects, "bulk_create", falhar)
    with pytest.raises(RuntimeError):
        reconstruir_movimento_produto_semanal(inicio)
    assert MovimentoProdutoSemanal.objects.get(semana_inicio=inicio).receita_bruta == 30
    assert MovimentoProdutoDiario.objects.count() == 2
    assert StatusMovimentoProdutoSemanal.objects.get(semana_inicio=inicio).status == "FALHA"


def test_api_semanal_equivalente_media_e_semana_zerada(base):
    raiz = base[0]
    foco = date(2026, 4, 5)
    for indice in range(20):
        inicio = foco - timedelta(days=7 * (20 - indice))
        if indice != 18:
            vender(base, 100 + indice * 2, inicio, 10)
            vender(base, 101 + indice * 2, inicio + timedelta(days=4), 20)
        reconstruir_movimento_produto_semanal(inicio)
    vender(base, 1000, foco, 15)
    vender(base, 1001, foco + timedelta(days=2), 25)
    reconstruir_movimento_produto_semanal(foco)

    client = APIClient()
    path = f"/api/analise/categorias/vendas/semanal/?raiz_id={raiz.id_conta}&semana_inicio={foco}&metrica=valor"
    response = client.get(path + "&periodo_equivalente=1", HTTP_HOST="localhost")
    assert response.status_code == 200
    payload = response.json()
    linha = linha_raiz(payload, raiz)
    assert payload["periodos_considerados_20"] == 20
    assert payload["periodos_considerados_5"] == 5
    assert payload["semana_parcial"] is True
    assert payload["semanas"][-1]["data_corte"] == "2026-04-07"
    assert [Decimal(valor) for valor in linha["valores"]] == [10, 10, 10, 0, 10, 40]
    assert Decimal(linha["media_20"]) == Decimal("9.5")
    assert Decimal(linha["media_5"]) == Decimal("8")
    assert Decimal(linha["variacao_5_vs_20_percentual"]) == (Decimal("8") - Decimal("9.5")) / Decimal("9.5") * 100
    assert Decimal(linha["variacao_5_percentual"]) == Decimal("400")

    completo = client.get(path + "&periodo_equivalente=0", HTTP_HOST="localhost").json()
    linha_completa = linha_raiz(completo, raiz)
    assert Decimal(linha_completa["media_5"]) == Decimal("24")
    assert completo["periodo_equivalente"] is False

    historica = client.get(path.replace(str(foco), str(foco - timedelta(days=7))), HTTP_HOST="localhost").json()
    assert historica["semana_parcial"] is False
    assert historica["semanas"][-1]["inicio"] == str(foco - timedelta(days=7))
    assert historica["periodos_considerados_20"] == 19
    assert Decimal(historica["linhas"][0]["media_20"]) == Decimal(18 * 30) / 19

    outra_folha = PlanoConta.objects.create(nome_conta="OUTRA", conta_pai=raiz)
    Produto.categorias.through.objects.create(produto_id=base[4].id_produto, planoconta_id=outra_folha.id_conta)
    conflito = client.get(path, HTTP_HOST="localhost")
    assert conflito.status_code == 409


def test_variacao_historica_e_recente_separam_medias_e_valem_por_unidade(base):
    raiz, folha, _, _, produto = base
    foco = date(2026, 5, 3)
    for indice in range(20):
        inicio = foco - timedelta(days=7 * (20 - indice))
        vender(base, 1000 + indice, inicio + timedelta(days=6), 100 if indice < 15 else 200,
               quantidade=1 if indice < 15 else 2)
        reconstruir_movimento_produto_semanal(inicio)
    vender(base, 2000, foco + timedelta(days=6), 150, quantidade=Decimal("1.5"))
    reconstruir_movimento_produto_semanal(foco)

    client = APIClient()
    for metrica in ("valor", "quantidade"):
        parametros = {"raiz_id": raiz.id_conta, "semana_inicio": str(foco), "metrica": metrica}
        categoria = client.get("/api/analise/categorias/vendas/semanal/", parametros, HTTP_HOST="localhost").json()
        produto_payload = client.get("/api/analise/categorias/produtos/vendas/semanal/",
                                     {**parametros, "categoria_id": folha.id_conta}, HTTP_HOST="localhost").json()
        linha_categoria = linha_raiz(categoria, folha)
        linha_produto = next(linha for linha in produto_payload["linhas"] if linha["id_produto"] == produto.id_produto)
        if metrica == "quantidade":
            linha_categoria = linha_categoria["unidades"][0]
            linha_produto = linha_produto["unidades"][0]
            assert linha_categoria["sigla"] == linha_produto["sigla"] == "UN"
        for linha in (linha_categoria, linha_produto):
            assert Decimal(linha["variacao_5_vs_20_percentual"]) == Decimal("60")
            assert Decimal(linha["variacao_5_percentual"]) == Decimal("-25")
            assert Decimal(linha["media_20"]) == (Decimal("125") if metrica == "valor" else Decimal("1.25"))
            assert Decimal(linha["media_5"]) == (Decimal("200") if metrica == "valor" else Decimal("2"))

    sem_referencia = client.get("/api/analise/categorias/produtos/vendas/semanal/",
                               {"raiz_id": raiz.id_conta, "categoria_id": folha.id_conta,
                                "semana_inicio": str(foco - timedelta(days=20 * 7)), "metrica": "valor"},
                               HTTP_HOST="localhost").json()
    assert sem_referencia["linhas"][0]["variacao_5_vs_20_percentual"] is None


def test_mensal_equivalente_preserva_padrao_e_separa_unidades(base, monkeypatch):
    raiz = base[0]
    monkeypatch.setattr("apps.analise.services.timezone.localdate", lambda: date(2026, 9, 16))
    vender(base, 1, date(2026, 1, 10), 10)
    vender(base, 2, date(2026, 1, 20), 20)
    vender(base, 3, date(2026, 9, 15), 50)
    reconstruir_movimento_produto_mensal(2026, 1)
    reconstruir_movimento_produto_mensal(2026, 9)
    incompleto = APIClient().get(
        f"/api/analise/categorias/vendas/?ano=2026&raiz_id={raiz.id_conta}&metrica=valor&periodo_equivalente=1",
        HTTP_HOST="localhost",
    )
    assert incompleto.status_code == 503
    produto_path = "/api/analise/categorias/produtos/vendas/"
    produto_params = {"ano": 2026, "raiz_id": raiz.id_conta, "categoria_id": base[1].id_conta, "metrica": "valor"}
    assert APIClient().get(produto_path, {**produto_params, "periodo_equivalente": "1"}, HTTP_HOST="localhost").status_code == 503
    reconstruir_movimentos_produto_semanais()
    mensal = montar_analise_vendas_categorias(ano=2026, raiz_id=raiz.id_conta, metrica="valor")
    comparavel = montar_analise_vendas_categorias(ano=2026, raiz_id=raiz.id_conta, metrica="valor", periodo_equivalente=True)
    assert Decimal(linha_raiz(mensal, raiz)["total"]) == 80
    assert Decimal(linha_raiz(comparavel, raiz)["valores"][0]) == 10
    assert Decimal(linha_raiz(comparavel, raiz)["total"]) == 60
    assert comparavel["dia_corte"] == 15

    padrao_produto = APIClient().get(produto_path, produto_params, HTTP_HOST="localhost").json()
    comparavel_produto = APIClient().get(produto_path, {**produto_params, "periodo_equivalente": "1"}, HTTP_HOST="localhost").json()
    assert padrao_produto["periodo_equivalente"] is False
    assert Decimal(padrao_produto["linhas"][0]["total"]) == 80
    assert comparavel_produto["periodo_equivalente"] is True
    assert comparavel_produto["dia_corte"] == 15
    assert Decimal(comparavel_produto["linhas"][0]["valores"][0]) == 10
    assert Decimal(comparavel_produto["linhas"][0]["total"]) == 60
    assert comparavel_produto["linhas"][0]["valores"] == linha_raiz(comparavel, base[1])["valores"]

    quantidades = APIClient().get(produto_path, {**produto_params, "metrica": "quantidade", "periodo_equivalente": "1"}, HTTP_HOST="localhost").json()
    assert [Decimal(valor) for valor in quantidades["linhas"][0]["unidades"][0]["valores"] if Decimal(valor)] == [1, 1]
    assert Decimal(quantidades["linhas"][0]["unidades"][0]["total"]) == 2
    monkeypatch.setattr("apps.analise.services.timezone.localdate", lambda: date(2027, 1, 1))
    historico_produto = APIClient().get(produto_path, {**produto_params, "periodo_equivalente": "1"}, HTTP_HOST="localhost").json()
    assert historico_produto["periodo_equivalente"] is False
    assert Decimal(historico_produto["linhas"][0]["total"]) == 80

    semanal = APIClient().get(
        f"/api/analise/categorias/vendas/semanal/?raiz_id={raiz.id_conta}&semana_inicio={inicio_semana(date(2026, 9, 15))}&metrica=quantidade",
        HTTP_HOST="localhost",
    ).json()
    unidades = linha_raiz(semanal, raiz)["unidades"]
    assert unidades[0]["sigla"] == "UN"
    assert Decimal(unidades[0]["valores"][-1]) == 1


def test_produtos_semanais_ordenacao_corte_unidades_e_conciliacao(base):
    raiz, folha, unidade, usuario, principal = base
    foco = date(2026, 1, 4)
    segundo = _produto(502, "BOLO", folha)
    inativo = _produto(503, "ROSCA", folha)
    inativo.status = "INATIVO"
    inativo.save(update_fields=["status"])
    parado = _produto(504, "SEM VENDA", folha)
    unidade_kg = UnidadeMedida.objects.create(sigla="KG", descricao="Quilograma")

    def venda_produto(produto, legado, data, valor, unidade_item=unidade, quantidade=2):
        venda = Venda.objects.create(id_legado=legado, tipo_documento=Venda.TIPO_NFCE, data_venda=data,
                                   usuario=usuario, valor_total_documento=Decimal(str(valor)), status="")
        ItemVenda.objects.create(venda=venda, produto=produto, unidade_medida=unidade_item,
                                quantidade=Decimal(str(quantidade)), valor_unitario=Decimal(str(valor)) / Decimal(str(quantidade)),
                                valor_total_item=Decimal(str(valor)))

    anterior = foco - timedelta(days=7)
    venda_produto(principal, 900, anterior, 100)
    venda_produto(principal, 901, anterior + timedelta(days=4), 100)
    venda_produto(segundo, 902, anterior, 60, unidade_kg, quantidade=100)
    venda_produto(inativo, 903, anterior, 20)
    reconstruir_movimento_produto_semanal(anterior)
    venda_produto(principal, 904, foco, 10)
    venda_produto(segundo, 905, foco, 25, unidade_kg, quantidade=1)
    reconstruir_movimento_produto_semanal(foco)

    path = "/api/analise/categorias/produtos/vendas/semanal/"
    params = {"raiz_id": raiz.id_conta, "categoria_id": folha.id_conta,
              "semana_inicio": str(foco), "metrica": "quantidade", "incluir_inativos": "1"}
    client = APIClient()
    resposta = client.get(path, params, HTTP_HOST="localhost")
    assert resposta.status_code == 200
    payload = resposta.json()
    assert payload["semana_parcial"] is True
    assert payload["periodos_considerados_20"] == 1
    assert payload["periodos_considerados_5"] == 1
    assert payload["semanas"][-1]["data_corte"] == "2026-01-04"
    # Segundo vende mais na semana foco; principal lidera pela média anterior.
    assert [linha["id_produto"] for linha in payload["linhas"]] == [principal.id_produto, segundo.id_produto, inativo.id_produto, parado.id_produto]
    assert payload["linhas"][0]["unidades"][0]["sigla"] == "UN"
    assert payload["linhas"][1]["unidades"][0]["sigla"] == "KG"
    assert Decimal(payload["linhas"][0]["unidades"][0]["media_5"]) == 2
    assert payload["linhas"][3]["unidades"] == []
    assert client.get(path, {**params, "incluir_inativos": "0"}, HTTP_HOST="localhost").json()["paginacao"]["total_produtos"] == 3

    # O corte equivalente descarta a venda da quinta-feira da semana anterior.
    valores = client.get(path, {**params, "metrica": "valor"}, HTTP_HOST="localhost").json()
    assert [linha["id_produto"] for linha in valores["linhas"][:2]] == [principal.id_produto, segundo.id_produto]
    assert Decimal(valores["linhas"][0]["media_20"]) == 100
    assert Decimal(valores["linhas"][0]["media_5"]) == 100
    completos = client.get(path, {**params, "metrica": "valor", "periodo_equivalente": "0"}, HTTP_HOST="localhost").json()
    assert [linha["id_produto"] for linha in completos["linhas"][:2]] == [principal.id_produto, segundo.id_produto]
    assert Decimal(completos["linhas"][0]["media_20"]) == 200
    assert Decimal(completos["linhas"][0]["media_5"]) == 200
    historico = client.get(path, {**params, "semana_inicio": str(anterior)}, HTTP_HOST="localhost").json()
    assert historico["periodos_considerados_20"] == 0
    assert [linha["id_produto"] for linha in historico["linhas"]] == [segundo.id_produto, principal.id_produto, inativo.id_produto, parado.id_produto]
    matriz = client.get("/api/analise/categorias/vendas/semanal/",
                        {"raiz_id": raiz.id_conta, "semana_inicio": str(foco), "metrica": "valor"}, HTTP_HOST="localhost").json()
    folha_matriz = linha_raiz(matriz, folha)
    for indice in range(6):
        if folha_matriz["valores"][indice] is not None:
            assert sum(Decimal(linha["valores"][indice]) for linha in valores["linhas"]) == Decimal(folha_matriz["valores"][indice])


def test_produtos_semanais_paginacao_busca_status_e_snapshot_ausente(base):
    raiz, folha, _, _, _ = base
    foco = date(2026, 2, 1)
    vender(base, 1000, foco - timedelta(days=14), 10)
    vender(base, 1001, foco, 5)
    reconstruir_movimento_produto_semanal(foco - timedelta(days=14))
    reconstruir_movimento_produto_semanal(foco)
    base[4].status = "INATIVO"
    base[4].save(update_fields=["status"])
    for indice in range(101):
        _produto(1000 + indice, f"PRODUTO {indice:03}", folha)
    path = "/api/analise/categorias/produtos/vendas/semanal/"
    params = {"raiz_id": raiz.id_conta, "categoria_id": folha.id_conta,
              "semana_inicio": str(foco), "metrica": "valor", "incluir_inativos": "1"}
    client = APIClient()
    primeira = client.get(path, params, HTTP_HOST="localhost").json()
    segunda = client.get(path, {**params, "page": 2}, HTTP_HOST="localhost").json()
    assert primeira["paginacao"]["total_produtos"] == 102
    assert len(primeira["linhas"]) == 100
    assert len(segunda["linhas"]) == 2
    assert primeira["desatualizado"] is True
    assert primeira["periodos_considerados_20"] == 1
    assert primeira["linhas"][0]["valores"][-2] is None
    assert client.get(path, {**params, "incluir_inativos": "0"}, HTTP_HOST="localhost").json()["paginacao"]["total_produtos"] == 101
    matriz = client.get("/api/analise/categorias/vendas/semanal/",
                        {"raiz_id": raiz.id_conta, "semana_inicio": str(foco), "metrica": "valor"}, HTTP_HOST="localhost").json()
    folha_matriz = linha_raiz(matriz, folha)
    todas_linhas = primeira["linhas"] + segunda["linhas"]
    for indice, valor in enumerate(folha_matriz["valores"]):
        if valor is not None:
            assert sum(Decimal(linha["valores"][indice]) for linha in todas_linhas) == Decimal(valor)
    familia_inteira = client.get(path, {**params, "categoria_id": raiz.id_conta}, HTTP_HOST="localhost").json()
    assert familia_inteira["paginacao"]["total_produtos"] == 102
    assert client.get(path, {**params, "search": "PRODUTO 010"}, HTTP_HOST="localhost").json()["paginacao"]["total_produtos"] == 1
    assert client.get(path, {**params, "semana_inicio": "2026-01-31"}, HTTP_HOST="localhost").status_code == 400
    assert client.get(path, {**params, "semana_inicio": "2026-02-08"}, HTTP_HOST="localhost").status_code == 404
    outra = PlanoConta.objects.create(nome_conta="OUTRA", conta_pai=raiz)
    Produto.categorias.through.objects.create(produto_id=base[4].id_produto, planoconta_id=outra.id_conta)
    assert client.get(path, params, HTTP_HOST="localhost").status_code == 409
