# Install a Windows Scheduled Task that syncs MT5 → Neon/SQLite every 30 minutes.
# Run once in PowerShell (as your user; no admin required for current-user tasks):
#   Set-ExecutionPolicy -Scope Process Bypass
#   .\scripts\install_sync_scheduler.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Script = Join-Path $Root "scripts\sync_mt5.py"
$TaskName = "TradeEdge MT5 Sync"

if (-not (Test-Path $Python)) {
    Write-Error "Missing $Python — create the venv and install requirements first."
}

$Action = New-ScheduledTaskAction -Execute $Python -Argument "`"$Script`" --quiet" -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 30) -RepetitionDuration ([TimeSpan]::MaxValue)
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description "Sync closed Exness MT5 trades into TradeEdge Journal (Neon/SQLite)." | Out-Null

Write-Host "Installed scheduled task '$TaskName' (every 30 minutes while logged in)."
Write-Host "Keep Exness MT5 open for reliable sync."
Write-Host "Remove later with: .\scripts\uninstall_sync_scheduler.ps1"
