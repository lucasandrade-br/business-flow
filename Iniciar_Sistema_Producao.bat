@echo off
setlocal

cd /d "%~dp0"

:: ── Lê PWA_SHORTCUT_PATH do .env ────────────────────────────────────────────
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

:: ── Validações ───────────────────────────────────────────────────────────────
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente virtual nao encontrado. Execute Instalar_Sistema.bat primeiro.
    pause & exit /b 1
)
if not exist "frontend\package.json" (
    echo Pasta frontend nao encontrada.
    pause & exit /b 1
)

call ".venv\Scripts\activate.bat"

:: ── Migrações por filial ─────────────────────────────────────────────────────
echo.
echo [1/4] Migrando banco Filial Centro...
set BUSINESS_FILIAL=centro
pushd backend
python manage.py migrate
if errorlevel 1 ( popd & echo Falha na migracao - Centro. & pause & exit /b 1 )
popd

echo [2/4] Migrando banco Filial Henrique...
set BUSINESS_FILIAL=henriques
pushd backend
python manage.py migrate
if errorlevel 1 ( popd & echo Falha na migracao - Henriques. & pause & exit /b 1 )
popd

:: ── Build do frontend ─────────────────────────────────────────────────────────
echo [3/4] Gerando build de producao do frontend...
pushd frontend
call npm run build
if errorlevel 1 ( popd & echo Falha ao gerar build do frontend. & pause & exit /b 1 )
popd

:: ── Pasta de logs ─────────────────────────────────────────────────────────────
if not exist "logs" mkdir logs

:: ── Inicia serviços em background (nesta janela, sem abrir novas) ────────────
echo [4/4] Iniciando servicos...

:: Gera scripts auxiliares no %TEMP% (sem espacos no caminho = sem conflito de aspas)
set BUSINESS_FILIAL=centro
> "%TEMP%\pd_centro.bat" (
    echo @echo off
    echo set BUSINESS_FILIAL=centro
    echo cd /d "%~dp0backend"
    echo "%~dp0.venv\Scripts\python.exe" -m waitress --listen=127.0.0.1:8001 core_project.wsgi:application ^>^> "%~dp0logs\api_centro.log" 2^>^&1
)

set BUSINESS_FILIAL=henriques
> "%TEMP%\pd_henriques.bat" (
    echo @echo off
    echo set BUSINESS_FILIAL=henriques
    echo cd /d "%~dp0backend"
    echo "%~dp0.venv\Scripts\python.exe" -m waitress --listen=127.0.0.1:8002 core_project.wsgi:application ^>^> "%~dp0logs\api_henriques.log" 2^>^&1
)

> "%TEMP%\pd_frontend.bat" (
    echo @echo off
    echo cd /d "%~dp0frontend"
    echo npm run preview -- --host 127.0.0.1 --port 4173 --strictPort ^>^> "%~dp0logs\frontend.log" 2^>^&1
)

start /b "" cmd /c "%TEMP%\pd_centro.bat"
start /b "" cmd /c "%TEMP%\pd_henriques.bat"
start /b "" cmd /c "%TEMP%\pd_frontend.bat"

:: Aguarda os serviços subirem
timeout /t 4 /nobreak > nul

:: ── Abre o PWA ─────────────────────────────────────────────────────────────────
if defined PWA_SHORTCUT_PATH (
    if exist "%PWA_SHORTCUT_PATH%" (
        start "" "%PWA_SHORTCUT_PATH%"
    ) else (
        echo Atalho PWA nao encontrado: %PWA_SHORTCUT_PATH%
        echo Abrindo no navegador como fallback...
        start http://127.0.0.1:4173
    )
) else (
    echo Variavel PWA_SHORTCUT_PATH nao definida no .env.
    echo Abrindo no navegador como fallback...
    start http://127.0.0.1:4173
)

:: ── Dashboard de status ───────────────────────────────────────────────────────
echo.
echo  ================================================================
echo   Sistema iniciado em modo producao local
echo   API Filial Centro    :  http://127.0.0.1:8001
echo   API Filial Henrique :  http://127.0.0.1:8002
echo   Frontend / PWA       :  http://127.0.0.1:4173
echo   Logs                 :  %~dp0logs\
echo  ================================================================
echo.
echo   Pressione qualquer tecla para ENCERRAR todos os servicos.
echo.
pause >nul

:: ── Encerra todos os serviços pelas portas ────────────────────────────────────
echo Encerrando servicos...
for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":8001 \|:8002 \|:4173 "') do (
    if not "%%p"=="" taskkill /f /pid %%p >nul 2>&1
)
del "%TEMP%\pd_centro.bat" 2>nul
del "%TEMP%\pd_henriques.bat" 2>nul
del "%TEMP%\pd_frontend.bat" 2>nul
echo Servicos encerrados.
endlocal

