# CABAL v291 active x64: read-only native Merit filename-selector callers.
# NO x86, live process, SQL, SSH, or client edits. Exact hash pinned.
[CmdletBinding()]
param([string]$ClientRoot='F:\CABAL_291_TEST',[switch]$SelfTestOnly)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
function Check([bool]$ok,[string]$reason){if(-not $ok){throw ('STOP: '+$reason)}}
$cs=@'
using System;
using System.Collections.Generic;
public static class MeritCallerFinderV4 {
    public sealed class Site {
        public int FileOffset;
        public int Opcode;
        public int TargetRva;
        public Site(int offset,int opcode,int target) {
            FileOffset=offset; Opcode=opcode; TargetRva=target;
        }
    }
    public static Site[] Scan(byte[] b,int from,int to,int delta,int target) {
        if (b==null || from<0 || to>b.Length || from>=to)
            throw new ArgumentException("Bad scan range");
        List<Site> found=new List<Site>();
        for (int i=from;i+5<=to;i++) {
            int opcode=b[i];
            if (opcode!=0xe8 && opcode!=0xe9) continue;
            long destination=(long)i+delta+5+BitConverter.ToInt32(b,i+1);
            if (destination==target)
                found.Add(new Site(i,opcode,(int)destination));
        }
        return found.ToArray();
    }
    public static int[] FindFunction(byte[] b,int pdataOff,int pdataLen,int rva){
        if (b==null || pdataOff<0 || pdataLen<12 ||
            pdataOff+pdataLen>b.Length || pdataLen%12!=0)
            throw new ArgumentException("Bad PDATA range");
        int left=0,right=pdataLen/12-1;
        while(left<=right){
            int middle=left+(right-left)/2;
            int off=pdataOff+12*middle;
            long begin=BitConverter.ToUInt32(b,off);
            long end=BitConverter.ToUInt32(b,off+4);
            if (rva<begin)right=middle-1;
            else if(rva>=end)left=middle+1;
            else return new int[]{(int)begin,(int)end};
        }
        return new int[0];
    }
}
'@
Add-Type -TypeDefinition $cs -Language CSharp -ErrorAction Stop -WarningAction Stop

# The in-memory smoke needs no CABAL EXE and is run in GitHub Windows CI.
$test=New-Object byte[] 256
$test[10]=0xe8
[BitConverter]::GetBytes([int]241).CopyTo($test,11)
$test[30]=0xe9
[BitConverter]::GetBytes([int]221).CopyTo($test,31)
[BitConverter]::GetBytes([uint32]4096).CopyTo($test,200)
[BitConverter]::GetBytes([uint32]4608).CopyTo($test,204)
$t=[MeritCallerFinderV4]::Scan($test,0,100,4096,4352)
Check ($t.Length -eq 2 -and $t[0].FileOffset -eq 10 -and
 $t[1].FileOffset -eq 30 -and $t[0].Opcode -eq 232 -and
 $t[1].Opcode -eq 233) 'Synthetic E8/E9 target match'
$bounds=[MeritCallerFinderV4]::FindFunction($test,200,12,4352)
Check ($bounds.Length -eq 2 -and $bounds[0] -eq 4096 -and
 $bounds[1] -eq 4608) 'Synthetic PDATA bounds'
Check ([MeritCallerFinderV4]::Scan($test,0,100,4096,4353).Length -eq 0) 'Negative call target check'
Write-Host 'MERIT_X64_CALLER_V4_WINDOWS_SELF_TEST=PASS'
if($SelfTestOnly){Write-Host 'NO_CLIENT_FILES_OPENED=YES';exit 0}

Write-Host 'CABAL_DIAMOND_MERIT_X64_CALLER_V4=READ_ONLY_STATIC'
Write-Host "CLIENT_ROOT=$ClientRoot"
Write-Host 'ACTIVE_ARCHITECTURE=x64;GAME_RUN=NO;SQL_OR_VM=NO;CLIENT_EDIT=NO'
$exe=Join-Path $ClientRoot 'Bin\x64\CabalMain.exe'
$enc=Join-Path $ClientRoot 'Data\meritsystem.enc'
Check (Test-Path -LiteralPath $exe -PathType Leaf) 'x64 executable missing'
Check (Test-Path -LiteralPath $enc -PathType Leaf) 'v291 Merit ENC missing'
$expectedExe='52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9'
$expectedEnc='3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a'
$shaExe=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
$shaEnc=(Get-FileHash -LiteralPath $enc -Algorithm SHA256).Hash.ToLowerInvariant()
Check ($shaExe -eq $expectedExe -and $shaEnc -eq $expectedEnc) 'x64 executable or ENC SHA changed'
$b=[IO.File]::ReadAllBytes($exe)
Check ($b.Length -eq 15089000) 'Unexpected executable size'
# Hash-locked PE coordinate facts from user's verified v291 V3 static report.
$delta=3072
$textBegin=1024
$textEnd=11733504
$pdataStart=14474752
$pdataLen=522240
$entryRva=0x21bb98
$endRva=0x21cbd2
Check ($pdataStart+$pdataLen -le $b.Length) 'PDATA outside executable'
$entryOff=$entryRva-$delta
$endOff=$endRva-$delta
Check ($entryOff -gt $textBegin -and $endOff -le $textEnd) 'Selector outside .text'
# Assert x64 reference sites are unchanged; other target code is read-only.
Check (([BitConverter]::ToString($b,2209957,7).Replace('-','').ToLowerInvariant()) -eq
 '488d15bc299400') 'meritsystem.enc instruction changed'
