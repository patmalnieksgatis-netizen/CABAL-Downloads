# CABAL v291 Diamond Merit dispatch: exact SHA-pinned read-only code-window audit.
[CmdletBinding()]
param([string]$ClientRoot='F:\CABAL_291_TEST',[switch]$SelfTestOnly)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
function Assert([bool]$Condition,[string]$Message){
 if(-not $Condition){throw "STOP: $Message"}
}
function HexAt([byte[]]$Bytes,[long]$Start,[int]$Count){
 Assert ($Start -ge 0 -and $Count -gt 0 -and $Start+$Count -le $Bytes.Length) 'Byte slice out of file'
 return [BitConverter]::ToString($Bytes,[int]$Start,$Count).Replace('-','').ToLowerInvariant()
}
function JmpLanding([byte[]]$Bytes,[long]$Offset,[int]$PrefixLen){
 Assert ($Offset -ge 0 -and $Offset+$PrefixLen+5 -le $Bytes.Length) 'Truncated jump sequence'
 $op=$Offset+$PrefixLen
 Assert ($Bytes[$op] -eq 0xe9) ('Expected E9 relative JMP at offset '+$op)
 $disp=[BitConverter]::ToInt32($Bytes,[int]($op+1))
 return [long]($op+5+$disp)
}
function CodeWindow([byte[]]$Bytes,[long]$Focus,[long]$Begin,[long]$End,[int]$Before,[int]$After){
 Assert ($Focus -ge $Begin -and $Focus -lt $End) 'Code window focus outside .text'
 $start=[long][Math]::Max($Begin,$Focus-$Before)
 $stop=[long][Math]::Min($End,$Focus+$After)
 $len=[int]($stop-$start)
 Assert ($len -gt 0 -and $len -le 2048) 'Invalid code window size'
 return [ordered]@{start_file_offset=$start;focus_file_offset=$Focus;focus_index=$Focus-$start;bytes_hex=(HexAt $Bytes $start $len)}
}
function PdataFunction([byte[]]$Bytes,[long]$Rva,[long]$Start,[long]$Length){
 for($p=$Start; $p+12 -le $Start+$Length; $p+=12){
  $begin=[long][BitConverter]::ToUInt32($Bytes,[int]$p)
  $end=[long][BitConverter]::ToUInt32($Bytes,[int]($p+4))
  if($begin -le $Rva -and $Rva -lt $end){
   return [ordered]@{begin_rva=('0x{0:x}' -f $begin);end_rva=('0x{0:x}' -f $end)}
  }
 }
 return $null
}
$fake=New-Object byte[] 64
$fake[10]=0xe9
[BitConverter]::GetBytes([int32](-15)).CopyTo($fake,11)
Assert ((JmpLanding $fake 10 0) -eq 0) 'Synthetic relative JMP failure'
Assert ((HexAt $fake 10 5) -eq 'e9f1ffffff') 'Synthetic bytes failure'
$fw=CodeWindow $fake 10 0 64 5 10
Assert ($fw.focus_index -eq 5 -and $fw.bytes_hex.Length -eq 30) 'Synthetic code context failure'
Write-Host 'MERIT_V3_POWERSHELL_SELF_TEST=PASS'
if($SelfTestOnly){Write-Host 'SELF_TEST_ONLY=YES';exit 0}

