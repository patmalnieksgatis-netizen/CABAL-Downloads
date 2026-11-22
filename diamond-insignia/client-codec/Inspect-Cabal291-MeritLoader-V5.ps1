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

 static int FileOff(byte[] d,int sect,int n,uint rva){
  for(int i=0;i<n;i++){
   int p=sect+i*40;
   if(p<0 || p+40>d.Length) return -1;
   uint virtualSize=BitConverter.ToUInt32(d,p+8);
   uint va=BitConverter.ToUInt32(d,p+12);
   uint rawSize=BitConverter.ToUInt32(d,p+16);
   uint rawPtr=BitConverter.ToUInt32(d,p+20);
   uint span=Math.Max(virtualSize,rawSize);
   if(rva>=va && (ulong)rva<(ulong)va+span && rva-va<rawSize){
    ulong off=(ulong)rawPtr+(rva-va);
    if(off<(ulong)d.Length)return (int)off;
   }
  }
  return -1;
 }
 static string Ascii(byte[] d,int off,int maxLen){
  if(off<0 || off>=d.Length)return null;
  int end=off;
  while(end<d.Length && end-off<maxLen && d[end]!=0)end++;
  if(end>=d.Length || end-off==maxLen)return null;
  return System.Text.Encoding.ASCII.GetString(d,off,end-off);
 }
 public static string ImportSlotName(byte[] d,int wantedRva){
  if(d==null || d.Length<512 || d[0]!=0x4d || d[1]!=0x5a)return null;
  int pe=BitConverter.ToInt32(d,0x3c);
  if(pe<64 || pe>d.Length-24 || BitConverter.ToUInt32(d,pe)!=0x00004550)return null;
  int n=BitConverter.ToUInt16(d,pe+6);
  int optLen=BitConverter.ToUInt16(d,pe+20);
  int opt=pe+24;
  if(n<1 || n>128 || optLen<128 || opt+optLen+n*40>d.Length ||
     BitConverter.ToUInt16(d,opt)!=0x20b)return null;
  int sec=opt+optLen;
  uint importRva=BitConverter.ToUInt32(d,opt+120);
  if(importRva==0)return null;
  int imp=FileOff(d,sec,n,importRva);
  if(imp<0)return null;
  for(int k=0;k<512;k++){
   int at=imp+k*20;
   if(at<0 || at+20>d.Length)break;
   uint orig=BitConverter.ToUInt32(d,at);
   uint dllRva=BitConverter.ToUInt32(d,at+12);
   uint iat=BitConverter.ToUInt32(d,at+16);
   if(orig==0 && dllRva==0 && iat==0)break;
   if(iat==0 || wantedRva<iat || (wantedRva-iat)%8!=0 || (wantedRva-iat)/8>65536)continue;
   uint index=(uint)(wantedRva-iat)/8;
   ulong lookup=(ulong)(orig!=0?orig:iat)+index*8UL;
   if(lookup>uint.MaxValue)continue;
   int thunk=FileOff(d,sec,n,(uint)lookup);
   if(thunk<0 || thunk+8>d.Length)continue;
   ulong entry=BitConverter.ToUInt64(d,thunk);
   if(entry==0)continue;
   int dllOff=FileOff(d,sec,n,dllRva);
   string dll=Ascii(d,dllOff,256);
   if(dll==null)continue;
   if((entry&0x8000000000000000UL)!=0)
    return dll+"!ordinal_"+(entry&0xffffUL).ToString();
   if(entry>uint.MaxValue)continue;
   int funcOff=FileOff(d,sec,n,(uint)entry);
   if(funcOff<0 || funcOff+3>d.Length)continue;
   string name=Ascii(d,funcOff+2,256);
   if(name!=null)return dll+"!"+name;
  }
  return null;
 }
 public static bool ImportParserSmoke(){
  byte[] b=new byte[4096];b[0]=0x4d;b[1]=0x5a;
  Buffer.BlockCopy(BitConverter.GetBytes(0x80),0,b,0x3c,4);
  Buffer.BlockCopy(BitConverter.GetBytes(0x00004550U),0,b,0x80,4);
  Buffer.BlockCopy(BitConverter.GetBytes((ushort)1),0,b,0x86,2);
  Buffer.BlockCopy(BitConverter.GetBytes((ushort)0xf0),0,b,0x94,2);
  int opt=0x98,sec=opt+0xf0;
  Buffer.BlockCopy(BitConverter.GetBytes((ushort)0x20b),0,b,opt,2);
  Buffer.BlockCopy(BitConverter.GetBytes(0x1000U),0,b,opt+120,4);
  Buffer.BlockCopy(BitConverter.GetBytes(0x800U),0,b,sec+8,4);
  Buffer.BlockCopy(BitConverter.GetBytes(0x1000U),0,b,sec+12,4);
  Buffer.BlockCopy(BitConverter.GetBytes(0x800U),0,b,sec+16,4);
  Buffer.BlockCopy(BitConverter.GetBytes(0x200U),0,b,sec+20,4);
  Buffer.BlockCopy(BitConverter.GetBytes(0x1100U),0,b,0x200,4);
  Buffer.BlockCopy(BitConverter.GetBytes(0x1180U),0,b,0x20c,4);
  Buffer.BlockCopy(BitConverter.GetBytes(0x1200U),0,b,0x210,4);
  Buffer.BlockCopy(BitConverter.GetBytes(0x1190UL),0,b,0x300,8);
  byte[] dll=System.Text.Encoding.ASCII.GetBytes("KERNEL32.dll\0");
  Buffer.BlockCopy(dll,0,b,0x380,dll.Length);
  byte[] name=System.Text.Encoding.ASCII.GetBytes("GetFileAttributesA\0");
  Buffer.BlockCopy(name,0,b,0x392,name.Length);
  return ImportSlotName(b,0x1200)=="KERNEL32.dll!GetFileAttributesA" &&
         ImportSlotName(b,0x1208)==null;
 }
}
'@
Add-Type -TypeDefinition $native -Language CSharp -ErrorAction Stop -WarningAction Stop
function Must([bool]$OK,[string]$Why){if(-not $OK){throw ('STOP: '+$Why)}}
function Get-MeritHexBytesV5([byte[]]$B,[int]$Start,[int]$Size) {
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
Must ([CabalMeritNativeV5]::ImportParserSmoke()) 'Synthetic PE import slot name resolution failure'
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
Must ((Get-MeritHexBytesV5 $b (0x21cc08-$delta) 5) -eq 'e88befffff') 'Selector callsite changed'
Must ((Get-MeritHexBytesV5 $b (0x21cc2a-$delta) 5) -eq 'e8090d0000') 'Helper callsite changed'
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
  total_bytes=$fullSize;leading_bytes_hex=(Get-MeritHexBytesV5 $b ($begin-$delta) $firstSize);
  trailing_bytes_start_rva=$(if($tailSize){'0x{0:x}' -f ($end-$tailSize)}else{$null});
  trailing_bytes_hex=$(if($tailSize){Get-MeritHexBytesV5 $b ($end-$delta-$tailSize) $tailSize}else{''});
  code_complete=($firstSize -eq $fullSize)
 })
 Write-Host ('FUNCTION='+$tgt.Key+';rva=0x{0:x}-0x{1:x};bytes={2}' -f $begin,$end,$fullSize)
}
$found=[CabalMeritNativeV5]::FindCalls($b,$textStart,$textEnd,$delta,[int[]]@($wrapper,$helper))
$importInfo=[ordered]@{
 iat_slot_0xb329f8=[CabalMeritNativeV5]::ImportSlotName($b,0xb329f8);
 iat_slot_0xb32c28=[CabalMeritNativeV5]::ImportSlotName($b,0xb32c28)
}
Write-Host ('IAT_0xB329F8=' + $(if($importInfo.iat_slot_0xb329f8){$importInfo.iat_slot_0xb329f8}else{'UNRESOLVED'}))
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
 import_slot_name_candidates=$importInfo;raw_e8_e9_candidate_count=$found.Length;exported_contexts=@($results.ToArray());
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
