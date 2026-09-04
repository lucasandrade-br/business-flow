import calendar
import logging
from collections import defaultdict
from decimal import Decimal
from datetime import date, time, timedelta

from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import CharField, DecimalField, Exists, F, Max, OuterRef, Q, Subquery, Sum, Count, Value
from django.db.models.functions import Cast, Coalesce, NullIf, Trim, TruncMonth
from django.utils import timezone

from apps.cadastros.models import Fornecedor, PlanoConta, Produto, TipoVenda
from apps.compras.models import Compra, ItemCompra
from apps.vendas.models import ItemVenda, Venda
from apps.analise.models import (
    DashboardKpiVenda,
    DashboardKpiCompra,
    DreMensalConsolidada,
    MovimentoDiario,
    MovimentoCompraProdutoMensal,
    MovimentoProdutoMensal,
    StatusMovimentoCompraProdutoMensal,
    StatusMovimentoProdutoMensal,
)

_MESES_LABELS = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
_STATUS_CANCELADO = "C"
_STATUS_CANCELADA_COMPRA = "CANCELADA"
logger = logging.getLogger(__name__)


class CategoriasAmbiguasError(Exception):
    def __init__(self, produtos: list[dict]):
        self.produtos = produtos
        super().__init__("Existem produtos vinculados a mais de uma folha desta familia.")


def _decimal_texto(valor: Decimal) -> str:
    return format(valor or Decimal("0"), "f")


def detectar_mes_aberto(ano: int, ultima_data: date | None) -> int | None:
    """Identifica o último mês parcial somente para o ano calendário atual."""
    if ultima_data is None or ano != timezone.localdate().year:
        return None
    ultimo_dia_mes = calendar.monthrange(ano, ultima_data.month)[1]
    return ultima_data.month if ultima_data.day < ultimo_dia_mes else None


def contexto_mes_aberto_vendas(ano: int) -> dict:
    ultima_data = (
        Venda.objects.filter(data_venda__year=ano)
        .exclude(status=_STATUS_CANCELADO)
        .aggregate(ultima=Max("data_venda"))["ultima"]
    )
    return {
        "ultima_data_disponivel": ultima_data.isoformat() if ultima_data else None,
        "mes_aberto": detectar_mes_aberto(ano, ultima_data),
    }


def contexto_mes_aberto_compras(ano: int) -> dict:
    ultima_data = (
        Compra.objects.filter(data_emissao__year=ano)
        .exclude(nfe_status__iexact=_STATUS_CANCELADA_COMPRA)
        .aggregate(ultima=Max("data_emissao"))["ultima"]
    )
    return {
        "ultima_data_disponivel": ultima_data.isoformat() if ultima_data else None,
        "mes_aberto": detectar_mes_aberto(ano, ultima_data),
    }


def status_agregados_vendas() -> dict:
    anos = list(
        MovimentoProdutoMensal.objects.values_list("ano", flat=True).distinct().order_by("-ano")
    )
    estados = list(
        StatusMovimentoProdutoMensal.objects.order_by("-ano", "mes").values(
            "ano", "mes", "status", "ultimo_sucesso_em", "atualizado_em"
        )
    )
    for item in estados:
        item["ultimo_sucesso_em"] = (
            item["ultimo_sucesso_em"].isoformat() if item["ultimo_sucesso_em"] else None
        )
        item["atualizado_em"] = item["atualizado_em"].isoformat()
    return {"anos_disponiveis": anos, "periodos": estados}


def reconstruir_movimento_produto_mensal(ano: int, mes: int) -> int:
    """Reconstrói um mes de forma atomica e preserva o snapshot anterior em caso de falha."""
    if mes < 1 or mes > 12:
        raise ValueError("Mes invalido.")
    inicio_periodo = date(ano, mes, 1)
    fim_periodo = date(ano + 1, 1, 1) if mes == 12 else date(ano, mes + 1, 1)

    status_obj, _ = StatusMovimentoProdutoMensal.objects.update_or_create(
        ano=ano,
        mes=mes,
        defaults={"status": StatusMovimentoProdutoMensal.STATUS_PROCESSANDO, "erro": ""},
    )

    try:
        linhas = list(
            ItemVenda.objects.filter(
                venda__data_venda__gte=inicio_periodo,
                venda__data_venda__lt=fim_periodo,
                cancelado=False,
                quantidade__gte=0,
                valor_total_item__gte=0,
            )
            .exclude(venda__status=_STATUS_CANCELADO)
            .values("produto_id", "unidade_medida_id", "unidade_medida__sigla")
            .annotate(receita_bruta=Sum("valor_total_item"), quantidade_total=Sum("quantidade"))
            .order_by()
        )

        novos = [
            MovimentoProdutoMensal(
                ano=ano,
                mes=mes,
                produto_id=linha["produto_id"],
                unidade_medida_id_origem=linha["unidade_medida_id"] or MovimentoProdutoMensal.SEM_UNIDADE_ID,
                unidade_sigla=(linha["unidade_medida__sigla"] or MovimentoProdutoMensal.SEM_UNIDADE_SIGLA),
                receita_bruta=linha["receita_bruta"] or Decimal("0"),
                quantidade=linha["quantidade_total"] or Decimal("0"),
            )
            for linha in linhas
        ]

        with transaction.atomic():
            MovimentoProdutoMensal.objects.filter(ano=ano, mes=mes).delete()
            MovimentoProdutoMensal.objects.bulk_create(novos, batch_size=2000)
            status_obj.status = StatusMovimentoProdutoMensal.STATUS_PRONTO
            status_obj.erro = ""
            status_obj.ultimo_sucesso_em = timezone.now()
            status_obj.save(update_fields=["status", "erro", "ultimo_sucesso_em", "atualizado_em"])
        return len(novos)
    except Exception as exc:
        StatusMovimentoProdutoMensal.objects.filter(pk=status_obj.pk).update(
            status=StatusMovimentoProdutoMensal.STATUS_FALHA,
            erro=str(exc)[:4000],
            atualizado_em=timezone.now(),
        )
        logger.exception("Falha ao reconstruir movimento mensal de produtos para %s/%02d", ano, mes)
        raise


