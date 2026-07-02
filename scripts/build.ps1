# Transcribe Studio — install (Grok-style one-liner)
#   irm https://raw.githubusercontent.com/Mishkat-Quantum-Labs/transcribe-studio/main/scripts/build.ps1 | iex
# Then in any new PowerShell window:
#   transcribe

$ErrorActionPreference = "Stop"

# Python 3.13 + Windows: prevent _pyrepl WinError 123 in Cursor/integrated terminals
$env:PYTHON_BASIC_REPL = "1"
$env:PIP_NO_INPUT = "1"
[Environment]::SetEnvironmentVariable("PYTHON_BASIC_REPL", "1", "User")

function Write-Step($msg) { Write-Host "  $msg" -ForegroundColor Cyan }

function Add-UserPath([string]$Dir) {
    if (-not $Dir -or -not (Test-Path $Dir)) { return }
    $dir = $Dir.TrimEnd('\')
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $parts = $userPath -split ';' | Where-Object { $_ -and $_ -ne $dir }
    if ($userPath -notlike "*$dir*") {
        [Environment]::SetEnvironmentVariable("Path", "$dir;" + ($parts -join ';'), "User")
    }
    if ($env:Path -notlike "*$dir*") { $env:Path = "$dir;$env:Path" }
}

Write-Host ""
Write-Host "  Transcribe Studio" -ForegroundColor Green
Write-Host "  Install once. Run with: transcribe" -ForegroundColor DarkGray
Write-Host ""

# Python 3.11+
$py = $null
foreach ($cmd in @("python", "python3", "py")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { continue }
    if ($cmd -eq "py") {
        foreach ($v in @("3.13", "3.12", "3.11")) {
            $null = & py "-$v" -c "import sys" 2>$null
            if ($LASTEXITCODE -eq 0) { $py = "py -$v"; break }
        }
    } else {
        $ver = & $cmd -c "import sys; print(sys.version_info.minor)" 2>$null
        if ($LASTEXITCODE -eq 0 -and [int]$ver -ge 11) { $py = $cmd; break }
    }
    if ($py) { break }
}

if (-not $py) {
    Write-Host "  Python 3.11+ required: https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

function Invoke-Py([string[]]$PyArgs) {
    if ($py -like "py -*") {
        $p = $py.Split(" ", 2)
        & $p[0] $p[1] @PyArgs
    } else {
        & $py @PyArgs
    }
}

Write-Step "Python: $py"
Write-Step "Installing transcribe-studio (pipx)..."

# Detect Microsoft Store Python (common source of hangs/slow installs)
$pyExe = $null
try { $pyExe = (Invoke-Py @("-c", "import sys; print(sys.executable)")) 2>$null } catch {}
if ($pyExe -and $pyExe -match 'WindowsApps\\Python') {
    Write-Host "  NOTE: Using Microsoft Store Python (sandboxed)." -ForegroundColor Yellow
    Write-Host "  Installs can be slow or restricted. For best results use the full" -ForegroundColor Yellow
    Write-Host "  installer from https://www.python.org/downloads/ (uncheck 'Add python.exe to PATH' alias)." -ForegroundColor Yellow
}

Write-Host "  Upgrading pip + installing pipx + wheel..." -ForegroundColor DarkGray
Write-Host "  (first run often takes 30s–3 minutes while downloading packages from PyPI)" -ForegroundColor DarkGray
# Use --user for pipx (recommended and more reliable on restricted Pythons like MS Store)
Invoke-Py @("-m", "pip", "install", "--user", "--upgrade", "--quiet", "--disable-pip-version-check", "pip", "pipx", "wheel") 2>&1 | Out-Null

if (-not (Get-Command pipx -ErrorAction SilentlyContinue)) {
    Invoke-Py @("-m", "pipx", "ensurepath", "--force") 2>&1 | Out-Null
}

$pipxPaths = @(
    (Join-Path $env:USERPROFILE ".local\bin")
    (Join-Path $env:USERPROFILE "AppData\Roaming\Python\Python313\Scripts")
    (Join-Path $env:USERPROFILE "AppData\Roaming\Python\Python312\Scripts")
    (Join-Path $env:USERPROFILE "AppData\Roaming\Python\Python311\Scripts")
    (Join-Path $env:USERPROFILE ".local\pipx\venvs\transcribe-studio\Scripts")
)
foreach ($p in $pipxPaths) { Add-UserPath $p }

Write-Host "  Running pipx install for transcribe-studio..." -ForegroundColor DarkGray
Write-Host "  (creating isolated venv + downloading the app - another 30-90s typical)" -ForegroundColor DarkGray
# Let pipx output its progress (creating venv, installing, done!) so the user sees activity
if (Get-Command pipx -ErrorAction SilentlyContinue) {
    pipx install transcribe-studio --force
} else {
    Invoke-Py @("-m", "pipx", "install", "transcribe-studio", "--force")
}
if ($LASTEXITCODE -ne 0) {
    Write-Step "pipx failed — using pip --user"
    Invoke-Py @("-m", "pip", "install", "--user", "--upgrade", "transcribe-studio") | Out-Null
    $userScripts = Join-Path $env:APPDATA "Python\Python313\Scripts"
    if (-not (Test-Path $userScripts)) {
        $userScripts = Join-Path $env:USERPROFILE "AppData\Roaming\Python\Python313\Scripts"
    }
    Add-UserPath $userScripts
}

try {
    if (Get-Command pipx -ErrorAction SilentlyContinue) {
        pipx ensurepath --force 2>&1 | Out-Null
    } else {
        Invoke-Py @("-m", "pipx", "ensurepath", "--force") 2>&1 | Out-Null
    }
} catch { }

foreach ($p in $pipxPaths) { Add-UserPath $p }

Write-Host ""
Write-Host "  ✓ Installed." -ForegroundColor Green
Write-Host ""
Write-Host "  Close this window, open a new PowerShell, then type:" -ForegroundColor White
Write-Host ""
Write-Host "    transcribe" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Opens http://127.0.0.1:8082 (foreground — Ctrl+C to stop)" -ForegroundColor DarkGray
Write-Host ""