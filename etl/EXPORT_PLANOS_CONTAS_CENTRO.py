import pandas as pd
import pyodbc
from pathlib import Path
import numpy as np

# =====================================================================
# CONFIGURAÇÕES
# =====================================================================
CAMINHO_ACCESS = r"C:\Users\emanu\Documents\Trabalho\Padaria\Dados Padrões\AC_HOST_DEL_2026.accdb"
CAMINHO_SAIDA = Path("DADOS_PLANO_CONTAS.xlsx")

# Separamos os dicionários para clareza da origem dos dados
DIMENSOES_PRODUTOS = {
    "SETORES": ['SETOR', 'SEÇAO', 'SUB_SECAO', 'GRUPO', 'PRODUTOS'],
    "CONTAGEM": ['Contagem']
}

DIMENSAO_OPERACOES = {
    "OPERAÇÕES": ['Operacao', 'Operacao_local', 'Operacao_Depto', 'Operacao_Setor', 'Area']
}

def build_codigo_ordenacao(codigo: str) -> str:
    segmentos = [parte for parte in str(codigo or "").split(".") if parte != ""]
    if not segmentos:
        return ""
    normalizados = [parte.zfill(6) if parte.isdigit() else parte for parte in segmentos]
    return ".".join(normalizados) + "."