def reconstruir_movimentos_produto_mensal(ano: int | None = None) -> dict:
    """Reconstrói todos os periodos encontrados ou somente os de um ano."""
    vendas = Venda.objects.all()
    movimentos = MovimentoProdutoMensal.objects.all()
    estados = StatusMovimentoProdutoMensal.objects.all()
    if ano is not None:
        vendas = vendas.filter(data_venda__year=ano)
        movimentos = movimentos.filter(ano=ano)
        estados = estados.filter(ano=ano)

    periodos = {(data.year, data.month) for data in vendas.dates("data_venda", "month")}
    periodos.update(movimentos.values_list("ano", "mes").distinct())
    periodos.update(estados.values_list("ano", "mes").distinct())

    total_linhas = 0
    for ano_periodo, mes_periodo in sorted(periodos):
        total_linhas += reconstruir_movimento_produto_mensal(ano_periodo, mes_periodo)
    return {"periodos_processados": len(periodos), "linhas_geradas": total_linhas}


def montar_analise_vendas_categorias(*, ano: int, raiz_id: int, metrica: str) -> dict:
    if metrica not in {"valor", "quantidade"}:
        raise ValueError("Metrica invalida. Use 'valor' ou 'quantidade'.")

    raiz = PlanoConta.objects.filter(id_conta=raiz_id, conta_pai__isnull=True).first()
    if raiz is None:
        raise PlanoConta.DoesNotExist
    if not MovimentoProdutoMensal.objects.filter(ano=ano).exists():
        raise MovimentoProdutoMensal.DoesNotExist

    nodes = list(
        PlanoConta.objects.filter(codigo_ordenacao__startswith=raiz.codigo_ordenacao)
        .order_by("codigo_ordenacao")
        .values("id_conta", "codigo_hierarquico", "nome_conta", "conta_pai_id")
    )
    node_ids = {node["id_conta"] for node in nodes}
    pais_com_filhas = {node["conta_pai_id"] for node in nodes if node["conta_pai_id"] in node_ids}
    folhas = node_ids - pais_com_filhas

    conflitos = list(
        Produto.objects.filter(categorias__id_conta__in=folhas)
        .values("id_produto", "produto")
        .annotate(qtd_categorias_familia=Count("categorias", distinct=True))
        .filter(qtd_categorias_familia__gt=1)
        .order_by("id_produto")
    )
    if conflitos:
        raise CategoriasAmbiguasError(conflitos)

    if metrica == "valor":
        acumulados = {node_id: [Decimal("0") for _ in range(12)] for node_id in node_ids}
        agregados = (
            MovimentoProdutoMensal.objects.filter(
                ano=ano,
                produto__categorias__id_conta__in=folhas,
            )
            .values("produto__categorias__id_conta", "mes")
            .annotate(total=Sum("receita_bruta"))
            .order_by()
        )
        for row in agregados:
            acumulados[row["produto__categorias__id_conta"]][row["mes"] - 1] += row["total"] or Decimal("0")
    else:
        acumulados = {node_id: defaultdict(lambda: [Decimal("0") for _ in range(12)]) for node_id in node_ids}
        agregados = (
            MovimentoProdutoMensal.objects.filter(
                ano=ano,
                produto__categorias__id_conta__in=folhas,
            )
            .values(
                "produto__categorias__id_conta",
                "mes",
                "unidade_medida_id_origem",
                "unidade_sigla",
            )
            .annotate(total=Sum("quantidade"))
            .order_by()
        )
        for row in agregados:
            chave_unidade = (row["unidade_medida_id_origem"], row["unidade_sigla"])
            acumulados[row["produto__categorias__id_conta"]][chave_unidade][row["mes"] - 1] += (
                row["total"] or Decimal("0")
            )

    # Os filhos aparecem depois dos pais em codigo_ordenacao; a ordem reversa propaga os totais.
    for node in reversed(nodes):
        pai_id = node["conta_pai_id"]
        if pai_id not in node_ids:
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
            "id_conta": node["id_conta"],
            "codigo_hierarquico": node["codigo_hierarquico"],
            "nome_conta": node["nome_conta"],
            "conta_pai_id": node["conta_pai_id"] if node["conta_pai_id"] in node_ids else None,
            "nivel": len([p for p in node["codigo_hierarquico"].split(".") if p]) - nivel_raiz,
            "tem_filhos": node["id_conta"] in pais_com_filhas,
        }
        if metrica == "valor":
            valores = acumulados[node["id_conta"]]
            linha["valores"] = [_decimal_texto(valor) for valor in valores]
            linha["total"] = _decimal_texto(sum(valores, Decimal("0")))
        else:
            linha["unidades"] = [
                {
                    "id_unidade": unidade[0],
                    "sigla": unidade[1],
                    "valores": [_decimal_texto(valor) for valor in valores],
                    "total": _decimal_texto(sum(valores, Decimal("0"))),
                }
                for unidade, valores in sorted(
                    acumulados[node["id_conta"]].items(), key=lambda item: (item[0][1], item[0][0])
                )
            ]
        linhas.append(linha)

    estados = list(
        StatusMovimentoProdutoMensal.objects.filter(ano=ano).order_by("mes")
    )
    periodos_desatualizados = [
        {"mes": item.mes, "status": item.status}
        for item in estados
        if item.status != StatusMovimentoProdutoMensal.STATUS_PRONTO
    ]
    ultimo_sucesso = max(
        (item.ultimo_sucesso_em for item in estados if item.ultimo_sucesso_em),
        default=None,
    )

    contexto_mes_aberto = contexto_mes_aberto_vendas(ano)
    return {
        "ano_consultado": ano,
        "metrica": metrica,
        "familia": {
            "id_conta": raiz.id_conta,
            "codigo_hierarquico": raiz.codigo_hierarquico,
            "nome_conta": raiz.nome_conta,
        },
        "meses": _MESES_LABELS,
        **contexto_mes_aberto,
        "linhas": linhas,
        "desatualizado": bool(periodos_desatualizados),
        "periodos_desatualizados": periodos_desatualizados,
        "atualizado_em": ultimo_sucesso.isoformat() if ultimo_sucesso else None,
    }


