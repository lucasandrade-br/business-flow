"""Snapshots e leitura temporal das compras; nunca consulta itens na API."""

import calendar
import logging
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Exists, F, Max, Min, OuterRef, Q, Sum, Value, CharField
from django.db.models.functions import Cast, Coalesce, NullIf, Trim
from django.utils import timezone

from apps.cadastros.models import PlanoConta, Produto
from apps.compras.models import Compra, ItemCompra
from .models import (
    MovimentoCompraProdutoDiario as Diario,
    MovimentoCompraProdutoSemanal as Semanal,
    MovimentoCompraProdutoMensal as Mensal,
    StatusMovimentoCompraProdutoSemanal as StatusSemanal,
    StatusMovimentoCompraProdutoMensal as StatusMensal,
)
from .services import CategoriasAmbiguasError, AgregadoDiarioIncompletoError, _decimal_texto, _fornecedor_contexto, _serializar_fornecedor

logger = logging.getLogger(__name__)
ZERO = Decimal("0")


def inicio_semana(data):
    return data - timedelta(days=(data.weekday() + 1) % 7)


def _limites():
    return ItemCompra.objects.filter(
        quantidade__gte=0, valor_custo__gte=0, valor_total_item__gte=0,
    ).exclude(compra__nfe_status__iexact="CANCELADA").aggregate(
        primeira=Min("compra__data_emissao"), ultima=Max("compra__data_emissao")
    )


def reconstruir_movimento_compra_produto_semanal(semana_inicio):
    if semana_inicio != inicio_semana(semana_inicio):
        raise ValueError("A semana deve começar no domingo.")
    fim = semana_inicio + timedelta(days=7)
    estado, _ = StatusSemanal.objects.update_or_create(
        semana_inicio=semana_inicio, defaults={"status": "PROCESSANDO", "erro": ""}
    )
    try:
        linhas = list(ItemCompra.objects.filter(
            compra__data_emissao__gte=semana_inicio, compra__data_emissao__lt=fim,
            quantidade__gte=0, valor_custo__gte=0, valor_total_item__gte=0,
        ).exclude(compra__nfe_status__iexact="CANCELADA").values(
            "compra__data_emissao", "produto_id", "compra__fornecedor_id",
            "unidade_medida_id", "unidade_medida__sigla",
        ).annotate(valor=Sum("valor_total_item"), qtd=Sum("quantidade")).order_by())
        diarios = []
        semanas = defaultdict(lambda: [ZERO, ZERO])
        for row in linhas:
            unidade = row["unidade_medida_id"] or 0
            sigla = row["unidade_medida__sigla"] or "SEM UN."
            valor, qtd = row["valor"] or ZERO, row["qtd"] or ZERO
            diarios.append(Diario(
                data=row["compra__data_emissao"], produto_id=row["produto_id"],
                fornecedor_id=row["compra__fornecedor_id"], unidade_medida_id_origem=unidade,
                unidade_sigla=sigla, valor_comprado=valor, quantidade=qtd,
            ))
            total = semanas[(row["produto_id"], row["compra__fornecedor_id"], unidade, sigla)]
            total[0] += valor
            total[1] += qtd
        semanais = [Semanal(
            semana_inicio=semana_inicio, produto_id=produto, fornecedor_id=fornecedor,
            unidade_medida_id_origem=unidade, unidade_sigla=sigla,
            valor_comprado=totais[0], quantidade=totais[1],
        ) for (produto, fornecedor, unidade, sigla), totais in semanas.items()]
        with transaction.atomic():
            Diario.objects.filter(data__gte=semana_inicio, data__lt=fim).delete()
            Semanal.objects.filter(semana_inicio=semana_inicio).delete()
            Diario.objects.bulk_create(diarios, batch_size=2000)
            Semanal.objects.bulk_create(semanais, batch_size=2000)
            estado.status = "PRONTO"
            estado.erro = ""
            estado.ultimo_sucesso_em = timezone.now()
            estado.save(update_fields=["status", "erro", "ultimo_sucesso_em", "atualizado_em"])
        return len(semanais)
    except Exception as exc:
        StatusSemanal.objects.filter(pk=estado.pk).update(
            status="FALHA", erro=str(exc)[:4000], atualizado_em=timezone.now()
        )
        logger.exception("Falha ao reconstruir compras da semana %s", semana_inicio)
        raise


