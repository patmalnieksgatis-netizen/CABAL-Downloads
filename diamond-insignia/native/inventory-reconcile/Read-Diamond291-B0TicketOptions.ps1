# CABAL EP36_291_TEST: read-only deidentified Merit Ticket itemOption sample.
# IMPORTANT: reads actual inventory rows but exports only item 33554961's
# 8-byte option (at most 48) and 3 anonymous blob lengths.
# No account name/number, CharacterIdx, serial or item blobs leave the VM.
$ErrorActionPreference='Stop'
$vbox=Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'
if (-not (Test-Path -LiteralPath $vbox)) { throw 'STOP: VBoxManage not found' }
$vmInfo=@(& $vbox list runningvms)
if ($LASTEXITCODE -ne 0 -or
    @($vmInfo | Where-Object { $_ -match '^"EP36_291_TEST"\s+\{' }).Count -ne 1) {
    throw 'STOP: EP36_291_TEST is not running'
}
$u='https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads/94d27dd518c91f0277c15d44c0e3e850ab153418/diamond-insignia/native/inventory-reconcile/probe_live_b0_ticket_options.py'
$p=Join-Path $env:TEMP 'probe_live_b0_ticket_options.py'
Invoke-WebRequest -UseBasicParsing -Uri $u -OutFile $p -ErrorAction Stop
if ((Get-Item -LiteralPath $p).Length -lt 3000) {
    throw 'STOP: downloaded Python source is unexpectedly short'
}
$source=[System.IO.File]::ReadAllText($p)
$prior=$OutputEncoding
try {
    $OutputEncoding=New-Object System.Text.UTF8Encoding($false)
    $out=@($source | & ssh.exe -T -o ConnectTimeout=12 root@192.168.56.101 'python3 -')
    $rc=$LASTEXITCODE
} finally { $OutputEncoding=$prior }
if ($rc -ne 0 -or $out.Count -ne 1) {
    throw "STOP: B0 sample audit error SSH=$rc LINES=$($out.Count)"
}
$report=$out[0] | ConvertFrom-Json
if ($report.mode -ne 'CABAL_291_B0_TICKET_RAW_OPTIONS' -or
    $report.status -ne 'PASS' -or
    $report.read_only -ne $true -or
    $report.target_item_id -ne 33554961 -or
    $report.sql_mutations -ne $false -or
    $report.player_identifiers_exported -ne $false -or
    $report.item_serials_exported -ne $false -or
    $report.quantity_codec_verified -ne $false -or
    @($report.matching_ticket_option_sample).Count -gt 48) {
    throw "STOP: unsupported probe output or unsafe flags ($($report.reason))"
}
$dest=Join-Path $env:USERPROFILE ('Downloads\CABAL_V291_B0_TICKET_OPTIONS_'+(Get-Date -Format 'yyyyMMdd_HHmmss')+'.json')
[System.IO.File]::WriteAllText($dest,$out[0],(New-Object System.Text.UTF8Encoding($false)))
Write-Host 'DIAMOND_B0_GAMEDATA_TICKET_OPTIONS_READ_ONLY=PASS'
Write-Host "ANON_BLOB_LENGTHS=$(@($report.anonymous_blob_length_samples).Count)"
Write-Host "MATCHING_TICKET_RECORDS=$($report.matching_ticket_record_count_in_sample)"
Write-Host "SAMPLE_MAY_BE_TRUNCATED=$($report.sample_may_be_truncated)"
Write-Host "UPLOAD_TICKET_OPTIONS_JSON=$dest"
Write-Host 'LIVE_WORLD_AND_SQL_UNMODIFIED=YES'