def montar_analise_vendas_produtos(
    *,
    ano: int,
    raiz_id: int,
    categoria_id: int,
    metrica: str,
    incluir_inativos: bool = False,
    search: str = "",
    pagina: int = 1,
    por_pagina: int = 100,
) -> dict:
    """Monta a matriz mensal paginada de produtos de uma subarvore do plano de contas."""
    if metrica not in {"valor", "quantidade"}:
        raise ValueError("Metrica invalida. Use 'valor' ou 'quantidade'.")
    if pagina < 1:
        raise ValueError("O parametro 'page' deve ser maior ou igual a 1.")

    raiz = PlanoConta.objects.filter(id_conta=raiz_id, conta_pai__isnull=True).first()
    if raiz is None:
        raise PlanoConta.DoesNotExist
    categoria = PlanoConta.objects.filter(id_conta=categoria_id).first()
    if categoria is None:
        raise PlanoConta.DoesNotExist
    if not str(categoria.codigo_ordenacao).startswith(str(raiz.codigo_ordenacao)):
        raise ValueError("A categoria selecionada nao pertence a familia informada.")
    if not MovimentoProdutoMensal.objects.filter(ano=ano).exists():
        raise MovimentoProdutoMensal.DoesNotExist

    categorias_subarvore = PlanoConta.objects.filter(
        codigo_ordenacao__startswith=categoria.codigo_ordenacao,
    )
    folhas = categorias_subarvore.exclude(
        Exists(PlanoConta.objects.filter(conta_pai_id=OuterRef("pk")))
    ).values_list("id_conta", flat=True)

    vinculo_folha = Produto.categorias.through.objects.filter(
        produto_id=OuterRef("pk"),
        planoconta_id__in=folhas,
    )
    receita_anual = (
        MovimentoProdutoMensal.objects.filter(ano=ano, produto_id=OuterRef("pk"))
        .values("produto_id")
        .annotate(total=Sum("receita_bruta"))
        .values("total")[:1]
    )
    campo_decimal = DecimalField(max_digits=24, decimal_places=6)
    nome_exibicao = Coalesce(
        NullIf(Trim("nome_gerencial"), Value("")),
        F("produto"),
        output_field=CharField(),
    )

    produtos_base = Produto.objects.annotate(
        pertence_subarvore=Exists(vinculo_folha),
        receita_anual=Coalesce(
            Subquery(receita_anual, output_field=campo_decimal),
            Value(Decimal("0"), output_field=campo_decimal),
        ),
        nome_exibicao=nome_exibicao,
        id_produto_texto=Cast("id_produto", output_field=CharField()),
    ).filter(pertence_subarvore=True)

    termo = str(search or "").strip()
    if termo:
        produtos_base = produtos_base.filter(
            Q(id_produto_texto__icontains=termo)
            | Q(nome_gerencial__icontains=termo)
            | Q(produto__icontains=termo)
        )

    inativos_ocultos = produtos_base.filter(status__iexact="INATIVO").count()
    status_permitidos = Q(status__iexact="ATIVO")
    if incluir_inativos:
        status_permitidos |= Q(status__iexact="INATIVO")

    produtos_ordenados = produtos_base.filter(status_permitidos).order_by(
        "-receita_anual", "nome_exibicao", "id_produto"
    )
    paginador = Paginator(produtos_ordenados, por_pagina)
    pagina_obj = paginador.get_page(pagina)
    produtos_pagina = list(pagina_obj.object_list)
    produto_ids = [produto.id_produto for produto in produtos_pagina]

    if metrica == "valor":
        acumulados = {produto_id: [Decimal("0") for _ in range(12)] for produto_id in produto_ids}
        movimentos = (
            MovimentoProdutoMensal.objects.filter(ano=ano, produto_id__in=produto_ids)
            .values("produto_id", "mes")
            .annotate(total=Sum("receita_bruta"))
            .order_by()
        )
        for movimento in movimentos:
            acumulados[movimento["produto_id"]][movimento["mes"] - 1] += movimento["total"] or Decimal("0")
    else:
        acumulados = {
            produto_id: defaultdict(lambda: [Decimal("0") for _ in range(12)])
            for produto_id in produto_ids
        }
        movimentos = (
            MovimentoProdutoMensal.objects.filter(ano=ano, produto_id__in=produto_ids)
            .values("produto_id", "mes", "unidade_medida_id_origem", "unidade_sigla")
            .annotate(total=Sum("quantidade"))
            .order_by()
        )
        for movimento in movimentos:
            unidade = (movimento["unidade_medida_id_origem"], movimento["unidade_sigla"])
            acumulados[movimento["produto_id"]][unidade][movimento["mes"] - 1] += (
                movimento["total"] or Decimal("0")
            )

    linhas = []
    for produto in produtos_pagina:
        linha = {
            "id_produto": produto.id_produto,
            "nome_produto": produto.nome_exibicao,
            "status": produto.status,
        }
        if metrica == "valor":
            valores = acumulados[produto.id_produto]
            linha["valores"] = [_decimal_texto(valor) for valor in valores]
            linha["total"] = _decimal_texto(sum(valores, Decimal("0")))
        else:
            linha["unidades"] = [
                {
                    "id_unidade": unidade[0],
                    "sigla": unidade[1],
                    "valores": [_decimal_texto(valor) for valor in valores],
                    "total": _decimal_texto(sum(valores, Decimal("0"))),
                }
                for unidade, valores in sorted(
                    acumulados[produto.id_produto].items(), key=lambda item: (item[0][1], item[0][0])
                )
            ]
        linhas.append(linha)

    estados = list(StatusMovimentoProdutoMensal.objects.filter(ano=ano).order_by("mes"))
    periodos_desatualizados = [
        {"mes": item.mes, "status": item.status}
        for item in estados
        if item.status != StatusMovimentoProdutoMensal.STATUS_PRONTO
    ]
    ultimo_sucesso = max(
        (item.ultimo_sucesso_em for item in estados if item.ultimo_sucesso_em),
        default=None,
    )

    contexto_mes_aberto = contexto_mes_aberto_vendas(ano)
    return {
        "ano_consultado": ano,
        "metrica": metrica,
        "familia": {
            "id_conta": raiz.id_conta,
            "codigo_hierarquico": raiz.codigo_hierarquico,
            "nome_conta": raiz.nome_conta,
        },
        "categoria": {
            "id_conta": categoria.id_conta,
            "codigo_hierarquico": categoria.codigo_hierarquico,
            "nome_conta": categoria.nome_conta,
        },
        "meses": _MESES_LABELS,
        **contexto_mes_aberto,
        "linhas": linhas,
        "paginacao": {
            "pagina": pagina_obj.number,
            "por_pagina": por_pagina,
            "total_produtos": paginador.count,
            "total_paginas": paginador.num_pages,
        },
        "inativos_ocultos": inativos_ocultos,
        "desatualizado": bool(periodos_desatualizados),
        "periodos_desatualizados": periodos_desatualizados,
        "atualizado_em": ultimo_sucesso.isoformat() if ultimo_sucesso else None,
    }


