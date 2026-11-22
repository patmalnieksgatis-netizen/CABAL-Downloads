param(
    [ValidateSet('Apply','Restore')][string]$Action = 'Apply',
    [string]$SourceRoot = 'F:\ CABAL',
    [string]$TestRoot = 'F:\CABAL_291_TEST',
    [string]$BackupRoot
)
$ErrorActionPreference = 'Stop'
function Need($ok,[string]$why) { if (!$ok) { throw $why } }
function Hash([string]$path) { Need (Test-Path -LiteralPath $path -PathType Leaf) ('FILE_MISSING='+$path); return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
$files = @'
[
  {
    "RelativePath": "Data/world/world1.enc",
    "SourceSHA256": "8cc32b59f30d84272b4a1427ea00ee370025bc08feb5af3bb6f25c72d15e0d4a",
    "TestSHA256": "73e069f11ee5f510d801c6c84068d819e895226145a018b5dc67220820231f87"
  },
  {
    "RelativePath": "Data/world/world2.enc",
    "SourceSHA256": "135dd53de56177b430cc9d40c52825bc979fea33771a6a7eaee932b5b82610f6",
    "TestSHA256": "707b34a30fc7f7b0b1bbe86774e8e75fd046c582d031e2b9e1cbd17060a97c89"
  },
  {
    "RelativePath": "Data/world/world3.enc",
    "SourceSHA256": "b7f1bdf441507bd093fcbd2f36ec92f51f98b2bd1a56cbf6ced66df911c0e0b2",
    "TestSHA256": "171f189d4e62b7a5f271a445f243a5bbb82f00223d97db2bd7c0dbda69c536b5"
  }
]
'@ | ConvertFrom-Json
Need (Test-Path -LiteralPath $TestRoot -PathType Container) 'TEST_FOLDER_MISSING'
$TestRoot = (Get-Item -LiteralPath $TestRoot).FullName
if (!$BackupRoot) {
    $documents = [Environment]::GetFolderPath('MyDocuments')
    Need (![string]::IsNullOrWhiteSpace($documents)) 'DOCUMENTS_FOLDER_UNAVAILABLE'
    $BackupRoot = Join-Path $documents 'CABAL291-MapBackups'
}
$backup = Join-Path $BackupRoot 'CabalPlay-Maps-20261122-v1'
$receiptPath = Join-Path $backup 'Receipt.json'
Need (@(Get-Process -Name CabalMain -ErrorAction SilentlyContinue).Count -eq 0) 'AIZVER_SPELI_UN_PALAID_KOMANDU_ATKARTOTI'
Need ((Hash (Join-Path $TestRoot 'Bin/x64/CabalMain.exe')) -eq '52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9') 'CLIENT_BUILD_DIFFERS'
Need ((Hash (Join-Path $TestRoot 'Bin/x64/libogg.dll')) -eq 'ceafa8291dcf090856a215285114270fea1a8978bc2d2b26b33bcb7b3ac5c2a9') 'WORKING_SDK_DIFFERS'
$hasReceipt = Test-Path -LiteralPath $receiptPath -PathType Leaf
if ($hasReceipt) {
    $receipt = Get-Content -Raw -LiteralPath $receiptPath | ConvertFrom-Json
    Need ($receipt.UpdateId -eq 'CabalPlay-Maps-20261122-v1' -and $receipt.TestRoot -eq $TestRoot) 'BACKUP_RECEIPT_DIFFERS'
    foreach ($file in $files) { Need ((Hash (Join-Path $backup $file.RelativePath)) -eq $file.TestSHA256) ('BACKUP_HASH_DIFFERS='+$file.RelativePath) }
}
foreach ($file in $files) {
    $current = Hash (Join-Path $TestRoot $file.RelativePath)
    if ($hasReceipt) { Need ($current -in @($file.TestSHA256,$file.SourceSHA256)) ('MAP_CHANGED_OUTSIDE_THIS_UPDATE='+$file.RelativePath) }
    else { Need ($current -eq $file.TestSHA256) ('ORIGINAL_MAP_DIFFERS='+$file.RelativePath) }
}
if ($Action -eq 'Apply') {
    if (!(Test-Path -LiteralPath $SourceRoot -PathType Container) -and $SourceRoot -eq 'F:\ CABAL' -and (Test-Path -LiteralPath 'F:\CABAL' -PathType Container)) { $SourceRoot = 'F:\CABAL' }
    Need (Test-Path -LiteralPath $SourceRoot -PathType Container) 'SOURCE_FOLDER_MISSING'
    Need ((Get-Item -LiteralPath $SourceRoot).FullName -ne $TestRoot) 'SOURCE_EQUALS_TEST'
    foreach ($file in $files) { Need ((Hash (Join-Path $SourceRoot $file.RelativePath)) -eq $file.SourceSHA256) ('SOURCE_MAP_DIFFERS='+$file.RelativePath) }
}
if (!$hasReceipt) {
    Need ($Action -eq 'Apply') 'NO_BACKUP_TO_RESTORE'
    Need (!(Test-Path -LiteralPath $backup)) ('BACKUP_FOLDER_ALREADY_EXISTS_WITHOUT_RECEIPT='+$backup)
    foreach ($file in $files) {
        $saved = Join-Path $backup $file.RelativePath
        [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($saved))
        Copy-Item -LiteralPath (Join-Path $TestRoot $file.RelativePath) -Destination $saved -ErrorAction Stop
        Need ((Hash $saved) -eq $file.TestSHA256) 'BACKUP_VERIFICATION_FAILED'
    }
    $receipt = [pscustomobject]@{UpdateId='CabalPlay-Maps-20261122-v1'; TestRoot=$TestRoot; State='ORIGINALS_BACKED_UP'; UTC=[datetime]::UtcNow.ToString('o')}
    $receipt | ConvertTo-Json | Set-Content -LiteralPath $receiptPath -Encoding UTF8 -ErrorAction Stop
}
'REZERVES_KOPIJA='+$backup
# Stage and verify every input before replacing any client file.
$stage = Join-Path $backup ('Stage-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($stage)
try {
    foreach ($file in $files) {
        $fromRoot = if ($Action -eq 'Apply') { $SourceRoot } else { $backup }
        $expected = if ($Action -eq 'Apply') { $file.SourceSHA256 } else { $file.TestSHA256 }
        $staged = Join-Path $stage ([IO.Path]::GetFileName($file.RelativePath))
        Copy-Item -LiteralPath (Join-Path $fromRoot $file.RelativePath) -Destination $staged -ErrorAction Stop
        Need ((Hash $staged) -eq $expected) 'STAGED_MAP_HASH_DIFFERS'
    }
    Need (@(Get-Process -Name CabalMain -ErrorAction SilentlyContinue).Count -eq 0) 'GAME_STARTED_DURING_UPDATE'
    try {
        foreach ($file in $files) {
            $staged = Join-Path $stage ([IO.Path]::GetFileName($file.RelativePath))
            Copy-Item -LiteralPath $staged -Destination (Join-Path $TestRoot $file.RelativePath) -Force -ErrorAction Stop
        }
        foreach ($file in $files) {
            $expected = if ($Action -eq 'Apply') { $file.SourceSHA256 } else { $file.TestSHA256 }
            Need ((Hash (Join-Path $TestRoot $file.RelativePath)) -eq $expected) 'INSTALLED_MAP_HASH_DIFFERS'
        }
        $receipt.State = if ($Action -eq 'Apply') { 'MAP_TRIAL_APPLIED_GAMEPLAY_PENDING' } else { 'ORIGINAL_MAPS_RESTORED' }
        $receipt.UTC = [datetime]::UtcNow.ToString('o')
        $receipt | ConvertTo-Json | Set-Content -LiteralPath $receiptPath -Encoding UTF8 -ErrorAction Stop
    } catch {
        $failure = $_
        foreach ($file in $files) {
            Copy-Item -LiteralPath (Join-Path $backup $file.RelativePath) -Destination (Join-Path $TestRoot $file.RelativePath) -Force -ErrorAction Stop
            Need ((Hash (Join-Path $TestRoot $file.RelativePath)) -eq $file.TestSHA256) ('ROLLBACK_FAILED; BACKUP='+$backup)
        }
        $receipt.State = 'ROLLED_BACK'
        $receipt.UTC = [datetime]::UtcNow.ToString('o')
        $receipt | ConvertTo-Json | Set-Content -LiteralPath $receiptPath -Encoding UTF8 -ErrorAction Stop
        throw $failure
    }
} finally { if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction Stop } }
$receipt.State
'PALAID_SPELI_AR_SAVU_PASREIZEJO_PALAIDEJU'
