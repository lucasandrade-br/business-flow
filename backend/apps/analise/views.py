import calendar
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.db.models import Max, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.cadastros.models import Fornecedor, PlanoConta
from apps.compras.models import Compra
from apps.vendas.models import Venda

from .models import (
    DashboardKpiVenda,
    DashboardKpiCompra,
    DreMensalConsolidada,
    MovimentoCompraProdutoMensal,
    MovimentoDiario,
    MovimentoProdutoMensal,
)
from .services import (
    CategoriasAmbiguasError,
    detectar_mes_aberto,
    montar_analise_compras_categorias,
    montar_analise_compras_produtos,
    montar_analise_vendas_categorias,
    montar_analise_vendas_produtos,
    status_agregados_compras,
    status_agregados_vendas,
)

_DIAS_LABELS = ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SAB"]


@require_GET
def vendas_por_categorias(request):
    ano_raw = request.GET.get("ano")
    raiz_raw = request.GET.get("raiz_id")
    metrica = str(request.GET.get("metrica") or "").strip().lower()

    if ano_raw is None and raiz_raw is None and not metrica:
        return JsonResponse(status_agregados_vendas())

    if ano_raw is None or raiz_raw is None or not metrica:
        return JsonResponse(
            {"detail": "Informe os parametros 'ano', 'raiz_id' e 'metrica'."},
            status=400,
        )
    try:
        ano = int(ano_raw)
        raiz_id = int(raiz_raw)
    except (TypeError, ValueError):
        return JsonResponse({"detail": "Os parametros 'ano' e 'raiz_id' devem ser inteiros."}, status=400)
    if metrica not in {"valor", "quantidade"}:
        return JsonResponse({"detail": "Metrica invalida. Use 'valor' ou 'quantidade'."}, status=400)

    try:
        payload = montar_analise_vendas_categorias(ano=ano, raiz_id=raiz_id, metrica=metrica)
    except CategoriasAmbiguasError as exc:
        return JsonResponse(
            {
                "detail": "Existem produtos vinculados a mais de uma categoria folha desta familia.",
                "produtos_conflitantes": exc.produtos,
            },
            status=409,
        )
    except MovimentoProdutoMensal.DoesNotExist:
        return JsonResponse({"detail": "Ano sem dados analiticos disponiveis."}, status=404)
    except PlanoConta.DoesNotExist:
        return JsonResponse({"detail": "Familia raiz nao encontrada."}, status=404)

    return JsonResponse(payload)


@require_GET
def vendas_por_produtos(request):
    ano_raw = request.GET.get("ano")
    raiz_raw = request.GET.get("raiz_id")
    categoria_raw = request.GET.get("categoria_id")
    metrica = str(request.GET.get("metrica") or "").strip().lower()
    page_raw = request.GET.get("page", "1")
    incluir_inativos = str(request.GET.get("incluir_inativos") or "").strip().lower() in {
        "1", "true", "on", "sim", "yes"
    }

    if ano_raw is None or raiz_raw is None or categoria_raw is None or not metrica:
        return JsonResponse(
            {"detail": "Informe os parametros 'ano', 'raiz_id', 'categoria_id' e 'metrica'."},
            status=400,
        )
    try:
        ano = int(ano_raw)
        raiz_id = int(raiz_raw)
        categoria_id = int(categoria_raw)
        pagina = int(page_raw)
    except (TypeError, ValueError):
        return JsonResponse(
            {"detail": "Os parametros 'ano', 'raiz_id', 'categoria_id' e 'page' devem ser inteiros."},
            status=400,
        )
    if metrica not in {"valor", "quantidade"}:
        return JsonResponse({"detail": "Metrica invalida. Use 'valor' ou 'quantidade'."}, status=400)

    try:
        payload = montar_analise_vendas_produtos(
            ano=ano,
            raiz_id=raiz_id,
            categoria_id=categoria_id,
            metrica=metrica,
            incluir_inativos=incluir_inativos,
            search=request.GET.get("search", ""),
            pagina=pagina,
        )
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    except MovimentoProdutoMensal.DoesNotExist:
        return JsonResponse({"detail": "Ano sem dados analiticos disponiveis."}, status=404)
    except PlanoConta.DoesNotExist:
        return JsonResponse({"detail": "Familia ou categoria nao encontrada."}, status=404)

    return JsonResponse(payload)


