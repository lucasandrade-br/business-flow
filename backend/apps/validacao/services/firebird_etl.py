from __future__ import annotations

import logging
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any

import fdb
from django.conf import settings
from django.db import transaction

from apps.validacao.models import STG_AuditoriaPlanilha, STG_ItemVenda, STG_PagamentoVenda, STG_Venda

logger = logging.getLogger(__name__)


def _build_firebird_dsn() -> str:
    fdb_path = settings.FDB_PATH
    if not fdb_path:
        raise ValueError("FDB_PATH is not configured in environment.")

    host = str(settings.FDB_HOST or "").strip()
    port = str(settings.FDB_PORT or "").strip()

    if host and port:
        return f"{host}/{port}:{fdb_path}"
    if host:
        return f"{host}:{fdb_path}"
    return fdb_path


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _to_time(value: Any) -> time | None:
    if value is None:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time()

    raw = str(value).strip()
    if not raw:
        return None

    parts = raw.split(":")
    if len(parts) >= 2:
        try:
            hh = int(parts[0])
            mm = int(parts[1])
            ss = int(parts[2]) if len(parts) > 2 else 0
            return time(hour=hh, minute=mm, second=ss)
        except (ValueError, TypeError):
            return None
    return None


def _to_bool_flag(value: Any) -> bool:
    if value is None:
        return False
    raw = str(value).strip().upper()
    return raw in {"1", "S", "SIM", "Y", "YES", "T", "TRUE"}


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("latin-1", errors="ignore").strip()
    return str(value).strip()


def _extract_documento_3_blocos(
    cursor: fdb.fbcore.Cursor,
    tipo_documento: str,
    tabela_cabecalho: str,
    tabela_itens: str,
    tabela_pagamentos: str,
    tabela_formas_pagamento: str,
    coluna_fk_itens: str,
    data_inicial: date,
    data_final: date,
) -> dict[str, int]:
    sql_cabecalho = f"""
        SELECT
            C.ID,
            C.DATA_VENDA,
            C.HORA_VENDA,
            C.ID_USUARIO,
            C.VALOR_FINAL,
            C.STATUS_VENDA,
            C.NOME_COMPUTADOR,
            U.USUARIO AS NOME_USUARIO_LEGADO,
            CASE WHEN (C.ID_CLIENTE = 0 OR C.ID_CLIENTE IS NULL) THEN 0 ELSE C.ID_CLIENTE END AS ID_CLIENTE_NORM,
            CASE WHEN (C.NOME_CLIENTE = '' OR C.NOME_CLIENTE IS NULL) THEN 'Consumidor Geral' ELSE C.NOME_CLIENTE END AS NOME_CLIENTE_NORM
        FROM {tabela_cabecalho} C
        LEFT JOIN USUARIO U ON C.ID_USUARIO = U.ID
        WHERE C.DATA_VENDA BETWEEN ? AND ?
    """

    cursor.execute(sql_cabecalho, (data_inicial, data_final))
    headers_rows = cursor.fetchall()

    stg_vendas = []

    for row in headers_rows:
        id_legado = int(row[0])
        stg_vendas.append(
            STG_Venda(
                tipo_documento=tipo_documento,
                id_legado=id_legado,
                data_venda=row[1],
                hora_venda=_to_time(row[2]),
                id_usuario_legado=row[3],
                valor_final=_to_decimal(row[4]),
                status_venda=_normalize_text(row[5]),
                nome_computador=_normalize_text(row[6]),
                nome_usuario_legado=_normalize_text(row[7]),
                id_cliente_legado=row[8],
                nome_cliente_legado=_normalize_text(row[9]) or "Consumidor Geral",
            )
        )

    STG_Venda.objects.bulk_create(stg_vendas, batch_size=2000)

    vendas_salvas = STG_Venda.objects.filter(
        tipo_documento=tipo_documento,
        data_venda__range=(data_inicial, data_final),
    )
    mapa_vendas_id = {v.id_legado: v.pk for v in vendas_salvas}
    mapa_vendas = {v.id_legado: v for v in vendas_salvas}

    if not mapa_vendas_id:
        return {"vendas": 0, "itens": 0, "pagamentos": 0}

    sql_itens = f"""
        SELECT
            I.ID_PRODUTO,
            P.PRODUTO,
            P.UNIDADE_COMECIAL,
            I.QUANTIDADE,
            I.VALOR_UNITARIO,
            (I.QUANTIDADE * I.VALOR_UNITARIO) AS VALOR_TOTAL_CALCULADO,
            I.CANCELADO,
            I.{coluna_fk_itens} AS ID_VENDA
        FROM {tabela_itens} I
        INNER JOIN {tabela_cabecalho} C ON I.{coluna_fk_itens} = C.ID
        INNER JOIN PRODUTOS P ON I.ID_PRODUTO = P.ID_PRODUTO
        WHERE C.DATA_VENDA BETWEEN ? AND ?
    """
    cursor.execute(sql_itens, (data_inicial, data_final))
    itens_rows = cursor.fetchall()

    stg_itens = []
    for row in itens_rows:
        id_venda_legado = int(row[7])
        stg_venda_id = mapa_vendas_id.get(id_venda_legado)
        parent = mapa_vendas.get(id_venda_legado)
        if stg_venda_id is None or parent is None:
            continue

        stg_itens.append(
            STG_ItemVenda(
                stg_venda_id=stg_venda_id,
                tipo_documento=tipo_documento,
                id_venda_legado=id_venda_legado,
                data_venda=parent.data_venda,
                hora_venda=parent.hora_venda,
                status_venda=parent.status_venda,
                id_cliente_legado=parent.id_cliente_legado,
                nome_cliente_legado=parent.nome_cliente_legado,
                id_produto_legado=row[0],
                nome_produto_legado=_normalize_text(row[1]),
                unidade_comercial_legado=_normalize_text(row[2]),
                quantidade=_to_decimal(row[3]),
                valor_unitario=_to_decimal(row[4]),
                valor_total_calculado=_to_decimal(row[5]),
                cancelado=_to_bool_flag(row[6]),
            )
        )

    STG_ItemVenda.objects.bulk_create(stg_itens, batch_size=3000)

    sql_pagamentos = f"""
        SELECT
            P.ID_TIPO_PAGAMENTO,
            COALESCE(FP.DESCRICAO, '') AS TIPO_PAGAMENTO_DESCRICAO,
            P.VALOR,
            P.ID_VENDA_CABECALHO
        FROM {tabela_pagamentos} P
        INNER JOIN {tabela_cabecalho} C ON P.ID_VENDA_CABECALHO = C.ID
        LEFT JOIN {tabela_formas_pagamento} FP ON P.ID_TIPO_PAGAMENTO = FP.ID
        WHERE C.DATA_VENDA BETWEEN ? AND ?
    """
    cursor.execute(sql_pagamentos, (data_inicial, data_final))
    pagamentos_rows = cursor.fetchall()

    stg_pagamentos = []
    for row in pagamentos_rows:
        id_venda_legado = int(row[3])
        stg_venda_id = mapa_vendas_id.get(id_venda_legado)
        if stg_venda_id is None:
            continue

        stg_pagamentos.append(
            STG_PagamentoVenda(
                stg_venda_id=stg_venda_id,
                tipo_documento=tipo_documento,
                id_venda_legado=id_venda_legado,
                id_tipo_pagamento_legado=row[0],
                tipo_pagamento_descricao_legado=_normalize_text(row[1]),
                valor_pago=_to_decimal(row[2]) or Decimal("0"),
            )
        )

    STG_PagamentoVenda.objects.bulk_create(stg_pagamentos, batch_size=3000)

    return {
        "vendas": len(mapa_vendas_id),
        "itens": len(stg_itens),
        "pagamentos": len(stg_pagamentos),
    }


