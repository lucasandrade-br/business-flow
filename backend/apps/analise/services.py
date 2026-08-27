import calendar
from decimal import Decimal
from datetime import date

from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth

from apps.cadastros.models import TipoVenda
from apps.compras.models import Compra, ItemCompra
from apps.vendas.models import Venda
from apps.analise.models import (
    DashboardKpiVenda,
    DashboardKpiCompra,
    DreMensalConsolidada,
    MovimentoDiario,
)

_MESES_LABELS = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
_STATUS_CANCELADO = "C"
_STATUS_CANCELADA_COMPRA = "CANCELADA"


def processar_kpis_dashboard() -> None:
    """Consolida KPIs de vendas no singleton DashboardKpiVenda. Operação idempotente."""
    qs = Venda.objects.exclude(status=_STATUS_CANCELADO)

    try:
        ultima_data: date = qs.latest("data_venda").data_venda
    except Venda.DoesNotExist:
        return

    ano_atual = ultima_data.year
    ano_anterior = ano_atual - 1
    mes_atual = ultima_data.month
    dia_atual = ultima_data.day

    # ── YTD ─────────────────────────────────────────────────────────────────
    # Corte justo: 01/Jan até ultima_data em ambos os anos
    max_dia_ytd_ant = calendar.monthrange(ano_anterior, mes_atual)[1]
    fim_ytd_ant = date(ano_anterior, mes_atual, min(dia_atual, max_dia_ytd_ant))

    ytd_a = qs.filter(
        data_venda__gte=date(ano_atual, 1, 1),
        data_venda__lte=ultima_data,
    ).aggregate(receita=Sum("valor_total_documento"), volume=Count("id_venda"))

    ytd_b = qs.filter(
        data_venda__gte=date(ano_anterior, 1, 1),
        data_venda__lte=fim_ytd_ant,
    ).aggregate(receita=Sum("valor_total_documento"), volume=Count("id_venda"))

    receita_ytd_a = ytd_a["receita"] or Decimal("0")
    volume_ytd_a = ytd_a["volume"] or 0
    receita_ytd_b = ytd_b["receita"] or Decimal("0")
    volume_ytd_b = ytd_b["volume"] or 0

    ticket_a = receita_ytd_a / volume_ytd_a if volume_ytd_a else Decimal("0")
    ticket_b = receita_ytd_b / volume_ytd_b if volume_ytd_b else Decimal("0")

    # ── MTD ─────────────────────────────────────────────────────────────────
    max_dia_mtd_ant = calendar.monthrange(ano_anterior, mes_atual)[1]
    fim_mtd_ant = date(ano_anterior, mes_atual, min(dia_atual, max_dia_mtd_ant))

    mtd_a = qs.filter(
        data_venda__gte=date(ano_atual, mes_atual, 1),
        data_venda__lte=ultima_data,
    ).aggregate(receita=Sum("valor_total_documento"))

    mtd_b = qs.filter(
        data_venda__gte=date(ano_anterior, mes_atual, 1),
        data_venda__lte=fim_mtd_ant,
    ).aggregate(receita=Sum("valor_total_documento"))

    # ── Dados mensais para o gráfico ────────────────────────────────────────
    meses_ant = {
        row["mes"].month: row
        for row in qs.filter(data_venda__year=ano_anterior)
        .annotate(mes=TruncMonth("data_venda"))
        .values("mes")
        .annotate(receita=Sum("valor_total_documento"), volume=Count("id_venda"))
    }

    meses_atu = {
        row["mes"].month: row
        for row in qs.filter(data_venda__year=ano_atual)
        .annotate(mes=TruncMonth("data_venda"))
        .values("mes")
        .annotate(receita=Sum("valor_total_documento"), volume=Count("id_venda"))
    }

    dados_mensais = []
    for m in range(1, 13):
        ant = meses_ant.get(m)
        atu = meses_atu.get(m) if m <= mes_atual else None
        dados_mensais.append({
            "mes": m,
            "label": _MESES_LABELS[m - 1],
            "receita_atual": float(atu["receita"]) if atu and atu["receita"] else None,
            "volume_atual": atu["volume"] if atu else None,
            "receita_anterior": float(ant["receita"]) if ant and ant["receita"] else None,
            "volume_anterior": ant["volume"] if ant else None,
        })

    # ── Salva o registro único (id=1) ────────────────────────────────────────
    DashboardKpiVenda.objects.update_or_create(
        id=1,
        defaults={
            "ytd_receita_atual": receita_ytd_a,
            "ytd_receita_anterior_equivalente": receita_ytd_b,
            "ytd_volume_atual": volume_ytd_a,
            "ytd_volume_anterior_equivalente": volume_ytd_b,
            "ticket_medio_atual": ticket_a,
            "ticket_medio_anterior_equivalente": ticket_b,
            "mtd_receita_atual": mtd_a["receita"] or Decimal("0"),
            "mtd_receita_anterior_equivalente": mtd_b["receita"] or Decimal("0"),
            "dados_mensais_grafico": dados_mensais,
            "ultima_data_processada": ultima_data,
        },
    )


