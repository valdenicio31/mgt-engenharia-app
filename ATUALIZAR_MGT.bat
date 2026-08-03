@echo off
setlocal
chcp 65001 >nul
title Atualizador MGT Engenharia - VIA IA
cd /d "%~dp0"

echo ==========================================================
echo       ATUALIZADOR AUTOMATICO - MGT ENGENHARIA
echo                    VIA IA 2026
echo ==========================================================
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Atualizar-MGT.ps1"
set "RESULTADO=%ERRORLEVEL%"

echo.
if "%RESULTADO%"=="0" (
  echo Atualizacao enviada ao GitHub com sucesso.
) else (
  echo A atualizacao nao foi concluida. Leia a mensagem acima.
)
echo.
pause
exit /b %RESULTADO%
