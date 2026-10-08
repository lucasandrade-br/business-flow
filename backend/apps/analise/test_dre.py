from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient
from django.db.models import Sum
from django.utils import timezone

from apps.analise.models import DreDiarioConsolidada, DreMensalConsolidada, StatusDreConsolidada
from apps.analise.services import detectar_mes_aberto
from apps.analise.services_dre import reconstruir_dre_mes, reconstruir_historico_dre
from apps.cadastros.models import Fornecedor, Usuario
from apps.compras.models import Compra
from apps.despesas.models import (
    AgregadoDespesaDiario, AgregadoDespesaMensal, MovimentoDespesa,
    PagamentoDespesa, SnapshotDespesaMensal, TipoDespesa,
)
from apps.despesas.services import reconstruir_mes as reconstruir_despesas_mes
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


def test_dre_diario_concilia_documentos_e_mantem_api_legada(cenario_dre):
    resultado = reconstruir_historico_dre()
    assert not resultado["falhas"]
    assert DreDiarioConsolidada.objects.get(data=date(2026, 9, 25)).total_receita == 120
    assert DreMensalConsolidada.objects.get(ano=2026, mes=9).total_custo == 60
    diario = DreDiarioConsolidada.objects.filter(data__year=2026, data__month=9).aggregate(
        receita=Sum("total_receita"), custo=Sum("total_custo"),
    )
    mensal_snapshot = DreMensalConsolidada.objects.get(ano=2026, mes=9)
    assert diario["receita"] == mensal_snapshot.total_receita
    assert diario["custo"] == mensal_snapshot.total_custo
    assert StatusDreConsolidada.objects.get(ano=2026, mes=2).status == "PRONTO"
    assert not DreMensalConsolidada.objects.filter(ano=2026, mes=2).exists()
    assert reconstruir_historico_dre(somente_pendentes=True)["processados"] == 0

    client = APIClient()
    anual = client.get("/api/analise/dashboard/dre/anual/", {"ano": 2026, "periodo_equivalente": 1}, HTTP_HOST="localhost")
    legado = client.get("/api/analise/dashboard/dre/", {"ano": 2026, "periodo_equivalente": 1}, HTTP_HOST="localhost")
    assert anual.status_code == legado.status_code == 200
    assert anual.json()["visao_anual"]["receita"] == legado.json()["visao_anual"]["receita"]
    assert anual.json()["visao_anual"]["custo"] == legado.json()["visao_anual"]["custo"]
    assert anual.json()["visao_anual"]["compras"] == legado.json()["visao_anual"]["custo"]
    assert anual.json()["visao_anual"]["despesas"]["atual"] is None
    assert legado.json()["visao_anual"]["margem_bruta"]["atual"] == 60.0
    assert "visao_mensal" not in anual.json()
    mensal = client.get("/api/analise/dashboard/dre/mensal/", {"ano": 2026}, HTTP_HOST="localhost").json()
    assert "visao_anual" not in mensal
    assert mensal["visao_mensal"]["receita"][1] is None
    assert mensal["periodo_equivalente"] is False


def test_dre_mensal_equivalente_corta_fevereiro_e_nao_mostra_meses_vazios(cenario_dre, monkeypatch):
    monkeypatch.setattr("apps.analise.services_dre.detectar_mes_aberto", lambda ano, ultima: 10 if ano == 2026 else None)
    usuario = Usuario.objects.get(id_usuario=90)
    Venda.objects.create(id_legado=9009, tipo_documento=Venda.TIPO_NFCE,
                         data_venda=date(2026, 1, 31), usuario=usuario, valor_total_documento=Decimal("31"))
    Venda.objects.create(id_legado=9010, tipo_documento=Venda.TIPO_NFCE,
                         data_venda=date(2026, 2, 28), usuario=usuario, valor_total_documento=Decimal("28"))
    Venda.objects.create(id_legado=9011, tipo_documento=Venda.TIPO_NFCE,
                         data_venda=date(2026, 9, 30), usuario=usuario, valor_total_documento=Decimal("50"))
    Venda.objects.create(id_legado=9012, tipo_documento=Venda.TIPO_NFCE,
                         data_venda=date(2026, 10, 30), usuario=usuario, valor_total_documento=Decimal("30"))
    assert not reconstruir_historico_dre()["falhas"]
    client = APIClient()
    params = {"ano": 2026, "periodo_equivalente": 1}
    payload = client.get("/api/analise/dashboard/dre/mensal/", params, HTTP_HOST="localhost").json()
    assert payload["periodo_equivalente"] is True
    assert payload["dia_corte"] == 30
    assert payload["visao_mensal"]["receita"][1] == 28.0
    assert payload["visao_mensal"]["receita"][8] == 170.0
    assert payload["visao_mensal"]["receita"][9] == 30.0
    assert payload["visao_mensal"]["receita"][10] is None
    assert payload["visao_mensal"]["receita"][0] == 0.0
    assert payload["visao_mensal"]["receita"][2] is None
    completo = client.get("/api/analise/dashboard/dre/mensal/", {"ano": 2026}, HTTP_HOST="localhost").json()
    assert completo["visao_mensal"]["receita"][8] == 170.0
    assert completo["visao_mensal"]["receita"][0] == 31.0

    StatusDreConsolidada.objects.filter(ano=2026, mes=2).delete()
    indisponivel = client.get("/api/analise/dashboard/dre/mensal/", params, HTTP_HOST="localhost")
    assert indisponivel.status_code == 503
    assert indisponivel.json()["periodos_pendentes"][0]["mes"] == 2
    assert client.get("/api/analise/dashboard/dre/mensal/", {"ano": 2026}, HTTP_HOST="localhost").status_code == 200


