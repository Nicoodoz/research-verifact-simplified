# Detached/scheduled entry point. Does not change the scientific freeze or ledger.
param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $taskRoot '../..'))
$privateRoot = Join-Path $repoRoot '.local_models/098_p90_native_confirmation'
$logRoot = Join-Path $privateRoot 'logs'
[System.IO.Directory]::CreateDirectory($logRoot) | Out-Null
$pwshPath = (Get-Command pwsh.exe -ErrorAction Stop).Source
$researchWrapper = Join-Path $repoRoot 'scripts/run_research.ps1'
$utf8 = [System.Text.UTF8Encoding]::new($false)
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$kind = if ($CheckOnly) { 'check' } else { 'resume' }
$runLog = Join-Path $logRoot ($kind + '_' + $timestamp + '_' + $PID + '.log')

if ($CheckOnly) {
    & $pwshPath -NoProfile -NonInteractive -File $researchWrapper (Join-Path $taskRoot 'resume_check098.py') *> $runLog
    $checkCode = $LASTEXITCODE
    Get-Content -LiteralPath $runLog
    Write-Output ('Check log: ' + $runLog)
    exit $checkCode
}

$mutex = [System.Threading.Mutex]::new($false, 'Local\ResearchVeriFact098Resume')
$acquired = $false
try {
    try { $acquired = $mutex.WaitOne(0) }
    catch [System.Threading.AbandonedMutexException] { $acquired = $true }
    if (-not $acquired) { Write-Output '098 already has an independent resume process.'; exit 0 }
    $completion = Join-Path $repoRoot 'outputs/098_p90_native_confirmation/complete.json'
    if (Test-Path -LiteralPath $completion) { Write-Output '098 already complete; no requests sent.'; exit 0 }
    $statePath = Join-Path $privateRoot 'background_status.json'
    $state = [ordered]@{ status = 'RUNNING'; started = (Get-Date -Format o); pid = $PID; log = $runLog; independent_of_codex = $true }
    [System.IO.File]::WriteAllText($statePath, ($state | ConvertTo-Json), $utf8)
    & $pwshPath -NoProfile -NonInteractive -File $researchWrapper (Join-Path $taskRoot 'resume_check098.py') *> $runLog
    $exitCode = $LASTEXITCODE
    if ($exitCode -eq 0) {
        & $pwshPath -NoProfile -NonInteractive -File $researchWrapper (Join-Path $taskRoot 'complete098.py') *>> $runLog
        $exitCode = $LASTEXITCODE
    }
    if ($exitCode -eq 0 -and (Test-Path -LiteralPath $completion)) {
        & $pwshPath -NoProfile -NonInteractive -File $researchWrapper (Join-Path $taskRoot 'update_status098.py') *>> $runLog
        $exitCode = $LASTEXITCODE
    }
    $state['status'] = if ($exitCode -eq 0) { 'COMPLETE' } else { 'FAILED' }
    $state['ended'] = Get-Date -Format o
    $state['exit_code'] = $exitCode
    [System.IO.File]::WriteAllText($statePath, ($state | ConvertTo-Json), $utf8)
    exit $exitCode
}
finally {
    if ($acquired) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
