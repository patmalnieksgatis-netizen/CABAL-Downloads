param(
    [string]$SourceRoot = 'F:\ CABAL',
    [string]$TestRoot = 'F:\CABAL_291_TEST',
    [string]$OutputRoot = [Environment]::GetFolderPath('DesktopDirectory')
)
$ErrorActionPreference = 'Stop'
if (!(Test-Path -LiteralPath $SourceRoot -PathType Container) -and $SourceRoot -eq 'F:\ CABAL' -and (Test-Path -LiteralPath 'F:\CABAL' -PathType Container)) {
    $SourceRoot = 'F:\CABAL'
}
if (!(Test-Path -LiteralPath $SourceRoot -PathType Container)) { throw ('SOURCE_FOLDER_MISSING='+$SourceRoot) }
if (!(Test-Path -LiteralPath $TestRoot -PathType Container)) { throw ('TEST_FOLDER_MISSING='+$TestRoot) }
$SourceRoot = (Get-Item -LiteralPath $SourceRoot).FullName.TrimEnd([IO.Path]::DirectorySeparatorChar)
$TestRoot = (Get-Item -LiteralPath $TestRoot).FullName.TrimEnd([IO.Path]::DirectorySeparatorChar)
if ($SourceRoot -eq $TestRoot) { throw 'SOURCE_AND_TEST_ARE_THE_SAME_FOLDER' }
if (!$OutputRoot) { throw 'OUTPUT_FOLDER_REQUIRED' }
$folder = Join-Path $OutputRoot ('CabalPlay-MapUpdate-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[guid]::NewGuid().ToString('N').Substring(0,6))
[void][IO.Directory]::CreateDirectory($folder)
function Relative([string]$root,[string]$file) { return $file.Substring($root.Length+1).Replace('\','/') }
function Files([string]$root) {
    $data = Join-Path $root 'Data'
    if (!(Test-Path -LiteralPath $data -PathType Container)) { throw ('DATA_FOLDER_MISSING='+$data) }
    Get-ChildItem -LiteralPath $data -File -Recurse -ErrorAction Stop
    foreach ($name in @('Bin/x64/CabalMain.exe','CabalMain.exe')) {
        $path = Join-Path $root $name
        if (Test-Path -LiteralPath $path -PathType Leaf) { Get-Item -LiteralPath $path }
    }
}
function StableHash([IO.FileInfo]$file) {
    $file.Refresh()
    $length = $file.Length
    $written = $file.LastWriteTimeUtc.Ticks
    $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()
    $file.Refresh()
    if (!$file.Exists -or $file.Length -ne $length -or $file.LastWriteTimeUtc.Ticks -ne $written) {
        throw 'FILE_CHANGED_DURING_SCAN'
    }
    return $hash
}
$source = @(Files $SourceRoot)
$target = [Collections.Generic.Dictionary[string,IO.FileInfo]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($file in @(Files $TestRoot)) { $target.Add((Relative $TestRoot $file.FullName),$file) }
$rows = [Collections.Generic.List[object]]::new()
$errors = [Collections.Generic.List[object]]::new()
$executables = [Collections.Generic.List[object]]::new()
$changed = 0
$added = 0
$checked = 0
"SALIDZINU=$SourceRoot"
"AR_TESTA_KLIENTU=$TestRoot"
foreach ($file in $source) {
    $relative = Relative $SourceRoot $file.FullName
    $other = $null
    [void]$target.TryGetValue($relative,[ref]$other)
    try {
        $sourceHash = StableHash $file
        $targetHash = if ($null -ne $other) { StableHash $other } else { '' }
        $status = if ($null -eq $other) { 'ADDED' } elseif ($sourceHash -eq $targetHash) { 'SAME' } else { 'CHANGED' }
        if ($status -eq 'ADDED') { $added++ }
        if ($status -eq 'CHANGED') { $changed++ }
        $row = [pscustomobject]@{
            RelativePath=$relative
            Status=$status
            SourceBytes=$file.Length
            TestBytes=$(if ($null -ne $other) { $other.Length } else { $null })
            SourceSHA256=$sourceHash
            TestSHA256=$targetHash
            SourceWriteUTC=$file.LastWriteTimeUtc.ToString('o')
            TestWriteUTC=$(if ($null -ne $other) { $other.LastWriteTimeUtc.ToString('o') } else { '' })
        }
        $rows.Add($row)
        if ($file.Name -eq 'CabalMain.exe') {
            $sourceVersion = ''
            $testVersion = ''
            try { $sourceVersion = [Diagnostics.FileVersionInfo]::GetVersionInfo($file.FullName).FileVersion } catch {}
            if ($null -ne $other) {
                try { $testVersion = [Diagnostics.FileVersionInfo]::GetVersionInfo($other.FullName).FileVersion } catch {}
            }
            $executables.Add([pscustomobject]@{
                RelativePath=$relative
                Status=$status
                SourceSHA256=$sourceHash
                TestSHA256=$targetHash
                SourceVersion=$sourceVersion
                TestVersion=$testVersion
            })
        }
    } catch {
        $errors.Add([pscustomobject]@{RelativePath=$relative;Error=$_.Exception.GetBaseException().Message})
    }
    if ($null -ne $other) { [void]$target.Remove($relative) }
    $checked++
    if ($checked % 100 -eq 0) {
        Write-Progress -Activity 'CabalPlay failu salidzinasana' -Status ("$checked / $($source.Count)") -PercentComplete ([int](100*$checked/[Math]::Max(1,$source.Count)))
    }
}
Write-Progress -Activity 'CabalPlay failu salidzinasana' -Completed
$rows | Export-Csv -LiteralPath (Join-Path $folder 'Compared-Files.csv') -NoTypeInformation -Encoding UTF8
@($rows | Where-Object {$_.Status -ne 'SAME'}) | Export-Csv -LiteralPath (Join-Path $folder 'Differences.csv') -NoTypeInformation -Encoding UTF8
$target.Keys | Sort-Object | ForEach-Object {[pscustomobject]@{RelativePath=$_}} |
    Export-Csv -LiteralPath (Join-Path $folder 'Only-In-Test.csv') -NoTypeInformation -Encoding UTF8
$errors | Export-Csv -LiteralPath (Join-Path $folder 'Errors.csv') -NoTypeInformation -Encoding UTF8
$summary = [ordered]@{
    Scope='READ_ONLY_DATA_AND_CABALMAIN_COMPARISON'
    SourceRoot=$SourceRoot
    TestRoot=$TestRoot
    UTC=[DateTime]::UtcNow.ToString('o')
    Checked=$checked
    Changed=$changed
    Added=$added
    OnlyInTest=$target.Count
    Errors=$errors.Count
    Executables=$executables.ToArray()
}
$summary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $folder 'Summary.json') -Encoding UTF8
$zip = $folder+'.zip'
Compress-Archive -LiteralPath @(Get-ChildItem -LiteralPath $folder -File | Select-Object -ExpandProperty FullName) -DestinationPath $zip -ErrorAction Stop
"PARBAUDITI=$checked; MAINITI=$changed; JAUNI=$added; KLUDAS=$($errors.Count)"
"ZIP=$zip"