def status_agregados_compras() -> dict:
    anos = list(
        MovimentoCompraProdutoMensal.objects.values_list("ano", flat=True)
        .distinct()
        .order_by("-ano")
    )
    estados = list(
        StatusMovimentoCompraProdutoMensal.objects.order_by("-ano", "mes").values(
            "ano", "mes", "status", "ultimo_sucesso_em", "atualizado_em"
        )
    )
    for item in estados:
        item["ultimo_sucesso_em"] = (
            item["ultimo_sucesso_em"].isoformat() if item["ultimo_sucesso_em"] else None
        )
        item["atualizado_em"] = item["atualizado_em"].isoformat()
    return {"anos_disponiveis": anos, "periodos": estados}


def reconstruir_movimento_compra_produto_mensal(ano: int, mes: int) -> int:
    """Reconstrói um mês de compras sem descartar o snapshot válido em caso de falha."""
    if mes < 1 or mes > 12:
        raise ValueError("Mes invalido.")
    inicio_periodo = date(ano, mes, 1)
    fim_periodo = date(ano + 1, 1, 1) if mes == 12 else date(ano, mes + 1, 1)

    status_obj, _ = StatusMovimentoCompraProdutoMensal.objects.update_or_create(
        ano=ano,
        mes=mes,
        defaults={"status": StatusMovimentoCompraProdutoMensal.STATUS_PROCESSANDO, "erro": ""},
    )

    try:
        linhas = list(
            ItemCompra.objects.filter(
                compra__data_emissao__gte=inicio_periodo,
                compra__data_emissao__lt=fim_periodo,
                quantidade__gte=0,
                valor_custo__gte=0,
                valor_total_item__gte=0,
            )
            .exclude(compra__nfe_status__iexact=_STATUS_CANCELADA_COMPRA)
            .values(
                "produto_id",
                "compra__fornecedor_id",
                "unidade_medida_id",
                "unidade_medida__sigla",
            )
            .annotate(
                valor_total=Sum("valor_total_item"),
                quantidade_total=Sum("quantidade"),
            )
            .order_by()
        )

        novos = [
            MovimentoCompraProdutoMensal(
                ano=ano,
                mes=mes,
                produto_id=linha["produto_id"],
                fornecedor_id=linha["compra__fornecedor_id"],
                unidade_medida_id_origem=(
                    linha["unidade_medida_id"] or MovimentoCompraProdutoMensal.SEM_UNIDADE_ID
                ),
                unidade_sigla=(
                    linha["unidade_medida__sigla"] or MovimentoCompraProdutoMensal.SEM_UNIDADE_SIGLA
                ),
                valor_comprado=linha["valor_total"] or Decimal("0"),
                quantidade=linha["quantidade_total"] or Decimal("0"),
            )
            for linha in linhas
        ]

        with transaction.atomic():
            MovimentoCompraProdutoMensal.objects.filter(ano=ano, mes=mes).delete()
            MovimentoCompraProdutoMensal.objects.bulk_create(novos, batch_size=2000)
            status_obj.status = StatusMovimentoCompraProdutoMensal.STATUS_PRONTO
            status_obj.erro = ""
            status_obj.ultimo_sucesso_em = timezone.now()
            status_obj.save(update_fields=["status", "erro", "ultimo_sucesso_em", "atualizado_em"])
        return len(novos)
    except Exception as exc:
        StatusMovimentoCompraProdutoMensal.objects.filter(pk=status_obj.pk).update(
            status=StatusMovimentoCompraProdutoMensal.STATUS_FALHA,
            erro=str(exc)[:4000],
            atualizado_em=timezone.now(),
        )
        logger.exception("Falha ao reconstruir movimento mensal de compras para %s/%02d", ano, mes)
        raise


