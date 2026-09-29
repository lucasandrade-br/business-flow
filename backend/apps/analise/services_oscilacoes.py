"""Radar financeiro de oscilações em categorias folha, sobre snapshots persistidos."""

import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Max, Min, Sum

from apps.vendas.models import Venda

from .models import (
    MovimentoProdutoDiario,
    MovimentoProdutoMensal,
    MovimentoProdutoSemanal,
    StatusMovimentoProdutoMensal,
    StatusMovimentoProdutoSemanal,
)
from .services import _decimal_texto, detectar_mes_aberto
from .services_vendas_semanais import _estrutura_familia, inicio_semana


ZERO = Decimal("0")
TRINTA = Decimal("30")
LIMITE = Decimal("15")


def _inicio_mes_relativo(inicio: date, deslocamento: int) -> date:
    mes_absoluto = inicio.year * 12 + inicio.month - 1 + deslocamento
    return date(mes_absoluto // 12, mes_absoluto % 12 + 1, 1)


def _periodos_semanais(semana_inicio: date):
    if inicio_semana(semana_inicio) != semana_inicio:
        raise ValueError("A semana deve comecar no domingo.")
    ultima = Venda.objects.exclude(status="C").aggregate(ultima=Max("data_venda"))["ultima"]
    if ultima is None or semana_inicio > inicio_semana(ultima):
        raise Venda.DoesNotExist
    parcial = semana_inicio == inicio_semana(ultima) and ultima < semana_inicio + timedelta(days=6)
    dias_foco = (ultima - semana_inicio).days + 1 if parcial else 7
    inicios = [semana_inicio - timedelta(days=7 * indice) for indice in range(24, -1, -1)]
    estados = {
        item.semana_inicio: item for item in StatusMovimentoProdutoSemanal.objects.filter(semana_inicio__in=inicios)
    }
    periodos = [
        {
            "inicio": inicio, "fim": inicio + timedelta(days=6),
            "corte": inicio + timedelta(days=dias_foco - 1) if parcial else inicio + timedelta(days=6),
            "dias": dias_foco if parcial else 7,
            "estado": estados.get(inicio),
        }
        for inicio in inicios
    ]
    return periodos, parcial, ultima, Decimal(dias_foco) / Decimal(7)


def _periodos_mensais(ano: int):
    ultima = Venda.objects.filter(data_venda__year=ano).exclude(status="C").aggregate(ultima=Max("data_venda"))["ultima"]
    if ultima is None:
        raise Venda.DoesNotExist
    foco = date(ultima.year, ultima.month, 1)
    parcial = detectar_mes_aberto(ano, ultima) is not None
    inicios = [_inicio_mes_relativo(foco, indice) for indice in range(-5, 1)]
    estados = {
        (item.ano, item.mes): item
        for item in StatusMovimentoProdutoMensal.objects.filter(ano__in={inicio.year for inicio in inicios})
    }
    periodos = []
    for inicio in inicios:
        dias_mes = calendar.monthrange(inicio.year, inicio.month)[1]
        dias = min(ultima.day, dias_mes) if parcial else dias_mes
        periodos.append({
            "inicio": inicio, "fim": date(inicio.year, inicio.month, dias_mes),
            "corte": date(inicio.year, inicio.month, dias), "dias": dias,
            "estado": estados.get((inicio.year, inicio.month)),
        })
    confiabilidade = Decimal(ultima.day) / Decimal(calendar.monthrange(ultima.year, ultima.month)[1]) if parcial else Decimal("1")
    return periodos, parcial, ultima, confiabilidade


def _pendencias(periodos, visao: str, parcial: bool, ultima: date):
    pendentes = [
        {"inicio": periodo["inicio"].isoformat(), "status": periodo["estado"].status if periodo["estado"] else "AUSENTE"}
        for periodo in periodos
        if periodo["estado"] is None or periodo["estado"].status != "PRONTO" or periodo["estado"].ultimo_sucesso_em is None
    ]
    if visao == "mensal" and parcial and not pendentes:
        primeira = Venda.objects.filter(data_venda__gte=periodos[0]["inicio"], data_venda__lte=ultima).exclude(status="C").aggregate(primeira=Min("data_venda"))["primeira"]
        if primeira:
            cursor = inicio_semana(primeira)
            fins = inicio_semana(ultima)
            estados_diarios = {
                item.semana_inicio: item for item in StatusMovimentoProdutoSemanal.objects.filter(
                    semana_inicio__gte=cursor, semana_inicio__lte=fins,
                )
            }
            while cursor <= fins:
                estado = estados_diarios.get(cursor)
                if estado is None or estado.status != "PRONTO" or estado.ultimo_sucesso_em is None:
                    pendentes.append({"inicio": cursor.isoformat(), "status": estado.status if estado else "AUSENTE", "agregado": "diario"})
                cursor += timedelta(days=7)
    return pendentes


def _receitas_por_folha(periodos, folhas, visao: str, parcial: bool):
    valores = {folha_id: [ZERO for _ in periodos] for folha_id in folhas}
    indice_por_inicio = {periodo["inicio"]: indice for indice, periodo in enumerate(periodos)}
    if parcial:
        rows = (
            MovimentoProdutoDiario.objects.filter(
                data__gte=periodos[0]["inicio"], data__lte=periodos[-1]["corte"],
                produto__categorias__id_conta__in=folhas,
            )
            .values("produto__categorias__id_conta", "data")
            .annotate(total=Sum("receita_bruta")).order_by()
        )
        for row in rows:
            inicio = inicio_semana(row["data"]) if visao == "semanal" else date(row["data"].year, row["data"].month, 1)
            indice = indice_por_inicio.get(inicio)
            if indice is not None and row["data"] <= periodos[indice]["corte"]:
                valores[row["produto__categorias__id_conta"]][indice] += row["total"] or ZERO
    elif visao == "semanal":
        rows = (
            MovimentoProdutoSemanal.objects.filter(
                semana_inicio__in=indice_por_inicio, produto__categorias__id_conta__in=folhas,
            )
            .values("produto__categorias__id_conta", "semana_inicio")
            .annotate(total=Sum("receita_bruta")).order_by()
        )
        for row in rows:
            indice = indice_por_inicio[row["semana_inicio"]]
            valores[row["produto__categorias__id_conta"]][indice] += row["total"] or ZERO
    else:
        rows = (
            MovimentoProdutoMensal.objects.filter(
                ano__in={periodo["inicio"].year for periodo in periodos},
                produto__categorias__id_conta__in=folhas,
            )
            .values("produto__categorias__id_conta", "ano", "mes")
            .annotate(total=Sum("receita_bruta")).order_by()
        )
        for row in rows:
            indice = indice_por_inicio.get(date(row["ano"], row["mes"], 1))
            if indice is not None:
                valores[row["produto__categorias__id_conta"]][indice] += row["total"] or ZERO
    return valores


def montar_radar_oscilacoes(*, raiz_id: int, visao: str, ano: int | None = None, semana_inicio: date | None = None) -> dict:
    if visao not in {"mensal", "semanal"}:
        raise ValueError("Visao invalida. Use 'mensal' ou 'semanal'.")
    if visao == "mensal":
        if ano is None:
            raise ValueError("Informe 'ano' para a visao mensal.")
        periodos, parcial, ultima, confiabilidade = _periodos_mensais(ano)
        tamanho_referencia = 5
    else:
        if semana_inicio is None:
            raise ValueError("Informe 'semana_inicio' para a visao semanal.")
        periodos, parcial, ultima, confiabilidade = _periodos_semanais(semana_inicio)
        tamanho_referencia = 20
    raiz, nodes, _, _, folhas = _estrutura_familia(raiz_id)
    pendentes = _pendencias(periodos, visao, parcial, ultima)
    foco = periodos[-1]
    atualizado_em = max(
        (periodo["estado"].ultimo_sucesso_em for periodo in periodos if periodo["estado"] and periodo["estado"].ultimo_sucesso_em),
        default=None,
    )
    base = {
        "familia": {"id_conta": raiz.id_conta, "codigo_hierarquico": raiz.codigo_hierarquico, "nome_conta": raiz.nome_conta},
        "visao": visao, "metrica": "valor", "limite_indice": _decimal_texto(LIMITE),
        "periodo_foco": {"inicio": foco["inicio"].isoformat(), "fim": foco["fim"].isoformat(), "corte": foco["corte"].isoformat()},
        "janela_referencia": {"inicio": periodos[0]["inicio"].isoformat(), "fim": periodos[tamanho_referencia - 1]["fim"].isoformat(), "periodos": tamanho_referencia},
        "janela_recente": {"inicio": periodos[tamanho_referencia]["inicio"].isoformat(), "fim": foco["fim"].isoformat(), "periodos": len(periodos) - tamanho_referencia},
        "previa": parcial, "ultima_data_disponivel": ultima.isoformat(),
        "atualizado_em": atualizado_em.isoformat() if atualizado_em else None,
        "disponivel": not pendentes, "periodos_pendentes": pendentes,
        "quedas": [], "crescimentos": [],
    }
    if pendentes:
        base["motivo"] = "HISTORICO_INCOMPLETO" if any(item["status"] == "AUSENTE" for item in pendentes) else "PERIODOS_DESATUALIZADOS"
        return base

    receitas = _receitas_por_folha(periodos, folhas, visao, parcial)
    nodes_por_id = {node["id_conta"]: node for node in nodes}
    for folha_id in folhas:
        normalizados = [valor * TRINTA / Decimal(periodo["dias"]) for valor, periodo in zip(receitas[folha_id], periodos)]
        referencia = sum(normalizados[:tamanho_referencia], ZERO) / Decimal(tamanho_referencia)
        if referencia <= ZERO:
            continue
        recente = sum(normalizados[tamanho_referencia:], ZERO) / Decimal(len(periodos) - tamanho_referencia)
        diferenca = recente - referencia
        indice_quadrado = diferenca * diferenca / referencia * confiabilidade
        if indice_quadrado < LIMITE * LIMITE:
            continue
        node = nodes_por_id[folha_id]
        linha = {
            "id_conta": folha_id, "codigo_hierarquico": node["codigo_hierarquico"], "nome_conta": node["nome_conta"],
            "media_referencia": _decimal_texto(referencia), "media_recente": _decimal_texto(recente),
            "diferenca": _decimal_texto(diferenca),
            "percentual": _decimal_texto(diferenca / referencia * 100),
            "indice": _decimal_texto(indice_quadrado.sqrt()),
        }
        (base["crescimentos"] if diferenca > ZERO else base["quedas"]).append(linha)
    for direcao in ("quedas", "crescimentos"):
        base[direcao].sort(key=lambda linha: (-Decimal(linha["indice"]), -abs(Decimal(linha["diferenca"])), linha["nome_conta"].casefold(), linha["id_conta"]))
    return base
