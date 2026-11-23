# Diamond Insignia: collect only game definition files needed for the EP45 -> v291 comparison.
# No game files, VM configuration, SQL or services are changed.
[CmdletBinding()]
param(
    [string]$ClientRoot = 'F:\CABAL_291_TEST',
    [string]$EP45Root = "$env:USERPROFILE\Downloads\CABAL Transcendence (UTS)\CABAL Transcendence (UTS)",
    [string]$Vm = 'root@192.168.56.101',
    [string]$Container = 'cabal_main'
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
Write-Host 'CABAL_DIAMOND_SOURCE_COLLECTION=READ_ONLY'
Write-Host "V291_CLIENT_ROOT=$ClientRoot"
Write-Host "EP45_DONOR_ROOT=$EP45Root"
Write-Host 'VM_OR_CLIENT_MODIFICATIONS=NO'

$downloads = Join-Path $env:USERPROFILE 'Downloads'
$unique = [guid]::NewGuid().ToString('N').Substring(0,10)
$work = Join-Path $env:TEMP ('CABAL-Diamond-Sources-' + $unique)
$zip = Join-Path $downloads ('CABAL-DIAMOND-SOURCES-' + $unique + '.zip')
New-Item -ItemType Directory -Path $work -Force | Out-Null
$files = New-Object System.Collections.Generic.List[object]

function Copy-DefinitionFile {
    param([string]$Source, [string]$Dest, [bool]$Required = $false)
    if (!(Test-Path -LiteralPath $Source -PathType Leaf)) {
        if ($Required) { throw "REQUIRED_FILE_MISSING: $Source" }
        Write-Host "OPTIONAL_FILE_MISSING=$Source"
        return
    }
    $original = Get-Item -LiteralPath $Source
    if ($original.Length -le 0 -or $original.Length -gt 2MB) {
        throw "UNEXPECTED_DEFINITION_SIZE: $Source size=$($original.Length)"
    }
    $destination = Join-Path $work $Dest
    $parent = Split-Path -Parent $destination
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    $sourceHash = (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash.ToLowerInvariant()
    Copy-Item -LiteralPath $Source -Destination $destination -ErrorAction Stop
    $copyHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($sourceHash -ne $copyHash) { throw "COPY_HASH_MISMATCH: $Dest" }
    $script:files.Add([pscustomobject]@{source=$Source;archive_path=$Dest.Replace('\','/');bytes=$original.Length;sha256=$copyHash})
    Write-Host ("SOURCE_COPIED=" + $Dest.Replace('\','/') + ';bytes=' + $original.Length + ';sha256=' + $copyHash)
}

try {
    # The actual v291 target from the prior project tooling. Never use an older
    # CABALOnline/EP35/EP275 client as an automatic substitute.
    Copy-DefinitionFile -Source (Join-Path $ClientRoot 'Data\meritsystem.enc') -Dest 'client\v291\meritsystem.enc' -Required $true
    Copy-DefinitionFile -Source (Join-Path $ClientRoot 'Data\Language\English\meritsystem_msg.enc') -Dest 'client\v291\Language\English\meritsystem_msg.enc'
    Copy-DefinitionFile -Source (Join-Path $ClientRoot 'Data\Language\Korean\meritsystem_msg.enc') -Dest 'client\v291\Language\Korean\meritsystem_msg.enc'
    Copy-DefinitionFile -Source (Join-Path $EP45Root 'data\meritsystem.enc') -Dest 'client\ep45\meritsystem.enc' -Required $true
    Copy-DefinitionFile -Source (Join-Path $EP45Root 'data\Language\Korean\meritsystem_msg.enc') -Dest 'client\ep45\Language\Korean\meritsystem_msg.enc'

    # This is a narrow, read-only export of one configuration table. It does NOT
    # read SQL, account records, character data, secrets or server binaries.
    $guestPython = @'
import base64,hashlib,json
from pathlib import Path
p=Path('/etc/cabal/Data/MeritSystem.scp')
if not p.is_file(): raise SystemExit('STOP: VM_MERITSYSTEM_SCP_MISSING')
b=p.read_bytes()
if not 1 <= len(b) <= 2*1024*1024: raise SystemExit('STOP: VM_MERITSYSTEM_SCP_SIZE_UNEXPECTED')
print('DIAMOND_SCP_EXPORT_JSON_BEGIN')
print(json.dumps({'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(), 'content_b64':base64.b64encode(b).decode('ascii')},separators=(',',':')))
print('DIAMOND_SCP_EXPORT_JSON_END')
'@
    $savedEncoding = $OutputEncoding
    try {
        $OutputEncoding = New-Object System.Text.UTF8Encoding($false)
        $lines = @($guestPython | & ssh.exe -T -o ConnectTimeout=10 $Vm "docker exec -i $Container python3 -")
        $exitCode = $LASTEXITCODE
    } finally {
        $OutputEncoding = $savedEncoding
    }
    if ($exitCode -ne 0) { throw "SERVER_READ_FAILED: ssh_exit=$exitCode" }
    $a = [Array]::IndexOf($lines, 'DIAMOND_SCP_EXPORT_JSON_BEGIN')
    $b = [Array]::IndexOf($lines, 'DIAMOND_SCP_EXPORT_JSON_END')
    if ($a -lt 0 -or $b -ne ($a+2)) { throw 'SERVER_READ_FORMAT_ERROR' }
    $result = $lines[$a+1] | ConvertFrom-Json
    $remoteBytes = [Convert]::FromBase64String($result.content_b64)
    if ($remoteBytes.Length -ne [int]$result.bytes) { throw 'SERVER_DATA_LENGTH_MISMATCH' }
    $hash = [System.Security.Cryptography.SHA256]::Create()
    try { $remoteHash = ([BitConverter]::ToString($hash.ComputeHash($remoteBytes))).Replace('-','').ToLowerInvariant() }
    finally { $hash.Dispose() }
    if ($remoteHash -ne [string]$result.sha256) { throw 'SERVER_DATA_HASH_MISMATCH' }
    $serverPath = Join-Path $work 'server\active-v291\MeritSystem.scp'
    New-Item -ItemType Directory -Path (Split-Path -Parent $serverPath) -Force | Out-Null
    [IO.File]::WriteAllBytes($serverPath,$remoteBytes)
    $files.Add([pscustomobject]@{source=$result.path;archive_path='server/active-v291/MeritSystem.scp';bytes=$remoteBytes.Length;sha256=$remoteHash})
    Write-Host "ACTIVE_SERVER_SCP_SHA256=$remoteHash"

    $manifest = [ordered]@{
        schema = 1
        created_utc = [DateTime]::UtcNow.ToString('o')
        mode = 'READ_ONLY_SELECTED_DEFINITIONS'
        sql_exported = $false
        client_or_vm_files_modified = $false
        client_root = $ClientRoot
        ep45_root = $EP45Root
        files = @($files.ToArray())
        note = 'Only two MeritSystem.enc files and a server MeritSystem.scp, plus optional message files. No account/character data.'
    }
    $json = $manifest | ConvertTo-Json -Depth 8
    $manifestPath = Join-Path $work 'MANIFEST.json'
    [IO.File]::WriteAllText($manifestPath,$json, (New-Object System.Text.UTF8Encoding($false)))

    # Do not place files from another earlier attempt in the export archive.
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory($work,$zip,[System.IO.Compression.CompressionLevel]::Optimal,$false)
    $archive = [System.IO.Compression.ZipFile]::OpenRead($zip)
    try {
        # Normalize ZIP entry separators (Windows uses backslashes for .NET Framework archives).
        $names = @($archive.Entries | ForEach-Object { $_.FullName.Replace('\','/') })
        foreach ($entry in $files) {
            if ($names -notcontains $entry.archive_path) { throw "ZIP_MISSING: $($entry.archive_path)" }
        }
        if ($names -notcontains 'MANIFEST.json') { throw 'ZIP_MANIFEST_MISSING' }
    } finally { $archive.Dispose() }
    Write-Host "DIAMOND_SOURCE_FILES=$($files.Count)"
    Write-Host "UPLOAD_THIS_ZIP=$zip"
    Write-Host 'SERVER_AND_CLIENT_UNMODIFIED=YES'
} finally {
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
}
