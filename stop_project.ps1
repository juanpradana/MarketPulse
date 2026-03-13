Write-Host "Stopping MarketPulse Services..."

$ports = @(3001, 8000)

function Get-ListeningPidsByPort {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    try {
        return Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop |
            Select-Object -ExpandProperty OwningProcess -Unique
    } catch {
        # Fallback when Get-NetTCPConnection is not permitted
        $lines = netstat -ano | Select-String "LISTENING" | Select-String (":$Port ")
        $pids = @()
        foreach ($line in $lines) {
            $parts = ($line.Line -split "\s+") | Where-Object { $_ -ne "" }
            if ($parts.Count -gt 0) {
                $pid = $parts[-1]
                if ($pid -match '^\d+$') {
                    $pids += [int]$pid
                }
            }
        }
        return $pids | Select-Object -Unique
    }
}

foreach ($port in $ports) {
    Write-Host "Checking port $port..."
    # Find process ID using NetTCPConnection
    $processIds = Get-ListeningPidsByPort -Port $port
    
    if ($processIds) {
        foreach ($pid_to_kill in $processIds) {
            try {
                $proc = Get-Process -Id $pid_to_kill -ErrorAction Stop
                Stop-Process -Id $pid_to_kill -Force -ErrorAction Stop
                Write-Host "  Stopped process '$($proc.ProcessName)' (PID: $pid_to_kill) on port $port"
            } catch {
                Write-Host "  Failed to stop process PID $pid_to_kill on port $port. It might already be gone."
            }
        }
    } else {
        Write-Host "  No active process found on port $port"
    }
}

Write-Host "Done."
Start-Sleep -Seconds 2
