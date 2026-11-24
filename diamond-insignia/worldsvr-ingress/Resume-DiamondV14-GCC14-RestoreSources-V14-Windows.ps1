# V14 rebuilds the missing V4 source copies from hash-verified GitHub files,
# then runs the V13 offline GCC14 candidate build. No live service changes.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$guest='root@192.168.56.101'
$vbox=Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'
if(-not (Test-Path -LiteralPath $vbox)){throw 'STOP: VBoxManage missing'}
$vms=@(& $vbox list runningvms)
if($LASTEXITCODE -ne 0 -or @($vms|Where-Object {$_ -match '^"EP36_291_TEST"\s+\{'}).Count -ne 1){throw 'STOP: expected VM not running'}
$oldrev='ea9f3b7da93188a523221e7a6e39a8d67998d592'
$newrev='1e1a86059dc1fdb16b8e983d69536b1cba336bfe'
$files=@(
 @('worldsvr-ingress/Build-DiamondV14Real0BDAOffline.py','127df1593a669b9293480cd217af6e8cced60e8d',$oldrev),
 @('worldsvr-ingress/Apply-DiamondV14BoundClone.py','68c656912544d184b28bcd0e41e594de1ba2a639',$oldrev),
 @('worldsvr-ingress/Apply-DiamondV14Real0BDAClone.py','978d8296e63d0c8db96c73d598987bc45bf0a5b2',$oldrev),
 @('worldsvr-ingress/DiamondIngress.h','9eabfd4340153c944d8da7abdb9d9a2c41fc4aec',$oldrev),
 @('worldsvr-ingress/DiamondBoundIngress.h','3e6a18ecbd50c14dbdda4ecd4dbf1acf6f040610',$oldrev),
 @('worldsvr-ingress/DiamondReal0BDAIngressPort.h','acca51f297e881444ae9b616480996c14c00168a',$oldrev),
 @('native/diamond_abi.h','187db3ce8e588812eb5dfc291238ebad755feec0',$oldrev),
 @('native/diamond_world_bridge.h','8750a6cf084a06f80ff5cc372ceaf49dcaad4b93',$oldrev),
 @('native/diamond_merit_world_entry.h','34b6b941150992c6877d50df9e7bb534e7870b35',$oldrev),
 @('native/diamond_merit_world_entry.cpp','488a6d1e9e1885c668fb53a711d93d064728f2ab',$oldrev),
 @('worldsvr-ingress/Build-DiamondV14-GCC14Candidates-V13.py','dccc8d388251734baddca203b8c4326b1035a9c6',$newrev)
)
$temp=Join-Path $env:TEMP ('diamond-v14-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temp | Out-Null
try{
 $bundle=@()
 foreach($item in $files){
  $path=$item[0];$hash=$item[1];$rev=$item[2]
  $url="https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads/$rev/diamond-insignia/$path"
  $local=Join-Path $temp ([IO.Path]::GetFileName($path))
  Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $local -ErrorAction Stop
  $bundle+=@{path=$path;blob=$hash;data=[Convert]::ToBase64String([IO.File]::ReadAllBytes($local))}
 }
 $json=ConvertTo-Json -InputObject $bundle -Depth 5 -Compress
 $payload=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
 $script=@'
import base64,hashlib,importlib.util,json,pathlib,sys,tempfile
sys.dont_write_bytecode=True
src=pathlib.Path("/root/CABAL_V282_LIVE_MERGE_CANDIDATE_v14/source_tree/src")
baseline=pathlib.Path("/root/cabal_diamond_backup/lib.so_before_diamond_20261122")
rebuilt=pathlib.Path("/tmp/cabal_diamond_v291_gcc14_isolated_v10/libDiamondV14_GCC14_REBUILT_OFFLINE.so")
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if not src.is_dir():raise SystemExit("STOP: original V14 source missing: "+str(src))
for p,h in [(baseline,"6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab"),(rebuilt,"519394563dc196b57cb221b4c4029c4e62a242d9b787f4585a372d222cb1f524")]:
    if not p.is_file() or digest(p)!=h:raise SystemExit("STOP: required binary missing or changed: "+str(p))
work=pathlib.Path(tempfile.mkdtemp(prefix="cabal-diamond-gcc14-v14-",dir="/tmp"))
deps=work/"dependencies"
bundle=json.loads(base64.b64decode("__PAYLOAD__"))
for entry in bundle:
    rel=pathlib.PurePosixPath(entry["path"])
    if rel.is_absolute() or ".." in rel.parts or len(rel.parts)!=2 or rel.parts[0] not in ("native","worldsvr-ingress"):
        raise RuntimeError("unsafe dependency path")
    data=base64.b64decode(entry["data"],validate=True)
    blob=hashlib.sha1(("blob "+str(len(data))+"\0").encode()+data).hexdigest()
    if blob!=entry["blob"]:raise RuntimeError("Git blob verification failed: "+str(rel))
    target=deps.joinpath(*rel.parts)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(data)
def load(name):
    path=deps/"worldsvr-ingress"/name
    spec=importlib.util.spec_from_file_location(name.replace("-","_"),path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
base=load("Apply-DiamondV14BoundClone.py")
if base.manifest(src)!=(base.V14_FILE_COUNT,base.V14_TREE_SHA):
    raise SystemExit("STOP: original V14 source manifest mismatch")
print("DIAMOND_V14_DEPENDENCY_BLOBS_VERIFIED="+str(len(bundle)),flush=True)
stage=work/"stage"
stage.mkdir()
v4=load("Build-DiamondV14Real0BDAOffline.py")
v4.minimal_pure_0bda_patch(src,stage/"minimal-source",base)
v4.passive_observer_patch(stage/"minimal-source",stage/"observer-source")
load("Apply-DiamondV14Real0BDAClone.py").patch(src,stage/"source")
print("DIAMOND_V14_SOURCE_COPIES_RESTORED="+str(stage),flush=True)
v13=load("Build-DiamondV14-GCC14Candidates-V13.py")
v13.STAGE=stage
v13.OUT=work/"build"
v13.main()
print("DIAMOND_V14_REPORT="+str(v13.OUT/"REPORT.json"),flush=True)
print("DIAMOND_V14=OFFLINE_BUILD_COMPLETE",flush=True)
'@
 $script=$script.Replace('__PAYLOAD__',$payload)
 $old=$OutputEncoding
 try{
  $OutputEncoding=New-Object System.Text.UTF8Encoding($false)
  $script | & ssh.exe -T -o ConnectTimeout=12 $guest 'python3 -'
  $rc=$LASTEXITCODE
 }finally{$OutputEncoding=$old}
 if($rc -ne 0){throw "STOP: V14 restoration/build failed SSH=$rc"}
}finally{
 Remove-Item -LiteralPath $temp -Recurse -Force
}
