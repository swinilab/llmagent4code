# Evaluate one generated application.
#
#   .\evaluator\run_app.ps1 -App claude-gen\app-claude
#   .\evaluator\run_app.ps1 -App claude-gen\app-claude -Runs 5
#
# Run from the repository root.
#
# The preflight checks exist because every one of them has already cost a run.
# A stack left up from a previous session holds port 8080 and the evaluation
# scores a container it did not start; a local PostgreSQL server holds 5432 and
# the database probes read the wrong database; a Docker daemon that has run out
# of resources reports application failures that never happened. Each is cheap
# to detect beforehand and expensive to diagnose afterwards.

param(
    [Parameter(Mandatory = $true)][string]$App,
    [int]$Runs = 5,
    [string]$AppId = "",
    [string]$Output = "",
    [int]$DbPort = 15432,
    [string]$BaseUrl = "http://localhost:8080",
    [int]$ToxiproxyPort = 8474,
    [switch]$KeepRunning,
    [switch]$SkipPreflight
)

$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
$python = Join-Path $PSScriptRoot ".venv-eval\Scripts\python.exe"

$appDir = if ([System.IO.Path]::IsPathRooted($App)) { $App } else { Join-Path $repo $App }
if (-not (Test-Path $appDir)) { throw "application directory not found: $appDir" }
if ($AppId -eq "") { $AppId = Split-Path $appDir -Leaf }
if ($Output -eq "") { $Output = Join-Path $repo "evaluation-results\$AppId" }
$project = "eval-$($AppId.ToLower())"

if (-not (Test-Path $python)) {
    throw "evaluator venv missing. Create it with:`n" +
          "  uv venv evaluator\.venv-eval`n" +
          "  uv pip install --python evaluator\.venv-eval\Scripts\python.exe httpx pyyaml 'psycopg[binary]'"
}

# ── preflight ─────────────────────────────────────────────────────────────

if (-not $SkipPreflight) {
    Write-Host "== preflight ==" -ForegroundColor Cyan

    # 1. Docker must be answering. A daemon that has fallen over produces
    #    scenario failures indistinguishable from application defects.
    docker version --format '{{.Server.Version}}' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Docker is not responding. Start Docker Desktop and retry." }
    Write-Host "  docker: responding"

    # 2. Nothing else may hold the application or Toxiproxy ports. A stack left
    #    running from an earlier session is the usual culprit, and the
    #    evaluation would silently measure it instead of a fresh deployment.
    foreach ($port in @(8080, $ToxiproxyPort)) {
        $busy = (netstat -ano -p tcp | Select-String "LISTENING" | Select-String ":$port\s")
        if ($busy) {
            Write-Host "  port $port is in use; taking down any evaluation stacks" -ForegroundColor Yellow
            Push-Location $appDir
            docker compose -p $project down -v 2>&1 | Out-Null
            docker compose -p (Split-Path $appDir -Leaf) down -v 2>&1 | Out-Null
            Pop-Location
            Start-Sleep -Seconds 3
            $busy = (netstat -ano -p tcp | Select-String "LISTENING" | Select-String ":$port\s")
            if ($busy) { throw "port $port is still held by another process; free it and retry" }
        }
        Write-Host "  port ${port}: free"
    }

    # 3. The database port must be publishable and must not be a *different*
    #    PostgreSQL. Reading the wrong database is worse than not reading one,
    #    because the rollback assertions would then be checked against rows the
    #    application never wrote.
    $dbBusy = (netstat -ano -p tcp | Select-String "LISTENING" | Select-String ":$DbPort\s")
    if ($dbBusy) { throw "port $DbPort is in use; pass -DbPort with a free port (and match it in the override file)" }
    Write-Host "  port ${DbPort}: free (PostgreSQL will be published here)"

    # 4. Three scenarios read PostgreSQL directly, which needs a published port.
    #    The submission is not required to publish one, so an evaluation-only
    #    overlay supplies it; Compose merges it automatically.
    $override = Join-Path $appDir "docker-compose.override.yml"
    if (-not (Test-Path $override)) {
        Write-Host "  writing docker-compose.override.yml (publishes PostgreSQL on $DbPort)" -ForegroundColor Yellow
        @"
# Evaluation-only overlay. Not part of the submission's deployment contract.
# ASR-A2, ASR-A4 and ASR-P1 read their decisive evidence straight out of
# PostgreSQL, which needs a host-side port. Nothing inside the network changes:
# the application still reaches the database only through toxiproxy:8666.
services:
  db:
    ports:
      - "${DbPort}:5432"
"@ | Set-Content -Path $override -Encoding ascii
    }
    Write-Host "  override: present"
}

# ── run ───────────────────────────────────────────────────────────────────

$dsn = "postgresql://orderman:orderman@localhost:$DbPort/orderman"

Write-Host ""
Write-Host "== evaluating $AppId ($Runs run(s) per scenario) ==" -ForegroundColor Cyan
Write-Host "   app:    $appDir"
Write-Host "   output: $Output"
Write-Host ""

# -u disables stdout buffering. Without it Python holds the narration in a pipe
# buffer and a redirected run shows nothing until it finishes -- which is
# exactly when the live trace stops being useful.
$evalArgs = @(
    "-u", "-m", "evaluator.run",
    "--app", $appDir,
    "--app-id", $AppId,
    "--runs", $Runs,
    "--base-url", $BaseUrl,
    "--dsn", $dsn,
    "--toxiproxy-port", $ToxiproxyPort,
    "--output", $Output
)
if ($KeepRunning) { $evalArgs += "--keep-running" }

Push-Location $repo
try { & $python @evalArgs; $code = $LASTEXITCODE } finally { Pop-Location }

Write-Host ""
Write-Host "report:    $Output\$AppId.json"
Write-Host "trace log: $Output\$AppId.trace.jsonl"
exit $code
