"""Reconstrução e leitura das visões independentes do DRE gerencial."""

import calendar
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Max, Min, Sum
from django.utils import timezone

from apps.compras.models import Compra
from apps.despesas.models import AgregadoDespesaDiario, AgregadoDespesaMensal, SnapshotDespesaMensal
from apps.vendas.models import Venda

from .models import DreDiarioConsolidada, DreMensalConsolidada, StatusDreConsolidada
from .services import detectar_mes_aberto


ZERO = Decimal("0")


class DreAgregadoIncompletoError(Exception):
    def __init__(self, periodos: list[dict]):
        self.periodos = periodos
        super().__init__("Há períodos do DRE aguardando consolidação.")


def reconstruir_dre_mes(ano: int, mes: int) -> int:
    """Substitui diário e mensal juntos; uma falha mantém os snapshots anteriores."""
    if not 1 <= mes <= 12 or not 1 <= ano <= 9999:
        raise ValueError("Ano ou mês inválido para reconstrução do DRE.")
    inicio = date(ano, mes, 1)
    fim = date(ano, mes, calendar.monthrange(ano, mes)[1])
    estado, _ = StatusDreConsolidada.objects.get_or_create(ano=ano, mes=mes)
    estado.status = StatusDreConsolidada.STATUS_PROCESSANDO
    estado.erro = ""
    estado.save(update_fields=["status", "erro", "atualizado_em"])
    try:
        vendas = (
            Venda.objects.filter(data_venda__gte=inicio, data_venda__lte=fim)
            .exclude(status="C").values("data_venda")
            .annotate(total=Sum("valor_total_documento")).order_by()
        )
        compras = (
            Compra.objects.filter(data_emissao__gte=inicio, data_emissao__lte=fim)
            .exclude(nfe_status__iexact="CANCELADA").values("data_emissao")
            .annotate(total=Sum("valor_total_documento")).order_by()
        )
        diarios = defaultdict(lambda: {"receita": ZERO, "custo": ZERO})
        for item in vendas:
            diarios[item["data_venda"]]["receita"] = item["total"] or ZERO
        for item in compras:
            diarios[item["data_emissao"]]["custo"] = item["total"] or ZERO
        receita = sum((item["receita"] for item in diarios.values()), ZERO)
        custo = sum((item["custo"] for item in diarios.values()), ZERO)
        with transaction.atomic():
            DreDiarioConsolidada.objects.filter(data__gte=inicio, data__lte=fim).delete()
            DreDiarioConsolidada.objects.bulk_create([
                DreDiarioConsolidada(data=dia, total_receita=totais["receita"], total_custo=totais["custo"])
                for dia, totais in sorted(diarios.items())
            ])
            if diarios:
                DreMensalConsolidada.objects.update_or_create(
                    ano=ano, mes=mes, defaults={"total_receita": receita, "total_custo": custo},
                )
            else:
                DreMensalConsolidada.objects.filter(ano=ano, mes=mes).delete()
            estado.status = StatusDreConsolidada.STATUS_PRONTO
            estado.erro = ""
            estado.ultimo_sucesso_em = timezone.now()
            estado.save(update_fields=["status", "erro", "ultimo_sucesso_em", "atualizado_em"])
        return len(diarios)
    except Exception as exc:
        estado.status = StatusDreConsolidada.STATUS_FALHA
        estado.erro = str(exc)[:2000]
        estado.save(update_fields=["status", "erro", "atualizado_em"])
        raise


def reconstruir_historico_dre(*, somente_pendentes: bool = False, ano: int | None = None) -> dict:
    """Carrega todos os meses conhecidos e um ano anterior para o comparativo."""
    datas = [
        Venda.objects.exclude(status="C").aggregate(inicio=Min("data_venda"), fim=Max("data_venda")),
        Compra.objects.exclude(nfe_status__iexact="CANCELADA").aggregate(inicio=Min("data_emissao"), fim=Max("data_emissao")),
    ]
    anos_mensais = DreMensalConsolidada.objects.aggregate(inicio=Min("ano"), fim=Max("ano"))
    inicios = [item["inicio"] for item in datas if item["inicio"]]
    fins = [item["fim"] for item in datas if item["fim"]]
    if anos_mensais["inicio"]:
        inicios.append(date(anos_mensais["inicio"], 1, 1))
        fins.append(date(anos_mensais["fim"], 12, 31))
    if not inicios:
        return {"processados": 0, "falhas": []}
    ano_inicial = max(1, min(item.year for item in inicios) - 1)
    ultimo = max(fins)
    periodos = [
        (ano_periodo, mes)
        for ano_periodo in range(ano_inicial, ultimo.year + 1)
        for mes in range(1, 13)
        if (ano is None or ano_periodo == ano) and (ano_periodo, mes) <= (ultimo.year, ultimo.month)
    ]
    estados_prontos = set()
    if somente_pendentes:
        estados_prontos = set(StatusDreConsolidada.objects.filter(
            status=StatusDreConsolidada.STATUS_PRONTO, ultimo_sucesso_em__isnull=False,
        ).values_list("ano", "mes"))
    processados = 0
    falhas = []
    for ano_periodo, mes in periodos:
        if (ano_periodo, mes) in estados_prontos:
            continue
        try:
            reconstruir_dre_mes(ano_periodo, mes)
            processados += 1
        except Exception as exc:
            falhas.append({"ano": ano_periodo, "mes": mes, "erro": str(exc)})
    return {"processados": processados, "falhas": falhas}


