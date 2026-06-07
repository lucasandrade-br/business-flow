Documento Base de Conhecimento: Arquitetura de Integração (SOR -> SOT)

1. O Motor da Integração: O Pipeline ETL (Python + Django ORM)
O extrator não é um mero script isolado; ele atua como um serviço integrado ao back-end (Django). O fluxo de execução do pipeline seguirá estritamente os 4 passos técnicos abaixo para garantir a integridade e a velocidade da transação.

Passo 1: A Conexão Direta ao SOR (Firebird)
O serviço inicia abrindo uma conexão nativa com o banco legado (.FDB) utilizando a biblioteca fdb.
Ação: O script lê as credenciais de ambiente (.env) e se autentica no servidor Firebird.
A Extração: Executam-se as consultas SQL (SELECTs cirúrgicos) capturando apenas as colunas mapeadas.
Resultado: O banco de origem devolve os registros de forma bruta.

Passo 2: O Buffer em Memória (Processamento Eficiente)
Não há gravação de arquivos intermediários (como .xlsx ou .csv). Os dados fluem diretamente para a memória RAM do servidor.
Transformação: Utilizando dicionários nativos ou pandas (DataFrames), os dados sofrem a primeira higienização (remoção de espaços em branco e tipagem inicial).
Vantagem: A manipulação na memória elimina os gargalos de I/O (leitura e escrita em disco), acelerando o processo massivamente.

Passo 3: A Inicialização do ORM (Django -> MySQL)
Com os dados limpos em memória, o sistema não utiliza drivers complexos de ODBC. Ele invoca os modelos nativos do Django (models.py) configurados para o MySQL.
Ação: O ORM do Django assume a responsabilidade de traduzir a lógica do Python para a linguagem do banco SOT de forma segura.

Passo 4: O Pouso Seguro (Gravação nas Tabelas Staging)
O destino final dos dados brutos é a camada de recepção (Staging) no MySQL.
Limpeza da Staging: Para evitar duplicidades, a tabela temporária é esvaziada rapidamente utilizando o comando do ORM (Ex: StgProdutosBrutos.objects.all().delete()).
Bulk Create (Inserção em Lote Massiva): O sistema abandona inserções linha a linha. Uma lista de instâncias do modelo é gerada na memória e salva em uma única transação super otimizada utilizando Model.objects.bulk_create().
Resumo Visual do Fluxo de Dados (A Mecânica)
A cronologia exata do processamento, executada nos bastidores:
Start: Gatilho temporal (CRON Job/Agendador) ou manual via API.
Python -> FDB: cursor.execute("SELECT ID, NOME FROM PRODUTOS")
FDB -> Python: Alocação de 100.000+ linhas na RAM (Lista de Dicionários).
Python -> Django ORM: Inicialização das instâncias ([StgProduto(id=1...), StgProduto(id=2...)]).
Django -> MySQL: StgProdutos.objects.all().delete() (Limpa o terreno).
Django -> MySQL: StgProdutos.objects.bulk_create(lista_instancias) (Pouso dos dados).
Fim da Transação: Conexão com FDB encerrada.

O Papel do Back-end a partir daqui:
A responsabilidade da extração (ETL) finaliza na tabela de Staging. A interface Vue.js consumirá a API REST do Django, que comparará as tabelas STG com as tabelas definitivas do MySQL para renderizar os painéis de "Divergências" e "Novos Cadastros". O Front-end só consome dados que já aterrissaram em segurança localmente.

2. Regras da Camada SPEC (Especificações de Negócio)
Antes que qualquer dado seja persistido do ambiente de Staging para o ambiente de Produção (SOT), a API Django deve aplicar as seguintes travas de segurança estrutural:

Soberania da Chave Primária: Os IDs originários do banco SOR (ID_FORNECEDOR, ID_CLIENTE, ID_PRODUTO) são dogmáticos. Eles serão as chaves primárias ou chaves de referência direta no MySQL para garantir rastreabilidade e evitar lógicas custosas de desduplicação.

