# Register a one-time, current-user task. No passwords or API keys are stored here.
$ErrorActionPreference = 'Stop'
$taskName = 'Research-VeriFact-098-Resume'
$pwshPath = (Get-Command pwsh.exe -ErrorAction Stop).Source
$entry = Join-Path $PSScriptRoot 'resume098.ps1'
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$runAt = [datetime]::Today.AddHours(22)
if ((Get-Date) -ge $runAt -and (Get-Date).Hour -ge 8) { $runAt = (Get-Date).AddMinutes(1) }
if ((Get-Date).Hour -lt 8) { $runAt = (Get-Date).AddMinutes(1) }
$arguments = '-NoProfile -NonInteractive -WindowStyle Hidden -File "' + $entry + '"'
$action = New-ScheduledTaskAction -Execute $pwshPath -Argument $arguments -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -Once -At $runAt
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -MultipleInstances IgnoreNew -ExecutionTimeLimit ([timespan]::FromHours(12)) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) { throw '098 scheduled task already exists; inspect before replacing it.' }
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description '098 frozen continuation after22:00; same ledger; no successful request re-send; logs in private098/logs.' | Out-Null
Get-ScheduledTask -TaskName $taskName | Select-Object TaskName,State,@{Name='Execute';Expression={$_.Actions.Execute}},@{Name='Arguments';Expression={$_.Actions.Arguments}}
Get-ScheduledTaskInfo -TaskName $taskName | Select-Object NextRunTime,LastRunTime,LastTaskResult