def anos_disponiveis_dre() -> list[int]:
    return list(DreMensalConsolidada.objects.values_list("ano", flat=True).distinct().order_by("-ano"))


def _estado_periodos(periodos: list[tuple[int, int]]) -> tuple[list[dict], str | None]:
    estados = {
        (item.ano, item.mes): item
        for item in StatusDreConsolidada.objects.filter(ano__in={ano for ano, _ in periodos})
    }
    pendentes = []
    sucessos = []
    for ano, mes in periodos:
        estado = estados.get((ano, mes))
        if estado is None or estado.status != StatusDreConsolidada.STATUS_PRONTO or estado.ultimo_sucesso_em is None:
            pendentes.append({"ano": ano, "mes": mes, "status": estado.status if estado else "AUSENTE"})
        elif estado.ultimo_sucesso_em:
            sucessos.append(estado.ultimo_sucesso_em)
    atualizado_em = max(sucessos).isoformat() if sucessos else None
    return pendentes, atualizado_em


def _ultima_data_ano(ano: int) -> date | None:
    return DreDiarioConsolidada.objects.filter(data__year=ano).aggregate(ultima=Max("data"))["ultima"]


def _soma_diaria(inicio: date, fim: date) -> tuple[Decimal, Decimal]:
    totais = DreDiarioConsolidada.objects.filter(data__gte=inicio, data__lte=fim).aggregate(
        receita=Sum("total_receita"), custo=Sum("total_custo"),
    )
    return totais["receita"] or ZERO, totais["custo"] or ZERO


def _meses_entre(inicio: date, fim: date):
    ano, mes = inicio.year, inicio.month
    while (ano, mes) <= (fim.year, fim.month):
        yield ano, mes
        ano, mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)


def _snapshots_pagamentos(inicio: date, fim: date) -> dict:
    return {
        (item.mes.year, item.mes.month): item
        for item in SnapshotDespesaMensal.objects.filter(
            base="PAGAMENTO", mes__gte=date(inicio.year, inicio.month, 1),
            mes__lte=date(fim.year, fim.month, 1),
        )
    }


def _total_pagamentos(inicio: date, fim: date, snapshots: dict) -> tuple[Decimal | None, list[dict]]:
    """Lê somente snapshots prontos; cortes parciais exigem o diário pronto."""
    total = ZERO
    pendentes = []
    for ano, mes in _meses_entre(inicio, fim):
        primeiro = max(inicio, date(ano, mes, 1))
        ultimo = min(fim, date(ano, mes, calendar.monthrange(ano, mes)[1]))
        parcial = primeiro.day != 1 or ultimo.day != calendar.monthrange(ano, mes)[1]
        snapshot = snapshots.get((ano, mes))
        status = snapshot.status if snapshot else "AUSENTE"
        if status == "PRONTO" and parcial and not snapshot.diario_atualizado_em:
            status = "DIARIO_AUSENTE"
        if status != "PRONTO":
            pendentes.append({"ano": ano, "mes": mes, "status": status})
            continue
        if parcial:
            valor = AgregadoDespesaDiario.objects.filter(
                base="PAGAMENTO", dia__gte=primeiro, dia__lte=ultimo,
            ).aggregate(total=Sum("valor"))["total"]
        else:
            valor = AgregadoDespesaMensal.objects.filter(
                base="PAGAMENTO", mes=date(ano, mes, 1),
            ).aggregate(total=Sum("valor"))["total"]
        total += valor or ZERO
    return (None if pendentes else total), pendentes


def _ultimo_pagamento(ano: int) -> date | None:
    return AgregadoDespesaDiario.objects.filter(
        base="PAGAMENTO", dia__year=ano, dia__lte=timezone.localdate(),
    ).aggregate(ultimo=Max("dia"))["ultimo"]


