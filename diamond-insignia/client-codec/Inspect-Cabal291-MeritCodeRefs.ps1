# Fixed: remove unused C# locals prefix/op that Add-Type treated as compilation errors.
# CABAL 291 / EP39: Merit file loader code-reference static inspection only.
# Never runs game, opens game process, edits binaries, accesses SQL or server.
[CmdletBinding()]
param([string]$ClientRoot='F:\CABAL_291_TEST')
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
Write-Host 'CABAL_291_MERIT_XREF_AUDIT=READ_ONLY_STATIC'
Write-Host "CLIENT_ROOT=$ClientRoot"
Write-Host 'NO_CLIENT_EDIT=YES;NO_GAME_LAUNCH=YES;NO_PROCESS_MEMORY=YES;NO_VM_OR_SQL=YES'

$merit=Join-Path $ClientRoot 'Data\meritsystem.enc'
if (!(Test-Path -LiteralPath $merit -PathType Leaf)) {throw 'MISSING_CLIENT_MERIT_ENC'}
$meritSha=(Get-FileHash -LiteralPath $merit -Algorithm SHA256).Hash.ToLowerInvariant()
if ($meritSha -ne '3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a') {
 throw "STOP: v291 Merit file SHA changed: $meritSha"
}

$source = @'
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
public sealed class CabalPeSection {
 public string Name {get;set;}
 public uint Rva {get;set;}
 public uint VirtualSize {get;set;}
 public uint RawOffset {get;set;}
 public uint RawSize {get;set;}
 public bool IsExecutable {get;set;}
}
public sealed class CabalTarget {
 public string Name {get;set;}
 public long FileOffset {get;set;}
 public long Rva {get;set;}
 public string VaddrHex {get;set;}
 public string Section {get;set;}
}
public sealed class CabalPointer {
 public string Target {get;set;}
 public long FileOffset {get;set;}
 public long Rva {get;set;}
 public string VaddrHex {get;set;}
 public string Section {get;set;}
 public string EncodingKind {get;set;}
}
public sealed class CabalXref {
 public string Target {get;set;}
 public string TargetKind {get;set;}
 public string Instruction {get;set;}
 public long FileOffset {get;set;}
 public long Rva {get;set;}
 public string VaddrHex {get;set;}
 public string BytesAroundInstructionHex {get;set;}
 public long ContextStartFileOffset {get;set;}
}
public sealed class CabalPeReport {
 public string Status {get;set;}
 public int Machine {get;set;}
 public bool Pe64 {get;set;}
 public string ImageBaseHex {get;set;}
 public CabalPeSection[] Sections {get;set;}
 public CabalTarget[] MeritFilenameLocations {get;set;}
 public CabalPointer[] PotentialPointerEntries {get;set;}
 public CabalXref[] PotentialCodeReferences {get;set;}
 public Dictionary<string,int> ExtraStringCounts {get;set;}
 public string Caveat {get;set;}
}
public static class CabalPeMeritInspector {
 static ushort U16(byte[] b,long p){Check(b,p,2);return BitConverter.ToUInt16(b,(int)p);}
 static uint U32(byte[] b,long p){Check(b,p,4);return BitConverter.ToUInt32(b,(int)p);}
 static ulong U64(byte[] b,long p){Check(b,p,8);return BitConverter.ToUInt64(b,(int)p);}
 static void Check(byte[] b,long p,int count){
  if(p<0 || p>b.Length-count)throw new FormatException("Invalid PE offset");
 }
 static IEnumerable<int> Finds(byte[] b,byte[] pat,int limit){
  if(pat.Length==0)yield break;
  int start=0,n=0;
  while(start<b.Length-pat.Length+1 && n<limit){
   int found=Array.IndexOf(b,pat[0],start);
   if(found<0 || found>b.Length-pat.Length)yield break;
   bool match=true;
   for(int j=1;j<pat.Length;j++)if(b[found+j]!=pat[j]){match=false;break;}
   start=found+1;
   if(match){yield return found;n++;}
  }
 }
 static byte[] LE(ulong n,int width){byte[] t=BitConverter.GetBytes(n);return t.Take(width).ToArray();}
 static string H(ulong n){return "0x"+n.ToString("x");}
 static string Context(byte[] b,int p,out long start){
  int a=Math.Max(0,p-32),stop=Math.Min(b.Length,p+96);
  start=a;return BitConverter.ToString(b,a,stop-a).Replace("-","").ToLowerInvariant();
 }
 static CabalPeSection Locate(List<CabalPeSection> ss,long pos){
  return ss.FirstOrDefault(s=>pos>=s.RawOffset && pos<(long)s.RawOffset+s.RawSize);
 }
 static long Rva(List<CabalPeSection> ss,long off){
  var s=Locate(ss,off);return s==null?-1:(long)s.Rva+(off-s.RawOffset);
 }
 static long Vaddr(ulong baseAddress,long rva){return rva<0?-1:unchecked((long)(baseAddress+(ulong)rva));}
 public static CabalPeReport Analyze(byte[] b){
  if(b.Length<2048 || U16(b,0)!=0x5a4d)throw new FormatException("Not MZ PE");
  long nt=U32(b,0x3c);if(nt<0x40 || nt>b.Length-280 || U32(b,nt)!=0x4550)throw new FormatException("Not PE signature");
  ushort machine=U16(b,nt+4),sectionsCount=U16(b,nt+6);
  ushort optionalSize=U16(b,nt+20),magic=U16(b,nt+24);
  if(magic!=0x20b && magic!=0x10b)throw new FormatException("Unsupported PE optional header");
  bool is64=magic==0x20b;
  if((is64 && machine!=0x8664) || (!is64 && machine!=0x14c))throw new FormatException("PE machine mismatch");
  if(sectionsCount<1 || sectionsCount>96 || optionalSize<96)throw new FormatException("Invalid PE section count/header");
  ulong imageBase=is64?U64(b,nt+24+24):U32(b,nt+24+28);
  long sectionHeader=nt+24+optionalSize;
  Check(b,sectionHeader,sectionsCount*40);
  var ss=new List<CabalPeSection>();
  for(int i=0;i<sectionsCount;i++){
   int o=checked((int)(sectionHeader+i*40));
   string name=Encoding.ASCII.GetString(b,o,8).TrimEnd('\0');
   uint vsize=U32(b,o+8),rva=U32(b,o+12),size=U32(b,o+16),raw=U32(b,o+20);
   uint chars=U32(b,o+36);
   if(size>0 && ((long)raw+size>b.Length))throw new FormatException("Invalid section bounds");
   ss.Add(new CabalPeSection{Name=name,Rva=rva,VirtualSize=vsize,RawOffset=raw,RawSize=size,
                            IsExecutable=(chars&0x20000000)!=0});
  }
  string[] names={"meritsystem.enc","meritsystem_msg.enc","MeritPlatinum","MeritSystem"};
  var targets=new List<CabalTarget>();
  foreach(string name in names){
   foreach(int p in Finds(b,Encoding.ASCII.GetBytes(name),24)){
    long rva=Rva(ss,p);if(rva<0)continue;
    CabalPeSection sec=Locate(ss,p);
    targets.Add(new CabalTarget{Name=name,FileOffset=p,Rva=rva,
                      VaddrHex=H(imageBase+(ulong)rva),Section=sec.Name});
   }
  }
  // A pointer entry is a data-section VA (or explicit RVA) whose value points to a Merit string.
  // Including pointers to strings is necessary if the application uses an array of resource names.
  var pointers=new List<CabalPointer>();
  int width=is64?8:4;
  foreach(var t in targets){
   ulong targetVa=imageBase+(ulong)t.Rva;
   byte[] vaBytes=LE(targetVa,width),rvaBytes=LE((ulong)t.Rva,4);
   foreach(var s in ss.Where(x=>!x.IsExecutable && x.RawSize>0)){
    int from=(int)s.RawOffset,stop=checked((int)((long)s.RawOffset+s.RawSize));
    for(int off=from;off<=stop-width && pointers.Count<128;off+=width){
     bool va=true;for(int j=0;j<width;j++)if(b[off+j]!=vaBytes[j]){va=false;break;}
     if(!va)continue;
     long prva=Rva(ss,off);
     pointers.Add(new CabalPointer{Target=t.Name,FileOffset=off,Rva=prva,
           VaddrHex=H(imageBase+(ulong)prva),Section=s.Name,EncodingKind="IMAGE_VA_POINTER"});
    }
    if(width==8)continue;
    for(int off=from;off<=stop-4 && pointers.Count<128;off+=4){
     bool match=true;for(int j=0;j<4;j++)if(b[off+j]!=rvaBytes[j]){match=false;break;}
     if(!match)continue;
     long prva=Rva(ss,off);
     pointers.Add(new CabalPointer{Target=t.Name,FileOffset=off,Rva=prva,
          VaddrHex=H(imageBase+(ulong)prva),Section=s.Name,EncodingKind="RVA_POINTER_CANDIDATE"});
    }
   }
  }
  // Compare real .text instruction operands against direct Merit string VAs and pointers.
  // Only well-described x86/x64 code shapes are searched; hits remain candidates.
  var refTargets=new List<Tuple<long,string,string>>();
  foreach(var t in targets){refTargets.Add(Tuple.Create(t.Rva,t.Name,"DIRECT_STRING"));}
  foreach(var p in pointers){refTargets.Add(Tuple.Create(p.Rva,p.Target,"DATA_POINTER"));}
  var refs=new List<CabalXref>();
  foreach(var s in ss.Where(x=>x.IsExecutable && x.RawSize>0)){
   int from=(int)s.RawOffset,stop=checked((int)((long)s.RawOffset+s.RawSize));
   for(int off=from;off<stop-8;off++){
    int dispAt=0,instrLength=0;
    string instr=null;
    long destRva=-1;
    if(is64){
     if((b[off]==0x48 || b[off]==0x4c) && (b[off+1]==0x8d || b[off+1]==0x8b) &&
        (b[off+2]&0xc7)==0x05){
       instr=b[off+1]==0x8d?"LEA_RIP_REL":"MOV_RIP_REL";
       dispAt=off+3;instrLength=7;
     } else if((b[off]==0x8d || b[off]==0x8b) && (b[off+1]&0xc7)==0x05){
       instr=b[off]==0x8d?"LEA_RIP_REL":"MOV_RIP_REL";
       dispAt=off+2;instrLength=6;
     }
     if(instr!=null){
      long currentRva=Rva(ss,off);
      int disp=unchecked((int)U32(b,dispAt));
      destRva=currentRva+instrLength+disp;
     }
    } else {
     if(b[off]==0x68){instr="PUSH_IMM_VA";instrLength=5;destRva=(long)U32(b,off+1)-(long)imageBase;}
     else if(b[off]>=0xb8 && b[off]<=0xbf){
       instr="MOV_REG_IMM_VA";instrLength=5;destRva=(long)U32(b,off+1)-(long)imageBase;
     } else if(b[off]==0xa1){instr="MOV_EAX_MEM_VA";instrLength=5;destRva=(long)U32(b,off+1)-(long)imageBase;}
    }
    if(instr==null || destRva<0)continue;
    foreach(var target in refTargets){
     if(target.Item1!=destRva)continue;
     if(refs.Count>=80)break;
     long start;string context=Context(b,off,out start);
     refs.Add(new CabalXref{Target=target.Item2,TargetKind=target.Item3,
          Instruction=instr,FileOffset=off,Rva=Rva(ss,off),
          VaddrHex=H(imageBase+(ulong)Rva(ss,off)),BytesAroundInstructionHex=context,
          ContextStartFileOffset=start});
    }
   }
  }
  string[] extras={"Diamond","diamond","DIAMOND","Insignia","MeritPlatinum","MeritSystem",
        "meritsystem.enc","meritsystem_msg.enc","inflate","uncompress","zlib","deflate",
        "OnCSCMeritPlatinum","Badge_Grade"};
  var counts=new Dictionary<string,int>();
  foreach(string name in extras){
   counts[name]=Finds(b,Encoding.ASCII.GetBytes(name),48).Count();
  }
  return new CabalPeReport{Status="PE_REFERENCE_CANDIDATES_ONLY",Machine=machine,Pe64=is64,
    ImageBaseHex=H(imageBase),Sections=ss.ToArray(),MeritFilenameLocations=targets.ToArray(),
    PotentialPointerEntries=pointers.ToArray(),PotentialCodeReferences=refs.ToArray(),
    ExtraStringCounts=counts,
    Caveat="Code reference candidates are not proof of codec, data loader, XOR key, exact opcode or Diamond UI. No process tracing."};
 }
}
'@
Add-Type -TypeDefinition $source -Language CSharp -ErrorAction Stop
$smoke=[byte[]]::new(4096)
$smoke[0]=0x4d;$smoke[1]=0x5a
try { [CabalPeMeritInspector]::Analyze($smoke)|Out-Null;throw 'SELF_TEST_FAIL_MALFORMED_MZ_ACCEPTED' }
catch [System.Management.Automation.MethodInvocationException] {
 if ($_.Exception.InnerException.Message -notmatch 'PE signature|Not PE'){throw}
}
Write-Host 'PE_PARSER_NEGATIVE_TEST=PASS'
$bins=@(
 [pscustomobject]@{relative='Bin\x64\CabalMain.exe';sha='52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9'},
 [pscustomobject]@{relative='Bin\x86\CabalMain.exe';sha='7f0aa64333d5c8e1e48c1e8e8512e45b6ea91ce3efee23d8cb7dbbc63f1feb26'}
)
$reports=New-Object System.Collections.Generic.List[object]
foreach($b in $bins){
 $path=Join-Path $ClientRoot $b.relative
 if (!(Test-Path -LiteralPath $path -PathType Leaf)){throw "MISSING_CLIENT_EXE=$($b.relative)"}
 $sha=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
 if ($sha -ne $b.sha){throw "STOP: client EXE hash different for $($b.relative); no guessing"}
 $raw=[IO.File]::ReadAllBytes($path)
 if ($raw.Length -gt 75000000){throw 'CLIENT_EXE_SIZE_UNEXPECTED'}
 $r=[CabalPeMeritInspector]::Analyze($raw)
 $reports.Add([ordered]@{file=$b.relative;sha256=$sha;size=$raw.Length;pe=$r})
 Write-Host ("AUDITED="+$b.relative+";merit_strings="+$r.MeritFilenameLocations.Length+
  ";pointer_candidates="+$r.PotentialPointerEntries.Length+";code_xref_candidates="+$r.PotentialCodeReferences.Length)
}
$metadata=[ordered]@{schema=2;mode='READ_ONLY_PE_MERIT_REFERENCE_AUDIT';utc_time=[DateTime]::UtcNow.ToString('o');
 client_root=$ClientRoot;enc_sha256=$meritSha;files=@($reports.ToArray());
 game_launched=$false;client_files_modified=$false;process_memory_read=$false;server_or_sql_touched=$false;
 static_refs_are_not_verified_loader=$true}
