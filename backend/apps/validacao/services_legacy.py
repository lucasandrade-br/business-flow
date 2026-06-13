from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
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
    percentual_semelhanca_textual,
    valores_equivalentes_com_tolerancia,
)
from apps.integracao.models import StgClientesNovos, StgFornecedoresNovos, StgProdutosNovos

logger = logging.getLogger(__name__)

LIMIAR_SEMELHANCA_TEXTO = 0.8


def _to_decimal_safe(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def _nova_divergencia(
    *,
    campo: str,
    label: str,
    valor_sor: Any,
    valor_sot: Any,
    gravidade: str,
    observacao: str = "",
) -> dict[str, Any]:
    return {
        "campo": campo,
        "label": label,
        "valor_sor": valor_sor,
        "valor_sot": valor_sot,
        "gravidade": gravidade,
        "observacao": observacao,
    }




def _gravidade_por_semelhanca(percentual: float) -> str:
    if percentual < 0.5:
        return "alta"
    if percentual < LIMIAR_SEMELHANCA_TEXTO:
        return "media"
    return "leve"


def _coletar_divergencias_produto(item_stg: StgProdutosNovos, item_sot: Produto | None) -> list[dict[str, Any]]:
    if item_sot is None:
        return []

    divergencias: list[dict[str, Any]] = []

    gtin_stg = str(item_stg.gtin or "").strip().upper()
    gtin_sot = str(item_sot.gtin or "").strip().upper()
    if gtin_stg != gtin_sot:
        divergencias.append(
            _nova_divergencia(
                campo="gtin",
                label="GTIN",
                valor_sor=item_stg.gtin,
                valor_sot=item_sot.gtin,
                gravidade="media",
            )
        )

    barras_stg = str(item_stg.barras or "").strip().upper()
    barras_sot = str(item_sot.barras or "").strip().upper()
    if barras_stg != barras_sot:
        divergencias.append(
            _nova_divergencia(
                campo="barras",
                label="Barras",
                valor_sor=item_stg.barras,
                valor_sot=item_sot.barras,
                gravidade="media",
            )
        )

    similaridade_nome = percentual_semelhanca_textual(item_stg.nome, item_sot.produto, ordenar_tokens=True)
    if similaridade_nome < LIMIAR_SEMELHANCA_TEXTO:
        divergencias.append(
            _nova_divergencia(
                campo="nome",
                label="Nome",
                valor_sor=item_stg.nome,
                valor_sot=item_sot.produto,
                gravidade=_gravidade_por_semelhanca(similaridade_nome),
                observacao=f"Semelhanca: {similaridade_nome * 100:.1f}%",
            )
        )

    custo_stg = _to_decimal_safe(item_stg.custo)
    custo_sot = _to_decimal_safe(item_sot.custo)
    diff_custo = abs(custo_stg - custo_sot)
    if not valores_equivalentes_com_tolerancia(custo_stg, custo_sot):
        divergencias.append(
            _nova_divergencia(
                campo="custo",
                label="Custo",
                valor_sor=str(item_stg.custo),
                valor_sot=str(item_sot.custo),
                gravidade="alta" if diff_custo >= Decimal("1") else "media",
                observacao=f"Diferenca: {diff_custo:.6f}",
            )
        )

    venda_stg = _to_decimal_safe(item_stg.valor_venda)
    venda_sot = _to_decimal_safe(item_sot.venda)
    diff_venda = abs(venda_stg - venda_sot)
    if not valores_equivalentes_com_tolerancia(venda_stg, venda_sot):
        divergencias.append(
            _nova_divergencia(
                campo="valor_venda",
                label="Venda",
                valor_sor=str(item_stg.valor_venda),
                valor_sot=str(item_sot.venda),
                gravidade="alta" if diff_venda >= Decimal("1") else "media",
                observacao=f"Diferenca: {diff_venda:.6f}",
            )
        )

    status_stg = normalizar_texto_tolerante(item_stg.status)
    status_sot = normalizar_texto_tolerante(item_sot.status)
    if status_stg != status_sot:
        divergencias.append(
            _nova_divergencia(
                campo="status",
                label="Status",
                valor_sor=item_stg.status,
                valor_sot=item_sot.status,
                gravidade="media",
            )
        )

    return divergencias


def _coletar_divergencias_cliente(item_stg: StgClientesNovos, item_sot: Cliente | None) -> list[dict[str, Any]]:
    if item_sot is None:
        return []

    divergencias: list[dict[str, Any]] = []

    similaridade_nome = percentual_semelhanca_textual(item_stg.cliente, item_sot.nome_cliente)
    if similaridade_nome < LIMIAR_SEMELHANCA_TEXTO:
        divergencias.append(
            _nova_divergencia(
                campo="nome_cliente",
                label="Nome",
                valor_sor=item_stg.cliente,
                valor_sot=item_sot.nome_cliente,
                gravidade=_gravidade_por_semelhanca(similaridade_nome),
                observacao=f"Semelhanca: {similaridade_nome * 100:.1f}%",
            )
        )

    similaridade_razao = percentual_semelhanca_textual(item_stg.raz_social, item_sot.raz_social)
    if similaridade_razao < LIMIAR_SEMELHANCA_TEXTO:
        divergencias.append(
            _nova_divergencia(
                campo="raz_social",
                label="Razao Social",
                valor_sor=item_stg.raz_social,
                valor_sot=item_sot.raz_social,
                gravidade=_gravidade_por_semelhanca(similaridade_razao),
                observacao=f"Semelhanca: {similaridade_razao * 100:.1f}%",
            )
        )

    return divergencias


def _coletar_divergencias_fornecedor(item_stg: StgFornecedoresNovos, item_sot: Fornecedor | None) -> list[dict[str, Any]]:
    if item_sot is None:
        return []

    divergencias: list[dict[str, Any]] = []

    similaridade_nome = percentual_semelhanca_textual(item_stg.fantasia, item_sot.nome_fornecedor)
    if similaridade_nome < LIMIAR_SEMELHANCA_TEXTO:
        divergencias.append(
            _nova_divergencia(
                campo="nome_fornecedor",
                label="Nome",
                valor_sor=item_stg.fantasia,
                valor_sot=item_sot.nome_fornecedor,
                gravidade=_gravidade_por_semelhanca(similaridade_nome),
                observacao=f"Semelhanca: {similaridade_nome * 100:.1f}%",
            )
        )

    similaridade_razao = percentual_semelhanca_textual(item_stg.raz_social, item_sot.raz_social)
    if similaridade_razao < LIMIAR_SEMELHANCA_TEXTO:
        divergencias.append(
            _nova_divergencia(
                campo="raz_social",
                label="Razao Social",
                valor_sor=item_stg.raz_social,
                valor_sot=item_sot.raz_social,
                gravidade=_gravidade_por_semelhanca(similaridade_razao),
                observacao=f"Semelhanca: {similaridade_razao * 100:.1f}%",
            )
        )

    return divergencias


def _montar_resumo_divergencias(divergencias: list[dict[str, Any]], tipo_pendencia: str) -> dict[str, Any]:
    severidades = {"alta": 0, "media": 0, "leve": 0}
    campos: list[str] = []

    for item in divergencias:
        gravidade = str(item.get("gravidade") or "").strip().lower()
        if gravidade in severidades:
            severidades[gravidade] += 1

        label = str(item.get("label") or "").strip()
        if label:
            campos.append(label)

    return {
        "tipo": tipo_pendencia,
        "total": len(divergencias),
        "alta": severidades["alta"],
        "media": severidades["media"],
        "leve": severidades["leve"],
        "campos": sorted(set(campos)),
    }


def _contains_search(haystacks: list[Any], search: str) -> bool:
    termo = str(search or "").strip().lower()
    if not termo:
        return True
    return any(termo in str(valor or "").lower() for valor in haystacks)


def _produto_equivalente(item_stg: StgProdutosNovos, item_sot: Produto | None) -> bool:
    return item_sot is not None and len(_coletar_divergencias_produto(item_stg, item_sot)) == 0


def _cliente_equivalente(item_stg: StgClientesNovos, item_sot: Cliente | None) -> bool:
    return item_sot is not None and len(_coletar_divergencias_cliente(item_stg, item_sot)) == 0


def _fornecedor_equivalente(item_stg: StgFornecedoresNovos, item_sot: Fornecedor | None) -> bool:
    return item_sot is not None and len(_coletar_divergencias_fornecedor(item_stg, item_sot)) == 0


def contar_produtos_pendentes_validacao() -> int:
    stg_items = list(StgProdutosNovos.objects.all())
    if not stg_items:
        return 0

    produto_ids = [item.id_produto for item in stg_items]
    sot_por_id = {
        item.id_produto: item
        for item in Produto.objects.filter(id_produto__in=produto_ids)
    }

    return sum(
        1
        for item in stg_items
        if not _produto_equivalente(item, sot_por_id.get(item.id_produto))
    )


def contar_clientes_pendentes_validacao() -> int:
    stg_items = list(StgClientesNovos.objects.all())
    if not stg_items:
        return 0

    cliente_ids = [item.id_cliente for item in stg_items]
    sot_por_id = {
        item.id_cliente: item
        for item in Cliente.objects.filter(id_cliente__in=cliente_ids)
    }

    return sum(
        1
        for item in stg_items
        if not _cliente_equivalente(item, sot_por_id.get(item.id_cliente))
    )


def contar_fornecedores_pendentes_validacao() -> int:
    stg_items = list(StgFornecedoresNovos.objects.all())
    if not stg_items:
        return 0

    fornecedor_ids = [item.id_fornecedor for item in stg_items]
    sot_por_id = {
        item.id_fornecedor: item
        for item in Fornecedor.objects.filter(id_fornecedor__in=fornecedor_ids)
    }

    return sum(
        1
        for item in stg_items
        if not _fornecedor_equivalente(item, sot_por_id.get(item.id_fornecedor))
    )


def contar_pendencias_validacao() -> dict[str, int]:
    return {
        "produtos": contar_produtos_pendentes_validacao(),
        "clientes": contar_clientes_pendentes_validacao(),
        "fornecedores": contar_fornecedores_pendentes_validacao(),
    }


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
            divergencias = _coletar_divergencias_produto(item, produto_sot)
            if produto_sot is not None and not divergencias:
                continue

            tipo_pendencia = "ATUALIZACAO" if produto_sot is not None else "NOVO"
            resumo_divergencias = _montar_resumo_divergencias(divergencias, tipo_pendencia)
            dados_sot: dict[str, Any] | None = None

            if produto_sot is not None:
                dados_sot = {
                    "nome": produto_sot.produto,
                    "gtin": produto_sot.gtin,
                    "barras": produto_sot.barras,
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
                    "gtin": item.gtin,
                    "barras": item.barras,
                    "unidade_comercial": item.unidade_comecial,
                    "custo": item.custo,
                    "valor_venda": item.valor_venda,
                    "dt_ultimo_movimento": item.dt_ultimo_movimento,
                    "status": item.status,
                    "unidade_sugerida_id": resolve_unidade_sugerida(item.unidade_comecial),
                    "tipo_pendencia": tipo_pendencia,
                    "dados_sot": dados_sot,
                    "divergencias": divergencias,
                    "divergencias_resumo": resumo_divergencias,
                }
            )

        if not search:
            return resultado

        return [
            item
            for item in resultado
            if _contains_search([item.get("id_produto"), item.get("nome")], search)
        ]
    except Exception:
        logger.exception("Falha ao listar produtos pendentes da staging.")
        raise


