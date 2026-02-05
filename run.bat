@echo off
title OCR MATRICULAS - AUTO
set BASE=%~dp0

echo ===============================
echo   OCR MATRICULAS - AUTO SETUP
echo ===============================
echo.

REM Criar pasta python se nao existir
if not exist "%BASE%python" (
    echo [1/5] A fazer download do Python 3.11 portatil...
    powershell -Command ^
     "Invoke-WebRequest https://www.python.org/ftp/python/3.11.8/python-3.11.8-embed-amd64.zip -OutFile python.zip"

    mkdir python
    powershell -Command ^
     "Expand-Archive python.zip python"

    del python.zip
)

REM Corrigir python311._pth
echo [2/5] A configurar Python...
(
echo .
echo Lib
echo Lib\site-packages
echo import site
) > "%BASE%python\python311._pth"

set PYTHON=%BASE%python\python.exe

echo.
echo [3/5] A instalar pip...
%PYTHON% -m ensurepip --default-pip

echo.
echo [4/5] A instalar bibliotecas (pode demorar)...
%PYTHON% -m pip install --upgrade pip
%PYTHON% -m pip install -r "%BASE%app\requirements.txt"

echo.
echo [5/5] A executar programa...
cd /d "%BASE%app"
%PYTHON% ler_matricula_ip.py

echo.
pause
