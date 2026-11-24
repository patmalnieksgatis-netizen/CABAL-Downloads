# V11: build GCC14 image on Windows, transfer by SSH, compile offline in VM.
param([string]$ImageTar = '')
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$vbox=Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'
if(-not (Test-Path -LiteralPath $vbox)){throw 'STOP: VBoxManage absent'}
$vms=@(& $vbox list runningvms)
if($LASTEXITCODE -ne 0 -or @($vms|Where-Object {$_ -match '^"EP36_291_TEST"\s+\{'}).Count -ne 1){throw 'STOP: EP36_291_TEST VM not running'}
$guest='root@192.168.56.101'
$image='cabal-diamond-gcc14-v10:local'
$id=[Guid]::NewGuid().ToString('N')
$remote="/tmp/cabal-diamond-gcc14-v11-$id.tar"
$created=$false
if([string]::IsNullOrWhiteSpace($ImageTar)){
 $docker=Get-Command docker.exe -ErrorAction SilentlyContinue
 if($null -eq $docker){
  Write-Host 'DIAMOND_V11=BLOCKED_WINDOWS_DOCKER_NOT_AVAILABLE'
  exit 2
 }
 $exe=$docker.Source
 $os=@(& $exe info --format '{{.OSType}}')
 if($LASTEXITCODE -ne 0 -or ($os -join '').Trim() -ne 'linux'){
  Write-Host 'DIAMOND_V11=BLOCKED_WINDOWS_LINUX_DOCKER_ENGINE_NOT_RUNNING'
  exit 2
 }
 $dockerfile=@'
FROM debian:trixie-slim
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends g++-14 binutils unixodbc-dev ca-certificates && rm -rf /var/lib/apt/lists/*
'@
 Write-Host 'DIAMOND_V11=BUILDING_COMPILER_IMAGE_ON_WINDOWS'
 $dockerfile | & $exe build --platform linux/amd64 --pull=false --tag $image -
 if($LASTEXITCODE -ne 0){throw 'STOP: local Docker build failed; VM untouched'}
 $version=@(& $exe run --rm --platform linux/amd64 --network none --entrypoint g++-14 $image -dumpfullversion -dumpversion)
 if($LASTEXITCODE -ne 0 -or ($version -join '').Trim() -notmatch '^14\.2\.'){throw "STOP: unexpected compiler version $version"}
 $ImageTar=Join-Path $env:TEMP "cabal-diamond-gcc14-v11-$id.tar"
 & $exe save --output $ImageTar $image
 if($LASTEXITCODE -ne 0){throw 'STOP: docker save failed'}
 $created=$true
}
$ImageTar=(Resolve-Path -LiteralPath $ImageTar).Path
$hash=(Get-FileHash -LiteralPath $ImageTar -Algorithm SHA256).Hash.ToLowerInvariant()
$bytes=(Get-Item -LiteralPath $ImageTar).Length
if($bytes -le 0){throw 'STOP: empty compiler archive'}
Write-Host "DIAMOND_V11_ARCHIVE=$ImageTar"
Write-Host "DIAMOND_V11_ARCHIVE_BYTES=$bytes"
Write-Host "DIAMOND_V11_ARCHIVE_SHA256=$hash"
$rev='d177a453c9df7565b6c69e1db064e339686f9109'
$u="https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads/$rev/diamond-insignia/worldsvr-ingress/Build-DiamondV14-IsolatedGCC14-V10.py"
$p=Join-Path $env:TEMP "Build-DiamondV14-IsolatedGCC14-V11-$id.py"
Invoke-WebRequest -UseBasicParsing -Uri $u -OutFile $p -ErrorAction Stop
$s=[System.IO.File]::ReadAllText($p)
if(-not $s.Contains('GCC14_OFFLINE_COMPARISON_COMPLETE') -or -not $s.Contains('install_allowed')){throw 'STOP: unexpected V10 source'}
Write-Host 'DIAMOND_V11=TRANSFERRING_COMPILER_ARCHIVE'
& scp.exe -o ConnectTimeout=12 $ImageTar ($guest+':'+$remote)
if($LASTEXITCODE -ne 0){throw "STOP: SCP failed; local archive retained at $ImageTar"}
$cmd="set -eu; printf '%s  %s\n' '$hash' '$remote' | sha256sum -c -; docker load -i '$remote'; docker image inspect '$image' >/dev/null; rm -f -- '$remote'; python3 -"
$old=$OutputEncoding
try{
 $OutputEncoding=New-Object System.Text.UTF8Encoding($false)
 $lines=@($s | & ssh.exe -T -o ConnectTimeout=12 $guest $cmd)
 $rc=$LASTEXITCODE
}finally{$OutputEncoding=$old}
foreach($line in $lines){Write-Host $line}
if($rc -ne 0 -or -not (($lines -join [Environment]::NewLine).Contains('END_DIAMOND_V10_GCC14_RESULT'))){throw "STOP: V11 load/build failed SSH=$rc; local archive retained at $ImageTar"}
if($created){Remove-Item -LiteralPath $ImageTar}
Remove-Item -LiteralPath $p
Write-Host 'DIAMOND_V11=OFFLINE_GCC14_COMPARISON_COMPLETE'
