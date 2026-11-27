# Read selected extension source files through the operator's existing SSH.
# No SQL/configuration export, installation, service or network changes.
[CmdletBinding()]
param([string]$SshTarget='root@192.168.56.101',
      [string]$Destination=(Join-Path $env:USERPROFILE 'Downloads'))
$ErrorActionPreference='Stop'
$python=@'
import base64,hashlib,io,json,os,stat,sys,zipfile
from pathlib import Path

roots=(Path('/root/projects/WorldSvr'),Path('/root/CABAL_NATIVE_EXTRA'))
skip_dirs={'.git','build','CMakeFiles','node_modules','__pycache__','.cache'}
extensions={'.h','.hpp','.hh','.c','.cc','.cpp','.cxx','.inl','.ipp'}
files=[];missing=[];total=0
archive_bytes=io.BytesIO()
with zipfile.ZipFile(archive_bytes,'w',zipfile.ZIP_DEFLATED) as archive:
    for root in roots:
        if not root.is_dir() or root.is_symlink():
            missing.append(str(root));continue
        for directory,dirs,names in os.walk(root,followlinks=False):
            dirs[:]=sorted(n for n in dirs if n not in skip_dirs and not (Path(directory)/n).is_symlink())
            for name in sorted(names):
                path=Path(directory)/name
                if path.suffix.lower() not in extensions and name not in ('CMakeLists.txt','Makefile'):
                    continue
                if path.is_symlink():continue
                before=path.stat()
                if not stat.S_ISREG(before.st_mode):continue
                if before.st_size>8*1024*1024:raise SystemExit('SOURCE_FILE_TOO_LARGE')
                if len(files)>=5000 or total+before.st_size>48*1024*1024:
                    raise SystemExit('SOURCE_EXPORT_LIMIT')
                data=path.read_bytes();after=path.stat()
                if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns):
                    raise SystemExit('SOURCE_CHANGED_DURING_READ')
                member=root.name+'/'+path.relative_to(root).as_posix()
                archive.writestr(member,data)
                files.append({'member':member,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
                total+=len(data)
    if not files:raise SystemExit('NATIVE_SOURCE_ROOTS_MISSING_OR_EMPTY')
    manifest={'mode':'DIAMOND_NATIVE_SOURCE_EXPORT','files':files,'missing_roots':missing,
              'source_bytes':total,'sql_exported':False,'game_or_source_files_changed':False,
              'services_restarted':False}
    archive.writestr('MANIFEST.json',json.dumps(manifest,indent=2))
data=archive_bytes.getvalue()
if len(data)>24*1024*1024:raise SystemExit('COMPRESSED_EXPORT_LIMIT')
print(json.dumps({'mode':'DIAMOND_NATIVE_SOURCE_EXPORT','files':len(files),
    'missing_roots':missing,'zip_bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
    'zip_base64':base64.b64encode(data).decode('ascii')}))
'@
Write-Host 'DIAMOND: LASU_NATIVE_PAPLASINAJUMU_AVOTUS; SERVERI_NEKO_NEMAINU'
$previousEncoding=$OutputEncoding
try {
    $OutputEncoding=New-Object System.Text.UTF8Encoding($false)
    $lines=@($python | & ssh.exe -T -o ConnectTimeout=12 $SshTarget 'python3 -')
    $code=$LASTEXITCODE
} finally {
    $OutputEncoding=$previousEncoding
}
if($code -ne 0 -or $lines.Count -ne 1){throw 'NATIVE_SOURCE_READ_FAILED; ATSUTI_KLUDAS_TEKSTU'}
$record=$lines[0] | ConvertFrom-Json
if($record.mode -ne 'DIAMOND_NATIVE_SOURCE_EXPORT' -or $record.files -lt 1){throw 'NATIVE_SOURCE_REPORT_INVALID'}
if($record.zip_bytes -lt 1 -or $record.zip_bytes -gt 24MB){throw 'NATIVE_SOURCE_ZIP_SIZE'}
$bytes=[Convert]::FromBase64String($record.zip_base64)
if($bytes.Length -ne $record.zip_bytes){throw 'NATIVE_SOURCE_TRANSFER_LENGTH'}
$hasher=[Security.Cryptography.SHA256]::Create()
try {$actual=([BitConverter]::ToString($hasher.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}
finally {$hasher.Dispose()}
if($actual -ne $record.sha256){throw 'NATIVE_SOURCE_TRANSFER_HASH'}
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
$path=Join-Path $Destination ('Diamond-NativeSources-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[guid]::NewGuid().ToString('N').Substring(0,6)+'.zip')
[IO.File]::WriteAllBytes($path,$bytes)
Write-Host ('SOURCE_FILES='+$record.files)
foreach($missing in @($record.missing_roots)){Write-Host ('MISSING_SOURCE_ROOT='+$missing)}
Write-Host ('UPLOAD='+$path)
Write-Host 'SERVERA_FAILI_UN_SQL_NAV_MAINITI; PARSTARTESANA_NAV_VEIKTA'