def reconstruir_movimentos_compra_produto_semanais(*, inicio=None, fim=None, somente_pendentes=False):
    limites = _limites()
    existentes = StatusSemanal.objects.aggregate(primeira=Min("semana_inicio"), ultima=Max("semana_inicio"))
    primeiro = inicio or limites["primeira"] or existentes["primeira"]
    ultimo = fim or limites["ultima"] or existentes["ultima"]
    if not primeiro or not ultimo:
        return {"periodos_processados": 0, "linhas_geradas": 0}
    cursor, fim_semana = inicio_semana(primeiro), inicio_semana(ultimo)
    if cursor > fim_semana:
        raise ValueError("Data inicial posterior à data final.")
    prontos = set(StatusSemanal.objects.filter(
        semana_inicio__gte=cursor, semana_inicio__lte=fim_semana,
        status="PRONTO", ultimo_sucesso_em__isnull=False,
    ).values_list("semana_inicio", flat=True)) if somente_pendentes else set()
    processados = linhas = 0
    while cursor <= fim_semana:
        if cursor not in prontos:
            linhas += reconstruir_movimento_compra_produto_semanal(cursor)
            processados += 1
        cursor += timedelta(days=7)
    return {"periodos_processados": processados, "linhas_geradas": linhas}


def status_agregados_compras_semanais():
    limites = _limites()
    primeira, ultima = limites["primeira"], limites["ultima"]
    if not primeira:
        return {"semanas_disponiveis": [], "semana_inicial": None, "ultima_data_disponivel": None}
    semanas = list(StatusSemanal.objects.filter(
        semana_inicio__gte=inicio_semana(primeira), semana_inicio__lte=inicio_semana(ultima),
        ultimo_sucesso_em__isnull=False,
    ).order_by("-semana_inicio").values_list("semana_inicio", flat=True))
    return {"semanas_disponiveis": [d.isoformat() for d in semanas],
            "semana_inicial": semanas[0].isoformat() if semanas else None,
            "ultima_data_disponivel": ultima.isoformat()}


def status_agregados_compras_anuais():
    limites = _limites()
    if not limites["primeira"]:
        return {"anos_disponiveis": [], "ultima_data_disponivel": None}
    return {"anos_disponiveis": list(range(limites["ultima"].year, limites["primeira"].year - 1, -1)),
            "ultima_data_disponivel": limites["ultima"].isoformat()}


def _estrutura(raiz_id):
    raiz = PlanoConta.objects.filter(id_conta=raiz_id, conta_pai__isnull=True).first()
    if not raiz:
        raise PlanoConta.DoesNotExist
    nodes = list(PlanoConta.objects.filter(codigo_ordenacao__startswith=raiz.codigo_ordenacao)
                 .order_by("codigo_ordenacao").values("id_conta", "codigo_hierarquico", "nome_conta", "conta_pai_id"))
    ids = {n["id_conta"] for n in nodes}
    pais = {n["conta_pai_id"] for n in nodes if n["conta_pai_id"] in ids}
    folhas = ids - pais
    conflitos = list(Produto.objects.filter(categorias__id_conta__in=folhas)
        .values("id_produto", "produto").annotate(qtd=Count("categorias", distinct=True))
        .filter(qtd__gt=1).order_by("id_produto"))
    if conflitos:
        raise CategoriasAmbiguasError(conflitos)
    return raiz, nodes, ids, pais, folhas


