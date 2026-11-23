# V6 offline, read-only symbol comparison. No uploads, installs or restarts.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$vbox=Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'
if (-not (Test-Path -LiteralPath $vbox)) { throw 'STOP: VBoxManage missing' }
$running=@(& $vbox list runningvms)
if ($LASTEXITCODE -ne 0 -or @($running | Where-Object { $_ -match '^"EP36_291_TEST"\s+\{' }).Count -ne 1) {
    throw 'STOP: EP36_291_TEST not running'
}
$rev='62ecfa5bb0d66695e6ee59b149769aa83fe0e1e9'
$u="https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads/$rev/diamond-insignia/worldsvr-ingress/Audit-DiamondV14-0BDA-Symbols-V6.py"
$p=Join-Path $env:TEMP 'Audit-DiamondV14-0BDA-Symbols-V6.py'
Invoke-WebRequest -UseBasicParsing -Uri $u -OutFile $p -ErrorAction Stop
$s=[System.IO.File]::ReadAllText($p)
if (-not $s.Contains('V6_READ_ONLY_SYMBOL_AUDIT_COMPLETE') -or -not $s.Contains('deploy_approved')) { throw 'STOP: unexpected script' }
$old=$OutputEncoding
try {
    $OutputEncoding=New-Object System.Text.UTF8Encoding($false)
    $lines=@($s | & ssh.exe -T -o ConnectTimeout=12 root@192.168.56.101 'python3 -')
    $rc=$LASTEXITCODE
} finally { $OutputEncoding=$old }
foreach($line in $lines){Write-Host $line}
if ($rc -ne 0 -or -not (($lines -join [Environment]::NewLine).Contains('END_DIAMOND_V6_SYMBOL_AUDIT'))) {
    throw "STOP: offline V6 audit failed (SSH=$rc)"
}
Write-Host 'DIAMOND_V6_SYMBOL_AUDIT=PASS_READ_ONLY'