def processar_exportacao():
    string_conexao = f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={CAMINHO_ACCESS};"
    
    arvore_nos = {}
    filhos_por_pai = {}
    
    # Função para construir a árvore garantindo a ordem cronológica
    def adicionar_no(tupla_no, nome, tupla_pai):
        if tupla_no not in arvore_nos:
            arvore_nos[tupla_no] = {'nome': nome, 'pai': tupla_pai}
            if tupla_pai not in filhos_por_pai:
                filhos_por_pai[tupla_pai] = []
            filhos_por_pai[tupla_pai].append(tupla_no)

    # 1. Inicializa todas as Raízes Analíticas
    ordem_raizes = list(DIMENSOES_PRODUTOS.keys()) + list(DIMENSAO_OPERACOES.keys())
    for analise_nome in ordem_raizes:
        adicionar_no((analise_nome,), analise_nome, None)

    try:
        conn = pyodbc.connect(string_conexao)
        
        # =================================================================
        # 2. PROCESSAR TABELA A_AGRP (OPERAÇÕES ISOLADAS)
        # =================================================================
        print("Processando tabela A_AGRP (Operações)...")
        colunas_op = ['COD_AAGRP'] + DIMENSAO_OPERACOES["OPERAÇÕES"]
        df_agrp = pd.read_sql(f"SELECT {', '.join(colunas_op)} FROM A_AGRP", conn)
        
        mapa_aagrp_para_caminho = {}
        
        for row in df_agrp.to_dict('records'):
            cod_aagrp_raw = row.get('COD_AAGRP')
            caminho_atual = ["OPERAÇÕES"]
            tupla_pai = tuple(caminho_atual)
            
            for col in DIMENSAO_OPERACOES["OPERAÇÕES"]:
                valor_bruto = row.get(col)
                if pd.isna(valor_bruto):
                    valor = 'NÃO DEFINIDO'
                else:
                    valor = str(valor_bruto).strip().upper()
                    if valor in ['NAN', 'NONE', 'NULL', '']:
                        valor = 'NÃO DEFINIDO'
                
                caminho_atual.append(valor)
                tupla_atual = tuple(caminho_atual)
                adicionar_no(tupla_atual, valor, tupla_pai)
                tupla_pai = tupla_atual
            
            # Mapeia o COD_AAGRP à última folha (Area) daquela linha
            if pd.notna(cod_aagrp_raw):
                try:
                    cod_val = int(float(cod_aagrp_raw))
                    mapa_aagrp_para_caminho[cod_val] = tupla_pai
                except ValueError:
                    pass
                    
        # =================================================================
        # 3. PROCESSAR TABELA A_GRITEMD (PRODUTOS ISOLADOS)
        # =================================================================
        print("Processando tabela A_GRITEMD (Produtos)...")
        colunas_prod = set(['COD_Dig', 'COD_AAGRP'])
        for cols in DIMENSOES_PRODUTOS.values():
            colunas_prod.update(cols)
            
        df_produtos = pd.read_sql(f"SELECT {', '.join(colunas_prod)} FROM A_GRITEMD", conn)
        
        vinculos = set()
        
        for row in df_produtos.to_dict('records'):
            id_produto_raw = row.get('COD_Dig')
            id_produto = None
            if pd.notna(id_produto_raw):
                try:
                    id_produto = int(float(id_produto_raw))
                except ValueError:
                    continue 
            else:
                continue
            
            # Monta os eixos vinculados exclusivamente à tabela de produtos
            for analise_nome, colunas in DIMENSOES_PRODUTOS.items():
                caminho_atual = [analise_nome]
                tupla_pai = tuple(caminho_atual)
                
                for col in colunas:
                    valor_bruto = row.get(col)
                    if pd.isna(valor_bruto):
                        valor = 'NÃO DEFINIDO'
                    else:
                        valor = str(valor_bruto).strip().upper()
                        if valor in ['NAN', 'NONE', 'NULL', '']:
                            valor = 'NÃO DEFINIDO'
                    
                    caminho_atual.append(valor)
                    tupla_atual = tuple(caminho_atual)
                    adicionar_no(tupla_atual, valor, tupla_pai)
                    tupla_pai = tupla_atual
                
                vinculos.add((id_produto, tupla_pai))
            
            # Vínculo "Mágico" com o eixo de Operações (Sem precisar ler colunas, apenas o ID)
            cod_aagrp_raw = row.get('COD_AAGRP')
            if pd.notna(cod_aagrp_raw):
                try:
                    cod_val = int(float(cod_aagrp_raw))
                    if cod_val in mapa_aagrp_para_caminho:
                        vinculos.add((id_produto, mapa_aagrp_para_caminho[cod_val]))
                except ValueError:
                    pass
                    
    finally:
        if 'conn' in locals():
            conn.close()

    # =================================================================
    # 4. GERAÇÃO DE CÓDIGOS E IDS FINAIS
    # =================================================================
    print("Calculando códigos hierárquicos...")
    
    nos_exportacao = []
    mapa_tupla_id = {}
    contador_id = [1]
    
    def processar_arvore(tupla_pai, codigo_pai, id_pai_temp):
        if tupla_pai not in filhos_por_pai:
            return
            
        filhos = filhos_por_pai[tupla_pai]
        
        for idx, tupla_filho in enumerate(filhos, start=1):
            meu_codigo = f"{codigo_pai}{idx}." if codigo_pai else f"{idx}."
            meu_id = contador_id[0]
            contador_id[0] += 1
            
            nome_conta = arvore_nos[tupla_filho]['nome']
            mapa_tupla_id[tupla_filho] = meu_id
            
            nos_exportacao.append({
                'id_temp': meu_id,
                'codigo_hierarquico': meu_codigo,
                'codigo_ordenacao': build_codigo_ordenacao(meu_codigo),
                'nome_conta': nome_conta,
                'id_pai_temp': id_pai_temp
            })
            
            processar_arvore(tupla_filho, meu_codigo, meu_id)

    processar_arvore(None, "", None)
    
    df_plano_contas = pd.DataFrame(nos_exportacao)
    
    print("Mapeando vínculos finais para o Excel...")
    vinculos_exportacao = []
    for id_prod, tupla_folha in vinculos:
        id_conta = mapa_tupla_id.get(tupla_folha)
        if id_conta:
            vinculos_exportacao.append({
                'id_produto': id_prod,
                'id_conta_temp': id_conta
            })
            
    df_vinculos = pd.DataFrame(vinculos_exportacao)
    
    print(f"Exportando {len(df_plano_contas)} contas e {len(df_vinculos)} vínculos...")
    with pd.ExcelWriter(CAMINHO_SAIDA, engine='openpyxl') as writer:
        df_plano_contas.to_excel(writer, sheet_name='plano_contas', index=False)
        df_vinculos.to_excel(writer, sheet_name='vinculo_produtos', index=False)
        
    print("Exportação concluída com sucesso! Árvores desacopladas e 100% capturadas.")

if __name__ == "__main__":
    processar_exportacao()