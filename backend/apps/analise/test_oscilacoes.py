import calendar
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.analise.models import StatusMovimentoProdutoMensal, StatusMovimentoProdutoSemanal
from apps.analise.services import reconstruir_movimento_produto_mensal
from apps.analise.services_vendas_semanais import reconstruir_movimento_produto_semanal, reconstruir_movimentos_produto_semanais
from apps.cadastros.models import PlanoConta, UnidadeMedida, Usuario
from apps.vendas.models import ItemVenda, Venda

from .test_categorias import _produto


pytestmark = pytest.mark.django_db


@pytest.fixture
def cenario():
    raiz = PlanoConta.objects.create(nome_conta="RECEITAS")
    unidade = UnidadeMedida.objects.create(sigla="UN", descricao="Unidade")
    usuario = Usuario.objects.create(id_usuario=700, nome="Operador")
    contador = [0]

    def produto(nome):
        folha = PlanoConta.objects.create(nome_conta=nome, conta_pai=raiz)
        return folha, _produto(700 + folha.id_conta, nome, folha)

    def venda(produto_obj, data, valor):
        contador[0] += 1
        valor = Decimal(str(valor)).quantize(Decimal("0.000001"))
        documento = Venda.objects.create(
            id_legado=contador[0], tipo_documento=Venda.TIPO_NFCE,
            data_venda=data, usuario=usuario, valor_total_documento=valor, status="",
        )
        ItemVenda.objects.create(
            venda=documento, produto=produto_obj, unidade_medida=unidade,
            quantidade=1, valor_unitario=valor, valor_total_item=valor,
        )

    return raiz, produto, venda


def _radar(client, raiz, **params):
    return client.get("/api/analise/categorias/vendas/oscilacoes/", {"raiz_id": raiz.id_conta, **params}, HTTP_HOST="localhost")


def test_radar_mensal_aplica_indice_e_exemplos_em_30_dias(cenario, monkeypatch):
    raiz, criar_produto, vender = cenario
    monkeypatch.setattr("apps.analise.services_oscilacoes.detectar_mes_aberto", lambda ano, ultima: None)
    exemplos = [
        ("UM_DOIS", Decimal("1"), Decimal("2")),
        ("DEZ_ZERO", Decimal("10"), Decimal("0")),
        ("CINCO_MIL", Decimal("5000"), Decimal("3500")),
        ("CEM_MIL", Decimal("100000"), Decimal("98500")),
        ("MILHAO", Decimal("1000000"), Decimal("950000")),
        ("CRESCE", Decimal("5000"), Decimal("6500")),
        ("NOVA", Decimal("0"), Decimal("1000")),
    ]
    folhas = {}
    for nome, referencia, recente in exemplos:
        folhas[nome], produto = criar_produto(nome)
        for mes in range(1, 6):
            if referencia:
                dias = calendar.monthrange(2026, mes)[1]
                vender(produto, date(2026, mes, 1), referencia * Decimal(dias) / 30)
        if recente:
            vender(produto, date(2026, 6, 30) if nome == "UM_DOIS" else date(2026, 6, 1), recente)
    for mes in range(1, 7):
        reconstruir_movimento_produto_mensal(2026, mes)

    resposta = _radar(APIClient(), raiz, visao="mensal", ano=2026)
    assert resposta.status_code == 200
    payload = resposta.json()
    assert payload["disponivel"] is True
    assert payload["previa"] is False
    assert payload["janela_referencia"]["inicio"] == "2026-01-01"
    assert payload["periodo_foco"]["inicio"] == "2026-06-01"
    assert [item["id_conta"] for item in payload["quedas"]] == [folhas["MILHAO"].id_conta, folhas["CINCO_MIL"].id_conta]
    assert [item["id_conta"] for item in payload["crescimentos"]] == [folhas["CRESCE"].id_conta]
    assert Decimal(payload["quedas"][1]["media_referencia"]).quantize(Decimal("0.01")) == Decimal("5000.00")

    StatusMovimentoProdutoMensal.objects.filter(ano=2026, mes=3).update(status="FALHA")
    indisponivel = _radar(APIClient(), raiz, visao="mensal", ano=2026).json()
    assert indisponivel["disponivel"] is False
    assert indisponivel["quedas"] == []
    assert indisponivel["periodos_pendentes"][0]["inicio"] == "2026-03-01"

    StatusMovimentoProdutoMensal.objects.filter(ano=2026, mes=3).update(status="PRONTO")
    outra_folha = PlanoConta.objects.create(nome_conta="CONFLITO", conta_pai=raiz)
    from apps.cadastros.models import Produto
    produto_milhao = Produto.objects.get(id_produto=700 + folhas["MILHAO"].id_conta)
    Produto.categorias.through.objects.create(produto_id=produto_milhao.id_produto, planoconta_id=outra_folha.id_conta)
    assert _radar(APIClient(), raiz, visao="mensal", ano=2026).status_code == 409