Check (([BitConverter]::ToString($b,2210148,7).Replace('-','').ToLowerInvariant()) -eq
 '4c8d0d0d299400') 'meritsystem_msg.enc instruction changed'
$entryFunc=[MeritCallerFinderV4]::FindFunction($b,$pdataStart,$pdataLen,$entryRva)
Check ($entryFunc.Length -eq 2 -and $entryFunc[0] -eq $entryRva -and
 $entryFunc[1] -eq $endRva) 'Selector function boundaries changed'
$sites=[MeritCallerFinderV4]::Scan($b,$textBegin,$textEnd,$delta,$entryRva)
Write-Host ('DIRECT_E8_OR_E9_CANDIDATE_COUNT='+$sites.Length)
# Multiple E8 bytes can occur inside other instructions; report as CANDIDATES.
$limit=120
$results=New-Object System.Collections.Generic.List[object]
foreach($s in @($sites | Select-Object -First $limit)){
 $rva=[int]($s.FileOffset+$delta)
 $func=[MeritCallerFinderV4]::FindFunction($b,$pdataStart,$pdataLen,$rva)
 $begin=[Math]::Max($textBegin,$s.FileOffset-160)
 $stop=[Math]::Min($textEnd,$s.FileOffset+192)
 $bytes=[BitConverter]::ToString($b,$begin,[int]($stop-$begin)).Replace('-','').ToLowerInvariant()
 $results.Add([ordered]@{
  source_rva=('0x{0:x}' -f $rva);source_file_offset=$s.FileOffset;
  opcode=$(if($s.Opcode -eq 232){'E8_CALL_CANDIDATE'}else{'E9_JMP_CANDIDATE'});
  function_bounds=$(if($func.Length -eq 2){
    [ordered]@{begin=('0x{0:x}' -f $func[0]);end=('0x{0:x}' -f $func[1])}
  }else{$null});
  window_start_rva=('0x{0:x}' -f ($begin+$delta));
  code_window_hex=$bytes;focus_byte_index=($s.FileOffset-$begin)
 })
}
$functionBytes=[BitConverter]::ToString($b,$entryOff,[int]($endOff-$entryOff)).Replace('-','').ToLowerInvariant()
$report=[ordered]@{
 schema=4;mode='READ_ONLY_X64_FILENAME_SELECTOR_CALLER_AUDIT';
 client_root=$ClientRoot;exe_sha256=$shaExe;merit_enc_sha256=$shaEnc;
 arch='x64';target_function=[ordered]@{begin_rva='0x21bb98';end_rva='0x21cbd2';
  image_rva_delta=3072;body_hex=$functionBytes};
 all_e8_e9_raw_candidates=$sites.Length;exported_candidate_limit=$limit;
 candidates=@($results.ToArray());game_executed=$false;client_modified=$false;
 process_memory_read=$false;sql_or_vm_access=$false;decoder_proven=$false;
 diamond_opcode_proven=$false
}
$temp=Join-Path $env:TEMP ('CABAL_DIAMOND_CALLER_V4_'+[guid]::NewGuid().ToString('N'))
$zip=Join-Path (Join-Path $env:USERPROFILE 'Downloads') (
 'CABAL_DIAMOND_MERIT_X64_CALLERS_V4_'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.zip')
[void](New-Item -ItemType Directory -Path $temp -Force)
try{
 [IO.File]::WriteAllText((Join-Path $temp 'MERIT_X64_CALLER_V4_REPORT.json'),
   ($report|ConvertTo-Json -Depth 12),(New-Object Text.UTF8Encoding($false)))
 [IO.File]::WriteAllText((Join-Path $temp 'README.txt'),
 'X64 E8/E9 relative call/jump CANDIDATES to filename selector. False positives possible. Not a decoded ENC or Diamond opcode.',
 (New-Object Text.UTF8Encoding($false)))
 Add-Type -AssemblyName System.IO.Compression.FileSystem
 [IO.Compression.ZipFile]::CreateFromDirectory($temp,$zip)
 Write-Host ('SELECTOR_FULL_BODY_BYTES='+($endOff-$entryOff))
 Write-Host ('EXPORTED_CALLER_CONTEXTS='+$results.Count)
 Write-Host "UPLOAD_THIS_ZIP=$zip"
 Write-Host 'CLIENT_AND_SERVER_UNMODIFIED=YES'
}finally{Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue}
