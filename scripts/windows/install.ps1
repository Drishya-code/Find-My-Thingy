$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Find My Thingy Windows scripts can run only on Windows.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
function Find-Command($name) { Get-Command $name -ErrorAction SilentlyContinue | Select-Object -First 1 }
$py = Find-Command 'py'
$python = Find-Command 'python'
if ($py) {
  $pyVersionCode = & $py.Source -3.12 -c 'import sys; print(sys.version_info[0]*100+sys.version_info[1])' 2>$null
  if ($LASTEXITCODE -eq 0 -and [int]$pyVersionCode -eq 312) { $pythonCommand = $py.Source; $pythonArgs = @('-3.12') }
}
if (-not $pythonCommand -and $python) {
  $pyVersionCode = & $python.Source -c 'import sys; print(sys.version_info[0]*100+sys.version_info[1])' 2>$null
  if ($LASTEXITCODE -eq 0 -and [int]$pyVersionCode -eq 312) { $pythonCommand = $python.Source; $pythonArgs = @() }
}
if (-not $pythonCommand) { throw 'Python 3.12 is required by the pinned backend dependencies. Install Python 3.12 and rerun this installer.' }
$node = Find-Command 'node'
$npm = Find-Command 'npm'
if (-not $node -or -not $npm) { throw 'Node.js 20.19+ or 22.12+ with npm is required. Install the current Node.js LTS release.' }
$npmCmd = Find-Command 'npm.cmd'
$npmPath = if ($npmCmd) { $npmCmd.Source } else { $npm.Source }
$nodeVersion = [version]((& $node.Source --version).TrimStart('v'))
if ($nodeVersion -lt [version]'20.19' -and $nodeVersion -lt [version]'22.12') { throw "Node.js 20.19+ or 22.12+ is required. Detected $nodeVersion." }
$ollama = Find-Command 'ollama'
$ollamaPath = if ($ollama) { $ollama.Source } else { Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe' }
if (-not (Test-Path $ollamaPath)) { $ollamaPath=$null }
$ollamaTags = $null
try { $ollamaTags=Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 3 } catch { }
if (-not $ollamaPath -and -not $ollamaTags) { Write-Warning 'Ollama CLI/API was not found. Install it from https://ollama.com/download before using local AI.' }
$venv = Join-Path $root 'backend\.venv'
if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) { & $pythonCommand @pythonArgs -m venv $venv; if ($LASTEXITCODE) { throw 'Could not create the backend virtual environment.' } }
& (Join-Path $venv 'Scripts\python.exe') -m pip install -r (Join-Path $root 'backend\requirements.txt')
if ($LASTEXITCODE) { throw 'Backend dependency installation failed.' }
Push-Location (Join-Path $root 'frontend')
try { & $npmPath ci; if ($LASTEXITCODE) { throw 'Frontend dependency installation failed.' } } finally { Pop-Location }
foreach ($dir in @('storage','storage\uploads','storage\chroma','storage\models','storage\logs')) { New-Item -ItemType Directory -Force -Path (Join-Path $root $dir) | Out-Null }
$envFile = Join-Path $root '.env'
if (-not (Test-Path $envFile)) { Copy-Item (Join-Path $root '.env.example') $envFile }
if (-not (Test-Path (Join-Path $root 'frontend\.env'))) { Copy-Item (Join-Path $root 'frontend\.env.example') (Join-Path $root 'frontend\.env') }
if ($ollamaTags) {
  if (-not ($ollamaTags.models.name -contains 'gemma3:4b' -or $ollamaTags.models.name -contains 'gemma3:4b-instruct-q4_K_M')) {
    if ($ollamaPath) {
      $answer=Read-Host 'Gemma 3 4B is missing. Download gemma3:4b now? This can be a large download (Y/N)'
      if ($answer -match '^[Yy]') { & $ollamaPath pull gemma3:4b; if ($LASTEXITCODE) { throw 'Ollama model download failed.' } }
    } else { Write-Warning 'Ollama is reachable but its CLI is not on PATH, so the missing Gemma model must be installed from Ollama manually.' }
  }
} elseif ($ollamaPath) {
  Write-Host 'Ollama is installed but is not currently running. Start it from its normal Windows app before launching Find My Thingy.'
}
& (Join-Path $venv 'Scripts\python.exe') -c 'import fastapi, chromadb, sentence_transformers'
if ($LASTEXITCODE) { throw 'Backend installation verification failed.' }
Write-Host 'Checking local all-MiniLM-L6-v2 embedding model. The first install downloads it into storage/models; later installs load the cached model.' -ForegroundColor Cyan
Push-Location (Join-Path $root 'backend')
try {
  @'
from app.services.embeddings import encode
vectors = encode(["Find My Thingy local model verification."])
assert len(vectors) == 1 and len(vectors[0]) > 0
assert all(abs(value) < float("inf") for value in vectors[0])
print("Embedding model loaded locally and generated a test vector.")
'@ | & (Join-Path $venv 'Scripts\python.exe') -
  if ($LASTEXITCODE) { throw 'Embedding model setup failed. Check internet access and storage/models, then rerun the installer; model downloads can resume.' }
} finally { Pop-Location }
Write-Host 'Python 3.12, frontend packages, local storage and embedding model are ready.' -ForegroundColor Green
