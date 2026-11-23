# CABAL v291 Diamond: stage & compile exact v14 0BDA source OFFLINE only.
# PowerShell 5.1+, VirtualBox EP36_291_TEST with SSH access.
# NO active lib.so, supervisor, WorldSvr, SQL or client modification.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$vbox=Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'
if (-not (Test-Path -LiteralPath $vbox)) { throw 'STOP: VBoxManage not installed' }
$running=@(& $vbox list runningvms)
if ($LASTEXITCODE -ne 0 -or
    @($running | Where-Object { $_ -match '^"EP36_291_TEST"\s+\{' }).Count -ne 1) {
    throw 'STOP: expected EP36_291_TEST is not running'
}
foreach ($exe in @('ssh.exe','scp.exe')) {
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) {
        throw "STOP: Windows $exe unavailable"
    }
}
# Pinned source revision containing the exact offline build implementation.
$commit='4682867ef15cf127f992b07dd152d7a2f6920769'
$url="https://api.github.com/repos/patmalnieksgatis-netizen/CABAL-Downloads/zipball/$commit"
$local=Join-Path $env:TEMP 'CABAL_DIAMOND_0BDA_OFFLINE_20261123'
$zip="$local.zip"
$remote='/tmp/cabal_diamond_v291_0bda_source_20261123'
$out='/tmp/cabal_diamond_v291_0bda_offline_build_20261123'
$hostTarget='root@192.168.56.101'
if ((Test-Path -LiteralPath $local) -or (Test-Path -LiteralPath $zip)) {
    throw 'STOP: local staging already exists; no overwrite'
}
Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $zip -ErrorAction Stop
if ((Get-Item -LiteralPath $zip).Length -lt 20000) {
    throw 'STOP: source download too short'
}
Expand-Archive -LiteralPath $zip -DestinationPath $local -ErrorAction Stop
$roots=@(Get-ChildItem -LiteralPath $local -Directory)
if ($roots.Count -ne 1) { throw 'STOP: unexpected GitHub source archive layout' }
$root=$roots[0].FullName
$ingress=Join-Path $root 'diamond-insignia\worldsvr-ingress'
$native=Join-Path $root 'diamond-insignia\native'
foreach ($f in @(
    (Join-Path $ingress 'Build-DiamondV14Real0BDAOffline.py'),
    (Join-Path $ingress 'Apply-DiamondV14Real0BDAClone.py'),
    (Join-Path $ingress 'Apply-DiamondV14BoundClone.py'),
    (Join-Path $native 'diamond_abi.h'),
    (Join-Path $native 'diamond_merit_world_entry.cpp'))) {
    if (-not (Test-Path -LiteralPath $f)) { throw "STOP: missing source $f" }
}
$check='test "$(hostname)" = "cabalep33" && test -f /root/CABAL_V282_LIVE_MERGE_CANDIDATE_v14/source_tree/src/hooks/Handlers/ProcSystem.cpp && test -f /root/cabal_diamond_backup/lib.so_before_diamond_20261122 && test ! -e /tmp/cabal_diamond_v291_0bda_source_20261123 && test ! -e /tmp/cabal_diamond_v291_0bda_offline_build_20261123'
& ssh.exe -T -o ConnectTimeout=12 $hostTarget $check
if ($LASTEXITCODE -ne 0) { throw 'STOP: source and baseline preflight failed on VM' }
& ssh.exe -T -o ConnectTimeout=12 $hostTarget "mkdir -p '$remote/diamond-insignia'"
if ($LASTEXITCODE -ne 0) { throw 'STOP: cannot prepare isolated VM /tmp staging' }
& scp.exe -r -o ConnectTimeout=12 "$ingress" "$native" "$($hostTarget):$remote/diamond-insignia/"
if ($LASTEXITCODE -ne 0) { throw 'STOP: isolated source upload failed' }
$cmd="python3 '$remote/diamond-insignia/worldsvr-ingress/Build-DiamondV14Real0BDAOffline.py' --source /root/CABAL_V282_LIVE_MERGE_CANDIDATE_v14/source_tree/src --baseline-lib /root/cabal_diamond_backup/lib.so_before_diamond_20261122 --output-dir '$out' && cat '$out/OFFLINE_BUILD_RESULT.json'"
& ssh.exe -T -o ConnectTimeout=12 $hostTarget $cmd
if ($LASTEXITCODE -ne 0) { throw 'STOP: build failed, live WorldSvr/lib.so unchanged' }
Write-Host 'DIAMOND_WORLD_0BDA_OFFLINE_BUILD=PASS'
Write-Host "VM_STAGING_RESULT=$out/OFFLINE_BUILD_RESULT.json"
Write-Host 'WORLD_SERVER_RESTARTED=NO'
Write-Host 'CLIENT_SQL_UNCHANGED=YES'
Write-Host 'IN_GAME_DIAMOND_ACTIVATED=NO'
