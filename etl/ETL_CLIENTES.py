import argparse
import os
import sys
from pathlib import Path

import pandas as pd

COLUNAS_OBRIGATORIAS = [
    "id_cliente",
    "nome_cliente",
]

COLUNAS_OPCIONAIS = [
    "nome_gerencial",
    "raz_social",
    "prazo_cob",
    "cliente_padrao",
    "id_grupo",
    "id_tipo_venda",
]

COLUNAS_TODAS = COLUNAS_OBRIGATORIAS + COLUNAS_OPCIONAIS


def obter_gerador_hash_cliente():
    backend_dir = Path(__file__).resolve().parent.parent / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    try:
        from apps.integracao.hash_engine import gerar_hash_cliente
    except Exception as exc:
        raise ImportError(
            "Nao foi possivel importar gerar_hash_cliente de backend/apps/integracao/hash_engine.py"
        ) from exc

    return gerar_hash_cliente


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


def to_bool(valor, campo: str, permite_nulo: bool = True) -> bool | None:
    if valor_vazio(valor):
        if permite_nulo:
            return None
        raise ValueError(f"Campo obrigatorio ausente: {campo}")

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
                "id_cliente": 1,
                "nome_cliente": "CLIENTE BALCAO",
                "nome_gerencial": "CLIENTE BALCAO",
                "raz_social": "",
                "prazo_cob": 0,
                "cliente_padrao": 1,
                "id_grupo": "",
                "id_tipo_venda": "",
            },
            {
                "id_cliente": 2,
                "nome_cliente": "SUPERMERCADO EXEMPLO",
                "nome_gerencial": "SUPERMERCADO EXEMPLO MATRIZ",
                "raz_social": "SUPERMERCADO EXEMPLO LTDA",
                "prazo_cob": 30,
                "cliente_padrao": 0,
                "id_grupo": 1,
                "id_tipo_venda": 1,
            },
        ]
    )

    with pd.ExcelWriter(caminho_saida, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="clientes", index=False)

    print(f"Modelo de clientes gerado em: {caminho_saida}")


def carregar_planilha(caminho_arquivo: Path) -> pd.DataFrame:
    if not caminho_arquivo.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {caminho_arquivo}")

    df = normalizar_colunas(
        pd.read_excel(caminho_arquivo, sheet_name="clientes", dtype=object)
    )
    validar_colunas(df, COLUNAS_OBRIGATORIAS, "clientes")

    for col in COLUNAS_OPCIONAIS:
        if col not in df.columns:
            df[col] = None

    return df[COLUNAS_TODAS]


def importar_clientes(caminho_arquivo: Path) -> None:
    import pymysql

    gerar_hash_cliente = obter_gerador_hash_cliente()
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
            ids_grupo = set()
            ids_tipo_venda = set()
            clientes_padrao_ids = []

            for _, row in df.iterrows():
                id_cliente = to_int(row["id_cliente"], "clientes.id_cliente")
                if id_cliente in chaves:
                    raise ValueError(f"Cliente duplicado no arquivo: {id_cliente}")
                chaves.add(id_cliente)

                nome_cliente = to_str(row["nome_cliente"])
                if not nome_cliente:
                    raise ValueError(
                        f"Campo obrigatorio ausente: clientes.nome_cliente ({id_cliente})"
                    )

                nome_gerencial_raw = row["nome_gerencial"]
                nome_gerencial = (
                    to_str(nome_gerencial_raw)
                    if not valor_vazio(nome_gerencial_raw)
                    else nome_cliente
                )

                raz_social = to_str(row["raz_social"])
                validar_tamanho(nome_cliente, "clientes.nome_cliente", 120)
                validar_tamanho(nome_gerencial, "clientes.nome_gerencial", 120)
                validar_tamanho(raz_social, "clientes.raz_social", 160)

                hash_md5 = gerar_hash_cliente(
                    id_cliente=id_cliente,
                    nome_cliente=nome_cliente,
                    raz_social=raz_social,
                )

                prazo_cob = to_int(
                    row["prazo_cob"],
                    "clientes.prazo_cob",
                    permite_nulo=True,
                )
                if prazo_cob is None:
                    prazo_cob = 0
                if prazo_cob < 0:
                    raise ValueError(
                        f"Campo clientes.prazo_cob nao pode ser negativo ({id_cliente})"
                    )

                cliente_padrao = bool(
                    to_bool(
                        row["cliente_padrao"],
                        "clientes.cliente_padrao",
                        permite_nulo=True,
                    )
                    or False
                )
                if cliente_padrao:
                    clientes_padrao_ids.append(id_cliente)

                id_grupo = to_int(
                    row["id_grupo"],
                    "clientes.id_grupo",
                    permite_nulo=True,
                )
                id_tipo_venda = to_int(
                    row["id_tipo_venda"],
                    "clientes.id_tipo_venda",
                    permite_nulo=True,
                )

                if id_grupo is not None:
                    ids_grupo.add(id_grupo)
                if id_tipo_venda is not None:
                    ids_tipo_venda.add(id_tipo_venda)

                registros.append(
                    (
                        id_cliente,
                        nome_cliente,
                        nome_gerencial,
                        raz_social,
                        hash_md5,
                        prazo_cob,
                        1 if cliente_padrao else 0,
                        id_grupo,
                        id_tipo_venda,
                    )
                )

            if len(clientes_padrao_ids) > 1:
                raise ValueError(
                    "A planilha possui mais de um cliente_padrao=1. Informe apenas um registro como padrao."
                )

            validar_fk(cursor, ids_grupo, "grupo_cliente", "id_grupo", "GrupoCliente")
            validar_fk(cursor, ids_tipo_venda, "tipo_venda", "id_tipo_venda", "TipoVenda")

            sql_upsert = """
                INSERT INTO clientes (
                    id_cliente, nome_cliente, nome_gerencial, raz_social, hash_md5,
                    prazo_cob, cliente_padrao, id_grupo, id_tipo_venda
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    nome_cliente = VALUES(nome_cliente),
                    nome_gerencial = IF(VALUES(nome_gerencial) = VALUES(nome_cliente), nome_gerencial, VALUES(nome_gerencial)),
                    raz_social = VALUES(raz_social),
                    hash_md5 = VALUES(hash_md5),
                    prazo_cob = VALUES(prazo_cob),
                    cliente_padrao = VALUES(cliente_padrao),
                    id_grupo = VALUES(id_grupo),
                    id_tipo_venda = VALUES(id_tipo_venda)
            """
            if registros:
                cursor.executemany(sql_upsert, registros)

            if clientes_padrao_ids:
                cursor.execute(
                    "UPDATE clientes SET cliente_padrao = 0 WHERE cliente_padrao = 1 AND id_cliente <> %s",
                    (clientes_padrao_ids[0],),
                )

        conn.commit()

        print("Importacao de clientes concluida com sucesso.")
        print(f"- Registros processados: {len(registros)}")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Importador de clientes via Excel."
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
        default=str(Path(__file__).resolve().parent / "MODELO_IMPORTACAO_CLIENTES.xlsx"),
        help="Caminho de saida para o arquivo modelo (padrao: etl_testes/MODELO_IMPORTACAO_CLIENTES.xlsx).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.gerar_modelo:
        build_template(Path(args.saida_modelo))

    if args.arquivo:
        importar_clientes(Path(args.arquivo))

    if not args.gerar_modelo and not args.arquivo:
        print("Nada para executar.")
        print("Use --gerar-modelo para gerar planilha exemplo.")
        print("Use --arquivo CAMINHO.xlsx para importar.")


if __name__ == "__main__":
    main()
