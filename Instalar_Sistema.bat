@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt

if exist "frontend" (
    pushd frontend
    npm install
    popd
)

echo Instalacao concluida.
endlocal
