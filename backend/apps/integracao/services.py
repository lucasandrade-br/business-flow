from __future__ import annotations

import asyncio
import logging
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
from typing import Any

import fdb
from django.conf import settings
from django.db import transaction

from apps.cadastros.models import UnidadeMedida

from .hash_engine import gerar_hash_cliente, gerar_hash_fornecedor, gerar_hash_produto
from .models import StgClientesNovos, StgFornecedoresNovos, StgProdutosNovos

logger = logging.getLogger(__name__)

SQL_PRODUTOS = """
SELECT
    PRODUTOS.ID_PRODUTO,
    PRODUTOS.GTIN,
    PRODUTOS.BARRAS,
    PRODUTOS.PRODUTO,
    PRODUTOS.UNIDADE_COMECIAL,
    PRODUTOS.CUSTO,
    PRODUTOS.VALOR_VENDA,
    PRODUTOS.DT_ULTIMO_MOVIMENTO,
    PRODUTOS.STATUS
FROM PRODUTOS
"""

SQL_FORNECEDORES = """
SELECT
    FORNECEDOR.ID_FORNECEDOR,
    FORNECEDOR.FANTASIA,
    FORNECEDOR.RAZ_SOCIAL,
    FORNECEDOR.DT_CADASTRO
FROM FORNECEDOR
"""

SQL_FORNECEDORES_FALLBACK = """
SELECT
    FORNECEDORES.ID_FORNECEDOR,
    FORNECEDORES.FANTASIA,
    FORNECEDORES.RAZ_SOCIAL,
    FORNECEDORES.DT_CADASTRO
FROM FORNECEDORES
"""

SQL_CLIENTES = """
SELECT
    CLIENTES.ID_CLIENTE,
    CLIENTES.CLIENTE,
    CLIENTES.RAZ_SOCIAL
FROM CLIENTES
"""


def _build_firebird_dsn() -> str:
    fdb_path = settings.FDB_PATH
    if not fdb_path:
        raise ValueError("FDB_PATH is not configured in environment.")

    host = settings.FDB_HOST.strip()
    port = str(settings.FDB_PORT).strip()

    if host:
        if port:
            return f"{host}/{port}:{fdb_path}"
        return f"{host}:{fdb_path}"
    return fdb_path


def _normalize_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("latin-1", errors="ignore")
    if isinstance(value, str):
        return value.replace("\ufffd", "")
    return value


