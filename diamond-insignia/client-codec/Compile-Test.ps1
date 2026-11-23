# Windows PowerShell 5.1 compile smoke-test for the exact committed static PE scanner.
# Requires no CABAL game files. This is a build-only test.
[CmdletBinding()]
param([string]$SourceFile = (Join-Path $PSScriptRoot 'Inspect-Cabal291-MeritCodeRefs.ps1'))
$ErrorActionPreference='Stop'
if (!(Test-Path -LiteralPath $SourceFile -PathType Leaf)) {throw 'SOURCE_FILE_MISSING'}
$raw=[System.IO.File]::ReadAllText((Resolve-Path -LiteralPath $SourceFile).Path)
$anchor='$source = @'+"'"
$begin=$raw.IndexOf($anchor,[StringComparison]::Ordinal)
if ($begin -lt 0) {throw 'C_SHARP_HERE_STRING_MISSING'}
$firstNewline=$raw.IndexOf([char]10,$begin)
if ($firstNewline -lt 0) {throw 'C_SHARP_SOURCE_NO_NEWLINE'}
$end=$raw.IndexOf("'@",$firstNewline+1,[StringComparison]::Ordinal)
if ($end -lt 0){throw 'C_SHARP_HERE_STRING_UNTERMINATED'}
$cs=$raw.Substring($firstNewline+1,$end-$firstNewline-1).TrimEnd([char]13,[char]10)
if ($cs.Length -lt 8000 -or !$cs.Contains('CabalPeMeritInspector')) {throw 'C_SHARP_SOURCE_UNEXPECTED_SIZE'}
if ($cs.Contains('int prefix=0,op=off')) {throw 'UNUSED_LOCAL_COMPILE_BUG_REGRESSED'}
Add-Type -TypeDefinition $cs -Language CSharp -ErrorAction Stop -WarningAction Stop
if (-not ('CabalPeMeritInspector' -as [type])) {throw 'C_SHARP_TYPE_NOT_COMPILED'}
$smoke=New-Object byte[] 4096
$smoke[0]=0x4d
$smoke[1]=0x5a
try {
 [CabalPeMeritInspector]::Analyze($smoke) | Out-Null
 throw 'MALFORMED_PE_ACCEPTED'
} catch [System.Management.Automation.MethodInvocationException] {
 if ($_.Exception.InnerException.Message -notmatch 'PE signature|Not PE') {throw}
}
Write-Output 'WINDOWS_POWERSHELL_51_ADD_TYPE_COMPILE=PASS'
Write-Output 'PE_NEGATIVE_SMOKE=PASS'
