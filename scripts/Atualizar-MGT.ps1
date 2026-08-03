$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$ProjectName = "MGT Engenharia"
$RepositoryUrl = "https://github.com/valdenicio31/mgt-engenharia-app.git"
$RenderUrl = "https://dashboard.render.com/"
$SourceDirectory = Split-Path -Parent $PSScriptRoot
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$WorkDirectory = Join-Path $env:TEMP "MGTDeploy-$Timestamp"
$RepositoryDirectory = Join-Path $WorkDirectory "mgt-engenharia-app"
$LogFile = Join-Path $SourceDirectory "MGT_Atualizacao_$Timestamp.log"

function Write-Step([string]$Message) {
    $line = "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Message
    Write-Host $line -ForegroundColor Cyan
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

function Find-Git {
    $command = Get-Command git.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    $knownPaths = @(
        "$env:ProgramFiles\Git\cmd\git.exe",
        "${env:ProgramFiles(x86)}\Git\cmd\git.exe",
        "$env:LOCALAPPDATA\Programs\Git\cmd\git.exe"
    )
    foreach ($path in $knownPaths) {
        if ($path -and (Test-Path $path)) { return $path }
    }

    $desktopGit = Get-ChildItem "$env:LOCALAPPDATA\GitHubDesktop" -Filter git.exe -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match "\\cmd\\git\.exe$" } |
        Sort-Object FullName -Descending |
        Select-Object -First 1
    if ($desktopGit) { return $desktopGit.FullName }
    return $null
}

function Invoke-Git([string[]]$Arguments, [string]$WorkingDirectory = $SourceDirectory) {
    Push-Location $WorkingDirectory
    try {
        # O Git envia progresso normal (como "Cloning into") pelo stderr.
        # No Windows PowerShell, ErrorActionPreference=Stop pode interpretar
        # esse progresso como uma exceção. Continue permite que o comando
        # termine; o resultado real é validado pelo código de saída.
        $previousPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            & $script:GitPath @Arguments 2>&1 | ForEach-Object {
                $text = $_.ToString()
                Write-Host $text
                Add-Content -Path $LogFile -Value $text -Encoding UTF8
            }
            $exitCode = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $previousPreference
        }
        if ($exitCode -ne 0) {
            throw "O Git retornou o código $exitCode ao executar: git $($Arguments -join ' ')"
        }
    }
    finally { Pop-Location }
}

try {
    "Atualização automática do $ProjectName - $Timestamp" | Set-Content -Path $LogFile -Encoding UTF8
    Write-Step "Localizando o Git no computador..."
    $script:GitPath = Find-Git
    if (-not $script:GitPath) {
        Write-Host "Git não encontrado. A página oficial de instalação será aberta." -ForegroundColor Yellow
        Start-Process "https://git-scm.com/download/win"
        throw "Instale o Git para Windows e execute este atualizador novamente."
    }

    Write-Step "Git localizado: $script:GitPath"
    Write-Step "Criando área temporária segura: $WorkDirectory"
    New-Item -ItemType Directory -Path $WorkDirectory -Force | Out-Null

    Write-Step "Baixando a versão atual do repositório..."
    Invoke-Git @("clone", $RepositoryUrl, $RepositoryDirectory) $WorkDirectory

    Write-Step "Copiando os arquivos novos da aplicação..."
    $ExcludedNames = @(".git", ".venv", "db.sqlite3", "media", "staticfiles", "__pycache__")
    Get-ChildItem -Path $SourceDirectory -Force | Where-Object {
        $_.Name -notin $ExcludedNames -and $_.Extension -ne ".zip" -and $_.Name -notlike "MGT_Atualizacao_*.log"
    } | ForEach-Object {
        Copy-Item -Path $_.FullName -Destination $RepositoryDirectory -Recurse -Force
    }

    Write-Step "Analisando as alterações antes do envio..."
    $status = & $script:GitPath -C $RepositoryDirectory status --porcelain
    if (-not $status) {
        Write-Host "Nenhuma alteração nova foi encontrada. O GitHub já está atualizado." -ForegroundColor Green
        Start-Process $RenderUrl
        exit 0
    }
    $status | Tee-Object -FilePath $LogFile -Append | Write-Host

    Write-Step "Preparando os arquivos e criando o registro da atualização..."
    Invoke-Git @("add", "--all") $RepositoryDirectory
    Invoke-Git @("commit", "-m", "Fase 25: cadastros, importacao e atualizacao automatica") $RepositoryDirectory

    $branch = (& $script:GitPath -C $RepositoryDirectory branch --show-current).Trim()
    if (-not $branch) { throw "Não foi possível identificar a ramificação do GitHub." }

    Write-Step "Enviando a atualização para o GitHub ($branch)..."
    Invoke-Git @("push", "origin", $branch) $RepositoryDirectory

    Write-Step "Atualização publicada. O Render iniciará o deploy automático."
    Write-Host "" 
    Write-Host "SUCESSO: a Fase 25 foi enviada ao GitHub." -ForegroundColor Green
    Write-Host "O navegador será aberto no painel do Render." -ForegroundColor Green
    Start-Process $RenderUrl
    exit 0
}
catch {
    $message = $_.Exception.Message
    Add-Content -Path $LogFile -Value "ERRO: $message" -Encoding UTF8
    Write-Host "" 
    Write-Host "ERRO: $message" -ForegroundColor Red
    Write-Host "Relatório salvo em: $LogFile" -ForegroundColor Yellow
    exit 1
}