def _periodos_semanais(foco, equivalente):
    if inicio_semana(foco) != foco:
        raise ValueError("A semana deve começar no domingo.")
    limites = _limites()
    primeira, ultima = limites["primeira"], limites["ultima"]
    if not primeira or foco > inicio_semana(ultima):
        raise Semanal.DoesNotExist
    datas = [foco - timedelta(days=7 * i) for i in range(20, -1, -1)]
    estados = {s.semana_inicio: s for s in StatusSemanal.objects.filter(semana_inicio__in=datas)}
    if foco not in estados or not estados[foco].ultimo_sucesso_em:
        raise Semanal.DoesNotExist
    primeiro = inicio_semana(primeira)
    disponiveis = {i for i, d in enumerate(datas) if d >= primeiro and d in estados and estados[d].ultimo_sucesso_em}
    faltantes = {i for i, d in enumerate(datas) if d >= primeiro and i not in disponiveis}
    validos = [i for i in range(20) if i in disponiveis]
    ultimos = [i for i in range(15, 20) if i in disponiveis]
    parcial = foco == inicio_semana(ultima) and ultima < foco + timedelta(days=6)
    corte = (ultima - foco).days if parcial else 6
    aplicar = bool(parcial and equivalente)
    avisos = [{"semana_inicio": d.isoformat(), "status": estados[d].status if d in estados else "AUSENTE"}
              for d in datas if d >= primeiro and (d not in estados or estados[d].status != "PRONTO")]
    return {"datas": datas, "disponiveis": disponiveis, "faltantes": faltantes, "validos": validos, "ultimos": ultimos,
        "aplicar": aplicar, "corte": corte,
        "publico": {"semana_inicio": foco.isoformat(), "periodo_equivalente": aplicar,
        "semana_parcial": parcial, "periodos_considerados_20": len(validos),
        "periodos_considerados_5": len(ultimos), "ultima_data_disponivel": ultima.isoformat(),
        "atualizado_em": estados[foco].ultimo_sucesso_em.isoformat(),
        "desatualizado": bool(avisos), "periodos_desatualizados": avisos,
        "semanas": [{"inicio": d.isoformat(), "fim": (d + timedelta(days=6)).isoformat(),
            "data_corte": (d + timedelta(days=corte)).isoformat() if aplicar or (i == 5 and parcial) else None,
            "parcial": i == 5 and parcial, "equivalente": aplicar and i < 5}
            for i, d in enumerate(datas[15:])]}}


def _periodos_mensais(ano, equivalente):
    ultima = _limites()["ultima"]
    if not ultima or ano > ultima.year:
        raise Mensal.DoesNotExist
    ultima_foco = ItemCompra.objects.filter(compra__data_emissao__year=ano,
        quantidade__gte=0, valor_custo__gte=0, valor_total_item__gte=0,
    ).exclude(compra__nfe_status__iexact="CANCELADA").aggregate(ultima=Max("compra__data_emissao"))["ultima"]
    if not ultima_foco:
        primeira = _limites()["primeira"]
        if not primeira or not primeira.year < ano < ultima.year:
            raise Mensal.DoesNotExist
        ultima_foco = date(ano, 12, 31)
    parcial = ano == timezone.localdate().year and ultima_foco.day < calendar.monthrange(ano, ultima_foco.month)[1]
    aplicar = bool(equivalente and parcial)
    estados = {s.mes: s for s in StatusMensal.objects.filter(ano=ano)}
    avisos = [{"ano": ano, "mes": m, "status": estados[m].status if m in estados else "AUSENTE"}
              for m in range(1, ultima_foco.month + 1) if m not in estados or estados[m].status != "PRONTO"]
    disponiveis = {i for i in range(12) if i + 1 in estados and estados[i + 1].ultimo_sucesso_em}
    limites = _limites()
    primeiro_mes = limites["primeira"].month if limites["primeira"] and limites["primeira"].year == ano else 1
    requeridos = set(range(primeiro_mes - 1, ultima_foco.month))
    if aplicar:
        semanas = {s.semana_inicio: s for s in StatusSemanal.objects.filter(
            semana_inicio__gte=inicio_semana(date(ano, primeiro_mes, 1)),
            semana_inicio__lte=inicio_semana(ultima_foco))}
        cursor = inicio_semana(date(ano, primeiro_mes, 1))
        while cursor <= ultima_foco:
            estado = semanas.get(cursor)
            if estado is None or estado.ultimo_sucesso_em is None:
                raise AgregadoDiarioIncompletoError(f"Semana {cursor} sem snapshot diário válido.")
            if estado.status != "PRONTO":
                avisos.append({"semana_inicio": cursor.isoformat(), "status": estado.status})
            cursor += timedelta(days=7)
    return {"disponiveis": disponiveis, "requeridos": requeridos, "aplicar": aplicar,
        "periodos": [(date(ano, m, 1), date(ano, m, min(ultima_foco.day, calendar.monthrange(ano, m)[1]))) for m in range(1, 13)],
        "publico": {"ano_consultado": ano, "meses": ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"],
            "periodo_equivalente": aplicar, "mes_aberto": ultima_foco.month if parcial else None,
            "ultima_data_disponivel": ultima_foco.isoformat(), "desatualizado": bool(avisos),
            "periodos_desatualizados": avisos, "data_corte": ultima_foco.isoformat() if aplicar else None,
            "rotulo_total": "Total comparável" if aplicar else "Total"}}


