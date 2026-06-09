from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from io import BytesIO
from os import cpu_count
from threading import Lock, Thread
from time import perf_counter
from typing import Any
from uuid import uuid4

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import Max, Min, Sum
from django.utils import timezone
from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel

from apps.cadastros.models import Cliente, FormaPagamento, Produto, Usuario
from apps.validacao.models import STG_AuditoriaPlanilha, STG_ItemVenda, STG_PagamentoVenda, STG_Venda
from apps.vendas.models import ItemVenda, PagamentoVenda, Venda


HOST_VENDA_SHEET_NAME = "HostVenda"
VALID_EXTENSIONS = {".xlsx", ".xlsm"}
DECIMAL_TOLERANCE = Decimal("0.01")
MOTIVOS_DIVERGENCIA_VALIDOS = {
    "divergencia_totais",
    "divergencia_formato",
    "duplicado_sot",
}

_IMPORT_JOBS: dict[str, dict[str, Any]] = {}
_IMPORT_JOBS_LOCK = Lock()


@dataclass
class ImportErrorItem:
    arquivo: str
    linha: int
    motivo: str


@dataclass
class ValidationResult:
    vendas_aprovadas: int
    vendas_divergentes: int
    vendas_duplicadas_sot: int
    divergencias: list[dict[str, Any]]
    inconsistencias: list[dict[str, Any]]
    kpis: dict[str, Any]
    pode_aprovar: bool


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_tipo_documento(value: Any) -> str:
    raw = _normalize_text(value).upper().replace("-", "")
    if raw in {"NFCE", "NFC-E"}:
        return STG_AuditoriaPlanilha.TIPO_NFCE
    if raw == STG_AuditoriaPlanilha.TIPO_DAV:
        return STG_AuditoriaPlanilha.TIPO_DAV
    return ""


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))

    raw = _normalize_text(value)
    if not raw:
        return None

    # Aceita entradas com simbolos monetarios e separadores pt-BR/en-US.
    cleaned = raw.replace("R$", "").replace(" ", "")
    allowed = "".join(ch for ch in cleaned if ch.isdigit() or ch in {".", ",", "-"})
    if not allowed or allowed in {"-", ".", ",", "-.", "-,"}:
        return None

    dot_count = allowed.count(".")
    comma_count = allowed.count(",")

    if dot_count and comma_count:
        # O ultimo separador visto e tratado como separador decimal.
        if allowed.rfind(",") > allowed.rfind("."):
            normalized = allowed.replace(".", "").replace(",", ".")
        else:
            normalized = allowed.replace(",", "")
    elif comma_count:
        normalized = allowed.replace(",", ".") if comma_count == 1 else allowed.replace(",", "")
    elif dot_count:
        normalized = allowed if dot_count == 1 else allowed.replace(".", "")
    else:
        normalized = allowed

    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError):
        return None


def _to_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, (int, float)):
        try:
            converted = from_excel(value)
            if isinstance(converted, datetime):
                return converted.date()
            if isinstance(converted, date):
                return converted
        except Exception:
            return None

    raw = _normalize_text(value)
    if not raw:
        return None

    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _to_time(value: Any) -> time | None:
    if value is None:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, (int, float)):
        try:
            converted = from_excel(value)
            if isinstance(converted, datetime):
                return converted.time()
            if isinstance(converted, time):
                return converted
        except Exception:
            return None

    raw = _normalize_text(value)
    if not raw:
        return None

    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
    return None


def _normalize_compare_token(value: Any) -> str:
    return _normalize_text(value).upper()


def _extract_pagamento_tokens(value: Any) -> set[str]:
    raw = _normalize_compare_token(value)
    if not raw:
        return set()

    tokens = {raw}
    for sep in ("/", "|", ",", ";", "+"):
        if sep in raw:
            parts = {_normalize_compare_token(part) for part in raw.split(sep)}
            tokens |= {part for part in parts if part}
    return {token for token in tokens if token}


def _find_last_data_row_by_col_d(sheet: Any, min_row: int = 6) -> int:
    last_data_row = 0
    saw_data = False
    empty_streak = 0

    # Emula a ideia do End(xlUp) do VBA: procura a última linha útil da coluna D.
    for row_idx, (id_legado_raw,) in enumerate(
        sheet.iter_rows(min_row=min_row, min_col=4, max_col=4, values_only=True),
        start=min_row,
    ):
        if id_legado_raw not in (None, ""):
            last_data_row = row_idx
            saw_data = True
            empty_streak = 0
            continue

        if saw_data:
            empty_streak += 1
            # Se já vimos dados e em seguida há um bloco grande vazio,
            # interrompe a busca para evitar varrer planilhas enormes vazias.
            if empty_streak >= 5000:
                break

    return last_data_row