def reconstruir_movimentos_compra_produto_mensal(
    ano: int | None = None,
    mes: int | None = None,
) -> dict:
    if mes is not None and ano is None:
        raise ValueError("Informe o ano ao reconstruir um mes especifico.")
    if mes is not None and (mes < 1 or mes > 12):
        raise ValueError("Mes invalido.")

    compras = Compra.objects.all()
    movimentos = MovimentoCompraProdutoMensal.objects.all()
    estados = StatusMovimentoCompraProdutoMensal.objects.all()
    if ano is not None:
        compras = compras.filter(data_emissao__year=ano)
        movimentos = movimentos.filter(ano=ano)
        estados = estados.filter(ano=ano)
    if mes is not None:
        compras = compras.filter(data_emissao__month=mes)
        movimentos = movimentos.filter(mes=mes)
        estados = estados.filter(mes=mes)

    periodos = {(data.year, data.month) for data in compras.dates("data_emissao", "month")}
    periodos.update(movimentos.values_list("ano", "mes").distinct())
    periodos.update(estados.values_list("ano", "mes").distinct())

    total_linhas = 0
    for ano_periodo, mes_periodo in sorted(periodos):
        total_linhas += reconstruir_movimento_compra_produto_mensal(ano_periodo, mes_periodo)
    return {"periodos_processados": len(periodos), "linhas_geradas": total_linhas}


def _fornecedor_contexto(fornecedor_id: int | None) -> Fornecedor | None:
    if fornecedor_id is None:
        return None
    fornecedor = Fornecedor.objects.filter(id_fornecedor=fornecedor_id).first()
    if fornecedor is None:
        raise Fornecedor.DoesNotExist
    return fornecedor


def _dados_status_compras(ano: int) -> tuple[list[dict], str | None]:
    estados = list(StatusMovimentoCompraProdutoMensal.objects.filter(ano=ano).order_by("mes"))
    periodos_desatualizados = [
        {"mes": item.mes, "status": item.status}
        for item in estados
        if item.status != StatusMovimentoCompraProdutoMensal.STATUS_PRONTO
    ]
    ultimo_sucesso = max(
        (item.ultimo_sucesso_em for item in estados if item.ultimo_sucesso_em),
        default=None,
    )
    return periodos_desatualizados, ultimo_sucesso.isoformat() if ultimo_sucesso else None


def _serializar_fornecedor(fornecedor: Fornecedor | None) -> dict | None:
    if fornecedor is None:
        return None
    nome = str(fornecedor.nome_gerencial or "").strip() or fornecedor.nome_fornecedor
    return {"id_fornecedor": fornecedor.id_fornecedor, "nome_fornecedor": nome}


def montar_analise_compras_categorias(
    *,
    ano: int,
    raiz_id: int,
    metrica: str,
    fornecedor_id: int | None = None,
) -> dict:
    if metrica not in {"valor", "quantidade"}:
        raise ValueError("Metrica invalida. Use 'valor' ou 'quantidade'.")

    raiz = PlanoConta.objects.filter(id_conta=raiz_id, conta_pai__isnull=True).first()
    if raiz is None:
        raise PlanoConta.DoesNotExist
    fornecedor = _fornecedor_contexto(fornecedor_id)
    if not MovimentoCompraProdutoMensal.objects.filter(ano=ano).exists():
        raise MovimentoCompraProdutoMensal.DoesNotExist

    nodes = list(
        PlanoConta.objects.filter(codigo_ordenacao__startswith=raiz.codigo_ordenacao)
        .order_by("codigo_ordenacao")
        .values("id_conta", "codigo_hierarquico", "nome_conta", "conta_pai_id")
    )
    node_ids = {node["id_conta"] for node in nodes}
    pais_com_filhas = {node["conta_pai_id"] for node in nodes if node["conta_pai_id"] in node_ids}
    folhas = node_ids - pais_com_filhas

    conflitos = list(
        Produto.objects.filter(categorias__id_conta__in=folhas)
        .values("id_produto", "produto")
        .annotate(qtd_categorias_familia=Count("categorias", distinct=True))
        .filter(qtd_categorias_familia__gt=1)
        .order_by("id_produto")
    )
    if conflitos:
        raise CategoriasAmbiguasError(conflitos)

    movimentos = MovimentoCompraProdutoMensal.objects.filter(
        ano=ano,
        produto__categorias__id_conta__in=folhas,
    )
    if fornecedor_id is not None:
        movimentos = movimentos.filter(fornecedor_id=fornecedor_id)

    if metrica == "valor":
        acumulados = {node_id: [Decimal("0") for _ in range(12)] for node_id in node_ids}
        agregados = (
            movimentos.values("produto__categorias__id_conta", "mes")
            .annotate(total=Sum("valor_comprado"))
            .order_by()
        )
        for row in agregados:
            acumulados[row["produto__categorias__id_conta"]][row["mes"] - 1] += (
                row["total"] or Decimal("0")
            )
    else:
        acumulados = {
            node_id: defaultdict(lambda: [Decimal("0") for _ in range(12)])
            for node_id in node_ids
        }
        agregados = (
            movimentos.values(
                "produto__categorias__id_conta",
                "mes",
                "unidade_medida_id_origem",
                "unidade_sigla",
            )
            .annotate(total=Sum("quantidade"))
            .order_by()
        )
        for row in agregados:
            unidade = (row["unidade_medida_id_origem"], row["unidade_sigla"])
            acumulados[row["produto__categorias__id_conta"]][unidade][row["mes"] - 1] += (
                row["total"] or Decimal("0")
            )

    for node in reversed(nodes):
        pai_id = node["conta_pai_id"]
        if pai_id not in node_ids:
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
            "id_conta": node["id_conta"],
            "codigo_hierarquico": node["codigo_hierarquico"],
            "nome_conta": node["nome_conta"],
            "conta_pai_id": node["conta_pai_id"] if node["conta_pai_id"] in node_ids else None,
            "nivel": len([p for p in node["codigo_hierarquico"].split(".") if p]) - nivel_raiz,
            "tem_filhos": node["id_conta"] in pais_com_filhas,
        }
        if metrica == "valor":
            valores = acumulados[node["id_conta"]]
            linha["valores"] = [_decimal_texto(valor) for valor in valores]
            linha["total"] = _decimal_texto(sum(valores, Decimal("0")))
        else:
            linha["unidades"] = [
                {
                    "id_unidade": unidade[0],
                    "sigla": unidade[1],
                    "valores": [_decimal_texto(valor) for valor in valores],
                    "total": _decimal_texto(sum(valores, Decimal("0"))),
                }
                for unidade, valores in sorted(
                    acumulados[node["id_conta"]].items(), key=lambda item: (item[0][1], item[0][0])
                )
            ]
        linhas.append(linha)

    periodos_desatualizados, atualizado_em = _dados_status_compras(ano)
    contexto_mes_aberto = contexto_mes_aberto_compras(ano)
    return {
        "ano_consultado": ano,
        "metrica": metrica,
        "familia": {
            "id_conta": raiz.id_conta,
            "codigo_hierarquico": raiz.codigo_hierarquico,
            "nome_conta": raiz.nome_conta,
        },
        "fornecedor": _serializar_fornecedor(fornecedor),
        "meses": _MESES_LABELS,
        **contexto_mes_aberto,
        "linhas": linhas,
        "desatualizado": bool(periodos_desatualizados),
        "periodos_desatualizados": periodos_desatualizados,
        "atualizado_em": atualizado_em,
    }


