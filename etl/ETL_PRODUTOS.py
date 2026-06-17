import argparse
import os
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

COLUNAS_OBRIGATORIAS = [
    "id_produto",
    "produto",
    "custo",
    "venda",
]

COLUNAS_OPCIONAIS = [
    "nome_gerencial",
    "gtin",
    "barras",
    "ncm",
    "id_und_medida",
    "status",
    "markup",
    "markup_inv",
    "perda",
    "ult_mov",
    "fisico",
    "aliqefc",
    "cod_g3n",
    "cod_rel",
    "usuario",
]

COLUNAS_TODAS = COLUNAS_OBRIGATORIAS + COLUNAS_OPCIONAIS


def obter_gerador_hash_produto():
    backend_dir = Path(__file__).resolve().parent.parent / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    try:
        from apps.integracao.hash_engine import gerar_hash_produto
    except Exception as exc:
        raise ImportError(
            "Nao foi possivel importar gerar_hash_produto de backend/apps/integracao/hash_engine.py"
        ) from exc

    return gerar_hash_produto


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


def normalizar_ncm(valor, campo: str) -> str:
    ncm = to_str(valor)
    if not ncm:
        return ""

    ##if not ncm.isdigit() or len(ncm) != 8:
    ##    raise ValueError(
    ##        f"Campo {campo} deve conter exatamente 8 digitos numericos: {ncm}"
    ##    )
    return ncm


def validar_tamanho(valor: str, campo: str, tamanho: int) -> None:
    if len(valor) > tamanho:
        raise ValueError(
            f"Campo {campo} excede o limite de {tamanho} caracteres: {valor}"
        )


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
    df_produtos = pd.DataFrame(
        [
            {
                "id_produto": 1001,
                "produto": "ARROZ TIPO 1 5KG",
                "nome_gerencial": "ARROZ 5KG - PACOTE",
                "custo": 19.90,
                "venda": 24.90,
                "gtin": "7891234567890",
                "barras": "7891234567890",
                "ncm": "10063011",
                "id_und_medida": 1,
                "status": "ATIVO",
                "markup": 25.0000,
                "markup_inv": 20.0000,
                "perda": 0.0000,
                "ult_mov": "2026-06-16",
                "fisico": 120.0000,
                "aliqefc": "",
                "cod_g3n": 0,
                "cod_rel": 0,
                "usuario": "",
            },
            {
                "id_produto": 1002,
                "produto": "FEIJAO CARIOCA 1KG",
                "nome_gerencial": "",
                "custo": 6.50,
                "venda": 8.90,
                "gtin": "",
                "barras": "",
                "ncm": "07133319",
                "id_und_medida": "",
                "status": "ATIVO",
                "markup": 0.0000,
                "markup_inv": 0.0000,
                "perda": 0.0000,
                "ult_mov": "",
                "fisico": 0.0000,
                "aliqefc": "",
                "cod_g3n": 0,
                "cod_rel": 0,
                "usuario": "",
            },
        ]
    )

    with pd.ExcelWriter(caminho_saida, engine="openpyxl") as writer:
        df_produtos.to_excel(writer, sheet_name="produtos", index=False)

    print(f"Modelo de produtos gerado em: {caminho_saida}")


def carregar_planilha(caminho_arquivo: Path) -> pd.DataFrame:
    if not caminho_arquivo.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {caminho_arquivo}")

    df = normalizar_colunas(
        pd.read_excel(caminho_arquivo, sheet_name="produtos", dtype=object)
    )
    validar_colunas(df, COLUNAS_OBRIGATORIAS, "produtos")

    for col in COLUNAS_OPCIONAIS:
        if col not in df.columns:
            df[col] = None

    return df[COLUNAS_TODAS]


