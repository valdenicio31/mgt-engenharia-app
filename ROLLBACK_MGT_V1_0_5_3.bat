@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
set "PROJECT_DIR=%~dp0"
if not exist "%PROJECT_DIR%manage.py" set /p "PROJECT_DIR=Informe a pasta do projeto MGT: "
if not defined PROJECT_DIR exit /b 2
if not "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR%\"
if not exist "%PROJECT_DIR%backups" (
 echo Nenhuma pasta de backup encontrada.
 pause
 exit /b 3
)
for /f "delims=" %%D in ('dir /b /ad /o-d "%PROJECT_DIR%backups\update_v1_0_5_3_*" 2^>nul') do (
 set "BACKUP=%PROJECT_DIR%backups\%%D"
 goto :found
)
:found
if not defined BACKUP (
 echo Nenhum backup da v1.0.5.3 foi encontrado.
 pause
 exit /b 4
)
if exist "%BACKUP%\core\migrations\0009_task_end_time_task_execution_date_task_planned_hours_and_more.py" (
 copy /y "%BACKUP%\core\migrations\0009_task_end_time_task_execution_date_task_planned_hours_and_more.py" "%PROJECT_DIR%core\migrations\" >nul
) else (
 del /q "%PROJECT_DIR%core\migrations\0009_task_end_time_task_execution_date_task_planned_hours_and_more.py" 2>nul
)
echo Rollback de arquivos concluido usando %BACKUP%.
echo Observacao: migrations ja aplicadas ao banco nao sao revertidas automaticamente.
pause
