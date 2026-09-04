@echo off
setlocal

cd /d "%~dp0"

:: ── Lê PWA_SHORTCUT_PATH do .env ────────────────────────────────────────────
set "PWA_SHORTCUT_PATH=C:\Users\emanu\Documents\Outros\Business Flow.lnk"
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

:: ── Inicia serviços em background (nesta janela, sem abrir novas) ────────────
echo [5/5] Iniciando servicos...

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


echo [3/5] Atualizando KPIs do dashboard...
set BUSINESS_FILIAL=centro
pushd backend
python manage.py refresh_dashboard_kpis 2>nul
python manage.py refresh_dashboard_kpis_compras 2>nul
python manage.py refresh_dre_consolidada 2>nul
python manage.py refresh_movimento_diario 2>nul
popd
set BUSINESS_FILIAL=henriques
pushd backend
python manage.py refresh_dashboard_kpis 2>nul
python manage.py refresh_dashboard_kpis_compras 2>nul
python manage.py refresh_dre_consolidada 2>nul
python manage.py refresh_movimento_diario 2>nul
popd

:: ── Pasta de logs ─────────────────────────────────────────────────────────────
if not exist "logs" mkdir logs


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

