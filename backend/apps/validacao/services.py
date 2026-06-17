from __future__ import annotations

import logging
from typing import Any
from datetime import date

from django.db import transaction

from apps.cadastros.models import (
    Cliente,
    CodSis,
    Fornecedor,
    GrupoCliente,
    PlanoConta,
    Produto,
    TipoVenda,
    UnidadeMedida,
)
from apps.integracao.hash_engine import (
    gerar_hash_cliente,
    gerar_hash_fornecedor,
    gerar_hash_produto,
    normalizar_texto_tolerante,
    textos_semelhantes,
    valores_equivalentes_com_tolerancia,
)
from apps.integracao.models import StgClientesNovos, StgFornecedoresNovos, StgProdutosNovos

logger = logging.getLogger(__name__)

LIMIAR_SEMELHANCA_TEXTO = 0.45


def _contains_search(haystacks: list[Any], search: str) -> bool:
    termo = str(search or "").strip().lower()
    if not termo:
        return True
    return any(termo in str(valor or "").lower() for valor in haystacks)


def _produto_equivalente(item_stg: StgProdutosNovos, item_sot: Produto | None) -> bool:
    if item_sot is None:
        return False

    return (
        str(item_stg.id_produto) == str(item_sot.id_produto)
        and str(item_stg.gtin or "").strip().upper() == str(item_sot.gtin or "").strip().upper()
        and str(item_stg.barras or "").strip().upper() == str(item_sot.barras or "").strip().upper()
        and textos_semelhantes(
            item_stg.nome,
            item_sot.produto,
            limiar=LIMIAR_SEMELHANCA_TEXTO,
            ordenar_tokens=True,
        )
        and valores_equivalentes_com_tolerancia(item_stg.custo, item_sot.custo)
        and valores_equivalentes_com_tolerancia(item_stg.valor_venda, item_sot.venda)
        and normalizar_texto_tolerante(item_stg.status) == normalizar_texto_tolerante(item_sot.status)
    )


def _cliente_equivalente(item_stg: StgClientesNovos, item_sot: Cliente | None) -> bool:
    if item_sot is None:
        return False

    return (
        str(item_stg.id_cliente) == str(item_sot.id_cliente)
        and textos_semelhantes(item_stg.cliente, item_sot.nome_cliente, limiar=LIMIAR_SEMELHANCA_TEXTO)
        and textos_semelhantes(item_stg.raz_social, item_sot.raz_social, limiar=LIMIAR_SEMELHANCA_TEXTO)
    )


def _fornecedor_equivalente(item_stg: StgFornecedoresNovos, item_sot: Fornecedor | None) -> bool:
    if item_sot is None:
        return False

    return (
        str(item_stg.id_fornecedor) == str(item_sot.id_fornecedor)
        and textos_semelhantes(item_stg.fantasia, item_sot.nome_fornecedor, limiar=LIMIAR_SEMELHANCA_TEXTO)
        and textos_semelhantes(item_stg.raz_social, item_sot.raz_social, limiar=LIMIAR_SEMELHANCA_TEXTO)
    )


