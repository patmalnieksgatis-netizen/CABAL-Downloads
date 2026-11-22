# Collect actual candidate Merit resource files from the verified CABAL v291 x64 client tree.
# READ ONLY with respect to the client. Writes one new ZIP in the user's Downloads folder.
[CmdletBinding()]
param([string]$ClientRoot = 'F:\CABAL_291_TEST')
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$expectedExe = '52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9'
$root = (Resolve-Path -LiteralPath $ClientRoot -ErrorAction Stop).ProviderPath.TrimEnd('\')
$exe = Join-Path $root 'Bin\x64\CabalMain.exe'
if (-not [IO.File]::Exists($exe)) { throw "CLIENT_EXE_MISSING: $exe" }
$hash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
if ($hash -cne $expectedExe) { throw "REFUSE_WRONG_CLIENT_SHA256: $hash" }
$hits = @(Get-ChildItem -LiteralPath $root -Recurse -File -Filter 'meritsystem*.enc' -ErrorAction Stop |
    Where-Object { $_.Name -ieq 'meritsystem.enc' -or $_.Name -ieq 'meritsystem_msg.enc' } |
    Sort-Object FullName -Unique)
if ($hits.Count -eq 0) { throw 'MERIT_RESOURCES_NOT_FOUND_ANYWHERE_UNDER_CLIENT_ROOT' }
if ($hits.Count -gt 150) { throw "REFUSE_UNEXPECTED_FILE_COUNT: $($hits.Count)" }
$total = ($hits | Measure-Object -Property Length -Sum).Sum
if ($total -gt 128MB) { throw "REFUSE_UNEXPECTED_TOTAL_SIZE: $total" }
$manifestFiles = @()
foreach ($f in $hits) {
    $relative = $f.FullName.Substring($root.Length).TrimStart([char[]]@('\','/'))
    $sha = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $manifestFiles += [pscustomobject]@{
        path = ($relative -replace '\\', '/')
        size_bytes = [long]$f.Length
        sha256 = $sha
        language_path = ($relative -match '(?i)(\\|/)Language(\\|/)')
    }
    Write-Host "MERIT_FILE=$relative BYTES=$($f.Length) SHA256=$sha"
}
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$output = Join-Path ([Environment]::GetFolderPath('UserProfile')) 'Downloads\CABAL_v291_Merit_Actual_Path_Candidates_20261122.zip'
if ([IO.File]::Exists($output)) { throw "REFUSE_OVERWRITE_EXISTING_ARCHIVE: $output" }
$archive = [System.IO.Compression.ZipFile]::Open($output, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    for ($i = 0; $i -lt $hits.Count; $i++) {
        $f = $hits[$i]
        $relative = [string]$manifestFiles[$i].path
        [void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $archive, $f.FullName, $relative, [System.IO.Compression.CompressionLevel]::Optimal)
    }
    $manifest = [ordered]@{
        purpose = 'read_only_exact_v291_merit_language_resource_candidates'
        client_sha256 = $hash
        note = 'Static code shows language/fallback paths, actual runtime path not observed.'
        sources_modified = $false
        count = $hits.Count
        files = $manifestFiles
    }
    $entry = $archive.CreateEntry('manifest.json')
    $writer = [System.IO.StreamWriter]::new($entry.Open(), [System.Text.UTF8Encoding]::new($false))
    try { $writer.Write(($manifest | ConvertTo-Json -Depth 7)) } finally { $writer.Dispose() }
} finally { $archive.Dispose() }
Write-Host "COLLECTION=PASS ARCHIVE=$output COUNT=$($hits.Count)"
Write-Host 'GAME_FILES_CHANGED=NO;NO_PROCESS_OR_VM_ACCESS=YES'
