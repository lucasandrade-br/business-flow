import pandas as pd
import pymysql
from pathlib import Path
import os
from dotenv import load_dotenv

def carregar_ambiente() -> dict:
    load_dotenv(override=True)
    cfg = {
        "host": os.getenv("DB_HOST"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
        "port": int(os.getenv("DB_PORT", 3306)),
    }
    return cfg

def processar_importacao(caminho_arquivo: str):
    print("Lendo arquivo Excel...")
    df_contas = pd.read_excel(caminho_arquivo, sheet_name='plano_contas')
    df_vinculos = pd.read_excel(caminho_arquivo, sheet_name='vinculo_produtos')
    
    df_contas['profundidade'] = df_contas['codigo_hierarquico'].str.count(r'\.')
    df_contas = df_contas.sort_values(by='profundidade')
    
    cfg = carregar_ambiente()
    conn = pymysql.connect(**cfg, autocommit=False)
    
    mapa_ids_temporarios_para_reais = {}
    
    try:
        with conn.cursor() as cursor:
            # =================================================================
            # 1. CARGA DA ÁRVORE DE CATEGORIAS
            # =================================================================
            print(f"Iniciando inserção de {len(df_contas)} categorias no Plano de Contas...")
            
            # Adicionado codigo_ordenacao no INSERT
            sql_insert_conta = """
                INSERT IGNORE INTO plano_conta (codigo_hierarquico, codigo_ordenacao, nome_conta, id_conta_pai)
                VALUES (%s, %s, %s, %s)
            """
            
            for _, row in df_contas.iterrows():
                id_temp = int(row['id_temp'])
                codigo = str(row['codigo_hierarquico'])
                codigo_ord = str(row['codigo_ordenacao']) # Captura do Excel
                nome = str(row['nome_conta'])
                
                id_pai_temp = row['id_pai_temp']
                id_pai_real = mapa_ids_temporarios_para_reais.get(id_pai_temp) if pd.notna(id_pai_temp) else None
                
                cursor.execute(sql_insert_conta, (codigo, codigo_ord, nome, id_pai_real))
                
                if cursor.lastrowid:
                    mapa_ids_temporarios_para_reais[id_temp] = cursor.lastrowid
                else:
                    cursor.execute("SELECT id_conta FROM plano_conta WHERE codigo_hierarquico = %s", (codigo,))
                    resultado = cursor.fetchone()
                    if resultado:
                        mapa_ids_temporarios_para_reais[id_temp] = resultado[0]

            # =================================================================
            # 2. VALIDAÇÃO DE PRODUTOS E CARGA DE VÍNCULOS
            # =================================================================
            print("Validando produtos no MySQL...")
            produtos_excel = tuple(df_vinculos['id_produto'].unique())
            
            placeholders = ','.join(['%s'] * len(produtos_excel))
            cursor.execute(f"SELECT id_produto FROM produtos WHERE id_produto IN ({placeholders})", produtos_excel)
            produtos_existentes = {row[0] for row in cursor.fetchall()}
            
            produtos_ausentes = set(produtos_excel) - produtos_existentes
            if produtos_ausentes:
                print(f"⚠️ AVISO: {len(produtos_ausentes)} produtos não encontrados no MySQL e serão ignorados.")
                print(f"Exemplos de IDs ausentes: {list(produtos_ausentes)[:10]}")
            
            print(f"Iniciando inserção dos vínculos para {len(produtos_existentes)} produtos validados...")
            
            sql_insert_vinculo = """
                INSERT IGNORE INTO produtos_categorias (produto_id, planoconta_id) 
                VALUES (%s, %s)
            """
            
            registros_vinculos = []
            for _, row in df_vinculos.iterrows():
                id_produto = int(row['id_produto'])
                if id_produto in produtos_existentes:
                    id_temp_categoria = row['id_conta_temp']
                    id_real_categoria = mapa_ids_temporarios_para_reais.get(id_temp_categoria)
                    
                    if id_real_categoria:
                        registros_vinculos.append((id_produto, id_real_categoria))
            
            if registros_vinculos:
                cursor.executemany(sql_insert_vinculo, registros_vinculos)

        conn.commit()
        print("\n✅ Carga do Plano de Contas e vínculos finalizada com sucesso!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Erro crítico. Rollback executado: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    processar_importacao("DADOS_PLANO_CONTAS.xlsx")