def processar_kpis_compras() -> None:
    """Consolida KPIs de compras no singleton DashboardKpiCompra. Operação idempotente."""
    qs = Compra.objects.exclude(nfe_status=_STATUS_CANCELADA_COMPRA)

    try:
        ultima_data: date = qs.latest("data_emissao").data_emissao
    except Compra.DoesNotExist:
        return

    ano_atual = ultima_data.year
    ano_anterior = ano_atual - 1
    mes_atual = ultima_data.month
    dia_atual = ultima_data.day

    # ── YTD ──────────────────────────────────────────────────────────────
    max_dia_ytd_ant = calendar.monthrange(ano_anterior, mes_atual)[1]
    fim_ytd_ant = date(ano_anterior, mes_atual, min(dia_atual, max_dia_ytd_ant))

    ytd_a = qs.filter(
        data_emissao__gte=date(ano_atual, 1, 1),
        data_emissao__lte=ultima_data,
    ).aggregate(custo=Sum("valor_total_documento"))

    ytd_b = qs.filter(
        data_emissao__gte=date(ano_anterior, 1, 1),
        data_emissao__lte=fim_ytd_ant,
    ).aggregate(custo=Sum("valor_total_documento"))

    custo_ytd_a = ytd_a["custo"] or Decimal("0")
    custo_ytd_b = ytd_b["custo"] or Decimal("0")

    # ── MTD ──────────────────────────────────────────────────────────────
    max_dia_mtd_ant = calendar.monthrange(ano_anterior, mes_atual)[1]
    fim_mtd_ant = date(ano_anterior, mes_atual, min(dia_atual, max_dia_mtd_ant))

    mtd_a = qs.filter(
        data_emissao__gte=date(ano_atual, mes_atual, 1),
        data_emissao__lte=ultima_data,
    ).aggregate(custo=Sum("valor_total_documento"))

    mtd_b = qs.filter(
        data_emissao__gte=date(ano_anterior, mes_atual, 1),
        data_emissao__lte=fim_mtd_ant,
    ).aggregate(custo=Sum("valor_total_documento"))

    # ── Volume de itens (ItemCompra) ─────────────────────────────────────────
    qs_itens = ItemCompra.objects.exclude(compra__nfe_status=_STATUS_CANCELADA_COMPRA)

    vol_atual = qs_itens.filter(
        compra__data_emissao__gte=date(ano_atual, 1, 1),
        compra__data_emissao__lte=ultima_data,
    ).aggregate(vol=Count("id_item_compra"))

    vol_anterior = qs_itens.filter(
        compra__data_emissao__gte=date(ano_anterior, 1, 1),
        compra__data_emissao__lte=fim_ytd_ant,
    ).aggregate(vol=Count("id_item_compra"))

    # ── Fator de retorno (Receita / Custo) ─────────────────────────────────
    try:
        kpi_venda = DashboardKpiVenda.objects.get(id=1)
        receita_atual = Decimal(str(kpi_venda.ytd_receita_atual))
        receita_anterior = Decimal(str(kpi_venda.ytd_receita_anterior_equivalente))
    except DashboardKpiVenda.DoesNotExist:
        receita_atual = receita_anterior = Decimal("0")

    fator_atual = receita_atual / custo_ytd_a if custo_ytd_a else Decimal("0")
    fator_anterior = receita_anterior / custo_ytd_b if custo_ytd_b else Decimal("0")

    # ── Dados mensais para o gráfico ─────────────────────────────────────────
    meses_ant = {
        row["mes"].month: row
        for row in qs.filter(data_emissao__year=ano_anterior)
        .annotate(mes=TruncMonth("data_emissao"))
        .values("mes")
        .annotate(custo=Sum("valor_total_documento"), volume=Count("id_compra"))
    }

    meses_atu = {
        row["mes"].month: row
        for row in qs.filter(data_emissao__year=ano_atual)
        .annotate(mes=TruncMonth("data_emissao"))
        .values("mes")
        .annotate(custo=Sum("valor_total_documento"), volume=Count("id_compra"))
    }

    dados_mensais = []
    for m in range(1, 13):
        ant = meses_ant.get(m)
        atu = meses_atu.get(m) if m <= mes_atual else None
        dados_mensais.append({
            "mes": m,
            "label": _MESES_LABELS[m - 1],
            "custo_atual": float(atu["custo"]) if atu and atu["custo"] else None,
            "volume_atual": atu["volume"] if atu else None,
            "custo_anterior": float(ant["custo"]) if ant and ant["custo"] else None,
            "volume_anterior": ant["volume"] if ant else None,
        })

    # ── Salva o registro único (id=1) ────────────────────────────────────────
    DashboardKpiCompra.objects.update_or_create(
        id=1,
        defaults={
            "ytd_custo_atual": custo_ytd_a,
            "ytd_custo_anterior_equivalente": custo_ytd_b,
            "mtd_custo_atual": mtd_a["custo"] or Decimal("0"),
            "mtd_custo_anterior_equivalente": mtd_b["custo"] or Decimal("0"),
            "fator_retorno_atual": fator_atual,
            "fator_retorno_anterior": fator_anterior,
            "volume_itens_atual": vol_atual["vol"] or 0,
            "volume_itens_anterior": vol_anterior["vol"] or 0,
            "dados_mensais_grafico": dados_mensais,
            "ultima_data_processada": ultima_data,
        },
    )


