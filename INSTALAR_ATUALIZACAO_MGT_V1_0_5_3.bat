@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo  MGT - Atualizacao v1.0.5.3 - Correcao de Migrations
echo ============================================================
echo.

set "PROJECT_DIR=%~dp0"
if exist "%PROJECT_DIR%manage.py" goto :path_ok

set /p "PROJECT_DIR=Informe a pasta do projeto MGT que contem manage.py: "
if not defined PROJECT_DIR (
  echo ERRO: nenhuma pasta foi informada.
  pause
  exit /b 2
)
if not "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR%\"

:path_ok
if not exist "%PROJECT_DIR%manage.py" (
  echo ERRO: manage.py nao foi encontrado em "%PROJECT_DIR%".
  echo Execute este instalador na raiz do projeto ou informe a pasta correta.
  pause
  exit /b 3
)

set "STAMP=%DATE:~-4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "STAMP=%STAMP: =0%"
set "BACKUP_DIR=%PROJECT_DIR%backups\update_v1_0_5_3_%STAMP%"
set "LOG_DIR=%PROJECT_DIR%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\update_v1_0_5_3_%STAMP%.log"

echo Projeto: %PROJECT_DIR% > "%LOG_FILE%"
echo Backup: %BACKUP_DIR% >> "%LOG_FILE%"

echo [1/7] Criando backup dos arquivos afetados...
mkdir "%BACKUP_DIR%\core\migrations" >nul 2>&1
if exist "%PROJECT_DIR%core\migrations\0010_merge_0007_landinglead_0009_task_updates.py" copy /y "%PROJECT_DIR%core\migrations\0010_merge_0007_landinglead_0009_task_updates.py" "%BACKUP_DIR%\core\migrations\" >> "%LOG_FILE%" 2>&1
if exist "%PROJECT_DIR%core\migrations\0009_task_end_time_task_execution_date_task_planned_hours_and_more.py" copy /y "%PROJECT_DIR%core\migrations\0009_task_end_time_task_execution_date_task_planned_hours_and_more.py" "%BACKUP_DIR%\core\migrations\" >> "%LOG_FILE%" 2>&1

if exist "%PROJECT_DIR%.venv\Scripts\python.exe" (
  set "PYTHON=%PROJECT_DIR%.venv\Scripts\python.exe"
) else (
  where py >nul 2>&1 && (set "PYTHON=py") || (set "PYTHON=python")
)

echo [2/7] Instalando a migration de compatibilidade...
if /I "%PROJECT_DIR%"=="%~dp0" (
  echo Pacote executado na propria raiz; migration ja esta presente. >> "%LOG_FILE%"
) else (
  copy /y "%~dp0core\migrations\0009_task_end_time_task_execution_date_task_planned_hours_and_more.py" "%PROJECT_DIR%core\migrations\" >> "%LOG_FILE%" 2>&1
  if errorlevel 1 goto :fail
)

echo [3/7] Validando configuracao Django...
cd /d "%PROJECT_DIR%"
%PYTHON% manage.py check >> "%LOG_FILE%" 2>&1
if errorlevel 1 goto :fail

echo [4/7] Validando arvore de migrations...
%PYTHON% manage.py showmigrations core >> "%LOG_FILE%" 2>&1
if errorlevel 1 goto :fail

echo [5/7] Gerando plano de migrations...
%PYTHON% manage.py migrate --plan >> "%LOG_FILE%" 2>&1
if errorlevel 1 goto :fail

echo [6/7] Aplicando migrations...
%PYTHON% manage.py migrate >> "%LOG_FILE%" 2>&1
if errorlevel 1 goto :fail

echo [7/7] Coletando arquivos estaticos...
%PYTHON% manage.py collectstatic --noinput >> "%LOG_FILE%" 2>&1
if errorlevel 1 goto :fail

echo.
echo ATUALIZACAO CONCLUIDA COM SUCESSO.
echo Log: %LOG_FILE%
pause
exit /b 0

:fail
echo.
echo ERRO: atualizacao nao concluida. Consulte:
echo %LOG_FILE%
echo Use ROLLBACK_MGT_V1_0_5_3.bat para restaurar os arquivos afetados.
pause
exit /b 1