def test_dre_reconstrucao_falha_preserva_ultimo_snapshot(cenario_dre, monkeypatch):
    reconstruir_dre_mes(2026, 9)
    antes = DreDiarioConsolidada.objects.get(data=date(2026, 9, 25)).total_receita
    usuario = Usuario.objects.get(id_usuario=90)
    Venda.objects.create(id_legado=9013, tipo_documento=Venda.TIPO_NFCE,
                         data_venda=date(2026, 9, 25), usuario=usuario, valor_total_documento=Decimal("80"))

    def falhar(*args, **kwargs):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(DreDiarioConsolidada.objects, "bulk_create", falhar)
    with pytest.raises(RuntimeError):
        reconstruir_dre_mes(2026, 9)
    assert DreDiarioConsolidada.objects.get(data=date(2026, 9, 25)).total_receita == antes
    assert DreMensalConsolidada.objects.get(ano=2026, mes=9).total_receita == 120
    assert StatusDreConsolidada.objects.get(ano=2026, mes=9).status == "FALHA"


def test_dre_anual_equivalente_ajusta_29_de_fevereiro(cenario_dre):
    usuario = Usuario.objects.get(id_usuario=90)
    Venda.objects.create(id_legado=9014, tipo_documento=Venda.TIPO_NFCE,
                         data_venda=date(2023, 2, 28), usuario=usuario, valor_total_documento=Decimal("40"))
    Venda.objects.create(id_legado=9015, tipo_documento=Venda.TIPO_NFCE,
                         data_venda=date(2024, 2, 29), usuario=usuario, valor_total_documento=Decimal("50"))
    reconstruir_historico_dre()
    tipo = TipoDespesa.objects.create(nome="Despesa bissexta", chave="BISSEXTA")
    _snapshot_pagamento(2023, 1, tipo)
    _snapshot_pagamento(2023, 2, tipo, ((date(2023, 2, 28), 12),))
    _snapshot_pagamento(2024, 1, tipo)
    _snapshot_pagamento(2024, 2, tipo, ((date(2024, 2, 29), 20),))
    payload = APIClient().get("/api/analise/dashboard/dre/anual/",
                              {"ano": 2024, "periodo_equivalente": 1}, HTTP_HOST="localhost").json()
    assert payload["data_corte_atual"] == "2024-02-29"
    assert payload["data_corte_anterior"] == "2023-02-28"
    assert payload["visao_anual"]["receita"]["atual"] == 50.0
    assert payload["visao_anual"]["receita"]["anterior"] == 40.0
    assert payload["visao_anual"]["despesas"]["atual"] == 20.0
    assert payload["visao_anual"]["despesas"]["anterior"] == 12.0


def _snapshot_pagamento(ano, mes, tipo, eventos=()):
    inicio = date(ano, mes, 1)
    SnapshotDespesaMensal.objects.create(
        mes=inicio, base="PAGAMENTO", status="PRONTO", atualizado_em=timezone.now(),
        diario_atualizado_em=timezone.now(),
    )
    total = Decimal("0")
    for dia, valor in eventos:
        valor = Decimal(str(valor))
        AgregadoDespesaDiario.objects.create(dia=dia, tipo=tipo, base="PAGAMENTO", valor=valor)
        total += valor
    if total:
        AgregadoDespesaMensal.objects.create(mes=inicio, tipo=tipo, base="PAGAMENTO", valor=total)


