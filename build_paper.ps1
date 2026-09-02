# Compile the IEEE paper and report the real page count.
#
# MiKTeX is installed per-user, so its bin directory is not on PATH by default.
# Two passes: the first resolves labels, the second fixes the cross-references
# and the final pagination.
#
#   powershell -File build_paper.ps1            # two passes, report pages
#   powershell -File build_paper.ps1 -Quick     # one pass, for fast iteration

param([switch]$Quick)

$ErrorActionPreference = 'Continue'
$env:PATH = "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64;$env:PATH"
Set-Location $PSScriptRoot
New-Item -ItemType Directory -Force -Path ".texbuild" | Out-Null

$passes = if ($Quick) { 1 } else { 2 }
$texArgs = @('-interaction=nonstopmode', '-output-directory=.texbuild', 'aimirror_ieee_paper.tex')

for ($i = 1; $i -le $passes; $i++) {
    $out = & pdflatex @texArgs 2>&1
}

$log = Get-Content ".texbuild\aimirror_ieee_paper.log" -Raw -ErrorAction SilentlyContinue

# Real errors only. MiKTeX prints an "update" nag on stderr that is not one.
$errors = $out | Select-String -Pattern '^!' | Select-Object -First 8
if ($errors) {
    Write-Output "LATEX ERRORS:"
    $errors | ForEach-Object { Write-Output "  $_" }
}

$overfull = ([regex]::Matches($log, 'Overfull \\hbox')).Count
$undefined = ([regex]::Matches($log, 'Citation .* undefined|Reference .* undefined')).Count

# The log hard-wraps at ~79 columns, so "Output written on ... (9 pages"
# is split across lines. [\s\S] matches across the wrap.
if ($log -match 'Output written on[\s\S]*?\((\d+) pages') {
    $pages = $Matches[1]
    Write-Output ""
    Write-Output "  PAGES: $pages   (limit 8)"
    Write-Output "  overfull hboxes: $overfull   undefined refs/cites: $undefined"
    if ([int]$pages -gt 8) { Write-Output "  OVER LIMIT by $([int]$pages - 8)" }
    else { Write-Output "  within limit" }

    # Source-level checks cannot see a command that lost its backslash:
    # "ef{sec:discussion}" is not a broken reference, it is prose, so pdflatex
    # is silent and the undefined-reference count stays at zero. This reads the
    # rendered page instead.
    $py = Join-Path $PSScriptRoot "backend\venv\Scripts\python.exe"
    if (Test-Path $py) {
        & $py "check_paper_render.py" ".texbuild\aimirror_ieee_paper.pdf"
    }
} else {
    Write-Output "  NO PDF PRODUCED - see .texbuild\aimirror_ieee_paper.log"
}
