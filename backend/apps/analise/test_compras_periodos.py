from datetime import date
from decimal import Decimal

import pytest
from django.db.models import Sum
from rest_framework.test import APIClient

from apps.analise.models import (
    MovimentoCompraProdutoDiario, MovimentoCompraProdutoMensal,
    MovimentoCompraProdutoSemanal, StatusMovimentoCompraProdutoSemanal,
)
from apps.analise.services import reconstruir_movimento_compra_produto_mensal, reconstruir_movimentos_compra_produto_mensal
from apps.analise.services_compras_periodos import (
    inicio_semana, reconstruir_movimento_compra_produto_semanal,
    reconstruir_movimentos_compra_produto_semanais,
    montar_analise_compras_categorias_periodo,
    montar_analise_compras_produtos_periodo,
)
from apps.analise.test_compras_categorias import cenario_compras, _item
from apps.compras.models import Compra, ItemCompra

pytestmark = pytest.mark.django_db


def test_calendario_reconstrucao_e_conciliacao(cenario_compras):
    assert inicio_semana(date(2026, 1, 1)) == date(2025, 12, 28)
    reconstruir_movimentos_compra_produto_mensal()
    resultado = reconstruir_movimentos_compra_produto_semanais(somente_pendentes=True)
    assert resultado["periodos_processados"] == 6
    assert reconstruir_movimentos_compra_produto_semanais(somente_pendentes=True)["periodos_processados"] == 0
    assert StatusMovimentoCompraProdutoSemanal.objects.filter(status="PRONTO").count() == 6
    assert MovimentoCompraProdutoSemanal.objects.filter(semana_inicio=date(2026, 1, 25)).count() == 0
    diario = MovimentoCompraProdutoDiario.objects.filter(data__month=1).aggregate(v=Sum("valor_comprado"))["v"]
    mensal = MovimentoCompraProdutoMensal.objects.filter(ano=2026, mes=1).aggregate(v=Sum("valor_comprado"))["v"]
    assert diario == mensal


def test_semanal_filtro_fornecedor_corte_e_custo_ponderado(cenario_compras):
    reconstruir_movimentos_compra_produto_semanais()
    folha = cenario_compras["folha_un"].id_conta
    raiz = cenario_compras["raiz"].id_conta
    kwargs = dict(periodo="semanal", raiz_id=raiz, categoria_id=folha,
                  semana_inicio=date(2026, 2, 8), fornecedor_id=1,
                  periodo_equivalente=True)
    dados = montar_analise_compras_produtos_periodo(**kwargs, metrica="custo_medio")
    linha = next(p for p in dados["linhas"] if p["id_produto"] == 201)
    unidade = linha["unidades"][0]
    assert dados["semana_parcial"] is True
    assert dados["periodos_considerados_20"] == 5
    assert Decimal(unidade["valores"][-1]) == 20
    assert dados["paginacao"]["total_produtos"] == 2
    valores = montar_analise_compras_categorias_periodo(
        periodo="semanal", raiz_id=raiz, semana_inicio=date(2026, 2, 8),
        metrica="valor", fornecedor_id=1, periodo_equivalente=True,
    )
    assert Decimal(next(x for x in valores["linhas"] if x["id_conta"] == folha)["valores"][-1]) == 100


def test_mensal_sem_snapshot_indisponivel_e_api(cenario_compras):
    raiz = cenario_compras["raiz"].id_conta
    reconstruir_movimentos_compra_produto_mensal()
    reconstruir_movimentos_compra_produto_semanais()
    payload = APIClient().get("/api/analise/categorias/compras/", {
        "ano": 2026, "raiz_id": raiz, "metrica": "valor",
    })
    assert payload.status_code == 200
    assert payload.json()["linhas"][0]["valores"][2] is None
    semanal = APIClient().get("/api/analise/categorias/compras/semanal/", {
        "semana_inicio": "2026-02-08", "raiz_id": raiz, "metrica": "valor",
    })
    assert semanal.status_code == 200
    StatusMovimentoCompraProdutoSemanal.objects.filter(semana_inicio=date(2026, 1, 25)).delete()
    aviso = APIClient().get("/api/analise/categorias/compras/semanal/", {
        "semana_inicio": "2026-02-08", "raiz_id": raiz, "metrica": "valor",
    }).json()
    assert aviso["desatualizado"] is True
    assert aviso["periodos_considerados_20"] == 4
    assert aviso["linhas"][0]["media_20"] is None


def test_mensal_equivalente_e_anual_api(cenario_compras):
    raiz = cenario_compras["raiz"].id_conta
    reconstruir_movimentos_compra_produto_mensal()
    reconstruir_movimentos_compra_produto_semanais()
    cliente = APIClient()
    base = {"ano": 2026, "raiz_id": raiz, "metrica": "valor"}
    mensal = cliente.get("/api/analise/categorias/compras/", base).json()
    equivalente = cliente.get("/api/analise/categorias/compras/", {
        **base, "periodo_equivalente": "1",
    }).json()
    if equivalente.get("periodo_equivalente"):
        assert Decimal(mensal["linhas"][0]["valores"][0]) > Decimal(equivalente["linhas"][0]["valores"][0])
        assert equivalente["rotulo_total"] == "Total comparável"
    anual = cliente.get("/api/analise/categorias/compras/anual/", {
        **base, "periodo_equivalente": "0",
    })
    assert anual.status_code == 200
    assert anual.json()["linhas"][0]["variacao_percentual"] is None
    assert anual.json()["anos"][-1]["ano"] == 2026


def test_falha_semanal_preserva_snapshot(cenario_compras, monkeypatch):
    semana = date(2026, 1, 4)
    reconstruir_movimento_compra_produto_semanal(semana)
    antes = list(MovimentoCompraProdutoSemanal.objects.filter(semana_inicio=semana).values_list("valor_comprado", flat=True))
    def falhar(*args, **kwargs):
        raise RuntimeError("falha simulada")
    monkeypatch.setattr(MovimentoCompraProdutoDiario.objects, "bulk_create", falhar)
    with pytest.raises(RuntimeError):
        reconstruir_movimento_compra_produto_semanal(semana)
    assert list(MovimentoCompraProdutoSemanal.objects.filter(semana_inicio=semana).values_list("valor_comprado", flat=True)) == antes
    assert StatusMovimentoCompraProdutoSemanal.objects.get(semana_inicio=semana).status == "FALHA"


def test_custo_medio_sem_quantidade_indisponivel(cenario_compras):
    unidade = ItemCompra.objects.filter(produto_id=201).first().unidade_medida
    compra = Compra.objects.create(id_legado=9090, fornecedor=cenario_compras["fornecedor_a"],
                                   data_emissao=date(2026, 1, 20), valor_total_documento=10)
    _item(compra, cenario_compras["produto_zero"], unidade, 0, 10)
    reconstruir_movimento_compra_produto_mensal(2026, 1)
    dados = montar_analise_compras_produtos_periodo(
        periodo="mensal", raiz_id=cenario_compras["raiz"].id_conta,
        categoria_id=cenario_compras["folha_un"].id_conta,
        ano=2026, metrica="custo_medio",
    )
    linha = next(p for p in dados["linhas"] if p["id_produto"] == cenario_compras["produto_zero"].id_produto)
    assert linha["unidades"][0]["valores"][0] is None
    assert linha["unidades"][0]["total"] is None
