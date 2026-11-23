# CABAL v291: exact GameData Inventory/WarExp/Merit SQL metadata-only contract.
# EP36_291_TEST only. Reads sys.* catalog; no SQL, WorldSvr, client mutations.
$ErrorActionPreference = 'Stop'
$vbox = Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'
if (-not (Test-Path -LiteralPath $vbox)) { throw 'STOP: VBoxManage not found' }
$running = @(& $vbox list runningvms)
if ($LASTEXITCODE -ne 0 -or
    @($running | Where-Object { $_ -match '^"EP36_291_TEST"\s+\{' }).Count -ne 1) {
    throw 'STOP: EP36_291_TEST not running'
}
$u = 'https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads/bcd248f89552743f3813099170ff4f440a2cf282/diamond-insignia/native/inventory-reconcile/audit_verified_gamedata_contract.py'
$p = Join-Path $env:TEMP 'audit_verified_gamedata_contract.py'
Invoke-WebRequest -UseBasicParsing -Uri $u -OutFile $p -ErrorAction Stop
if ((Get-Item -LiteralPath $p).Length -lt 4000) { throw 'STOP: audit source is too short' }
$source = [System.IO.File]::ReadAllText($p)
$oldEncoding = $OutputEncoding
try {
    $OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $out = @($source | & ssh.exe -T -o ConnectTimeout=12 root@192.168.56.101 'python3 -')
    $sshCode = $LASTEXITCODE
} finally {
    $OutputEncoding = $oldEncoding
}
if ($sshCode -ne 0 -or $out.Count -ne 1) {
    throw "STOP: contract auditor SSH=$sshCode output_lines=$($out.Count)"
}
$report = $out[0] | ConvertFrom-Json
if ($report.mode -ne 'CABAL_V291_REAL_GAMEDATA_CONTRACT' -or
    $report.status -ne 'PASS' -or
    $report.database -ne 'Server01' -or
    $report.metadata_only -ne $true -or
    $report.game_player_rows_read -ne $false -or
    $report.sql_mutations -ne $false -or
    $report.worldsvr_changed -ne $false) {
    throw "STOP: audit not verified ($($report.reason))"
}
$path = Join-Path $env:USERPROFILE ('Downloads\CABAL_V291_REAL_GAMEDATA_CONTRACT_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.json')
[System.IO.File]::WriteAllText($path,$out[0],(New-Object System.Text.UTF8Encoding($false)))
Write-Host 'DIAMOND_V291_GAMEDATA_CONTRACT=PASS'
foreach ($key in @('TABLE','COLUMN','INDEX','TRIGGER','PROCEDURE','PARAMETER','MODULE')) {
    Write-Host "CATALOG_$key=$($report.counts.$key)"
}
foreach ($entry in @($report.catalog.INDEX | Where-Object { $_[4] -eq '1' })) {
    Write-Host "PRIMARY_KEY=$($entry[0]).$($entry[1]).$($entry[6])"
}
Write-Host "UPLOAD_CONTRACT_JSON=$path"
Write-Host 'GAME_PLAYER_ROWS_SQL_VM_UNMODIFIED=YES'
