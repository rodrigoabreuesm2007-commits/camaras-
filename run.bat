@echo off
setlocal EnableDelayedExpansion

REM Garantir que o script corre na pasta certa
cd /d "%~dp0"

title OCR MATRICULAS - AUTO

echo ===============================
echo   OCR MATRICULAS - AUTO SETUP
echo ===============================
echo Pasta atual:
echo %cd%
echo.

set BASE=%cd%
set PYTHON_DIR=%BASE%\python
set PYTHON_EXE=%PYTHON_DIR%\python.exe

REM ===============================
REM 1 - DOWNLOAD PYTHON PORTATIL
REM ===============================
if not exist "%PYTHON_EXE%" (
    echo [1/5] A fazer download do Python 3.11 portatil...

    powershell -Command ^
     "Invoke-WebRequest -Uri https://www.python.org/ftp/python/3.11.8/python-3.11.8-embed-amd64.zip -OutFile '%BASE%\python.zip'"

    mkdir "%PYTHON_DIR%"
    powershell -Command ^
     "Expand-Archive '%BASE%\python.zip' '%PYTHON_DIR%' -Force"

    del "%BASE%\python.zip"
)

REM ===============================
REM 2 - CONFIGURAR PYTHON
REM ===============================
echo [2/5] A configurar Python...

(
echo .
echo Lib
echo Lib\site-packages
echo import site
) > "%PYTHON_DIR%\python311._pth"

REM ===============================
REM 3 - INSTALAR PIP
REM ===============================
echo [3/5] A instalar pip...
"%PYTHON_EXE%" -m ensurepip --default-pip

REM ===============================
REM 4 - INSTALAR BIBLIOTECAS
REM ===============================
echo [4/5] A instalar bibliotecas...
"%PYTHON_EXE%" -m pip install --upgrade pip
"%PYTHON_EXE%" -m pip install -r "%BASE%\app\requirements.txt"

REM ===============================
REM 5 - EXECUTAR PROGRAMA
REM ===============================
echo [5/5] A executar programa...
cd /d "%BASE%\app"
"%PYTHON_EXE%" ler_matricula_ip.py

echo.
pause
