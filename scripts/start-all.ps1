<#
.SYNOPSIS
  Starts the backend and dashboard, each under scripts\supervise.ps1
  (auto-restart + real crash logs in .\logs\). Additive to the manual
  commands in RUN.md - use whichever you prefer.

  Does NOT start behavioral-engine/ (port 3000) - that's a separate,
  pre-existing service outside the scope of this pass; add it here later
  if you want it supervised too.

  Invokes supervise.ps1 via `powershell -Command "& ... -ArgsJoined '...'"`
  rather than `-File ... -ArgsJoined ...` — verified live that passing a
  space-containing value (e.g. "-m uvicorn app.main:app --host 127.0.0.1
  --port 8000") through Start-Process's -ArgumentList array and then
  through -File's own CLI re-tokenization silently corrupts it (each word
  becomes a separate token, which supervise.ps1's param() block can't bind,
  so it exits before writing a single log line). A single pre-built
  -Command string sidesteps that: the child's own parser reads it once,
  correctly, as PowerShell source rather than reconstructed CLI tokens.
#>
$RepoRoot = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $RepoRoot "logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
}

$supervisePath = Join-Path $PSScriptRoot "supervise.ps1"

Write-Host "Starting backend (supervised, port 8000)..."
$backendCmd = "& '$supervisePath' -Name backend -WorkingDirectory '$RepoRoot\backend' -FilePath '$RepoRoot\backend\venv\Scripts\python.exe' -ArgsJoined '-m uvicorn app.main:app --host 127.0.0.1 --port 8000' -LogDir '$LogDir' -PythonPath '$RepoRoot;$RepoRoot\backend'"
Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -ArgumentList @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $backendCmd
)

Write-Host "Starting dashboard (supervised, port 5173)..."
$dashboardCmd = "& '$supervisePath' -Name dashboard -WorkingDirectory '$RepoRoot\dashboard' -FilePath 'npm.cmd' -ArgsJoined 'run dev' -LogDir '$LogDir'"
Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -ArgumentList @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $dashboardCmd
)

Start-Sleep -Seconds 2
Write-Host ""
Write-Host "Both launched under supervision. Logs: $LogDir"
Write-Host "  Get-Content '$LogDir\supervisor.log' -Tail 20 -Wait   # watch restarts live"
Write-Host "  .\scripts\stop-all.ps1                                # stop both"
