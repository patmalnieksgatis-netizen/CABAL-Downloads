[CmdletBinding()]
param([string]$SshTarget='root@192.168.56.101')
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$url='https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads/58428070f44cd011481db32972703ec2fc2b4581/diamond-insignia/worldsvr-ingress/trace_native_session_lifecycle.py'
$expected='32622ab07599b62ffc4653011b423f99a9c12d89b06b11aed03cba4b8cfac633'
$temp=Join-Path $env:TEMP ('Diamond-Trace-'+[guid]::NewGuid().ToString('N')+'.py')
$folder=Join-Path $env:USERPROFILE 'Downloads'
[void][IO.Directory]::CreateDirectory($folder)
$name='Diamond-NativeLifecycle-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[guid]::NewGuid().ToString('N').Substring(0,6)+'.txt'
$report=Join-Path $folder $name
$utf8=New-Object Text.UTF8Encoding($false)
[IO.File]::WriteAllText($report,'',$utf8)
try {
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $temp -ErrorAction Stop
    if((Get-FileHash -LiteralPath $temp -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
        throw 'TRACE_SOURCE_HASH_DIFFERS'
    }
    $code=[IO.File]::ReadAllText($temp)
    Write-Host 'GAIDI DIAMOND_TRACE_READY; TAD IZEJ LIDZ TELU IZVELEI UN IELOGOJIES ATPAKAL.'
    Write-Host 'NOVEROJU LIDZ 45 SEKUNDEM VAI 12 IZSAUKUMIEM.'
    Write-Host 'GDB PIEVIENOSANAS BRIDI CH1 VAR ISLAICIGI IEPAUZET.'
    $saved=$OutputEncoding
    $complete=$false
    try {
        $OutputEncoding=$utf8
        $code | ssh.exe -T -o ConnectTimeout=12 $SshTarget 'python3 -' | ForEach-Object {
            Write-Host $_
            [IO.File]::AppendAllText($report,([string]$_+[Environment]::NewLine),$utf8)
            if($_ -eq 'DIAMOND_LIFECYCLE_TRACE_COMPLETE') {$complete=$true}
        }
        $status=$LASTEXITCODE
    } finally {$OutputEncoding=$saved}
    if($status -ne 0 -or !$complete) {throw 'TRACE_NAV_APSTIPRINATS; ATSUTI_ATSKAITI'}
} finally {
    Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
    Write-Host "UPLOAD=$report"
}
