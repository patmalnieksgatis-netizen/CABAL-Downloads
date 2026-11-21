# CABAL v291 / EP39 Diamond Merit - exact x64 loader helper xref audit, READ ONLY.
# Source executable and Merit data SHA-256 pinned. No game run, VM, SQL or file changes.
[CmdletBinding()]
param([string]$ClientRoot='F:\CABAL_291_TEST',[switch]$SelfTestOnly)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'

$native=@'
using System;
using System.Collections.Generic;
public static class CabalMeritNativeV5 {
 public sealed class Hit {
  public int FileOffset;public int Opcode;public int Target;
  public Hit(int off,int op,int target){FileOffset=off;Opcode=op;Target=target;}
 }
 public static Hit[] FindCalls(byte[] data,int start,int stop,int delta,int[] targets){
  if(data==null || targets==null || start<0 || stop>data.Length || start>=stop)
   throw new ArgumentException("Invalid static x64 code range");
  List<Hit> hits=new List<Hit>();
  for(int i=start;i+5<=stop;i++){
   int op=data[i];if(op!=0xe8 && op!=0xe9)continue;
   long dest=(long)i+delta+5+BitConverter.ToInt32(data,i+1);
   foreach(int target in targets)if(dest==target){
    hits.Add(new Hit(i,op,target));break;
   }
  }
  return hits.ToArray();
 }
 public static int[] PdataFunction(byte[] data,int start,int length,int rva){
  if(data==null || start<0 || length<12 || (length%12)!=0 ||
     (long)start+length>data.Length)throw new ArgumentException("PDATA range invalid");
  int left=0,right=length/12-1;
  while(left<=right){
   int idx=left+(right-left)/2;
   int off=start+idx*12;
   long begin=BitConverter.ToUInt32(data,off),end=BitConverter.ToUInt32(data,off+4);
   if(rva<begin)right=idx-1;
   else if(rva>=end)left=idx+1;
   else return new int[]{(int)begin,(int)end};
  }
  return new int[0];
 }
}
'@
Add-Type -TypeDefinition $native -Language CSharp -ErrorAction Stop -WarningAction Stop
function Must([bool]$OK,[string]$Why){if(-not $OK){throw ('STOP: '+$Why)}}
function H([byte[]]$B,[int]$Start,[int]$Size) {
 Must ($Start -ge 0 -and $Size -ge 0 -and $Start+$Size -le $B.Length) 'Byte range outside client binary'
 return [BitConverter]::ToString($B,$Start,$Size).Replace('-','').ToLowerInvariant()
}
function Segment([byte[]]$B,[int]$Rva,[int]$RadiusBefore,[int]$RadiusAfter) {
 $s=[Math]::Max(1024,$Rva-3072-$RadiusBefore)
 $e=[Math]::Min(11733504,$Rva-3072+$RadiusAfter)
 Must ($s -le $e -and $e-$s -le 1024) 'Invalid snippet bounds'
 return [ordered]@{start_rva=('0x{0:x}' -f ($s+3072));bytes_hex=(H $B $s ($e-$s));
  focus_index=($Rva-3072-$s)}
}
# No game files required for synthetic Windows CI tests.
$t=New-Object byte[] 512
$t[10]=0xe8;[BitConverter]::GetBytes([int32]241).CopyTo($t,11)
$t[30]=0xe9;[BitConverter]::GetBytes([int32]221).CopyTo($t,31)
$t[60]=0xe8;[BitConverter]::GetBytes([int32]223).CopyTo($t,61)
[BitConverter]::GetBytes([uint32]0x1000).CopyTo($t,360)
[BitConverter]::GetBytes([uint32]0x1100).CopyTo($t,364)
[BitConverter]::GetBytes([uint32]0x1100).CopyTo($t,372)
[BitConverter]::GetBytes([uint32]0x1200).CopyTo($t,376)
$hits=[CabalMeritNativeV5]::FindCalls($t,0,128,4096,[int[]]@(0x1100,0x1120))
Must ($hits.Length -eq 3 -and $hits[0].Target -eq 0x1100 -and
 $hits[1].Target -eq 0x1100 -and $hits[2].Target -eq 0x1120) 'Synthetic relative call/jump target failure'
