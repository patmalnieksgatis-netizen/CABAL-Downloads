$ErrorActionPreference = 'Stop'
$root = 'https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads/503cfb74739281b323f1666615b5e297cd3d0b2e'
$dir = Join-Path $env:TEMP ([guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $dir | Out-Null
$files = @('Mandarat-Lv1-Ticket.zip','Apply-Mandarat-Lv1-Ticket.py','Send-Storm-NativeRelic.py')
$paths = foreach ($file in $files) {
    $path = Join-Path $dir $file
    Invoke-WebRequest -UseBasicParsing "$root/$file" -OutFile $path
    $path
}
scp @paths root@192.168.56.101:/tmp/
if ($LASTEXITCODE -ne 0) { throw 'COPY_FAILED' }
ssh root@192.168.56.101 'python3 /tmp/Apply-Mandarat-Lv1-Ticket.py --six && python3 /tmp/Send-Storm-NativeRelic.py'
if ($LASTEXITCODE -ne 0) { throw 'TICKET_UPDATE_NOT_CONFIRMED' }
