"""Leitura anual das vendas a partir dos snapshots mensais e diários existentes."""

import calendar
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import CharField, Exists, F, Max, Min, OuterRef, Q, Sum, Value
from django.db.models.functions import Cast, Coalesce, NullIf, Trim
from django.utils import timezone

from apps.cadastros.models import PlanoConta, Produto
from apps.vendas.models import Venda

from .models import (
    MovimentoProdutoDiario, MovimentoProdutoMensal,
    StatusMovimentoProdutoMensal, StatusMovimentoProdutoSemanal,
)
from .services import AgregadoDiarioIncompletoError, _decimal_texto
from .services_vendas_semanais import _estrutura_familia, inicio_semana


ZERO = Decimal("0")


def status_agregados_vendas_anuais() -> dict:
    limites = Venda.objects.exclude(status="C").aggregate(primeira=Min("data_venda"), ultima=Max("data_venda"))
    primeira, ultima = limites["primeira"], limites["ultima"]
    if primeira is None:
        return {"anos_disponiveis": [], "ultima_data_disponivel": None}
    anos = set(StatusMovimentoProdutoMensal.objects.filter(
        ultimo_sucesso_em__isnull=False, ano__gte=primeira.year, ano__lte=ultima.year,
    ).values_list("ano", flat=True))
    anos.update(MovimentoProdutoMensal.objects.filter(
        ano__gte=primeira.year, ano__lte=ultima.year,
    ).values_list("ano", flat=True).distinct())
    return {"anos_disponiveis": sorted(anos, reverse=True), "ultima_data_disponivel": ultima.isoformat()}


def _fim_equivalente(ano: int, ultima: date) -> date:
    return date(ano, ultima.month, min(ultima.day, calendar.monthrange(ano, ultima.month)[1]))


def _validar_semanas(inicio: date, fim: date, estados: dict, desatualizados: list):
    cursor = inicio_semana(inicio)
    while cursor <= fim:
        estado = estados.get(cursor)
        if estado is None or estado.ultimo_sucesso_em is None:
            raise AgregadoDiarioIncompletoError(
                f"Agregado diário incompleto: semana de {cursor.isoformat()} sem snapshot válido."
            )
        if estado.status != StatusMovimentoProdutoSemanal.STATUS_PRONTO:
            desatualizados.append({"semana_inicio": cursor.isoformat(), "status": estado.status})
        cursor += timedelta(days=7)


def _contexto_anual(ano: int, periodo_equivalente: bool) -> dict:
    limites = Venda.objects.exclude(status="C").aggregate(primeira=Min("data_venda"), ultima=Max("data_venda"))
    primeira, ultima = limites["primeira"], limites["ultima"]
    if primeira is None or not primeira.year <= ano <= ultima.year:
        raise Venda.DoesNotExist
    ultima_venda_foco = Venda.objects.filter(data_venda__year=ano).exclude(status="C").aggregate(
        ultima=Max("data_venda")
    )["ultima"]
    ultima_foco = ultima_venda_foco or date(ano, 12, 31)

    anos = list(range(max(primeira.year, ano - 3), ano + 1))
    parcial = ano == timezone.localdate().year and ultima_venda_foco is not None and ultima_foco < date(ano, 12, 31)
    equivalente = bool(periodo_equivalente and parcial)
    estados_semanais = {
        item.semana_inicio: item for item in StatusMovimentoProdutoSemanal.objects.filter(
            semana_inicio__gte=inicio_semana(date(anos[0], 1, 1)),
            semana_inicio__lte=ultima_foco,
        )
    }
    estados_mensais = {
        (item.ano, item.mes): item for item in StatusMovimentoProdutoMensal.objects.filter(
            ano__gte=anos[0], ano__lte=ano,
        )
    }
    desatualizados = []
    periodos = []
    for ano_periodo in anos:
        inicio = date(ano_periodo, 1, 1)
        fim = (_fim_equivalente(ano_periodo, ultima_foco) if equivalente else
               ultima_foco if ano_periodo == ano and parcial else date(ano_periodo, 12, 31))
        if equivalente:
            _validar_semanas(inicio, fim, estados_semanais, desatualizados)
        else:
            # Um mês sem status só é zero se o diário cobrir o mês e não houver
            # movimento mensal nem diário. Isso preserva lacunas como indisponíveis.
            for mes in range(1, fim.month + 1):
                chave = (ano_periodo, mes)
                estado = estados_mensais.get(chave)
                if estado is None or estado.ultimo_sucesso_em is None:
                    mes_inicio = date(ano_periodo, mes, 1)
                    mes_fim = min(fim, date(ano_periodo, mes, calendar.monthrange(ano_periodo, mes)[1]))
                    _validar_semanas(mes_inicio, mes_fim, estados_semanais, desatualizados)
                    if MovimentoProdutoMensal.objects.filter(ano=ano_periodo, mes=mes).exists() or MovimentoProdutoDiario.objects.filter(data__gte=mes_inicio, data__lte=mes_fim).exists():
                        raise AgregadoDiarioIncompletoError(
                            f"Agregado mensal incompleto: {ano_periodo}-{mes:02d} sem snapshot válido."
                        )
                elif estado.status != StatusMovimentoProdutoMensal.STATUS_PRONTO:
                    desatualizados.append({"ano": ano_periodo, "mes": mes, "status": estado.status})
        periodos.append({
            "ano": ano_periodo, "inicio": inicio.isoformat(), "fim": fim.isoformat(),
            "data_corte": fim.isoformat(), "parcial": ano_periodo == ano and parcial,
            "equivalente": equivalente and ano_periodo != ano,
        })
    atualizado = max(
        (estado.ultimo_sucesso_em for estado in list(estados_mensais.values()) + list(estados_semanais.values())
         if estado.ultimo_sucesso_em), default=None,
    )
    return {
        "ano_consultado": ano, "anos": periodos, "ano_parcial": parcial,
        "periodo_equivalente": equivalente,
        "ultima_data_disponivel": ultima_venda_foco.isoformat() if ultima_venda_foco else None,
        "atualizado_em": atualizado.isoformat() if atualizado else None,
        "desatualizado": bool(desatualizados), "periodos_desatualizados": desatualizados,
        "_usar_diario": equivalente,
    }