def _base_ano(ano: int) -> dict:
    ultima = _ultima_data_ano(ano)
    mes_aberto = detectar_mes_aberto(ano, ultima)
    ultimo_mes = max(
        DreMensalConsolidada.objects.filter(ano=ano).aggregate(mes=Max("mes"))["mes"] or 0,
        ultima.month if ultima else 0,
    )
    periodos = [(ano, mes) for mes in range(1, ultimo_mes + 1)]
    pendentes, atualizado_em = _estado_periodos(periodos)
    return {
        "anos_disponiveis": anos_disponiveis_dre(), "ano_consultado": ano,
        "ultima_data_disponivel": ultima.isoformat() if ultima else None,
        "mes_aberto": mes_aberto, "desatualizado": bool(pendentes),
        "periodos_pendentes": pendentes, "atualizado_em": atualizado_em,
    }


def montar_dre_anual(*, ano: int, periodo_equivalente: bool) -> dict:
    base = _base_ano(ano)
    if periodo_equivalente and base["periodos_pendentes"]:
        raise DreAgregadoIncompletoError(base["periodos_pendentes"])
    anterior = ano - 1
    rows = {
        (item.ano, item.mes): item
        for item in DreMensalConsolidada.objects.filter(ano__in=[ano, anterior])
    }
    def soma_mensal(ano_periodo, campo):
        return sum((getattr(row, campo) for (ano_row, _), row in rows.items() if ano_row == ano_periodo), ZERO)

    rec_a, cst_a = soma_mensal(ano, "total_receita"), soma_mensal(ano, "total_custo")
    rec_b, cst_b = soma_mensal(anterior, "total_receita"), soma_mensal(anterior, "total_custo")
    corte_a = corte_b = None
    aplicado = False
    if periodo_equivalente and base["ultima_data_disponivel"]:
        corte_a = date.fromisoformat(base["ultima_data_disponivel"])
        corte_b = date(anterior, corte_a.month, min(corte_a.day, calendar.monthrange(anterior, corte_a.month)[1]))
        periodos = [
            (ano_periodo, mes)
            for ano_periodo in (anterior, ano)
            for mes in range(1, corte_a.month + 1)
        ]
        pendentes, _ = _estado_periodos(periodos)
        if pendentes:
            raise DreAgregadoIncompletoError(pendentes)
        rec_a, cst_a = _soma_diaria(date(ano, 1, 1), corte_a)
        rec_b, cst_b = _soma_diaria(date(anterior, 1, 1), corte_b)
        aplicado = True

    hoje = timezone.localdate()
    if aplicado:
        fim_atual, fim_anterior = corte_a, corte_b
    else:
        ultima_dre = date.fromisoformat(base["ultima_data_disponivel"]) if base["ultima_data_disponivel"] else None
        ultimo_pagamento = _ultimo_pagamento(ano)
        if ano == hoje.year:
            fim_atual = max((dia for dia in (ultima_dre, ultimo_pagamento) if dia), default=date(ano, 1, 1))
            fim_atual = min(fim_atual, hoje)
        else:
            fim_atual = date(ano, 12, 31)
        fim_anterior = date(anterior, 12, 31)
    snapshots = _snapshots_pagamentos(date(anterior, 1, 1), fim_atual)
    desp_a, pend_a = _total_pagamentos(date(ano, 1, 1), fim_atual, snapshots)
    desp_b, pend_b = _total_pagamentos(date(anterior, 1, 1), fim_anterior, snapshots)
    pendentes_despesas = pend_b + pend_a

    def diferenca(atual, anterior_valor):
        return {
            "atual": float(atual) if atual is not None else None,
            "anterior": float(anterior_valor) if anterior_valor is not None else None,
            "var_nominal": float(atual - anterior_valor) if atual is not None and anterior_valor is not None else None,
            "var_relativa": round(float((atual - anterior_valor) / anterior_valor * 100), 2)
            if atual is not None and anterior_valor not in (None, ZERO) else None,
        }

    res_a = rec_a - desp_a if desp_a is not None else None
    res_b = rec_b - desp_b if desp_b is not None else None
    base.update({
        "periodo_equivalente": aplicado,
        "data_corte_atual": corte_a.isoformat() if corte_a else None,
        "data_corte_anterior": corte_b.isoformat() if corte_b else None,
        "periodos_despesas_pendentes": pendentes_despesas,
        "despesas_incompletas": bool(pendentes_despesas),
        "cobertura_despesas_confirmada": False,
        "visao_anual": {
            "receita": diferenca(rec_a, rec_b),
            "custo": diferenca(cst_a, cst_b),
            "compras": diferenca(cst_a, cst_b),
            "despesas": diferenca(desp_a, desp_b),
            "resultado": diferenca(res_a, res_b),
            "resultado_percentual": {
                "atual": round(float(res_a / rec_a * 100), 2) if res_a is not None and rec_a else None,
                "anterior": round(float(res_b / rec_b * 100), 2) if res_b is not None and rec_b else None,
            },
            "fator_retorno": {
                "atual": round(float(rec_a / desp_a), 4) if desp_a not in (None, ZERO) else None,
                "anterior": round(float(rec_b / desp_b), 4) if desp_b not in (None, ZERO) else None,
            },
        },
    })
    return base