$bounds=[CabalMeritNativeV5]::PdataFunction($t,360,24,0x1100)
Must ($bounds.Length -eq 2 -and $bounds[0] -eq 0x1100 -and
 $bounds[1] -eq 0x1200) 'Synthetic function-boundary failure'
Must ([CabalMeritNativeV5]::FindCalls($t,0,128,4096,[int[]]@(0x1300)).Length -eq 0) 'Synthetic negative caller failure'
Write-Host 'MERIT_X64_V5_WINDOWS_SELF_TEST=PASS'
if($SelfTestOnly){Write-Host 'SELF_TEST_ONLY_NO_GAME_FILES_OPENED=YES';exit 0}

Write-Host 'CABAL_DIAMOND_MERIT_X64_V5=READ_ONLY_STATIC'
Write-Host "CLIENT_ROOT=$ClientRoot"
Write-Host 'ARCH=x64;GAME_LAUNCHED=NO;PROCESS_MEMORY=NO;SQL_OR_VM=NO;CLIENT_EDIT=NO'
$exe=Join-Path $ClientRoot 'Bin\x64\CabalMain.exe'
$enc=Join-Path $ClientRoot 'Data\meritsystem.enc'
Must (Test-Path -LiteralPath $exe -PathType Leaf) 'x64 client missing'
Must (Test-Path -LiteralPath $enc -PathType Leaf) 'meritsystem.enc missing'
$exeSHA=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
$encSHA=(Get-FileHash -LiteralPath $enc -Algorithm SHA256).Hash.ToLowerInvariant()
Must ($exeSHA -eq '52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9') 'Unexpected CabalMain.exe SHA'
Must ($encSHA -eq '3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a') 'Unexpected v291 Merit ENC SHA'
$b=[IO.File]::ReadAllBytes($exe)
Must ($b.Length -eq 15089000) 'Unexpected binary length'
$delta=3072;$textStart=1024;$textEnd=11733504
$pdataOff=14474752;$pdataLen=522240
Must ($pdataOff+$pdataLen -le $b.Length) 'PDATA not in executable'
# 0x21CBD4 is caller of the filename selector. 0x21D938 is its direct callee.
$wrapper=0x21cbd4
$helper=0x21d938
Must ((H $b (0x21cc08-$delta) 5) -eq 'e88befffff') 'Selector callsite changed'
Must ((H $b (0x21cc2a-$delta) 5) -eq 'e8090d0000') 'Helper callsite changed'
$targets=[ordered]@{selector_wrapper=$wrapper;selector_posthelper=$helper}
$blocks=New-Object System.Collections.Generic.List[object]
foreach($tgt in $targets.GetEnumerator()){
 $range=[CabalMeritNativeV5]::PdataFunction($b,$pdataOff,$pdataLen,[int]$tgt.Value)
 Must ($range.Length -eq 2) ('No matching PDATA function for '+$tgt.Key)
 $begin=[int]$range[0];$end=[int]$range[1]
 if($tgt.Key -eq 'selector_wrapper'){
  Must ($begin -eq $wrapper -and $end -eq 0x21cda4) 'Wrapper bounds differ from verified V4'
 }
 Must ($begin -ge $textStart+$delta -and $end -le $textEnd+$delta -and
    $end -gt $begin) ('Unexpected function range '+$tgt.Key)
 $fullSize=$end-$begin
 $firstSize=[Math]::Min($fullSize,12288)
 $tailSize=$(if($fullSize -gt $firstSize){[Math]::Min(2048,$fullSize-$firstSize)}else{0})
 $blocks.Add([ordered]@{
  name=$tgt.Key;requested_rva=('0x{0:x}' -f $tgt.Value);
  function_begin_rva=('0x{0:x}' -f $begin);
  function_end_rva=('0x{0:x}' -f $end);
  total_bytes=$fullSize;leading_bytes_hex=(H $b ($begin-$delta) $firstSize);
  trailing_bytes_start_rva=$(if($tailSize){'0x{0:x}' -f ($end-$tailSize)}else{$null});
  trailing_bytes_hex=$(if($tailSize){H $b ($end-$delta-$tailSize) $tailSize}else{''});
  code_complete=($firstSize -eq $fullSize)
 })
 Write-Host ('FUNCTION='+$tgt.Key+';rva=0x{0:x}-0x{1:x};bytes={2}' -f $begin,$end,$fullSize)
}
$found=[CabalMeritNativeV5]::FindCalls($b,$textStart,$textEnd,$delta,[int[]]@($wrapper,$helper))
Write-Host ('DIRECT_E8_E9_CANDIDATES='+$found.Length)
$results=New-Object System.Collections.Generic.List[object]
foreach($h in @($found | Select-Object -First 120)){
 $source=[int]($h.FileOffset+$delta)
 $range=[CabalMeritNativeV5]::PdataFunction($b,$pdataOff,$pdataLen,$source)
 $name=$(if($h.Target -eq $wrapper){'selector_wrapper'}else{'selector_posthelper'})
 $results.Add([ordered]@{
  source_rva=('0x{0:x}' -f $source);target=$name;
  target_rva=('0x{0:x}' -f $h.Target);
  opcode=$(if($h.Opcode -eq 232){'E8_CALL_CANDIDATE'}else{'E9_JMP_CANDIDATE'});
  source_function=$(if($range.Length -eq 2){[ordered]@{
   begin_rva=('0x{0:x}' -f $range[0]);end_rva=('0x{0:x}' -f $range[1])
  }}else{$null});window=(Segment $b $source 128 256)
 })
}
$report=[ordered]@{
 schema=5;mode='READ_ONLY_X64_MERIT_LOADER_CALL_GRAPH';
 exe_sha256=$exeSHA;merit_enc_sha256=$encSHA;
 source='F:\CABAL_291_TEST\Bin\x64\CabalMain.exe';
 functions=@($blocks.ToArray());
 raw_e8_e9_candidate_count=$found.Length;exported_contexts=@($results.ToArray());
 export_limit=120;game_launched=$false;process_memory_read=$false;
 sql_or_vm_access=$false;client_modified=$false;
 actual_decoder_found=$false;diamond_opcode_found=$false
}
$temp=Join-Path $env:TEMP ('CABAL_X64_MERIT_V5_'+[guid]::NewGuid().ToString('N'))
$zip=Join-Path (Join-Path $env:USERPROFILE 'Downloads') ('CABAL_DIAMOND_MERIT_X64_V5_'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.zip')
[void](New-Item -ItemType Directory -Path $temp)
try{
 [IO.File]::WriteAllText((Join-Path $temp 'MERIT_X64_V5_REPORT.json'),
   ($report|ConvertTo-Json -Depth 14),(New-Object Text.UTF8Encoding($false)))
 [IO.File]::WriteAllText((Join-Path $temp 'README.txt'),
   'Static x64 call target mapping only. Raw E8/E9 hits are candidates, NOT confirmed instruction boundaries, decryption, or network opcodes.',
   (New-Object Text.UTF8Encoding($false)))
 Add-Type -AssemblyName System.IO.Compression.FileSystem
 [IO.Compression.ZipFile]::CreateFromDirectory($temp,$zip)
 Write-Host ('EXPORTED_CALLER_CONTEXTS='+$results.Count)
 Write-Host "UPLOAD_THIS_ZIP=$zip"
 Write-Host 'CLIENT_AND_SERVER_UNMODIFIED=YES'
}finally{Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue}
