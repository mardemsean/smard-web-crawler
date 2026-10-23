<#
.SYNOPSIS
  SMard Web Crawler installer for Windows.
.DESCRIPTION
  Installs into %USERPROFILE%\.smard-crawler: a Python venv with the package, the Obscura
  stealth binary (checksum-verified), and a .env with generated tokens. Adds the venv
  Scripts folder to the user PATH so `smard-crawler` and `smard-crawler-mcp` resolve.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -WithCloak
#>
[CmdletBinding()]
param(
    [string]$Prefix = $(if ($env:SMARD_HOME) { $env:SMARD_HOME } else { Join-Path $env:USERPROFILE '.smard-crawler' }),
    [switch]$WithCloak,
    [switch]$WithDocker,
    [switch]$WithChromium,
    [switch]$NoObscura,
    [switch]$Dev
)
$ErrorActionPreference = 'Stop'
$RepoDir = Split-Path -Parent $PSScriptRoot
$ObscuraVersion = 'v0.2.5'
$ObscuraAsset = 'obscura-x86_64-windows-stealth.zip'
$ObscuraSha256 = '33c15a57c2c09e1bd8738bbb5d757107bded9749827d4248b7234d4bb5ed7303'

function Say($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }

# --- Python >= 3.12 -----------------------------------------------------------
$Py = $null
foreach ($cand in @(@('py', '-3.13'), @('py', '-3.12'), @('python'), @('python3'))) {
    try {
        $exe = $cand[0]; $pyArgs = @($cand | Select-Object -Skip 1)
        & $exe @pyArgs -c "import sys; sys.exit(sys.version_info < (3, 12))" 2>$null
        if ($LASTEXITCODE -eq 0) { $Py = $cand; break }
    } catch { }
}
if (-not $Py) { throw 'Python 3.12+ is required (https://www.python.org/downloads/)' }
$PyExe = $Py[0]; $PyArgs = @($Py | Select-Object -Skip 1)
Say ("Python: " + (& $PyExe @PyArgs --version))

New-Item -ItemType Directory -Force -Path $Prefix, (Join-Path $Prefix 'bin'), (Join-Path $Prefix 'output') | Out-Null

# --- Virtualenv + package -----------------------------------------------------
$Venv = Join-Path $Prefix 'venv'
$VPy = Join-Path $Venv 'Scripts\python.exe'
if (-not (Test-Path $VPy)) {
    Say "Creating virtualenv in $Venv"
    & $PyExe @PyArgs -m venv $Venv
}
& $VPy -m pip install --quiet --upgrade pip
$Extras = 'server,mcp,bench'
if ($WithCloak) { $Extras += ',cloak' }
if ($Dev) { $Extras += ',dev' }
Say "Installing smard-web-crawler[$Extras]"
$env:PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD = '1'
# Pinned versions for a reproducible install; skipped if the file is absent.
$Constraints = @()
if (Test-Path (Join-Path $RepoDir 'constraints.txt')) { $Constraints = @('-c', (Join-Path $RepoDir 'constraints.txt')) }
if ($Dev) { & $VPy -m pip install --quiet @Constraints -e "$RepoDir[$Extras]" }
else { & $VPy -m pip install --quiet @Constraints "$RepoDir[$Extras]" }
if ($LASTEXITCODE -ne 0) { throw 'pip install failed' }
Remove-Item Env:PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD
if ($WithChromium) { & $VPy -m playwright install chromium }

