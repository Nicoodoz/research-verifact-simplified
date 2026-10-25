param([string]$RunId = 'run_001')
$ErrorActionPreference = 'Stop'
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
if ($RunId -notmatch '^[A-Za-z0-9_-]+$') { throw 'Invalid run ID' }
$taskOutput = Join-Path $repoRoot 'outputs/029_semantic_information_gate'
$launchDirectory = Join-Path $taskOutput ('launch_' + $RunId)
$runDirectory = Join-Path $taskOutput $RunId
if ((Test-Path -LiteralPath $launchDirectory) -or (Test-Path -LiteralPath $runDirectory)) { throw 'Launch/run already exists; refusing overwrite' }
$null = New-Item -ItemType Directory -Path $launchDirectory
$condaExe = 'E:/miniconda3/Scripts/conda.exe'
$arguments = @('run','--no-capture-output','-n','research-verifact-029','python','-u','-B','tasks/029_semantic_information_gate/run029.py','--run-id',$RunId)
$process = Start-Process -FilePath $condaExe -ArgumentList $arguments -WorkingDirectory $repoRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $launchDirectory 'stdout.log') -RedirectStandardError (Join-Path $launchDirectory 'stderr.log') -PassThru
$record = [ordered]@{ created_utc = [DateTime]::UtcNow.ToString('o'); launcher_pid = $process.Id; executable = $condaExe; arguments = $arguments; run_directory = $runDirectory; monitoring = 'No polling; program saves its own status and errors' }
[System.IO.File]::WriteAllText((Join-Path $launchDirectory 'launch.json'),($record | ConvertTo-Json -Depth 4),[System.Text.UTF8Encoding]::new($false))
Write-Output ('029 launched once in background. Launcher PID: ' + $process.Id)
Write-Output ('Status: ' + (Join-Path $runDirectory 'execution_status.json'))
Write-Output ('Logs: ' + $launchDirectory)
