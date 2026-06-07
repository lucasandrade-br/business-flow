# Documento Base de Conhecimento: Arquitetura de Software e Infraestrutura



###### **1. Visão Geral da Arquitetura (Decoupled Monorepo)**

O sistema não utilizará a estrutura monolítica tradicional onde o back-end renderiza as telas. Adotaremos uma arquitetura Desacoplada (Decoupled) organizada em um Monorepo (um único repositório de versão, contendo duas aplicações distintas).

O sistema rodará localmente (localhost), mas entregará a experiência de um aplicativo de desktop moderno através de tecnologia PWA (Progressive Web App).



###### **2. O Ecossistema Back-end (Motor de Regras, Validação e API)**

O Back-end será desenvolvido em Python + Django, atuando estritamente como uma API REST para servir ao Front-end (PWA). A arquitetura interna foge do padrão básico do Django e adota o modelo de separação de responsabilidades (Camada de Transporte -> Camada de Negócio -> Camada de Dados).

Modularidade e Escopo: O projeto é dividido em Apps de responsabilidade única (integracao, validacao, analise, admin).

Injeção de Dependências Dinâmica (Segurança): Nenhum caminho de arquivo (C:\\...), driver ODBC ou credencial existirá hardcoded no código fonte. O sistema utilizará bibliotecas como python-decouple para ler variáveis do arquivo .env e montar as strings de conexão dinamicamente no settings.py.

Validação Estrita de Contrato (A Camada SPEC): Antes que qualquer dado modificado pelo usuário atinja o banco de dados, o payload (JSON) recebido pela API passará por uma validação de tipagem rigorosa (utilizando Pydantic ou Serializers). Isso garante que o motor de banco de dados nunca receba uma string onde deveria haver um inteiro, evitando quebras na execução do ODBC.

Isolamento da Regra de Negócio: Os arquivos de visualização da API (views.py ou api.py) não executam comunicação com o banco. Eles apenas recebem a requisição, passam pela validação e chamam funções de serviços (services.py).



###### **3. Estratégia de Banco de Dados e Padrões de Projeto**

O sistema utilizará dois motores de banco de dados simultâneos para separar o controle da aplicação dos dados de negócio, garantindo estabilidade e "Zero Gambiarras" na comunicação.

**3.1. Banco de Dados Interno (Aplicações e Sessões)**

Motor: SQLite3 nativo.

Propósito: Gerenciar exclusivamente o ecossistema do sistema (usuários, permissões, sessões do Front-end e logs). É gerenciado nativamente pelo ORM do Django (models.py).

**3.2. Banco de Dados de Negócio (SOT - MS Access)**

Motor: Arquivo .accdb acessado via driver ODBC do Windows.

Propósito: Armazenar as tabelas de Staging e as tabelas finais de Produção (Fornecedores, Clientes, Produtos).

Arquitetura de Comunicação (Repository Pattern): O ORM do Django está estritamente proibido de acessar este banco. A comunicação será feita via pyodbc abstraído através das seguintes estruturas:

Context Manager (Segurança de Conexão): Implementação de uma classe com métodos \_\_enter\_\_ e \_\_exit\_\_ para abrir e fechar conexões ODBC com o Access. Isso garante que, em caso de falha de código, a transação sofra um rollback automático e a conexão seja destruída, evitando vazamento de memória e travamento do arquivo .accdb.

Base Repository (Abstração e Proteção): Para manter o princípio DRY (Don't Repeat Yourself) e proteger contra SQL Injection, não haverá strings de SELECT, INSERT ou UPDATE escritas manualmente nas regras de negócio. Existirá uma classe BaseAccessRepository que receberá dicionários de dados do Python (ex: kwargs) e montará as instruções SQL parametrizadas dinamicamente.

Uso Prático: A camada de serviços instanciará o repositório informando apenas a tabela alvo e passará os dados validados. O repositório faz o trabalho pesado de converter isso para a linguagem que o Access entende.

###### 

###### **4. O Ecossistema Front-end (Interface e Experiência do Usuário)**

A interface será um projeto JavaScript/TypeScript isolado, empacotado como um PWA.

PWA (Progressive Web App): Permite que o sistema web seja "instalado" no computador local, criando um atalho, rodando em janela própria (sem a barra de endereços do navegador) e entregando uma experiência fluida de software nativo.

Consumo de API: O Front-end será responsável por renderizar a interface visual, os modais de validação, as tabelas de Diff e capturar as ações do usuário, enviando tudo empacotado via JSON para as rotas da API do Django.



###### **5. Estrutura de Diretórios Padrão**

A árvore de desenvolvimento deverá seguir a seguinte hierarquia física:

business flow/

├── .gitignore

├─── .env

│ 

├─── knowledge base/            # Todo estudo e idealização do software

│    ├── README.md

│

├── backend/                  # API REST em Python

│   ├── venv/                 # Ambiente virtual

│   ├── requirements.txt      # Dependências (Django, pyodbc, pandas)

│   ├── core\_project/         # Configurações globais e urls base

│   └── apps/                 

│       ├── integracao/       # Lógica ETL (Firebird -> Access)

│       ├── validacao/        # API para os modais de pendências e categorias

│       └── analise/          # API para leitura do SOT (futuros relatórios)

│       └── admin/            # API responsável pelos CRUD dos dados

│

└── frontend/                 # PWA Local

&#x20;   ├── package.json          # Dependências Node.js

&#x20;   ├── public/               

&#x20;   │   ├── manifest.json     # Configuração do App PWA (ícones, nome, cores)

&#x20;   │   ├── serviceWorker.js  # Permite o funcionamento do PWA e cache local

&#x20;   └── src/                  

&#x20;       ├── components/       # Componentes visuais reutilizáveis (Tabelas, Modais)

&#x20;       ├── pages/            # Telas do sistema (Dashboard, Aprovação)

&#x20;       └── services/         # Funções para consumir a API do backend

