# CABAL v291 x64 Merit resource call graph V6 — READ ONLY
# Works with Windows PowerShell 5.1. No game launch, memory reads, SQL, VM or modifications.
[CmdletBinding()]
param([string]$ClientRoot='F:\CABAL_291_TEST',[switch]$SelfTestOnly)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'

function Assert-MeritV6([bool]$Condition,[string]$Message) {
 if(-not $Condition){throw ('STOP: '+$Message)}
}
function Get-MeritV6Hex([byte[]]$Bytes,[int]$Offset,[int]$Size) {
 Assert-MeritV6 ($null -ne $Bytes -and $Offset -ge 0 -and $Size -ge 0 -and
  ([long]$Offset+$Size) -le $Bytes.Length -and $Size -le 16384) 'Invalid static byte extraction'
 if($Size -eq 0){return ''}
 return [BitConverter]::ToString($Bytes,$Offset,$Size).Replace('-','').ToLowerInvariant()
}
function Find-MeritV6Pdata([byte[]]$Bytes,[int]$Offset,[int]$Length,[int]$Rva) {
 Assert-MeritV6 ($Offset -ge 0 -and $Length -ge 12 -and ($Length%12) -eq 0 -and
   ([long]$Offset+$Length) -le $Bytes.Length) 'Invalid PDATA'
 $lo=0;$hi=[int]($Length/12)-1
 while($lo -le $hi){
  $mid=[int]($lo+[Math]::Floor(($hi-$lo)/2))
  $pos=$Offset+$mid*12
  $begin=[BitConverter]::ToUInt32($Bytes,$pos)
  $end=[BitConverter]::ToUInt32($Bytes,$pos+4)
  if($Rva -lt $begin){$hi=$mid-1}
  elseif($Rva -ge $end){$lo=$mid+1}
  else {return @([int]$begin,[int]$end)}
 }
 return @()
}
function Get-MeritV6PdataNeighbors([byte[]]$Bytes,[int]$Offset,[int]$Length,[int]$Rva) {
 Assert-MeritV6 ($Offset -ge 0 -and $Length -ge 12 -and ($Length%12) -eq 0 -and
   ([long]$Offset+$Length) -le $Bytes.Length) 'Invalid neighbor PDATA'
 $lo=0;$hi=[int]($Length/12)-1
 while($lo -le $hi){
  $mid=[int]($lo+[Math]::Floor(($hi-$lo)/2))
  $v=[BitConverter]::ToUInt32($Bytes,$Offset+$mid*12)
  if($v -le $Rva){$lo=$mid+1}else{$hi=$mid-1}
 }
 $prevBegin=$null;$prevEnd=$null;$nextBegin=$null;$nextEnd=$null
 if($hi -ge 0){
  $p=$Offset+$hi*12
  $prevBegin=[int][BitConverter]::ToUInt32($Bytes,$p)
  $prevEnd=[int][BitConverter]::ToUInt32($Bytes,$p+4)
 }
 if($lo -lt [int]($Length/12)){
  $p=$Offset+$lo*12
  $nextBegin=[int][BitConverter]::ToUInt32($Bytes,$p)
  $nextEnd=[int][BitConverter]::ToUInt32($Bytes,$p+4)
 }
 return [pscustomobject]@{
  previous_begin_rva=$(if($null -ne $prevBegin){'0x{0:x}' -f $prevBegin}else{$null});
  previous_end_rva=$(if($null -ne $prevEnd){'0x{0:x}' -f $prevEnd}else{$null});
  next_begin_rva=$(if($null -ne $nextBegin){'0x{0:x}' -f $nextBegin}else{$null});
  next_end_rva=$(if($null -ne $nextEnd){'0x{0:x}' -f $nextEnd}else{$null})
 }
}