Write-Host 'CABAL_DIAMOND_MERIT_DISPATCH_V3=READ_ONLY_STATIC'
Write-Host "CLIENT_ROOT=$ClientRoot"
Write-Host 'GAME_RUN=NO;PROCESS_MEMORY=NO;SQL_OR_VM=NO;CLIENT_EDIT=NO'
$enc=Join-Path $ClientRoot 'Data\meritsystem.enc'
Assert (Test-Path -LiteralPath $enc -PathType Leaf) 'v291 Merit file missing'
$encSha=(Get-FileHash -LiteralPath $enc -Algorithm SHA256).Hash.ToLowerInvariant()
Assert ($encSha -eq '3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a') 'v291 Merit hash changed'
$specs=@(
 [pscustomobject]@{Path='Bin\x64\CabalMain.exe';Sha='52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9';
  Size=15089000;TextEnd=11733504;PdataStart=14474752;PdataLen=522240;
  Entries=@(@{name='meritsystem.enc';off=2209957;ins='488d15bc299400';jump=2209290},
            @{name='meritsystem_msg.enc';off=2210148;ins='4c8d0d0d299400';jump=2209660})}
)
$all=New-Object System.Collections.Generic.List[object]
foreach($spec in $specs){
 $path=Join-Path $ClientRoot $spec.Path
 Assert (Test-Path -LiteralPath $path -PathType Leaf) ('Missing '+$spec.Path)
 $sha=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
 Assert ($sha -eq $spec.Sha) ('Client SHA mismatch '+$spec.Path)
 $bytes=[IO.File]::ReadAllBytes($path)
 Assert ($bytes.Length -eq $spec.Size) ('Unexpected file size '+$spec.Path)
 $items=New-Object System.Collections.Generic.List[object]
 $landings=New-Object 'System.Collections.Generic.HashSet[long]'
 foreach($r in $spec.Entries){
  $want=[string]$r.ins
  $len=[int]($want.Length/2)
  $actual=HexAt $bytes ([long]$r.off) $len
  Assert ($actual -eq $want) ('Instruction differs '+$spec.Path+' '+$r.name)
  $dest=JmpLanding $bytes ([long]$r.off) $len
  Assert ($dest -eq [long]$r.jump) ('Changed static branch target '+$spec.Path+' '+$r.name)
  Assert ($dest -ge 1024 -and $dest -lt $spec.TextEnd) 'Landing not in .text'
  [void]$landings.Add([long]$dest)
  $func=$null
  if($spec.PdataLen -gt 0){$func=PdataFunction $bytes ([long]$r.off+3072) $spec.PdataStart $spec.PdataLen}
  $items.Add([ordered]@{file_name=$r.name;reference_rva=('0x{0:x}' -f ([long]$r.off+3072));
    source_file_offset=$r.off;reference_opcode=$want;branch_landing_rva=('0x{0:x}' -f ($dest+3072));
    source_function=$func;source_window=(CodeWindow $bytes $r.off 1024 $spec.TextEnd 128 320)})
  Write-Host ('REF='+$spec.Path+';'+$r.name+';branch_rva=0x{0:x}' -f ($dest+3072))
 }
 $outLandings=New-Object System.Collections.Generic.List[object]
 foreach($off in @($landings | Sort-Object)){
  $func=$null
  if($spec.PdataLen -gt 0){$func=PdataFunction $bytes ($off+3072) $spec.PdataStart $spec.PdataLen}
  $outLandings.Add([ordered]@{rva=('0x{0:x}' -f ($off+3072));function=$func;
    code_window=(CodeWindow $bytes $off 1024 $spec.TextEnd 192 1088)})
 }
 $all.Add([ordered]@{exe=$spec.Path;sha256=$sha;references=@($items.ToArray());
   landing_regions=@($outLandings.ToArray())})
}
$report=[ordered]@{schema=3;mode='READ_ONLY_MERIT_DISPATCH_LANDING_AUDIT';time_utc=[DateTime]::UtcNow.ToString('o');
 client_root=$ClientRoot;merit_enc_sha256=$encSha;files=@($all.ToArray());
 independent_sites=2;game_launched=$false;client_modified=$false;sql_or_vm_touched=$false;
 decoder_found=$false;diamond_opcode_found=$false}
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$zip=Join-Path (Join-Path $env:USERPROFILE 'Downloads') ('CABAL_DIAMOND_MERIT_DISPATCH_V3_'+$stamp+'.zip')
$tempDir=Join-Path $env:TEMP ('CABAL_MERIT_DISPATCH_V3_'+[guid]::NewGuid().ToString('N'))
[void](New-Item -ItemType Directory -Path $tempDir -Force)
try{
 [IO.File]::WriteAllText((Join-Path $tempDir 'MERIT_DISPATCH_V3_REPORT.json'),
    ($report|ConvertTo-Json -Depth 16),(New-Object Text.UTF8Encoding($false)))
 [IO.File]::WriteAllText((Join-Path $tempDir 'README.txt'),
    'Static bounded x64 ONLY Merit filename branch windows, NOT a proven decoder or game opcode.',
    (New-Object Text.UTF8Encoding($false)))
 Add-Type -AssemblyName System.IO.Compression.FileSystem
 [IO.Compression.ZipFile]::CreateFromDirectory($tempDir,$zip)
 Write-Host 'INDEPENDENT_MERIT_CODE_REFERENCES=2'
 Write-Host "UPLOAD_THIS_ZIP=$zip"
 Write-Host 'CLIENT_AND_SERVER_UNMODIFIED=YES'
}finally{Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue}