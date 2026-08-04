<#
.SYNOPSIS
  Generic process supervisor: launches a command, waits for it to exit,
  restarts it (up to a limit) with a real crash trace captured each time.

  Built to fix a concrete problem hit repeatedly this session: the backend
  and dashboard dev servers died silently while launched via
  `Start-Process -WindowStyle Hidden`, with nothing in the logs explaining
  why. Root cause candidates: (a) nothing was watching for the exit at all,
  and (b) -WindowStyle Hidden without explicit stdout/stderr redirection
  can swallow the crash output that would explain it. This script fixes
  both: it redirects real stdout/stderr per attempt and logs every
  exit/restart with a timestamp and exit code to logs\supervisor.log.

.EXAMPLE
  .\supervise.ps1 -Name backend -WorkingDirectory C:\...\backend `
    -FilePath C:\...\backend\venv\Scripts\python.exe `
    -ArgsJoined "-m uvicorn app.main:app --host 127.0.0.1 --port 8000"
#>
param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$WorkingDirectory,
    [Parameter(Mandatory = $true)][string]$FilePath,
    # Space-separated argument string (not an array) - avoids CLI parsing
    # ambiguity when this script is itself launched via `powershell -File`
    # with arguments like "--host" that would otherwise look like new
    # named parameters.
    [string]$ArgsJoined = "",
    [string]$LogDir = ".\logs",
    [int]$MaxRestarts = 10,
    [int]$RestartDelaySeconds = 3,
    # Optional: prepended onto PYTHONPATH before each launch (the backend
    # needs this; most services won't).
    [string]$PythonPath = ""
)

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
}
$LogDir = (Resolve-Path $LogDir).Path
$supervisorLog = Join-Path $LogDir "supervisor.log"
$pidFile = Join-Path $LogDir "$Name.pid"

function Write-SupervisorLog {
    param([string]$Message)
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [$Name] $Message"
    Add-Content -Path $supervisorLog -Value $line
    Write-Host $line
}

if ($PythonPath) {
    $env:PYTHONPATH = $PythonPath
}

$argArray = @()
if ($ArgsJoined) {
    $argArray = $ArgsJoined -split ' '
}

Write-SupervisorLog "Supervisor starting (MaxRestarts=$MaxRestarts, RestartDelaySeconds=$RestartDelaySeconds)"

$restartCount = 0
while ($true) {
    $attempt = $restartCount + 1
    # Per-attempt log files (not overwritten on restart) so a crash trace
    # from attempt 1 is still there to read after attempt 2 starts.
    $stdoutLog = Join-Path $LogDir "$Name`_stdout_$attempt.log"
    $stderrLog = Join-Path $LogDir "$Name`_stderr_$attempt.log"

    Write-SupervisorLog "Launching (attempt $attempt): $FilePath $ArgsJoined"
    try {
        $proc = Start-Process -FilePath $FilePath -ArgumentList $argArray -WorkingDirectory $WorkingDirectory `
            -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog
    } catch {
        Write-SupervisorLog "FATAL: failed to launch process: $_"
        break
    }

    Set-Content -Path $pidFile -Value $proc.Id
    Write-SupervisorLog "Started PID $($proc.Id) (stdout: $stdoutLog, stderr: $stderrLog)"

    $proc.WaitForExit()
    $exitCode = $proc.ExitCode
    $restartCount++
    Write-SupervisorLog "Process exited with code $exitCode"

    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue

    if ($restartCount -ge $MaxRestarts) {
        Write-SupervisorLog "FATAL: MaxRestarts ($MaxRestarts) reached - giving up. Check $stderrLog for the last crash trace."
        break
    }

    Start-Sleep -Seconds $RestartDelaySeconds
}