def _collect_file_rows_from_payload(filename: str, payload: bytes) -> tuple[list[STG_AuditoriaPlanilha], list[ImportErrorItem]]:
    errors: list[ImportErrorItem] = []
    records: list[STG_AuditoriaPlanilha] = []

    extension = filename.lower().rsplit(".", 1)
    if len(extension) < 2 or f".{extension[-1]}" not in VALID_EXTENSIONS:
        return records, [ImportErrorItem(arquivo=filename, linha=0, motivo="Extensao nao suportada.")]

    try:
        workbook = load_workbook(filename=BytesIO(payload), data_only=True, read_only=True)
    except Exception as exc:
        return records, [ImportErrorItem(arquivo=filename, linha=0, motivo=f"Falha ao abrir arquivo: {exc}")]

    if HOST_VENDA_SHEET_NAME not in workbook.sheetnames:
        workbook.close()
        return records, [ImportErrorItem(arquivo=filename, linha=0, motivo="Aba HostVenda nao encontrada.")]

    sheet = workbook[HOST_VENDA_SHEET_NAME]
    last_row = _find_last_data_row_by_col_d(sheet, min_row=6)

    if last_row < 6:
        workbook.close()
        return records, errors

    for row_offset, row_data in enumerate(
        sheet.iter_rows(min_row=6, max_row=last_row, min_col=4, max_col=25, values_only=True),
        start=6,
    ):
        id_legado_raw = row_data[0]
        if id_legado_raw in (None, ""):
            continue

        data_venda = _to_date(row_data[1])
        hora_venda = _to_time(row_data[3])
        tipo_documento = _normalize_tipo_documento(row_data[4])
        usuario_nome = _normalize_text(row_data[9])
        cliente_nome = _normalize_text(row_data[14])
        tipo_pagamento_descricao = _normalize_text(row_data[18])
        valor_total = _to_decimal(row_data[21])

        try:
            id_legado = int(id_legado_raw)
        except (ValueError, TypeError):
            errors.append(ImportErrorItem(arquivo=filename, linha=row_offset, motivo="ID legado invalido."))
            continue

        if data_venda is None:
            errors.append(ImportErrorItem(arquivo=filename, linha=row_offset, motivo="Data de venda invalida."))
            continue

        if not tipo_documento:
            errors.append(ImportErrorItem(arquivo=filename, linha=row_offset, motivo="Tipo de documento invalido."))
            continue

        if valor_total is None:
            errors.append(ImportErrorItem(arquivo=filename, linha=row_offset, motivo="Valor total invalido."))
            continue

        records.append(
            STG_AuditoriaPlanilha(
                data_venda=data_venda,
                hora_venda=hora_venda,
                tipo_documento=tipo_documento,
                id_legado=id_legado,
                usuario_nome=usuario_nome,
                cliente_nome=cliente_nome,
                valor_total=valor_total,
                tipo_pagamento_descricao=tipo_pagamento_descricao,
            )
        )

    workbook.close()
    return records, errors


def _set_job(job_id: str, **kwargs: Any) -> None:
    with _IMPORT_JOBS_LOCK:
        job = _IMPORT_JOBS.get(job_id)
        if job is None:
            return
        job.update(kwargs)


def get_importacao_job(job_id: str) -> dict[str, Any] | None:
    with _IMPORT_JOBS_LOCK:
        job = _IMPORT_JOBS.get(job_id)
        if job is None:
            return None
        return dict(job)


def _build_divergencia_snapshot(
    *,
    venda: STG_Venda,
    motivos: list[str],
    total_documento: Decimal,
    total_itens: Decimal,
    total_pagamentos: Decimal,
    status_venda: str,
    auditoria_encontrada: bool,
    auditoria_valor: Decimal,
    auditoria_pagamentos: list[str],
    pagamentos_stg: list[str],
) -> dict[str, Any]:
    return {
        "motivos": motivos,
        "status_venda": status_venda,
        "total_documento": str(total_documento),
        "total_itens": str(total_itens),
        "total_pagamentos": str(total_pagamentos),
        "total_auditoria": str(auditoria_valor) if auditoria_encontrada else None,
        "formato_venda": pagamentos_stg,
        "formato_auditoria": auditoria_pagamentos,
    }


def _avaliar_venda(
    *,
    venda: STG_Venda,
    total_itens: Decimal,
    total_pagamentos: Decimal,
    pagamentos_tokens: set[str],
    auditoria_encontrada: bool,
    auditoria_total: Decimal,
    auditoria_pagamentos: set[str],
    sot_keys: set[tuple[str, int]],
) -> tuple[list[str], dict[str, Any]]:
    total_documento = venda.valor_final or Decimal("0")
    motivos: list[str] = []
    status_venda_norm = _normalize_text(venda.status_venda).upper()

    if venda.validacao_override:
        return motivos, {}

    divergencia_totais = (
        abs(total_documento - total_itens) > DECIMAL_TOLERANCE
        or abs(total_documento - total_pagamentos) > DECIMAL_TOLERANCE
        or (not auditoria_encontrada)
        or abs(total_documento - auditoria_total) > DECIMAL_TOLERANCE
        or status_venda_norm == "C"
    )

    if divergencia_totais:
        motivos.append("divergencia_totais")

    if pagamentos_tokens != auditoria_pagamentos:
        motivos.append("divergencia_formato")

    if (venda.tipo_documento, int(venda.id_legado)) in sot_keys:
        motivos.append("duplicado_sot")

    motivos = sorted(set(motivos))
    snapshot = _build_divergencia_snapshot(
        venda=venda,
        motivos=motivos,
        total_documento=total_documento,
        total_itens=total_itens,
        total_pagamentos=total_pagamentos,
        status_venda=venda.status_venda,
        auditoria_encontrada=auditoria_encontrada,
        auditoria_valor=auditoria_total,
        auditoria_pagamentos=sorted(auditoria_pagamentos),
        pagamentos_stg=sorted(pagamentos_tokens),
    )
    return motivos, snapshot


