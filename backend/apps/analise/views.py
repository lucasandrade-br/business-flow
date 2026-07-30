from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import DashboardKpiVenda, DashboardKpiCompra, DreMensalConsolidada


@require_GET
def dashboard_kpis(request):
    try:
        kpi = DashboardKpiVenda.objects.get(id=1)
    except DashboardKpiVenda.DoesNotExist:
        return JsonResponse({"detail": "KPIs ainda nao calculados."}, status=404)

    return JsonResponse({
        "ytd_receita_atual": str(kpi.ytd_receita_atual),
        "ytd_receita_anterior_equivalente": str(kpi.ytd_receita_anterior_equivalente),
        "ytd_volume_atual": kpi.ytd_volume_atual,
        "ytd_volume_anterior_equivalente": kpi.ytd_volume_anterior_equivalente,
        "ticket_medio_atual": str(kpi.ticket_medio_atual),
        "ticket_medio_anterior_equivalente": str(kpi.ticket_medio_anterior_equivalente),
        "mtd_receita_atual": str(kpi.mtd_receita_atual),
        "mtd_receita_anterior_equivalente": str(kpi.mtd_receita_anterior_equivalente),
        "dados_mensais_grafico": kpi.dados_mensais_grafico,
        "ultima_data_processada": kpi.ultima_data_processada.isoformat() if kpi.ultima_data_processada else None,
        "atualizado_em": kpi.atualizado_em.isoformat(),
    })


@require_GET
def dashboard_kpis_compras(request):
    try:
        kpi = DashboardKpiCompra.objects.get(id=1)
    except DashboardKpiCompra.DoesNotExist:
        return JsonResponse({"detail": "KPIs de compras ainda não calculados."}, status=404)

    return JsonResponse({
        "ytd_custo_atual": str(kpi.ytd_custo_atual),
        "ytd_custo_anterior_equivalente": str(kpi.ytd_custo_anterior_equivalente),
        "mtd_custo_atual": str(kpi.mtd_custo_atual),
        "mtd_custo_anterior_equivalente": str(kpi.mtd_custo_anterior_equivalente),
        "fator_retorno_atual": str(kpi.fator_retorno_atual),
        "fator_retorno_anterior": str(kpi.fator_retorno_anterior),
        "volume_itens_atual": kpi.volume_itens_atual,
        "volume_itens_anterior": kpi.volume_itens_anterior,
        "dados_mensais_grafico": kpi.dados_mensais_grafico,
        "ultima_data_processada": kpi.ultima_data_processada.isoformat() if kpi.ultima_data_processada else None,
        "atualizado_em": kpi.atualizado_em.isoformat(),
    })


@require_GET
def dre_dashboard(request):
    anos_disponiveis = list(
        DreMensalConsolidada.objects
        .values_list("ano", flat=True)
        .distinct()
        .order_by("-ano")
    )

    ano_param = request.GET.get("ano")
    if not ano_param:
        if not anos_disponiveis:
            return JsonResponse({"detail": "Nenhum dado disponível."}, status=404)
        return JsonResponse({"anos_disponiveis": anos_disponiveis})

    try:
        ano = int(ano_param)
    except (ValueError, TypeError):
        return JsonResponse({"detail": "Parâmetro 'ano' inválido."}, status=400)

    ano_anterior = ano - 1

    rows = {
        (r.ano, r.mes): r
        for r in DreMensalConsolidada.objects.filter(ano__in=[ano, ano_anterior])
    }

    def _rec(a, m):
        return rows[(a, m)].total_receita if (a, m) in rows else None

    def _cst(a, m):
        return rows[(a, m)].total_custo if (a, m) in rows else None

    def _soma(a):
        rv = [rows[(a, m)].total_receita for m in range(1, 13) if (a, m) in rows]
        cv = [rows[(a, m)].total_custo   for m in range(1, 13) if (a, m) in rows]
        return (sum(rv) if rv else 0), (sum(cv) if cv else 0)

    def _var_nom(a, b):
        return float(a - b)

    def _var_rel(a, b):
        if not b:
            return None
        return round(float((a - b) / b * 100), 2)

    rec_a, cst_a = _soma(ano)
    rec_b, cst_b = _soma(ano_anterior)

    mg_a = rec_a - cst_a
    mg_b = rec_b - cst_b

    mgp_a = round(float(mg_a / rec_a * 100), 2) if rec_a else None
    mgp_b = round(float(mg_b / rec_b * 100), 2) if rec_b else None
    fat_a = round(float(rec_a / cst_a), 4) if cst_a else None
    fat_b = round(float(rec_b / cst_b), 4) if cst_b else None

    rec_meses = [_rec(ano, m) for m in range(1, 13)]
    cst_meses = [_cst(ano, m) for m in range(1, 13)]

    return JsonResponse({
        "anos_disponiveis": anos_disponiveis,
        "ano_consultado": ano,
        "visao_anual": {
            "receita": {
                "atual": float(rec_a), "anterior": float(rec_b),
                "var_nominal": _var_nom(rec_a, rec_b),
                "var_relativa": _var_rel(rec_a, rec_b),
            },
            "custo": {
                "atual": float(cst_a), "anterior": float(cst_b),
                "var_nominal": _var_nom(cst_a, cst_b),
                "var_relativa": _var_rel(cst_a, cst_b),
            },
            "margem_bruta": {
                "atual": float(mg_a), "anterior": float(mg_b),
                "var_nominal": _var_nom(mg_a, mg_b),
                "var_relativa": _var_rel(mg_a, mg_b),
            },
            "margem_percentual": {"atual": mgp_a, "anterior": mgp_b},
            "fator_retorno":     {"atual": fat_a, "anterior": fat_b},
        },
        "visao_mensal": {
            "receita": [float(v) if v is not None else None for v in rec_meses],
            "custo":   [float(v) if v is not None else None for v in cst_meses],
        },
    })
