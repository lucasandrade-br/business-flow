import argparse
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

COLUNAS_COMPRAS = [
    "id_legado",
    "nota",
    "id_fornecedor",
    "data_emissao",
    "data_lanc",
    "valor_produtos",
    "valor_total_documento",
    "nfe_status",
]

COLUNAS_ITENS = [
    "id_legado_compra",
    "id_produto",
    "id_und_medida",
    "quantidade",
    "valor_custo",
    "valor_total_item",
    "descricao_origem",
    "descricao_compra_origem",
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


def to_date(valor, campo: str, permite_nulo: bool = False):
    if valor_vazio(valor):
        if permite_nulo:
            return None
        raise ValueError(f"Campo obrigatorio ausente: {campo}")

    if isinstance(valor, datetime):
        return valor.date()

    parsed = pd.to_datetime(valor, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"Campo {campo} invalido para data (YYYY-MM-DD): {valor}")
    return parsed.date()


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
    df_compras = pd.DataFrame(
        [
            {
                "id_legado": 50001,
                "nota": 12345,
                "id_fornecedor": 1,
                "data_emissao": "2026-06-10",
                "data_lanc": "2026-06-10",
                "valor_produtos": 150.50,
                "valor_total_documento": 150.50,
                "nfe_status": "AUTORIZADA",
            },
            {
                "id_legado": 50002,
                "nota": 12346,
                "id_fornecedor": 2,
                "data_emissao": "2026-06-11",
                "data_lanc": "2026-06-11",
                "valor_produtos": 89.90,
                "valor_total_documento": 89.90,
                "nfe_status": "AUTORIZADA",
            },
        ]
    )

    df_itens = pd.DataFrame(
        [
            {
                "id_legado_compra": 50001,
                "id_produto": 1,
                "id_und_medida": 1,
                "quantidade": 2,
                "valor_custo": 50.00,
                "valor_total_item": 100.00,
                "descricao_origem": "ITEM 1",
                "descricao_compra_origem": "DESCRICAO COMPRA ITEM 1",
            },
            {
                "id_legado_compra": 50001,
                "id_produto": 2,
                "id_und_medida": 1,
                "quantidade": 1,
                "valor_custo": 50.50,
                "valor_total_item": 50.50,
                "descricao_origem": "ITEM 2",
                "descricao_compra_origem": "DESCRICAO COMPRA ITEM 2",
            },
            {
                "id_legado_compra": 50002,
                "id_produto": 3,
                "id_und_medida": "",
                "quantidade": 1,
                "valor_custo": 89.90,
                "valor_total_item": 89.90,
                "descricao_origem": "ITEM UNICO",
                "descricao_compra_origem": "DESCRICAO COMPRA ITEM UNICO",
            },
        ]
    )

    with pd.ExcelWriter(caminho_saida, engine="openpyxl") as writer:
        df_compras.to_excel(writer, sheet_name="compras", index=False)
        df_itens.to_excel(writer, sheet_name="itens_compra", index=False)

    print(f"Modelo de compras gerado em: {caminho_saida}")


def carregar_planilha(caminho_arquivo: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not caminho_arquivo.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {caminho_arquivo}")

    df_compras = normalizar_colunas(pd.read_excel(caminho_arquivo, sheet_name="compras", dtype=object))
    df_itens = normalizar_colunas(pd.read_excel(caminho_arquivo, sheet_name="itens_compra", dtype=object))

    validar_colunas(df_compras, COLUNAS_COMPRAS, "compras")
    validar_colunas(df_itens, COLUNAS_ITENS, "itens_compra")

    return df_compras, df_itens


def importar_compras(caminho_arquivo: Path) -> None:
    import pymysql

    cfg = carregar_ambiente()
    df_compras, df_itens = carregar_planilha(caminho_arquivo)

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
            compras_registros = []
            chaves_compra = set()
            ids_fornecedor = set()

            for _, row in df_compras.iterrows():
                id_legado = to_int(row["id_legado"], "compras.id_legado")
                if id_legado in chaves_compra:
                    raise ValueError(f"Compra duplicada no arquivo: {id_legado}")
                chaves_compra.add(id_legado)

                id_fornecedor = to_int(row["id_fornecedor"], "compras.id_fornecedor")
                ids_fornecedor.add(id_fornecedor)

                compras_registros.append(
                    (
                        id_legado,
                        to_int(row["nota"], "compras.nota", permite_nulo=True),
                        id_fornecedor,
                        to_date(row["data_emissao"], "compras.data_emissao"),
                        to_date(row["data_lanc"], "compras.data_lanc", permite_nulo=True),
                        to_decimal(row["valor_produtos"], "compras.valor_produtos", permite_nulo=True),
                        to_decimal(row["valor_total_documento"], "compras.valor_total_documento"),
                        to_str(row["nfe_status"]),
                    )
                )

            validar_fk(cursor, ids_fornecedor, "fornecedores", "id_fornecedor", "Fornecedor")

            sql_upsert_compra = """
                INSERT INTO compra (
                    id_legado, nota, id_fornecedor,
                    data_emissao, data_lanc, valor_produtos,
                    valor_total_documento, nfe_status, momento_consolidacao
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL)
                ON DUPLICATE KEY UPDATE
                    nota = VALUES(nota),
                    id_fornecedor = VALUES(id_fornecedor),
                    data_emissao = VALUES(data_emissao),
                    data_lanc = VALUES(data_lanc),
                    valor_produtos = VALUES(valor_produtos),
                    valor_total_documento = VALUES(valor_total_documento),
                    nfe_status = VALUES(nfe_status)
            """
            cursor.executemany(sql_upsert_compra, compras_registros)

            ids_legado = sorted({item[0] for item in compras_registros})
            cursor.execute(
                f"SELECT id_compra, id_legado FROM compra WHERE id_legado IN ({placeholders(len(ids_legado))})",
                tuple(ids_legado),
            )
            mapa_compra = {int(r[1]): int(r[0]) for r in cursor.fetchall()}

            ids_compra_afetadas = [mapa_compra[item[0]] for item in compras_registros if item[0] in mapa_compra]
            if ids_compra_afetadas:
                cursor.execute(
                    f"DELETE FROM item_compra WHERE id_compra IN ({placeholders(len(ids_compra_afetadas))})",
                    tuple(ids_compra_afetadas),
                )

            itens_registros = []
            ids_produto = set()
            ids_unidade = set()

            for _, row in df_itens.iterrows():
                id_legado_compra = to_int(row["id_legado_compra"], "itens_compra.id_legado_compra")
                id_compra = mapa_compra.get(id_legado_compra)
                if id_compra is None:
                    raise ValueError(f"Compra nao encontrada para item: {id_legado_compra}")

                id_produto = to_int(row["id_produto"], "itens_compra.id_produto")
                id_unidade = to_int(
                    row["id_und_medida"], "itens_compra.id_und_medida", permite_nulo=True
                )
                ids_produto.add(id_produto)
                if id_unidade is not None:
                    ids_unidade.add(id_unidade)

                itens_registros.append(
                    (
                        id_compra,
                        id_produto,
                        id_unidade,
                        to_decimal(row["quantidade"], "itens_compra.quantidade"),
                        to_decimal(row["valor_custo"], "itens_compra.valor_custo"),
                        to_decimal(row["valor_total_item"], "itens_compra.valor_total_item"),
                        to_str(row["descricao_origem"]),
                        to_str(row["descricao_compra_origem"]),
                    )
                )

            validar_fk(cursor, ids_produto, "produtos", "id_produto", "Produto")
            validar_fk(cursor, ids_unidade, "unidade_medida", "id_und_medida", "UnidadeMedida")

            sql_item = """
                INSERT INTO item_compra (
                    id_compra, id_produto, id_und_medida,
                    quantidade, valor_custo, valor_total_item,
                    descricao_origem, descricao_compra_origem
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            if itens_registros:
                cursor.executemany(sql_item, itens_registros)

        conn.commit()

        print("Importacao de compras concluida com sucesso.")
        print(f"- Documentos processados: {len(compras_registros)}")
        print(f"- Itens processados: {len(itens_registros)}")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Importador de compras (documentos e itens) via Excel."
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
        default=str(Path(__file__).resolve().parent / "MODELO_IMPORTACAO_COMPRAS.xlsx"),
        help="Caminho de saida para o arquivo modelo (padrao: etl_testes/MODELO_IMPORTACAO_COMPRAS.xlsx).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.gerar_modelo:
        build_template(Path(args.saida_modelo))

    if args.arquivo:
        importar_compras(Path(args.arquivo))

    if not args.gerar_modelo and not args.arquivo:
        print("Nada para executar.")
        print("Use --gerar-modelo para gerar planilha exemplo.")
        print("Use --arquivo CAMINHO.xlsx para importar.")


if __name__ == "__main__":
    main()