def executar_tripla_validacao(reset_tracking: bool = False) -> ValidationResult:
    if reset_tracking:
        STG_Venda.objects.update(
            validacao_override=False,
            status_tratamento=STG_Venda.TRATAMENTO_PENDENTE,
            snapshot_divergencia={},
            tratamento_atualizado_em=None,
        )

    item_totais = {
        (item["tipo_documento"], int(item["id_venda_legado"])): item["total_itens"] or Decimal("0")
        for item in STG_ItemVenda.objects.filter(cancelado=False)
        .values("tipo_documento", "id_venda_legado")
        .annotate(total_itens=Sum("valor_total_calculado"))
    }

    pagamentos_totais = {
        (item["tipo_documento"], int(item["id_venda_legado"])): item["total_pago"] or Decimal("0")
        for item in STG_PagamentoVenda.objects.values("tipo_documento", "id_venda_legado").annotate(total_pago=Sum("valor_pago"))
    }

    pagamentos_map: dict[tuple[str, int], set[str]] = {}
    for pagamento in STG_PagamentoVenda.objects.values(
        "tipo_documento", "id_venda_legado", "tipo_pagamento_descricao_legado"
    ):
        key = (pagamento["tipo_documento"], int(pagamento["id_venda_legado"]))
        pagamentos_map.setdefault(key, set()).add(
            _normalize_compare_token(pagamento["tipo_pagamento_descricao_legado"])
        )

    auditoria_map: dict[tuple[str, int], dict[str, Any]] = {}
    for row in STG_AuditoriaPlanilha.objects.all():
        key = (row.tipo_documento, int(row.id_legado))
        agg = auditoria_map.setdefault(
            key,
            {
                "encontrada": False,
                "total": Decimal("0"),
                "pagamentos": set(),
                "pagamentos_detalhe": [],
            },
        )
        agg["encontrada"] = True
        total_valor = row.valor_total or Decimal("0")
        agg["total"] += total_valor
        agg["pagamentos"] |= _extract_pagamento_tokens(row.tipo_pagamento_descricao)
        agg["pagamentos_detalhe"].append(
            {
                "tipo_pagamento_descricao": _normalize_text(row.tipo_pagamento_descricao),
                "valor_linha": str(total_valor),
            }
        )

    sot_keys = set(Venda.objects.values_list("tipo_documento", "id_legado"))

    aprovadas = 0
    divergentes = 0
    duplicadas = 0
    detalhes_divergencia: list[dict[str, Any]] = []
    inconsistencias: list[dict[str, Any]] = []

    motivos_count: dict[str, int] = {
        "divergencia_totais": 0,
        "divergencia_formato": 0,
        "duplicado_sot": 0,
    }

    soma_stg_finalizadas = Decimal("0")
    soma_stg_canceladas = Decimal("0")
    soma_auditoria_finalizadas = Decimal("0")
    soma_auditoria_canceladas = Decimal("0")

    vendas = list(STG_Venda.objects.all())
    for venda in vendas:
        key = (venda.tipo_documento, int(venda.id_legado))
        total_itens = item_totais.get(key, Decimal("0"))
        total_pagamentos = pagamentos_totais.get(key, Decimal("0"))
        total_documento = venda.valor_final or Decimal("0")
        status_venda_norm = _normalize_text(venda.status_venda).upper()
        if status_venda_norm == "C":
            soma_stg_canceladas += total_documento
        else:
            soma_stg_finalizadas += total_documento

        auditoria_data = auditoria_map.get(key) or {
            "encontrada": False,
            "total": Decimal("0"),
            "pagamentos": set(),
        }
        pagamentos = pagamentos_map.get(key, set())
        motivos, snapshot = _avaliar_venda(
            venda=venda,
            total_itens=total_itens,
            total_pagamentos=total_pagamentos,
            pagamentos_tokens=pagamentos,
            auditoria_encontrada=bool(auditoria_data["encontrada"]),
            auditoria_total=auditoria_data["total"],
            auditoria_pagamentos=set(auditoria_data["pagamentos"]),
            sot_keys=sot_keys,
        )

        if auditoria_data["encontrada"]:
            if status_venda_norm == "C":
                soma_auditoria_canceladas += auditoria_data["total"]
            else:
                soma_auditoria_finalizadas += auditoria_data["total"]

        if "duplicado_sot" in motivos:
            duplicadas += 1

        if motivos:
            if venda.status_tratamento != STG_Venda.TRATAMENTO_NEGLIGENCIADO:
                divergentes += 1
            venda.status_validacao = STG_Venda.STATUS_DIVERGENTE
            venda.snapshot_divergencia = snapshot
            clean_motivos = sorted(set(motivos))
            for motivo in clean_motivos:
                motivos_count[motivo] += 1

            inconsistencias.append(
                {
                    "tipo_documento": venda.tipo_documento,
                    "id_legado": venda.id_legado,
                    **snapshot,
                    "tratamento": venda.status_tratamento,
                }
            )
            detalhes_divergencia.append(
                {
                    "tipo_documento": venda.tipo_documento,
                    "id_legado": venda.id_legado,
                    "motivos": clean_motivos,
                }
            )
        else:
            aprovadas += 1
            venda.status_validacao = STG_Venda.STATUS_APROVADO
            venda.snapshot_divergencia = {}
            if not venda.validacao_override:
                venda.status_tratamento = STG_Venda.TRATAMENTO_PENDENTE

    if vendas:
        STG_Venda.objects.bulk_update(vendas, ["status_validacao", "status_tratamento", "snapshot_divergencia"], batch_size=2000)

    kpis = {
        "total_vendas_stg": len(vendas),
        "vendas_aprovadas": aprovadas,
        "vendas_divergentes": divergentes,
        "vendas_duplicadas_sot": duplicadas,
        "motivos_divergencia": motivos_count,
        "soma_valor_stg": str(soma_stg_finalizadas),
        "soma_valor_stg_canceladas": str(soma_stg_canceladas),
        "soma_valor_auditoria": str(soma_auditoria_finalizadas),
        "soma_valor_auditoria_canceladas": str(soma_auditoria_canceladas),
        "diferenca_total": str(soma_stg_finalizadas - soma_auditoria_finalizadas),
        "vendas_tratadas": STG_Venda.objects.filter(status_validacao=STG_Venda.STATUS_DIVERGENTE)
        .exclude(status_tratamento=STG_Venda.TRATAMENTO_PENDENTE)
        .count(),
        "vendas_negligenciadas": STG_Venda.objects.filter(status_tratamento=STG_Venda.TRATAMENTO_NEGLIGENCIADO).count(),
    }

    periodo = STG_Venda.objects.aggregate(data_inicial=Min("data_venda"), data_final=Max("data_venda"))
    kpis["periodo_data_inicial"] = periodo["data_inicial"].isoformat() if periodo["data_inicial"] else None
    kpis["periodo_data_final"] = periodo["data_final"].isoformat() if periodo["data_final"] else None

    return ValidationResult(
        vendas_aprovadas=aprovadas,
        vendas_divergentes=divergentes,
        vendas_duplicadas_sot=duplicadas,
        divergencias=detalhes_divergencia[:300],
        inconsistencias=inconsistencias[:500],
        kpis=kpis,
        pode_aprovar=divergentes == 0 and aprovadas > 0,
    )


