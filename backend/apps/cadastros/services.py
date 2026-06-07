from __future__ import annotations

from io import BytesIO
import re

import pandas as pd
from django.db.models import QuerySet
from django.core.exceptions import PermissionDenied
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle


EXPORT_CONTENT_TYPES = {
    "csv": "text/csv; charset=utf-8",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}

FORBIDDEN_SQL_TOKENS = ("DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE")


def _queryset_to_dataframe(queryset: QuerySet, selected_columns: list[str]) -> pd.DataFrame:
    rows = list(queryset.values(*selected_columns).iterator(chunk_size=5000))
    return pd.DataFrame(rows, columns=selected_columns)


def _render_csv(dataframe: pd.DataFrame) -> bytes:
    text = dataframe.to_csv(index=False)
    return text.encode("utf-8-sig")


def _render_xlsx(dataframe: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="Exportacao")
    buffer.seek(0)
    return buffer.read()


def _render_pdf(dataframe: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=20,
        rightMargin=20,
        topMargin=20,
        bottomMargin=20,
    )

    styles = getSampleStyleSheet()
    header = [Paragraph(str(column), styles["Heading5"]) for column in dataframe.columns]
    rows = [[str(value) if value is not None else "" for value in row] for row in dataframe.itertuples(index=False, name=None)]
    table_data = [header, *rows] if rows else [header]

    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ececec")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0d0d0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    document.build([table])
    buffer.seek(0)
    return buffer.read()


def export_queryset_data(queryset: QuerySet, selected_columns: list[str], export_format: str) -> bytes:
    dataframe = _queryset_to_dataframe(queryset, selected_columns)
    return export_dataframe(dataframe, export_format)


def export_dataframe(dataframe: pd.DataFrame, export_format: str) -> bytes:
    if export_format == "csv":
        return _render_csv(dataframe)
    if export_format == "xlsx":
        return _render_xlsx(dataframe)
    if export_format == "pdf":
        return _render_pdf(dataframe)
    raise ValueError("Formato de exportacao invalido.")


def validate_safe_select_sql(query_sql: str) -> str:
    normalized = str(query_sql or "").strip()
    query_upper = normalized.upper()
    if not query_upper.startswith("SELECT"):
        raise PermissionDenied("Apenas consultas SELECT sao permitidas.")
    if any(re.search(rf"\b{token}\b", query_upper) for token in FORBIDDEN_SQL_TOKENS):
        raise PermissionDenied("Consulta bloqueada por regra de seguranca.")
    return normalized
