"""Snapshots e leitura da análise semanal de vendas por categoria."""

import logging
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import CharField, Count, Exists, Max, Min, OuterRef, Q, Sum
from django.db.models.functions import Cast, Coalesce, NullIf, Trim
from django.db.models import F, Value
from django.utils import timezone

from apps.cadastros.models import PlanoConta, Produto
from apps.vendas.models import ItemVenda, Venda

from .models import MovimentoProdutoDiario, MovimentoProdutoSemanal, StatusMovimentoProdutoSemanal
from .services import CategoriasAmbiguasError, _decimal_texto


logger = logging.getLogger(__name__)
ZERO = Decimal("0")


def inicio_semana(data: date) -> date:
    """Domingo da semana que contem a data, inclusive na virada de ano."""
    return data - timedelta(days=(data.weekday() + 1) % 7)


def reconstruir_movimento_produto_semanal(semana_inicio: date) -> int:
    if inicio_semana(semana_inicio) != semana_inicio:
        raise ValueError("A semana deve comecar no domingo.")
    semana_seguinte = semana_inicio + timedelta(days=7)
    status, _ = StatusMovimentoProdutoSemanal.objects.update_or_create(
        semana_inicio=semana_inicio,
        defaults={"status": StatusMovimentoProdutoSemanal.STATUS_PROCESSANDO, "erro": ""},
    )
    try:
        linhas = list(
            ItemVenda.objects.filter(
                venda__data_venda__gte=semana_inicio,
                venda__data_venda__lt=semana_seguinte,
                cancelado=False,
                quantidade__gte=0,
                valor_total_item__gte=0,
            )
            .exclude(venda__status="C")
            .values("venda__data_venda", "produto_id", "unidade_medida_id", "unidade_medida__sigla")
            .annotate(receita_bruta=Sum("valor_total_item"), quantidade_total=Sum("quantidade"))
            .order_by()
        )
        diarios = []
        semanais = defaultdict(lambda: [ZERO, ZERO])
        for linha in linhas:
            unidade_id = linha["unidade_medida_id"] or 0
            sigla = linha["unidade_medida__sigla"] or "SEM UN."
            receita = linha["receita_bruta"] or ZERO
            quantidade = linha["quantidade_total"] or ZERO
            diarios.append(MovimentoProdutoDiario(
                data=linha["venda__data_venda"], produto_id=linha["produto_id"],
                unidade_medida_id_origem=unidade_id, unidade_sigla=sigla,
                receita_bruta=receita, quantidade=quantidade,
            ))
            acumulado = semanais[(linha["produto_id"], unidade_id, sigla)]
            acumulado[0] += receita
            acumulado[1] += quantidade
        semanais_novos = [
            MovimentoProdutoSemanal(
                semana_inicio=semana_inicio, produto_id=produto_id,
                unidade_medida_id_origem=unidade_id, unidade_sigla=sigla,
                receita_bruta=totais[0], quantidade=totais[1],
            )
            for (produto_id, unidade_id, sigla), totais in semanais.items()
        ]
        with transaction.atomic():
            MovimentoProdutoDiario.objects.filter(data__gte=semana_inicio, data__lt=semana_seguinte).delete()
            MovimentoProdutoSemanal.objects.filter(semana_inicio=semana_inicio).delete()
            MovimentoProdutoDiario.objects.bulk_create(diarios, batch_size=2000)
            MovimentoProdutoSemanal.objects.bulk_create(semanais_novos, batch_size=2000)
            status.status = StatusMovimentoProdutoSemanal.STATUS_PRONTO
            status.erro = ""
            status.ultimo_sucesso_em = timezone.now()
            status.save(update_fields=["status", "erro", "ultimo_sucesso_em", "atualizado_em"])
        return len(semanais_novos)
    except Exception as exc:
        StatusMovimentoProdutoSemanal.objects.filter(pk=status.pk).update(
            status=StatusMovimentoProdutoSemanal.STATUS_FALHA,
            erro=str(exc)[:4000], atualizado_em=timezone.now(),
        )
        logger.exception("Falha ao reconstruir movimento semanal de produtos em %s", semana_inicio)
        raise


