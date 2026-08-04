<#
.SYNOPSIS
  Stops processes started by start-all.ps1. Kills both the supervised
  child (backend/dashboard) via its .pid file AND the supervise.ps1
  wrapper process itself, so it doesn't immediately restart what you just
  stopped.
#>
$RepoRoot = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $RepoRoot "logs"

# Stop the supervisor wrapper processes (any powershell.exe running
# supervise.ps1) so they don't restart the service the moment it's killed.
Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and $_.CommandLine -like "*supervise.ps1*" } |
    ForEach-Object {
        Write-Host "Stopping supervisor process (PID $($_.ProcessId))"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

foreach ($name in @("backend", "dashboard")) {
    $pidFile = Join-Path $LogDir "$name.pid"
    if (Test-Path $pidFile) {
        $procId = Get-Content $pidFile
        Write-Host "Stopping $name (PID $procId, with its process tree)"
        # Plain Stop-Process only kills the recorded PID; npm.cmd (dashboard)
        # spawns child node processes (npm-cli -> vite) that survive that and
        # keep the dev server up. taskkill /T kills the whole tree.
        taskkill /PID $procId /T /F 2>$null | Out-Null
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    } else {
        Write-Host "${name}: no .pid file found (not running under supervision?)"
    }
}

Write-Host "Done."