def aprovar_produto_novo(dados_validados: dict[str, Any]) -> None:
    try:
        with transaction.atomic():
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
                    "produto": dados_validados["nome"],
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
                        nome=dados_validados["nome"],
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
            divergencias = _coletar_divergencias_cliente(item, cliente_sot)
            if cliente_sot is not None and not divergencias:
                continue

            tipo_pendencia = "ATUALIZACAO" if cliente_sot is not None else "NOVO"
            resumo_divergencias = _montar_resumo_divergencias(divergencias, tipo_pendencia)
            dados_sot: dict[str, Any] | None = None
            if cliente_sot is not None:
                dados_sot = {
                    "id_cliente": cliente_sot.id_cliente,
                    "cliente": cliente_sot.nome_cliente,
                    "nome_cliente": cliente_sot.nome_cliente,
                    "raz_social": cliente_sot.raz_social,
                    "prazo_cob": cliente_sot.prazo_cob,
                    "id_grupo": cliente_sot.id_grupo_id,
                    "id_tipo_venda": cliente_sot.id_tipo_venda_id,
                }

            resultado.append(
                {
                    "id_cliente": item.id_cliente,
                    "nome_cliente": item.cliente,
                    "raz_social": item.raz_social,
                    "tipo_pendencia": tipo_pendencia,
                    "dados_sot": dados_sot,
                    "divergencias": divergencias,
                    "divergencias_resumo": resumo_divergencias,
                }
            )

        if not search:
            return resultado

        return [
            item
            for item in resultado
            if _contains_search([item.get("id_cliente"), item.get("nome_cliente"), item.get("raz_social")], search)
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
            divergencias = _coletar_divergencias_fornecedor(item, fornecedor_sot)
            if fornecedor_sot is not None and not divergencias:
                continue

            tipo_pendencia = "ATUALIZACAO" if fornecedor_sot is not None else "NOVO"
            resumo_divergencias = _montar_resumo_divergencias(divergencias, tipo_pendencia)
            dados_sot: dict[str, Any] | None = None
            if fornecedor_sot is not None:
                dados_sot = {
                    "id_fornecedor": fornecedor_sot.id_fornecedor,
                    "fantasia": fornecedor_sot.nome_fornecedor,
                    "nome_fornecedor": fornecedor_sot.nome_fornecedor,
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
                    "raz_social": item.raz_social,
                    "dt_cadastro": item.dt_cadastro,
                    "tipo_pendencia": tipo_pendencia,
                    "dados_sot": dados_sot,
                    "divergencias": divergencias,
                    "divergencias_resumo": resumo_divergencias,
                }
            )

        if not search:
            return resultado

        return [
            item
            for item in resultado
            if _contains_search([item.get("id_fornecedor"), item.get("nome_fornecedor"), item.get("raz_social")], search)
        ]
    except Exception:
        logger.exception("Falha ao listar fornecedores pendentes da staging.")
        raise