def atualizar_dre_consolidada() -> None:
    """Reconsolida toda a tabela DRE agregando vendas e compras por ano/mês."""
    vendas_por_mes = (
        Venda.objects
        .exclude(status=_STATUS_CANCELADO)
        .values("data_venda__year", "data_venda__month")
        .annotate(total=Sum("valor_total_documento"))
    )

    compras_por_mes = (
        Compra.objects
        .exclude(nfe_status=_STATUS_CANCELADA_COMPRA)
        .values("data_emissao__year", "data_emissao__month")
        .annotate(total=Sum("valor_total_documento"))
    )

    dre: dict = {}

    for row in vendas_por_mes:
        key = (row["data_venda__year"], row["data_venda__month"])
        dre.setdefault(key, {"receita": Decimal("0"), "custo": Decimal("0")})
        dre[key]["receita"] = row["total"] or Decimal("0")

    for row in compras_por_mes:
        key = (row["data_emissao__year"], row["data_emissao__month"])
        dre.setdefault(key, {"receita": Decimal("0"), "custo": Decimal("0")})
        dre[key]["custo"] = row["total"] or Decimal("0")

    for (ano, mes), vals in dre.items():
        DreMensalConsolidada.objects.update_or_create(
            ano=ano,
            mes=mes,
            defaults={
                "total_receita": vals["receita"],
                "total_custo":   vals["custo"],
            },
        )


def atualizar_movimento_diario() -> None:
    """Reconsolida o movimento por data e tipo de venda. Full refresh idempotente."""
    nomes_tipo = dict(TipoVenda.objects.values_list("id_tipo_venda", "descricao"))

    agregado = (
        Venda.objects
        .exclude(status=_STATUS_CANCELADO)
        .values("data_venda", "cliente__id_tipo_venda")
        .annotate(qtd=Count("id_venda"), valor=Sum("valor_total_documento"))
    )

    for row in agregado:
        tipo_id = row["cliente__id_tipo_venda"]
        if tipo_id is None:
            tipo_id = MovimentoDiario.SEM_TIPO_ID
            tipo_nome = MovimentoDiario.SEM_TIPO_NOME
        else:
            tipo_nome = nomes_tipo.get(tipo_id, f"Tipo {tipo_id}")

        MovimentoDiario.objects.update_or_create(
            data=row["data_venda"],
            tipo_venda_id=tipo_id,
            defaults={
                "tipo_venda_nome": tipo_nome,
                "qtd_vendas": row["qtd"] or 0,
                "valor_total": row["valor"] or Decimal("0"),
            },
        )
