# Calibration: confirm the evaluator catches each deliberate defect.
#
# A green result on a correct application only shows the evaluator produces no
# false failures. This checks the other half -- that each assertion actually
# fires when the mechanism behind it is broken. An assertion that never fires
# is indistinguishable from one that always passes.
#
# One defect at a time: combining them makes it impossible to attribute a
# failure to a particular assertion.

param(
    [string]$BaseUrl = "http://localhost:18080",
    [string]$Dsn = "postgresql://orderman:orderman@localhost:15432/orderman",
    [int]$ToxiproxyPort = 18474
)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $PSScriptRoot ".venv-eval\Scripts\python.exe"
$appDir = Join-Path $PSScriptRoot "reference_app"

# Each defect names every scenario it is expected to break. Anything failing
# outside that set means the defect is less targeted than intended, or an
# assertion is over-reaching -- either way it needs explaining rather than
# recording as a pass.
#
# DEFECT_WRONG_ERROR_CODE legitimately breaks two: it swaps the timeout and
# unavailable codes, and both ASR-A1 and ASR-A3 assert on the classification.
$defects = [ordered]@{
    "DEFECT_NO_SINGLE_FLIGHT"        = @("ASR-P1")
    "DEFECT_QUEUE_INSTEAD_OF_REJECT" = @("ASR-P2")
    "DEFECT_WRONG_ERROR_CODE"        = @("ASR-A1", "ASR-A3")
    "DEFECT_METRICS_NEED_DB"         = @("ASR-A3")
    "DEFECT_NO_DEGRADED_CACHE"       = @("ASR-A3")
    "DEFECT_PARTIAL_COMMIT"          = @("ASR-A4")
}

$results = @()

foreach ($flag in $defects.Keys) {
    $expected = $defects[$flag]
    Write-Host "=== $flag (expect $expected to fail) ==="

    # Compose reads the flag from .env; a PowerShell environment variable does
    # not reach it, which silently produced a defect-free run when first tried.
    Set-Content -Path (Join-Path $appDir ".env") -Value "$flag=true" -Encoding ascii

    Push-Location $appDir
    docker compose -p eval-reference up -d --force-recreate app 2>&1 | Out-Null
    Pop-Location
    Start-Sleep -Seconds 12

    $out = Join-Path $PSScriptRoot "results\defect-$($flag.ToLower())"
    & $python -m evaluator.run --app $appDir --app-id reference --runs 1 `
        --base-url $BaseUrl --dsn $Dsn --toxiproxy-port $ToxiproxyPort `
        --output $out --keep-running 2>&1 | Out-Null

    $report = Get-Content (Join-Path $out "reference.json") -Raw | ConvertFrom-Json
    $failed = @($report.scenarios | Where-Object { $_.result -eq 'FAIL' } | ForEach-Object { $_.scenarioId })
    $caught = @($expected | Where-Object { $failed -contains $_ }).Count -eq $expected.Count
    $collateral = @($failed | Where-Object { $expected -notcontains $_ })

    $results += [PSCustomObject]@{
        Defect     = $flag
        Expected   = ($expected -join ',')
        Caught     = $caught
        Collateral = ($collateral -join ',')
    }
    Write-Host ("  caught={0} failed=[{1}] collateral=[{2}]" -f $caught, ($failed -join ','), ($collateral -join ','))
}

# Restore a defect-free deployment so the next ordinary run is not poisoned.
Set-Content -Path (Join-Path $appDir ".env") -Value "" -Encoding ascii
Push-Location $appDir
docker compose -p eval-reference up -d --force-recreate app 2>&1 | Out-Null
Pop-Location

Write-Host ""
Write-Host "=============== calibration summary ==============="
$results | Format-Table -AutoSize
$missed = @($results | Where-Object { -not $_.Caught })
if ($missed.Count -gt 0) {
    Write-Host "NOT CAUGHT: $($missed.Defect -join ', ')" -ForegroundColor Red
    Write-Host "The assertion for each of these is not doing its job." -ForegroundColor Red
    exit 1
}
Write-Host "every defect was caught by its intended scenario" -ForegroundColor Green