def listar_produtos_pendentes(search: str = "") -> list[dict[str, Any]]:
    try:
        pendentes = list(StgProdutosNovos.objects.all().order_by("id_produto"))

        produto_ids = [item.id_produto for item in pendentes]
        produtos_sot = {
            item.id_produto: item
            for item in Produto.objects.select_related("id_und_medida")
            .prefetch_related("categorias")
            .filter(id_produto__in=produto_ids)
        }

        unidade_cache: dict[str, int | None] = {}

        def resolve_unidade_sugerida(sigla_raw: str) -> int | None:
            sigla = str(sigla_raw or "").strip().upper()
            if not sigla:
                return None
            if sigla in unidade_cache:
                return unidade_cache[sigla]

            unidade, _ = UnidadeMedida.objects.get_or_create(
                sigla=sigla,
                defaults={"descricao": sigla},
            )
            unidade_cache[sigla] = unidade.id_und_medida
            return unidade.id_und_medida

        resultado: list[dict[str, Any]] = []
        for item in pendentes:
            produto_sot = produtos_sot.get(item.id_produto)
            if _produto_equivalente(item, produto_sot):
                continue

            tipo_pendencia = "ATUALIZACAO" if produto_sot is not None else "NOVO"
            dados_sot: dict[str, Any] | None = None

            if produto_sot is not None:
                dados_sot = {
                    "nome": produto_sot.produto,
                    "nome_gerencial": produto_sot.nome_gerencial,
                    "gtin": produto_sot.gtin,
                    "barras": produto_sot.barras,
                    "ncm": produto_sot.ncm,
                    "custo": produto_sot.custo,
                    "valor_venda": produto_sot.venda,
                    "status": produto_sot.status,
                    "markup": produto_sot.markup,
                    "markup_inv": produto_sot.markup_inv,
                    "perda": produto_sot.perda,
                    "fisico": produto_sot.fisico,
                    "aliqefc": produto_sot.aliqefc,
                    "cod_g3n": produto_sot.cod_g3n,
                    "cod_rel": produto_sot.cod_rel,
                    "usuario": produto_sot.usuario,
                    "codigo": "",
                    "id_und_medida": produto_sot.id_und_medida_id,
                    "categorias_ids": list(produto_sot.categorias.values_list("id_conta", flat=True)),
                }

            resultado.append(
                {
                    "id_produto": item.id_produto,
                    "nome": item.nome,
                    "nome_gerencial": (produto_sot.nome_gerencial if produto_sot and produto_sot.nome_gerencial else item.nome),
                    "gtin": item.gtin,
                    "barras": item.barras,
                    "ncm": item.ncm,
                    "unidade_comercial": item.unidade_comecial,
                    "custo": item.custo,
                    "valor_venda": item.valor_venda,
                    "dt_ultimo_movimento": item.dt_ultimo_movimento,
                    "status": item.status,
                    "unidade_sugerida_id": resolve_unidade_sugerida(item.unidade_comecial),
                    "tipo_pendencia": tipo_pendencia,
                    "dados_sot": dados_sot,
                }
            )

        if not search:
            return resultado

        return [
            item
            for item in resultado
            if _contains_search(
                [item.get("id_produto"), item.get("nome"), item.get("nome_gerencial"), item.get("ncm")],
                search,
            )
        ]
    except Exception:
        logger.exception("Falha ao listar produtos pendentes da staging.")
        raise


def aprovar_produto_novo(dados_validados: dict[str, Any]) -> None:
    try:
        with transaction.atomic():
            nome_original = str(
                dados_validados.get("nome_original")
                or dados_validados.get("nome")
                or ""
            ).strip()
            if not nome_original:
                raise ValueError("nome_original do produto e obrigatorio para aprovacao.")

            nome_gerencial = str(dados_validados.get("nome_gerencial") or "").strip() or nome_original

            unidade, _ = UnidadeMedida.objects.get_or_create(
                id_und_medida=dados_validados["id_und_medida"],
                defaults={
                    "sigla": f"UND{dados_validados['id_und_medida']}",
                    "descricao": "Unidade cadastrada automaticamente",
                },
            )

            categoria_ids = set(dados_validados.get("categorias_ids", []))
            categorias = []
            for categoria_id in sorted(categoria_ids):
                categoria, _ = PlanoConta.objects.get_or_create(
                    id_conta=categoria_id,
                    defaults={
                        "codigo_hierarquico": str(categoria_id),
                        "nome_conta": f"Categoria {categoria_id}",
                    },
                )
                categorias.append(categoria)

            produto, _ = Produto.objects.update_or_create(
                id_produto=dados_validados["id_produto"],
                defaults={
                    "gtin": dados_validados.get("gtin", ""),
                    "barras": dados_validados.get("barras", ""),
                    "ncm": dados_validados.get("ncm", ""),
                    "produto": nome_original,
                    "nome_gerencial": nome_gerencial,
                    "id_und_medida": unidade,
                    "custo": dados_validados["custo"],
                    "venda": dados_validados["valor_venda"],
                    "status": dados_validados["status"],
                    "markup": dados_validados.get("markup", 0),
                    "markup_inv": dados_validados.get("markup_inv", 0),
                    "perda": dados_validados.get("perda", 0),
                    "ult_mov": dados_validados.get("ult_mov"),
                    "fisico": dados_validados.get("fisico", 0),
                    "aliqefc": dados_validados.get("aliqefc", ""),
                    "cod_g3n": dados_validados.get("cod_g3n", 0),
                    "cod_rel": dados_validados.get("cod_rel", 0),
                    "usuario": dados_validados.get("usuario", ""),
                    "hash_md5": gerar_hash_produto(
                        id_produto=dados_validados["id_produto"],
                        gtin=dados_validados.get("gtin", ""),
                        barras=dados_validados.get("barras", ""),
                        nome=nome_original,
                        custo=dados_validados["custo"],
                        venda=dados_validados["valor_venda"],
                        status=dados_validados.get("status", ""),
                    ),
                },
            )
            if categoria_ids:
                produto.categorias.set(categorias)

            StgProdutosNovos.objects.filter(
                id_produto=dados_validados["id_produto"]
            ).delete()

        logger.info(
            "Produto %s aprovado com sucesso.",
            dados_validados["id_produto"],
        )
    except Exception:
        logger.exception(
            "Falha ao aprovar produto %s.",
            dados_validados.get("id_produto"),
        )
        raise