def _fonte_periodo(periodo: dict, usar_diario: bool):
    if usar_diario:
        return MovimentoProdutoDiario.objects.filter(
            data__gte=periodo["inicio"], data__lte=periodo["fim"]
        )
    return MovimentoProdutoMensal.objects.filter(
        ano=periodo["ano"], mes__lte=date.fromisoformat(periodo["fim"]).month,
    )


def _variacao(valores):
    if len(valores) < 2 or not valores[-2]:
        return None
    return _decimal_texto((valores[-1] - valores[-2]) / valores[-2] * 100)


def _variacao_historica(valores):
    """Média das taxas ano a ano anteriores ao foco; sem descartar bases zero."""
    if len(valores) < 3:
        return None
    taxas = []
    for indice in range(1, len(valores) - 1):
        base = valores[indice - 1]
        if not base:
            return None
        taxas.append((valores[indice] - base) / base * 100)
    return _decimal_texto(sum(taxas, ZERO) / len(taxas))


def _serializar(valores):
    return {
        "valores": [_decimal_texto(valor) for valor in valores],
        "variacao_historica_percentual": _variacao_historica(valores),
        "variacao_percentual": _variacao(valores),
    }


def montar_analise_vendas_categorias_anual(*, raiz_id: int, ano: int, metrica: str, periodo_equivalente: bool) -> dict:
    if metrica not in {"valor", "quantidade"}:
        raise ValueError("Metrica invalida. Use 'valor' ou 'quantidade'.")
    raiz, nodes, ids, pais, folhas = _estrutura_familia(raiz_id)
    contexto = _contexto_anual(ano, periodo_equivalente)
    tamanho = len(contexto["anos"])
    if metrica == "valor":
        acumulados = {node_id: [ZERO] * tamanho for node_id in ids}
    else:
        acumulados = {node_id: defaultdict(lambda: [ZERO] * tamanho) for node_id in ids}
    campo = "receita_bruta" if metrica == "valor" else "quantidade"
    for indice, periodo in enumerate(contexto["anos"]):
        rows = (_fonte_periodo(periodo, contexto["_usar_diario"])
                .filter(produto__categorias__id_conta__in=folhas)
                .values("produto__categorias__id_conta", "unidade_medida_id_origem", "unidade_sigla")
                .annotate(total=Sum(campo)).order_by())
        for row in rows:
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
            for indice, total in enumerate(acumulados[node["id_conta"]]):
                acumulados[pai_id][indice] += total
        else:
            for unidade, valores in acumulados[node["id_conta"]].items():
                for indice, total in enumerate(valores):
                    acumulados[pai_id][unidade][indice] += total
    nivel_raiz = len(raiz.codigo_hierarquico.split("."))
    linhas = []
    for node in nodes:
        node_id = node["id_conta"]
        linha = {
            "id_conta": node_id, "codigo_hierarquico": node["codigo_hierarquico"],
            "nome_conta": node["nome_conta"],
            "conta_pai_id": node["conta_pai_id"] if node["conta_pai_id"] in ids else None,
            "nivel": len(node["codigo_hierarquico"].split(".")) - nivel_raiz,
            "tem_filhos": node_id in pais,
        }
        if metrica == "valor":
            linha.update(_serializar(acumulados[node_id]))
        else:
            linha["unidades"] = [
                {"id_unidade": unidade[0], "sigla": unidade[1], **_serializar(valores)}
                for unidade, valores in sorted(acumulados[node_id].items(), key=lambda x: (x[0][1], x[0][0]))
            ]
        linhas.append(linha)
    contexto.pop("_usar_diario")
    return {
        "familia": {"id_conta": raiz.id_conta, "codigo_hierarquico": raiz.codigo_hierarquico, "nome_conta": raiz.nome_conta},
        "metrica": metrica, **contexto, "linhas": linhas,
    }


