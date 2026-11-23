# Read-only Diamond V5 ELF audit. Never writes to guest or game files.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$vbox=Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'
if (-not (Test-Path -LiteralPath $vbox)) { throw 'STOP: VBoxManage missing' }
$running=@(& $vbox list runningvms)
if ($LASTEXITCODE -ne 0 -or @($running | Where-Object { $_ -match '^"EP36_291_TEST"\s+\{' }).Count -ne 1) {
    throw 'STOP: EP36_291_TEST is not running'
}
$revision='d17c7ca06d6b15dcce8c5976349d666139af1be6'
$url="https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads/$revision/diamond-insignia/worldsvr-ingress/Audit-DiamondV14-0BDA-ELF-V5.py"
$local=Join-Path $env:TEMP 'Audit-DiamondV14-0BDA-ELF-V5.py'
Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $local -ErrorAction Stop
$src=[System.IO.File]::ReadAllText($local)
if (-not $src.Contains('READ_ONLY_ELF_AUDIT_COMPLETE') -or -not $src.Contains('strict_compatibility_proven')) { throw 'STOP: unexpected audit source' }
$old=$OutputEncoding
try {
    $OutputEncoding=New-Object System.Text.UTF8Encoding($false)
    $output=@($src | & ssh.exe -T -o ConnectTimeout=12 root@192.168.56.101 'python3 -')
    $rc=$LASTEXITCODE
} finally { $OutputEncoding=$old }
foreach ($line in $output) { Write-Host $line }
if ($rc -ne 0 -or -not (($output -join "`n").Contains('END_DIAMOND_V5_ELF_AUDIT'))) {
    throw "STOP: ELF audit unsuccessful (SSH=$rc); active files unchanged"
}
Write-Host 'DIAMOND_V5_ELF_AUDIT=PASS_READ_ONLY'
