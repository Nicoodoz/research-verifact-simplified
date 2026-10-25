$ErrorActionPreference = 'Stop'
Set-Location 'D:\Research-VeriFact'
$out = 'outputs\032_evidence_relation_correction'
$active = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'tasks[\\/]032_evidence_relation_correction[\\/](run032|train032|evaluate032)\.py' }
if ($active) { throw 'A 032 runner/trainer is already active; refusing duplicate launch.' }
$nli = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'tasks[\\/]032_evidence_relation_correction[\\/]nli032\.py' }
foreach ($p in $nli) {
    if (Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue) {
        Write-Output ('Waiting for existing NLI process ' + $p.ProcessId)
        Wait-Process -Id $p.ProcessId -ErrorAction SilentlyContinue
    }
}
if (!(Test-Path "$out\nli_001\manifest.json")) { throw 'NLI has not completed successfully; will not train on partial features.' }
Write-Output 'NLI complete; resuming the frozen 032 pipeline.'
$ErrorActionPreference = 'Continue'
& E:\miniconda3\Scripts\conda.exe run --no-capture-output -n research D:\Research-VeriFact\.local_models\032\venv\Scripts\python.exe -u tasks\032_evidence_relation_correction\run032.py --resume *> "$out\continue_run001.log"
$code = $LASTEXITCODE
Write-Output ('032 runner exit code: ' + $code)
exit $code
