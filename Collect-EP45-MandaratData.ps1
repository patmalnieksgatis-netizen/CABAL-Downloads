param([string]$DataPath, [string]$OutputDirectory = (Join-Path $env:USERPROFILE 'Downloads'))
$ErrorActionPreference = 'Stop'
if (!$DataPath) {
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Title = 'EP45 - select Data/mobserver.dat'
    $dialog.Filter = 'mobserver.dat|mobserver.dat'
    try {
        if ($dialog.ShowDialog() -ne 'OK') { return }
        $DataPath = Split-Path -Parent $dialog.FileName
    } finally { $dialog.Dispose() }
}
$root = (Get-Item -LiteralPath $DataPath).FullName
foreach ($required in 'mobserver.dat','World/world166.enc','boss_resistlist.enc') {
    if (!(Test-Path -LiteralPath (Join-Path $root $required) -PathType Leaf)) { throw "Missing: $required" }
}
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$dat = 'DgSetting.dat','Item.dat','item2.dat','item3.dat','mob.dat','mobserver.dat','ui.dat'
$entries = @(Get-ChildItem -LiteralPath $root -File -Recurse | ForEach-Object {
    $relative = $_.FullName.Substring($root.Length + 1).Replace('\','/')
    if ($relative -notmatch '(^|/)(userdata|logs?)(/|$)' -and
        ($_.Extension -in '.enc','.cbl','.scp','.xml','.lua' -or $relative -in $dat -or $relative -eq 'Map/world_113.mcl')) {
        [pscustomobject]@{ Source = $_.FullName; Name = "Data/$relative" }
    }
})
$name = 'EP45-Mandarat-Data-' + [guid]::NewGuid().ToString('N').Substring(0,10) + '.zip'
$zip = Join-Path $OutputDirectory $name
$tmp = "$zip.partial"
try {
    $archive = [IO.Compression.ZipFile]::Open($tmp, 'Create')
    try {
        foreach ($entry in $entries) {
            [void][IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive,$entry.Source,$entry.Name,[IO.Compression.CompressionLevel]::Optimal)
        }
    } finally { $archive.Dispose() }
    $check = [IO.Compression.ZipFile]::OpenRead($tmp)
    try {
        if ($check.Entries.Count -ne $entries.Count) { throw 'Archive entry count mismatch' }
    } finally { $check.Dispose() }
    [IO.File]::Move($tmp,$zip)
} finally { if ([IO.File]::Exists($tmp)) { [IO.File]::Delete($tmp) } }
Write-Host "FILES=$($entries.Count)"
Write-Host "ZIP=$zip"