def montar_analise_vendas_produtos_anual(
    *, raiz_id: int, categoria_id: int, ano: int, metrica: str, periodo_equivalente: bool,
    incluir_inativos: bool = False, search: str = "", pagina: int = 1, por_pagina: int = 100,
) -> dict:
    if metrica not in {"valor", "quantidade"}:
        raise ValueError("Metrica invalida. Use 'valor' ou 'quantidade'.")
    if pagina < 1:
        raise ValueError("O parametro 'page' deve ser maior ou igual a 1.")
    raiz, nodes, ids, _, folhas = _estrutura_familia(raiz_id)
    contexto = _contexto_anual(ano, periodo_equivalente)
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
    vinculo = Produto.categorias.through.objects.filter(
        produto_id=OuterRef("pk"), planoconta_id__in=folhas_subarvore,
    )
    nome = Coalesce(NullIf(Trim("nome_gerencial"), Value("")), F("produto"), output_field=CharField())
    produtos = Produto.objects.annotate(
        pertence=Exists(vinculo), nome_exibicao=nome,
        id_produto_texto=Cast("id_produto", output_field=CharField()),
    ).filter(pertence=True)
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
    foco = contexto["anos"][-1]
    ids_candidatos = [item["id_produto"] for item in candidatos]
    receita_foco = defaultdict(lambda: ZERO)
    if ids_candidatos:
        for row in (_fonte_periodo(foco, contexto["_usar_diario"])
                    .filter(produto_id__in=ids_candidatos).values("produto_id")
                    .annotate(total=Sum("receita_bruta")).order_by()):
            receita_foco[row["produto_id"]] = row["total"] or ZERO
    candidatos.sort(key=lambda item: (
        -receita_foco[item["id_produto"]], item["nome_exibicao"].casefold(), item["id_produto"]
    ))
    paginador = Paginator(candidatos, por_pagina)
    pagina_obj = paginador.get_page(pagina)
    produtos_pagina = list(pagina_obj.object_list)
    ids_pagina = [item["id_produto"] for item in produtos_pagina]
    tamanho = len(contexto["anos"])
    if metrica == "valor":
        acumulados = {produto_id: [ZERO] * tamanho for produto_id in ids_pagina}
    else:
        acumulados = {produto_id: defaultdict(lambda: [ZERO] * tamanho) for produto_id in ids_pagina}
    campo = "receita_bruta" if metrica == "valor" else "quantidade"
    for indice, periodo in enumerate(contexto["anos"]):
        rows = (_fonte_periodo(periodo, contexto["_usar_diario"])
                .filter(produto_id__in=ids_pagina)
                .values("produto_id", "unidade_medida_id_origem", "unidade_sigla")
                .annotate(total=Sum(campo)).order_by())
        for row in rows:
            produto_id = row["produto_id"]
            if metrica == "valor":
                acumulados[produto_id][indice] += row["total"] or ZERO
            else:
                unidade = (row["unidade_medida_id_origem"], row["unidade_sigla"])
                acumulados[produto_id][unidade][indice] += row["total"] or ZERO
    linhas = []
    for item in produtos_pagina:
        produto_id = item["id_produto"]
        linha = {"id_produto": produto_id, "nome_produto": item["nome_exibicao"], "status": item["status"]}
        if metrica == "valor":
            linha.update(_serializar(acumulados[produto_id]))
        else:
            linha["unidades"] = [
                {"id_unidade": unidade[0], "sigla": unidade[1], **_serializar(valores)}
                for unidade, valores in sorted(acumulados[produto_id].items(), key=lambda x: (x[0][1], x[0][0]))
            ]
        linhas.append(linha)
    contexto.pop("_usar_diario")
    return {
        "familia": {"id_conta": raiz.id_conta, "codigo_hierarquico": raiz.codigo_hierarquico, "nome_conta": raiz.nome_conta},
        "categoria": {"id_conta": categoria_id, "codigo_hierarquico": categoria["codigo_hierarquico"], "nome_conta": categoria["nome_conta"]},
        "metrica": metrica, **contexto, "linhas": linhas,
        "paginacao": {"pagina": pagina_obj.number, "por_pagina": por_pagina, "total_produtos": paginador.count, "total_paginas": paginador.num_pages},
        "inativos_ocultos": inativos_ocultos,
    }