def importar_produtos(caminho_arquivo: Path) -> None:
    import pymysql

    gerar_hash_produto = obter_gerador_hash_produto()
    cfg = carregar_ambiente()
    df = carregar_planilha(caminho_arquivo)

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
            registros = []
            chaves = set()
            ids_unidade = set()

            for _, row in df.iterrows():
                id_produto = to_int(row["id_produto"], "produtos.id_produto")
                if id_produto in chaves:
                    raise ValueError(f"Produto duplicado no arquivo: {id_produto}")
                chaves.add(id_produto)

                nome_produto = to_str(row["produto"])
                if not nome_produto:
                    raise ValueError(f"Campo obrigatorio ausente: produtos.produto ({id_produto})")

                nome_gerencial_raw = row["nome_gerencial"]
                nome_gerencial = (
                    to_str(nome_gerencial_raw)
                    if not valor_vazio(nome_gerencial_raw)
                    else nome_produto
                )

                gtin = to_str(row["gtin"])
                barras = to_str(row["barras"])
                ncm = normalizar_ncm(row["ncm"], "produtos.ncm")
                status = to_str(row["status"])
                aliqefc = to_str(row["aliqefc"])
                usuario = to_str(row["usuario"])

                validar_tamanho(gtin, "produtos.gtin", 32)
                validar_tamanho(barras, "produtos.barras", 64)
                validar_tamanho(ncm, "produtos.ncm", 8)
                validar_tamanho(nome_produto, "produtos.produto", 120)
                validar_tamanho(nome_gerencial, "produtos.nome_gerencial", 120)
                validar_tamanho(status, "produtos.status", 30)
                validar_tamanho(aliqefc, "produtos.aliqefc", 20)
                validar_tamanho(usuario, "produtos.usuario", 100)

                id_unidade = to_int(
                    row["id_und_medida"],
                    "produtos.id_und_medida",
                    permite_nulo=True,
                )
                if id_unidade is not None:
                    ids_unidade.add(id_unidade)

                markup = to_decimal(
                    row["markup"],
                    "produtos.markup",
                    permite_nulo=True,
                ) or Decimal("0")
                markup_inv = to_decimal(
                    row["markup_inv"],
                    "produtos.markup_inv",
                    permite_nulo=True,
                ) or Decimal("0")
                perda = to_decimal(
                    row["perda"],
                    "produtos.perda",
                    permite_nulo=True,
                ) or Decimal("0")
                fisico = to_decimal(
                    row["fisico"],
                    "produtos.fisico",
                    permite_nulo=True,
                ) or Decimal("0")

                cod_g3n = to_int(
                    row["cod_g3n"],
                    "produtos.cod_g3n",
                    permite_nulo=True,
                )
                cod_rel = to_int(
                    row["cod_rel"],
                    "produtos.cod_rel",
                    permite_nulo=True,
                )

                custo = to_decimal(row["custo"], "produtos.custo")
                venda = to_decimal(row["venda"], "produtos.venda")

                hash_md5 = gerar_hash_produto(
                    id_produto=id_produto,
                    gtin=gtin,
                    barras=barras,
                    nome=nome_produto,
                    custo=custo,
                    venda=venda,
                    status=status,
                )

                registros.append(
                    (
                        id_produto,
                        gtin,
                        barras,
                        ncm,
                        nome_produto,
                        nome_gerencial,
                        id_unidade,
                        custo,
                        venda,
                        status,
                        hash_md5,
                        markup,
                        markup_inv,
                        perda,
                        to_date(
                            row["ult_mov"],
                            "produtos.ult_mov",
                            permite_nulo=True,
                        ),
                        fisico,
                        aliqefc,
                        cod_g3n if cod_g3n is not None else 0,
                        cod_rel if cod_rel is not None else 0,
                        usuario,
                    )
                )

            validar_fk(cursor, ids_unidade, "unidade_medida", "id_und_medida", "UnidadeMedida")

            sql_upsert = """
                INSERT INTO produtos (
                    id_produto, gtin, barras, ncm, produto, nome_gerencial, id_und_medida,
                    custo, venda, status, hash_md5, markup, markup_inv, perda,
                    ult_mov, fisico, aliqefc, cod_g3n, cod_rel, usuario
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    gtin = VALUES(gtin),
                    barras = VALUES(barras),
                    ncm = VALUES(ncm),
                    produto = VALUES(produto),
                    nome_gerencial = IF(VALUES(nome_gerencial) = VALUES(produto), nome_gerencial, VALUES(nome_gerencial)),
                    id_und_medida = VALUES(id_und_medida),
                    custo = VALUES(custo),
                    venda = VALUES(venda),
                    status = VALUES(status),
                    hash_md5 = VALUES(hash_md5),
                    markup = VALUES(markup),
                    markup_inv = VALUES(markup_inv),
                    perda = VALUES(perda),
                    ult_mov = VALUES(ult_mov),
                    fisico = VALUES(fisico),
                    aliqefc = VALUES(aliqefc),
                    cod_g3n = VALUES(cod_g3n),
                    cod_rel = VALUES(cod_rel),
                    usuario = VALUES(usuario)
            """
            if registros:
                cursor.executemany(sql_upsert, registros)

        conn.commit()

        print("Importacao de produtos concluida com sucesso.")
        print(f"- Registros processados: {len(registros)}")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Importador de produtos via Excel."
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
        default=str(Path(__file__).resolve().parent / "MODELO_IMPORTACAO_PRODUTOS.xlsx"),
        help="Caminho de saida para o arquivo modelo (padrao: etl_testes/MODELO_IMPORTACAO_PRODUTOS.xlsx).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.gerar_modelo:
        build_template(Path(args.saida_modelo))

    if args.arquivo:
        importar_produtos(Path(args.arquivo))

    if not args.gerar_modelo and not args.arquivo:
        print("Nada para executar.")
        print("Use --gerar-modelo para gerar planilha exemplo.")
        print("Use --arquivo CAMINHO.xlsx para importar.")


if __name__ == "__main__":
    main()