def _periodos_anuais(ano, equivalente):
    limites = _limites()
    primeira, ultima = limites["primeira"], limites["ultima"]
    if not primeira or not primeira.year <= ano <= ultima.year:
        raise Compra.DoesNotExist
    ultima_foco = ItemCompra.objects.filter(compra__data_emissao__year=ano,
        quantidade__gte=0, valor_custo__gte=0, valor_total_item__gte=0,
    ).exclude(compra__nfe_status__iexact="CANCELADA").aggregate(ultima=Max("compra__data_emissao"))["ultima"]
    data_compra_foco = ultima_foco
    if ultima_foco is None:
        ultima_foco = date(ano, 12, 31)
    anos = list(range(max(primeira.year, ano - 3), ano + 1))
    parcial = ano == timezone.localdate().year and ultima_foco and ultima_foco < date(ano, 12, 31)
    aplicar = bool(parcial and equivalente)
    periodos, avisos, disponiveis = [], [], set()
    estados_m = {(s.ano, s.mes): s for s in StatusMensal.objects.filter(ano__in=anos)}
    estados_s = {s.semana_inicio: s for s in StatusSemanal.objects.filter(
        semana_inicio__gte=inicio_semana(date(anos[0], 1, 1)), semana_inicio__lte=ultima_foco)}
    for i, a in enumerate(anos):
        fim = (date(a, ultima_foco.month, min(ultima_foco.day, calendar.monthrange(a, ultima_foco.month)[1]))
               if aplicar else ultima_foco if a == ano and parcial else date(a, 12, 31))
        inicio = date(a, 1, 1)
        if aplicar:
            cursor = inicio_semana(inicio)
            while cursor <= fim:
                estado = estados_s.get(cursor)
                if estado is None or estado.ultimo_sucesso_em is None:
                    raise AgregadoDiarioIncompletoError(f"Semana {cursor} sem snapshot diário válido.")
                if estado.status != "PRONTO":
                    avisos.append({"semana_inicio": cursor.isoformat(), "status": estado.status})
                cursor += timedelta(days=7)
        else:
            for m in range(1, fim.month + 1):
                estado = estados_m.get((a, m))
                if estado is None or estado.ultimo_sucesso_em is None:
                    raise AgregadoDiarioIncompletoError(f"Mês {a}-{m:02d} sem snapshot válido.")
                if estado.status != "PRONTO":
                    avisos.append({"ano": a, "mes": m, "status": estado.status})
        disponiveis.add(i)
        periodos.append({"ano": a, "inicio": inicio.isoformat(), "fim": fim.isoformat(),
                         "data_corte": fim.isoformat(), "parcial": i == len(anos) - 1 and bool(parcial),
                         "equivalente": aplicar and a != ano})
    return {"disponiveis": disponiveis, "aplicar": aplicar, "periodos": periodos,
        "publico": {"ano_consultado": ano, "anos": periodos, "ano_parcial": bool(parcial),
            "periodo_equivalente": aplicar, "ultima_data_disponivel": data_compra_foco.isoformat() if data_compra_foco else None,
            "desatualizado": bool(avisos), "periodos_desatualizados": avisos}}