def reconstruir_movimentos_produto_semanais(*, inicio: date | None = None, fim: date | None = None, somente_pendentes: bool = False) -> dict:
    """Reconstrói o intervalo histórico; inclui semanas zeradas e snapshots antigos."""
    limites = Venda.objects.aggregate(primeira=Min("data_venda"), ultima=Max("data_venda"))
    existentes = StatusMovimentoProdutoSemanal.objects.aggregate(
        primeira=Min("semana_inicio"), ultima=Max("semana_inicio"),
    )
    datas_inicio = [valor for valor in (limites["primeira"], existentes["primeira"], inicio) if valor]
    datas_fim = [valor for valor in (limites["ultima"], existentes["ultima"], fim) if valor]
    if not datas_inicio or not datas_fim:
        return {"periodos_processados": 0, "linhas_geradas": 0}
    cursor = inicio_semana(inicio if inicio else min(datas_inicio))
    ultimo = inicio_semana(fim if fim else max(datas_fim))
    if cursor > ultimo:
        raise ValueError("Data inicial posterior a data final.")
    processados = linhas_geradas = 0
    prontos = set()
    if somente_pendentes:
        prontos = set(StatusMovimentoProdutoSemanal.objects.filter(
            semana_inicio__gte=cursor, semana_inicio__lte=ultimo,
            status=StatusMovimentoProdutoSemanal.STATUS_PRONTO,
            ultimo_sucesso_em__isnull=False,
        ).values_list("semana_inicio", flat=True))
    while cursor <= ultimo:
        if cursor not in prontos:
            linhas_geradas += reconstruir_movimento_produto_semanal(cursor)
            processados += 1
        cursor += timedelta(days=7)
    return {"periodos_processados": processados, "linhas_geradas": linhas_geradas}


def status_agregados_vendas_semanais() -> dict:
    limites = Venda.objects.exclude(status="C").aggregate(primeira=Min("data_venda"), ultima=Max("data_venda"))
    primeira, ultima = limites["primeira"], limites["ultima"]
    if primeira is None or ultima is None:
        return {"semanas_disponiveis": [], "semana_inicial": None, "ultima_data_disponivel": None, "atualizado_em": None}
    semanas = list(
        StatusMovimentoProdutoSemanal.objects.filter(
            ultimo_sucesso_em__isnull=False,
            semana_inicio__gte=inicio_semana(primeira), semana_inicio__lte=inicio_semana(ultima),
        )
        .order_by("-semana_inicio").values_list("semana_inicio", flat=True)
    )
    atualizado_em = StatusMovimentoProdutoSemanal.objects.filter(
        semana_inicio__gte=inicio_semana(primeira), semana_inicio__lte=inicio_semana(ultima),
    ).aggregate(ultimo=Max("atualizado_em"))["ultimo"]
    return {
        "semanas_disponiveis": [semana.isoformat() for semana in semanas],
        "semana_inicial": inicio_semana(ultima).isoformat() if ultima and inicio_semana(ultima) in semanas else (semanas[0].isoformat() if semanas else None),
        "ultima_data_disponivel": ultima.isoformat() if ultima else None,
        "atualizado_em": atualizado_em.isoformat() if atualizado_em else None,
    }


def _estrutura_familia(raiz_id: int):
    raiz = PlanoConta.objects.filter(id_conta=raiz_id, conta_pai__isnull=True).first()
    if raiz is None:
        raise PlanoConta.DoesNotExist
    nodes = list(
        PlanoConta.objects.filter(codigo_ordenacao__startswith=raiz.codigo_ordenacao)
        .order_by("codigo_ordenacao")
        .values("id_conta", "codigo_hierarquico", "nome_conta", "conta_pai_id")
    )
    ids = {node["id_conta"] for node in nodes}
    pais = {node["conta_pai_id"] for node in nodes if node["conta_pai_id"] in ids}
    folhas = ids - pais
    conflitos = list(
        Produto.objects.filter(categorias__id_conta__in=folhas)
        .values("id_produto", "produto")
        .annotate(qtd_categorias_familia=Count("categorias", distinct=True))
        .filter(qtd_categorias_familia__gt=1).order_by("id_produto")
    )
    if conflitos:
        raise CategoriasAmbiguasError(conflitos)
    return raiz, nodes, ids, pais, folhas


def _variacao(valor: Decimal, media: Decimal | None) -> str | None:
    if not media:
        return None
    return _decimal_texto((valor - media) / media * 100)


