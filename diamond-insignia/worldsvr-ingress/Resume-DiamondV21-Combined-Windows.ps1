$ErrorActionPreference = 'Stop'
$repo = 'https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads'
$ref = '70ce83102b57c1816419f7449ca714085e54c1e9'
$builderRef = '238fe0178a5a4500a0e40aa917a5902cc6746cd8'
$id = [Guid]::NewGuid().ToString('N')
$work = Join-Path $env:TEMP "DiamondV21-$id"
$root = Join-Path $work 'src'
New-Item -ItemType Directory -Path $root -Force | Out-Null
$root = [IO.Path]::GetFullPath($root)
$seen = @{}
function Fetch-Source([string]$relative) {
    $local = [IO.Path]::GetFullPath((Join-Path $root ($relative.Replace('/','\'))))
    if (-not $local.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)) { throw "Invalid include: $relative" }
    $relative = $local.Substring($root.Length+1).Replace('\','/')
    if ($seen.ContainsKey($relative)) { return }
    $seen[$relative] = $true
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $local) | Out-Null
    Invoke-WebRequest -UseBasicParsing -Uri "$repo/$ref/diamond-insignia/$relative" -OutFile $local -ErrorAction Stop
    $source = [IO.File]::ReadAllText($local)
    foreach ($match in [regex]::Matches($source,'(?m)^\s*#\s*include\s*"([^"]+)"')) {
        $child = [IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $local) $match.Groups[1].Value))
        if (-not $child.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)) { throw "Include outside package: $child" }
        Fetch-Source ($child.Substring($root.Length+1).Replace('\','/'))
    }
}
$units = @(
 'worldsvr-ingress/DiamondNativeRankUpV20.h',
 'worldsvr-ingress/test_native_rankup_v20.cpp',
 'native/grade2-ingress/DiamondGradeUp0BDA.cpp',
 'native/grade2-ingress/Diamond0BDATicketSelection.cpp',
 'native/grade2-ingress/Diamond0BDAGameplayAction.cpp',
 'native/grade2-ingress/Diamond0BDAAuthenticatedIngress.cpp',
 'native/real-gamedata-transaction/DiamondRealGameDataOdbc.cpp',
 'native/real-gamedata-transaction/Diamond0BDARealServer01Bridge.cpp',
 'native/world-save-barrier/DiamondWorldSaveBarrier.cpp',
 'native/grade2-ingress/Diamond0BDASaveReplyGate.cpp'
)
foreach ($unit in $units) { Fetch-Source $unit }
Write-Host "V21_SOURCE_FILES=$($seen.Count)"
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zipName = "diamond-v21-$id.zip"
$pyName = "diamond-v21-$id.py"
$zip = Join-Path $work $zipName
$py = Join-Path $work $pyName
[IO.Compression.ZipFile]::CreateFromDirectory($root,$zip)
Invoke-WebRequest -UseBasicParsing -Uri "$repo/$builderRef/diamond-insignia/worldsvr-ingress/Build-DiamondV21-Combined.py" -OutFile $py -ErrorAction Stop
& scp $zip $py 'root@192.168.56.101:/tmp/'
if ($LASTEXITCODE -ne 0) { throw 'SCP failed' }
& ssh -T root@192.168.56.101 "python3 /tmp/$pyName /tmp/$zipName"
if ($LASTEXITCODE -ne 0) { throw 'V21 build failed; active game unchanged' }
Write-Host 'V21_BUILD_ONLY: no install, no restart, no database write'
