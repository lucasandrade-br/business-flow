import pandas as pd
import pyodbc
from pathlib import Path

# =====================================================================
# 1. PARÂMETROS DE CONFIGURAÇÃO
# =====================================================================
CAMINHO_ACCESS = r"C:\Users\emanu\Documents\Trabalho\Padaria\Dados Padrões\AC_HOST_MOI_2026.accdb"
DIRETORIO_SAIDA = Path(r"C:\Users\emanu\Documents\Desenvolvimento\Business Flow\etl_testes\exports") 
PREFIXO_ARQUIVO = "DADOS_TRANSFORMADOS_COMPRAS"

MAPA_UNIDADES = {
    'UND': 1, 'CX': 2, 'KG': 3, 'UN': 4, 'LT': 6,
    'BNG': 8, 'UNI': 9, 'FD': 10, 'DY': 11, 'SC': 12,
    'CRT': 9002, 'GF': 9003, 'MIL': 9004, 'PCT': 9005, 'TP': 9006
}

# Colunas que apenas pesam na memória e não irão para o Excel
COLUNAS_DESCARTAR = ['Marcar', 'X', 'GRCMV', 'SETOR', 'SECAO', 'SUB_SECAO', 'GRUPO', 'FATOR']

def extrair_dados_access(caminho_banco: str) -> pd.DataFrame:
    """Conecta ao banco Access e extrai a tabela bruta de compras."""
    string_conexao = f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={caminho_banco};"
    try:
        conn = pyodbc.connect(string_conexao)
        df_compras = pd.read_sql("SELECT * FROM COMPRAS", conn)
        return df_compras
    finally:
        if 'conn' in locals():
            conn.close()

def processar_dados() -> None:
    print("Iniciando extração do banco legado de Compras...")
    df_base = extrair_dados_access(CAMINHO_ACCESS)

    print("\nIniciando validação e higienização dos dados...")
    
    # Descartar colunas irrelevantes
    colunas_presentes = [col for col in COLUNAS_DESCARTAR if col in df_base.columns]
    df_base = df_base.drop(columns=colunas_presentes)

    # =================================================================
    # 2. TRATAMENTO DE ANOMALIAS (ID_NFE Nulo)
    # =================================================================
    # Força a conversão para numérico para capturar textos vazios como NaN
    df_base['ID_NFE'] = pd.to_numeric(df_base['ID_NFE'], errors='coerce')
    
    # Identifica as linhas inválidas
    mask_nulos = df_base['ID_NFE'].isna()
    df_nulos = df_base[mask_nulos]
    
    qtd_negligenciados = len(df_nulos)
    ids_negligenciados = []
    
    if qtd_negligenciados > 0:
        # Extrai a chave primária do Access para facilitar sua auditoria depois
        if 'IDcp' in df_nulos.columns:
            ids_negligenciados = df_nulos['IDcp'].tolist()
        else:
            # Fallback caso a coluna IDcp não venha por algum motivo
            ids_negligenciados = (df_nulos.index + 2).tolist()
            
        print(f"⚠️ Atenção: Detectadas {qtd_negligenciados} linhas sem ID_NFE.")
        
    # Filtra o DataFrame, mantendo estritamente as linhas válidas
    df_valido = df_base[~mask_nulos].copy()
    
    # Garante que o ID_NFE fique inteiro (remove formatações flutuantes como .0)
    df_valido['ID_NFE'] = df_valido['ID_NFE'].astype(int)

    print("Iniciando agregações e mapeamentos...")

    # =================================================================
    # 3. TRANSFORMAÇÃO: ABA 'compras' (Cabeçalho Agrupado)
    # =================================================================
    # O método agg() consolida a compra e aplica regras específicas por coluna
    df_compras = df_valido.groupby('ID_NFE').agg(
        nota=('NOTA', 'first'),
        id_fornecedor=('ID_FORNECE', 'first'),
        data_emissao=('DATA', 'first'),
        data_lanc=('DATA_LANC', 'first'),
        valor_produtos=('CTOTAL', 'sum'),
        valor_total_documento=('CTOTAL', 'sum'),
        nfe_status=('STATUS', 'first')
    ).reset_index()
    
    df_compras = df_compras.rename(columns={'ID_NFE': 'id_legado'})

    # Preparação para o particionamento anual
    df_compras['data_emissao_dt'] = pd.to_datetime(df_compras['data_emissao'])
    df_compras['data_emissao'] = df_compras['data_emissao_dt'].dt.date
    df_compras['data_lanc'] = pd.to_datetime(df_compras['data_lanc']).dt.date
    df_compras['ano_compra'] = df_compras['data_emissao_dt'].dt.year

    # =================================================================
    # 4. TRANSFORMAÇÃO: ABA 'itens_compra'
    # =================================================================
    df_itens = pd.DataFrame()
    df_itens['id_legado_compra'] = df_valido['ID_NFE']
    df_itens['id_produto'] = df_valido['COD']
    
    if 'UND' in df_valido.columns:
        df_itens['id_und_medida'] = df_valido['UND'].astype(str).str.strip().str.upper().map(MAPA_UNIDADES)
    else:
        df_itens['id_und_medida'] = None
        
    df_itens['quantidade'] = df_valido['QUANT']
    df_itens['valor_custo'] = df_valido['CUSTO']
    df_itens['valor_total_item'] = df_valido['CTOTAL']
    df_itens['descricao_origem'] = df_valido['NOMENCLATURA']
    df_itens['descricao_compra_origem'] = df_valido['NOMENCLATURA']

    # =================================================================
    # 5. CARGA: PARTICIONAMENTO E EXPORTAÇÃO
    # =================================================================
    anos_unicos = df_compras['ano_compra'].dropna().unique()
    anos_unicos.sort()

    print(f"\nParticionando dados de {len(anos_unicos)} ano(s): {list(anos_unicos)}")

    for ano in anos_unicos:
        print(f"\nProcessando lote do ano: {int(ano)}...")
        
        compras_ano = df_compras[df_compras['ano_compra'] == ano].copy()
        ids_compra_ano = compras_ano['id_legado'].unique()
        
        itens_ano = df_itens[df_itens['id_legado_compra'].isin(ids_compra_ano)].copy()

        compras_ano = compras_ano.drop(columns=['data_emissao_dt', 'ano_compra'])

        nome_arquivo = f"{PREFIXO_ARQUIVO}_{int(ano)}.xlsx"
        caminho_saida = DIRETORIO_SAIDA / nome_arquivo

        with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
            compras_ano.to_excel(writer, sheet_name='compras', index=False)
            itens_ano.to_excel(writer, sheet_name='itens_compra', index=False)
        
        print(f"Lote {int(ano)} concluído! ({len(compras_ano)} documentos de compra, {len(itens_ano)} itens)")

    # =================================================================
    # 6. RELATÓRIO FINAL
    # =================================================================
    print("\n" + "="*60)
    print("🚀 Pipeline de ETL de Compras concluído!")
    if qtd_negligenciados > 0:
        print(f"\n⚠️ RELATÓRIO DE ANOMALIAS:")
        print(f"Total de registros descartados por falta de ID_NFE: {qtd_negligenciados}")
        print(f"Os seguintes valores de IDcp (Access) foram removidos da exportação:")
        print(ids_negligenciados)
    else:
        print("\n✅ Nenhuma anomalia encontrada. Todas as linhas possuíam ID_NFE.")
    print("="*60)

if __name__ == "__main__":
    processar_dados()