def _contexto_semanal(semana_inicio: date, periodo_equivalente: bool) -> dict:
    if inicio_semana(semana_inicio) != semana_inicio:
        raise ValueError("A semana deve comecar no domingo.")
    status_foco = StatusMovimentoProdutoSemanal.objects.filter(semana_inicio=semana_inicio).first()
    if status_foco is None or status_foco.ultimo_sucesso_em is None:
        raise MovimentoProdutoSemanal.DoesNotExist
    limites = Venda.objects.exclude(status="C").aggregate(primeira=Min("data_venda"), ultima=Max("data_venda"))
    primeira, ultima = limites["primeira"], limites["ultima"]
    if ultima is None or primeira is None or semana_inicio > inicio_semana(ultima):
        raise MovimentoProdutoSemanal.DoesNotExist
    parcial = semana_inicio == inicio_semana(ultima) and ultima < semana_inicio + timedelta(days=6)
    corte_dias = (ultima - semana_inicio).days if parcial else 6
    aplicar_corte = parcial and periodo_equivalente
    semanas = [semana_inicio - timedelta(days=7 * indice) for indice in range(20, -1, -1)]
    primeiro_historico = inicio_semana(primeira)
    estados = StatusMovimentoProdutoSemanal.objects.filter(semana_inicio__in=semanas)
    estado_por_semana = {estado.semana_inicio: estado for estado in estados}
    indices_com_snapshot = {
        indice for indice, semana in enumerate(semanas)
        if semana >= primeiro_historico and semana in estado_por_semana
        and estado_por_semana[semana].ultimo_sucesso_em is not None
    }
    indices_validos = [indice for indice in range(20) if indice in indices_com_snapshot]
    ultimas_cinco_indices = [indice for indice in range(15, 20) if indice in indices_com_snapshot]
    periodos = [
        {
            "inicio": semana.isoformat(), "fim": (semana + timedelta(days=6)).isoformat(),
            "data_corte": (semana + timedelta(days=corte_dias)).isoformat() if aplicar_corte or (indice == 5 and parcial) else None,
            "parcial": indice == 5 and parcial, "equivalente": aplicar_corte and indice < 5,
        }
        for indice, semana in enumerate(semanas[15:])
    ]
    desatualizados = [
        {"semana_inicio": semana.isoformat(), "status": estado_por_semana[semana].status if semana in estado_por_semana else "AUSENTE"}
        for semana in semanas if semana >= primeiro_historico and (
            semana not in estado_por_semana or estado_por_semana[semana].status != StatusMovimentoProdutoSemanal.STATUS_PRONTO
        )
    ]
    return {
        "semana_inicio": semana_inicio.isoformat(), "semanas": periodos,
        "periodo_equivalente": aplicar_corte, "semana_parcial": parcial,
        "periodos_considerados_20": len(indices_validos),
        "periodos_considerados_5": len(ultimas_cinco_indices),
        "ultima_data_disponivel": ultima.isoformat(),
        "atualizado_em": status_foco.ultimo_sucesso_em.isoformat(),
        "desatualizado": bool(desatualizados), "periodos_desatualizados": desatualizados,
        "datas": semanas, "indices_com_snapshot": indices_com_snapshot,
        "indices_validos": indices_validos, "ultimas_cinco_indices": ultimas_cinco_indices,
        "aplicar_corte": aplicar_corte, "corte_dias": corte_dias,
    }


def _contexto_publico(contexto: dict) -> dict:
    internos = {"datas", "indices_com_snapshot", "indices_validos", "ultimas_cinco_indices", "aplicar_corte", "corte_dias"}
    return {chave: valor for chave, valor in contexto.items() if chave not in internos}


