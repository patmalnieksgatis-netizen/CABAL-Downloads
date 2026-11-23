# CABAL V8: isolated GCC14 rebuild only; no active WorldSvr / SQL modification.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$vbox=Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'
if (-not (Test-Path -LiteralPath $vbox)){throw 'STOP: VBoxManage missing'}
$running=@(& $vbox list runningvms)
if ($LASTEXITCODE -ne 0 -or @($running | Where-Object {$_ -match '^"EP36_291_TEST"\s+\{'}).Count -ne 1){
 throw 'STOP: EP36_291_TEST not running'
}
$rev='00acfe8edcab165f20c2a8a9bb52048dcdf6806b'
$u="https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads/$rev/diamond-insignia/worldsvr-ingress/Build-DiamondV14-GCC14Offline-V8.py"
$p=Join-Path $env:TEMP 'Build-DiamondV14-GCC14Offline-V8.py'
Invoke-WebRequest -UseBasicParsing -Uri $u -OutFile $p -ErrorAction Stop
$s=[System.IO.File]::ReadAllText($p)
if (-not $s.Contains('BLOCKED_GCC14_NOT_INSTALLED') -or -not $s.Contains('install_allowed')) {
 throw 'STOP: unexpected script source'
}
$old=$OutputEncoding
try {
 $OutputEncoding=New-Object System.Text.UTF8Encoding($false)
 $lines=@($s | & ssh.exe -T -o ConnectTimeout=12 root@192.168.56.101 'python3 -')
 $rc=$LASTEXITCODE
} finally {$OutputEncoding=$old}
foreach($line in $lines){Write-Host $line}
if ($rc -ne 0 -or -not (($lines -join [Environment]::NewLine).Contains('END_DIAMOND_V8_GCC14_RESULT'))){
 throw "STOP: V8 offline build/availability failed SSH=$rc"
}
Write-Host 'DIAMOND_V8_GCC14=OFFLINE_COMPLETE_OR_BLOCKED'
