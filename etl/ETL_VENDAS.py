import argparse
import os
from datetime import datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

TIPOS_DOCUMENTO_VALIDOS = {"NFCE", "DAV"}

COLUNAS_VENDAS = [
    "id_legado",
    "tipo_documento",
    "data_venda",
    "hora_venda",
    "status",
    "id_cliente",
    "id_usuario",
    "valor_total_documento",
]

COLUNAS_ITENS = [
    "id_legado_venda",
    "tipo_documento",
    "id_produto",
    "id_und_medida",
    "quantidade",
    "valor_unitario",
    "valor_total_item",
    "cancelado",
]

COLUNAS_PAGAMENTOS = [
    "id_legado_venda",
    "tipo_documento",
    "id_forma",
    "valor_pago",
    "estorno",
]


def carregar_ambiente() -> dict:
    from dotenv import load_dotenv

    base_dir = Path(__file__).resolve().parent
    candidatos_env = [
        base_dir / ".env",
        base_dir.parent / "backend" / ".env",
        base_dir.parent / ".env",
    ]

    for caminho in candidatos_env:
        if caminho.exists():
            load_dotenv(caminho, override=True)

    cfg = {
        "host": os.getenv("DB_HOST"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
        "port": os.getenv("DB_PORT"),
    }

    faltando = [chave for chave, valor in cfg.items() if valor in (None, "")]
    if faltando:
        raise ValueError(
            "Variaveis de ambiente ausentes para conexao com banco: "
            + ", ".join(sorted(faltando))
        )

    cfg["port"] = int(cfg["port"])
    return cfg


def normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).strip().lower() for col in df.columns]
    return df


def validar_colunas(df: pd.DataFrame, colunas_esperadas: list[str], nome_sheet: str) -> None:
    faltando = [col for col in colunas_esperadas if col not in df.columns]
    if faltando:
        raise ValueError(
            f"Sheet '{nome_sheet}' sem colunas obrigatorias: {', '.join(faltando)}"
        )


def valor_vazio(valor) -> bool:
    if valor is None:
        return True
    if isinstance(valor, str) and valor.strip() == "":
        return True
    return bool(pd.isna(valor))


def to_int(valor, campo: str, permite_nulo: bool = False) -> int | None:
    if valor_vazio(valor):
        if permite_nulo:
            return None
        raise ValueError(f"Campo obrigatorio ausente: {campo}")
    try:
        return int(str(valor).strip())
    except (ValueError, TypeError):
        raise ValueError(f"Campo {campo} invalido para inteiro: {valor}")


def to_decimal(valor, campo: str, permite_nulo: bool = False) -> Decimal | None:
    if valor_vazio(valor):
        if permite_nulo:
            return None
        raise ValueError(f"Campo obrigatorio ausente: {campo}")
    try:
        return Decimal(str(valor).strip().replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"Campo {campo} invalido para decimal: {valor}")


def to_date(valor, campo: str):
    if valor_vazio(valor):
        raise ValueError(f"Campo obrigatorio ausente: {campo}")

    if isinstance(valor, datetime):
        return valor.date()

    parsed = pd.to_datetime(valor, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"Campo {campo} invalido para data (YYYY-MM-DD): {valor}")
    return parsed.date()


def to_time(valor, campo: str, permite_nulo: bool = True):
    if valor_vazio(valor):
        return None if permite_nulo else ValueError(f"Campo obrigatorio ausente: {campo}")

    if isinstance(valor, time):
        return valor
    if isinstance(valor, datetime):
        return valor.time()

    texto = str(valor).strip()
    for formato in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(texto, formato).time()
        except ValueError:
            continue
    raise ValueError(f"Campo {campo} invalido para hora (HH:MM ou HH:MM:SS): {valor}")


def to_bool(valor, campo: str, permite_nulo: bool = True) -> bool:
    if valor_vazio(valor):
        return False if permite_nulo else ValueError(f"Campo obrigatorio ausente: {campo}")

    if isinstance(valor, bool):
        return valor

    texto = str(valor).strip().upper()
    if texto in {"1", "S", "SIM", "Y", "YES", "TRUE", "T"}:
        return True
    if texto in {"0", "N", "NAO", "NÃO", "NO", "FALSE", "F"}:
        return False
    raise ValueError(f"Campo {campo} invalido para booleano: {valor}")