Máscara de Códigos (Zero-Padding): Colunas como CODIGO exigem exatos 5 caracteres. A validação do back-end (serializers.py) forçará a inserção de zeros à esquerda (Ex: o input 15 será gravado no MySQL estritamente como 00015).

Auditoria de Operações: Nenhuma inserção ou modificação manual ocorre de forma anônima. O banco SOT gravará o ID_OPERADOR (INT) e USUARIO (VARCHAR) capturados da sessão de autenticação web.

Estrutura de Hierarquia (Plano de Contas): O modelo das tabelas de categorização adotará o padrão Adjacency List (Auto-relacionamento).

Estrutura: ID_CONTA (PK), CODIGO_HIERARQUICO (String), NOME_CONTA (String) e ID_CONTA_PAI (FK referenciando a própria tabela).


###### **3. Mapeamento de Entidades (De/Para)**

**Entidade: FORNECEDORES**

Extração FDB: ID_FORNECEDOR, FANTASIA, RAZ_SOCIAL, DT_CADASTRO.
Entrada Manual (Enriquecimento): ID_CODSIS, CODIGO, OPERADOR, USUARIO.
Tabelas Auxiliares: N/A.

Estrutura Final SOT:
ID_FORNECEDOR (PK)
NOME_FORNECEDOR (STRING) <- Vem de FANTASIA
RAZ_SOCIAL (STRING)
DT_CADASTRO (DATE)
ID_CODSIS (INT/FK)
CODIGO (STRING) <- Máscara de 5 dígitos
OPERADOR (INT)
USUARIO (STRING)



**Entidade: CLIENTES**

Extração FDB: ID_CLIENTE, CLIENTE, RAZ_SOCIAL.
Entrada Manual (Enriquecimento): ID_GRUPO, ID_TIPO_VENDA, PRAZO_COB.
Tabelas Auxiliares: Grupos, Tipos de Venda.

Estrutura Final SOT:
ID_CLIENTE (PK)
NOME_CLIENTE (STRING) <- Vem de CLIENTE
RAZ_SOCIAL (STRING)
PRAZO_COB (INT)
ID_GRUPO (INT/FK)
ID_TIPO_VENDA (INT/FK)



**Entidade: PRODUTOS**

Extração FDB: ID_PRODUTO, PRODUTO, CUSTO, VALOR_VENDA, DT_ULTIMO_MOVIMENTO, STATUS, UNIDADE_COMECIAL, GTIN, BARRAS
Entrada Manual (Enriquecimento de Cálculo): MARKUP, MARKUP_INV, PERDA, FISICO, ALIQEFC, COD_G3N, COD_REL.
Entrada Manual (Planos de Contas): IDs para Financeiro, Cat_Vendas, Cont_Estoque, CMV, Marcar, Area, Darea.
Tabelas Auxiliares (7 Hierárquicas): Plano de contas estruturado, Tabela para unidades de medida (UNIDADE_COMECIAL - "KG, UND, LT...").

Estrutura Final SOT:
ID_PRODUTO (PK)
GTIN (STRING)
BARRAS (STRING)
PRODUTO (STRING)
ID_UND_MEDIDA (INT/FK)
CUSTO (FLOAT)
VENDA (FLOAT) <- Vem de VALOR_VENDA
STATUS
MARKUP (DECIMAL)
MARKUP_INV (DECIMAL)
PERDA (DECIMAL)
ID_FINANCEIRO (INT/FK)
ID_CAT_VENDAS (INT/FK)
ID_CONT_ETQ (INT/FK)
ID_CMV (INT/FK)
ID_MARC (INT/FK)
ID_AREA (INT/FK)
ID_DAREA (INT/FK)
ULT_MOV (DATE) <- Vem de DT_ULTIMO_MOVIMENTO
FISICO (DECIMAL)
ALIQEFC (STRING)
COD_G3N (INT)
COD_REL (INT)

