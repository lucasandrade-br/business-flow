@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Ambiente virtual nao encontrado. Execute Instalar_Sistema.bat primeiro.
    exit /b 1
)

call ".venv\Scripts\activate.bat"

start "API Django" cmd /k "cd /d ""%~dp0backend"" && python -m waitress --listen=127.0.0.1:8000 core_project.wsgi:application"

if exist "%~dp0frontend" (
    start "Frontend Vue" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"
)

start http://localhost:5173

echo Sistema iniciado.
endlocal