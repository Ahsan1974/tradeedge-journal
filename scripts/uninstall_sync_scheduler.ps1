# Remove the TradeEdge MT5 Sync scheduled task.
$TaskName = "TradeEdge MT5 Sync"
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Write-Host "Removed scheduled task '$TaskName' (if it existed)."
