# Run CPU/API research tasks with the conda DLL search path activated.
param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$PythonArguments
)
$ErrorActionPreference = 'Stop'
if (-not $PythonArguments -or $PythonArguments.Count -eq 0) {
    throw 'Usage: pwsh -File scripts/run_research.ps1 <script.py> [arguments]'
}
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$condaExe = 'E:/miniconda3/Scripts/conda.exe'
if (-not (Test-Path -LiteralPath $condaExe)) {
    $condaExe = (Get-Command conda.exe -ErrorAction Stop).Source
}
Push-Location -LiteralPath $repoRoot
try {
    & $condaExe run --no-capture-output -n research-verifact-029 python -B @PythonArguments
    exit $LASTEXITCODE
}
finally { Pop-Location }