def montar_analise_vendas_categorias_semanal(*, raiz_id: int, semana_inicio: date, metrica: str, periodo_equivalente: bool) -> dict:
    if metrica not in {"valor", "quantidade"}:
        raise ValueError("Metrica invalida. Use 'valor' ou 'quantidade'.")
    contexto = _contexto_semanal(semana_inicio, periodo_equivalente)
    raiz, nodes, ids, pais, folhas = _estrutura_familia(raiz_id)
    semanas = contexto["datas"]
    indices_com_snapshot = contexto["indices_com_snapshot"]
    indices_validos = contexto["indices_validos"]
    ultimas_cinco_indices = contexto["ultimas_cinco_indices"]
    aplicar_corte = contexto["aplicar_corte"]
    corte_dias = contexto["corte_dias"]
    fim_foco = semana_inicio + timedelta(days=6)

    if metrica == "valor":
        acumulados = {node_id: [ZERO for _ in range(21)] for node_id in ids}
    else:
        acumulados = {node_id: defaultdict(lambda: [ZERO for _ in range(21)]) for node_id in ids}
    campo = "receita_bruta" if metrica == "valor" else "quantidade"
    if aplicar_corte:
        rows = (
            MovimentoProdutoDiario.objects.filter(
                data__gte=semanas[0], data__lte=fim_foco,
                produto__categorias__id_conta__in=folhas,
            )
            .values("produto__categorias__id_conta", "data", "unidade_medida_id_origem", "unidade_sigla")
            .annotate(total=Sum(campo)).order_by()
        )
        for row in rows:
            periodo = inicio_semana(row["data"])
            indice = (periodo - semanas[0]).days // 7
            if not 0 <= indice < 21 or (row["data"] - periodo).days > corte_dias:
                continue
            folha_id = row["produto__categorias__id_conta"]
            if metrica == "valor":
                acumulados[folha_id][indice] += row["total"] or ZERO
            else:
                unidade = (row["unidade_medida_id_origem"], row["unidade_sigla"])
                acumulados[folha_id][unidade][indice] += row["total"] or ZERO
    else:
        rows = (
            MovimentoProdutoSemanal.objects.filter(
                semana_inicio__in=semanas, produto__categorias__id_conta__in=folhas,
            )
            .values("produto__categorias__id_conta", "semana_inicio", "unidade_medida_id_origem", "unidade_sigla")
            .annotate(total=Sum(campo)).order_by()
        )
        for row in rows:
            indice = (row["semana_inicio"] - semanas[0]).days // 7
            folha_id = row["produto__categorias__id_conta"]
            if metrica == "valor":
                acumulados[folha_id][indice] += row["total"] or ZERO
            else:
                unidade = (row["unidade_medida_id_origem"], row["unidade_sigla"])
                acumulados[folha_id][unidade][indice] += row["total"] or ZERO

    for node in reversed(nodes):
        pai_id = node["conta_pai_id"]
        if pai_id not in ids:
            continue
        if metrica == "valor":
            for indice, valor in enumerate(acumulados[node["id_conta"]]):
                acumulados[pai_id][indice] += valor
        else:
            for unidade, valores in acumulados[node["id_conta"]].items():
                for indice, valor in enumerate(valores):
                    acumulados[pai_id][unidade][indice] += valor

    nivel_raiz = len([parte for parte in raiz.codigo_hierarquico.split(".") if parte])
    linhas = []
    for node in nodes:
        linha = {
            "id_conta": node["id_conta"], "codigo_hierarquico": node["codigo_hierarquico"],
            "nome_conta": node["nome_conta"],
            "conta_pai_id": node["conta_pai_id"] if node["conta_pai_id"] in ids else None,
            "nivel": len([parte for parte in node["codigo_hierarquico"].split(".") if parte]) - nivel_raiz,
            "tem_filhos": node["id_conta"] in pais,
        }
        def serializar(valores):
            media_20 = sum((valores[i] for i in indices_validos), ZERO) / len(indices_validos) if indices_validos else None
            media_5 = sum((valores[i] for i in ultimas_cinco_indices), ZERO) / len(ultimas_cinco_indices) if ultimas_cinco_indices else None
            return {
                "valores": [_decimal_texto(valores[i]) if i in indices_com_snapshot else None for i in range(15, 21)],
                "media_20": _decimal_texto(media_20) if media_20 is not None else None,
                "media_5": _decimal_texto(media_5) if media_5 is not None else None,
                "variacao_5_vs_20_percentual": _variacao(media_5, media_20) if media_5 is not None else None,
                "variacao_5_percentual": _variacao(valores[20], media_5),
            }
        if metrica == "valor":
            linha.update(serializar(acumulados[node["id_conta"]]))
        else:
            linha["unidades"] = [
                {"id_unidade": unidade[0], "sigla": unidade[1], **serializar(valores)}
                for unidade, valores in sorted(acumulados[node["id_conta"]].items(), key=lambda item: (item[0][1], item[0][0]))
            ]
        linhas.append(linha)

    return {
        "familia": {"id_conta": raiz.id_conta, "codigo_hierarquico": raiz.codigo_hierarquico, "nome_conta": raiz.nome_conta},
        "metrica": metrica, **_contexto_publico(contexto),
        "linhas": linhas,
    }


