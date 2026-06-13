from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import fdb
from django.conf import settings
from django.db import transaction

from apps.compras.models import STG_Compra, STG_ItemCompra

logger = logging.getLogger(__name__)


SQL_COMPRAS = """
    SELECT
        NC.ID,
        NC.NOTA,
        NC.ID_FORNECEDOR,
        COALESCE(F.FANTASIA, '') AS NOME_FORNECEDOR,
        NC.DATA_EMISSAO,
        NC.DATA_LANC,
        NC.VALOR_PRODUTOS,
        NC.VALOR_TOTAL,
        COALESCE(NC.NFE_STATUS, '') AS NFE_STATUS
    FROM NOTA_COMPRA NC
    LEFT JOIN FORNECEDOR F ON F.ID_FORNECEDOR = NC.ID_FORNECEDOR
    WHERE NC.DATA_EMISSAO BETWEEN ? AND ?
"""


SQL_ITENS_COMPRA = """
    SELECT
        NCD.ID,
        NCD.ID_NFE,
        NCD.ID_PRODUTO,
        COALESCE(P.PRODUTO, '') AS NOME_PRODUTO,
        NCD.QUANTIDADE,
        NCD.VALOR_CUSTO,
        (COALESCE(NCD.QUANTIDADE, 0) * COALESCE(NCD.VALOR_CUSTO, 0)) AS VALOR_TOTAL,
        COALESCE(NCD.UNIDADE, '') AS UNIDADE,
        COALESCE(NCD.DESCRICAO, '') AS DESCRICAO,
        COALESCE(NCD.DESCRICAO_COMPRA, '') AS DESCRICAO_COMPRA
    FROM NOTA_COMPRA_DETALHE NCD
    INNER JOIN NOTA_COMPRA NC ON NC.ID = NCD.ID_NFE
    LEFT JOIN PRODUTOS P ON P.ID_PRODUTO = NCD.ID_PRODUTO
    WHERE NC.DATA_EMISSAO BETWEEN ? AND ?
"""


def _build_firebird_dsn(firebird_path: str | None = None) -> str:
    fdb_path = str(firebird_path or settings.FDB_PATH or "").strip()
    if not fdb_path:
        raise ValueError("FDB_PATH is not configured in environment.")

    host = str(settings.FDB_HOST or "").strip()
    port = str(settings.FDB_PORT or "").strip()

    if host and port:
        return f"{host}/{port}:{fdb_path}"
    if host:
        return f"{host}:{fdb_path}"
    return fdb_path


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("latin-1", errors="ignore").strip()
    return str(value).strip()


def _to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _to_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()

    raw = _normalize_text(value)
    if not raw:
        return None

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def sincronizar_compras_legado(
    data_inicial: date,
    data_final: date,
    firebird_path: str | None = None,
) -> dict[str, Any]:
    logger.info(
        "Iniciando sincronizacao de compras legado (Firebird). Periodo: %s a %s",
        data_inicial,
        data_final,
    )

    if settings.FDB_CLIENT_LIB_PATH:
        fdb.fb_library_name = settings.FDB_CLIENT_LIB_PATH

    dsn = _build_firebird_dsn(firebird_path=firebird_path)

    conn = None
    cursor = None

    try:
        conn = fdb.connect(
            dsn=dsn,
            user=settings.FDB_USER,
            password=settings.FDB_PASS,
            charset="WIN1252",
        )
        cursor = conn.cursor()

        with transaction.atomic():
            STG_ItemCompra.objects.all().delete()
            STG_Compra.objects.all().delete()

            cursor.execute(SQL_COMPRAS, (data_inicial, data_final))
            compras_rows = cursor.fetchall()

            stg_compras: list[STG_Compra] = []
            ids_compra: set[int] = set()
            for row in compras_rows:
                id_compra_legado = _to_int(row[0])
                if id_compra_legado is None:
                    continue

                ids_compra.add(id_compra_legado)
                stg_compras.append(
                    STG_Compra(
                        id_compra_legado=id_compra_legado,
                        nota=_to_int(row[1]),
                        id_fornecedor_legado=_to_int(row[2]),
                        nome_fornecedor_legado=_normalize_text(row[3]),
                        data_emissao=_to_date(row[4]) or data_inicial,
                        data_lanc=_to_date(row[5]),
                        valor_produtos=_to_decimal(row[6]),
                        valor_total=_to_decimal(row[7]),
                        nfe_status=_normalize_text(row[8]),
                    )
                )

            if stg_compras:
                STG_Compra.objects.bulk_create(stg_compras, batch_size=2000)

            mapa_stg_compra_id: dict[int, int] = {}
            if ids_compra:
                for compra in STG_Compra.objects.filter(id_compra_legado__in=ids_compra).only(
                    "id_stg_compra", "id_compra_legado"
                ):
                    mapa_stg_compra_id[int(compra.id_compra_legado)] = int(compra.id_stg_compra)

            cursor.execute(SQL_ITENS_COMPRA, (data_inicial, data_final))
            itens_rows = cursor.fetchall()

            stg_itens: list[STG_ItemCompra] = []
            for row in itens_rows:
                id_compra_legado = _to_int(row[1])
                if id_compra_legado is None:
                    continue

                stg_compra_id = mapa_stg_compra_id.get(id_compra_legado)
                if stg_compra_id is None:
                    continue

                quantidade = _to_decimal(row[4])
                valor_custo = _to_decimal(row[5])
                valor_total_legado = _to_decimal(row[6])
                valor_total_calculado = None
                if quantidade is not None and valor_custo is not None:
                    valor_total_calculado = quantidade * valor_custo

                stg_itens.append(
                    STG_ItemCompra(
                        stg_compra_id=stg_compra_id,
                        id_item_legado=_to_int(row[0]),
                        id_compra_legado=id_compra_legado,
                        id_produto_legado=_to_int(row[2]),
                        nome_produto_legado=_normalize_text(row[3]),
                        quantidade=quantidade,
                        valor_custo=valor_custo,
                        valor_total_legado=valor_total_legado,
                        valor_total_calculado=valor_total_calculado,
                        unidade_legado=_normalize_text(row[7]),
                        descricao_legado=_normalize_text(row[8]),
                        descricao_compra_legado=_normalize_text(row[9]),
                    )
                )

            if stg_itens:
                STG_ItemCompra.objects.bulk_create(stg_itens, batch_size=3000)

        resultado = {
            "periodo": {
                "data_inicial": data_inicial.isoformat(),
                "data_final": data_final.isoformat(),
            },
            "totais": {
                "compras": len(stg_compras),
                "itens": len(stg_itens),
            },
        }

        logger.info("Sincronizacao de compras legado concluida: %s", resultado)
        return resultado
    except Exception:
        logger.exception("Falha ao sincronizar compras legado")
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()