# Independently verify import ownership by walking EACH descriptor's lookup thunk list
# up to the first zero entry. V5's nearest-IAT heuristic could mislabel DLL ownership.
function Get-MeritV6PeFileOffset([byte[]]$Bytes,[int]$SectionStart,[int]$SectionCount,[uint32]$Rva) {
 for($i=0;$i -lt $SectionCount;$i++){
  $p=$SectionStart+$i*40
  if($p -lt 0 -or $p+40 -gt $Bytes.Length){return -1}
  $vsize=[BitConverter]::ToUInt32($Bytes,$p+8)
  $va=[BitConverter]::ToUInt32($Bytes,$p+12)
  $rawSize=[BitConverter]::ToUInt32($Bytes,$p+16)
  $rawPtr=[BitConverter]::ToUInt32($Bytes,$p+20)
  $span=[Math]::Max([long]$vsize,[long]$rawSize)
  if($Rva -ge $va -and [long]$Rva -lt [long]$va+$span -and
    ([long]$Rva-$va) -lt $rawSize){
   $o=[long]$rawPtr+([long]$Rva-$va)
   if($o -ge 0 -and $o -lt $Bytes.Length){return [int]$o}
  }
 }
 return -1
}
function Get-MeritV6Ascii([byte[]]$Bytes,[int]$Off,[int]$MaxLen) {
 if($Off -lt 0 -or $Off -ge $Bytes.Length){return $null}
 $end=$Off
 while($end -lt $Bytes.Length -and $end-$Off -lt $MaxLen -and $Bytes[$end] -ne 0){
  $end++
 }
 if($end -ge $Bytes.Length -or $end-$Off -ge $MaxLen){return $null}
 return [Text.Encoding]::ASCII.GetString($Bytes,$Off,$end-$Off)
}
function Get-MeritV6CheckedImport([byte[]]$Bytes,[int]$SlotRva) {
 if($Bytes.Length -lt 512 -or $Bytes[0] -ne 0x4d -or $Bytes[1] -ne 0x5a){return $null}
 $pe=[BitConverter]::ToInt32($Bytes,0x3c)
 if($pe -lt 64 -or $pe -gt $Bytes.Length-24){return $null}
 if([BitConverter]::ToUInt32($Bytes,$pe) -ne 0x4550){return $null}
 $n=[int][BitConverter]::ToUInt16($Bytes,$pe+6)
 $optLen=[int][BitConverter]::ToUInt16($Bytes,$pe+20)
 $opt=$pe+24
 if($n -lt 1 -or $n -gt 128 -or $optLen -lt 128 -or
   ([long]$opt+$optLen+$n*40) -gt $Bytes.Length -or
   [BitConverter]::ToUInt16($Bytes,$opt) -ne 0x20b){return $null}
 $sections=$opt+$optLen
 $impRva=[BitConverter]::ToUInt32($Bytes,$opt+120)
 if($impRva -eq 0){return $null}
 $imp=Get-MeritV6PeFileOffset $Bytes $sections $n $impRva
 if($imp -lt 0){return $null}
 for($k=0;$k -lt 512;$k++){
  $at=$imp+$k*20
  if($at+20 -gt $Bytes.Length){break}
  $orig=[BitConverter]::ToUInt32($Bytes,$at)
  $dllRva=[BitConverter]::ToUInt32($Bytes,$at+12)
  $first=[BitConverter]::ToUInt32($Bytes,$at+16)
  if($orig -eq 0 -and $dllRva -eq 0 -and $first -eq 0){break}
  if($first -eq 0 -or $SlotRva -lt $first -or ($SlotRva-$first)%8 -ne 0){continue}
  $idx=[int](($SlotRva-$first)/8)
  if($idx -gt 16384){continue}
  $lookupBase=$(if($orig -ne 0){[long]$orig}else{[long]$first})
  $entry=0UL
  $isMember=$true
  for($i=0;$i -le $idx;$i++){
   $thunkRva=$lookupBase+8L*$i
   if($thunkRva -gt [uint32]::MaxValue){$isMember=$false;break}
   $thunkOff=Get-MeritV6PeFileOffset $Bytes $sections $n ([uint32]$thunkRva)
   if($thunkOff -lt 0 -or $thunkOff+8 -gt $Bytes.Length){$isMember=$false;break}
   $entry=[BitConverter]::ToUInt64($Bytes,$thunkOff)
   if($entry -eq 0){$isMember=$false;break}
  }
  if(-not $isMember){continue}
  $dllOff=Get-MeritV6PeFileOffset $Bytes $sections $n $dllRva
  $dllName=Get-MeritV6Ascii $Bytes $dllOff 256
  if(-not $dllName){continue}
  $funcName=$null
  if(($entry -band 0x8000000000000000UL) -ne 0){
   $funcName='ordinal_'+($entry -band 0xffffUL).ToString()
  }elseif($entry -le [uint32]::MaxValue){
   $nameOff=Get-MeritV6PeFileOffset $Bytes $sections $n ([uint32]$entry)
   $funcName=Get-MeritV6Ascii $Bytes ($nameOff+2) 256
  }
  if($funcName){
   return [pscustomobject]@{
    dll=$dllName;function=$funcName;slot_rva=('0x{0:x}' -f $SlotRva);
    descriptor_index=$k;lookup_index=$idx;
    validation='CONTIGUOUS_LOOKUP_THUNKS_TO_FIRST_ZERO'
   }
  }
 }
 return $null
}