# --- Obscura stealth binary ---------------------------------------------------
$ObscuraBin = ''
if (-not $NoObscura) {
    $ObscuraBin = Join-Path $Prefix 'bin\obscura.exe'
    $current = if (Test-Path $ObscuraBin) { & $ObscuraBin --version 2>$null } else { '' }
    if ($current -notmatch [regex]::Escape($ObscuraVersion.TrimStart('v'))) {
        Say "Downloading Obscura $ObscuraVersion ($ObscuraAsset)"
        $zip = Join-Path $env:TEMP $ObscuraAsset
        Invoke-WebRequest -UseBasicParsing -OutFile $zip "https://github.com/h4ckf0r0day/obscura/releases/download/$ObscuraVersion/$ObscuraAsset"
        $got = (Get-FileHash -Algorithm SHA256 $zip).Hash.ToLower()
        if ($got -ne $ObscuraSha256) { throw "Obscura checksum mismatch: expected $ObscuraSha256, got $got" }
        Expand-Archive -Force -Path $zip -DestinationPath (Join-Path $Prefix 'bin')
        Remove-Item $zip
    }
    Say ("Obscura: " + (& $ObscuraBin --version))
}

# --- .env with generated secrets ---------------------------------------------
$EnvFile = Join-Path $Prefix '.env'
if (-not (Test-Path $EnvFile)) {
    Say "Writing $EnvFile (tokens generated; add proxy/Decodo credentials yourself)"
    Copy-Item (Join-Path $RepoDir '.env.example') $EnvFile
}
function New-Token { $b = New-Object byte[] 32; [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); -join ($b | ForEach-Object { $_.ToString('x2') }) }
$text = Get-Content -Raw $EnvFile
function Set-EnvValue([string]$Key, [string]$Value, [switch]$Force) {
    $pattern = "(?m)^$Key=(.*)$"
    $m = [regex]::Match($script:text, $pattern)
    if (-not $m.Success) { $script:text += "`n$Key=$Value`n" }
    elseif ($Force -or -not $m.Groups[1].Value.Trim()) { $script:text = [regex]::Replace($script:text, $pattern, "$Key=$($Value.Replace('$', '$$'))", 1) }
}
Set-EnvValue 'OBSCURA_CDP_TOKEN' (New-Token)
Set-EnvValue 'SMARD_API_TOKEN' (New-Token)
Set-EnvValue 'CRAWL4AI_API_TOKEN' (New-Token)
Set-EnvValue 'OBSCURA_CDP_URL' 'ws://127.0.0.1:9222'
if ($ObscuraBin) { Set-EnvValue 'OBSCURA_BIN' $ObscuraBin -Force }
if ($text -match '(?m)^OUTPUT_DIR=\./data/output') { Set-EnvValue 'OUTPUT_DIR' (Join-Path $Prefix 'output') -Force }
if ($WithCloak) { Set-EnvValue 'CLOAKBROWSER_ENABLED' 'true' -Force }
Set-Content -NoNewline -Path $EnvFile -Value $text
# Restrict the secrets file to the current user.
icacls $EnvFile /inheritance:r /grant:r "$($env:USERNAME):(R,W)" | Out-Null

# --- PATH ---------------------------------------------------------------------
$Scripts = Join-Path $Venv 'Scripts'
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if (($userPath -split ';') -notcontains $Scripts) {
    [Environment]::SetEnvironmentVariable('Path', "$Scripts;$userPath", 'User')
    Say "Added $Scripts to the user PATH (open a new terminal to pick it up)"
}
$env:Path = "$Scripts;$env:Path"

if ($WithDocker) {
    Say 'Starting Docker services (obscura, crawl4ai, api)'
    docker compose --project-directory $RepoDir --env-file $EnvFile up -d --build
}

Say 'Engine health:'
$env:SMARD_HOME = $Prefix
& (Join-Path $Scripts 'smard-crawler.exe') health

@"

Installed.
  CLI:        smard-crawler scrape https://example.com
  HTTP API:   smard-crawler serve            (http://127.0.0.1:8787, Bearer SMARD_API_TOKEN)
  MCP:        claude mcp add --scope user smard-crawler -- "$Scripts\smard-crawler-mcp.exe"
  Plugin:     /plugin marketplace add mardemsean/smard-web-crawler
              /plugin install smard-crawler@smard-labs
  Config:     $EnvFile
"@ | Write-Host
