$ErrorActionPreference = 'Stop'
$root = 'F:\CABAL_291_TEST'
$exe = Join-Path $root 'Bin\x64\CabalMain.exe'
$enc = Join-Path $root 'Data\costume.enc'
if ((Get-FileHash -LiteralPath $enc).Hash -ne '880fd140066cf0c30977aa0ae7f8fbf58181b0b81932380f50b80c84a186322f') { throw 'COSTUME_ENC_DIFFERS' }
if ((Get-FileHash -LiteralPath $exe).Hash -ne '52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9') { throw 'CLIENT_BUILD_DIFFERS' }
Add-Type -TypeDefinition @'
// Read known original resource-cache records. No process writes or hooks.
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
public static class Client291ResourceCacheRead {
    [StructLayout(LayoutKind.Sequential)] struct Region {
        public IntPtr Base,AllocationBase; public uint AllocationProtect;
        public ushort Partition,Padding; public UIntPtr Size; public uint State,Protect,Type;
    }
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool ReadProcessMemory(IntPtr p,IntPtr at,byte[] data,UIntPtr n,out UIntPtr got);
    [DllImport("kernel32.dll",SetLastError=true)] static extern UIntPtr VirtualQueryEx(IntPtr p,IntPtr at,out Region r,UIntPtr n);
    const long Main=0x140000000L;
    public static string Hash(byte[] b) { using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(b)).Replace("-","").ToLowerInvariant(); }
    static void Need(bool b,string error){if(!b)throw new Exception(error);}
    static byte[] Read(IntPtr handle,long at,int n) {
        Need(at>=65536 && n>0 && n<=8*1024*1024 && at<=0x7fffffffffffL-n,"READ_BOUNDS");
        long end=at+n,cursor=at;
        while(cursor<end){Region r;Need(VirtualQueryEx(handle,new IntPtr(cursor),out r,new UIntPtr(48)).ToUInt64()==48,"QUERY_FAILED");
            long next=checked(r.Base.ToInt64()+(long)r.Size.ToUInt64());
            Need(r.State==0x1000 && (r.Protect&0x101)==0 && r.Base.ToInt64()<=cursor && next>cursor,"RESOURCE_NOT_READABLE");cursor=Math.Min(next,end);}
        byte[] b=new byte[n];UIntPtr got;
        if(!ReadProcessMemory(handle,new IntPtr(at),b,new UIntPtr((uint)n),out got))throw new Win32Exception(Marshal.GetLastWin32Error());
        Need(got.ToUInt64()==(ulong)n,"SHORT_READ");return b;
    }
    static bool Equal(byte[] a,byte[] b){if(a.Length!=b.Length)return false;for(int i=0;i<a.Length;i++)if(a[i]!=b[i])return false;return true;}
    public static void CheckNativeCacheContract(IntPtr handle) {
        Need(Encoding.ASCII.GetString(Read(handle,Main,2))=="MZ","MAIN_BASE_DIFFERS");
        Need(Hash(Read(handle,Main+0x21cddb,17))=="bfe3d4f0b0724a715057165f62afbd21d98489c3b40a69db4341bdeedfff3975","RESOURCE_LOADER_CALLSITE_DIFFERS");
        Need(Hash(Read(handle,Main+0x26927a,12))=="c9b2b475fccc65d7143ce8cb3a096312c78d9a47db302de0880894119addfc04","RESOURCE_CACHE_OWNER_DIFFERS");
        Need(Hash(Read(handle,Main+0x21c18a,34))=="c9664dadf86f03431da8212867ba39938c37dcb453c3a33e92c0afd14d816101","QUEST_FILENAME_BRANCH_DIFFERS");
        Need(Hash(Read(handle,Main+0x21ca86,14))=="79080a5f6616f8579cc0254a52b886aef8d8b85537b7583c41a3e025ca630289","ANIMA_FILENAME_BRANCH_DIFFERS");
    }
    public sealed class Result {
        public string Name,Status,Root,SHA256;
        public int Index,Bytes;
        public byte[] Data;
    }
    public static Result ReadDefinition(IntPtr handle,int index) {
        Need(index==29 || index==126 || index==112,"UNKNOWN_GAME_RESOURCE_RECORD");
        string name=index==112?"costume":index==29?"quest":"AnimaMastery";
        int plain=index==112?62019:index==29?1670353:13499;
        var result=new Result{Name=name,Index=index,Status="NOT_LOADED"};
        long slot=Main+0xdd6430+index*16;
        byte[] before=Read(handle,slot,16);long pointer=BitConverter.ToInt64(before,0);uint length=BitConverter.ToUInt32(before,8);
        if(pointer==0 || length==0)return result;
        result.Status="LOADING";
        if(length==plain)return result; // Header read, before original reader increments the size.
        Need(length==plain+1,"RESOURCE_SIZE_DIFFERS="+name+":"+length);
        byte[] first=Read(handle,pointer,plain+1);
        if(first[plain]!=0)return result;
        int bom=first[0]==0xef && first[1]==0xbb && first[2]==0xbf?3:0;
        string prefix=Encoding.ASCII.GetString(first,bom,Math.Min(4096,plain-bom));
        var match=Regex.Match(prefix,@"^\s*(?:<\?xml[^>]*>\s*)?(?:<!--[\s\S]*?-->\s*)*<([A-Za-z_][A-Za-z0-9_:\-]*)\b",RegexOptions.CultureInvariant);
        if(!match.Success)return result;
        Need(index!=112 || match.Groups[1].Value=="costume","COSTUME_ROOT_DIFFERS");
        Need(index!=29 || match.Groups[1].Value=="quest","QUEST_ROOT_DIFFERS");
        string tail=Encoding.ASCII.GetString(first,Math.Max(0,plain-256),Math.Min(256,plain)).TrimEnd(' ','\t','\r','\n','\0');
        if(!tail.EndsWith("</"+match.Groups[1].Value+">",StringComparison.Ordinal))return result;
        byte[] second=Read(handle,pointer,plain+1),after=Read(handle,slot,16);
        if(!Equal(first,second) || !Equal(before,after))return result;
        byte[] data=new byte[plain];Array.Copy(first,data,plain);
        result.Status="STABLE_ORIGINAL_SDK_DECODED_RESOURCE";result.Root=match.Groups[1].Value;
        result.Data=data;result.Bytes=plain;result.SHA256=Hash(data);return result;
    }
}
'@
'GAIDU_KATALOGU: palaid CABAL_291_TEST ar savu palaideju un atver Costume Manager.'
$timer = [Diagnostics.Stopwatch]::StartNew()
$client = $null
$record = $null
$last = 'WAIT_CLIENT'
try {
    while ($timer.Elapsed.TotalSeconds -lt 180) {
        if ($null -ne $client -and $client.HasExited) {
            $client.Dispose()
            $client = $null
        }
        if ($null -eq $client) {
            $clients = @(Get-Process -Name CabalMain -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $exe })
            if ($clients.Count -gt 1) { throw 'MULTIPLE_TEST_CLIENTS' }
            if ($clients.Count -eq 0) {
                $last = 'WAIT_CLIENT'
                Start-Sleep -Milliseconds 250
                continue
            }
            $client = $clients[0]
            $checked = $false
        }
        try {
            if (!$checked) {
                [Client291ResourceCacheRead]::CheckNativeCacheContract($client.Handle)
                $checked = $true
            }
            $record = [Client291ResourceCacheRead]::ReadDefinition($client.Handle,112)
            $last = $record.Status
            if ($last -eq 'STABLE_ORIGINAL_SDK_DECODED_RESOURCE') { break }
        } catch {
            if ($client.HasExited) {
                $last = 'CLIENT_EXITED'
            } elseif (!$checked) {
                $last = 'WAIT_CLIENT_READY: ' + $_.Exception.GetBaseException().Message
            } else { throw }
        }
        Start-Sleep -Milliseconds 100
    }
    if ($last -ne 'STABLE_ORIGINAL_SDK_DECODED_RESOURCE') { throw ('COSTUME_EXPORT_TIMEOUT=' + $last) }
    $desktop = [Environment]::GetFolderPath('DesktopDirectory')
    $raw = Join-Path $desktop 'Costume291-catalogue.raw'
    [byte[]]$data = $record.Data
    [IO.File]::WriteAllBytes($raw,$data)
    try {
        $start = 0
        if ($data.Length -ge 3 -and $data[0] -eq 0xef -and $data[1] -eq 0xbb -and $data[2] -eq 0xbf) { $start = 3 }
        $offset = $start
        while ($offset -lt $data.Length -and $data[$offset] -eq 12) { $offset++ }
        if ($offset -gt $start) {
            $clean = [byte[]]::new($data.Length - $offset + $start)
            [Array]::Copy($data,0,$clean,0,$start)
            [Array]::Copy($data,$offset,$clean,$start,$data.Length - $offset)
        } else { $clean = $data }
        $stream = [IO.MemoryStream]::new($clean)
        try {
            $xml = [Xml.XmlDocument]::new()
            $xml.XmlResolver = $null
            $xml.Load($stream)
        } finally { $stream.Dispose() }
        $rows = $xml.SelectNodes('/costume/costume_list/*[@Item_ID and @Type]')
        if ($rows.Count -eq 0) { throw 'COSTUME_XML_SCHEMA_DIFFERS' }
        $pets = $xml.SelectNodes('/costume/costume_list/*[@Item_ID and @Type="5"]')
        $file = Join-Path $desktop 'Costume291-catalogue.xml'
        [IO.File]::WriteAllBytes($file,$clean)
        "PET_COUNT=$($pets.Count)"
        "UPLOAD=$file"
    } catch {
        "XML_STATUS=$($_.Exception.GetBaseException().Message)"
        "UPLOAD=$raw"
    }
} finally { if ($null -ne $client) { $client.Dispose() } }
