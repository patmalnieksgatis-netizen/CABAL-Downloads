# CABAL v291 Diamond Insignia: READ-ONLY client and VM preflight.
# No patches, database changes, or service restarts.
[CmdletBinding()]
param(
    [string]$ClientRoot = (Join-Path $env:USERPROFILE 'Downloads'),
    [string]$Vm = 'root@192.168.56.101',
    [string]$Container = 'cabal_main'
)
$ErrorActionPreference = 'Stop'
Write-Host 'CABAL_DIAMOND_PREFLIGHT_MODE=READ_ONLY'
Write-Host "CLIENT_SEARCH_ROOT=$ClientRoot"
Write-Host "REMOTE_VM=$Vm CONTAINER=$Container"

$clientFiles = @()
if (Test-Path -LiteralPath $ClientRoot) {
    $files = @(Get-ChildItem -LiteralPath $ClientRoot -Recurse -File -Filter 'meritsystem.enc' -ErrorAction SilentlyContinue)
    foreach ($file in $files) {
        $sha = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
        $head = if ($bytes.Length -gt 0) { [BitConverter]::ToString($bytes, 0, [Math]::Min(24, $bytes.Length)).Replace('-', '').ToLowerInvariant() } else { '' }
        $source = if ($file.FullName -match 'CABAL Transcendence \(UTS\)') { 'EP45_REFERENCE' } else { 'CLIENT_CANDIDATE' }
        $clientFiles += [pscustomobject]@{ source = $source; path = $file.FullName; bytes = $file.Length; sha256 = $sha; head_hex = $head }
    }
}
Write-Host 'CLIENT_MERIT_FILES_BEGIN'
foreach ($entry in $clientFiles) { Write-Host ($entry | ConvertTo-Json -Compress) }
Write-Host 'CLIENT_MERIT_FILES_END'
if ($clientFiles.Count -eq 0) { Write-Host 'CLIENT_MERITSYSTEM_NOT_FOUND_IN_SEARCH_ROOT=YES' }

$python = @'
import sys, json, os, hashlib, re
from collections import Counter
from pathlib import Path
from glob import glob
paths = [Path('/etc/cabal/Data/MeritSystem.scp'),Path('/etc/cabal/Data/meritsystem.scp')]
paths.extend(Path(x) for x in glob('/etc/cabal/**/MeritSystem.scp', recursive=True)[:20])
seen=set(); found=[]
for path in paths:
    if str(path) in seen: continue
    seen.add(str(path))
    if not path.is_file(): continue
    b=path.read_bytes()
    lines=b.decode('utf-8','replace').replace('\r\n','\n').splitlines()
    sections=[]; cur=None
    for ln,line in enumerate(lines,1):
        text=line.strip()
        if not text or text.startswith('#') or text.startswith(';'): continue
        if text.startswith('['):
            section=text.split(']',1)[0][1:]
            cur={'name':section,'header':text[:180],'line':ln,'rows':0,'badge_grade_values':{}}
            sections.append(cur)
        elif cur is not None:
            cur['rows']+=1
            if cur['name']=='MeritMastery_Base':
                parts=re.split(r'\s+',text)
                if len(parts)>=3:
                    k=parts[2]
                    cur['badge_grade_values'][k]=cur['badge_grade_values'].get(k,0)+1
    found.append({'path':str(path),'sha256':hashlib.sha256(b).hexdigest(),
                  'bytes':len(b),'sections':sections,
                  'diamond_or_insignia_text_hits':len(re.findall(rb'(?i)diamond|insignia',b))})
config=Path('/etc/cabal/Common.ini')
link=None
if config.is_file():
    for line in config.read_text(encoding='utf-8',errors='replace').splitlines():
        if re.match(r'^\s*MeritSystem\s*=',line,re.I):
            link=line.split('#',1)[0].strip()[:160]
            break
print('VM_DIAMOND_CONFIG_BEGIN')
print(json.dumps({'found':found,'merit_config_link':link},ensure_ascii=False))
print('VM_DIAMOND_CONFIG_END')
'@
$ssh = Get-Command ssh -ErrorAction Stop
$remoteCommand = "docker exec -i $Container python3 -"
$remoteOutput = @($python | & $ssh.Source -T $Vm $remoteCommand)
$sshCode = $LASTEXITCODE
foreach ($line in $remoteOutput) { Write-Host $line }
if ($sshCode -ne 0) { throw "DIAMOND_PREFLIGHT_SSH_FAILED_CODE=$sshCode" }
$begin = [Array]::IndexOf($remoteOutput, 'VM_DIAMOND_CONFIG_BEGIN')
if ($begin -lt 0 -or ($begin + 1) -ge $remoteOutput.Count) { throw 'VM_DIAMOND_CONFIG_JSON_MISSING' }
$server = $remoteOutput[$begin+1] | ConvertFrom-Json
$report = [pscustomobject]@{ audit = 'DiamondInsignia_v291_READONLY'; timestamp = (Get-Date).ToString('o'); client = $clientFiles; server = $server }
$reportPath = Join-Path $env:USERPROFILE 'Downloads\CABAL_DIAMOND_PREFLIGHT_REPORT.json'
$report | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host "DIAMOND_PREFLIGHT_REPORT=$reportPath"
Write-Host 'NO_CLIENT_OR_VM_FILES_CHANGED=YES'