def listar_clientes_pendentes(search: str = "") -> list[dict[str, Any]]:
    try:
        pendentes = list(StgClientesNovos.objects.all().order_by("id_cliente"))
        clientes_sot = {
            item.id_cliente: item
            for item in Cliente.objects.select_related("id_grupo", "id_tipo_venda").filter(
                id_cliente__in=[obj.id_cliente for obj in pendentes]
            )
        }

        resultado: list[dict[str, Any]] = []
        for item in pendentes:
            cliente_sot = clientes_sot.get(item.id_cliente)
            if _cliente_equivalente(item, cliente_sot):
                continue

            tipo_pendencia = "ATUALIZACAO" if cliente_sot is not None else "NOVO"
            dados_sot: dict[str, Any] | None = None
            if cliente_sot is not None:
                dados_sot = {
                    "id_cliente": cliente_sot.id_cliente,
                    "cliente": cliente_sot.nome_cliente,
                    "nome_cliente": cliente_sot.nome_cliente,
                    "nome_gerencial": cliente_sot.nome_gerencial,
                    "raz_social": cliente_sot.raz_social,
                    "prazo_cob": cliente_sot.prazo_cob,
                    "id_grupo": cliente_sot.id_grupo_id,
                    "id_tipo_venda": cliente_sot.id_tipo_venda_id,
                }

            resultado.append(
                {
                    "id_cliente": item.id_cliente,
                    "nome_cliente": item.cliente,
                    "nome_gerencial": (cliente_sot.nome_gerencial if cliente_sot and cliente_sot.nome_gerencial else item.cliente),
                    "raz_social": item.raz_social,
                    "tipo_pendencia": tipo_pendencia,
                    "dados_sot": dados_sot,
                }
            )

        if not search:
            return resultado

        return [
            item
            for item in resultado
            if _contains_search(
                [item.get("id_cliente"), item.get("nome_cliente"), item.get("nome_gerencial"), item.get("raz_social")],
                search,
            )
        ]
    except Exception:
        logger.exception("Falha ao listar clientes pendentes da staging.")
        raise


def listar_fornecedores_pendentes(search: str = "") -> list[dict[str, Any]]:
    try:
        pendentes = list(StgFornecedoresNovos.objects.all().order_by("id_fornecedor"))
        fornecedores_sot = {
            item.id_fornecedor: item
            for item in Fornecedor.objects.select_related("id_codsis").filter(
                id_fornecedor__in=[obj.id_fornecedor for obj in pendentes]
            )
        }

        resultado: list[dict[str, Any]] = []
        for item in pendentes:
            fornecedor_sot = fornecedores_sot.get(item.id_fornecedor)
            if _fornecedor_equivalente(item, fornecedor_sot):
                continue

            tipo_pendencia = "ATUALIZACAO" if fornecedor_sot is not None else "NOVO"
            dados_sot: dict[str, Any] | None = None
            if fornecedor_sot is not None:
                dados_sot = {
                    "id_fornecedor": fornecedor_sot.id_fornecedor,
                    "fantasia": fornecedor_sot.nome_fornecedor,
                    "nome_fornecedor": fornecedor_sot.nome_fornecedor,
                    "nome_gerencial": fornecedor_sot.nome_gerencial,
                    "raz_social": fornecedor_sot.raz_social,
                    "dt_cadastro": fornecedor_sot.dt_cadastro,
                    "id_codsis": fornecedor_sot.id_codsis_id,
                    "codigo": fornecedor_sot.codigo,
                    "operador": fornecedor_sot.operador,
                    "usuario": fornecedor_sot.usuario,
                }

            resultado.append(
                {
                    "id_fornecedor": item.id_fornecedor,
                    "nome_fornecedor": item.fantasia,
                    "nome_gerencial": (fornecedor_sot.nome_gerencial if fornecedor_sot and fornecedor_sot.nome_gerencial else item.fantasia),
                    "raz_social": item.raz_social,
                    "dt_cadastro": item.dt_cadastro,
                    "tipo_pendencia": tipo_pendencia,
                    "dados_sot": dados_sot,
                }
            )

        if not search:
            return resultado

        return [
            item
            for item in resultado
            if _contains_search(
                [item.get("id_fornecedor"), item.get("nome_fornecedor"), item.get("nome_gerencial"), item.get("raz_social")],
                search,
            )
        ]
    except Exception:
        logger.exception("Falha ao listar fornecedores pendentes da staging.")
        raise