# Synthetic regression tests, always run before reading the owner's game files.
$test=New-Object byte[] 128
[BitConverter]::GetBytes([uint32]0x1000).CopyTo($test,8)
[BitConverter]::GetBytes([uint32]0x1100).CopyTo($test,12)
[BitConverter]::GetBytes([uint32]0x1300).CopyTo($test,20)
[BitConverter]::GetBytes([uint32]0x1400).CopyTo($test,24)
$r=@(Find-MeritV6Pdata $test 8 24 0x1010)
Assert-MeritV6 ($r.Count -eq 2 -and $r[0] -eq 0x1000 -and $r[1] -eq 0x1100) 'PDATA success synthetic test'
$r=@(Find-MeritV6Pdata $test 8 24 0x1200)
$n=Get-MeritV6PdataNeighbors $test 8 24 0x1200
Assert-MeritV6 ($r.Count -eq 0 -and $n.previous_end_rva -eq '0x1100' -and
 $n.next_begin_rva -eq '0x1300') 'PDATA missing-entry fallback synthetic test'
$test[36]=0xab;$test[37]=0xcd
Assert-MeritV6 ((Get-MeritV6Hex $test 36 2) -eq 'abcd') 'Hex extraction synthetic test'
# Synthetic PE32+ import descriptor with one nonzero thunk followed by a terminator.
$peProbe=New-Object byte[] 4096
$peProbe[0]=0x4d;$peProbe[1]=0x5a
[BitConverter]::GetBytes([uint32]0x80).CopyTo($peProbe,0x3c)
[BitConverter]::GetBytes([uint32]0x4550).CopyTo($peProbe,0x80)
[BitConverter]::GetBytes([uint16]1).CopyTo($peProbe,0x86)
[BitConverter]::GetBytes([uint16]0xf0).CopyTo($peProbe,0x94)
[BitConverter]::GetBytes([uint16]0x20b).CopyTo($peProbe,0x98)
[BitConverter]::GetBytes([uint32]0x1000).CopyTo($peProbe,0x98+120)
$sec=0x98+0xf0
[BitConverter]::GetBytes([uint32]0x800).CopyTo($peProbe,$sec+8)
[BitConverter]::GetBytes([uint32]0x1000).CopyTo($peProbe,$sec+12)
[BitConverter]::GetBytes([uint32]0x800).CopyTo($peProbe,$sec+16)
[BitConverter]::GetBytes([uint32]0x200).CopyTo($peProbe,$sec+20)
[BitConverter]::GetBytes([uint32]0x1100).CopyTo($peProbe,0x200)
[BitConverter]::GetBytes([uint32]0x1180).CopyTo($peProbe,0x20c)
[BitConverter]::GetBytes([uint32]0x1200).CopyTo($peProbe,0x210)
[BitConverter]::GetBytes([uint64]0x1190).CopyTo($peProbe,0x300)
[Text.Encoding]::ASCII.GetBytes('KERNEL32.dll'+[char]0).CopyTo($peProbe,0x380)
[Text.Encoding]::ASCII.GetBytes('GetFileAttributesA'+[char]0).CopyTo($peProbe,0x392)
$checked=Get-MeritV6CheckedImport $peProbe 0x1200
$pastEnd=Get-MeritV6CheckedImport $peProbe 0x1208
Assert-MeritV6 ($checked.dll -eq 'KERNEL32.dll' -and
 $checked.function -eq 'GetFileAttributesA' -and $null -eq $pastEnd) 'Import owner validation test'
