# Windows PowerShell 5.1. Export the active character-save definition only.
[CmdletBinding()]
param([string]$SshTarget = 'root@192.168.56.101')
$ErrorActionPreference = 'Stop'
$reader = @'
import base64, hashlib, json, re, subprocess, sys

sql = """
SET NOCOUNT ON;
DECLARE @body varbinary(max) = CONVERT(varbinary(max),
    OBJECT_DEFINITION(OBJECT_ID(N'dbo.set_cabal_character', N'P')));
IF @body IS NULL OR DATALENGTH(@body)=0
    THROW 51001, 'SAVE_DEFINITION_UNAVAILABLE', 1;
SELECT 'SHA|' + CONVERT(varchar(64), HASHBYTES('SHA2_256',@body), 2);
DECLARE @at int=1;
WHILE @at <= DATALENGTH(@body)
BEGIN
    SELECT CONCAT(@at, '|', CONVERT(varchar(1024),SUBSTRING(@body,@at,512),2));
    SET @at += 512;
END;
"""
shell = """
set -eu
export SQLCMDPASSWORD="${MSSQL_SA_PASSWORD:-${SA_PASSWORD:-}}"
for exe in /opt/mssql-tools18/bin/sqlcmd /opt/mssql-tools/bin/sqlcmd /usr/bin/sqlcmd; do
    if [ -x "$exe" ]; then
        exec "$exe" -S localhost -d Server01 -U sa -C -b -h -1 -W -w 2048 -l 8 -t 30 -i /dev/stdin
    fi
done
exit 23
"""
result = subprocess.run(['docker','exec','-i','sql_main','sh','-c',shell],
                        input=sql.encode('ascii'), capture_output=True, timeout=60)
if result.returncode:
    sys.exit('SQLCMD_UNAVAILABLE' if result.returncode==23 else 'SAVE_DEFINITION_READ_FAILED')
rows = [s.strip() for s in result.stdout.decode('ascii').splitlines() if s.strip()]
if not rows or not re.fullmatch(r'SHA\|[0-9A-F]{64}',rows[0]):
    sys.exit('SAVE_HASH_MISSING')
data = bytearray()
for row in rows[1:]:
    pos, sep, chunk = row.partition('|')
    if not sep or pos!=str(len(data)+1) or not re.fullmatch(r'(?:[0-9a-fA-F]{2}){1,512}',chunk):
        sys.exit('SAVE_CHUNK_INVALID')
    data.extend(bytes.fromhex(chunk))
digest = hashlib.sha256(data).hexdigest()
if not data or digest != rows[0][4:].lower():
    sys.exit('SAVE_HASH_DIFFERS')
print(json.dumps(dict(sha256=digest, data=base64.b64encode(data).decode('ascii'))))
'@
$report = $reader | ssh.exe -T -o ConnectTimeout=12 $SshTarget 'python3 -'
if ($LASTEXITCODE -ne 0) { throw 'SAVE_DEFINITION_EXPORT_FAILED' }
$record = $report | ConvertFrom-Json
$bytes = [Convert]::FromBase64String($record.data)
$sha = [Security.Cryptography.SHA256]::Create()
try { $digest = [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-','').ToLowerInvariant() }
finally { $sha.Dispose() }
if ($digest -ne $record.sha256 -or $bytes.Length -eq 0) { throw 'SAVE_DOWNLOAD_HASH_DIFFERS' }
$folder = Join-Path $env:USERPROFILE 'Downloads'
[void][IO.Directory]::CreateDirectory($folder)
$path = Join-Path $folder ("Diamond-CharacterSave-" + $digest + ".txt")
$text = [Text.UnicodeEncoding]::new($false, $false, $true).GetString($bytes)
[IO.File]::WriteAllText($path, $text, [Text.UTF8Encoding]::new($false))
Write-Host "SHA256_SQL_UTF16LE=$digest"
Write-Host "UPLOAD=$path"