def _iterar(periodo, contexto, fornecedor_id, produto_ids=None, folhas=None):
    """Retorna produto, folha, índice, unidade, valor e quantidade dos snapshots."""
    if periodo == "semanal":
        inicio, fim = contexto["datas"][0], contexto["datas"][-1] + timedelta(days=6)
        query = (Diario.objects.filter(data__gte=inicio, data__lte=fim) if contexto["aplicar"]
                 else Semanal.objects.filter(semana_inicio__in=contexto["datas"]))
    elif periodo == "mensal":
        ano = contexto["publico"]["ano_consultado"]
        query = (Diario.objects.filter(data__year=ano) if contexto["aplicar"]
                 else Mensal.objects.filter(ano=ano))
    else:
        anos = [p["ano"] for p in contexto["periodos"]]
        query = (Diario.objects.filter(data__year__in=anos) if contexto["aplicar"]
                 else Mensal.objects.filter(ano__in=anos))
    if fornecedor_id is not None:
        query = query.filter(fornecedor_id=fornecedor_id)
    if produto_ids is not None:
        query = query.filter(produto_id__in=produto_ids)
    if folhas is not None:
        query = query.filter(produto__categorias__id_conta__in=folhas)
    campos = ["produto_id", "unidade_medida_id_origem", "unidade_sigla"]
    if folhas is not None:
        campos.append("produto__categorias__id_conta")
    if isinstance(query.model, type) and query.model is Diario:
        campos.append("data")
    elif query.model is Semanal:
        campos.append("semana_inicio")
    else:
        campos.extend(["ano", "mes"])
    for row in query.values(*campos).annotate(valor=Sum("valor_comprado"), qtd=Sum("quantidade")).order_by():
        if periodo == "semanal":
            dia = row.get("data")
            semana = inicio_semana(dia) if dia else row["semana_inicio"]
            indice = (semana - contexto["datas"][0]).days // 7
            if not 0 <= indice < 21 or indice not in contexto["disponiveis"]:
                continue
            if dia and (dia - semana).days > contexto["corte"]:
                continue
        elif periodo == "mensal":
            indice = row["data"].month - 1 if "data" in row else row["mes"] - 1
            if indice not in contexto["disponiveis"]:
                continue
            if "data" in row and row["data"] > contexto["periodos"][indice][1]:
                continue
        else:
            ano = row["data"].year if "data" in row else row["ano"]
            indice = ano - contexto["periodos"][0]["ano"]
            if indice not in contexto["disponiveis"]:
                continue
            if "data" in row and row["data"] > date.fromisoformat(contexto["periodos"][indice]["fim"]):
                continue
            if "data" not in row and row["mes"] > date.fromisoformat(contexto["periodos"][indice]["fim"]).month:
                continue
        yield (row["produto_id"], row.get("produto__categorias__id_conta"), indice,
               (row["unidade_medida_id_origem"], row["unidade_sigla"]), row["valor"] or ZERO, row["qtd"] or ZERO)


def _taxa(atual, base):
    return _decimal_texto((atual - base) / base * 100) if atual is not None and base else None


def _historica(valores):
    if len(valores) < 3:
        return None
    taxas = []
    for i in range(1, len(valores) - 1):
        if not valores[i - 1]:
            return None
        taxas.append((valores[i] - valores[i - 1]) / valores[i - 1] * 100)
    return _decimal_texto(sum(taxas, ZERO) / len(taxas))


def _serializar(periodo, metrica, series, disponiveis, contexto):
    tamanho = 21 if periodo == "semanal" else 12 if periodo == "mensal" else len(contexto["periodos"])
    valor = [series[i][0] for i in range(tamanho)]
    qtd = [series[i][1] for i in range(tamanho)]
    def medir(i):
        if i not in disponiveis:
            return None
        if metrica == "valor":
            return valor[i]
        if metrica == "quantidade":
            return qtd[i]
        return valor[i] / qtd[i] if qtd[i] else None
    valores = [medir(i) for i in range(tamanho)]
    def texto(n):
        return _decimal_texto(n) if n is not None else None
    if periodo == "semanal":
        def media(indices, referencia):
            if not indices:
                return None
            if any(i in contexto["faltantes"] for i in referencia):
                return None
            v = sum((valor[i] for i in indices), ZERO) / len(indices)
            q = sum((qtd[i] for i in indices), ZERO) / len(indices)
            return v if metrica == "valor" else q if metrica == "quantidade" else v / q if q else None
        m20, m5 = media(contexto["validos"], range(20)), media(contexto["ultimos"], range(15, 20))
        return {"valores": [texto(v) for v in valores[15:]], "media_20": texto(m20), "media_5": texto(m5),
                "variacao_5_vs_20_percentual": _taxa(m5, m20), "variacao_5_percentual": _taxa(valores[-1], m5)}
    if periodo == "mensal":
        total_v, total_q = sum(valor, ZERO), sum(qtd, ZERO)
        total = total_v if metrica == "valor" else total_q if metrica == "quantidade" else total_v / total_q if total_q else None
        if not contexto["requeridos"].issubset(disponiveis):
            total = None
        return {"valores": [texto(v) for v in valores], "total": texto(total)}
    return {"valores": [texto(v) for v in valores],
            "variacao_historica_percentual": _historica(valores),
            "variacao_percentual": _taxa(valores[-1], valores[-2]) if len(valores) > 1 else None}


