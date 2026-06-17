import pandas as pd
import pyodbc
from pathlib import Path

# =====================================================================
# 1. PARÂMETROS DE CONFIGURAÇÃO
# =====================================================================
CAMINHO_ACCESS = r"C:\Users\emanu\Documents\Trabalho\Padaria\Dados Padrões\AC_HOST_DEL_2026.accdb"
DIRETORIO_SAIDA = Path(r"C:\Users\emanu\Documents\Desenvolvimento\Business Flow\etl_testes\exports") 
PREFIXO_ARQUIVO = "DADOS_TRANSFORMADOS_VENDAS_CENTRO"

# Regras de Negócio
CLIENTE_PADRAO_ID = 269 
TIPO_DOCUMENTO_FIXO = 'DAV'
CLIENTES_INVALIDOS = ['000', '', '0', None, 'NaN']

# Mapeamento de Unidades
MAPA_UNIDADES = {
    'UND': 1, 'CX': 2, 'KG': 3, 'UN': 4, 'LT': 6,
    'BNG': 8, 'UNI': 9, 'FD': 10, 'DY': 11, 'SC': 12,
    'CRT': 9002, 'GF': 9003, 'MIL': 9004, 'PCT': 9005, 'TP': 9006
}

def extrair_dados_access(caminho_banco: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    string_conexao = f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={caminho_banco};"
    try:
        conn = pyodbc.connect(string_conexao)
        df_vforma = pd.read_sql("SELECT * FROM VFORMA", conn)
        df_vitem = pd.read_sql("SELECT * FROM VITEM", conn)
        return df_vforma, df_vitem
    finally:
        if 'conn' in locals():
            conn.close()

def converter_booleano(valor) -> int:
    if pd.isna(valor):
        return 0
    return 1 if str(valor).strip().upper() == 'S' else 0

def processar_dados() -> None:
    print("Iniciando extração do banco legado (Centro)...")
    df_vforma, df_vitem = extrair_dados_access(CAMINHO_ACCESS)

    print("Iniciando transformações computadas...")

    # =================================================================
    # 2. TRANSFORMAÇÃO: ABA 'vendas' (Com Agregação)
    # =================================================================
    df_vendas_base = df_vforma.drop_duplicates(subset=['ID']).copy()
    
    # NOVO: Calcula o valor total agrupando a coluna Vtotal da VITEM pelo ID da Venda
    totais_calculados = df_vitem.groupby('ID_NFCE')['VTotal'].sum().reset_index()
    totais_calculados = totais_calculados.rename(columns={'ID_NFCE': 'ID', 'VTotal': 'VALOR_TOTAL_CALCULADO'})
    
    # Faz o merge para trazer o valor calculado para a tabela base de vendas
    df_vendas_base = df_vendas_base.merge(totais_calculados, on='ID', how='left')
    
    # Preenche com 0 caso existam vendas sem itens registrados (evita nulos)
    df_vendas_base['VALOR_TOTAL_CALCULADO'] = df_vendas_base['VALOR_TOTAL_CALCULADO'].fillna(0)
    
    df_vendas = pd.DataFrame()
    df_vendas['id_legado'] = df_vendas_base['ID']
    df_vendas['tipo_documento'] = TIPO_DOCUMENTO_FIXO
    
    df_vendas['data_venda_dt'] = pd.to_datetime(df_vendas_base['DATA_VENDA'])
    df_vendas['data_venda'] = df_vendas['data_venda_dt'].dt.date
    df_vendas['ano_venda'] = df_vendas['data_venda_dt'].dt.year 
    
    df_vendas['hora_venda'] = df_vendas_base['HORA_VENDA']
    df_vendas['status'] = df_vendas_base['STATUS_VEN']
    df_vendas['id_cliente'] = df_vendas_base['ID_CLIENTE'].apply(
        lambda x: CLIENTE_PADRAO_ID if str(x).strip() in CLIENTES_INVALIDOS else x
    )
    df_vendas['id_usuario'] = df_vendas_base['ID_USUARIO']
    
    # Atribui o novo valor agregado à coluna exigida pelo modelo
    df_vendas['valor_total_documento'] = df_vendas_base['VALOR_TOTAL_CALCULADO']

    # =================================================================
    # 3. TRANSFORMAÇÃO: ABA 'itens_venda'
    # =================================================================
    df_itens = pd.DataFrame()
    df_itens['id_legado_venda'] = df_vitem['ID_NFCE']
    df_itens['tipo_documento'] = TIPO_DOCUMENTO_FIXO
    df_itens['id_produto'] = df_vitem['ID_PRODUTO']
    df_itens['id_und_medida'] = df_vitem['UNIDADE_CO'].str.strip().str.upper().map(MAPA_UNIDADES)
    df_itens['quantidade'] = df_vitem['QUANTIDADE']
    df_itens['valor_unitario'] = df_vitem['VALOR_UNIT']
    df_itens['valor_total_item'] = df_vitem['VTotal']
    df_itens['cancelado'] = df_vitem['CANCELADO'].apply(converter_booleano)

    # =================================================================
    # 4. TRANSFORMAÇÃO: ABA 'pagamentos_venda'
    # =================================================================
    df_pagamentos = pd.DataFrame()
    df_pagamentos['id_legado_venda'] = df_vforma['ID']
    df_pagamentos['tipo_documento'] = TIPO_DOCUMENTO_FIXO
    df_pagamentos['id_forma'] = df_vforma['ID_TIPO_PA']
    df_pagamentos['valor_pago'] = df_vforma['VALOR']
    df_pagamentos['estorno'] = df_vforma['ESTORNO'].apply(converter_booleano)

    # =================================================================
    # 5. CARGA: PARTICIONAMENTO E EXPORTAÇÃO
    # =================================================================
    anos_unicos = df_vendas['ano_venda'].dropna().unique()
    anos_unicos.sort()

    print(f"\nParticionando dados encontrados em {len(anos_unicos)} ano(s): {list(anos_unicos)}")

    for ano in anos_unicos:
        print(f"\nProcessando lote do ano: {int(ano)}...")
        
        vendas_ano = df_vendas[df_vendas['ano_venda'] == ano].copy()
        ids_venda_ano = vendas_ano['id_legado'].unique()
        
        itens_ano = df_itens[df_itens['id_legado_venda'].isin(ids_venda_ano)].copy()
        pagamentos_ano = df_pagamentos[df_pagamentos['id_legado_venda'].isin(ids_venda_ano)].copy()

        vendas_ano = vendas_ano.drop(columns=['data_venda_dt', 'ano_venda'])

        nome_arquivo = f"{PREFIXO_ARQUIVO}_{int(ano)}.xlsx"
        caminho_saida = DIRETORIO_SAIDA / nome_arquivo

        print(f"Gerando arquivo: {nome_arquivo}")
        with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
            vendas_ano.to_excel(writer, sheet_name='vendas', index=False)
            itens_ano.to_excel(writer, sheet_name='itens_venda', index=False)
            pagamentos_ano.to_excel(writer, sheet_name='pagamentos_venda', index=False)
        
        print(f"Lote {int(ano)} concluído! "
              f"({len(vendas_ano)} vendas, {len(itens_ano)} itens, {len(pagamentos_ano)} pagamentos)")

    print("\nTodo o pipeline de ETL do Centro foi concluído com sucesso!")

if __name__ == "__main__":
    processar_dados()