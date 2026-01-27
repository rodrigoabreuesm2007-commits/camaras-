@echo off
echo ===============================
echo LEITOR DE MATRICULAS - SETUP
echo ===============================

REM garantir que estamos na pasta certa
cd /d %~dp0

REM verificar se o Python existe
python --version
IF ERRORLEVEL 1 (
    echo Python nao encontrado.
    echo Instala o Python primeiro.
    pause
    exit
)

echo -------------------------------
echo Instalando bibliotecas...
echo -------------------------------
pip install --upgrade pip
pip install -r requirements.txt

echo -------------------------------
echo Executando o programa...
echo -------------------------------
python ler_matricula_imagem.py

pause