def aprovar_cliente_novo(dados_validados: dict[str, Any]) -> None:
    try:
        with transaction.atomic():
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
                    "nome_cliente": dados_validados["nome_cliente"],
                    "raz_social": dados_validados.get("raz_social", ""),
                    "prazo_cob": dados_validados.get("prazo_cob", 0),
                    "id_grupo": grupo,
                    "id_tipo_venda": tipo_venda,
                    "hash_md5": gerar_hash_cliente(
                        id_cliente=dados_validados["id_cliente"],
                        nome_cliente=dados_validados["nome_cliente"],
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
            codsis = None
            if dados_validados.get("id_codsis") is not None:
                codsis, _ = CodSis.objects.get_or_create(
                    id_codsis=dados_validados["id_codsis"],
                    defaults={"nome": f"CodSis {dados_validados['id_codsis']}"},
                )

            Fornecedor.objects.update_or_create(
                id_fornecedor=dados_validados["id_fornecedor"],
                defaults={
                    "nome_fornecedor": dados_validados["nome_fornecedor"],
                    "raz_social": dados_validados.get("raz_social", ""),
                    "dt_cadastro": dados_validados.get("dt_cadastro") or date.today(),
                    "id_codsis": codsis,
                    "codigo": dados_validados.get("codigo", ""),
                    "operador": dados_validados.get("operador", 0),
                    "usuario": dados_validados.get("usuario", ""),
                    "hash_md5": gerar_hash_fornecedor(
                        id_fornecedor=dados_validados["id_fornecedor"],
                        nome_fornecedor=dados_validados["nome_fornecedor"],
                        raz_social=dados_validados.get("raz_social", ""),
                        dt_cadastro=dados_validados.get("dt_cadastro") or date.today(),
                    ),
                },
            )

            StgFornecedoresNovos.objects.filter(id_fornecedor=dados_validados["id_fornecedor"]).delete()

        logger.info("Fornecedor %s aprovado com sucesso.", dados_validados["id_fornecedor"])
    except Exception:
        logger.exception("Falha ao aprovar fornecedor %s.", dados_validados.get("id_fornecedor"))
        raise


def aplicar_tratamento_pendencias_lote(*, entidade: str, acao: str, ids: list[int]) -> dict[str, Any]:
    entidade_norm = str(entidade or "").strip().lower()
    acao_norm = str(acao or "").strip().lower()

    if entidade_norm not in {"produtos", "clientes", "fornecedores"}:
        raise ValueError("entidade invalida. Use produtos, clientes ou fornecedores.")
    if acao_norm not in {"validar", "negligenciar"}:
        raise ValueError("acao invalida. Use validar ou negligenciar.")

    ids_norm = sorted({int(raw_id) for raw_id in ids if str(raw_id).strip()})
    if not ids_norm:
        raise ValueError("Informe ao menos um ID para tratamento em lote.")

    falhas: list[dict[str, Any]] = []
    processados = 0

    if acao_norm == "negligenciar":
        if entidade_norm == "produtos":
            deletados, _ = StgProdutosNovos.objects.filter(id_produto__in=ids_norm).delete()
        elif entidade_norm == "clientes":
            deletados, _ = StgClientesNovos.objects.filter(id_cliente__in=ids_norm).delete()
        else:
            deletados, _ = StgFornecedoresNovos.objects.filter(id_fornecedor__in=ids_norm).delete()

        return {
            "detail": f"Tratamento em lote concluido para {entidade_norm}.",
            "entidade": entidade_norm,
            "acao": acao_norm,
            "processados": int(deletados),
            "falhas": falhas,
        }

    for item_id in ids_norm:
        try:
            if entidade_norm == "produtos":
                pendente = StgProdutosNovos.objects.filter(id_produto=item_id).first()
                if pendente is None:
                    raise ValueError("produto pendente nao encontrado")

                produto_sot = (
                    Produto.objects.select_related("id_und_medida")
                    .prefetch_related("categorias")
                    .filter(id_produto=item_id)
                    .first()
                )

                unidade_id = None
                sigla = str(pendente.unidade_comecial or "").strip().upper()
                if sigla:
                    unidade, _ = UnidadeMedida.objects.get_or_create(sigla=sigla, defaults={"descricao": sigla})
                    unidade_id = unidade.id_und_medida
                elif produto_sot and produto_sot.id_und_medida_id is not None:
                    unidade_id = int(produto_sot.id_und_medida_id)

                if unidade_id is None:
                    raise ValueError("unidade de medida nao identificada")

                categorias_ids: list[int] = []
                if produto_sot is not None:
                    categorias_ids = list(produto_sot.categorias.values_list("id_conta", flat=True))

                aprovar_produto_novo(
                    {
                        "id_produto": pendente.id_produto,
                        "nome": pendente.nome,
                        "gtin": pendente.gtin,
                        "barras": pendente.barras,
                        "status": pendente.status or (produto_sot.status if produto_sot else "ATIVO"),
                        "ult_mov": pendente.dt_ultimo_movimento,
                        "custo": pendente.custo,
                        "valor_venda": pendente.valor_venda,
                        "id_und_medida": unidade_id,
                        "markup": produto_sot.markup if produto_sot else 0,
                        "markup_inv": produto_sot.markup_inv if produto_sot else 0,
                        "perda": produto_sot.perda if produto_sot else 0,
                        "categorias_ids": categorias_ids,
                        "fisico": produto_sot.fisico if produto_sot else 0,
                        "aliqefc": produto_sot.aliqefc if produto_sot else "",
                        "cod_g3n": produto_sot.cod_g3n if produto_sot else 0,
                        "cod_rel": produto_sot.cod_rel if produto_sot else 0,
                        "usuario": produto_sot.usuario if produto_sot else "",
                    }
                )

            elif entidade_norm == "clientes":
                pendente = StgClientesNovos.objects.filter(id_cliente=item_id).first()
                if pendente is None:
                    raise ValueError("cliente pendente nao encontrado")

                cliente_sot = Cliente.objects.filter(id_cliente=item_id).first()
                aprovar_cliente_novo(
                    {
                        "id_cliente": pendente.id_cliente,
                        "nome_cliente": pendente.cliente,
                        "raz_social": pendente.raz_social,
                        "prazo_cob": cliente_sot.prazo_cob if cliente_sot else 0,
                        "id_grupo": cliente_sot.id_grupo_id if cliente_sot else None,
                        "id_tipo_venda": cliente_sot.id_tipo_venda_id if cliente_sot else None,
                    }
                )

            else:
                pendente = StgFornecedoresNovos.objects.filter(id_fornecedor=item_id).first()
                if pendente is None:
                    raise ValueError("fornecedor pendente nao encontrado")

                fornecedor_sot = Fornecedor.objects.filter(id_fornecedor=item_id).first()
                aprovar_fornecedor_novo(
                    {
                        "id_fornecedor": pendente.id_fornecedor,
                        "nome_fornecedor": pendente.fantasia,
                        "raz_social": pendente.raz_social,
                        "dt_cadastro": pendente.dt_cadastro or (fornecedor_sot.dt_cadastro if fornecedor_sot else date.today()),
                        "id_codsis": fornecedor_sot.id_codsis_id if fornecedor_sot else None,
                        "codigo": fornecedor_sot.codigo if fornecedor_sot else "",
                        "operador": fornecedor_sot.operador if fornecedor_sot else 0,
                        "usuario": fornecedor_sot.usuario if fornecedor_sot else "",
                    }
                )

            processados += 1
        except Exception as exc:
            falhas.append({"id": item_id, "erro": str(exc)})

    return {
        "detail": f"Tratamento em lote concluido para {entidade_norm}.",
        "entidade": entidade_norm,
        "acao": acao_norm,
        "processados": processados,
        "falhas": falhas[:100],
    }
