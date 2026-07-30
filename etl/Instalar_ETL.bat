@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "VENV_DIR=.venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo Criando ambiente virtual do ETL em "%CD%\%VENV_DIR%"...
    py -3 -m venv "%VENV_DIR%" 2>nul
    if errorlevel 1 (
        python -m venv "%VENV_DIR%"
        if errorlevel 1 (
            echo Falha ao criar ambiente virtual. Verifique se o Python esta instalado.
            exit /b 1
        )
    )
)

if not exist "requirements.txt" (
    echo Arquivo requirements.txt nao encontrado em "%CD%".
    exit /b 1
)

"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 (
    echo Falha ao atualizar pip no ambiente virtual do ETL.
    exit /b 1
)

"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Falha ao instalar dependencias do ETL.
    exit /b 1
)

echo.
echo Dependencias do ETL instaladas com sucesso.
echo Para ativar o ambiente depois:
echo   call "%VENV_DIR%\Scripts\activate.bat"

endlocal