def _contexto(periodo, *, ano=None, semana_inicio=None, periodo_equivalente=False):
    if periodo == "semanal":
        return _periodos_semanais(semana_inicio, periodo_equivalente)
    if periodo == "mensal":
        return _periodos_mensais(ano, periodo_equivalente)
    return _periodos_anuais(ano, periodo_equivalente)


def montar_analise_compras_categorias_periodo(*, periodo, raiz_id, metrica, fornecedor_id=None,
                                                ano=None, semana_inicio=None, periodo_equivalente=False):
    if metrica not in {"valor", "quantidade"}:
        raise ValueError("Métrica inválida.")
    raiz, nodes, ids, pais, folhas = _estrutura(raiz_id)
    fornecedor = _fornecedor_contexto(fornecedor_id)
    contexto = _contexto(periodo, ano=ano, semana_inicio=semana_inicio, periodo_equivalente=periodo_equivalente)
    tamanho = 21 if periodo == "semanal" else 12 if periodo == "mensal" else len(contexto["periodos"])
    acumulados = {node_id: defaultdict(lambda: [[ZERO, ZERO] for _ in range(tamanho)]) for node_id in ids}
    for _, folha, indice, unidade, valor, qtd in _iterar(periodo, contexto, fornecedor_id, folhas=folhas):
        totais = acumulados[folha][unidade][indice]
        totais[0] += valor
        totais[1] += qtd
    for node in reversed(nodes):
        pai = node["conta_pai_id"]
        if pai not in ids:
            continue
        for unidade, serie in acumulados[node["id_conta"]].items():
            destino = acumulados[pai][unidade]
            for i, (v, q) in enumerate(serie):
                destino[i][0] += v
                destino[i][1] += q
    nivel_raiz = len(raiz.codigo_hierarquico.split("."))
    linhas = []
    for node in nodes:
        linha = {**node, "conta_pai_id": node["conta_pai_id"] if node["conta_pai_id"] in ids else None,
                 "nivel": len(node["codigo_hierarquico"].split(".")) - nivel_raiz,
                 "tem_filhos": node["id_conta"] in pais}
        series = acumulados[node["id_conta"]]
        if metrica == "valor":
            soma = [[sum((s[i][0] for s in series.values()), ZERO),
                     sum((s[i][1] for s in series.values()), ZERO)] for i in range(tamanho)]
            linha.update(_serializar(periodo, metrica, soma, contexto["disponiveis"], contexto))
        else:
            linha["unidades"] = [{"id_unidade": u[0], "sigla": u[1],
                                   **_serializar(periodo, metrica, s, contexto["disponiveis"], contexto)}
                                  for u, s in sorted(series.items(), key=lambda item: (item[0][1], item[0][0]))]
        linhas.append(linha)
    return {"familia": {"id_conta": raiz.id_conta, "codigo_hierarquico": raiz.codigo_hierarquico,
                         "nome_conta": raiz.nome_conta}, "fornecedor": _serializar_fornecedor(fornecedor),
            "metrica": metrica, **contexto["publico"], "linhas": linhas}


