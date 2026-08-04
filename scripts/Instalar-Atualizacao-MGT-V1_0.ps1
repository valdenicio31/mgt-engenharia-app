$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$python = if (Test-Path '.venv/Scripts/python.exe') { '.venv/Scripts/python.exe' } else { 'python' }
& $python -m pip install -r requirements.txt
& $python manage.py migrate
& $python manage.py collectstatic --noinput
Write-Host 'Atualizacao MGT V1.0 instalada com sucesso.' -ForegroundColor Green
