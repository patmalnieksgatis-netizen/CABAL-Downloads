$ErrorActionPreference = 'Stop'
$root = 'https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads/main'
$dir = Join-Path $env:TEMP ([guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $dir | Out-Null
foreach ($file in 'Mandarat-Six-R1.zip','Apply-Mandarat-Six-R1.py') {
    Invoke-WebRequest -UseBasicParsing "$root/$file" -OutFile "$dir\$file"
}
scp "$dir\Mandarat-Six-R1.zip" "$dir\Apply-Mandarat-Six-R1.py" root@192.168.56.101:/tmp/
if ($LASTEXITCODE -ne 0) { throw 'COPY_FAILED' }
ssh root@192.168.56.101 python3 /tmp/Apply-Mandarat-Six-R1.py --six
if ($LASTEXITCODE -ne 0) { throw 'UPDATE_NOT_CONFIRMED' }
