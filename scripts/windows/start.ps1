$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$statePath = Join-Path $root 'storage\find-my-thingy-processes.json'
$logs = Join-Path $root 'storage\logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
if (-not (Test-Path (Join-Path $root 'backend\.venv\Scripts\python.exe')) -or -not (Test-Path (Join-Path $root 'frontend\node_modules\vite\bin\vite.js'))) { throw 'Dependencies are missing. Run Install-FindMyThingy.bat once first.' }
if (Test-Path $statePath) {
  try {
    $state=Get-Content -Raw $statePath | ConvertFrom-Json
    if ($state.backendUrl -and $state.frontendUrl) {
      Invoke-WebRequest "$($state.backendUrl)/api/health" -TimeoutSec 2 | Out-Null
      Invoke-WebRequest $state.frontendUrl -TimeoutSec 2 | Out-Null
      Start-Process $state.frontendUrl
      Write-Host "Find My Thingy is already running: $($state.frontendUrl)"
      return
    }
  } catch { }
  & (Join-Path $PSScriptRoot 'stop.ps1')
}
function Test-Port($port) { $listener=$null; try { $listener=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,$port); $listener.Start(); return $true } catch { return $false } finally { if ($listener) { $listener.Stop() } } }
function Find-FreePort($start) { for ($p=$start; $p -lt ($start+100); $p++) { if (Test-Port $p) { return $p } }; throw "No available port found near $start." }
$backendPort=Find-FreePort 8080
$frontendPort=Find-FreePort 5173
$backendUrl="http://127.0.0.1:$backendPort"
$frontendUrl="http://127.0.0.1:$frontendPort"
$ollamaCmd=Get-Command ollama -ErrorAction SilentlyContinue | Select-Object -First 1
$ollamaPath=if($ollamaCmd){$ollamaCmd.Source}else{Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'}
if (-not (Test-Path $ollamaPath)) { $ollamaPath=$null }
if ($ollamaPath) {
  try { Invoke-WebRequest 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2 | Out-Null } catch {
    Start-Process -FilePath $ollamaPath -ArgumentList 'serve' -WindowStyle Hidden -PassThru | Out-Null
    for ($i=0; $i -lt 10; $i++) { Start-Sleep -Seconds 1; try { Invoke-WebRequest 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2 | Out-Null; break } catch { } }
  }
}
$python=Join-Path $root 'backend\.venv\Scripts\python.exe'
$node=(Get-Command node -ErrorAction Stop).Source
$vite=Join-Path $root 'frontend\node_modules\vite\bin\vite.js'
$env:FRONTEND_ORIGIN=$frontendUrl
$backend=Start-Process -FilePath $python -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port',"$backendPort") -WorkingDirectory (Join-Path $root 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logs 'backend.log') -RedirectStandardError (Join-Path $logs 'backend-error.log')
try {
  $ready=$false
  for ($i=0; $i -lt 45; $i++) { Start-Sleep -Seconds 1; try { $h=Invoke-RestMethod "$backendUrl/api/health" -TimeoutSec 2; if ($h.backend -eq 'ok' -and $h.sqlite -eq 'ok') { $ready=$true; break } } catch { if ($backend.HasExited) { throw 'Backend stopped during startup. See storage/logs/backend-error.log.' } } }
  if (-not $ready) { throw 'Backend health check timed out. See storage/logs/backend-error.log.' }
  $backendServer=Get-CimInstance Win32_Process -Filter "ParentProcessId = $($backend.Id)" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match 'uvicorn\s+app\.main:app' -and $_.CommandLine -match "--port\s+$backendPort(?:\s|$)" } | Select-Object -First 1
  if (-not $backendServer) { $backendServer=Get-CimInstance Win32_Process -Filter "ProcessId = $($backend.Id)" -ErrorAction SilentlyContinue }
  if (-not $backendServer) { throw 'Could not identify the launched backend process for safe shutdown.' }
  if ($h.gemma_model -ne 'ok') { Write-Warning 'Local Gemma 3 4B is not ready. The app will open, but AI questions need Ollama and gemma3:4b. See docs/WINDOWS_SETUP.md.' }
  $env:VITE_API_URL="$backendUrl/api"
  $frontend=Start-Process -FilePath $node -ArgumentList @($vite,'--host','127.0.0.1','--port',"$frontendPort",'--strictPort') -WorkingDirectory (Join-Path $root 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logs 'frontend.log') -RedirectStandardError (Join-Path $logs 'frontend-error.log')
  $ready=$false
  for ($i=0; $i -lt 30; $i++) { Start-Sleep -Seconds 1; try { Invoke-WebRequest $frontendUrl -TimeoutSec 2 | Out-Null; $ready=$true; break } catch { if ($frontend.HasExited) { throw 'Frontend stopped during startup. See storage/logs/frontend-error.log.' } } }
  if (-not $ready) { throw 'Frontend HTTP check timed out. See storage/logs/frontend-error.log.' }
  @{backendPid=$backend.Id;backendServerPid=[int]$backendServer.ProcessId;backendUrl=$backendUrl;frontendPid=$frontend.Id;frontendUrl=$frontendUrl;root=$root} | ConvertTo-Json | Set-Content -Encoding UTF8 $statePath
  Start-Process $frontendUrl
  Write-Host "Find My Thingy is ready at $frontendUrl."
} catch {
  foreach ($proc in @($frontend,$backend)) { if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } }
  throw
}
