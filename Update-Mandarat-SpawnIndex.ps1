$ErrorActionPreference = 'Stop'
$root = 'https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads/d52c784f58076c7b791258e5809810e5ec085fdf'
$dir = Join-Path $env:TEMP ([guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $dir | Out-Null
$files = @('Mandarat-SpawnIndex-R2.zip','Apply-Mandarat-SpawnIndex-R2.py')
$paths = foreach ($file in $files) {
    $path = Join-Path $dir $file
    Invoke-WebRequest -UseBasicParsing "$root/$file" -OutFile $path
    $path
}
scp @paths root@192.168.56.101:/tmp/
if ($LASTEXITCODE -ne 0) { throw 'COPY_FAILED' }
ssh root@192.168.56.101 'python3 /tmp/Apply-Mandarat-SpawnIndex-R2.py --six'
if ($LASTEXITCODE -ne 0) { throw 'SPAWN_UPDATE_NOT_CONFIRMED' }
