# Diamond v291 V7: read-only offline ELF inspection on EP36_291_TEST.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$vbox=Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'
if (-not (Test-Path -LiteralPath $vbox)) {throw 'STOP: VBoxManage missing'}
$running=@(& $vbox list runningvms)
if ($LASTEXITCODE -ne 0 -or @($running | Where-Object {$_ -match '^"EP36_291_TEST"\s+\{'}).Count -ne 1) {
 throw 'STOP: EP36_291_TEST VM not running'
}
$rev='65607df911bc430b478073f20d3413e1c0623531'
$url="https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads/$rev/diamond-insignia/worldsvr-ingress/Audit-DiamondV14-0BDA-Toolchain-V7.py"
$p=Join-Path $env:TEMP 'Audit-DiamondV14-0BDA-Toolchain-V7.py'
Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $p -ErrorAction Stop
$script=[System.IO.File]::ReadAllText($p)
if (-not $script.Contains('V7_READ_ONLY_TARGETED_AUDIT_COMPLETE') -or -not $script.Contains('installation_allowed')) {
 throw 'STOP: source verification failed'
}
$old=$OutputEncoding
try {
 $OutputEncoding=New-Object System.Text.UTF8Encoding($false)
 $lines=@($script | & ssh.exe -T -o ConnectTimeout=12 root@192.168.56.101 'python3 -')
 $rc=$LASTEXITCODE
} finally {$OutputEncoding=$old}
foreach($line in $lines){Write-Host $line}
if ($rc -ne 0 -or -not (($lines -join [Environment]::NewLine).Contains('END_DIAMOND_V7_TOOLCHAIN_AUDIT'))) {
 throw "STOP: audit did not complete SSH=$rc"
}
Write-Host 'DIAMOND_V7_TOOLCHAIN_AUDIT=PASS_READ_ONLY'