def _fornecedor_id_parametro(request):
    fornecedor_raw = request.GET.get("fornecedor_id")
    if fornecedor_raw in (None, ""):
        return None
    return int(fornecedor_raw)


@require_GET
def compras_por_categorias(request):
    ano_raw = request.GET.get("ano")
    raiz_raw = request.GET.get("raiz_id")
    metrica = str(request.GET.get("metrica") or "").strip().lower()

    if ano_raw is None and raiz_raw is None and not metrica and not request.GET.get("fornecedor_id"):
        return JsonResponse(status_agregados_compras())
    if ano_raw is None or raiz_raw is None or not metrica:
        return JsonResponse(
            {"detail": "Informe os parametros 'ano', 'raiz_id' e 'metrica'."},
            status=400,
        )
    try:
        ano = int(ano_raw)
        raiz_id = int(raiz_raw)
        fornecedor_id = _fornecedor_id_parametro(request)
    except (TypeError, ValueError):
        return JsonResponse(
            {"detail": "Os parametros 'ano', 'raiz_id' e 'fornecedor_id' devem ser inteiros."},
            status=400,
        )
    if metrica not in {"valor", "quantidade"}:
        return JsonResponse({"detail": "Metrica invalida. Use 'valor' ou 'quantidade'."}, status=400)

    try:
        payload = montar_analise_compras_categorias(
            ano=ano,
            raiz_id=raiz_id,
            metrica=metrica,
            fornecedor_id=fornecedor_id,
        )
    except CategoriasAmbiguasError as exc:
        return JsonResponse(
            {
                "detail": "Existem produtos vinculados a mais de uma categoria folha desta familia.",
                "produtos_conflitantes": exc.produtos,
            },
            status=409,
        )
    except MovimentoCompraProdutoMensal.DoesNotExist:
        return JsonResponse({"detail": "Ano sem dados analiticos disponiveis."}, status=404)
    except PlanoConta.DoesNotExist:
        return JsonResponse({"detail": "Familia raiz nao encontrada."}, status=404)
    except Fornecedor.DoesNotExist:
        return JsonResponse({"detail": "Fornecedor nao encontrado."}, status=404)

    return JsonResponse(payload)


@require_GET
def compras_por_produtos(request):
    ano_raw = request.GET.get("ano")
    raiz_raw = request.GET.get("raiz_id")
    categoria_raw = request.GET.get("categoria_id")
    metrica = str(request.GET.get("metrica") or "").strip().lower()
    page_raw = request.GET.get("page", "1")
    incluir_inativos = str(request.GET.get("incluir_inativos") or "").strip().lower() in {
        "1", "true", "on", "sim", "yes"
    }

    if ano_raw is None or raiz_raw is None or categoria_raw is None or not metrica:
        return JsonResponse(
            {"detail": "Informe os parametros 'ano', 'raiz_id', 'categoria_id' e 'metrica'."},
            status=400,
        )
    try:
        ano = int(ano_raw)
        raiz_id = int(raiz_raw)
        categoria_id = int(categoria_raw)
        pagina = int(page_raw)
        fornecedor_id = _fornecedor_id_parametro(request)
    except (TypeError, ValueError):
        return JsonResponse(
            {
                "detail": (
                    "Os parametros 'ano', 'raiz_id', 'categoria_id', 'fornecedor_id' e 'page' "
                    "devem ser inteiros."
                )
            },
            status=400,
        )
    if metrica not in {"valor", "quantidade", "custo_medio"}:
        return JsonResponse(
            {"detail": "Metrica invalida. Use 'valor', 'quantidade' ou 'custo_medio'."},
            status=400,
        )

    try:
        payload = montar_analise_compras_produtos(
            ano=ano,
            raiz_id=raiz_id,
            categoria_id=categoria_id,
            metrica=metrica,
            fornecedor_id=fornecedor_id,
            incluir_inativos=incluir_inativos,
            search=request.GET.get("search", ""),
            pagina=pagina,
        )
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    except MovimentoCompraProdutoMensal.DoesNotExist:
        return JsonResponse({"detail": "Ano sem dados analiticos disponiveis."}, status=404)
    except PlanoConta.DoesNotExist:
        return JsonResponse({"detail": "Familia ou categoria nao encontrada."}, status=404)
    except Fornecedor.DoesNotExist:
        return JsonResponse({"detail": "Fornecedor nao encontrado."}, status=404)

    return JsonResponse(payload)


