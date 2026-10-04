$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$statePath = Join-Path $root 'storage\find-my-thingy-processes.json'
if (-not (Test-Path $statePath)) { Write-Host 'Find My Thingy is not running (no launcher state found).'; exit 0 }
$state=Get-Content -Raw $statePath | ConvertFrom-Json
$front=Get-CimInstance Win32_Process -Filter "ProcessId = $($state.frontendPid)" -ErrorAction SilentlyContinue
$vitePath=(Join-Path $root 'frontend\node_modules\vite\bin\vite.js')
if ($front -and $front.CommandLine -like "*$vitePath*") { Stop-Process -Id ([int]$front.ProcessId) -Force -ErrorAction SilentlyContinue }
elseif ($state.frontendPid) { Write-Host "Skipped PID $($state.frontendPid): it no longer matches this project's Vite process." }
$backendPort=([uri]$state.backendUrl).Port
$serverPid=if($state.backendServerPid){[int]$state.backendServerPid}else{
  $child=Get-CimInstance Win32_Process -Filter "ParentProcessId = $($state.backendPid)" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match 'uvicorn\s+app\.main:app' -and $_.CommandLine -match "--port\s+$backendPort(?:\s|$)" } | Select-Object -First 1
  if($child){[int]$child.ProcessId}else{[int]$state.backendPid}
}
$server=Get-CimInstance Win32_Process -Filter "ProcessId = $serverPid" -ErrorAction SilentlyContinue
$backendLauncher=Get-CimInstance Win32_Process -Filter "ProcessId = $($state.backendPid)" -ErrorAction SilentlyContinue
$matchesServer=$server -and $server.CommandLine -match 'uvicorn\s+app\.main:app' -and $server.CommandLine -match "--port\s+$backendPort(?:\s|$)"
if ($matchesServer -and ($server.ProcessId -eq $state.backendPid -or $server.ParentProcessId -eq $state.backendPid) -and $backendLauncher -and $backendLauncher.ExecutablePath -like "$root\backend\.venv\Scripts\python.exe") {
  if ($server.ProcessId -ne $state.backendPid) { Stop-Process -Id $serverPid -Force -ErrorAction SilentlyContinue }
  Stop-Process -Id ([int]$state.backendPid) -Force -ErrorAction SilentlyContinue
} elseif ($state.backendPid) { Write-Host "Skipped backend PID $serverPid`: its process tree no longer matches this launch." }
Remove-Item -LiteralPath $statePath -Force
Write-Host 'Find My Thingy processes started by this launcher have been stopped.'