def to_str(valor) -> str:
    if valor_vazio(valor):
        return ""
    return str(valor).strip()


def placeholders(qtd: int) -> str:
    return ",".join(["%s"] * qtd)


def obter_ids_existentes(cursor, tabela: str, coluna: str, ids: set[int]) -> set[int]:
    if not ids:
        return set()
    sql = f"SELECT {coluna} FROM {tabela} WHERE {coluna} IN ({placeholders(len(ids))})"
    cursor.execute(sql, tuple(ids))
    return {int(row[0]) for row in cursor.fetchall()}


def validar_fk(cursor, ids: set[int], tabela: str, coluna: str, nome: str) -> None:
    if not ids:
        return
    existentes = obter_ids_existentes(cursor, tabela, coluna, ids)
    faltantes = sorted(ids - existentes)
    if faltantes:
        amostra = ", ".join(str(x) for x in faltantes[:20])
        raise ValueError(f"{nome} inexistente(s) na tabela {tabela}: {amostra}")


def build_template(caminho_saida: Path) -> None:
    df_vendas = pd.DataFrame(
        [
            {
                "id_legado": 10001,
                "tipo_documento": "NFCE",
                "data_venda": "2026-06-10",
                "hora_venda": "10:34:00",
                "status": "F",
                "id_cliente": 1,
                "id_usuario": 1,
                "valor_total_documento": 199.90,
            },
            {
                "id_legado": 20001,
                "tipo_documento": "DAV",
                "data_venda": "2026-06-10",
                "hora_venda": "16:15:00",
                "status": "F",
                "id_cliente": "",
                "id_usuario": 1,
                "valor_total_documento": 89.50,
            },
        ]
    )

    df_itens = pd.DataFrame(
        [
            {
                "id_legado_venda": 10001,
                "tipo_documento": "NFCE",
                "id_produto": 1,
                "id_und_medida": 1,
                "quantidade": 2,
                "valor_unitario": 50.00,
                "valor_total_item": 100.00,
                "cancelado": 0,
            },
            {
                "id_legado_venda": 10001,
                "tipo_documento": "NFCE",
                "id_produto": 2,
                "id_und_medida": 1,
                "quantidade": 1,
                "valor_unitario": 99.90,
                "valor_total_item": 99.90,
                "cancelado": 0,
            },
            {
                "id_legado_venda": 20001,
                "tipo_documento": "DAV",
                "id_produto": 3,
                "id_und_medida": "",
                "quantidade": 1,
                "valor_unitario": 89.50,
                "valor_total_item": 89.50,
                "cancelado": 0,
            },
        ]
    )

    df_pagamentos = pd.DataFrame(
        [
            {
                "id_legado_venda": 10001,
                "tipo_documento": "NFCE",
                "id_forma": 1,
                "valor_pago": 199.90,
                "estorno": 0,
            },
            {
                "id_legado_venda": 20001,
                "tipo_documento": "DAV",
                "id_forma": 2,
                "valor_pago": 89.50,
                "estorno": 0,
            },
        ]
    )

    with pd.ExcelWriter(caminho_saida, engine="openpyxl") as writer:
        df_vendas.to_excel(writer, sheet_name="vendas", index=False)
        df_itens.to_excel(writer, sheet_name="itens_venda", index=False)
        df_pagamentos.to_excel(writer, sheet_name="pagamentos_venda", index=False)

    print(f"Modelo de vendas gerado em: {caminho_saida}")