$time=Get-Date -Format 'yyyyMMdd-HHmmss'
$rand=[guid]::NewGuid().ToString('N').Substring(0,8)
$zip=Join-Path (Join-Path $env:USERPROFILE 'Downloads') ("CABAL_DIAMOND_MERIT_REFS_${time}_${rand}.zip")
$tmp=Join-Path $env:TEMP ("CABAL_DIAMOND_MERIT_REFS_${time}_${rand}")
[void](New-Item -ItemType Directory -Path $tmp -Force)
try {
 $json=Join-Path $tmp 'MERIT_PE_XREF_REPORT.json'
 [IO.File]::WriteAllText($json,($metadata|ConvertTo-Json -Depth 10), (New-Object Text.UTF8Encoding($false)))
 [IO.File]::WriteAllText((Join-Path $tmp 'README.txt'),
  'Code xrefs and pointer-table entries are static candidates, not a proven decoder or Diamond opcode. No original binaries are in this ZIP.',
  (New-Object Text.UTF8Encoding($false)))
 Add-Type -AssemblyName System.IO.Compression.FileSystem
 [System.IO.Compression.ZipFile]::CreateFromDirectory($tmp,$zip)
 Write-Host "UPLOAD_THIS_ZIP=$zip"
 Write-Host 'CLIENT_AND_SERVER_UNMODIFIED=YES'
} finally {Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue}