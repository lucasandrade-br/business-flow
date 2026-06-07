# **Documento Base de Conhecimento: Operações, Qualidade e Distribuição**

###### **1. Visão Geral Operacional**

A camada operacional define como o software se comporta em produção no ambiente local (máquinas Windows com acesso à internet). O objetivo é garantir que o sistema seja facilmente instalável, resiliente a falhas temporárias (como quedas de rede durante o ETL) e auditável através de registros de atividades.



###### **2. Qualidade e Prevenção de Regressões (QA)**

Para evitar que futuras atualizações quebrem regras de negócio críticas, o desenvolvimento adotará uma política de Testes Unitários Automatizados.

Ferramenta: pytest (Ecossistema Python/Django).

Foco de Cobertura: \* Camada SPEC: Validação estrita das regras de negócio (ex: cálculo de Markup, validação de máscaras de códigos com zero-padding).

Padrão Repository: Garantir que o BaseAccessRepository gere as instruções SQL dinâmicas corretamente e rejeite dados com tipagem incorreta antes da comunicação com o ODBC.

Execução: Os testes devem ser rodados localmente pelo desenvolvedor antes de qualquer commit na branch principal (Main/Master) do repositório.



###### **3. Observabilidade e Rastreamento (Logs Corporativos)**

Falhas silenciosas são inaceitáveis. O sistema possuirá uma arquitetura de rastreamento de eventos para facilitar manutenções e auditorias futuras.

Ferramenta: Módulo nativo logging do Python.

Política de Rotação (Log Rotation): O sistema criará arquivos físicos diários (ex: logs/sistema\_2026-06-04.log). Para evitar o consumo excessivo de disco, os arquivos com mais de 30 dias serão expurgados automaticamente.

Eventos Rastreados (Níveis de Log):

INFO: Início e término de extrações bem-sucedidas do ETL (Firebird -> Access) e logins de usuários.

WARNING: Divergências de estrutura ou tentativas de acesso negado.

ERROR: Quedas de conexão com o banco .FDB, falhas de leitura/escrita no arquivo .accdb e exceções não tratadas na API.



###### **4. Segurança e Controle de Acesso (Autenticação e RBAC)**

A governança de dados exige rastreabilidade de quem aprova e modifica as informações no banco SOT.

Motor Base: Sistema de Autenticação nativo do Django (django.contrib.auth).

Fase 1 (V1): Implementação de Login básico. Todos os usuários logados compartilham o mesmo nível de permissão. O ID do usuário logado será capturado e gravado no campo OPERADOR/USUARIO das tabelas de auditoria durante as ações.

Fase 2 (Escalabilidade RBAC - Role-Based Access Control): O sistema utilizará os Grupos nativos do Django (ex: "Operadores", "Gerentes"). As rotas da API (views.py) serão protegidas por decoradores (@permission\_required), garantindo que ações destrutivas ou aprovações críticas sejam bloqueadas em nível de back-end para contas sem o privilégio adequado.



###### **5. Empacotamento e Distribuição (Deploy Local)**

Como o sistema não será hospedado em infraestrutura de nuvem, a implantação nas máquinas locais será abstraída do usuário final através de automação via scripts de lote (Batch/PowerShell) do Windows. Os computadores alvo possuem acesso à internet.

Script 1: Instalar\_Sistema.bat (Setup Único)

Criação do ambiente virtual Python (python -m venv venv).

Instalação de dependências do back-end (pip install -r requirements.txt).

Instalação de pacotes do front-end (npm install).

Execução das migrações iniciais do SQLite do Django (python manage.py migrate).

Script 2: Iniciar\_Sistema.bat (Uso Diário)

Ativação silenciada dos servidores.

Inicialização da API Django utilizando o servidor Waitress (robusto para produção em ambiente Windows, substituindo o servidor de desenvolvimento nativo do Django).

Inicialização do servidor estático do Front-end (Vite/PWA).

Abertura automática do navegador padrão apontando para a interface do software (escondendo terminais CMD do usuário).

