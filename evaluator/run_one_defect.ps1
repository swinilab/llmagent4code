# Re-run a single deliberate defect.
#
# Useful when an assertion has been changed in response to a defect the
# evaluator missed: the full suite takes half an hour, and mixing results from
# two versions of the evaluator makes the summary meaningless.

param(
    [Parameter(Mandatory = $true)][string]$Flag,
    [Parameter(Mandatory = $true)][string]$Expected,
    [string]$BaseUrl = "http://localhost:18080",
    [string]$Dsn = "postgresql://orderman:orderman@localhost:15432/orderman",
    [int]$ToxiproxyPort = 18474
)

$python = Join-Path $PSScriptRoot ".venv-eval\Scripts\python.exe"
$appDir = Join-Path $PSScriptRoot "reference_app"

# Compose reads the flag from .env; a PowerShell environment variable does not
# reach the container and produces a clean run with no defect active at all.
Set-Content -Path (Join-Path $appDir ".env") -Value "$Flag=true" -Encoding ascii

Push-Location $appDir
docker compose -p eval-reference up -d --force-recreate app 2>&1 | Out-Null
Pop-Location
Start-Sleep -Seconds 12

$active = docker exec eval-reference-app-1 printenv | Select-String "$Flag=true"
if (-not $active) {
    Write-Host "$Flag did not reach the container; aborting" -ForegroundColor Red
    exit 1
}

$out = Join-Path $PSScriptRoot "results\defect-$($Flag.ToLower())"
& $python -m evaluator.run --app $appDir --app-id reference --runs 1 `
    --base-url $BaseUrl --dsn $Dsn --toxiproxy-port $ToxiproxyPort `
    --output $out --keep-running 2>&1 | Out-Null

$report = Get-Content (Join-Path $out "reference.json") -Raw | ConvertFrom-Json
$failed = @($report.scenarios | Where-Object { $_.result -eq 'FAIL' } | ForEach-Object { $_.scenarioId })
$caught = $failed -contains $Expected

Write-Host ("{0}: expected={1} caught={2} failed=[{3}]" -f $Flag, $Expected, $caught, ($failed -join ','))

if ($caught) {
    $scenario = $report.scenarios | Where-Object { $_.scenarioId -eq $Expected }
    foreach ($a in $scenario.runs[0].assertions) {
        if (-not $a.passed) { Write-Host ("  x {0} | want={1} got={2}" -f $a.name, $a.expected, $a.actual) }
    }
}

# Leave a defect-free deployment behind.
Set-Content -Path (Join-Path $appDir ".env") -Value "" -Encoding ascii
Push-Location $appDir
docker compose -p eval-reference up -d --force-recreate app 2>&1 | Out-Null
Pop-Location

if (-not $caught) { exit 1 }