def aprovar_cliente_novo(dados_validados: dict[str, Any]) -> None:
    try:
        with transaction.atomic():
            nome_original = str(
                dados_validados.get("nome_original")
                or dados_validados.get("nome_cliente")
                or ""
            ).strip()
            if not nome_original:
                raise ValueError("nome_original do cliente e obrigatorio para aprovacao.")

            nome_gerencial = str(dados_validados.get("nome_gerencial") or "").strip() or nome_original

            grupo = None
            if dados_validados.get("id_grupo") is not None:
                grupo, _ = GrupoCliente.objects.get_or_create(
                    id_grupo=dados_validados["id_grupo"],
                    defaults={"descricao": f"Grupo {dados_validados['id_grupo']}"},
                )

            tipo_venda = None
            if dados_validados.get("id_tipo_venda") is not None:
                tipo_venda, _ = TipoVenda.objects.get_or_create(
                    id_tipo_venda=dados_validados["id_tipo_venda"],
                    defaults={"descricao": f"Tipo {dados_validados['id_tipo_venda']}"},
                )

            Cliente.objects.update_or_create(
                id_cliente=dados_validados["id_cliente"],
                defaults={
                    "nome_cliente": nome_original,
                    "nome_gerencial": nome_gerencial,
                    "raz_social": dados_validados.get("raz_social", ""),
                    "prazo_cob": dados_validados.get("prazo_cob", 0),
                    "id_grupo": grupo,
                    "id_tipo_venda": tipo_venda,
                    "hash_md5": gerar_hash_cliente(
                        id_cliente=dados_validados["id_cliente"],
                        nome_cliente=nome_original,
                        raz_social=dados_validados.get("raz_social", ""),
                    ),
                },
            )

            StgClientesNovos.objects.filter(id_cliente=dados_validados["id_cliente"]).delete()

        logger.info("Cliente %s aprovado com sucesso.", dados_validados["id_cliente"])
    except Exception:
        logger.exception("Falha ao aprovar cliente %s.", dados_validados.get("id_cliente"))
        raise


def aprovar_fornecedor_novo(dados_validados: dict[str, Any]) -> None:
    try:
        with transaction.atomic():
            nome_original = str(
                dados_validados.get("nome_original")
                or dados_validados.get("nome_fornecedor")
                or ""
            ).strip()
            if not nome_original:
                raise ValueError("nome_original do fornecedor e obrigatorio para aprovacao.")

            nome_gerencial = str(dados_validados.get("nome_gerencial") or "").strip() or nome_original

            codsis = None
            if dados_validados.get("id_codsis") is not None:
                codsis, _ = CodSis.objects.get_or_create(
                    id_codsis=dados_validados["id_codsis"],
                    defaults={"nome": f"CodSis {dados_validados['id_codsis']}"},
                )

            Fornecedor.objects.update_or_create(
                id_fornecedor=dados_validados["id_fornecedor"],
                defaults={
                    "nome_fornecedor": nome_original,
                    "nome_gerencial": nome_gerencial,
                    "raz_social": dados_validados.get("raz_social", ""),
                    "dt_cadastro": dados_validados.get("dt_cadastro") or date.today(),
                    "id_codsis": codsis,
                    "codigo": dados_validados.get("codigo", ""),
                    "operador": dados_validados.get("operador", 0),
                    "usuario": dados_validados.get("usuario", ""),
                    "hash_md5": gerar_hash_fornecedor(
                        id_fornecedor=dados_validados["id_fornecedor"],
                        nome_fornecedor=nome_original,
                        raz_social=dados_validados.get("raz_social", ""),
                        #dt_cadastro=dados_validados.get("dt_cadastro") or date.today(),
                    ),
                },
            )

            StgFornecedoresNovos.objects.filter(id_fornecedor=dados_validados["id_fornecedor"]).delete()

        logger.info("Fornecedor %s aprovado com sucesso.", dados_validados["id_fornecedor"])
    except Exception:
        logger.exception("Falha ao aprovar fornecedor %s.", dados_validados.get("id_fornecedor"))
        raise