def montar_analise_compras_produtos(
    *,
    ano: int,
    raiz_id: int,
    categoria_id: int,
    metrica: str,
    fornecedor_id: int | None = None,
    incluir_inativos: bool = False,
    search: str = "",
    pagina: int = 1,
    por_pagina: int = 100,
) -> dict:
    if metrica not in {"valor", "quantidade", "custo_medio"}:
        raise ValueError("Metrica invalida. Use 'valor', 'quantidade' ou 'custo_medio'.")
    if pagina < 1:
        raise ValueError("O parametro 'page' deve ser maior ou igual a 1.")

    raiz = PlanoConta.objects.filter(id_conta=raiz_id, conta_pai__isnull=True).first()
    if raiz is None:
        raise PlanoConta.DoesNotExist
    categoria = PlanoConta.objects.filter(id_conta=categoria_id).first()
    if categoria is None:
        raise PlanoConta.DoesNotExist
    if not str(categoria.codigo_ordenacao).startswith(str(raiz.codigo_ordenacao)):
        raise ValueError("A categoria selecionada nao pertence a familia informada.")
    fornecedor = _fornecedor_contexto(fornecedor_id)
    if not MovimentoCompraProdutoMensal.objects.filter(ano=ano).exists():
        raise MovimentoCompraProdutoMensal.DoesNotExist

    categorias_subarvore = PlanoConta.objects.filter(
        codigo_ordenacao__startswith=categoria.codigo_ordenacao,
    )
    folhas = categorias_subarvore.exclude(
        Exists(PlanoConta.objects.filter(conta_pai_id=OuterRef("pk")))
    ).values_list("id_conta", flat=True)
    vinculo_folha = Produto.categorias.through.objects.filter(
        produto_id=OuterRef("pk"),
        planoconta_id__in=folhas,
    )

    movimento_anual = MovimentoCompraProdutoMensal.objects.filter(
        ano=ano,
        produto_id=OuterRef("pk"),
    )
    if fornecedor_id is not None:
        movimento_anual = movimento_anual.filter(fornecedor_id=fornecedor_id)
    valor_anual = (
        movimento_anual.values("produto_id")
        .annotate(total=Sum("valor_comprado"))
        .values("total")[:1]
    )
    campo_decimal = DecimalField(max_digits=24, decimal_places=6)
    nome_exibicao = Coalesce(
        NullIf(Trim("nome_gerencial"), Value("")),
        F("produto"),
        output_field=CharField(),
    )
    produtos_base = Produto.objects.annotate(
        pertence_subarvore=Exists(vinculo_folha),
        valor_anual=Coalesce(
            Subquery(valor_anual, output_field=campo_decimal),
            Value(Decimal("0"), output_field=campo_decimal),
        ),
        nome_exibicao=nome_exibicao,
        id_produto_texto=Cast("id_produto", output_field=CharField()),
    ).filter(pertence_subarvore=True)

    termo = str(search or "").strip()
    if termo:
        produtos_base = produtos_base.filter(
            Q(id_produto_texto__icontains=termo)
            | Q(nome_gerencial__icontains=termo)
            | Q(produto__icontains=termo)
        )
    inativos_ocultos = produtos_base.filter(status__iexact="INATIVO").count()
    status_permitidos = Q(status__iexact="ATIVO")
    if incluir_inativos:
        status_permitidos |= Q(status__iexact="INATIVO")

    produtos_ordenados = produtos_base.filter(status_permitidos).order_by(
        "-valor_anual", "nome_exibicao", "id_produto"
    )
    paginador = Paginator(produtos_ordenados, por_pagina)
    pagina_obj = paginador.get_page(pagina)
    produtos_pagina = list(pagina_obj.object_list)
    produto_ids = [produto.id_produto for produto in produtos_pagina]

    movimentos = MovimentoCompraProdutoMensal.objects.filter(
        ano=ano,
        produto_id__in=produto_ids,
    )
    if fornecedor_id is not None:
        movimentos = movimentos.filter(fornecedor_id=fornecedor_id)

    if metrica == "valor":
        acumulados = {produto_id: [Decimal("0") for _ in range(12)] for produto_id in produto_ids}
        agregados = (
            movimentos.values("produto_id", "mes")
            .annotate(total=Sum("valor_comprado"))
            .order_by()
        )
        for row in agregados:
            acumulados[row["produto_id"]][row["mes"] - 1] += row["total"] or Decimal("0")
    elif metrica == "quantidade":
        acumulados = {
            produto_id: defaultdict(lambda: [Decimal("0") for _ in range(12)])
            for produto_id in produto_ids
        }
        agregados = (
            movimentos.values("produto_id", "mes", "unidade_medida_id_origem", "unidade_sigla")
            .annotate(total=Sum("quantidade"))
            .order_by()
        )
        for row in agregados:
            unidade = (row["unidade_medida_id_origem"], row["unidade_sigla"])
            acumulados[row["produto_id"]][unidade][row["mes"] - 1] += row["total"] or Decimal("0")
    else:
        acumulados = {
            produto_id: defaultdict(
                lambda: {
                    "valor": [Decimal("0") for _ in range(12)],
                    "quantidade": [Decimal("0") for _ in range(12)],
                }
            )
            for produto_id in produto_ids
        }
        agregados = (
            movimentos.values("produto_id", "mes", "unidade_medida_id_origem", "unidade_sigla")
            .annotate(valor=Sum("valor_comprado"), quantidade=Sum("quantidade"))
            .order_by()
        )
        for row in agregados:
            unidade = (row["unidade_medida_id_origem"], row["unidade_sigla"])
            acumulados[row["produto_id"]][unidade]["valor"][row["mes"] - 1] += (
                row["valor"] or Decimal("0")
            )
            acumulados[row["produto_id"]][unidade]["quantidade"][row["mes"] - 1] += (
                row["quantidade"] or Decimal("0")
            )

    linhas = []
    for produto in produtos_pagina:
        linha = {
            "id_produto": produto.id_produto,
            "nome_produto": produto.nome_exibicao,
            "status": produto.status,
        }
        if metrica == "valor":
            valores = acumulados[produto.id_produto]
            linha["valores"] = [_decimal_texto(valor) for valor in valores]
            linha["total"] = _decimal_texto(sum(valores, Decimal("0")))
        elif metrica == "quantidade":
            linha["unidades"] = [
                {
                    "id_unidade": unidade[0],
                    "sigla": unidade[1],
                    "valores": [_decimal_texto(valor) for valor in valores],
                    "total": _decimal_texto(sum(valores, Decimal("0"))),
                }
                for unidade, valores in sorted(
                    acumulados[produto.id_produto].items(), key=lambda item: (item[0][1], item[0][0])
                )
            ]
        else:
            unidades = []
            for unidade, totais in sorted(
                acumulados[produto.id_produto].items(), key=lambda item: (item[0][1], item[0][0])
            ):
                valores = [
                    valor / quantidade if quantidade else Decimal("0")
                    for valor, quantidade in zip(totais["valor"], totais["quantidade"])
                ]
                valor_anual_unidade = sum(totais["valor"], Decimal("0"))
                quantidade_anual = sum(totais["quantidade"], Decimal("0"))
                unidades.append(
                    {
                        "id_unidade": unidade[0],
                        "sigla": unidade[1],
                        "valores": [_decimal_texto(valor) for valor in valores],
                        "total": _decimal_texto(
                            valor_anual_unidade / quantidade_anual if quantidade_anual else Decimal("0")
                        ),
                    }
                )
            linha["unidades"] = unidades
        linhas.append(linha)

    periodos_desatualizados, atualizado_em = _dados_status_compras(ano)
    contexto_mes_aberto = contexto_mes_aberto_compras(ano)
    return {
        "ano_consultado": ano,
        "metrica": metrica,
        "familia": {
            "id_conta": raiz.id_conta,
            "codigo_hierarquico": raiz.codigo_hierarquico,
            "nome_conta": raiz.nome_conta,
        },
        "categoria": {
            "id_conta": categoria.id_conta,
            "codigo_hierarquico": categoria.codigo_hierarquico,
            "nome_conta": categoria.nome_conta,
        },
        "fornecedor": _serializar_fornecedor(fornecedor),
        "meses": _MESES_LABELS,
        **contexto_mes_aberto,
        "linhas": linhas,
        "paginacao": {
            "pagina": pagina_obj.number,
            "por_pagina": por_pagina,
            "total_produtos": paginador.count,
            "total_paginas": paginador.num_pages,
        },
        "inativos_ocultos": inativos_ocultos,
        "desatualizado": bool(periodos_desatualizados),
        "periodos_desatualizados": periodos_desatualizados,
        "atualizado_em": atualizado_em,
    }