def test_dre_usa_pagamentos_sem_subtrair_compras_duas_vezes(cenario_dre, monkeypatch):
    monkeypatch.setattr("apps.analise.services_dre.timezone.localdate", lambda: date(2026, 9, 26))
    monkeypatch.setattr("apps.analise.services.timezone.localdate", lambda: date(2026, 9, 26))
    assert not reconstruir_historico_dre()["falhas"]
    tipo = TipoDespesa.objects.create(nome="Despesas gerais", chave="GERAIS")
    for ano, limite in ((2025, 12), (2026, 9)):
        for mes in range(1, limite + 1):
            eventos = ()
            if (ano, mes) == (2025, 9):
                eventos = ((date(2025, 9, 20), 30),)
            if (ano, mes) == (2026, 9):
                eventos = ((date(2026, 9, 20), 40), (date(2026, 9, 26), 10))
            _snapshot_pagamento(ano, mes, tipo, eventos)

    client = APIClient()
    anual = client.get("/api/analise/dashboard/dre/anual/", {"ano": 2026, "periodo_equivalente": 1}, HTTP_HOST="localhost").json()
    assert anual["data_corte_atual"] == "2026-09-25"
    assert anual["visao_anual"]["custo"]["atual"] == 60.0
    assert anual["visao_anual"]["compras"]["atual"] == 60.0
    assert anual["visao_anual"]["despesas"]["atual"] == 40.0
    assert anual["visao_anual"]["despesas"]["anterior"] == 30.0
    assert anual["visao_anual"]["resultado"]["atual"] == 80.0
    assert anual["visao_anual"]["resultado_percentual"]["atual"] == 66.67
    assert anual["visao_anual"]["fator_retorno"]["atual"] == 3.0

    mensal = client.get("/api/analise/dashboard/dre/mensal/", {"ano": 2026, "periodo_equivalente": 1}, HTTP_HOST="localhost").json()
    assert mensal["visao_mensal"]["despesas"][8] == 40.0
    assert mensal["visao_mensal"]["compras"][8] == 60.0
    assert mensal["total_resultado_disponivel"] is True
    completo = client.get("/api/analise/dashboard/dre/mensal/", {"ano": 2026}, HTTP_HOST="localhost").json()
    assert completo["visao_mensal"]["despesas"][8] == 50.0


def test_dre_snapshot_ausente_nao_vira_zero_e_pagamento_sem_venda(cenario_dre, monkeypatch):
    monkeypatch.setattr("apps.analise.services_dre.timezone.localdate", lambda: date(2026, 9, 26))
    assert not reconstruir_historico_dre()["falhas"]
    tipo = TipoDespesa.objects.create(nome="Despesas gerais", chave="GERAIS")
    for mes in range(1, 10):
        eventos = ((date(2026, 2, 5), 20),) if mes == 2 else ()
        _snapshot_pagamento(2026, mes, tipo, eventos)

    client = APIClient()
    mensal = client.get("/api/analise/dashboard/dre/mensal/", {"ano": 2026}, HTTP_HOST="localhost").json()
    assert mensal["visao_mensal"]["receita"][1] == 0.0
    assert mensal["visao_mensal"]["despesas"][1] == 20.0
    assert mensal["total_resultado_disponivel"] is True

    SnapshotDespesaMensal.objects.filter(mes=date(2026, 8, 1), base="PAGAMENTO").delete()
    SnapshotDespesaMensal.objects.filter(mes=date(2026, 7, 1), base="PAGAMENTO").update(status="FALHO")
    parcial = client.get("/api/analise/dashboard/dre/mensal/", {"ano": 2026}, HTTP_HOST="localhost")
    assert parcial.status_code == 200
    payload = parcial.json()
    assert payload["visao_mensal"]["despesas"][7] is None
    assert payload["visao_mensal"]["despesas"][8] == 0.0
    assert payload["total_resultado_disponivel"] is False
    assert {"ano": 2026, "mes": 8, "status": "AUSENTE"} in payload["periodos_despesas_pendentes"]
    assert {"ano": 2026, "mes": 7, "status": "FALHO"} in payload["periodos_despesas_pendentes"]
    anual = client.get("/api/analise/dashboard/dre/anual/", {"ano": 2026}, HTTP_HOST="localhost")
    assert anual.status_code == 200
    assert anual.json()["visao_anual"]["resultado"]["atual"] is None


def test_dre_reflete_pagamento_reconstruido_sem_reprocessar_vendas(cenario_dre):
    assert not reconstruir_historico_dre()["falhas"]
    tipo = TipoDespesa.objects.create(nome="Despesa atualizada", chave="ATUALIZADA")
    movimento = MovimentoDespesa.objects.create(
        tipo=tipo, vencimento=date(2026, 9, 20), valor=Decimal("100"),
    )
    pagamento = PagamentoDespesa.objects.create(
        movimento=movimento, data=date(2026, 9, 20), valor=Decimal("40"),
    )
    reconstruir_despesas_mes(date(2026, 9, 1), "PAGAMENTO")
    client = APIClient()
    url = "/api/analise/dashboard/dre/mensal/"
    antes = client.get(url, {"ano": 2026}, HTTP_HOST="localhost").json()
    assert antes["visao_mensal"]["despesas"][8] == 40.0
    assert antes["visao_mensal"]["custo"][8] == 60.0

    pagamento.valor = Decimal("55")
    pagamento.save(update_fields=["valor"])
    reconstruir_despesas_mes(date(2026, 9, 1), "PAGAMENTO")
    depois = client.get(url, {"ano": 2026}, HTTP_HOST="localhost").json()
    assert depois["visao_mensal"]["despesas"][8] == 55.0
    assert depois["visao_mensal"]["custo"][8] == 60.0
    assert DreMensalConsolidada.objects.get(ano=2026, mes=9).total_receita == 120
