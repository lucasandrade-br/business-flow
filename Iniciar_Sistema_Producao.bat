@echo off
setlocal

cd /d "%~dp0"

set "PWA_SHORTCUT_PATH="
if exist ".env" (
    for /f "usebackq eol=# tokens=1* delims==" %%A in (".env") do (
        if /i "%%~A"=="PWA_SHORTCUT_PATH" set "PWA_SHORTCUT_PATH=%%~B"
    )
)
if not defined PWA_SHORTCUT_PATH if exist "backend\.env" (
    for /f "usebackq eol=# tokens=1* delims==" %%A in ("backend\.env") do (
        if /i "%%~A"=="PWA_SHORTCUT_PATH" set "PWA_SHORTCUT_PATH=%%~B"
    )
)

if defined PWA_SHORTCUT_PATH (
    for %%I in ("%PWA_SHORTCUT_PATH%") do set "PWA_SHORTCUT_PATH=%%~I"
)

if not exist ".venv\Scripts\python.exe" (
    echo Ambiente virtual nao encontrado. Execute Instalar_Sistema.bat primeiro.
    exit /b 1
)

if not exist "frontend\package.json" (
    echo Pasta frontend nao encontrada.
    exit /b 1
)

call ".venv\Scripts\activate.bat"

pushd backend
python manage.py migrate
if errorlevel 1 (
    popd
    echo Falha ao executar migracoes do Django.
    exit /b 1
)
popd

pushd frontend
echo Executando build de producao do frontend...
call npm run build
if errorlevel 1 (
    popd
    echo Falha ao gerar build do frontend.
    exit /b 1
)
popd

start "API Django (Producao Local)" /D "%~dp0backend" cmd /k ""%~dp0.venv\Scripts\python.exe" -m waitress --listen=127.0.0.1:8000 core_project.wsgi:application"
start "Frontend PWA (Preview)" /D "%~dp0frontend" cmd /k "npm run preview -- --host 127.0.0.1 --port 4173 --strictPort"

if defined PWA_SHORTCUT_PATH (
    if exist "%PWA_SHORTCUT_PATH%" (
        start "PWA Business Flow" "%PWA_SHORTCUT_PATH%"
    ) else (
        echo Atalho PWA nao encontrado no caminho configurado: %PWA_SHORTCUT_PATH%
        echo Ajuste PWA_SHORTCUT_PATH no .env e execute novamente.
        echo Abrindo no navegador como fallback...
        start http://127.0.0.1:4173
    )
) else (
    echo Variavel PWA_SHORTCUT_PATH nao encontrada em .env ou backend\.env.
    echo Defina o caminho completo do atalho PWA para abertura automatica.
    echo Abrindo no navegador como fallback...
    start http://127.0.0.1:4173
)

echo Sistema iniciado em modo producao local.
endlocal
