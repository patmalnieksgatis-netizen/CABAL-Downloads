# V12: download Debian rootfs on Windows without Docker Desktop.
# A temporary restricted SSH reverse SOCKS tunnel serves APT in a separate
# build container. No VirtualBox changes, service restarts or host APT.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$guest='root@192.168.56.101'
$vbox=Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'
if(-not (Test-Path -LiteralPath $vbox)){throw 'STOP: VBoxManage absent'}
$vms=@(& $vbox list runningvms)
if($LASTEXITCODE -ne 0 -or @($vms|Where-Object {$_ -match '^"EP36_291_TEST"\s+\{'}).Count -ne 1){throw 'STOP: EP36_291_TEST not running'}
$ssh=(Get-Command ssh.exe -ErrorAction Stop).Source
$scp=(Get-Command scp.exe -ErrorAction Stop).Source
$curl=(Get-Command curl.exe -ErrorAction Stop).Source
$id=[Guid]::NewGuid().ToString('N')
$port=Get-Random -Minimum 21000 -Maximum 49000
$dir=Join-Path $env:TEMP "diamond-v12-$id"
New-Item -ItemType Directory -Path $dir | Out-Null
$rootfs=Join-Path $dir 'debian-amd64-rootfs.tar.gz'
$remote="/tmp/diamond-v12-$id.tar.gz"
$rev='d177a453c9df7565b6c69e1db064e339686f9109'
$py=Join-Path $dir 'V10.py'
$u="https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads/$rev/diamond-insignia/worldsvr-ingress/Build-DiamondV14-IsolatedGCC14-V10.py"
Invoke-WebRequest -UseBasicParsing -Uri $u -OutFile $py -ErrorAction Stop
$source=[System.IO.File]::ReadAllText($py)
if(-not $source.Contains('GCC14_OFFLINE_COMPARISON_COMPLETE')){throw 'STOP: unexpected V10 source'}
$payload=[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($source))
Write-Host 'DIAMOND_V12=DOWNLOADING_OFFICIAL_DEBIAN_ROOTFS_ON_WINDOWS'
$token=(Invoke-RestMethod -Uri 'https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/debian:pull').token
$headers=@{Authorization="Bearer $token";Accept='application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json'}
$registry='https://registry-1.docker.io/v2/library/debian'
$m=Invoke-RestMethod -Uri "$registry/manifests/trixie-slim" -Headers $headers
if($null -ne $m.PSObject.Properties['manifests']){
 $entry=@($m.manifests|Where-Object {$_.platform.os -eq 'linux' -and $_.platform.architecture -eq 'amd64'})
 if($entry.Count -ne 1){throw 'STOP: ambiguous or missing Linux amd64 manifest'}
 $digest=$entry[0].digest
 if($digest -notmatch '^sha256:[a-f0-9]{64}$'){throw 'STOP: bad manifest digest'}
 $m=Invoke-RestMethod -Uri "$registry/manifests/$digest" -Headers $headers
}
$layers=@($m.layers)
if($layers.Count -ne 1){throw 'STOP: expected a single Debian rootfs layer'}
$layer=$layers[0]
if($layer.digest -notmatch '^sha256:[a-f0-9]{64}$' -or $layer.mediaType -notmatch 'gzip$'){throw 'STOP: unexpected layer digest or compression'}
$hash=$layer.digest.Substring(7)
& $curl --fail --location --retry 2 --silent --show-error --header "Authorization: Bearer $token" --output $rootfs "$registry/blobs/$($layer.digest)"
if($LASTEXITCODE -ne 0){throw 'STOP: Windows rootfs download failed'}
if((Get-FileHash -LiteralPath $rootfs -Algorithm SHA256).Hash.ToLowerInvariant() -ne $hash){throw 'STOP: Debian layer hash mismatch'}
Write-Host "DIAMOND_V12_ROOTFS_SHA256=$hash"
& $scp -o ConnectTimeout=12 $rootfs ($guest+':'+$remote)
if($LASTEXITCODE -ne 0){throw "STOP: SCP failed; files retained in $dir"}
$remoteScript=@'
set -eu
archive='__ARCHIVE__'
hash='__HASH__'
port='__PORT__'
id='__ID__'
base="cabal-diamond-debian-v12:$id"
builder="cabal-diamond-gcc14-v12-$id"
target='cabal-diamond-gcc14-v10:local'
cleanup() {
  docker rm -f "$builder" >/dev/null 2>&1 || true
  docker image rm "$base" >/dev/null 2>&1 || true
  rm -f -- "$archive"
}
trap cleanup EXIT
printf '%s  %s\n' "$hash" "$archive" | sha256sum -c -
if ! docker image inspect "$target" >/dev/null 2>&1; then
  echo DIAMOND_V12=IMPORTING_ISOLATED_DEBIAN
  docker import "$archive" "$base"
  proxy="socks5h://127.0.0.1:$port"
  docker create --name "$builder" --network host --security-opt no-new-privileges \
    "$base" /bin/sh -ec '
      proxy="$1"
      export DEBIAN_FRONTEND=noninteractive
      apt-get -o Acquire::http::Proxy="$proxy" -o Acquire::https::Proxy="$proxy" -o Acquire::Retries=2 -o APT::Update::Error-Mode=any update
      apt-get -o Acquire::http::Proxy="$proxy" -o Acquire::https::Proxy="$proxy" -o Acquire::Retries=2 install -y --no-install-recommends g++-14 binutils unixodbc-dev ca-certificates
      g++-14 -dumpfullversion -dumpversion
      rm -rf /var/lib/apt/lists/*
    ' sh "$proxy"
  echo DIAMOND_V12=INSTALLING_COMPILER_IN_ISOLATED_CONTAINER
  docker start -a "$builder"
  test "$(docker inspect -f '{{.State.ExitCode}}' "$builder")" = 0
  docker commit "$builder" "$target"
fi
version=$(docker run --rm --network none --entrypoint g++-14 "$target" -dumpfullversion -dumpversion)
case "$version" in 14.2.*) ;; *) echo "STOP: wrong compiler: $version"; exit 2;; esac
echo "DIAMOND_V12_GCC=$version"
echo DIAMOND_V12=REBUILDING_ORIGINAL_V14_OFFLINE
printf '%s' '__PAYLOAD__' | base64 -d | python3 -
echo DIAMOND_V12=COMPLETE
# EOF
'@
$remoteScript=$remoteScript.Replace('__ARCHIVE__',$remote).Replace('__HASH__',$hash).Replace('__PORT__',[string]$port).Replace('__ID__',$id).Replace('__PAYLOAD__',$payload)
$old=$OutputEncoding
try {
 $OutputEncoding=New-Object System.Text.UTF8Encoding($false)
 ($remoteScript.Replace([string][char]13,'')) | & $ssh -T -o ConnectTimeout=12 -o ExitOnForwardFailure=yes -o 'PermitRemoteOpen=deb.debian.org:80 deb.debian.org:443 security.debian.org:80 security.debian.org:443' -R "127.0.0.1:$port" $guest 'bash -s'
 $rc=$LASTEXITCODE
} finally {$OutputEncoding=$old}
if($rc -ne 0){throw "STOP: V12 isolated build failed SSH=$rc; Windows files retained in $dir"}
Remove-Item -LiteralPath $dir -Recurse -Force
Write-Host 'DIAMOND_V12=PASS_OFFLINE_COMPARISON'