def _movimentos_produtos_semanal(produto_ids: list[int], contexto: dict, campo: str):
    """Lê somente snapshots persistidos e devolve produto, índice, unidade e total."""
    if not produto_ids:
        return
    semanas = contexto["datas"]
    if contexto["aplicar_corte"]:
        rows = (
            MovimentoProdutoDiario.objects.filter(
                produto_id__in=produto_ids, data__gte=semanas[0],
                data__lte=semanas[20] + timedelta(days=6),
            )
            .values("produto_id", "data", "unidade_medida_id_origem", "unidade_sigla")
            .annotate(total=Sum(campo)).order_by()
        )
        for row in rows:
            periodo = inicio_semana(row["data"])
            indice = (periodo - semanas[0]).days // 7
            if indice not in contexto["indices_com_snapshot"] or (row["data"] - periodo).days > contexto["corte_dias"]:
                continue
            yield row["produto_id"], indice, (row["unidade_medida_id_origem"], row["unidade_sigla"]), row["total"] or ZERO
    else:
        rows = (
            MovimentoProdutoSemanal.objects.filter(
                produto_id__in=produto_ids, semana_inicio__in=semanas,
            )
            .values("produto_id", "semana_inicio", "unidade_medida_id_origem", "unidade_sigla")
            .annotate(total=Sum(campo)).order_by()
        )
        for row in rows:
            indice = (row["semana_inicio"] - semanas[0]).days // 7
            if indice not in contexto["indices_com_snapshot"]:
                continue
            yield row["produto_id"], indice, (row["unidade_medida_id_origem"], row["unidade_sigla"]), row["total"] or ZERO


