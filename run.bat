@echo off
echo ===============================
echo LEITOR DE MATRICULAS - AUTOMATICO
echo ===============================

REM --- Ir para a pasta do .bat ---
cd /d %~dp0

REM --- Baixar foto do Raspberry Pi ---
echo Baixando foto do Raspberry Pi...
scp raspcam@10.1.26.181:/home/raspcam/matriculas/matricula.jpg "C:\Users\Utilizador\rodrigo\matricula.jpg"

REM --- Instalar bibliotecas (uma vez, se necessário) ---
echo -------------------------------
echo Instalando bibliotecas...
echo -------------------------------
pip install --upgrade pip
pip install -r requirements.txt

REM --- Ativar ambiente virtual ---
echo Ativando ambiente virtual...
call venv\Scripts\activate.bat

REM --- Executar script Python ---
echo Executando leitura de matricula...
python ler_matricula_imagem.py

echo ===============================
echo FIM
echo ===============================
pause
