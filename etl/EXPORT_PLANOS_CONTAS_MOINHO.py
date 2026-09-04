import pandas as pd
import pyodbc
from pathlib import Path

# =====================================================================
# CONFIGURAÇÕES
# =====================================================================
CAMINHO_ACCESS = r"C:\Users\emanu\Documents\Trabalho\Padaria\Dados Padrões\AC_HOST_MOI_2026.accdb"
CAMINHO_SAIDA = Path("DADOS_PLANO_CONTAS.xlsx")

ANALISES_DIMENSOES = {
    "SETORES": ['SETOR', 'SECAO', 'SUB_SECAO', 'GRUPO', 'PRODUTOS'],
    "CONTAGEM": ['Contagem']
}

def build_codigo_ordenacao(codigo: str) -> str:
    """Replica a lógica do Django para gerar o código zero-padded."""
    segmentos = [parte for parte in str(codigo or "").split(".") if parte != ""]
    if not segmentos:
        return ""
    normalizados = [parte.zfill(6) if parte.isdigit() else parte for parte in segmentos]
    return ".".join(normalizados) + "."

def extrair_dados_access(caminho_banco: str) -> pd.DataFrame:
    string_conexao = f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={caminho_banco};"
    todas_colunas = set(['COD_Dig'])
    for colunas in ANALISES_DIMENSOES.values():
        todas_colunas.update(colunas)
        
    try:
        conn = pyodbc.connect(string_conexao)
        query = f"SELECT {', '.join(todas_colunas)} FROM A_GRITEMM"
        df = pd.read_sql(query, conn)
        return df
    finally:
        if 'conn' in locals():
            conn.close()

def processar_exportacao():
    print("Extraindo dados do Access...")
    df_bruto = extrair_dados_access(CAMINHO_ACCESS)
    
    for colunas in ANALISES_DIMENSOES.values():
        for col in colunas:
            if col in df_bruto.columns:
                df_bruto[col] = df_bruto[col].astype(str).str.strip().str.upper()

    print("Montando as árvores hierárquicas multidimensionais...")
    
    arvore_nos = {}
    id_temp_counter = 1
    indice_raiz = 1

    # 1. Criação dos Nós Raiz
    for analise_nome in ANALISES_DIMENSOES.keys():
        tupla_raiz = (analise_nome,)
        codigo_gerado = f"{indice_raiz}."
        
        arvore_nos[tupla_raiz] = {
            'id_temp': id_temp_counter,
            'codigo_hierarquico': codigo_gerado,
            'codigo_ordenacao': build_codigo_ordenacao(codigo_gerado),
            'nome_conta': analise_nome,
            'id_pai_temp': None
        }
        id_temp_counter += 1
        indice_raiz += 1

    # 2. Preenchimento de cada ramo
    for analise_nome, colunas in ANALISES_DIMENSOES.items():
        df_unicos = df_bruto[colunas].drop_duplicates()
        
        for _, row in df_unicos.iterrows():
            caminho_atual = [analise_nome]
            
            for col in colunas:
                valor_no = row[col]
                if not valor_no or valor_no in ['NAN', 'NONE', '']:
                    break
                    
                caminho_atual.append(valor_no)
                tupla_caminho = tuple(caminho_atual)
                
                if tupla_caminho not in arvore_nos:
                    tupla_pai = tuple(caminho_atual[:-1])
                    pai = arvore_nos[tupla_pai]
                    
                    irmaos = [no for caminho, no in arvore_nos.items() 
                              if len(caminho) == len(tupla_caminho) and caminho[:-1] == tupla_pai]
                    
                    proximo_indice = len(irmaos) + 1
                    codigo_gerado = f"{pai['codigo_hierarquico']}{proximo_indice}."
                    
                    arvore_nos[tupla_caminho] = {
                        'id_temp': id_temp_counter,
                        'codigo_hierarquico': codigo_gerado,
                        'codigo_ordenacao': build_codigo_ordenacao(codigo_gerado),
                        'nome_conta': valor_no,
                        'id_pai_temp': pai['id_temp']
                    }
                    id_temp_counter += 1

    df_plano_contas = pd.DataFrame(list(arvore_nos.values()))
    
    print("Gerando vínculos multiplos entre Produtos e Categorias...")
    
    df_bruto['COD_Dig'] = pd.to_numeric(df_bruto['COD_Dig'], errors='coerce')
    df_produtos_validos = df_bruto.dropna(subset=['COD_Dig']).copy()
    df_produtos_validos['COD_Dig'] = df_produtos_validos['COD_Dig'].astype(int)
    
    vinculos = []
    
    for _, row in df_produtos_validos.iterrows():
        id_produto = row['COD_Dig']
        
        for analise_nome, colunas in ANALISES_DIMENSOES.items():
            caminho_atual = [analise_nome]
            
            for col in colunas:
                valor_no = row[col]
                if not valor_no or valor_no in ['NAN', 'NONE', '']:
                    break
                caminho_atual.append(valor_no)
                
            tupla_caminho = tuple(caminho_atual)
            
            if len(tupla_caminho) > 1 and tupla_caminho in arvore_nos:
                id_categoria = arvore_nos[tupla_caminho]['id_temp']
                vinculos.append({
                    'id_produto': id_produto,
                    'id_conta_temp': id_categoria
                })
            
    df_vinculos = pd.DataFrame(vinculos).drop_duplicates()

    print(f"Exportando {len(df_plano_contas)} contas e {len(df_vinculos)} vínculos para Excel...")
    with pd.ExcelWriter(CAMINHO_SAIDA, engine='openpyxl') as writer:
        df_plano_contas.to_excel(writer, sheet_name='plano_contas', index=False)
        df_vinculos.to_excel(writer, sheet_name='vinculo_produtos', index=False)
        
    print("Exportação multidimensional concluída com sucesso!")

if __name__ == "__main__":
    processar_exportacao()