"""Export only the checked active Mileage+Crest source and bounded SQL metadata."""
import base64,hashlib,io,json,os,subprocess,zipfile
from pathlib import Path

SOURCE='5030798e4291bd319910679807e7b5e6054c7fa571a02624f4aab66509e0984e'
MODULE='bc6ca208ab6ba4fff92cd40884069c9c7106a8fec8166d0256e875bde51914a3'
INNER=r'''import base64,hashlib,json,stat
from pathlib import Path
source=Path('/etc/cabal/migration_tools/ep36-crest-v1/source')
root=Path('/etc/cabal/migration_tools/ep36-costume-trial-v1')
expected='5030798e4291bd319910679807e7b5e6054c7fa571a02624f4aab66509e0984e'
def need(ok,why):
 if not ok:raise RuntimeError(why)
def read(p,limit=1048576):
 need(not any(x.is_symlink() for x in (p,*p.parents)),'SOURCE_SYMLINK')
 s=p.stat();need(stat.S_ISREG(s.st_mode) and s.st_uid==0 and not s.st_mode&0o022 and s.st_size<=limit,'UNSAFE_SOURCE_FILE')
 return p.read_bytes()
def sha(b):return hashlib.sha256(b).hexdigest()
build=json.loads(read(root/'mileage-v1/build.json'))
need(build['package_sha256']==expected,'ACTIVE_SOURCE_PROFILE_CHANGED')
module=read(root/'mileage-v1/EP36CostumeMileage.so',8388608)
need(sha(module)=='bc6ca208ab6ba4fff92cd40884069c9c7106a8fec8166d0256e875bde51914a3','ACTIVE_MODULE_CHANGED')
manifest=read(source/'SHA256.json',65536);need(sha(manifest)==expected,'SOURCE_MANIFEST_CHANGED')
files={'SHA256.json':base64.b64encode(manifest).decode()};total=0
for name,digest in json.loads(manifest).items():
 p=Path(name);need(not p.is_absolute() and '..' not in p.parts and len(p.parts)<=4,'SOURCE_PATH_INVALID')
 body=read(source/p);need(sha(body)==digest,'SOURCE_FILE_CHANGED:'+name)
 total+=len(body);need(total<=4194304,'SOURCE_SIZE_LIMIT')
 files[name]=base64.b64encode(body).decode()
need(30<=len(files)<=50,'SOURCE_FILE_COUNT_DIFFERS')
print(json.dumps(dict(source_manifest_sha256=expected,module_sha256=sha(module),build=build,files=files)))
'''

SQL=r'''SET NOCOUNT ON; SET LOCK_TIMEOUT 3000;
SELECT
 (SELECT UserNum,ID FROM Account.dbo.cabal_auth_table WHERE UserNum IN(1002,1004) FOR JSON PATH) AS accounts,
 (SELECT t.name AS [table],c.name AS [column],ty.name AS [type],c.max_length,c.is_nullable
  FROM sys.tables t JOIN sys.columns c ON c.object_id=t.object_id JOIN sys.types ty ON ty.user_type_id=c.user_type_id
  WHERE t.name IN(N'CostumeCoreState',N'CostumeCoreOwned',N'CostumeCorePreset',N'CostumeCoreCatalog',N'CostumeCoreAux',N'EP36CostumeMileagePurchaseV1',N'EP36CostumeCleanV1')
  ORDER BY t.name,c.column_id FOR JSON PATH) AS schema_columns,
 (SELECT CostumeId,ServiceType,MileagePrice,ForceGemPrice,CatalogAuxValue,Enabled FROM dbo.CostumeCoreCatalog ORDER BY CostumeId FOR JSON PATH) AS catalogue,
 (SELECT c.CharacterIdx,c.Name,c.LEV,s.Mileage,s.ActivePage,s.Revision,
   (SELECT COUNT(*) FROM dbo.CostumeCoreOwned o WHERE o.CharacterIdx=c.CharacterIdx) AS owned_count,
   (SELECT COUNT(*) FROM dbo.CostumeCorePreset p WHERE p.CharacterIdx=c.CharacterIdx) AS preset_count,
   DATALENGTH(e.DATA) AS equipment_bytes
  FROM dbo.cabal_character_table c LEFT JOIN dbo.CostumeCoreState s ON s.CharacterIdx=c.CharacterIdx
  LEFT JOIN dbo.CABAL_EQUIPMENT_TABLE e ON e.CharacterIdx=c.CharacterIdx
  WHERE c.CharacterIdx/16=1004 ORDER BY c.CharacterIdx FOR JSON PATH) AS target_characters
FOR JSON PATH,WITHOUT_ARRAY_WRAPPER;
'''