def carregar_planilha(caminho_arquivo: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not caminho_arquivo.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {caminho_arquivo}")

    df_vendas = normalizar_colunas(pd.read_excel(caminho_arquivo, sheet_name="vendas", dtype=object))
    df_itens = normalizar_colunas(pd.read_excel(caminho_arquivo, sheet_name="itens_venda", dtype=object))
    df_pag = normalizar_colunas(pd.read_excel(caminho_arquivo, sheet_name="pagamentos_venda", dtype=object))

    validar_colunas(df_vendas, COLUNAS_VENDAS, "vendas")
    validar_colunas(df_itens, COLUNAS_ITENS, "itens_venda")
    validar_colunas(df_pag, COLUNAS_PAGAMENTOS, "pagamentos_venda")

    return df_vendas, df_itens, df_pag


def importar_vendas(caminho_arquivo: Path) -> None:
    import pymysql

    cfg = carregar_ambiente()
    df_vendas, df_itens, df_pag = carregar_planilha(caminho_arquivo)

    conn = pymysql.connect(
        host=cfg["host"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        port=cfg["port"],
        autocommit=False,
    )

    try:
        with conn.cursor() as cursor:
            vendas_registros = []
            chaves_venda = set()
            ids_cliente = set()
            ids_usuario = set()

            for _, row in df_vendas.iterrows():
                id_legado = to_int(row["id_legado"], "vendas.id_legado")
                tipo_documento = to_str(row["tipo_documento"]).upper()
                if tipo_documento not in TIPOS_DOCUMENTO_VALIDOS:
                    raise ValueError(
                        f"tipo_documento invalido em vendas ({id_legado}): {tipo_documento}"
                    )

                chave = (id_legado, tipo_documento)
                if chave in chaves_venda:
                    raise ValueError(f"Venda duplicada no arquivo: {chave}")
                chaves_venda.add(chave)

                id_cliente = to_int(row["id_cliente"], "vendas.id_cliente", permite_nulo=True)
                id_usuario = to_int(row["id_usuario"], "vendas.id_usuario")

                if id_cliente is not None:
                    ids_cliente.add(id_cliente)
                ids_usuario.add(id_usuario)

                vendas_registros.append(
                    (
                        id_legado,
                        tipo_documento,
                        to_date(row["data_venda"], "vendas.data_venda"),
                        to_time(row["hora_venda"], "vendas.hora_venda", permite_nulo=True),
                        to_str(row["status"]),
                        id_cliente,
                        id_usuario,
                        to_decimal(row["valor_total_documento"], "vendas.valor_total_documento"),
                    )
                )

            validar_fk(cursor, ids_cliente, "clientes", "id_cliente", "Cliente")
            validar_fk(cursor, ids_usuario, "usuario", "id_usuario", "Usuario")

            sql_upsert_venda = """
                INSERT INTO venda (
                    id_legado, tipo_documento, data_venda, hora_venda,
                    status, id_cliente, id_usuario, valor_total_documento, momento_consolidacao
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL)
                ON DUPLICATE KEY UPDATE
                    data_venda = VALUES(data_venda),
                    hora_venda = VALUES(hora_venda),
                    status = VALUES(status),
                    id_cliente = VALUES(id_cliente),
                    id_usuario = VALUES(id_usuario),
                    valor_total_documento = VALUES(valor_total_documento)
            """
            cursor.executemany(sql_upsert_venda, vendas_registros)

            ids_legado = sorted({item[0] for item in vendas_registros})
            cursor.execute(
                f"SELECT id_venda, id_legado, tipo_documento FROM venda WHERE id_legado IN ({placeholders(len(ids_legado))})",
                tuple(ids_legado),
            )
            mapa_venda = {(int(r[1]), str(r[2]).upper()): int(r[0]) for r in cursor.fetchall()}

            ids_venda_afetadas = [
                mapa_venda[(item[0], item[1])] for item in vendas_registros if (item[0], item[1]) in mapa_venda
            ]
            if ids_venda_afetadas:
                cursor.execute(
                    f"DELETE FROM item_venda WHERE id_venda IN ({placeholders(len(ids_venda_afetadas))})",
                    tuple(ids_venda_afetadas),
                )
                cursor.execute(
                    f"DELETE FROM pagamento_venda WHERE id_venda IN ({placeholders(len(ids_venda_afetadas))})",
                    tuple(ids_venda_afetadas),
                )

            itens_registros = []
            ids_produto = set()
            ids_unidade = set()

            for _, row in df_itens.iterrows():
                id_legado_venda = to_int(row["id_legado_venda"], "itens_venda.id_legado_venda")
                tipo_documento = to_str(row["tipo_documento"]).upper()
                chave_venda = (id_legado_venda, tipo_documento)
                id_venda = mapa_venda.get(chave_venda)
                if id_venda is None:
                    raise ValueError(f"Venda nao encontrada para item: {chave_venda}")

                id_produto = to_int(row["id_produto"], "itens_venda.id_produto")
                id_unidade = to_int(
                    row["id_und_medida"], "itens_venda.id_und_medida", permite_nulo=True
                )

                ids_produto.add(id_produto)
                if id_unidade is not None:
                    ids_unidade.add(id_unidade)

                itens_registros.append(
                    (
                        id_venda,
                        id_produto,
                        id_unidade,
                        to_decimal(row["quantidade"], "itens_venda.quantidade"),
                        to_decimal(row["valor_unitario"], "itens_venda.valor_unitario"),
                        to_decimal(row["valor_total_item"], "itens_venda.valor_total_item"),
                        to_bool(row["cancelado"], "itens_venda.cancelado"),
                    )
                )

            validar_fk(cursor, ids_produto, "produtos", "id_produto", "Produto")
            validar_fk(cursor, ids_unidade, "unidade_medida", "id_und_medida", "UnidadeMedida")

            sql_item = """
                INSERT INTO item_venda (
                    id_venda, id_produto, id_und_medida,
                    quantidade, valor_unitario, valor_total_item, cancelado
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            if itens_registros:
                cursor.executemany(sql_item, itens_registros)

            pagamentos_registros = []
            ids_forma = set()

            for _, row in df_pag.iterrows():
                id_legado_venda = to_int(row["id_legado_venda"], "pagamentos_venda.id_legado_venda")
                tipo_documento = to_str(row["tipo_documento"]).upper()
                chave_venda = (id_legado_venda, tipo_documento)
                id_venda = mapa_venda.get(chave_venda)
                if id_venda is None:
                    raise ValueError(f"Venda nao encontrada para pagamento: {chave_venda}")

                id_forma = to_int(row["id_forma"], "pagamentos_venda.id_forma")
                ids_forma.add(id_forma)

                pagamentos_registros.append(
                    (
                        id_venda,
                        id_forma,
                        to_decimal(row["valor_pago"], "pagamentos_venda.valor_pago"),
                        to_bool(row["estorno"], "pagamentos_venda.estorno"),
                    )
                )

            validar_fk(cursor, ids_forma, "forma_pagamento", "id_forma", "FormaPagamento")

            sql_pag = """
                INSERT INTO pagamento_venda (
                    id_venda, id_forma, valor_pago, estorno
                ) VALUES (%s, %s, %s, %s)
            """
            if pagamentos_registros:
                cursor.executemany(sql_pag, pagamentos_registros)

        conn.commit()

        print("Importacao de vendas concluida com sucesso.")
        print(f"- Documentos processados: {len(vendas_registros)}")
        print(f"- Itens processados: {len(itens_registros)}")
        print(f"- Pagamentos processados: {len(pagamentos_registros)}")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Importador de vendas (documentos, itens e pagamentos) via Excel."
    )
    parser.add_argument(
        "--arquivo",
        type=str,
        help="Caminho do arquivo Excel para importacao.",
    )
    parser.add_argument(
        "--gerar-modelo",
        action="store_true",
        help="Gera um arquivo Excel modelo com a estrutura esperada.",
    )
    parser.add_argument(
        "--saida-modelo",
        type=str,
        default=str(Path(__file__).resolve().parent / "MODELO_IMPORTACAO_VENDAS.xlsx"),
        help="Caminho de saida para o arquivo modelo (padrao: etl_testes/MODELO_IMPORTACAO_VENDAS.xlsx).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.gerar_modelo:
        build_template(Path(args.saida_modelo))

    if args.arquivo:
        importar_vendas(Path(args.arquivo))

    if not args.gerar_modelo and not args.arquivo:
        print("Nada para executar.")
        print("Use --gerar-modelo para gerar planilha exemplo.")
        print("Use --arquivo CAMINHO.xlsx para importar.")


if __name__ == "__main__":
    main()