def _dia_semana(d):
    """Normaliza para DOM=0 ... SAB=6 (Python usa SEG=0)."""
    return (d.weekday() + 1) % 7


@require_GET
def dashboard_kpis(request):
    try:
        kpi = DashboardKpiVenda.objects.get(id=1)
    except DashboardKpiVenda.DoesNotExist:
        return JsonResponse({"detail": "KPIs ainda nao calculados."}, status=404)

    graficos = kpi.dados_periodicos_grafico or {"mensal": [], "semanal": []}

    def _periodos_fechados(granularidade):
        return sum(1 for item in graficos.get(granularidade, []) if not item.get("parcial"))

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
        "faturamento_medio": {
            "semanal": {
                "atual": str(kpi.faturamento_semanal_medio_atual),
                "anterior_equivalente": str(kpi.faturamento_semanal_medio_anterior_equivalente),
                "periodos_considerados": _periodos_fechados("semanal"),
            },
            "mensal": {
                "atual": str(kpi.faturamento_mensal_medio_atual),
                "anterior_equivalente": str(kpi.faturamento_mensal_medio_anterior_equivalente),
                "periodos_considerados": _periodos_fechados("mensal"),
            },
        },
        "graficos": graficos,
        "vendas_sem_horario": {
            "quantidade": kpi.volume_sem_horario_atual,
            "faturamento": str(kpi.faturamento_sem_horario_atual),
        },
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
    periodo_equivalente_solicitado = str(
        request.GET.get("periodo_equivalente") or ""
    ).strip().lower() in {"1", "true", "on", "sim", "yes"}
    ultima_venda = (
        Venda.objects.filter(data_venda__year=ano)
        .exclude(status="C")
        .aggregate(ultima=Max("data_venda"))["ultima"]
    )
    ultima_compra = (
        Compra.objects.filter(data_emissao__year=ano)
        .exclude(nfe_status__iexact="CANCELADA")
        .aggregate(ultima=Max("data_emissao"))["ultima"]
    )
    datas_disponiveis = [data for data in (ultima_venda, ultima_compra) if data is not None]
    ultima_data_disponivel = max(datas_disponiveis) if datas_disponiveis else None
    mes_aberto = detectar_mes_aberto(ano, ultima_data_disponivel)

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
    data_corte_atual = None
    data_corte_anterior = None
    periodo_equivalente_aplicado = False

    if periodo_equivalente_solicitado:
        if datas_disponiveis:
            data_corte_atual = ultima_data_disponivel
            ultimo_dia_anterior = calendar.monthrange(ano_anterior, data_corte_atual.month)[1]
            data_corte_anterior = date(
                ano_anterior,
                data_corte_atual.month,
                min(data_corte_atual.day, ultimo_dia_anterior),
            )

            rec_a = (
                Venda.objects.filter(
                    data_venda__gte=date(ano, 1, 1),
                    data_venda__lte=data_corte_atual,
                )
                .exclude(status="C")
                .aggregate(total=Sum("valor_total_documento"))["total"]
                or Decimal("0")
            )
            cst_a = (
                Compra.objects.filter(
                    data_emissao__gte=date(ano, 1, 1),
                    data_emissao__lte=data_corte_atual,
                )
                .exclude(nfe_status__iexact="CANCELADA")
                .aggregate(total=Sum("valor_total_documento"))["total"]
                or Decimal("0")
            )
            rec_b = (
                Venda.objects.filter(
                    data_venda__gte=date(ano_anterior, 1, 1),
                    data_venda__lte=data_corte_anterior,
                )
                .exclude(status="C")
                .aggregate(total=Sum("valor_total_documento"))["total"]
                or Decimal("0")
            )
            cst_b = (
                Compra.objects.filter(
                    data_emissao__gte=date(ano_anterior, 1, 1),
                    data_emissao__lte=data_corte_anterior,
                )
                .exclude(nfe_status__iexact="CANCELADA")
                .aggregate(total=Sum("valor_total_documento"))["total"]
                or Decimal("0")
            )
            periodo_equivalente_aplicado = True

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
        "periodo_equivalente": periodo_equivalente_aplicado,
        "data_corte_atual": data_corte_atual.isoformat() if data_corte_atual else None,
        "data_corte_anterior": data_corte_anterior.isoformat() if data_corte_anterior else None,
        "ultima_data_disponivel": ultima_data_disponivel.isoformat() if ultima_data_disponivel else None,
        "mes_aberto": mes_aberto,
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


