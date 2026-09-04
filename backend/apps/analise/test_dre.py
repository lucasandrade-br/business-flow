from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.analise.models import DreMensalConsolidada
from apps.analise.services import detectar_mes_aberto
from apps.cadastros.models import Fornecedor, Usuario
from apps.compras.models import Compra
from apps.vendas.models import Venda


pytestmark = pytest.mark.django_db


@pytest.fixture
def cenario_dre():
    usuario = Usuario.objects.create(id_usuario=90, nome="Operador")
    fornecedor = Fornecedor.objects.create(id_fornecedor=90, nome_fornecedor="Fornecedor")

    DreMensalConsolidada.objects.create(ano=2025, mes=9, total_receita=100, total_custo=50)
    DreMensalConsolidada.objects.create(ano=2025, mes=12, total_receita=100, total_custo=150)
    DreMensalConsolidada.objects.create(ano=2026, mes=9, total_receita=120, total_custo=60)

    Venda.objects.create(
        id_legado=9001,
        tipo_documento=Venda.TIPO_NFCE,
        data_venda=date(2025, 9, 20),
        usuario=usuario,
        valor_total_documento=Decimal("100"),
    )
    Venda.objects.create(
        id_legado=9002,
        tipo_documento=Venda.TIPO_NFCE,
        data_venda=date(2025, 12, 10),
        usuario=usuario,
        valor_total_documento=Decimal("100"),
    )
    Venda.objects.create(
        id_legado=9003,
        tipo_documento=Venda.TIPO_NFCE,
        data_venda=date(2026, 9, 25),
        usuario=usuario,
        valor_total_documento=Decimal("120"),
    )
    Venda.objects.create(
        id_legado=9004,
        tipo_documento=Venda.TIPO_NFCE,
        data_venda=date(2026, 12, 20),
        usuario=usuario,
        valor_total_documento=Decimal("999"),
        status="C",
    )

    Compra.objects.create(
        id_legado=9001,
        fornecedor=fornecedor,
        data_emissao=date(2025, 9, 20),
        valor_total_documento=Decimal("50"),
    )
    Compra.objects.create(
        id_legado=9002,
        fornecedor=fornecedor,
        data_emissao=date(2025, 12, 10),
        valor_total_documento=Decimal("150"),
    )
    Compra.objects.create(
        id_legado=9003,
        fornecedor=fornecedor,
        data_emissao=date(2026, 9, 20),
        valor_total_documento=Decimal("60"),
    )
    Compra.objects.create(
        id_legado=9004,
        fornecedor=fornecedor,
        data_emissao=date(2026, 12, 20),
        valor_total_documento=Decimal("999"),
        nfe_status="CANCELADA",
    )


def test_dre_mantem_ano_completo_quando_recorte_desligado(cenario_dre):
    response = APIClient().get(
        "/api/analise/dashboard/dre/",
        {"ano": 2026, "periodo_equivalente": 0},
        HTTP_HOST="localhost",
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["periodo_equivalente"] is False
    assert payload["visao_anual"]["receita"]["atual"] == 120.0
    assert payload["visao_anual"]["receita"]["anterior"] == 200.0
    assert payload["visao_anual"]["custo"]["anterior"] == 200.0


def test_dre_recorta_ambos_os_anos_na_ultima_data_valida(cenario_dre, monkeypatch):
    monkeypatch.setattr("apps.analise.services.timezone.localdate", lambda: date(2026, 9, 26))
    response = APIClient().get(
        "/api/analise/dashboard/dre/",
        {"ano": 2026, "periodo_equivalente": 1},
        HTTP_HOST="localhost",
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["periodo_equivalente"] is True
    assert payload["data_corte_atual"] == "2026-09-25"
    assert payload["data_corte_anterior"] == "2025-09-25"
    assert payload["ultima_data_disponivel"] == "2026-09-25"
    assert payload["mes_aberto"] == 9
    assert payload["visao_anual"]["receita"]["atual"] == 120.0
    assert payload["visao_anual"]["receita"]["anterior"] == 100.0
    assert payload["visao_anual"]["custo"]["atual"] == 60.0
    assert payload["visao_anual"]["custo"]["anterior"] == 50.0
    assert payload["visao_anual"]["receita"]["var_relativa"] == 20.0


def test_mes_aberto_so_existe_no_ano_atual_e_antes_do_fim_do_mes(monkeypatch):
    monkeypatch.setattr("apps.analise.services.timezone.localdate", lambda: date(2026, 9, 26))

    assert detectar_mes_aberto(2026, date(2026, 9, 25)) == 9
    assert detectar_mes_aberto(2026, date(2026, 9, 30)) is None
    assert detectar_mes_aberto(2025, date(2025, 9, 25)) is None
    assert detectar_mes_aberto(2026, None) is None