def _normalize_decimal(value: Any, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)

    normalized = _normalize_value(value)
    if isinstance(normalized, Decimal):
        return normalized

    try:
        return Decimal(str(normalized).replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


def _normalize_date(value: Any) -> date | None:
    if value is None:
        return None

    normalized = _normalize_value(value)
    if isinstance(normalized, datetime):
        return normalized.date()
    if isinstance(normalized, date):
        return normalized
    return None


def extrair_produtos_novos_sync() -> int:
    logger.info("Iniciando ETL de produtos para staging MySQL")

    if settings.FDB_CLIENT_LIB_PATH:
        fdb.fb_library_name = settings.FDB_CLIENT_LIB_PATH

    dsn = _build_firebird_dsn()

    conn = None
    cursor = None
    rows_to_insert: list[StgProdutosNovos] = []
    unidades_detectadas: set[str] = set()
    skipped_rows = 0

    try:
        conn = fdb.connect(
            dsn=dsn,
            user=settings.FDB_USER,
            password=settings.FDB_PASS,
        )
        cursor = conn.cursor()
        cursor.execute(SQL_PRODUTOS)

        for row in cursor:
            raw_id = _normalize_value(row[0])
            if raw_id is None:
                skipped_rows += 1
                continue

            id_produto = int(raw_id)
            gtin = str(_normalize_value(row[1]) or "").strip()
            barras = str(_normalize_value(row[2]) or "").strip()
            produto = str(_normalize_value(row[3]) or "").strip()
            unidade_comercial = str(_normalize_value(row[4]) or "").strip().upper()
            custo = _normalize_decimal(row[5])
            valor_venda = _normalize_decimal(row[6])
            dt_ultimo_movimento = _normalize_date(row[7])
            status = str(_normalize_value(row[8]) or "").strip()

            if unidade_comercial:
                unidades_detectadas.add(unidade_comercial)

            rows_to_insert.append(
                StgProdutosNovos(
                    id_produto=id_produto,
                    gtin=gtin,
                    barras=barras,
                    nome=produto,
                    unidade_comecial=unidade_comercial,
                    custo=custo,
                    valor_venda=valor_venda,
                    dt_ultimo_movimento=dt_ultimo_movimento,
                    status=status,
                    hash_md5=gerar_hash_produto(
                        id_produto=id_produto,
                        gtin=gtin,
                        barras=barras,
                        nome=produto,
                        custo=custo,
                        venda=valor_venda,
                        status=status,
                    ),
                )
            )

        with transaction.atomic():
            if unidades_detectadas:
                unidades_existentes = set(
                    UnidadeMedida.objects.filter(sigla__in=unidades_detectadas).values_list(
                        "sigla", flat=True
                    )
                )
                novas_unidades = [
                    UnidadeMedida(sigla=codigo, descricao=codigo)
                    for codigo in sorted(unidades_detectadas - unidades_existentes)
                ]
                if novas_unidades:
                    UnidadeMedida.objects.bulk_create(novas_unidades, batch_size=500)

            StgProdutosNovos.objects.all().delete()
            if rows_to_insert:
                StgProdutosNovos.objects.bulk_create(rows_to_insert, batch_size=2000)

        logger.info(
            "ETL de produtos finalizado com sucesso. Registros inseridos: %s. Registros ignorados: %s",
            len(rows_to_insert),
            skipped_rows,
        )
        return len(rows_to_insert)

    except Exception:
        logger.exception("Falha no ETL de produtos")
        raise

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


async def extrair_produtos_novos() -> int:
    return await asyncio.to_thread(extrair_produtos_novos_sync)


def extrair_fornecedores_novos_sync() -> int:
    logger.info("Iniciando ETL de fornecedores para staging MySQL")

    if settings.FDB_CLIENT_LIB_PATH:
        fdb.fb_library_name = settings.FDB_CLIENT_LIB_PATH

    dsn = _build_firebird_dsn()
    conn = None
    cursor = None
    rows_to_insert: list[StgFornecedoresNovos] = []

    try:
        conn = fdb.connect(dsn=dsn, user=settings.FDB_USER, password=settings.FDB_PASS)
        cursor = conn.cursor()

        # Alguns bancos de origem usam FORNECEDOR e outros FORNECEDORES.
        executed = False
        last_error: Exception | None = None
        for sql in (SQL_FORNECEDORES, SQL_FORNECEDORES_FALLBACK):
            try:
                cursor.execute(sql)
                executed = True
                break
            except Exception as exc:
                last_error = exc
                logger.warning("Consulta de fornecedores falhou para um alias de tabela. Tentando fallback...")

        if not executed:
            raise last_error if last_error is not None else RuntimeError("Nao foi possivel executar SQL de fornecedores.")

        for row in cursor:
            raw_id = _normalize_value(row[0])
            if raw_id is None:
                continue

            rows_to_insert.append(
                StgFornecedoresNovos(
                    id_fornecedor=int(raw_id),
                    fantasia=str(_normalize_value(row[1]) or "").strip(),
                    raz_social=str(_normalize_value(row[2]) or "").strip(),
                    dt_cadastro=_normalize_date(row[3]),
                    hash_md5=gerar_hash_fornecedor(
                        id_fornecedor=raw_id,
                        nome_fornecedor=row[1],
                        raz_social=row[2],
                        dt_cadastro=_normalize_date(row[3]),
                    ),
                )
            )

        with transaction.atomic():
            StgFornecedoresNovos.objects.all().delete()
            if rows_to_insert:
                StgFornecedoresNovos.objects.bulk_create(rows_to_insert, batch_size=2000)

        logger.info("ETL de fornecedores finalizado com sucesso. Registros inseridos: %s", len(rows_to_insert))
        return len(rows_to_insert)

    except Exception:
        logger.exception("Falha no ETL de fornecedores")
        raise

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


async def extrair_fornecedores_novos() -> int:
    return await asyncio.to_thread(extrair_fornecedores_novos_sync)


def extrair_clientes_novos_sync() -> int:
    logger.info("Iniciando ETL de clientes para staging MySQL")

    if settings.FDB_CLIENT_LIB_PATH:
        fdb.fb_library_name = settings.FDB_CLIENT_LIB_PATH

    dsn = _build_firebird_dsn()
    conn = None
    cursor = None
    rows_to_insert: list[StgClientesNovos] = []

    try:
        conn = fdb.connect(dsn=dsn, user=settings.FDB_USER, password=settings.FDB_PASS)
        cursor = conn.cursor()
        cursor.execute(SQL_CLIENTES)

        for row in cursor:
            raw_id = _normalize_value(row[0])
            if raw_id is None:
                continue

            rows_to_insert.append(
                StgClientesNovos(
                    id_cliente=int(raw_id),
                    cliente=str(_normalize_value(row[1]) or "").strip(),
                    raz_social=str(_normalize_value(row[2]) or "").strip(),
                    hash_md5=gerar_hash_cliente(
                        id_cliente=raw_id,
                        nome_cliente=row[1],
                        raz_social=row[2],
                    ),
                )
            )

        with transaction.atomic():
            StgClientesNovos.objects.all().delete()
            if rows_to_insert:
                StgClientesNovos.objects.bulk_create(rows_to_insert, batch_size=2000)

        logger.info("ETL de clientes finalizado com sucesso. Registros inseridos: %s", len(rows_to_insert))
        return len(rows_to_insert)

    except Exception:
        logger.exception("Falha no ETL de clientes")
        raise

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


async def extrair_clientes_novos() -> int:
    return await asyncio.to_thread(extrair_clientes_novos_sync)


async def executar_extracao_completa() -> dict[str, int]:
    results = {
        "produtos": await extrair_produtos_novos(),
        "clientes": await extrair_clientes_novos(),
        "fornecedores": await extrair_fornecedores_novos(),
    }
    logger.info("Extracao completa concluida. Resultado: %s", results)
    return results


async def executar_etl_integracao() -> dict[str, int]:
    """Compatibilidade: alias para extracao completa."""
    return await executar_extracao_completa()
