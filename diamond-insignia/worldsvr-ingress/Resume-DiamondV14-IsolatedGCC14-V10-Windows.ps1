# Diamond V10 GCC14 isolation; changes only Docker image cache and /tmp output.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$vbox=Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'
if(-not (Test-Path -LiteralPath $vbox)){throw 'STOP: VBoxManage absent'}
$vms=@(& $vbox list runningvms)
if($LASTEXITCODE -ne 0 -or @($vms|Where-Object {$_ -match '^"EP36_291_TEST"\s+\{'}).Count -ne 1){
 throw 'STOP: EP36_291_TEST VM not running'
}
$rev='d177a453c9df7565b6c69e1db064e339686f9109'
$u="https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads/$rev/diamond-insignia/worldsvr-ingress/Build-DiamondV14-IsolatedGCC14-V10.py"
$p=Join-Path $env:TEMP 'Build-DiamondV14-IsolatedGCC14-V10.py'
Invoke-WebRequest -UseBasicParsing -Uri $u -OutFile $p -ErrorAction Stop
$s=[System.IO.File]::ReadAllText($p)
if(-not $s.Contains('GCC14_OFFLINE_COMPARISON_COMPLETE') -or -not $s.Contains('install_allowed')){
 throw 'STOP: unknown V10 payload'
}
$old=$OutputEncoding
try {
 $OutputEncoding=New-Object System.Text.UTF8Encoding($false)
 $lines=@($s | & ssh.exe -T -o ConnectTimeout=12 root@192.168.56.101 'python3 -')
 $rc=$LASTEXITCODE
} finally {$OutputEncoding=$old}
foreach($line in $lines){Write-Host $line}
if($rc -ne 0 -or -not (($lines -join [Environment]::NewLine).Contains('END_DIAMOND_V10_GCC14_RESULT'))){
 throw "STOP: V10 isolated build did not complete SSH=$rc"
}
Write-Host 'DIAMOND_V10_GCC14=OFFLINE_COMPLETE'