def _periodos_calendario_dashboard(ano: int, granularidade: str) -> list[dict]:
    """Gera meses ou semanas (domingo-sábado) limitados ao ano calendário."""
    inicio_ano = date(ano, 1, 1)
    fim_ano = date(ano, 12, 31)
    periodos = []

    if granularidade == "mensal":
        for mes in range(1, 13):
            periodos.append({
                "inicio": date(ano, mes, 1),
                "fim": date(ano, mes, calendar.monthrange(ano, mes)[1]),
                "label": _MESES_LABELS[mes - 1],
            })
        return periodos

    cursor = inicio_ano
    indice = 1
    while cursor <= fim_ano:
        # Python: segunda=0 ... sábado=5; o primeiro período é cortado em 01/Jan.
        dias_ate_sabado = (5 - cursor.weekday()) % 7
        fim = min(cursor + timedelta(days=dias_ate_sabado), fim_ano)
        periodos.append({"inicio": cursor, "fim": fim, "label": f"S{indice:02d}"})
        cursor = fim + timedelta(days=1)
        indice += 1
    return periodos


def _resumo_diario_dashboard(qs, ano_atual: int, ano_anterior: int) -> dict[date, dict]:
    """Reduz os documentos de dois anos a, no máximo, uma linha por dia."""
    rows = (
        qs.filter(
            data_venda__gte=date(ano_anterior, 1, 1),
            data_venda__lte=date(ano_atual, 12, 31),
        )
        .values("data_venda")
        .annotate(
            receita=Sum("valor_total_documento"),
            volume=Count("id_venda"),
            faturamento_manha=Sum(
                "valor_total_documento",
                filter=Q(hora_venda__isnull=False, hora_venda__lt=time(13, 0)),
            ),
            faturamento_tarde=Sum(
                "valor_total_documento",
                filter=Q(hora_venda__gte=time(13, 0)),
            ),
            faturamento_sem_horario=Sum(
                "valor_total_documento",
                filter=Q(hora_venda__isnull=True),
            ),
            volume_sem_horario=Count("id_venda", filter=Q(hora_venda__isnull=True)),
        )
        .order_by("data_venda")
    )
    return {row["data_venda"]: row for row in rows}


