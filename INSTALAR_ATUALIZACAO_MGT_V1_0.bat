@echo off
setlocal
cd /d %~dp0
if not exist .venv\Scripts\python.exe (
  echo Ambiente virtual nao encontrado. Usando Python do sistema.
  set PY=python
) else (
  set PY=.venv\Scripts\python.exe
)
%PY% -m pip install -r requirements.txt
if errorlevel 1 goto erro
%PY% manage.py migrate
if errorlevel 1 goto erro
%PY% manage.py collectstatic --noinput
if errorlevel 1 goto erro
echo.
echo Atualizacao MGT V1.0 instalada com sucesso.
pause
exit /b 0
:erro
echo.
echo Falha na instalacao. Verifique as mensagens acima.
pause
exit /b 1
