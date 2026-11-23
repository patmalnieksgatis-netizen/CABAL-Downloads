# CABAL v291: resume ONLY the existing /tmp offline 0BDA build (no re-upload).
# Prior VM attempt already staged all source files on EP36_291_TEST.
# No game file replacement, SQL, supervisorctl, world restart or preload.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$vbox=Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'
if (-not (Test-Path -LiteralPath $vbox)) { throw 'STOP: VBoxManage missing' }
$running=@(& $vbox list runningvms)
if ($LASTEXITCODE -ne 0 -or
    @($running | Where-Object { $_ -match '^"EP36_291_TEST"\s+\{' }).Count -ne 1) {
    throw 'STOP: EP36_291_TEST is not running'
}
$rev='6848484dfb5e006bcbe178676db8fda22f1fe5e4'
$url="https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads/$rev/diamond-insignia/worldsvr-ingress/Build-DiamondV14Real0BDAOffline.py"
$local=Join-Path $env:TEMP 'Build-DiamondV14Real0BDAOffline-v2.py'
Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $local -ErrorAction Stop
if ((Get-Item -LiteralPath $local).Length -lt 8000) {
    throw 'STOP: unexpected short offline source'
}
$script=[System.IO.File]::ReadAllText($local)
if (-not $script.Contains('OFFLINE_RECONSTRUCTED_TOOLCHAIN_WEAK_DRIFT') -or
    -not $script.Contains('compare_exports')) {
    throw 'STOP: downloaded source missing dual-build diagnostics'
}
$remoteRoot='/tmp/cabal_diamond_v291_0bda_source_20261123/diamond-insignia/worldsvr-ingress'
$remoteScript="$remoteRoot/Build-DiamondV14Real0BDAOffline.py"
$out='/tmp/cabal_diamond_v291_0bda_offline_build_20261123_v2'
$src='/root/CABAL_V282_LIVE_MERGE_CANDIDATE_v14/source_tree/src'
$base='/root/cabal_diamond_backup/lib.so_before_diamond_20261122'
$guest='root@192.168.56.101'
$command="set -eu; test " + '$(hostname)' + " = 'cabalep33'; test -d '$remoteRoot'; test -f '$src/hooks/Handlers/ProcSystem.cpp'; test -f '$base'; test ! -e '$out'; cat > '$remoteScript'; python3 '$remoteScript' --source '$src' --baseline-lib '$base' --output-dir '$out'; echo BEGIN_DIAMOND_OFFLINE_REPORT; cat '$out/OFFLINE_BUILD_RESULT.json'; echo END_DIAMOND_OFFLINE_REPORT"
$oldEncoding=$OutputEncoding
try {
    $OutputEncoding=New-Object System.Text.UTF8Encoding($false)
    $lines=@($script | & ssh.exe -T -o ConnectTimeout=12 $guest $command)
    $rc=$LASTEXITCODE
} finally { $OutputEncoding=$oldEncoding }
foreach ($line in $lines) { Write-Host $line }
if ($rc -ne 0) {
    throw "STOP: offline dual-build diagnostic failed (SSH=$rc); live WorldSvr unchanged"
}
$joined=$lines -join [Environment]::NewLine
$match=[regex]::Match($joined,'(?s)BEGIN_DIAMOND_OFFLINE_REPORT\s*(\{.*?\})\s*END_DIAMOND_OFFLINE_REPORT')
if (-not $match.Success) { throw 'STOP: expected offline ABI report missing' }
$report=$match.Groups[1].Value | ConvertFrom-Json
if ($report.active_worldsvr_modified -ne $false -or
    $report.sql_game_data_modified -ne $false -or
    $report.can_install_on_active_worldsvr -ne $false) {
    throw 'STOP: unsafe offline report flags'
}
Write-Host "DIAMOND_REAL0BDA_ABI_RESULT=$($report.status)"
Write-Host "MISSING_STRONG_EXPORTS=$(@($report.missing_strong_exports_patched).Count)"
Write-Host "KNOWN_STDLIB_WEAK_EXPORT_DIFF=$(@($report.known_weak_template_missing_in_both).Count)"
Write-Host "HOOK_NEWLY_LOST_EXPORTS=$(@($report.patch_lost_reconstructed_exports).Count)"
Write-Host "DIAMOND_HOOK_FUNCTION_RVA_MOVES=$($report.source_hook_changed_exported_function_rvas)"
Write-Host 'WORLD_SVR_SQL_GAME_FILES_UNCHANGED=YES'
Write-Host 'UPLOAD_OR_PASTE_REPORT_ABOVE=YES'
