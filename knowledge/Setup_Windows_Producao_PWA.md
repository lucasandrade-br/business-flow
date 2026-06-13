# Setup completo em outra maquina Windows (ZIP + GitHub)

Este guia cobre o fluxo completo para rodar o sistema em outra maquina Windows com:
- backend Django + MySQL
- frontend Vue em build de producao
- execucao local em modo PWA (porta 4173)

## 1) Pre-requisitos da maquina

Instale os itens abaixo antes de iniciar:

1. Python 3.11 (x64)
2. Node.js 20 LTS (ou superior compativel com Vite 5)
3. MySQL Server 8.0+
4. Microsoft Visual C++ Redistributable x64
5. (Opcional) Git para atualizacoes futuras

Observacao importante sobre Firebird:
- O sistema le dados de um arquivo Firebird (.fdb/.gdb/.fbk)
- Garanta acesso ao arquivo na maquina
- Se necessario, configure FDB_CLIENT_LIB_PATH no .env para apontar para fbclient.dll

## 2) Baixar e descompactar o projeto

1. Baixe o ZIP do repositorio no GitHub
2. Extraia para uma pasta local, por exemplo:
   C:\Sistemas\BusinessFlow

## 3) Preparar o MySQL

Conecte no MySQL e execute:

```sql
CREATE DATABASE business_flow CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'business_flow'@'localhost' IDENTIFIED BY 'troque_sua_senha';
GRANT ALL PRIVILEGES ON business_flow.* TO 'business_flow'@'localhost';
FLUSH PRIVILEGES;
```

Se preferir usar root, tambem funciona (ajuste no .env).

## 4) Criar arquivo de configuracao backend/.env

Dentro da pasta backend, crie um arquivo chamado .env com este modelo:

```env
SECRET_KEY=troque_esta_chave
DEBUG=False

DB_NAME=business_flow
DB_USER=business_flow
DB_PASSWORD=troque_sua_senha
DB_HOST=127.0.0.1
DB_PORT=3306

FDB_HOST=
FDB_PORT=3050
FDB_USER=SYSDBA
FDB_PASS=masterkey
FDB_PATH=
FDB_CLIENT_LIB_PATH=

# Caminho completo do atalho PWA (arquivo .lnk) criado apos instalar o app no navegador.
PWA_SHORTCUT_PATH=C:\Users\SEU_USUARIO\Desktop\Business Flow.lnk
```

Notas:
- Se usar modo dinamico no sistema, FDB_PATH pode ficar vazio.
- Se usar modo fixo, informe FDB_PATH com caminho completo do arquivo Firebird.

## 5) Instalar dependencias do projeto

No diretorio raiz do projeto, execute:

1. Instalar_Sistema.bat

Esse script faz:
- cria .venv (se nao existir)
- instala dependencias Python do backend
- instala dependencias Node do frontend

## 6) Aplicar migracoes

Opcao manual (recomendada na primeira vez):

```bat
cd backend
..\.venv\Scripts\python.exe manage.py migrate
```

## 7) Gerar build do frontend (producao)

```bat
cd frontend
npm run build
```

Isso cria a pasta frontend/dist.

## 8) Iniciar em modo producao local (PWA)

Use o arquivo:

- Iniciar_Sistema_Producao.bat

Esse arquivo:
1. valida ambiente
2. executa migracoes
3. gera build de producao do frontend
4. sobe API Django (waitress) na porta 8000
5. sobe frontend em preview na porta 4173
6. abre o atalho PWA configurado em PWA_SHORTCUT_PATH (em vez do navegador)
7. se o atalho nao estiver configurado ou nao existir, abre no navegador como fallback

## 9) Instalar como PWA no Windows

1. Abra http://127.0.0.1:4173
2. No navegador (Edge/Chrome), clique em "Instalar aplicativo"
3. O app abre em janela separada (modo PWA)

## 10) Checklist de validacao rapida

1. API online: http://127.0.0.1:8000/api/integracao/firebird-config
2. Frontend online: http://127.0.0.1:4173
3. Em Sistema > Conexao Firebird:
   - salve modo FIXED ou DYNAMIC
4. Teste sincronizacao dos 3 fluxos

## 11) Problemas comuns

1. Erro ao instalar mysqlclient
- Instale Visual C++ Redistributable x64
- Garanta Python x64

2. Erro de conexao MySQL
- revise DB_HOST/DB_PORT/DB_USER/DB_PASSWORD no backend/.env
- confirme se o servico MySQL esta ativo

3. Frontend nao abre em 4173
- confirme se a porta esta livre
- execute novamente Iniciar_Sistema_Producao.bat

4. Erro com Firebird
- confirme permissao de leitura no arquivo .fdb
- em modo dinamico, selecione o arquivo correto
- se necessario configure FDB_CLIENT_LIB_PATH

## 12) Fluxo para atualizacoes futuras

Quando baixar nova versao (ZIP novo):

1. substitua os arquivos do projeto
2. execute Instalar_Sistema.bat
3. execute Iniciar_Sistema_Producao.bat