def obter_kpis_reconciliacao() -> dict[str, Any]:
    validation = executar_tripla_validacao(reset_tracking=False)
    return validation.kpis


def listar_divergencias_reconciliacao(
    *,
    motivo: str | None = None,
    status_tratamento: str | None = None,
    somente_finalizados: bool = False,
    status_venda: str | None = None,
) -> list[dict[str, Any]]:
    motivo_norm = _normalize_text(motivo).lower()
    if motivo_norm and motivo_norm not in MOTIVOS_DIVERGENCIA_VALIDOS:
        motivo_norm = ""

    status_norm = _normalize_text(status_tratamento).upper()
    if status_norm not in {
        "",
        STG_Venda.TRATAMENTO_PENDENTE,
        STG_Venda.TRATAMENTO_AJUSTADO,
        STG_Venda.TRATAMENTO_VALIDADO,
        STG_Venda.TRATAMENTO_NEGLIGENCIADO,
    }:
        status_norm = ""

    status_venda_norm = _normalize_text(status_venda).upper()
    if status_venda_norm not in {"", "F", "C"}:
        status_venda_norm = ""

    divergentes = (
        STG_Venda.objects.filter(status_validacao=STG_Venda.STATUS_DIVERGENTE)
        .prefetch_related("itens", "pagamentos")
        .order_by("tipo_documento", "id_legado")
    )

    auditoria_rows = STG_AuditoriaPlanilha.objects.values(
        "tipo_documento",
        "id_legado",
        "tipo_pagamento_descricao",
        "valor_total",
    )
    auditoria_details_map: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in auditoria_rows:
        key = (row["tipo_documento"], int(row["id_legado"]))
        auditoria_details_map.setdefault(key, []).append(
            {
                "tipo_pagamento_descricao": _normalize_text(row["tipo_pagamento_descricao"]),
                "valor_linha": str(row["valor_total"] or Decimal("0")),
            }
        )

    rows: list[dict[str, Any]] = []
    for venda in divergentes:
        if status_norm and venda.status_tratamento != status_norm:
            continue

        if somente_finalizados and _normalize_text(venda.status_venda).upper() != "F":
            continue

        if status_venda_norm and _normalize_text(venda.status_venda).upper() != status_venda_norm:
            continue

        snapshot = venda.snapshot_divergencia or {}
        motivos = snapshot.get("motivos") or []
        if motivo_norm and motivo_norm not in motivos:
            continue

        rows.append(
            {
                "tipo_documento": venda.tipo_documento,
                "id_legado": venda.id_legado,
                "data_venda": venda.data_venda.isoformat() if venda.data_venda else None,
                "venda": f"{venda.tipo_documento} #{int(venda.id_legado):06d}",
                "motivos": motivos,
                "tratamento": venda.status_tratamento,
                "status_venda": venda.status_venda,
                "nome_cliente_legado": venda.nome_cliente_legado,
                "stg": {
                    "valor_documento": snapshot.get("total_documento"),
                    "total_itens": snapshot.get("total_itens"),
                    "total_pagamentos": snapshot.get("total_pagamentos"),
                    "pagamentos": snapshot.get("formato_venda") or [],
                    "itens": [
                        {
                            "id_stg_item_venda": item.id_stg_item_venda,
                            "status_venda": item.status_venda,
                            "id_produto_legado": item.id_produto_legado,
                            "nome_produto_legado": item.nome_produto_legado,
                            "quantidade": str(item.quantidade or Decimal("0")),
                            "valor_unitario": str(item.valor_unitario or Decimal("0")),
                            "valor_total_calculado": str(item.valor_total_calculado or Decimal("0")),
                            "cancelado": item.cancelado,
                        }
                        for item in venda.itens.all()
                    ],
                    "pagamentos_detalhe": [
                        {
                            "id_stg_pagamento_venda": pg.id_stg_pagamento_venda,
                            "id_tipo_pagamento_legado": pg.id_tipo_pagamento_legado,
                            "tipo_pagamento_descricao_legado": pg.tipo_pagamento_descricao_legado,
                            "valor_pago": str(pg.valor_pago or Decimal("0")),
                        }
                        for pg in venda.pagamentos.all()
                    ],
                },
                "auditoria": {
                    "valor_total": snapshot.get("total_auditoria"),
                    "pagamentos": snapshot.get("formato_auditoria") or [],
                    "pagamentos_detalhe": auditoria_details_map.get((venda.tipo_documento, int(venda.id_legado)), []),
                },
                "totais": {
                    "total_documento": snapshot.get("total_documento"),
                    "total_itens": snapshot.get("total_itens"),
                    "total_pagamentos": snapshot.get("total_pagamentos"),
                    "total_auditoria": snapshot.get("total_auditoria"),
                },
                "atualizado_em": venda.tratamento_atualizado_em.isoformat() if venda.tratamento_atualizado_em else None,
            }
        )

    return rows