def decode(raw):
    if raw.startswith((b'\xff\xfe',b'\xfe\xff')):return raw.decode('utf-16')
    if b'\0' in raw[:100]:return raw.decode('utf-16-le')
    return raw.decode('utf-8-sig')

def main():
    if os.geteuid()!=0 or Path('/sys/class/dmi/id/product_uuid').read_text().strip().lower()!='7632fb78-37a0-f645-97c0-dc322c50b002':
        raise RuntimeError('WRONG_TEST_VM_OR_ROOT_REQUIRED')
    p=subprocess.run(['docker','exec','-i','cabal_main','python3','-'],input=INNER.encode(),capture_output=True,timeout=30)
    if p.returncode:raise RuntimeError('SOURCE_READ_FAILED; NO_CHANGES')
    source=json.loads(p.stdout);files={name:base64.b64decode(b,validate=True) for name,b in source.pop('files').items()}
    if hashlib.sha256(files['SHA256.json']).hexdigest()!=SOURCE or source['module_sha256']!=MODULE:raise RuntimeError('SOURCE_IDENTITY_DIFFERS')
    for name,digest in json.loads(files['SHA256.json']).items():
        if hashlib.sha256(files[name]).hexdigest()!=digest:raise RuntimeError('SOURCE_MEMBER_HASH_DIFFERS')
    shell='''set +x
export SQLCMDPASSWORD="${MSSQL_SA_PASSWORD:-${SA_PASSWORD:-}}"
[ -n "$SQLCMDPASSWORD" ] || exit 2
tool=/opt/mssql-tools18/bin/sqlcmd
[ -x "$tool" ] || tool=/opt/mssql-tools/bin/sqlcmd
exec "$tool" -S localhost -U sa -N -C -d Server01 -b -l 5 -t 20 -h -1 -y 0 -w 65535 -i /dev/stdin
'''
    p=subprocess.run(['docker','exec','-i','sql_main','sh','-ec',shell],input=SQL.encode(),capture_output=True,timeout=30)
    source['sql_status']='READ_FAILED';snapshot={}
    if not p.returncode:
        try:
            snapshot=json.loads(decode(p.stdout).strip())
            for name,value in list(snapshot.items()):
                if isinstance(value,str) and value.startswith(('[','{')):snapshot[name]=json.loads(value)
            source['sql_status']='READ_ONLY_COMPLETE'
        except (ValueError,UnicodeError):source['sql_status']='RESULT_FORMAT_UNRECOGNIZED'
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        for name,body in files.items():z.writestr('source/'+name,body)
        z.writestr('source-report.json',json.dumps(source,indent=2))
        z.writestr('sql-read-only.json',json.dumps(snapshot,indent=2))
    body=output.getvalue()
    print(json.dumps(dict(Status='READ_ONLY_SOURCE_COMPLETE',Files=len(files),Bytes=len(body),SHA256=hashlib.sha256(body).hexdigest(),Base64=base64.b64encode(body).decode())))

if __name__=='__main__':
    try:main()
    except Exception as e:
        print(json.dumps(dict(Status='SOURCE_READ_STOPPED',Reason=str(e))));raise SystemExit(1)