def sincronizar_vendas_legado(data_inicial: date, data_final: date) -> dict[str, Any]:
    logger.info(
        "Iniciando sincronizacao de vendas legado (Firebird). Periodo: %s a %s",
        data_inicial,
        data_final,
    )

    if settings.FDB_CLIENT_LIB_PATH:
        fdb.fb_library_name = settings.FDB_CLIENT_LIB_PATH

    dsn = _build_firebird_dsn()

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
            # Cada sincronizacao reinicia o staging para manter apenas dados mais recentes.
            STG_AuditoriaPlanilha.objects.all().delete()
            STG_PagamentoVenda.objects.all().delete()
            STG_ItemVenda.objects.all().delete()
            STG_Venda.objects.all().delete()

            nfce_result = _extract_documento_3_blocos(
                cursor=cursor,
                tipo_documento=STG_Venda.TIPO_NFCE,
                tabela_cabecalho="NFCE",
                tabela_itens="NFCE_ITENS",
                tabela_pagamentos="NFCE_TOTAL_TIPO_PGTO",
                tabela_formas_pagamento="NFCE_FORMAS_PAGAMENTO",
                coluna_fk_itens="ID_NFCE",
                data_inicial=data_inicial,
                data_final=data_final,
            )

            dav_result = _extract_documento_3_blocos(
                cursor=cursor,
                tipo_documento=STG_Venda.TIPO_DAV,
                tabela_cabecalho="DAV",
                tabela_itens="DAV_ITENS",
                tabela_pagamentos="DAV_TOTAL_TIPO_PGTO",
                tabela_formas_pagamento="DAV_FORMAS_PAGAMENTO",
                coluna_fk_itens="ID_DAV",
                data_inicial=data_inicial,
                data_final=data_final,
            )

        resultado = {
            "periodo": {
                "data_inicial": data_inicial.isoformat(),
                "data_final": data_final.isoformat(),
            },
            "nfce": nfce_result,
            "dav": dav_result,
            "totais": {
                "vendas": nfce_result["vendas"] + dav_result["vendas"],
                "itens": nfce_result["itens"] + dav_result["itens"],
                "pagamentos": nfce_result["pagamentos"] + dav_result["pagamentos"],
            },
        }

        logger.info("Sincronizacao de vendas legado concluida: %s", resultado)
        return resultado
    except Exception:
        logger.exception("Falha ao sincronizar vendas legado")
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()
