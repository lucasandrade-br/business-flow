import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

COLUNAS_OBRIGATORIAS = [
    "id_fornecedor",
    "nome_fornecedor",
]

COLUNAS_OPCIONAIS = [
    "nome_gerencial",
    "raz_social",
    "dt_cadastro",
    "id_codsis",
    "codigo",
    "operador",
    "usuario",
]

COLUNAS_TODAS = COLUNAS_OBRIGATORIAS + COLUNAS_OPCIONAIS


def obter_gerador_hash_fornecedor():
    backend_dir = Path(__file__).resolve().parent.parent / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    try:
        from apps.integracao.hash_engine import gerar_hash_fornecedor
    except Exception as exc:
        raise ImportError(
            "Nao foi possivel importar gerar_hash_fornecedor de backend/apps/integracao/hash_engine.py"
        ) from exc

    return gerar_hash_fornecedor


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
    df = pd.DataFrame(
        [
            {
                "id_fornecedor": 1,
                "nome_fornecedor": "FORNECEDOR EXEMPLO",
                "nome_gerencial": "FORNECEDOR EXEMPLO",
                "raz_social": "FORNECEDOR EXEMPLO LTDA",
                "dt_cadastro": "2026-06-16",
                "id_codsis": "",
                "codigo": "00001",
                "operador": 0,
                "usuario": "",
            },
            {
                "id_fornecedor": 2,
                "nome_fornecedor": "DISTRIBUIDORA MODELO",
                "nome_gerencial": "DISTRIBUIDORA MODELO REGIONAL",
                "raz_social": "DISTRIBUIDORA MODELO SA",
                "dt_cadastro": "",
                "id_codsis": 1,
                "codigo": "00002",
                "operador": 0,
                "usuario": "",
            },
        ]
    )

    with pd.ExcelWriter(caminho_saida, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="fornecedores", index=False)

    print(f"Modelo de fornecedores gerado em: {caminho_saida}")


def carregar_planilha(caminho_arquivo: Path) -> pd.DataFrame:
    if not caminho_arquivo.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {caminho_arquivo}")

    df = normalizar_colunas(
        pd.read_excel(caminho_arquivo, sheet_name="fornecedores", dtype=object)
    )
    validar_colunas(df, COLUNAS_OBRIGATORIAS, "fornecedores")

    for col in COLUNAS_OPCIONAIS:
        if col not in df.columns:
            df[col] = None

    return df[COLUNAS_TODAS]


def importar_fornecedores(caminho_arquivo: Path) -> None:
    import pymysql

    gerar_hash_fornecedor = obter_gerador_hash_fornecedor()
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
            ids_codsis = set()

            for _, row in df.iterrows():
                id_fornecedor = to_int(
                    row["id_fornecedor"],
                    "fornecedores.id_fornecedor",
                )
                if id_fornecedor in chaves:
                    raise ValueError(f"Fornecedor duplicado no arquivo: {id_fornecedor}")
                chaves.add(id_fornecedor)

                nome_fornecedor = to_str(row["nome_fornecedor"])
                if not nome_fornecedor:
                    raise ValueError(
                        f"Campo obrigatorio ausente: fornecedores.nome_fornecedor ({id_fornecedor})"
                    )

                nome_gerencial_raw = row["nome_gerencial"]
                nome_gerencial = (
                    to_str(nome_gerencial_raw)
                    if not valor_vazio(nome_gerencial_raw)
                    else nome_fornecedor
                )

                raz_social = to_str(row["raz_social"])
                codigo = to_str(row["codigo"])
                usuario = to_str(row["usuario"])

                validar_tamanho(nome_fornecedor, "fornecedores.nome_fornecedor", 120)
                validar_tamanho(nome_gerencial, "fornecedores.nome_gerencial", 120)
                validar_tamanho(raz_social, "fornecedores.raz_social", 160)
                validar_tamanho(codigo, "fornecedores.codigo", 5)
                validar_tamanho(usuario, "fornecedores.usuario", 100)

                id_codsis = to_int(
                    row["id_codsis"],
                    "fornecedores.id_codsis",
                    permite_nulo=True,
                )
                if id_codsis is not None:
                    ids_codsis.add(id_codsis)

                operador = to_int(
                    row["operador"],
                    "fornecedores.operador",
                    permite_nulo=True,
                )
                if operador is None:
                    operador = 0

                dt_cadastro = to_date(
                    row["dt_cadastro"],
                    "fornecedores.dt_cadastro",
                    permite_nulo=True,
                )
                hash_md5 = gerar_hash_fornecedor(
                    id_fornecedor=id_fornecedor,
                    nome_fornecedor=nome_fornecedor,
                    raz_social=raz_social,
                    dt_cadastro=dt_cadastro,
                )

                registros.append(
                    (
                        id_fornecedor,
                        nome_fornecedor,
                        nome_gerencial,
                        raz_social,
                        hash_md5,
                        dt_cadastro,
                        id_codsis,
                        codigo,
                        operador,
                        usuario,
                    )
                )

            validar_fk(cursor, ids_codsis, "cod_sis", "id_codsis", "CodSis")

            sql_upsert = """
                INSERT INTO fornecedores (
                    id_fornecedor, nome_fornecedor, nome_gerencial, raz_social, hash_md5,
                    dt_cadastro, id_codsis, codigo, operador, usuario
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    nome_fornecedor = VALUES(nome_fornecedor),
                    nome_gerencial = IF(VALUES(nome_gerencial) = VALUES(nome_fornecedor), nome_gerencial, VALUES(nome_gerencial)),
                    raz_social = VALUES(raz_social),
                    hash_md5 = VALUES(hash_md5),
                    dt_cadastro = VALUES(dt_cadastro),
                    id_codsis = VALUES(id_codsis),
                    codigo = VALUES(codigo),
                    operador = VALUES(operador),
                    usuario = VALUES(usuario)
            """
            if registros:
                cursor.executemany(sql_upsert, registros)

        conn.commit()

        print("Importacao de fornecedores concluida com sucesso.")
        print(f"- Registros processados: {len(registros)}")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Importador de fornecedores via Excel."
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
        default=str(Path(__file__).resolve().parent / "MODELO_IMPORTACAO_FORNECEDORES.xlsx"),
        help="Caminho de saida para o arquivo modelo (padrao: etl_testes/MODELO_IMPORTACAO_FORNECEDORES.xlsx).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.gerar_modelo:
        build_template(Path(args.saida_modelo))

    if args.arquivo:
        importar_fornecedores(Path(args.arquivo))

    if not args.gerar_modelo and not args.arquivo:
        print("Nada para executar.")
        print("Use --gerar-modelo para gerar planilha exemplo.")
        print("Use --arquivo CAMINHO.xlsx para importar.")


if __name__ == "__main__":
    main()