@require_GET
def movimento_clientes(request):
    anos_disponiveis = sorted(
        {d.year for d in MovimentoDiario.objects.values_list("data", flat=True)},
        reverse=True,
    )

    tipos_disponiveis = [
        {"id": r["tipo_venda_id"], "descricao": r["tipo_venda_nome"]}
        for r in MovimentoDiario.objects
        .values("tipo_venda_id", "tipo_venda_nome")
        .distinct()
        .order_by("tipo_venda_id")
    ]

    ano_param = request.GET.get("ano")
    if not ano_param:
        if not anos_disponiveis:
            return JsonResponse({"detail": "Nenhum dado disponível."}, status=404)
        return JsonResponse({
            "anos_disponiveis": anos_disponiveis,
            "tipos_disponiveis": tipos_disponiveis,
        })

    try:
        ano = int(ano_param)
    except (ValueError, TypeError):
        return JsonResponse({"detail": "Parâmetro 'ano' inválido."}, status=400)

    qs = MovimentoDiario.objects.filter(data__year__in=[ano, ano - 1])

    tipos_param = str(request.GET.get("tipos") or "").strip()
    if tipos_param:
        try:
            tipos_ids = [int(t) for t in tipos_param.split(",") if t.strip() != ""]
        except (ValueError, TypeError):
            return JsonResponse({"detail": "Parâmetro 'tipos' inválido."}, status=400)
        if tipos_ids:
            qs = qs.filter(tipo_venda_id__in=tipos_ids)

    # Consolida por data, somando os tipos selecionados.
    por_data = defaultdict(lambda: {"qtd": 0, "valor": 0.0})
    for data, qtd, valor in qs.values_list("data", "qtd_vendas", "valor_total"):
        acc = por_data[data]
        acc["qtd"] += qtd or 0
        acc["valor"] += float(valor or 0)

    meses_com_dados = sorted({d.month for d in por_data if d.year == ano})
    if not meses_com_dados:
        return JsonResponse({
            "anos_disponiveis": anos_disponiveis,
            "tipos_disponiveis": tipos_disponiveis,
            "ano_consultado": ano,
            "mes_consultado": None,
            "meses_com_dados": [],
            "matriz_semanal": [],
            "detalhe_mensal": [],
        })

    mes_param = request.GET.get("mes")
    try:
        mes = int(mes_param) if mes_param else meses_com_dados[-1]
    except (ValueError, TypeError):
        return JsonResponse({"detail": "Parâmetro 'mes' inválido."}, status=400)
    if mes not in meses_com_dados:
        mes = meses_com_dados[-1]

    # ── Matriz semanal: [dia_da_semana][mes] ────────────────────────────────
    grade_atual = defaultdict(int)
    grade_anterior = defaultdict(int)
    ocor_atual = defaultdict(int)
    ocor_anterior = defaultdict(int)
    for data, acc in por_data.items():
        chave = (_dia_semana(data), data.month)
        if data.year == ano:
            grade_atual[chave] += acc["qtd"]
            ocor_atual[chave] += 1
        else:
            grade_anterior[chave] += acc["qtd"]
            ocor_anterior[chave] += 1

    def _pct(a, b):
        return round((a - b) / b * 100, 1) if b else None

    n_meses = len(meses_com_dados)
    matriz_semanal = []
    for dia in range(7):
        meses_soma = []
        meses_media = []
        for m in range(1, 13):
            if m not in meses_com_dados:
                meses_soma.append(None)
                meses_media.append(None)
                continue
            soma = grade_atual.get((dia, m))
            ocor = ocor_atual.get((dia, m), 0)
            meses_soma.append(soma)
            meses_media.append(round(soma / ocor, 1) if soma is not None and ocor else None)

        # Ano anterior usa o mesmo conjunto de meses (corte justo).
        soma_atual = sum(grade_atual.get((dia, m), 0) for m in meses_com_dados)
        soma_ant = sum(grade_anterior.get((dia, m), 0) for m in meses_com_dados)
        # Denominador da média diária: dias efetivamente operados, não dias de calendário.
        oc_atual = sum(ocor_atual.get((dia, m), 0) for m in meses_com_dados)
        oc_ant = sum(ocor_anterior.get((dia, m), 0) for m in meses_com_dados)

        media_soma = soma_atual / n_meses
        media_soma_ant = soma_ant / n_meses
        media_dia = soma_atual / oc_atual if oc_atual else 0
        media_dia_ant = soma_ant / oc_ant if oc_ant else 0

        matriz_semanal.append({
            "dia": dia,
            "label": _DIAS_LABELS[dia],
            "meses_soma": meses_soma,
            "meses_media": meses_media,
            "media_soma": round(media_soma, 1),
            "media_soma_anterior": round(media_soma_ant, 1),
            "variacao_soma": _pct(media_soma, media_soma_ant),
            "media_dia": round(media_dia, 1),
            "media_dia_anterior": round(media_dia_ant, 1),
            "variacao_dia": _pct(media_dia, media_dia_ant),
        })

    # ── Detalhe do mês selecionado, agrupado por dia da semana ──────────────
    grupos = defaultdict(list)
    for data, acc in sorted(por_data.items()):
        if data.year != ano or data.month != mes:
            continue
        qtd, valor = acc["qtd"], acc["valor"]
        grupos[_dia_semana(data)].append({
            "data": data.isoformat(),
            "dia": data.day,
            "qtd": qtd,
            "valor": round(valor, 2),
            "ticket": round(valor / qtd, 2) if qtd else None,
        })

    detalhe_mensal = []
    for dia in range(7):
        ocorrencias = grupos.get(dia, [])
        n = len(ocorrencias)
        soma_qtd = sum(o["qtd"] for o in ocorrencias)
        soma_valor = sum(o["valor"] for o in ocorrencias)
        detalhe_mensal.append({
            "dia": dia,
            "label": _DIAS_LABELS[dia],
            "ocorrencias": ocorrencias,
            "media_qtd": round(soma_qtd / n, 1) if n else None,
            "media_valor": round(soma_valor / n, 2) if n else None,
            "media_ticket": round(soma_valor / soma_qtd, 2) if soma_qtd else None,
        })

    return JsonResponse({
        "anos_disponiveis": anos_disponiveis,
        "tipos_disponiveis": tipos_disponiveis,
        "ano_consultado": ano,
        "mes_consultado": mes,
        "meses_com_dados": meses_com_dados,
        "matriz_semanal": matriz_semanal,
        "detalhe_mensal": detalhe_mensal,
    })