Write-Host 'MERIT_X64_V6_WINDOWS_SELF_TEST=PASS'
if($SelfTestOnly){Write-Host 'SELF_TEST_ONLY_NO_GAME_FILES_OPENED=YES';exit 0}

Write-Host 'CABAL_DIAMOND_MERIT_X64_V6=READ_ONLY_STATIC'
Write-Host "CLIENT_ROOT=$ClientRoot"
Write-Host 'ARCH=x64;GAME_LAUNCHED=NO;PROCESS_MEMORY=NO;SQL_OR_VM=NO;CLIENT_EDIT=NO'
$exe=Join-Path $ClientRoot 'Bin\x64\CabalMain.exe'
$enc=Join-Path $ClientRoot 'Data\meritsystem.enc'
Assert-MeritV6 (Test-Path -LiteralPath $exe -PathType Leaf) 'x64 client missing'
Assert-MeritV6 (Test-Path -LiteralPath $enc -PathType Leaf) 'Merit ENC missing'
$exeSha=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
$encSha=(Get-FileHash -LiteralPath $enc -Algorithm SHA256).Hash.ToLowerInvariant()
Assert-MeritV6 ($exeSha -eq '52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9') 'Unexpected CabalMain.exe SHA'
Assert-MeritV6 ($encSha -eq '3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a') 'Unexpected meritsystem.enc SHA'
$bytes=[IO.File]::ReadAllBytes($exe)
Assert-MeritV6 ($bytes.Length -eq 15089000) 'Unexpected binary length'
$delta=3072;$textBeginFile=1024;$textEndFile=11733504
$pdataOffset=14474752;$pdataLength=522240
Assert-MeritV6 (($pdataOffset+$pdataLength) -le $bytes.Length) 'Unexpected PDATA end'
Assert-MeritV6 ((Get-MeritV6Hex $bytes (0x21cc2a-$delta) 5) -eq 'e8090d0000') 'V5 caller anchor mismatch'
# Targets are next evidence, NOT asserted to be read/decode routines.
$targets=@(
 [pscustomobject]@{name='filename_selector';rva=0x21bb98},
 [pscustomobject]@{name='filename_builder_helper';rva=0x21b720},
 [pscustomobject]@{name='false_branch_path_builder';rva=0x216fac},
 [pscustomobject]@{name='missing_file_path_builder';rva=0x217244},
 [pscustomobject]@{name='indexed_resource_slot_callee';rva=0x2178e0},
 [pscustomobject]@{name='special_resource_string_callee';rva=0x273c8},
 [pscustomobject]@{name='bulk_resource_initializer';rva=0x21ce38},
 [pscustomobject]@{name='indexed_path_wrapper_caller';rva=0x21cda4},
 [pscustomobject]@{name='special_id_0x89_caller';rva=0x6828a0},
 [pscustomobject]@{name='path_append_callee';rva=0x27350}
)
$out=New-Object System.Collections.Generic.List[object]
foreach($item in $targets){
 $target=[int]$item.rva
 Assert-MeritV6 ($target-$delta -ge $textBeginFile -and
  $target-$delta+2048 -le $textEndFile) ('Target outside pinned code section: '+$item.name)
 $range=@(Find-MeritV6Pdata $bytes $pdataOffset $pdataLength $target)
 if($range.Count -eq 2){
  $begin=[int]$range[0];$end=[int]$range[1]
  Assert-MeritV6 ($begin -ge $textBeginFile+$delta -and $end -le $textEndFile+$delta -and
    $end -gt $begin -and ($end-$begin) -lt 200000) ('Invalid bounded function: '+$item.name)
  $length=$end-$begin
  $head=[Math]::Min($length,8192)
  $tail=$(if($head -lt $length){[Math]::Min($length-$head,2048)}else{0})
  $out.Add([pscustomobject]@{
   name=$item.name;requested_rva=('0x{0:x}' -f $target);
   classification='PDATA_BOUNDED_FUNCTION';pdata_range_proven=$true;
   function_begin_rva=('0x{0:x}' -f $begin);function_end_rva=('0x{0:x}' -f $end);
   total_bytes=$length;code_complete=($head -eq $length);
   leading_bytes_hex=(Get-MeritV6Hex $bytes ($begin-$delta) $head);
   trailing_bytes_start_rva=$(if($tail){'0x{0:x}' -f ($end-$tail)}else{$null});
   trailing_bytes_hex=$(if($tail){Get-MeritV6Hex $bytes ($end-$delta-$tail) $tail}else{''})
  })
  Write-Host ('FUNCTION='+$item.name+';pdata=YES;range=0x{0:x}-0x{1:x};exported={2}' -f $begin,$end,($head+$tail))
 }else{
  $near=Get-MeritV6PdataNeighbors $bytes $pdataOffset $pdataLength $target
  $out.Add([pscustomobject]@{
   name=$item.name;requested_rva=('0x{0:x}' -f $target);
   classification='RAW_CALL_TARGET_NO_PDATA_ENTRY';pdata_range_proven=$false;
   function_begin_rva=$null;function_end_rva=$null;total_bytes=$null;
   code_complete=$false;raw_window_start_rva=('0x{0:x}' -f $target);
   raw_window_bytes=2048;raw_window_hex=(Get-MeritV6Hex $bytes ($target-$delta) 2048);
   preceding_window_start_rva=('0x{0:x}' -f ($target-128));
   preceding_window_hex=(Get-MeritV6Hex $bytes ($target-$delta-128) 128);
   pdata_neighbors=$near
  })
  Write-Host ('FUNCTION='+$item.name+';pdata=NO;raw_window=2048;BOUNDARIES_UNPROVEN=YES')
 }
}
$importNames=[ordered]@{
 iat_slot_0xb329f8=Get-MeritV6CheckedImport $bytes 0xb329f8
 iat_slot_0xb32c28=Get-MeritV6CheckedImport $bytes 0xb32c28
}
Write-Host ('CHECKED_IMPORT_0xB329F8=' + $(if($importNames.iat_slot_0xb329f8){$importNames.iat_slot_0xb329f8.dll+'!'+$importNames.iat_slot_0xb329f8.function}else{'UNRESOLVED'}))
Write-Host ('CHECKED_IMPORT_0xB32C28=' + $(if($importNames.iat_slot_0xb32c28){$importNames.iat_slot_0xb32c28.dll+'!'+$importNames.iat_slot_0xb32c28.function}else{'UNRESOLVED'}))
$report=[ordered]@{
 schema=6;mode='READ_ONLY_X64_MERIT_RESOURCE_CALL_CHAIN';
 exe_sha256=$exeSha;merit_enc_sha256=$encSha;
 source='F:\CABAL_291_TEST\Bin\x64\CabalMain.exe';
 targets=@($out.ToArray());checked_import_slots=$importNames;game_launched=$false;process_memory_read=$false;
 sql_or_vm_access=$false;client_modified=$false;
 binary_function_names_are_analysis_labels_only=$true;
 actual_merit_decoder_proven=$false;diamond_opcode_proven=$false
}
$temp=Join-Path $env:TEMP ('CABAL_X64_MERIT_V6_'+[guid]::NewGuid().ToString('N'))
$zip=Join-Path (Join-Path $env:USERPROFILE 'Downloads') ('CABAL_DIAMOND_MERIT_X64_V6_'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.zip')
[void](New-Item -ItemType Directory -Path $temp -Force)
try {
 [IO.File]::WriteAllText((Join-Path $temp 'MERIT_X64_V6_REPORT.json'),
  ($report|ConvertTo-Json -Depth 12),(New-Object Text.UTF8Encoding($false)))
 [IO.File]::WriteAllText((Join-Path $temp 'README.txt'),
  'Static x64 disassembly source snippets only. Analysis labels are not symbols. Unknown PDATA means no proven function boundaries. No original EXE or ENC included.',
  (New-Object Text.UTF8Encoding($false)))
 Add-Type -AssemblyName System.IO.Compression.FileSystem
 [IO.Compression.ZipFile]::CreateFromDirectory($temp,$zip)
 Write-Host ('TARGET_CONTEXTS='+$out.Count)
 Write-Host "UPLOAD_THIS_ZIP=$zip"
 Write-Host 'CLIENT_AND_SERVER_UNMODIFIED=YES'
}finally {
 Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
}