def test_radar_semanal_cruza_ano_e_nao_usa_semanas_futuras(cenario):
    raiz, criar_produto, vender = cenario
    principal, produto_principal = criar_produto("PRINCIPAL")
    secundario, produto_secundario = criar_produto("SECUNDARIO")
    foco = date(2026, 1, 4)
    inicios = [foco - timedelta(days=7 * indice) for indice in range(24, -1, -1)]
    for indice, inicio in enumerate(inicios):
        recente = indice >= 20
        vender(produto_principal, inicio + timedelta(days=6), (Decimal("3500") if recente else Decimal("5000")) * 7 / 30)
        vender(produto_secundario, inicio + timedelta(days=6), (Decimal("98500") if recente else Decimal("100000")) * 7 / 30)
        reconstruir_movimento_produto_semanal(inicio)
    params = {"visao": "semanal", "semana_inicio": str(foco)}
    with CaptureQueriesContext(connection) as consultas:
        antes = _radar(APIClient(), raiz, **params).json()
    assert len(consultas) <= 10
    assert all('"item_venda"' not in consulta["sql"].lower() for consulta in consultas)
    assert antes["disponivel"] is True
    assert antes["janela_referencia"]["inicio"] == str(inicios[0])
    assert antes["janela_recente"]["inicio"] == str(inicios[20])
    assert [item["id_conta"] for item in antes["quedas"]] == [principal.id_conta]
    assert secundario.id_conta not in [item["id_conta"] for item in antes["quedas"]]

    futuro = foco + timedelta(days=7)
    vender(produto_secundario, futuro + timedelta(days=6), Decimal("1000000"))
    reconstruir_movimento_produto_semanal(futuro)
    depois = _radar(APIClient(), raiz, **params).json()
    assert depois["quedas"] == antes["quedas"]
    StatusMovimentoProdutoSemanal.objects.filter(semana_inicio=inicios[0]).delete()
    incompleto = _radar(APIClient(), raiz, **params).json()
    assert incompleto["disponivel"] is False
    assert incompleto["quedas"] == []
    assert incompleto["motivo"] == "HISTORICO_INCOMPLETO"


def test_radar_semanal_parcial_recorta_todos_os_periodos(cenario):
    raiz, criar_produto, vender = cenario
    folha, produto = criar_produto("CORTE SEMANAL")
    foco = date(2026, 4, 5)
    for indice in range(25):
        inicio = foco - timedelta(days=7 * (24 - indice))
        vender(produto, inicio, 200 if indice < 20 else 50)
        if indice < 24:
            vender(produto, inicio + timedelta(days=4), 900)
        reconstruir_movimento_produto_semanal(inicio)
    payload = _radar(APIClient(), raiz, visao="semanal", semana_inicio=str(foco)).json()
    assert payload["previa"] is True
    assert payload["periodo_foco"]["corte"] == str(foco)
    assert [item["id_conta"] for item in payload["quedas"]] == [folha.id_conta]
    assert Decimal(payload["quedas"][0]["media_referencia"]) == 6000
    assert Decimal(payload["quedas"][0]["media_recente"]) == 1500


def test_radar_mensal_parcial_exige_diario_e_recorta_por_dia(cenario, monkeypatch):
    raiz, criar_produto, vender = cenario
    folha, produto = criar_produto("CORTE MENSAL")
    monkeypatch.setattr("apps.analise.services_oscilacoes.detectar_mes_aberto", lambda ano, ultima: 9)
    for mes in range(4, 10):
        vender(produto, date(2026, mes, 1), 500 if mes < 9 else 50)
        if mes < 9:
            vender(produto, date(2026, mes, 20), 5000)
        reconstruir_movimento_produto_mensal(2026, mes)
    params = {"visao": "mensal", "ano": 2026}
    sem_diario = _radar(APIClient(), raiz, **params).json()
    assert sem_diario["disponivel"] is False
    assert sem_diario["periodos_pendentes"][0]["agregado"] == "diario"
    reconstruir_movimentos_produto_semanais()
    payload = _radar(APIClient(), raiz, **params).json()
    assert payload["disponivel"] is True
    assert payload["previa"] is True
    assert payload["periodo_foco"]["corte"] == "2026-09-01"
    assert [item["id_conta"] for item in payload["quedas"]] == [folha.id_conta]
    assert Decimal(payload["quedas"][0]["media_referencia"]) == 15000
    assert Decimal(payload["quedas"][0]["media_recente"]) == 1500


def test_radar_mensal_cruza_ano_e_normaliza_meses_de_tamanhos_diferentes(cenario):
    raiz, criar_produto, vender = cenario
    folha, produto = criar_produto("VIRADA MENSAL")
    for mes in range(8, 13):
        dias = calendar.monthrange(2025, mes)[1]
        vender(produto, date(2025, mes, dias), Decimal("5000") * dias / 30)
        reconstruir_movimento_produto_mensal(2025, mes)
    vender(produto, date(2026, 1, 31), Decimal("3500") * 31 / 30)
    reconstruir_movimento_produto_mensal(2026, 1)

    payload = _radar(APIClient(), raiz, visao="mensal", ano=2026).json()
    assert payload["disponivel"] is True
    assert payload["janela_referencia"]["inicio"] == "2025-08-01"
    assert payload["periodo_foco"]["inicio"] == "2026-01-01"
    assert [item["id_conta"] for item in payload["quedas"]] == [folha.id_conta]
    assert Decimal(payload["quedas"][0]["media_referencia"]).quantize(Decimal("0.01")) == Decimal("5000.00")


def test_radar_semana_pronta_sem_vendas_da_folha_vale_zero(cenario):
    raiz, criar_produto, vender = cenario
    folha, produto = criar_produto("PAROU DE VENDER")
    _, outro = criar_produto("OUTRA FOLHA")
    foco = date(2026, 1, 4)
    for indice in range(25):
        inicio = foco - timedelta(days=7 * (24 - indice))
        if indice < 20:
            vender(produto, inicio + timedelta(days=6), Decimal("5000") * 7 / 30)
        if indice == 24:
            vender(outro, inicio + timedelta(days=6), Decimal("100"))
        reconstruir_movimento_produto_semanal(inicio)

    payload = _radar(APIClient(), raiz, visao="semanal", semana_inicio=str(foco)).json()
    assert payload["disponivel"] is True
    assert [item["id_conta"] for item in payload["quedas"]] == [folha.id_conta]
    assert Decimal(payload["quedas"][0]["media_recente"]) == 0