def montar_analise_compras_produtos_periodo(*, periodo, raiz_id, categoria_id, metrica,
                                              fornecedor_id=None, ano=None, semana_inicio=None,
                                              periodo_equivalente=False, incluir_inativos=False,
                                              search="", pagina=1, por_pagina=100):
    if metrica not in {"valor", "quantidade", "custo_medio"} or pagina < 1:
        raise ValueError("Métrica ou página inválida.")
    raiz, nodes, ids, pais, folhas = _estrutura(raiz_id)
    fornecedor = _fornecedor_contexto(fornecedor_id)
    contexto = _contexto(periodo, ano=ano, semana_inicio=semana_inicio, periodo_equivalente=periodo_equivalente)
    por_id = {n["id_conta"]: n for n in nodes}
    if categoria_id not in por_id:
        if PlanoConta.objects.filter(id_conta=categoria_id).exists():
            raise ValueError("A categoria selecionada não pertence à família informada.")
        raise PlanoConta.DoesNotExist
    subfolhas = set()
    for folha in folhas:
        atual = folha
        while atual in por_id:
            if atual == categoria_id:
                subfolhas.add(folha)
                break
            atual = por_id[atual]["conta_pai_id"]
    vinculo = Produto.categorias.through.objects.filter(produto_id=OuterRef("pk"), planoconta_id__in=subfolhas)
    nome = Coalesce(NullIf(Trim("nome_gerencial"), Value("")), F("produto"), output_field=CharField())
    produtos = Produto.objects.annotate(pertence=Exists(vinculo), nome_exibicao=nome,
               id_texto=Cast("id_produto", output_field=CharField())).filter(pertence=True)
    termo = str(search or "").strip()
    if termo:
        produtos = produtos.filter(Q(id_texto__icontains=termo) | Q(nome_gerencial__icontains=termo) | Q(produto__icontains=termo))
    ocultos = produtos.filter(status__iexact="INATIVO").count()
    permitidos = Q(status__iexact="ATIVO")
    if incluir_inativos:
        permitidos |= Q(status__iexact="INATIVO")
    candidatos = list(produtos.filter(permitidos).values("id_produto", "nome_exibicao", "status"))
    ids_candidatos = [p["id_produto"] for p in candidatos]
    tamanho = 21 if periodo == "semanal" else 12 if periodo == "mensal" else len(contexto["periodos"])
    todos = {pid: defaultdict(lambda: [[ZERO, ZERO] for _ in range(tamanho)]) for pid in ids_candidatos}
    for produto, _, indice, unidade, valor, qtd in _iterar(periodo, contexto, fornecedor_id, produto_ids=ids_candidatos):
        alvo = todos[produto][unidade][indice]
        alvo[0] += valor
        alvo[1] += qtd
    def ordem(p):
        series = todos[p["id_produto"]].values()
        indices = contexto["validos"] if periodo == "semanal" else range(12) if periodo == "mensal" else [tamanho - 1]
        valor = sum((s[i][0] for s in series for i in indices), ZERO)
        if periodo == "semanal" and indices:
            valor /= len(indices)
        indisponivel = (bool(contexto["faltantes"]) or not indices) if periodo == "semanal" else (
            not contexto["requeridos"].issubset(contexto["disponiveis"]) if periodo == "mensal" else False)
        return (indisponivel, -valor if not indisponivel else ZERO,
                p["nome_exibicao"].casefold(), p["id_produto"])
    candidatos.sort(key=ordem)
    paginador = Paginator(candidatos, por_pagina)
    page = paginador.get_page(pagina)
    linhas = []
    for produto in page.object_list:
        series = todos[produto["id_produto"]]
        linha = {"id_produto": produto["id_produto"], "nome_produto": produto["nome_exibicao"],
                 "status": produto["status"]}
        if metrica == "valor":
            soma = [[sum((s[i][0] for s in series.values()), ZERO),
                     sum((s[i][1] for s in series.values()), ZERO)] for i in range(tamanho)]
            linha.update(_serializar(periodo, metrica, soma, contexto["disponiveis"], contexto))
        else:
            linha["unidades"] = [{"id_unidade": u[0], "sigla": u[1],
                                   **_serializar(periodo, metrica, s, contexto["disponiveis"], contexto)}
                                  for u, s in sorted(series.items(), key=lambda item: (item[0][1], item[0][0]))]
        linhas.append(linha)
    categoria = por_id[categoria_id]
    return {"familia": {"id_conta": raiz.id_conta, "codigo_hierarquico": raiz.codigo_hierarquico,
                         "nome_conta": raiz.nome_conta}, "categoria": categoria,
            "fornecedor": _serializar_fornecedor(fornecedor), "metrica": metrica,
            **contexto["publico"], "linhas": linhas,
            "paginacao": {"pagina": page.number, "por_pagina": por_pagina,
                          "total_produtos": paginador.count, "total_paginas": paginador.num_pages},
            "inativos_ocultos": ocultos}