def montar_analise_vendas_produtos_semanal(
    *, raiz_id: int, categoria_id: int, semana_inicio: date, metrica: str,
    periodo_equivalente: bool, incluir_inativos: bool = False, search: str = "",
    pagina: int = 1, por_pagina: int = 100,
) -> dict:
    if metrica not in {"valor", "quantidade"}:
        raise ValueError("Metrica invalida. Use 'valor' ou 'quantidade'.")
    if pagina < 1:
        raise ValueError("O parametro 'page' deve ser maior ou igual a 1.")
    contexto = _contexto_semanal(semana_inicio, periodo_equivalente)
    raiz, nodes, ids, pais, folhas = _estrutura_familia(raiz_id)
    categoria = next((node for node in nodes if node["id_conta"] == categoria_id), None)
    if categoria is None:
        if PlanoConta.objects.filter(id_conta=categoria_id).exists():
            raise ValueError("A categoria selecionada nao pertence a familia informada.")
        raise PlanoConta.DoesNotExist
    por_id = {node["id_conta"]: node for node in nodes}
    folhas_subarvore = []
    for folha_id in folhas:
        atual = folha_id
        while atual in por_id:
            if atual == categoria_id:
                folhas_subarvore.append(folha_id)
                break
            atual = por_id[atual]["conta_pai_id"]
    vinculo_folha = Produto.categorias.through.objects.filter(
        produto_id=OuterRef("pk"), planoconta_id__in=folhas_subarvore,
    )
    nome_exibicao = Coalesce(NullIf(Trim("nome_gerencial"), Value("")), F("produto"), output_field=CharField())
    produtos = Produto.objects.annotate(
        pertence_subarvore=Exists(vinculo_folha),
        nome_exibicao=nome_exibicao,
        id_produto_texto=Cast("id_produto", output_field=CharField()),
    ).filter(pertence_subarvore=True)
    termo = str(search or "").strip()
    if termo:
        produtos = produtos.filter(
            Q(id_produto_texto__icontains=termo) | Q(nome_gerencial__icontains=termo) | Q(produto__icontains=termo)
        )
    inativos_ocultos = produtos.filter(status__iexact="INATIVO").count()
    permitidos = Q(status__iexact="ATIVO")
    if incluir_inativos:
        permitidos |= Q(status__iexact="INATIVO")
    candidatos = list(produtos.filter(permitidos).values("id_produto", "nome_exibicao", "status"))
    produto_ids = [produto["id_produto"] for produto in candidatos]

    # A ordem usa a mesma média financeira de 20 períodos exibida na matriz.
    # A semana foco nunca entra nessa média, inclusive quando ainda está parcial.
    indices_vinte = contexto["indices_validos"]
    receitas_vinte = defaultdict(lambda: ZERO)
    if produto_ids and indices_vinte:
        semanas_referencia = {contexto["datas"][indice] for indice in indices_vinte}
        if contexto["aplicar_corte"]:
            receitas = (
                MovimentoProdutoDiario.objects.filter(
                    produto_id__in=produto_ids, data__gte=contexto["datas"][0], data__lt=semana_inicio,
                )
                .values("produto_id", "data").annotate(total=Sum("receita_bruta")).order_by()
            )
            for receita in receitas:
                inicio = inicio_semana(receita["data"])
                if inicio in semanas_referencia and (receita["data"] - inicio).days <= contexto["corte_dias"]:
                    receitas_vinte[receita["produto_id"]] += receita["total"] or ZERO
        else:
            receitas = (
                MovimentoProdutoSemanal.objects.filter(
                    produto_id__in=produto_ids, semana_inicio__in=semanas_referencia,
                )
                .values("produto_id").annotate(total=Sum("receita_bruta")).order_by()
            )
            for receita in receitas:
                receitas_vinte[receita["produto_id"]] = receita["total"] or ZERO
    indices_cinco = contexto["ultimas_cinco_indices"]
    def chave_ordenacao(produto):
        media_vinte = receitas_vinte[produto["id_produto"]] / len(indices_vinte) if indices_vinte else ZERO
        return (-media_vinte, produto["nome_exibicao"].casefold(), produto["id_produto"])
    candidatos.sort(key=chave_ordenacao)
    paginador = Paginator(candidatos, por_pagina)
    pagina_obj = paginador.get_page(pagina)
    produtos_pagina = list(pagina_obj.object_list)
    ids_pagina = [produto["id_produto"] for produto in produtos_pagina]

    if metrica == "valor":
        acumulados = {produto_id: [ZERO for _ in range(21)] for produto_id in ids_pagina}
    else:
        acumulados = {produto_id: defaultdict(lambda: [ZERO for _ in range(21)]) for produto_id in ids_pagina}
    for produto_id, indice, unidade, total in _movimentos_produtos_semanal(
        ids_pagina, contexto, "receita_bruta" if metrica == "valor" else "quantidade",
    ):
        if metrica == "valor":
            acumulados[produto_id][indice] += total
        else:
            acumulados[produto_id][unidade][indice] += total

    indices_validos = contexto["indices_validos"]
    indices_snapshot = contexto["indices_com_snapshot"]
    def serializar(valores):
        media_20 = sum((valores[i] for i in indices_validos), ZERO) / len(indices_validos) if indices_validos else None
        media_5 = sum((valores[i] for i in indices_cinco), ZERO) / len(indices_cinco) if indices_cinco else None
        return {
            "valores": [_decimal_texto(valores[i]) if i in indices_snapshot else None for i in range(15, 21)],
            "media_20": _decimal_texto(media_20) if media_20 is not None else None,
            "media_5": _decimal_texto(media_5) if media_5 is not None else None,
            "variacao_5_vs_20_percentual": _variacao(media_5, media_20) if media_5 is not None else None,
            "variacao_5_percentual": _variacao(valores[20], media_5),
        }
    linhas = []
    for produto in produtos_pagina:
        produto_id = produto["id_produto"]
        linha = {"id_produto": produto_id, "nome_produto": produto["nome_exibicao"], "status": produto["status"]}
        if metrica == "valor":
            linha.update(serializar(acumulados[produto_id]))
        else:
            linha["unidades"] = [
                {"id_unidade": unidade[0], "sigla": unidade[1], **serializar(valores)}
                for unidade, valores in sorted(acumulados[produto_id].items(), key=lambda item: (item[0][1], item[0][0]))
            ]
        linhas.append(linha)
    return {
        "familia": {"id_conta": raiz.id_conta, "codigo_hierarquico": raiz.codigo_hierarquico, "nome_conta": raiz.nome_conta},
        "categoria": {"id_conta": categoria_id, "codigo_hierarquico": categoria["codigo_hierarquico"], "nome_conta": categoria["nome_conta"]},
        "metrica": metrica, **_contexto_publico(contexto), "linhas": linhas,
        "paginacao": {"pagina": pagina_obj.number, "por_pagina": por_pagina, "total_produtos": paginador.count, "total_paginas": paginador.num_pages},
        "inativos_ocultos": inativos_ocultos,
    }
