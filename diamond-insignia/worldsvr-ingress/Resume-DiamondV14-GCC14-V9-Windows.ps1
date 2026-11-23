# CABAL Diamond V9: read-only compiler discovery through SSH.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$vbox=Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'
if(-not (Test-Path -LiteralPath $vbox)){throw 'STOP: VirtualBox not installed'}
$vms=@(& $vbox list runningvms)
if($LASTEXITCODE -ne 0 -or @($vms|Where-Object {$_ -match '^"EP36_291_TEST"\s+\{'}).Count -ne 1){
 throw 'STOP: EP36_291_TEST not running'
}
$rev='8a6647f11bdf768994374160ab5a001c5e2e81bf'
$u="https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads/$rev/diamond-insignia/worldsvr-ingress/Discover-DiamondV14-GCC14-V9.py"
$p=Join-Path $env:TEMP 'Discover-DiamondV14-GCC14-V9.py'
Invoke-WebRequest -UseBasicParsing -Uri $u -OutFile $p -ErrorAction Stop
$s=[System.IO.File]::ReadAllText($p)
if(-not $s.Contains('V9_READ_ONLY_TOOLCHAIN_DISCOVERY') -or -not $s.Contains('changes_made')){throw 'STOP: unexpected source'}
$old=$OutputEncoding
try {
 $OutputEncoding=New-Object System.Text.UTF8Encoding($false)
 $lines=@($s | & ssh.exe -T -o ConnectTimeout=12 root@192.168.56.101 'python3 -')
 $rc=$LASTEXITCODE
} finally {$OutputEncoding=$old}
foreach($line in $lines){Write-Host $line}
if($rc -ne 0 -or -not (($lines -join [Environment]::NewLine).Contains('END_DIAMOND_V9_TOOLCHAIN_DISCOVERY'))){
 throw "STOP: V9 discovery failed SSH=$rc"
}
Write-Host 'DIAMOND_V9_DISCOVERY=PASS_READ_ONLY'