def montar_dre_mensal(*, ano: int, periodo_equivalente: bool) -> dict:
    base = _base_ano(ano)
    rows = {item.mes: item for item in DreMensalConsolidada.objects.filter(ano=ano)}
    if periodo_equivalente and ano == timezone.localdate().year and base["periodos_pendentes"]:
        raise DreAgregadoIncompletoError(base["periodos_pendentes"])
    receitas = [rows[mes].total_receita if mes in rows else None for mes in range(1, 13)]
    custos = [rows[mes].total_custo if mes in rows else None for mes in range(1, 13)]
    aplicado = bool(periodo_equivalente and base["mes_aberto"] and base["ultima_data_disponivel"])
    dia_corte = None
    if aplicado:
        foco = date.fromisoformat(base["ultima_data_disponivel"])
        dia_corte = foco.day
        periodos = [(ano, mes) for mes in range(1, foco.month + 1)]
        pendentes, _ = _estado_periodos(periodos)
        if pendentes:
            raise DreAgregadoIncompletoError(pendentes)
        for mes in range(1, foco.month + 1):
            if mes not in rows:
                continue
            fim = date(ano, mes, min(dia_corte, calendar.monthrange(ano, mes)[1]))
            receitas[mes - 1], custos[mes - 1] = _soma_diaria(date(ano, mes, 1), fim)
    hoje = timezone.localdate()
    pagamentos_mensais = {
        item["mes"].month: item["total"]
        for item in AgregadoDespesaMensal.objects.filter(base="PAGAMENTO", mes__year=ano, mes__lte=hoje)
        .values("mes").annotate(total=Sum("valor"))
    }
    estados_dre = {
        item.mes: item for item in StatusDreConsolidada.objects.filter(ano=ano)
    }
    meses_ativos = set(rows) | set(pagamentos_mensais)
    if aplicado:
        meses_ativos = {mes for mes in meses_ativos if mes <= foco.month}
    for mes in meses_ativos - set(rows):
        estado = estados_dre.get(mes)
        if estado and estado.status == StatusDreConsolidada.STATUS_PRONTO and estado.ultimo_sucesso_em:
            receitas[mes - 1] = custos[mes - 1] = ZERO
    ultimo_mes = max(meses_ativos, default=0)
    snapshots = _snapshots_pagamentos(date(ano, 1, 1), date(ano, max(ultimo_mes, 1), 1))
    despesas = [None] * 12
    pendentes_despesas = []
    for mes in range(1, ultimo_mes + 1):
        fim = date(ano, mes, min(dia_corte, calendar.monthrange(ano, mes)[1])) if aplicado else date(ano, mes, calendar.monthrange(ano, mes)[1])
        if ano == hoje.year and fim > hoje:
            fim = hoje
        if fim < date(ano, mes, 1):
            continue
        valor, pendentes = _total_pagamentos(date(ano, mes, 1), fim, snapshots)
        pendentes_despesas.extend(pendentes)
        if mes in meses_ativos:
            despesas[mes - 1] = valor
    base.update({
        "periodo_equivalente": aplicado, "dia_corte": dia_corte,
        "periodos_despesas_pendentes": pendentes_despesas,
        "despesas_incompletas": bool(pendentes_despesas),
        "cobertura_despesas_confirmada": False,
        "total_resultado_disponivel": not pendentes_despesas and all(
            receitas[mes - 1] is not None for mes in meses_ativos
        ),
        "visao_mensal": {
            "receita": [float(valor) if valor is not None else None for valor in receitas],
            "custo": [float(valor) if valor is not None else None for valor in custos],
            "compras": [float(valor) if valor is not None else None for valor in custos],
            "despesas": [float(valor) if valor is not None else None for valor in despesas],
        },
    })
    return base