def _somar_periodo_dashboard(diarios: dict[date, dict], inicio: date, fim: date) -> dict:
    total = {
        "receita": Decimal("0"),
        "volume": 0,
        "faturamento_manha": Decimal("0"),
        "faturamento_tarde": Decimal("0"),
        "faturamento_sem_horario": Decimal("0"),
        "volume_sem_horario": 0,
    }
    cursor = inicio
    while cursor <= fim:
        row = diarios.get(cursor)
        if row:
            total["receita"] += row["receita"] or Decimal("0")
            total["volume"] += row["volume"] or 0
            total["faturamento_manha"] += row["faturamento_manha"] or Decimal("0")
            total["faturamento_tarde"] += row["faturamento_tarde"] or Decimal("0")
            total["faturamento_sem_horario"] += row["faturamento_sem_horario"] or Decimal("0")
            total["volume_sem_horario"] += row["volume_sem_horario"] or 0
        cursor += timedelta(days=1)
    return total


def _montar_serie_dashboard(
    diarios: dict[date, dict],
    ano_atual: int,
    ultima_data: date,
    granularidade: str,
) -> list[dict]:
    periodos_atuais = [
        periodo
        for periodo in _periodos_calendario_dashboard(ano_atual, granularidade)
        if periodo["inicio"] <= ultima_data
    ]
    periodos_anteriores = _periodos_calendario_dashboard(ano_atual - 1, granularidade)
    serie = []

    for indice, periodo in enumerate(periodos_atuais):
        fim_consulta = min(periodo["fim"], ultima_data)
        parcial = fim_consulta < periodo["fim"]
        atual = _somar_periodo_dashboard(diarios, periodo["inicio"], fim_consulta)

        anterior_periodo = periodos_anteriores[indice]
        if parcial:
            dias_decorridos = (fim_consulta - periodo["inicio"]).days
            fim_anterior = min(
                anterior_periodo["inicio"] + timedelta(days=dias_decorridos),
                anterior_periodo["fim"],
            )
        else:
            fim_anterior = anterior_periodo["fim"]
        anterior = _somar_periodo_dashboard(diarios, anterior_periodo["inicio"], fim_anterior)

        ticket = atual["receita"] / atual["volume"] if atual["volume"] else None
        serie.append({
            "indice": indice + 1,
            "label": periodo["label"],
            "inicio": periodo["inicio"].isoformat(),
            "fim": periodo["fim"].isoformat(),
            "data_corte": fim_consulta.isoformat(),
            "parcial": parcial,
            "receita_atual": _decimal_texto(atual["receita"]),
            "receita_anterior_equivalente": _decimal_texto(anterior["receita"]),
            "volume_atual": atual["volume"],
            "ticket_medio_atual": _decimal_texto(ticket) if ticket is not None else None,
            "faturamento_manha": _decimal_texto(atual["faturamento_manha"]),
            "faturamento_tarde": _decimal_texto(atual["faturamento_tarde"]),
        })
    return serie


def _media_periodos_fechados(serie: list[dict], campo: str) -> Decimal:
    fechados = [item for item in serie if not item["parcial"]]
    if not fechados:
        return Decimal("0")
    return sum((Decimal(item[campo]) for item in fechados), Decimal("0")) / len(fechados)


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

    # ── Séries mensal/semanal e turnos ─────────────────────────────────────
    diarios = _resumo_diario_dashboard(qs, ano_atual, ano_anterior)
    serie_mensal = _montar_serie_dashboard(diarios, ano_atual, ultima_data, "mensal")
    serie_semanal = _montar_serie_dashboard(diarios, ano_atual, ultima_data, "semanal")
    dados_periodicos = {"mensal": serie_mensal, "semanal": serie_semanal}

    media_mensal_atual = _media_periodos_fechados(serie_mensal, "receita_atual")
    media_mensal_anterior = _media_periodos_fechados(
        serie_mensal, "receita_anterior_equivalente"
    )
    media_semanal_atual = _media_periodos_fechados(serie_semanal, "receita_atual")
    media_semanal_anterior = _media_periodos_fechados(
        serie_semanal, "receita_anterior_equivalente"
    )
    sem_horario = _somar_periodo_dashboard(
        diarios, date(ano_atual, 1, 1), ultima_data
    )

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
            "faturamento_semanal_medio_atual": media_semanal_atual,
            "faturamento_semanal_medio_anterior_equivalente": media_semanal_anterior,
            "faturamento_mensal_medio_atual": media_mensal_atual,
            "faturamento_mensal_medio_anterior_equivalente": media_mensal_anterior,
            "dados_periodicos_grafico": dados_periodicos,
            "volume_sem_horario_atual": sem_horario["volume_sem_horario"],
            "faturamento_sem_horario_atual": sem_horario["faturamento_sem_horario"],
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
