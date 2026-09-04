from datetime import date, time
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.analise.models import DashboardKpiVenda
from apps.analise.services import processar_kpis_dashboard
from apps.cadastros.models import Produto, Usuario
from apps.vendas.models import ItemVenda, Venda


pytestmark = pytest.mark.django_db


def _venda(usuario, legado, data, valor, hora=None, status=""):
    return Venda.objects.create(
        id_legado=legado,
        tipo_documento=Venda.TIPO_NFCE,
        data_venda=data,
        hora_venda=hora,
        status=status,
        usuario=usuario,
        valor_total_documento=Decimal(str(valor)),
    )


@pytest.fixture
def cenario_dashboard_vendas():
    usuario = Usuario.objects.create(id_usuario=701, nome="Operador")
    produto = Produto.objects.create(
        id_produto=701,
        produto="Produto teste",
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

    venda_manha = _venda(usuario, 701, date(2026, 1, 2), 10, time(12, 59, 59))
    ItemVenda.objects.create(
        venda=venda_manha,
        produto=produto,
        quantidade=1,
        valor_unitario=5,
        valor_total_item=5,
    )
    ItemVenda.objects.create(
        venda=venda_manha,
        produto=produto,
        quantidade=1,
        valor_unitario=5,
        valor_total_item=5,
    )
    _venda(usuario, 702, date(2026, 1, 4), 30, time(13, 0, 0))
    _venda(usuario, 703, date(2026, 2, 8), 50, time(9, 0, 0))
    _venda(usuario, 704, date(2026, 2, 11), 40, None)
    _venda(usuario, 705, date(2026, 12, 20), 999, time(14, 0, 0), status="C")

    _venda(usuario, 601, date(2025, 1, 2), 20, time(10, 0, 0))
    _venda(usuario, 602, date(2025, 2, 10), 70, time(14, 0, 0))

    processar_kpis_dashboard()
    return DashboardKpiVenda.objects.get(id=1)


def test_dashboard_periodico_volume_ticket_turnos_e_periodo_aberto(cenario_dashboard_vendas):
    kpi = cenario_dashboard_vendas
    mensal = kpi.dados_periodicos_grafico["mensal"]
    semanal = kpi.dados_periodicos_grafico["semanal"]

    assert kpi.ultima_data_processada == date(2026, 2, 11)
    assert len(mensal) == 2
    assert mensal[0]["receita_atual"] == "40"
    assert mensal[0]["volume_atual"] == 2  # Dois documentos, apesar dos dois itens da primeira venda.
    assert Decimal(mensal[0]["ticket_medio_atual"]) == Decimal("20")
    assert mensal[0]["faturamento_manha"] == "10"
    assert mensal[0]["faturamento_tarde"] == "30"

    assert mensal[1]["parcial"] is True
    assert mensal[1]["data_corte"] == "2026-02-11"
    assert mensal[1]["receita_atual"] == "90"
    assert mensal[1]["receita_anterior_equivalente"] == "70"
    assert Decimal(mensal[1]["ticket_medio_atual"]) == Decimal("45")
    assert mensal[1]["faturamento_manha"] == "50"
    assert mensal[1]["faturamento_tarde"] == "0"

    assert semanal[2]["receita_atual"] == "0"  # Semana fechada sem movimento.
    assert semanal[2]["parcial"] is False
    assert semanal[-1]["label"] == "S07"
    assert semanal[-1]["parcial"] is True
    assert semanal[-1]["receita_anterior_equivalente"] == "70"

    assert kpi.faturamento_mensal_medio_atual == Decimal("40.00")
    assert kpi.faturamento_mensal_medio_anterior_equivalente == Decimal("20.00")
    assert kpi.faturamento_semanal_medio_atual == Decimal("6.67")
    assert kpi.faturamento_semanal_medio_anterior_equivalente == Decimal("3.33")
    assert kpi.volume_sem_horario_atual == 1
    assert kpi.faturamento_sem_horario_atual == Decimal("40.00")


def test_api_preserva_contrato_e_expoe_expansao(cenario_dashboard_vendas):
    response = APIClient().get("/api/analise/dashboard/kpis/", HTTP_HOST="localhost")

    assert response.status_code == 200
    payload = response.json()
    assert "dados_mensais_grafico" in payload
    assert payload["faturamento_medio"]["mensal"] == {
        "atual": "40.00",
        "anterior_equivalente": "20.00",
        "periodos_considerados": 1,
    }
    assert payload["faturamento_medio"]["semanal"]["periodos_considerados"] == 6
    assert payload["graficos"]["semanal"][-1]["parcial"] is True
    assert payload["vendas_sem_horario"] == {"quantidade": 1, "faturamento": "40.00"}
