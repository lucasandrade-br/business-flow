# Versão 2.0: Motor de Reconciliação Financeira e Transações

## 1. Visão Geral do Negócio
A Versão 2.0 eleva o sistema de um repositório de dados mestres (MDM) para um motor transacional financeiro. O objetivo central é extrair os dados de vendas (NFCe e DAV) do banco legado (Firebird), cruzá-los com as planilhas de auditoria geradas pela operação (Excel/VBA) e garantir 100% de integridade antes de consolidá-los nas tabelas oficiais do sistema (SOT).

## 2. Arquitetura de Domínios (Domain-Driven Design)
Para manter o monolito escalável, o sistema divide os domínios:
* **App `cadastros`:** Entidades compartilhadas e estruturais (Produtos, Clientes, Fornecedores, Usuários, Formas de Pagamento, Plano de Contas).
* **App `vendas`:** Entidades estritamente transacionais consolidadas e higienizadas (SOT).
* **App `validacao`:** A *Staging Area* (STG). Recebe dados "crus" do Firebird e das planilhas para processamento e triagem.

## 3. O Paradigma de Unificação (SOT)
O sistema legado trata Vendas Fiscais (NFCe) e Orçamentos/Pedidos (DAV) em tabelas distintas. 
**Regra de Ouro:** No SOT (Tabelas Oficiais), ambas as naturezas são unificadas na tabela central `Venda`, sendo diferenciadas apenas pelo campo `tipo_documento` ('NFCE' ou 'DAV'). Isso viabiliza relatórios de Business Intelligence (BI) unificados e cálculos financeiros precisos sem a necessidade de *JOINs* complexos.

## 4. Estrutura de Banco de Dados
### 4.1. Tabelas Compartilhadas (`cadastros`)
* `Usuario`
* `FormaPagamento`

### 4.2. Tabelas Oficiais (`vendas` - SOT)
* `Venda`: id_venda, id_legado, tipo_documento, data_venda, hora_venda, valor_total_documento (FKs para Cliente e Usuario).
* `ItemVenda`: Relaciona a Venda ao Produto (quantidade, valor_unitario, valor_total).
* `PagamentoVenda`: Relaciona a Venda à FormaPagamento (valor_pago).

### 4.3. Tabelas Temporárias (`validacao` - STG)
* `STG_Venda`, `STG_ItemVenda`, `STG_PagamentoVenda`: Recebem a carga direta do Firebird (desnormalizada, sem restrição forte de Foreign Key, usando literais do legado).
* `STG_AuditoriaPlanilha`: Recebe a carga do arquivo `.xlsx` do operador. Armazena a "verdade auditada" (Data, ID_Legado, Tipo, Usuário, Valor, Tipo_Pagamento).

## 5. O Funil de Tripla Validação (Regras de Negócio)
Para que uma venda cruze da Staging Area (STG) para o Oficial (SOT), ela deve passar pelos seguintes testes no Motor de Reconciliação:
1. **Teste de Integridade Interna:** A soma dos valores de todos os `STG_ItemVenda` atrelados à venda bate exatamente com o `valor_total_documento` registrado na `STG_Venda`?
2. **Teste de Reconciliação (Cross-Check Humano):** Os dados da Venda importada do Firebird batem com os dados inseridos em `STG_AuditoriaPlanilha` (planilha do funcionário) no tocante a ID, Valor e Tipo de Pagamento?
3. **Teste de Idempotência (Antiduplicidade):** O `id_legado` + `tipo_documento` já existe na tabela SOT `Venda`? Se sim, o registro deve ser ignorado na importação final.

## 6. O Fluxo de Trabalho (Roadmap de Implementação)
* **Sprint 1:** Modelagem robusta de banco de dados (SOT e STG).
* **Sprint 2:** Motor ETL de extração do Firebird para as tabelas STG.
* **Sprint 3:** Motor de Ingestão de Planilhas via Pandas para `STG_AuditoriaPlanilha`.
* **Sprint 4:** Dashboard de Auditoria Visual e Efetivação para o SOT.