# Keeps this Windows machine from entering sleep/Modern Standby for the rest of the IV Desk
# competition. `powercfg /change standby-timeout-ac 0` alone was not enough — Modern Standby
# cycled the machine anyway overnight 1->2 Sep, losing ~6.5h of the local pacemaker's dispatches
# (harmless that night since the market was closed the whole gap, but not something to risk
# during a live session). This calls the same Win32 API caffeine-style keep-awake tools use:
# SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED), refreshed
# every 30s so it survives even if a single call gets missed.
Add-Type -Name Sleep -Namespace Win32 -MemberDefinition @'
[DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
public static extern uint SetThreadExecutionState(uint esFlags);
'@
$ES_CONTINUOUS = 0x80000000
$ES_SYSTEM_REQUIRED = 0x00000001
$ES_AWAYMODE_REQUIRED = 0x00000040
Write-Output "$(Get-Date -Format o)  keep-awake started (pid $PID)"
while ($true) {
    [Win32.Sleep]::SetThreadExecutionState($ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED -bor $ES_AWAYMODE_REQUIRED) | Out-Null
    Start-Sleep -Seconds 30
}
