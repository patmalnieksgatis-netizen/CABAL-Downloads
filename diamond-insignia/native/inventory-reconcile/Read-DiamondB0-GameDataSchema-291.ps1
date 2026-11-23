# Read ONLY real Server01 inventory/WExp SQL system metadata from EP36_291_TEST.
# Never queries player rows or writes MSSQL, CABAL files, services, or VM.
$ErrorActionPreference = 'Stop'
$vbox = Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'
if (-not (Test-Path -LiteralPath $vbox)) { throw 'STOP: VBoxManage not found' }
$running = @(& $vbox list runningvms)
if ($LASTEXITCODE -ne 0 -or
    @($running | Where-Object { $_ -match '^"EP36_291_TEST"\s+\{' }).Count -ne 1) {
    throw 'STOP: wrong VM; EP36_291_TEST not running'
}
$u = 'https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads/012d0b04dc0ef0fade894a8ff9c91ffc5377edb8/diamond-insignia/native/inventory-reconcile/audit_live_inventory_schema.py'
$p = Join-Path $env:TEMP 'audit_live_inventory_schema.py'
Invoke-WebRequest -UseBasicParsing -Uri $u -OutFile $p -ErrorAction Stop
if (-not (Test-Path -LiteralPath $p) -or
    (Get-Item -LiteralPath $p).Length -lt 3000) {
    throw 'STOP: audit python source missing/short'
}
$source = [System.IO.File]::ReadAllText($p)
$savedEncoding = $OutputEncoding
try {
    $OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $out = @($source | & ssh.exe -T -o ConnectTimeout=12 root@192.168.56.101 'python3 -')
    $sshCode = $LASTEXITCODE
} finally {
    $OutputEncoding = $savedEncoding
}
if ($sshCode -ne 0 -or $out.Count -ne 1) {
    throw "STOP: Server01 audit failed; ssh exit $sshCode; unexpected line count $($out.Count)"
}
$report = $out[0] | ConvertFrom-Json
if ($report.mode -ne 'CABAL_DIAMOND_B0_METADATA_ONLY' -or
    $report.player_rows_read -ne $false -or
    $report.sql_mutations -ne $false -or
    $report.worldsvr_changed -ne $false) {
    throw 'STOP: unexpected metadata-only safety flags'
}
if ($report.status -ne 'PASS' -or $report.database -ne 'Server01') {
    throw "STOP: metadata read unavailable ($($report.reason))"
}
$dest = Join-Path $env:USERPROFILE ('Downloads\CABAL_DIAMOND_B0_GAMEDATA_SCHEMA_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.json')
[System.IO.File]::WriteAllText($dest,$out[0],(New-Object System.Text.UTF8Encoding($false)))
Write-Host 'DIAMOND_B0_SERVER01_METADATA=PASS'
foreach ($name in @('TABLE','COLUMN','PROCEDURE','PARAMETER')) {
    Write-Host "SQL_$name=$($report.counts.$name)"
}
Write-Host "SCHEMA_MAY_BE_TRUNCATED=$($report.result_may_be_truncated)"
foreach ($entry in @($report.inventory_wexp_candidates.column_candidates | Select-Object -First 8)) {
    Write-Host "STORAGE_CANDIDATE=$($entry.table).$($entry.column) [$($entry.type)]"
}
Write-Host "UPLOAD_SCHEMA_JSON=$dest"
Write-Host 'LIVE_GAME_FILES_SQL_WORLD_UNCHANGED=YES'