def aplicar_tratamento_divergencia(
    *,
    tipo_documento: str,
    id_legado: int,
    acao: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    venda = STG_Venda.objects.filter(tipo_documento=tipo_documento, id_legado=id_legado).first()
    if venda is None:
        raise ValueError("Venda STG nao encontrada para tratamento.")

    acao_norm = _normalize_text(acao).lower()
    if acao_norm not in {"validar", "ajustar", "negligenciar"}:
        raise ValueError("Acao invalida. Use 'validar', 'ajustar' ou 'negligenciar'.")

    with transaction.atomic():
        if acao_norm == "validar":
            venda.validacao_override = True
            venda.status_validacao = STG_Venda.STATUS_APROVADO
            venda.status_tratamento = STG_Venda.TRATAMENTO_VALIDADO
            venda.snapshot_divergencia = {}
            venda.tratamento_atualizado_em = timezone.now()
            venda.save(
                update_fields=[
                    "validacao_override",
                    "status_validacao",
                    "status_tratamento",
                    "snapshot_divergencia",
                    "tratamento_atualizado_em",
                ]
            )
        elif acao_norm == "negligenciar":
            venda.validacao_override = False
            venda.status_validacao = STG_Venda.STATUS_DIVERGENTE
            venda.status_tratamento = STG_Venda.TRATAMENTO_NEGLIGENCIADO
            venda.tratamento_atualizado_em = timezone.now()
            venda.save(
                update_fields=[
                    "validacao_override",
                    "status_validacao",
                    "status_tratamento",
                    "tratamento_atualizado_em",
                ]
            )
        else:
            venda.validacao_override = False
            update_fields_venda = ["validacao_override", "tratamento_atualizado_em"]

            valor_final_raw = payload.get("valor_final")
            if valor_final_raw not in (None, ""):
                valor_final = _to_decimal(valor_final_raw)
                if valor_final is None:
                    raise ValueError("valor_final invalido.")
                venda.valor_final = valor_final
                update_fields_venda.append("valor_final")

            status_venda_raw = _normalize_text(payload.get("status_venda")).upper()
            if status_venda_raw:
                if status_venda_raw not in {"F", "C"}:
                    raise ValueError("status_venda invalido. Use 'F' ou 'C'.")
                venda.status_venda = status_venda_raw
                update_fields_venda.append("status_venda")
                STG_ItemVenda.objects.filter(stg_venda=venda).update(status_venda=status_venda_raw)

            for item_data in payload.get("itens") or []:
                item_id = item_data.get("id_stg_item_venda")
                item = STG_ItemVenda.objects.filter(id_stg_item_venda=item_id, stg_venda=venda).first()
                if item is None:
                    continue

                for field_name in ("quantidade", "valor_unitario", "valor_total_calculado"):
                    if field_name in item_data:
                        value = _to_decimal(item_data.get(field_name))
                        setattr(item, field_name, value)

                if "cancelado" in item_data:
                    item.cancelado = bool(item_data.get("cancelado"))

                item.save(update_fields=["quantidade", "valor_unitario", "valor_total_calculado", "cancelado"])

            for pg_data in payload.get("pagamentos") or []:
                pg_id = pg_data.get("id_stg_pagamento_venda")
                pagamento = STG_PagamentoVenda.objects.filter(id_stg_pagamento_venda=pg_id, stg_venda=venda).first()
                if pagamento is None:
                    continue

                if "valor_pago" in pg_data:
                    valor_pago = _to_decimal(pg_data.get("valor_pago"))
                    if valor_pago is not None:
                        pagamento.valor_pago = valor_pago

                if "id_tipo_pagamento_legado" in pg_data:
                    pagamento.id_tipo_pagamento_legado = pg_data.get("id_tipo_pagamento_legado")

                if "tipo_pagamento_descricao_legado" in pg_data:
                    pagamento.tipo_pagamento_descricao_legado = _normalize_text(pg_data.get("tipo_pagamento_descricao_legado"))

                pagamento.save(
                    update_fields=["valor_pago", "id_tipo_pagamento_legado", "tipo_pagamento_descricao_legado"]
                )

            venda.tratamento_atualizado_em = timezone.now()
            venda.save(update_fields=update_fields_venda)

    validation = executar_tripla_validacao(reset_tracking=False)
    return {
        "detail": "Tratamento aplicado com sucesso.",
        "kpis": validation.kpis,
    }


def aplicar_tratamento_divergencias_lote(
    *,
    vendas: list[dict[str, Any]],
    acao: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    acao_norm = _normalize_text(acao).lower()
    if acao_norm not in {"validar", "negligenciar", "editar_pagamento"}:
        raise ValueError("Acao em lote invalida. Use 'validar', 'negligenciar' ou 'editar_pagamento'.")

    payload = payload or {}
    id_forma_destino: int | None = None
    descricao_destino = ""
    if acao_norm == "editar_pagamento":
        id_forma_raw = payload.get("id_forma")
        if id_forma_raw in (None, ""):
            raise ValueError("Para editar em lote, informe id_forma no payload.")
        try:
            id_forma_destino = int(id_forma_raw)
        except (TypeError, ValueError):
            raise ValueError("id_forma invalido para edicao em lote.")

        forma = FormaPagamento.objects.filter(id_forma=id_forma_destino).first()
        if forma is None:
            raise ValueError("Forma de pagamento destino nao encontrada.")
        descricao_destino = _normalize_text(forma.descricao)

    processadas = 0
    ignoradas = 0
    with transaction.atomic():
        for venda_data in vendas:
            tipo_documento = _normalize_text(venda_data.get("tipo_documento")).upper()
            id_legado_raw = venda_data.get("id_legado")
            try:
                id_legado = int(id_legado_raw)
            except (TypeError, ValueError):
                ignoradas += 1
                continue

            venda = STG_Venda.objects.filter(tipo_documento=tipo_documento, id_legado=id_legado).first()
            if venda is None:
                ignoradas += 1
                continue

            if acao_norm == "validar":
                venda.validacao_override = True
                venda.status_validacao = STG_Venda.STATUS_APROVADO
                venda.status_tratamento = STG_Venda.TRATAMENTO_VALIDADO
                venda.snapshot_divergencia = {}
                venda.tratamento_atualizado_em = timezone.now()
                venda.save(
                    update_fields=[
                        "validacao_override",
                        "status_validacao",
                        "status_tratamento",
                        "snapshot_divergencia",
                        "tratamento_atualizado_em",
                    ]
                )
            elif acao_norm == "negligenciar":
                venda.validacao_override = False
                venda.status_validacao = STG_Venda.STATUS_DIVERGENTE
                venda.status_tratamento = STG_Venda.TRATAMENTO_NEGLIGENCIADO
                venda.tratamento_atualizado_em = timezone.now()
                venda.save(
                    update_fields=[
                        "validacao_override",
                        "status_validacao",
                        "status_tratamento",
                        "tratamento_atualizado_em",
                    ]
                )
            else:
                STG_PagamentoVenda.objects.filter(stg_venda=venda).update(
                    id_tipo_pagamento_legado=id_forma_destino,
                    tipo_pagamento_descricao_legado=descricao_destino,
                )

            processadas += 1

    validation = executar_tripla_validacao(reset_tracking=False)
    return {
        "detail": "Tratamento em lote concluido.",
        "processadas": processadas,
        "ignoradas": ignoradas,
        "kpis": validation.kpis,
    }


def listar_formas_pagamento() -> list[dict[str, Any]]:
    formas = FormaPagamento.objects.order_by("descricao", "id_forma")
    return [{"id_forma": int(item.id_forma), "descricao": item.descricao} for item in formas]


def _importar_planilhas_auditoria_sync(payloads: list[dict[str, Any]], job_id: str | None = None) -> dict[str, Any]:
    started_at = perf_counter()
    imported_records: list[STG_AuditoriaPlanilha] = []
    import_errors: list[ImportErrorItem] = []

    total_files = len(payloads)
    parse_started_at = perf_counter()
    parse_workers = max(1, min(total_files, cpu_count() or 4, 8))

    with ThreadPoolExecutor(max_workers=parse_workers) as executor:
        future_to_file: dict[Any, str] = {}
        for file_info in payloads:
            filename = _normalize_text(file_info.get("name") or "arquivo_sem_nome")
            content = file_info.get("content") or b""
            future = executor.submit(_collect_file_rows_from_payload, filename, content)
            future_to_file[future] = filename

        processed = 0
        for future in as_completed(future_to_file):
            filename = future_to_file[future]
            try:
                records, errors = future.result()
            except Exception as exc:
                records = []
                errors = [
                    ImportErrorItem(
                        arquivo=filename,
                        linha=0,
                        motivo=f"Falha no parser paralelo: {exc}",
                    )
                ]

            imported_records.extend(records)
            import_errors.extend(errors)
            processed += 1

            if job_id:
                _set_job(
                    job_id,
                    stage="importando_arquivos",
                    detail=f"Processando {processed}/{total_files}: {filename}",
                    arquivos_processados=processed,
                    total_arquivos=total_files,
                    linhas_parciais=len(imported_records),
                )

    parse_elapsed_s = perf_counter() - parse_started_at

    db_started_at = perf_counter()
    with transaction.atomic():
        STG_AuditoriaPlanilha.objects.all().delete()

        if imported_records:
            STG_AuditoriaPlanilha.objects.bulk_create(imported_records, batch_size=3000)

        if job_id:
            _set_job(
                job_id,
                stage="validando",
                detail="Executando tripla validacao entre STG e auditoria.",
            )

        validation = executar_tripla_validacao(reset_tracking=True)

    db_and_validation_elapsed_s = perf_counter() - db_started_at
    total_elapsed_s = perf_counter() - started_at

    return {
        "arquivos_recebidos": total_files,
        "linhas_importadas": len(imported_records),
        "performance": {
            "parse_workers": parse_workers,
            "parse_segundos": round(parse_elapsed_s, 3),
            "persistencia_validacao_segundos": round(db_and_validation_elapsed_s, 3),
            "total_segundos": round(total_elapsed_s, 3),
        },
        "erros_importacao": [
            {"arquivo": err.arquivo, "linha": err.linha, "motivo": err.motivo}
            for err in import_errors[:500]
        ],
        "validacao": {
            "vendas_aprovadas": validation.vendas_aprovadas,
            "vendas_divergentes": validation.vendas_divergentes,
            "vendas_duplicadas_sot": validation.vendas_duplicadas_sot,
            "divergencias": validation.divergencias,
            "inconsistencias": validation.inconsistencias,
            "kpis": validation.kpis,
            "pode_aprovar": validation.pode_aprovar,
        },
    }


def _process_import_job(job_id: str, payloads: list[dict[str, Any]]) -> None:
    try:
        _set_job(job_id, status="processing", stage="iniciando", detail="Iniciando importacao de planilhas.")
        resultado = _importar_planilhas_auditoria_sync(payloads, job_id=job_id)
        _set_job(
            job_id,
            status="completed",
            stage="concluido",
            detail="Importacao e validacao concluidas.",
            resultado=resultado,
        )
    except Exception as exc:
        _set_job(
            job_id,
            status="failed",
            stage="erro",
            detail=f"Falha no processamento: {exc}",
            erro=str(exc),
        )


def start_importacao_planilhas_auditoria(uploads: list[UploadedFile]) -> str:
    if not uploads:
        raise ValueError("Nenhum arquivo foi enviado para importacao.")

    payloads: list[dict[str, Any]] = []
    for upload in uploads:
        payloads.append(
            {
                "name": _normalize_text(getattr(upload, "name", "arquivo_sem_nome")),
                "content": upload.read(),
            }
        )

    job_id = uuid4().hex
    with _IMPORT_JOBS_LOCK:
        _IMPORT_JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "stage": "fila",
            "detail": "Aguardando processamento.",
            "arquivos_processados": 0,
            "total_arquivos": len(payloads),
            "linhas_parciais": 0,
            "resultado": None,
            "erro": None,
        }

    worker = Thread(target=_process_import_job, args=(job_id, payloads), daemon=True)
    worker.start()
    return job_id


def consolidar_stg_para_sot() -> dict[str, Any]:
    if STG_Venda.objects.filter(status_validacao=STG_Venda.STATUS_DIVERGENTE).exclude(
        status_tratamento=STG_Venda.TRATAMENTO_NEGLIGENCIADO
    ).exists():
        raise ValueError("Existem vendas divergentes na STG. Corrija antes da consolidacao.")

    aprovadas = list(
        STG_Venda.objects.filter(status_validacao=STG_Venda.STATUS_APROVADO).exclude(
            status_tratamento=STG_Venda.TRATAMENTO_NEGLIGENCIADO
        )
        .prefetch_related("itens", "pagamentos")
        .order_by("tipo_documento", "id_legado")
    )

    if not aprovadas:
        raise ValueError("Nao ha vendas aprovadas na STG para consolidar.")

    existentes = set(Venda.objects.values_list("tipo_documento", "id_legado"))

    inseridas = 0
    ignoradas_duplicadas = 0
    ignoradas_incompletas = 0
    detalhes_ignorados: list[dict[str, Any]] = []

    for stg_venda in aprovadas:
        key = (stg_venda.tipo_documento, int(stg_venda.id_legado))
        if key in existentes:
            ignoradas_duplicadas += 1
            continue

        if stg_venda.id_usuario_legado is None:
            ignoradas_incompletas += 1
            detalhes_ignorados.append(
                {
                    "tipo_documento": stg_venda.tipo_documento,
                    "id_legado": stg_venda.id_legado,
                    "motivo": "usuario_legado_ausente",
                }
            )
            continue

        itens = list(stg_venda.itens.all())
        pagamentos = list(stg_venda.pagamentos.all())

        if not itens or not pagamentos:
            ignoradas_incompletas += 1
            detalhes_ignorados.append(
                {
                    "tipo_documento": stg_venda.tipo_documento,
                    "id_legado": stg_venda.id_legado,
                    "motivo": "venda_sem_itens_ou_pagamentos",
                }
            )
            continue

        produto_ids = [item.id_produto_legado for item in itens if item.id_produto_legado is not None]
        produto_map = {
            p.id_produto: p
            for p in Produto.objects.filter(id_produto__in=produto_ids)
        }

        if len(produto_map) != len(set(produto_ids)):
            ignoradas_incompletas += 1
            detalhes_ignorados.append(
                {
                    "tipo_documento": stg_venda.tipo_documento,
                    "id_legado": stg_venda.id_legado,
                    "motivo": "produto_nao_encontrado",
                }
            )
            continue

        pagamentos_convertidos: list[tuple[FormaPagamento, STG_PagamentoVenda]] = []
        pagamento_invalido = False
        for pg in pagamentos:
            if pg.id_tipo_pagamento_legado is None:
                pagamento_invalido = True
                break
            forma, _ = FormaPagamento.objects.get_or_create(
                id_forma=pg.id_tipo_pagamento_legado,
                defaults={"descricao": pg.tipo_pagamento_descricao_legado or f"Forma {pg.id_tipo_pagamento_legado}"},
            )
            pagamentos_convertidos.append((forma, pg))

        if pagamento_invalido:
            ignoradas_incompletas += 1
            detalhes_ignorados.append(
                {
                    "tipo_documento": stg_venda.tipo_documento,
                    "id_legado": stg_venda.id_legado,
                    "motivo": "pagamento_sem_id_forma",
                }
            )
            continue

        usuario, _ = Usuario.objects.get_or_create(
            id_usuario=stg_venda.id_usuario_legado,
            defaults={"nome": stg_venda.nome_usuario_legado or f"Usuario {stg_venda.id_usuario_legado}"},
        )

        cliente = None
        if stg_venda.id_cliente_legado is not None:
            cliente = Cliente.objects.filter(id_cliente=stg_venda.id_cliente_legado).first()

        with transaction.atomic():
            venda = Venda.objects.create(
                id_legado=stg_venda.id_legado,
                tipo_documento=stg_venda.tipo_documento,
                data_venda=stg_venda.data_venda,
                hora_venda=stg_venda.hora_venda,
                cliente=cliente,
                usuario=usuario,
                valor_total_documento=stg_venda.valor_final or Decimal("0"),
            )

            ItemVenda.objects.bulk_create(
                [
                    ItemVenda(
                        venda=venda,
                        produto=produto_map[item.id_produto_legado],
                        quantidade=item.quantidade or Decimal("0"),
                        valor_unitario=item.valor_unitario or Decimal("0"),
                        valor_total_item=item.valor_total_calculado or Decimal("0"),
                        cancelado=item.cancelado,
                    )
                    for item in itens
                ],
                batch_size=2000,
            )

            PagamentoVenda.objects.bulk_create(
                [
                    PagamentoVenda(
                        venda=venda,
                        forma_pagamento=forma,
                        valor_pago=pg.valor_pago or Decimal("0"),
                    )
                    for forma, pg in pagamentos_convertidos
                ],
                batch_size=2000,
            )

        inseridas += 1

    return {
        "vendas_inseridas": inseridas,
        "vendas_ignoradas_duplicadas": ignoradas_duplicadas,
        "vendas_ignoradas_incompletas": ignoradas_incompletas,
        "detalhes_ignorados": detalhes_ignorados[:300],
    }
