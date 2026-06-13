NOVO MOTOR DE COMPRAS PARA IMPORTAÇÕES, VALIDAÇÕES E CONSOLIDAÇÕES.

1. Semelhante ao fluxo de importação, validação, tratamento e consolidação que já existe por completo para vendas, precisamos idealizar um processo lógico para esses mesmos tratamentos de compras.
1.1. Ele será um pouco mais fácil, pois não exigirá nenhuma validação com dados de auditoria ou coisas do tipo. Apenas capturar o dados do dataset Firebird.
1.2. Precisamos apenas realizar o fluxo padrão:
1.2.1. Importar os dados de compras com base em uma data inicial e final. Esses dados irão para tabelas de stagging e receber os tratamentos/validações necessárias.
1.2.2. Após tudo ser importado e validado, poderemos consolidar os dados nas tabelas oficiais

2. Sobre a validação, precisamos conferir as seguintes questões:
2.1. Se a compra já existe no nosso dataset através do ID
2.1.1. A chave de unicidade da compra no SOT será apenas NOTA_COMPRA.ID.
2.2. Se os fornecedores e produtos realmente existem no nosso dataset
2.2.1. Sobre essa validação através dos nomes, devemos utilizar a lógica que já existe no nosso software que utiliza uma % de semelhança pelos nomes.
2.2.2. Regra de prioridade: a validação de correspondência deve ser primeiramente semântica por similaridade de nome (não baseada apenas na existência do ID).
2.2.3. O ID será um sinal auxiliar de apoio, mas não o único critério para concluir convergência/divergência de fornecedor e produto.
2.2.4. Limiar oficial de similaridade: 80%.
2.2.5. Caso não seja encontrado, o usuário poderá realizar um cadastro manual pelo fluxo normal do software ou através da própria validação, poder vincular/alterar o fornecedor ou produto para algum que realmente já exista no dataset
2.3. Se um dado de compra está com um valor muito diferente dos somatório dos itens dessa compra
2.4. Compras de devolução/retorno (incluindo cenários com valores negativos) deverão ser bloqueadas no MVP.

3. Processo de validação
3.1 Gerar uma lógica para converter/vincular o dado "UNIDADE" para que se torne uma FK ligando à tabela do nosso dataset de unidades de medidas.
3.1.1. Uma forma que esse dado chegará para tratamento será ('KG', 'UN' etc.)
3.2. Sobre os produtos e fornecedores, devemos garantir que esses dados realmente corresponderão aos dados reais do nosso dataset

4. Devemos consultar/capturar os dados do dataset de origem com LEFT JOIN para realizar as validações se os dados de produtos e fornecedores realmente batem com os dados do nosso dataset com base nos nomes
4.1. LEFT JOIN com ID_PRODUTO para também puxar o nome do produto
4.2. LEFT JOIN com ID_FORNECEDOR para também capturar o nome do fornecedor


CREATE TABLE NOTA_COMPRA (
	ID INTEGER NOT NULL,
	NOTA INTEGER NOT NULL,
	ID_FORNECEDOR INTEGER NOT NULL,
	DATA_EMISSAO DATE NOT NULL,
	DATA_LANC DATE,
	VALOR_PRODUTOS NUMERIC(15,4) DEFAULT 0,
	VALOR_TOTAL NUMERIC(15,4) DEFAULT 0,
	NFE_STATUS VARCHAR(30),
);
*LEFT JOIN para adicionar uma coluna do nome fantasia do fornecedor

CREATE TABLE NOTA_COMPRA_DETALHE (
	ID INTEGER NOT NULL,
	ID_PRODUTO INTEGER,
	ID_NFE INTEGER,
	QUANTIDADE DECIMAL(18,6) DEFAULT 0,
	VALOR_CUSTO NUMERIC(18,6) DEFAULT 0,
	VALOR_TOTAL NUMERIC(15,4) DEFAULT 0,
	UNIDADE VARCHAR(6),
	DESCRICAO VARCHAR(120),
	DESCRICAO_COMPRA VARCHAR(120),
);
*LEFT JOIN para adicionar na consulta a coluna do nome do produto
*"ID_NFE" em "NOTA_COMPRA_DETALHE" é simplesmente uma FK que se referencia a "ID" em "NOTA_COMPRA"


Colunas necessárias de produtos e fornecedores do dataset de origem:
CREATE TABLE PRODUTOS (
	ID_PRODUTO INTEGER NOT NULL,
	PRODUTO VARCHAR(120),
);
CREATE TABLE FORNECEDOR (
	ID_FORNECEDOR INTEGER NOT NULL,
	FANTASIA VARCHAR(60),
);

5. Por fim, devemos ter um app no backend especializado para compras
5.1. Um frontend especializado também para as compras
5.1.1. Um template focalizado para realizar as validações etc.
5.1.2. Template para listagem dos dados das compras e outros para os dados dos itens.
5.1.3. Permitindo filtragens e formatos exportações como já existe no padrão dos outros templates.

*Resumindo, devemos analisar o flulxo de vendas e literalmente replicálo para o novo fluxo de compras

6. Decisões aprovadas (2026-06-11)
6.1. Unicidade da compra: apenas NOTA_COMPRA.ID.
6.2. Devoluções/retornos no fluxo de compras: bloqueado no MVP.
6.3. Similaridade textual para fornecedor/produto: limiar fixo de 80%.
6.4. Ordem da validação de correspondência: primeiro semelhança nominal, com ID como apoio, nunca como único critério.